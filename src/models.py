from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum


class Tier(str, Enum):
    A = "A"
    B = "B"
    C = "C"


class WorkExperience(BaseModel):
    company: str = "Unknown"
    title: str = "Unknown"
    duration_months: int = 0
    responsibilities: List[str] = []
    achievements: List[str] = []
    technologies: List[str] = []


class Education(BaseModel):
    institution: str = "Unknown"
    degree: str = "Unknown"
    field: str = ""
    year: Optional[int] = None


class ParsedResume(BaseModel):
    name: str = "Unknown"
    email: Optional[str] = None
    phone: Optional[str] = None
    github_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    years_of_experience: float = 0.0
    skills: List[str] = []
    tools_and_technologies: List[str] = []
    education: List[Education] = []
    work_experience: List[WorkExperience] = []
    projects: List[Dict[str, Any]] = []
    certifications: List[str] = []
    achievements: List[str] = []
    raw_text: str = ""


class JobDescription(BaseModel):
    title: str = "Unknown Role"
    required_skills: List[str] = []
    preferred_skills: List[str] = []
    min_years_experience: float = 0.0
    responsibilities: List[str] = []
    tools_and_technologies: List[str] = []
    seniority_level: str = "mid"
    raw_text: str = ""


class DimensionalScore(BaseModel):
    score: float = Field(..., ge=0, le=100)
    explanation: str = ""
    evidence: List[str] = Field(default_factory=list)


class MultiDimensionalScores(BaseModel):
    exact_match: DimensionalScore
    semantic_similarity: DimensionalScore
    achievement: DimensionalScore
    ownership: DimensionalScore
    overall: float = Field(..., ge=0, le=100)


class VerificationResult(BaseModel):
    platform: str = ""
    url: str = ""
    verified: bool = False
    details: Dict[str, Any] = {}
    red_flags: List[str] = []
    positive_signals: List[str] = []


class InterviewQuestion(BaseModel):
    question: str = ""
    category: str = "General"
    rationale: str = ""
    follow_up: Optional[str] = None


class CandidateReport(BaseModel):
    candidate_name: str = "Unknown"
    job_title: str = "Unknown"
    tier: Tier
    tier_explanation: str = ""
    scores: MultiDimensionalScores
    verification_results: List[VerificationResult] = []
    interview_questions: List[InterviewQuestion] = []
    overall_recommendation: str = ""
    red_flags: List[str] = []
    strengths: List[str] = []