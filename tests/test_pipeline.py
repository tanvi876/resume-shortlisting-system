"""
Smoke test for the evaluation pipeline.
Uses minimal mocking — tests the actual flow end-to-end.
Run with: python -m pytest tests/ -v
"""

import pytest
from src.models import ParsedResume, JobDescription, Tier
from src.scoring_engine import compute_scores, _score_exact_match
from src.question_generator import classify_tier


# ─── Unit: Exact Match Score ──────────────────────────────────────────────────

def test_exact_match_perfect():
    resume = ParsedResume(
        name="Test",
        skills=["Python", "Kafka", "PostgreSQL"],
        tools_and_technologies=["Docker"],
    )
    jd = JobDescription(
        title="Backend Engineer",
        required_skills=["Python", "Kafka"],
        preferred_skills=["Docker"],
    )
    score = _score_exact_match(resume, jd)
    assert score.score >= 90, f"Expected high exact match, got {score.score}"


def test_exact_match_zero():
    resume = ParsedResume(name="Test", skills=["Java", "Spring"], tools_and_technologies=[])
    jd = JobDescription(title="Backend Engineer", required_skills=["Python", "Kafka", "Redis"])
    score = _score_exact_match(resume, jd)
    assert score.score < 20


# ─── Unit: Tier Classification ────────────────────────────────────────────────

def test_tier_a_threshold():
    from src.models import MultiDimensionalScores, DimensionalScore
    scores = MultiDimensionalScores(
        exact_match=DimensionalScore(score=80, explanation="", evidence=[]),
        semantic_similarity=DimensionalScore(score=80, explanation="", evidence=[]),
        achievement=DimensionalScore(score=70, explanation="", evidence=[]),
        ownership=DimensionalScore(score=65, explanation="", evidence=[]),
        overall=76.25,
    )
    tier, _ = classify_tier(scores)
    assert tier == Tier.A


def test_tier_c_threshold():
    from src.models import MultiDimensionalScores, DimensionalScore
    scores = MultiDimensionalScores(
        exact_match=DimensionalScore(score=20, explanation="", evidence=[]),
        semantic_similarity=DimensionalScore(score=25, explanation="", evidence=[]),
        achievement=DimensionalScore(score=30, explanation="", evidence=[]),
        ownership=DimensionalScore(score=20, explanation="", evidence=[]),
        overall=23.75,
    )
    tier, _ = classify_tier(scores)
    assert tier == Tier.C


# ─── Integration: Full pipeline (requires API key) ────────────────────────────

@pytest.mark.integration
def test_full_pipeline_with_sample():
    """Integration test — requires ANTHROPIC_API_KEY in environment."""
    import os
    if not os.getenv("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set")

    from src.pipeline import evaluate

    with open("sample_data/sample_resume.txt") as f:
        resume_text = f.read()

    import json
    with open("sample_data/sample_jd.json") as f:
        jd_dict = json.load(f)

    report = evaluate(
        resume_text=resume_text,
        jd_dict=jd_dict,
        skip_verification=True,
    )

    assert report.candidate_name  # name was extracted
    assert 0 <= report.scores.overall <= 100
    assert report.tier in (Tier.A, Tier.B, Tier.C)
    assert len(report.interview_questions) > 0
    print(f"\n✓ {report.candidate_name} → Tier {report.tier.value} ({report.scores.overall}/100)")