from __future__ import annotations
import json, re
import google.generativeai as genai
from .config import GEMINI_API_KEY, LLM_MODEL, TIER_A_MIN, TIER_B_MIN, QUESTIONS_PER_TIER
from .models import ParsedResume, JobDescription, MultiDimensionalScores, Tier, InterviewQuestion

genai.configure(api_key=GEMINI_API_KEY)
_model = genai.GenerativeModel(LLM_MODEL)

def classify_tier(scores: MultiDimensionalScores) -> tuple[Tier, str]:
    """
    Classify into A/B/C based on overall score. Returns (Tier, explanation).
    The explanation is the 'why' that goes into the report.
    """
    overall = scores.overall

    if overall >= TIER_A_MIN:
        tier = Tier.A
        explanation = (
            f"Overall score of {overall}/100 meets the fast-track threshold ({TIER_A_MIN}+). "
            f"Strong exact match ({scores.exact_match.score:.0f}/100) combined with "
            f"high semantic similarity ({scores.semantic_similarity.score:.0f}/100) "
            f"indicates this candidate is well-aligned with the role."
        )
    elif overall >= TIER_B_MIN:
        tier = Tier.B
        explanation = (
            f"Overall score of {overall}/100 falls in the technical screen range "
            f"({TIER_B_MIN}–{TIER_A_MIN - 1}). "
            f"The candidate shows promise but has gaps that require deeper evaluation. "
            f"Lowest dimension: "
            + _lowest_dimension_label(scores)
            + "."
        )
    else:
        tier = Tier.C
        explanation = (
            f"Overall score of {overall}/100 is below the threshold for a standard technical screen. "
            f"Multiple significant gaps detected. "
            f"Recommend foundational evaluation before investing in a full interview loop."
        )

    return tier, explanation


def _lowest_dimension_label(scores: MultiDimensionalScores) -> str:
    dims = {
        "Exact Match": scores.exact_match.score,
        "Semantic Similarity": scores.semantic_similarity.score,
        "Achievement": scores.achievement.score,
        "Ownership": scores.ownership.score,
    }
    lowest = min(dims, key=dims.__getitem__)
    return f"{lowest} ({dims[lowest]:.0f}/100)"


_QUESTION_PROMPT = """You are a senior engineering interviewer. Generate {n} specific, high-quality interview questions for this candidate applying for the {job_title} role.

--- CANDIDATE PROFILE ---
Name: {name}
Years of Experience: {yoe}
Key Skills: {skills}
Recent Role: {recent_role}
Notable Achievements: {achievements}
Identified Skill Gaps (from JD comparison): {gaps}
Tier: {tier} ({tier_rationale})

--- SCORING CONTEXT ---
Exact Match Score: {exact}/100 — {exact_expl}
Semantic Similarity Score: {sem}/100 — {sem_expl}
Achievement Score: {ach}/100 — {ach_expl}
Ownership Score: {own}/100 — {own_expl}

--- INSTRUCTIONS ---
Generate {n} questions tailored to THIS specific candidate. Do NOT use generic questions.
For Tier A: probe depth, system design, edge cases in their strongest areas.
For Tier B: probe the identified gaps, verify the truthfulness of high-scoring areas.
For Tier C: start foundational, check if gaps are knowledge gaps or experience gaps.

Each question must reference something specific from the candidate's profile (a technology they listed, a claim they made, a gap identified).

Return ONLY a JSON array with no markdown:
[
  {{
    "question": "the actual interview question",
    "category": "Technical|Behavioral|Gap-Probing|Architecture|System Design",
    "rationale": "one sentence: why THIS question for THIS candidate",
    "follow_up": "optional follow-up question or null"
  }}
]
"""


def generate_questions(
    resume: ParsedResume,
    jd: JobDescription,
    scores: MultiDimensionalScores,
    tier: Tier,
    tier_explanation: str,
) -> list[InterviewQuestion]:
    """Generate a tailored interview question set for the candidate."""

    n = QUESTIONS_PER_TIER[tier.value]

    # Identify skill gaps: JD requirements not in resume
    resume_terms = {s.lower() for s in resume.skills + resume.tools_and_technologies}
    gaps = [s for s in jd.required_skills if s.lower() not in resume_terms][:5]

    recent_role = ""
    if resume.work_experience:
        exp = resume.work_experience[0]
        recent_role = f"{exp.title} at {exp.company}"

    top_achievements = (resume.achievements + [
        a for exp in resume.work_experience for a in exp.achievements
    ])[:4]

    prompt = _QUESTION_PROMPT.format(
        n=n,
        job_title=jd.title,
        name=resume.name,
        yoe=resume.years_of_experience,
        skills=", ".join(resume.skills[:10]),
        recent_role=recent_role or "Not specified",
        achievements="; ".join(top_achievements) or "None listed",
        gaps=", ".join(gaps) or "None identified",
        tier=tier.value,
        tier_rationale=tier_explanation,
        exact=scores.exact_match.score,
        exact_expl=scores.exact_match.explanation,
        sem=scores.semantic_similarity.score,
        sem_expl=scores.semantic_similarity.explanation,
        ach=scores.achievement.score,
        ach_expl=scores.achievement.explanation,
        own=scores.ownership.score,
        own_expl=scores.ownership.explanation,
    )

    response = _model.generate_content(prompt)
    raw = response.text.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return [InterviewQuestion(**q) for q in json.loads(raw)]