import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")

LLM_MODEL = "llama-3.3-70b-versatile"
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