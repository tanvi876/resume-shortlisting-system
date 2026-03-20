from __future__ import annotations
import json
import re
from groq import Groq
from .config import GROQ_API_KEY, LLM_MODEL, TIER_A_MIN, TIER_B_MIN, QUESTIONS_PER_TIER
from .models import ParsedResume, JobDescription, MultiDimensionalScores, Tier, InterviewQuestion

_client = Groq(api_key=GROQ_API_KEY)


def classify_tier(scores: MultiDimensionalScores) -> tuple[Tier, str]:
    o = scores.overall
    dims = {
        "Exact Match": scores.exact_match.score,
        "Semantic Similarity": scores.semantic_similarity.score,
        "Achievement": scores.achievement.score,
        "Ownership": scores.ownership.score,
    }
    lowest = min(dims, key=dims.__getitem__)

    if o >= TIER_A_MIN:
        return Tier.A, (
            f"Overall score {o}/100 meets fast-track threshold ({TIER_A_MIN}+). "
            f"Strong exact match ({scores.exact_match.score:.0f}/100) and semantic similarity "
            f"({scores.semantic_similarity.score:.0f}/100) indicate solid role alignment."
        )
    elif o >= TIER_B_MIN:
        return Tier.B, (
            f"Overall score {o}/100 is in the technical screen range ({TIER_B_MIN}-{TIER_A_MIN-1}). "
            f"Shows promise but has gaps. Weakest dimension: {lowest} ({dims[lowest]:.0f}/100)."
        )
    else:
        return Tier.C, (
            f"Overall score {o}/100 is below the technical screen threshold. "
            f"Multiple significant gaps detected. Recommend calibration call first."
        )


def generate_questions(
    resume: ParsedResume,
    jd: JobDescription,
    scores: MultiDimensionalScores,
    tier: Tier,
    tier_explanation: str,
) -> list[InterviewQuestion]:
    n = QUESTIONS_PER_TIER[tier.value]
    resume_terms = {s.lower() for s in resume.skills + resume.tools_and_technologies}
    gaps = [s for s in jd.required_skills if s.lower() not in resume_terms][:5]
    recent_role = (
        f"{resume.work_experience[0].title} at {resume.work_experience[0].company}"
        if resume.work_experience else "N/A"
    )
    achievements = (
        resume.achievements + [a for e in resume.work_experience for a in e.achievements]
    )[:4]

    prompt = (
        f"You are a senior engineering interviewer. Generate {n} specific interview questions for this candidate.\n\n"
        f"Job: {jd.title}\n"
        f"Candidate: {resume.name}, {resume.years_of_experience} years exp\n"
        f"Recent Role: {recent_role}\n"
        f"Skills: {', '.join(resume.skills[:10])}\n"
        f"Achievements: {'; '.join(achievements) or 'None listed'}\n"
        f"Skill Gaps vs JD: {', '.join(gaps) or 'None'}\n"
        f"Tier: {tier.value} — {tier_explanation}\n\n"
        f"Scoring:\n"
        f"- Exact Match: {scores.exact_match.score}/100 — {scores.exact_match.explanation}\n"
        f"- Semantic Similarity: {scores.semantic_similarity.score}/100 — {scores.semantic_similarity.explanation}\n"
        f"- Achievement: {scores.achievement.score}/100 — {scores.achievement.explanation}\n"
        f"- Ownership: {scores.ownership.score}/100 — {scores.ownership.explanation}\n\n"
        f"Rules:\n"
        f"- Every question must reference something SPECIFIC from this candidate's profile\n"
        f"- Tier A: probe depth, edge cases, system design in strongest areas\n"
        f"- Tier B: probe gaps and verify strong-scoring areas\n"
        f"- Tier C: foundational questions to calibrate true knowledge level\n\n"
        f"Return ONLY a JSON array (no markdown):\n"
        f'[{{"question": "...", "category": "Technical|Behavioral|Gap-Probing|Architecture", '
        f'"rationale": "one sentence why this question for this candidate", "follow_up": "..." }}]'
    )

    response = _client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2000,
    )
    raw = response.choices[0].message.content.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return [InterviewQuestion(**q) for q in json.loads(raw)]