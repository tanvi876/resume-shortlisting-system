# System Design Document
## RecruitAI — AI Resume Shortlisting & Interview Assistant

---

## 1. Overview

RecruitAI automates the candidate evaluation pipeline. Given a resume and a job description, it produces a structured report with multi-dimensional scores, verified claims, a tier classification, and a tailored interview question set — all explainable, not just a number.

The core design principle is **depth over breadth**: every score comes with a reason, every interview question references something specific from the candidate's profile.

---

## 2. System Architecture

```
                         INPUT LAYER
                ┌────────────────────────────┐
                │   Resume (PDF or text)      │
                │   Job Description (JSON     │
                │   or plain text)            │
                └────────────┬───────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │   pipeline.py   │  <-- single orchestration entry point
                    └──┬──────────────┘
                       │
          ┌────────────┼─────────────────────┐
          │            │                     │
          ▼            ▼                     ▼
   ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐
   │   Resume    │  │   Scoring    │  │    Verification     │
   │   Parser    │  │   Engine     │  │    Engine           │
   └──────┬──────┘  └──────┬───────┘  └──────────┬──────────┘
          │                │                      │
          └────────────────┼──────────────────────┘
                           │
                           ▼
                  ┌─────────────────────┐
                  │  Question Generator │
                  │  + Tier Classifier  │
                  └──────────┬──────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ CandidateReport │  <-- final structured output
                    └─────────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  Streamlit UI   │
                    └─────────────────┘
```

---

## 3. Component Breakdown

### 3.1 Resume Parser (`resume_parser.py`)

**Job:** Turn raw resume text or a PDF into a structured `ParsedResume` object.

**How it works:**
- PDFs are converted to plain text using `pdfplumber`
- The text is passed to an LLM (Llama 3.3 70B via Groq) with a strict JSON schema prompt
- The response is parsed into a Pydantic model with fields like `skills`, `work_experience`, `achievements`, `github_url`, etc.
- A regex fence-stripper handles cases where the model wraps output in markdown code blocks

**Why LLM-based parsing instead of regex/rules?**
Resumes have no standard format. Rule-based parsers break on unconventional layouts. An LLM can handle any format and extract semantic distinctions that regex can't, like separating "skills" (conceptual: Machine Learning) from "tools" (concrete: PyTorch).

---

### 3.2 Scoring Engine (`scoring_engine.py`)

Produces four independent dimensional scores. Each score is a number plus an explanation plus evidence strings pulled from the resume.

#### Score 1: Exact Match (30%)
Simple set intersection between JD required/preferred skills and candidate's skill list. Required skills are weighted at 70%, preferred at 30%.

```
required_score = (matching_required / total_required) * 70
preferred_score = (matching_preferred / total_preferred) * 30
exact_match = required_score + preferred_score
```

#### Score 2: Semantic Similarity (30%)
This is the key differentiator. Instead of checking if "Kafka" appears verbatim, we embed every JD term and every resume term using `sentence-transformers` (`all-MiniLM-L6-v2`) and compute a cosine similarity matrix.

```
similarity_matrix[i][j] = cosine_sim(jd_term[i], resume_term[j])
best_match[i] = max(similarity_matrix[i])
score = mean(best_match) * 100
```

This catches semantically equivalent technologies:
- Kafka <-> RabbitMQ (both message queues, sim ~0.72)
- PyTorch <-> TensorFlow (both deep learning frameworks, sim ~0.78)
- AWS Kinesis <-> Kafka (both event streaming, sim ~0.68)

The near-equivalences are surfaced in the explanation so the evaluator knows why the score is high.

#### Score 3: Achievement (25%)
Passed to the LLM with a scoring rubric. The model evaluates quantification (does the achievement have numbers?), relevance to the role, ambition relative to seniority, and breadth of impact.

#### Score 4: Ownership (15%)
The LLM reads work history and looks for ownership signals: first-person language ("I built", "I led"), scope of responsibility, mentorship, cross-functional impact, and growth across roles.

#### Overall Score
```
overall = (exact * 0.30) + (semantic * 0.30) + (achievement * 0.25) + (ownership * 0.15)
```

---

### 3.3 Verification Engine (`verification_engine.py`)

Checks candidate-provided GitHub URLs against the GitHub REST API. No scraping, just public API calls.

**Checks performed:**
- Account existence and age (new accounts flagged)
- Public repo count and original vs forked ratio
- Recent push activity (last commit date)
- Language distribution vs claimed skills
- Community stars as a proxy for code quality

**LinkedIn** is URL-format validated only. LinkedIn aggressively blocks automated access so no API calls are made.

**Rate limiting:** 60 requests/hour unauthenticated, 5000/hour with a `GITHUB_TOKEN`.

---

### 3.4 Tier Classifier + Question Generator (`question_generator.py`)

**Tier classification** is deterministic, based purely on the overall score:

| Tier | Threshold | Action |
|------|-----------|--------|
| A | >= 72 | Fast-track |
| B | 48-71 | Technical screen |
| C | < 48 | Calibration call |

