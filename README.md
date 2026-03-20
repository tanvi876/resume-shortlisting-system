# AI Resume Shortlisting & Interview Assistant

An end-to-end system that automates candidate evaluation by comparing resumes against Job Descriptions, verifying public claims, and generating tailored interview question sets.

## Demo
```bash
pip install -r requirements.txt
cp .env.example .env  # add your ANTHROPIC_API_KEY
streamlit run app.py
```

## Architecture
```
                    ┌──────────────────────────────────────────┐
                    │               pipeline.py                │
                    │         (Single Orchestration Layer)     │
                    └──┬──────────┬──────────┬────────────────┘
                       │          │          │
             ┌─────────▼──┐  ┌───▼────┐  ┌──▼──────────────┐
             │  Resume    │  │Scoring │  │  Verification   │
             │  Parser    │  │Engine  │  │  Engine         │
             └─────────┬──┘  └───┬────┘  └──┬──────────────┘
                       │         │           │
                    ┌──▼─────────▼───────────▼──┐
                    │      Question Generator    │
                    │   (Tier → Questions)       │
                    └────────────────────────────┘
```

### Components

| Module | Responsibility |
|--------|---------------|
| `resume_parser.py` | PDF → text → LLM call → structured `ParsedResume` |
| `scoring_engine.py` | 4-dimensional scoring with embeddings + LLM |
| `verification_engine.py` | GitHub REST API checks |
| `question_generator.py` | Tier classification + tailored question generation |
| `pipeline.py` | Orchestrates all of the above |
| `app.py` | Streamlit UI |

## Scoring Model

| Dimension | Weight | Method |
|-----------|--------|--------|
| Exact Match | 30% | Case-insensitive keyword intersection |
| Semantic Similarity | 30% | `all-MiniLM-L6-v2` cosine similarity matrix |
| Achievement | 25% | LLM evaluation of quantified impact claims |
| Ownership | 15% | LLM analysis of leadership/initiative language |

### Why Semantic Similarity catches Kafka ↔ RabbitMQ

Both terms embed in the same region of the vector space (message queuing concepts). When we compute the cosine similarity matrix between JD terms and resume terms, a candidate with RabbitMQ experience scores ~0.72 similarity against a Kafka requirement — surfaced in the explanation with an evidence string like `'Kafka' ↔ 'RabbitMQ' (sim=0.72)`.

### Tier Classification

| Tier | Score | Action |
|------|-------|--------|
| A | ≥72 | Fast-track |
| B | 48–71 | Technical Screen |
| C | <48 | Calibration call |

## Scalability (Design Notes)

For 10,000+ resumes/day:

1. **Async processing**: Replace synchronous LLM calls with async batching using `asyncio` + Anthropic's batch API
2. **Queue-based ingestion**: Push resumes to SQS/Kafka; worker pool pulls and evaluates
3. **Embedding caching**: JD embeddings are computed once per JD and cached in Redis (they don't change)
4. **Rate limiting**: GitHub verification is the bottleneck (60 req/hr unauthenticated); use token pool + exponential backoff
5. **Storage**: Write reports to PostgreSQL; use Pinecone or pgvector for similarity search across all evaluated candidates
6. **Horizontal scaling**: Each pipeline.evaluate() call is stateless — deploy as container replicas behind a load balancer

## Running Tests
```bash
# Unit tests only (no API key required)
python -m pytest tests/ -v -m "not integration"

# Integration tests (requires ANTHROPIC_API_KEY)
python -m pytest tests/ -v
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Claude API key |
| `GITHUB_TOKEN` | No | Increases GitHub rate limit from 60 to 5000 req/hr |

## AI Usage Disclosure

**What I used AI for:**
- Brainstorming the four scoring dimensions and their weights
- Drafting initial prompt templates for the achievement and ownership scorers
- Debugging a JSON parsing edge case where the model occasionally wrapped output in markdown fences

**What I reviewed and changed manually:**
- All prompt templates were iterated on manually — the initial ownership prompt generated generic outputs; I added the explicit instruction to cite specific language from the resume, which dramatically improved explainability
- The semantic similarity approach was designed independently — I chose `sentence-transformers` over asking the LLM to rate similarity because it's deterministic, fast, and doesn't incur extra API costs per comparison
- The tier thresholds (72/48) were set after testing against 5 sample resumes

**One example where I disagreed with the AI's suggestion:**
The AI suggested using LangChain's structured output parser for the JSON extraction layer. I chose to write the extraction logic manually (with a regex fence-stripper and `json.loads`) because LangChain adds significant dependency weight and the extraction logic is simple enough that the abstraction doesn't pay for itself here.