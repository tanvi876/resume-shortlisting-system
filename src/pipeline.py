from __future__ import annotations
from .models import ParsedResume, JobDescription, CandidateReport
from .resume_parser import parse_resume, parse_jd_text
from .scoring_engine import compute_scores
from .verification_engine import verify_all
from .question_generator import classify_tier, generate_questions


def evaluate(
    resume_text=None, resume_pdf_path=None,
    jd_text=None, jd_dict=None,
    skip_verification=False,
) -> CandidateReport:
    resume = parse_resume(text=resume_text, pdf_path=resume_pdf_path)

    if jd_dict:
        jd = JobDescription(**jd_dict)
    elif jd_text:
        jd = JobDescription(**parse_jd_text(jd_text))
    else:
        raise ValueError("Must provide jd_text or jd_dict")

    scores = compute_scores(resume, jd)
    tier, tier_explanation = classify_tier(scores)
    verification_results = [] if skip_verification else verify_all(resume)
    questions = generate_questions(resume, jd, scores, tier, tier_explanation)

    red_flags = [f for vr in verification_results for f in vr.red_flags]
    if scores.exact_match.score < 40:
        red_flags.append(f"Low exact skill match ({scores.exact_match.score:.0f}/100)")
    if scores.ownership.score < 35:
        red_flags.append("Weak ownership signals in work history")

    strengths = [p for vr in verification_results for p in vr.positive_signals[:2]]
    if scores.semantic_similarity.score >= 75:
        strengths.append("Strong semantic alignment — transferable tech stack")
    if scores.achievement.score >= 70:
        strengths.append("Well-quantified achievements show measurable impact")
    if scores.ownership.score >= 70:
        strengths.append("Clear ownership signals — led, not just contributed")

    tier_action = {
        "A": "Fast-track to final round.",
        "B": "Proceed to technical screen. Focus on identified gaps.",
        "C": "Calibration call recommended before full interview loop.",
    }
    recommendation = (
        f"{tier_action[tier.value]} Score: {scores.overall}/100. "
        + (f"Key concern: {red_flags[0]}." if red_flags else "No major red flags.")
    )

    return CandidateReport(
        candidate_name=resume.name, job_title=jd.title,
        tier=tier, tier_explanation=tier_explanation, scores=scores,
        verification_results=verification_results, interview_questions=questions,
        overall_recommendation=recommendation, red_flags=red_flags, strengths=strengths,
    )