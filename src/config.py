import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")

LLM_MODEL = "claude-sonnet-4-6"
FAST_LLM_MODEL = "claude-haiku-4-5-20251001"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

SCORE_WEIGHTS = {
    "exact_match": 0.30,
    "semantic_similarity": 0.30,
    "achievement": 0.25,
    "ownership": 0.15,
}

TIER_A_MIN = 72
TIER_B_MIN = 48

GITHUB_API_BASE = "https://api.github.com"

QUESTIONS_PER_TIER = {"A": 6, "B": 8, "C": 5}