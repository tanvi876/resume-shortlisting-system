"""
Core data models for the Resume Shortlisting System.
All inter-module data exchange happens through these Pydantic models
so every layer has a typed, validated contract.
"""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum


class Tier(str, Enum):
    A = "A"  # Fast-track: strong match, proceed to offer/final round
    B = "B"  # Technical Screen: promising, needs deeper evaluation
    C = "C"  # Needs Evaluation: significant gaps or red flags


# ─── Resume & JD ──────────────────────────────────────────────────────────────

class WorkExperience(BaseModel):
    company: str
    title: str
    duration_months: int = 0
    responsibilities: List[str] = []
    achievements: List[str] = []
    technologies: List[str] = []

class Education(BaseModel):
    institution: str
    degree: str
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
    achievements: List[str] = []  # standalone quantified achievements
    raw_text: str = ""

class JobDescription(BaseModel):
    title: str
    required_skills: List[str] = []
    preferred_skills: List[str] = []
    min_years_experience: float = 0.0
    responsibilities: List[str] = []
    tools_and_technologies: List[str] = []
    seniority_level: str = "mid"  # junior / mid / senior / staff
    raw_text: str = ""


# ─── Scoring ──────────────────────────────────────────────────────────────────

class DimensionalScore(BaseModel):
    score: float = Field(..., ge=0, le=100, description="Score from 0 to 100")
    explanation: str
    evidence: List[str] = Field(default_factory=list, description="Concrete excerpts from resume supporting the score")

class MultiDimensionalScores(BaseModel):
    exact_match: DimensionalScore
    semantic_similarity: DimensionalScore
    achievement: DimensionalScore
    ownership: DimensionalScore
    overall: float = Field(..., ge=0, le=100)


# ─── Verification ─────────────────────────────────────────────────────────────

class VerificationResult(BaseModel):
    platform: str
    url: str
    verified: bool
    details: Dict[str, Any] = {}
    red_flags: List[str] = []
    positive_signals: List[str] = []


# ─── Questions & Report ───────────────────────────────────────────────────────

class InterviewQuestion(BaseModel):
    question: str
    category: str  # "Technical" | "Behavioral" | "Gap-Probing" | "Architecture"
    rationale: str  # why this question for this candidate
    follow_up: Optional[str] = None

class CandidateReport(BaseModel):
    candidate_name: str
    job_title: str
    tier: Tier
    tier_explanation: str
    scores: MultiDimensionalScores
    verification_results: List[VerificationResult] = []
    interview_questions: List[InterviewQuestion] = []
    overall_recommendation: str
    red_flags: List[str] = []
    strengths: List[str] = []