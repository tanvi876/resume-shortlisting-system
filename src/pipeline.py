"""
End-to-End Evaluation Pipeline
================================
Single entry point for the full candidate evaluation flow.
Takes resume text/PDF + JD text, returns a complete CandidateReport.

Flow:
  1. Parse resume → ParsedResume
  2. Parse JD → JobDescription
  3. Compute scores → MultiDimensionalScores
  4. Classify tier → Tier + explanation
  5. Verify GitHub/LinkedIn claims
  6. Generate tailored interview questions
  7. Assemble CandidateReport
"""

from __future__ import annotations
import anthropic

from .config import ANTHROPIC_API_KEY, LLM_MODEL
from .models import (
    ParsedResume, JobDescription, CandidateReport,
)
from .resume_parser import parse_resume, parse_jd_text
from .scoring_engine import compute_scores
from .verification_engine import verify_all
from .question_generator import classify_tier, generate_questions


def evaluate(
    resume_text: str | None = None,
    resume_pdf_path: str | None = None,
    jd_text: str | None = None,
    jd_dict: dict | None = None,
    skip_verification: bool = False,
) -> CandidateReport:
    """
    Run the full evaluation pipeline.

    Args:
        resume_text: Raw resume text (use this or pdf_path)
        resume_pdf_path: Path to a PDF resume
        jd_text: Raw job description text (use this or jd_dict)
        jd_dict: Pre-parsed JD dict (must match JobDescription schema)
        skip_verification: Set True to skip GitHub/LinkedIn API calls (faster for demos)

    Returns:
        CandidateReport with all scores, tier, and interview questions.
    """
    # ── 1. Parse inputs ───────────────────────────────────────────────────────
    resume: ParsedResume = parse_resume(text=resume_text, pdf_path=resume_pdf_path)

    if jd_dict:
        jd = JobDescription(**jd_dict)
    elif jd_text:
        jd = JobDescription(**parse_jd_text(jd_text))
    else:
        raise ValueError("Must provide jd_text or jd_dict")

    # ── 2. Score ──────────────────────────────────────────────────────────────
    scores = compute_scores(resume, jd)

    # ── 3. Classify tier ─────────────────────────────────────────────────────
    tier, tier_explanation = classify_tier(scores)

    # ── 4. Verify claims ──────────────────────────────────────────────────────
    verification_results = []
    if not skip_verification:
        verification_results = verify_all(resume)

    # ── 5. Generate questions ─────────────────────────────────────────────────
    questions = generate_questions(resume, jd, scores, tier, tier_explanation)

    # ── 6. Compile red flags and strengths ───────────────────────────────────
    red_flags: list[str] = []
    for vr in verification_results:
        red_flags.extend(vr.red_flags)
    if scores.exact_match.score < 40:
        red_flags.append(f"Low exact skill match ({scores.exact_match.score:.0f}/100) against JD requirements")
    if scores.ownership.score < 35:
        red_flags.append("Weak ownership signals — limited evidence of leadership or initiative")

    strengths: list[str] = []
    if scores.semantic_similarity.score >= 75:
        strengths.append("Strong semantic alignment — transferable tech stack matches role well")
    if scores.achievement.score >= 70:
        strengths.append("Well-quantified achievements demonstrate measurable impact")
    if scores.ownership.score >= 70:
        strengths.append("Clear ownership signals — candidate has led, not just contributed")
    for vr in verification_results:
        strengths.extend(vr.positive_signals[:2])

    # ── 7. Overall recommendation ─────────────────────────────────────────────
    tier_action = {
        "A": "Recommend fast-tracking to offer or final round interview.",
        "B": "Proceed to technical screen. Focus questions on identified gaps.",
        "C": "Conduct a calibration call before committing to a full interview loop.",
    }
    recommendation = (
        f"{tier_action[tier.value]} "
        f"Candidate scores {scores.overall}/100 overall. "
        + (f"Key concern: {red_flags[0]}." if red_flags else "No major red flags identified.")
    )

    return CandidateReport(
        candidate_name=resume.name,
        job_title=jd.title,
        tier=tier,
        tier_explanation=tier_explanation,
        scores=scores,
        verification_results=verification_results,
        interview_questions=questions,
        overall_recommendation=recommendation,
        red_flags=red_flags,
        strengths=strengths,
    )