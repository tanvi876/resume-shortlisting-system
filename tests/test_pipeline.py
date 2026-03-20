import pytest
from src.models import ParsedResume, JobDescription, Tier, MultiDimensionalScores, DimensionalScore
from src.scoring_engine import _score_exact_match
from src.question_generator import classify_tier


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


def test_tier_a_threshold():
    d = lambda s: DimensionalScore(score=s, explanation="", evidence=[])
    scores = MultiDimensionalScores(
        exact_match=d(80),
        semantic_similarity=d(80),
        achievement=d(70),
        ownership=d(65),
        overall=76.25,
    )
    tier, _ = classify_tier(scores)
    assert tier == Tier.A


def test_tier_c_threshold():
    d = lambda s: DimensionalScore(score=s, explanation="", evidence=[])
    scores = MultiDimensionalScores(
        exact_match=d(20),
        semantic_similarity=d(25),
        achievement=d(30),
        ownership=d(20),
        overall=23.75,
    )
    tier, _ = classify_tier(scores)
    assert tier == Tier.C


@pytest.mark.integration
def test_full_pipeline_with_sample():
    """Integration test — requires GROQ_API_KEY in environment."""
    import os, json
    if not os.getenv("GROQ_API_KEY"):
        pytest.skip("GROQ_API_KEY not set")
    from src.pipeline import evaluate
    resume_text = open("sample_data/sample_resume.txt").read()
    jd_dict = json.load(open("sample_data/sample_jd.json"))
    report = evaluate(
        resume_text=resume_text,
        jd_dict=jd_dict,
        skip_verification=True,
    )
    assert report.candidate_name
    assert 0 <= report.scores.overall <= 100
    assert report.tier in (Tier.A, Tier.B, Tier.C)
    assert len(report.interview_questions) > 0
    print(f"\n✓ {report.candidate_name} → Tier {report.tier.value} ({report.scores.overall}/100)")