from __future__ import annotations
import json, re
import numpy as np
import anthropic
from sentence_transformers import SentenceTransformer
from .config import ANTHROPIC_API_KEY, LLM_MODEL, EMBEDDING_MODEL, SCORE_WEIGHTS
from .models import ParsedResume, JobDescription, DimensionalScore, MultiDimensionalScores

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
_embedding_model = None


def _get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL)
    return _embedding_model


def _score_exact_match(resume: ParsedResume, jd: JobDescription) -> DimensionalScore:
    resume_tokens = {s.lower() for s in resume.skills + resume.tools_and_technologies}
    required = jd.required_skills
    preferred = jd.preferred_skills
    required_hits = [s for s in required if s.lower() in resume_tokens]
    preferred_hits = [s for s in preferred if s.lower() in resume_tokens]
    req_score = (len(required_hits) / len(required) * 70) if required else 70
    pref_score = (len(preferred_hits) / len(preferred) * 30) if preferred else 30
    score = round(req_score + pref_score, 1)
    missing = [s for s in required if s.lower() not in resume_tokens]
    explanation = (
        f"Candidate matches {len(required_hits)}/{len(required)} required skills "
        f"and {len(preferred_hits)}/{len(preferred)} preferred skills verbatim."
    )
    if missing:
        explanation += f" Missing required: {', '.join(missing)}."
    evidence = [f"✓ {s}" for s in required_hits[:5]] + [f"✗ {s} (missing)" for s in missing[:3]]
    return DimensionalScore(score=score, explanation=explanation, evidence=evidence)


def _score_semantic_similarity(resume: ParsedResume, jd: JobDescription) -> DimensionalScore:
    model = _get_embedding_model()
    jd_terms = jd.required_skills + jd.preferred_skills + jd.tools_and_technologies
    resume_terms = resume.skills + resume.tools_and_technologies
    if not jd_terms or not resume_terms:
        return DimensionalScore(score=0, explanation="Insufficient data.", evidence=[])
    jd_emb = model.encode(jd_terms, normalize_embeddings=True)
    res_emb = model.encode(resume_terms, normalize_embeddings=True)
    sim_matrix = np.dot(jd_emb, res_emb.T)
    best_scores = sim_matrix.max(axis=1)
    best_idx = sim_matrix.argmax(axis=1)
    avg_sim = float(best_scores.mean())
    score = round(avg_sim * 100, 1)
    top_pairs = sorted(
        zip(jd_terms, [resume_terms[i] for i in best_idx], best_scores),
        key=lambda x: -x[2]
    )[:5]
    evidence = [f"'{j}' ↔ '{r}' (sim={s:.2f})" for j, r, s in top_pairs]
    near_misses = [
        f"JD wants '{jd_terms[i]}', candidate has '{resume_terms[best_idx[i]]}' (semantically equivalent)"
        for i in range(len(jd_terms))
        if best_scores[i] > 0.65 and jd_terms[i].lower() not in {t.lower() for t in resume_terms}
    ][:3]
    explanation = f"Average semantic match: {avg_sim:.2%} across {len(jd_terms)} JD requirements."
    if near_misses:
        explanation += f" Near-equivalences: {'; '.join(near_misses)}."
    return DimensionalScore(score=score, explanation=explanation, evidence=evidence)


def _llm_score(prompt: str) -> DimensionalScore:
    response = _client.messages.create(
        model=LLM_MODEL, max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return DimensionalScore(**json.loads(raw))


def _score_achievement(resume: ParsedResume, jd: JobDescription) -> DimensionalScore:
    all_achievements = list(resume.achievements)
    for exp in resume.work_experience:
        all_achievements.extend(exp.achievements)
    if not all_achievements:
        return DimensionalScore(score=20, explanation="No quantified achievements found.", evidence=[])
    achievements_text = "\n".join(f"- {a}" for a in all_achievements[:15])
    prompt = f"""Score this candidate's achievements for the {jd.title} role (seniority: {jd.seniority_level}) from 0-100.
Consider: quantification (numbers/%), relevance to role, ambition, breadth of impact.

Achievements:
{achievements_text}

Return ONLY JSON (no markdown):
{{"score": 75, "explanation": "one paragraph", "evidence": ["achievement 1", "achievement 2"]}}"""
    return _llm_score(prompt)


def _score_ownership(resume: ParsedResume, jd: JobDescription) -> DimensionalScore:
    lines = []
    for exp in resume.work_experience:
        lines.append(f"[{exp.title} at {exp.company}]")
        for r in exp.responsibilities[:3]:
            lines.append(f"  - {r}")
        for a in exp.achievements[:2]:
            lines.append(f"  * {a}")
    for p in resume.projects[:3]:
        lines.append(f"[Project: {p.get('name','')}] {p.get('description','')}")
    if not lines:
        return DimensionalScore(score=15, explanation="Insufficient work history.", evidence=[])
    work_text = "\n".join(lines[:40])
    prompt = f"""Score ownership/leadership signals for a candidate applying for {jd.title} (seniority: {jd.seniority_level}) from 0-100.
Consider: leadership, initiative, first-person ownership language, scope growth, cross-functional impact.

Work history:
{work_text}

Return ONLY JSON (no markdown):
{{"score": 65, "explanation": "one paragraph citing specific resume language", "evidence": ["phrase 1", "phrase 2"]}}"""
    return _llm_score(prompt)


def compute_scores(resume: ParsedResume, jd: JobDescription) -> MultiDimensionalScores:
    exact = _score_exact_match(resume, jd)
    semantic = _score_semantic_similarity(resume, jd)
    achievement = _score_achievement(resume, jd)
    ownership = _score_ownership(resume, jd)
    overall = round(
        exact.score * SCORE_WEIGHTS["exact_match"]
        + semantic.score * SCORE_WEIGHTS["semantic_similarity"]
        + achievement.score * SCORE_WEIGHTS["achievement"]
        + ownership.score * SCORE_WEIGHTS["ownership"], 1
    )
    return MultiDimensionalScores(
        exact_match=exact, semantic_similarity=semantic,
        achievement=achievement, ownership=ownership, overall=overall,
    )