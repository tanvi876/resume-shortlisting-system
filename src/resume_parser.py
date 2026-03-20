from __future__ import annotations
import json
import re
import pdfplumber
from groq import Groq
from .config import GROQ_API_KEY, LLM_MODEL
from .models import ParsedResume, WorkExperience, Education

_client = Groq(api_key=GROQ_API_KEY)

_EXTRACTION_PROMPT = """You are a resume parsing expert. Extract all information from the resume text below and return it as a single JSON object matching this exact schema. Return ONLY the JSON, no markdown, no explanation.

Schema:
{
  "name": "string",
  "email": "string or null",
  "phone": "string or null",
  "github_url": "string or null",
  "linkedin_url": "string or null",
  "years_of_experience": number,
  "skills": ["list of skill strings"],
  "tools_and_technologies": ["list of tools/tech strings"],
  "education": [{"institution": "string", "degree": "string", "field": "string", "year": number or null}],
  "work_experience": [{"company": "string", "title": "string", "duration_months": number, "responsibilities": ["strings"], "achievements": ["quantified achievement strings"], "technologies": ["strings"]}],
  "projects": [{"name": "string", "description": "string", "technologies": ["strings"], "url": "string or null"}],
  "certifications": ["strings"],
  "achievements": ["standalone quantified achievements"]
}

Rules:
- years_of_experience: calculate from work history. If unclear, estimate conservatively.
- Separate skills (conceptual) from tools_and_technologies (concrete).
- duration_months: convert year ranges to months.
- achievements must contain numbers/percentages. Skip vague statements.
- If work_experience has no real entries, return an empty array [].

Resume text:
"""


def extract_text_from_pdf(pdf_path: str) -> str:
    parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                parts.append(t)
    text = "\n".join(parts)
    
    # If pdfplumber got very little text, try extracting words directly
    if len(text.strip()) < 100:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                words = page.extract_words()
                if words:
                    parts.append(" ".join(w["text"] for w in words))
        text = "\n".join(parts)
    
    return text

def _call_llm(prompt: str) -> str:
    response = _client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2000,
    )
    raw = response.choices[0].message.content.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return raw


def parse_resume(text: str | None = None, pdf_path: str | None = None) -> ParsedResume:
    if pdf_path:
        raw_text = extract_text_from_pdf(pdf_path)
    elif text:
        raw_text = text
    else:
        raise ValueError("Must provide text or pdf_path")

    raw_json = _call_llm(_EXTRACTION_PROMPT + raw_text)
    data = json.loads(raw_json)
    data["work_experience"] = [WorkExperience(**w) for w in data.get("work_experience", [])]
    data["education"] = [Education(**e) for e in data.get("education", [])]
    data["raw_text"] = raw_text
    return ParsedResume(**data)


def parse_jd_text(jd_raw: str) -> dict:
    prompt = """Extract information from this job description and return ONLY a JSON object:
{
  "title": "string",
  "required_skills": ["strings"],
  "preferred_skills": ["strings"],
  "min_years_experience": number,
  "responsibilities": ["strings"],
  "tools_and_technologies": ["strings"],
  "seniority_level": "junior|mid|senior|staff"
}

Job Description:
""" + jd_raw

    data = json.loads(_call_llm(prompt))
    data["raw_text"] = jd_raw
    return data