**Question generation** is where the system earns its keep. The LLM is given the full candidate profile, all four scores with explanations, identified skill gaps, and the tier classification. It generates N questions (6 for Tier A, 8 for Tier B, 5 for Tier C) that are explicitly tied to this specific candidate.

The prompt enforces:
- Every question must reference something from the candidate's actual profile
- Tier A questions probe depth and edge cases in strong areas
- Tier B questions probe gaps and verify high-scoring claims
- Tier C questions are foundational to calibrate actual knowledge level

---

### 3.5 Pipeline (`pipeline.py`)

Single entry point that orchestrates all of the above in order. Stateless by design: takes inputs, returns a `CandidateReport`, holds no state between calls. This makes it horizontally scalable without any changes.

---

## 4. Data Flow

```
1. User provides resume text/PDF + JD text/JSON
        |
2. resume_parser extracts structured ParsedResume
        |
3. scoring_engine computes 4 scores in parallel (conceptually):
        |-- exact_match (deterministic, no API call)
        |-- semantic_similarity (local embedding model, no API call)
        |-- achievement (1 LLM call)
        |-- ownership (1 LLM call)
        |
4. question_generator classifies tier + calls LLM for questions
        |
5. verification_engine calls GitHub API (optional)
        |
6. pipeline assembles CandidateReport
        |
7. Streamlit renders the report
```

**Total LLM calls per evaluation: 4**
- 1x resume parsing
- 1x JD parsing (if plain text)
- 1x achievement scoring
- 1x ownership scoring
- 1x question generation

**Local compute:** Semantic similarity runs entirely locally using the `all-MiniLM-L6-v2` model (~80MB). No API cost, deterministic results.

---

## 5. Data Models

All inter-module data is typed with Pydantic. Nothing is passed as raw dicts between modules.

```
ParsedResume
  name, email, phone, github_url, linkedin_url
  years_of_experience
  skills[], tools_and_technologies[]
  work_experience[]: WorkExperience
    company, title, duration_months
    responsibilities[], achievements[], technologies[]
  education[], projects[], certifications[]
  achievements[]  # standalone quantified achievements

JobDescription
  title, required_skills[], preferred_skills[]
  min_years_experience, responsibilities[]
  tools_and_technologies[], seniority_level

DimensionalScore
  score (0-100), explanation, evidence[]

MultiDimensionalScores
  exact_match, semantic_similarity, achievement, ownership
  overall

CandidateReport
  candidate_name, job_title, tier, tier_explanation
  scores: MultiDimensionalScores
  verification_results[]
  interview_questions[]
  overall_recommendation, red_flags[], strengths[]
```

---

## 6. Tech Stack Choices

| Component | Choice | Why |
|-----------|--------|-----|
| LLM | Llama 3.3 70B via Groq | Free tier, fast inference, strong instruction following |
| Embeddings | `all-MiniLM-L6-v2` | Small (80MB), fast, accurate enough for skill matching, runs locally |
| PDF parsing | `pdfplumber` | More reliable than PyPDF2 on complex layouts |
| Data validation | Pydantic v2 | Typed contracts between modules, automatic validation |
| UI | Streamlit | No frontend knowledge needed, fast to iterate |
| HTTP (GitHub) | `requests` | Simple, no overhead needed for a few API calls |

---

## 7. Scalability Plan

The current implementation is synchronous and single-process, which is fine for a demo. For production at 10,000+ resumes/day:

**Bottlenecks and fixes:**

| Bottleneck | Fix |
|------------|-----|
| Synchronous LLM calls | Async batching with `asyncio`; Groq supports parallel requests |
| Single process | Each `pipeline.evaluate()` is stateless, deploy N container replicas behind a load balancer |
| JD embeddings recomputed per call | Cache JD embeddings in Redis; they only change when the JD changes |
| GitHub rate limiting | Token pool (one token per worker) + exponential backoff |
| No persistence | Write CandidateReports to PostgreSQL; use pgvector for "find similar candidates" queries |
| Resume ingestion | SQS or Kafka queue; workers pull and evaluate asynchronously |

**Estimated throughput with simple horizontal scaling:**
- Each evaluation takes ~5-10 seconds (LLM latency)
- 10 workers = ~3600-7200 evaluations/hour
- 10,000/day = ~417/hour, so 2 workers is sufficient with async batching

---

## 8. Known Limitations

- **LinkedIn verification** is URL-format only. Real claim verification would need a partnership or manual review.
- **LLM non-determinism**: achievement and ownership scores can vary slightly between runs. This is acceptable for a screening tool but worth noting.
- **Embedding model bias**: `all-MiniLM-L6-v2` was trained on general English text. Domain-specific tech terms (niche frameworks, proprietary tools) may embed poorly.
- **Resume parsing failures**: Heavily formatted PDFs (tables, columns, logos) can confuse `pdfplumber`. A fallback OCR step (e.g. `pytesseract`) would help.