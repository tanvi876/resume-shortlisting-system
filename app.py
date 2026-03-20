"""
Streamlit UI for the Resume Shortlisting System.
Run with: streamlit run app.py
"""

import json
import streamlit as st
from src.pipeline import evaluate
from src.models import Tier

# ─── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Resume Shortlisting System",
    page_icon="🎯",
    layout="wide",
)

st.title("🎯 AI Resume Shortlisting & Interview Assistant")
st.markdown("Upload a resume and job description to get a full candidate evaluation.")

# ─── Sidebar: JD Input ────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Job Description")
    jd_input_mode = st.radio("Input mode", ["Paste text", "Load sample"])

    if jd_input_mode == "Load sample":
        try:
            with open("sample_data/sample_jd.json") as f:
                sample_jd = json.load(f)
            jd_text_input = json.dumps(sample_jd, indent=2)
            st.code(jd_text_input[:300] + "...", language="json")
        except FileNotFoundError:
            jd_text_input = ""
            st.warning("sample_data/sample_jd.json not found")
    else:
        jd_text_input = st.text_area(
            "Paste job description text",
            height=250,
            placeholder="We are looking for a Senior Backend Engineer with experience in...",
        )

    st.divider()
    skip_verification = st.checkbox(
        "Skip GitHub/LinkedIn verification",
        value=False,
        help="Faster for demos — disables external API calls",
    )

# ─── Main: Resume Input ───────────────────────────────────────────────────────
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Resume Input")
    resume_input_mode = st.radio("Mode", ["Paste text", "Upload PDF", "Load sample"])

    resume_text = None
    resume_pdf_path = None

    if resume_input_mode == "Paste text":
        resume_text = st.text_area("Paste resume text", height=350, placeholder="John Doe\njohn@example.com\n...")

    elif resume_input_mode == "Upload PDF":
        uploaded = st.file_uploader("Upload PDF", type=["pdf"])
        if uploaded:
            import tempfile, os
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(uploaded.getbuffer())
                resume_pdf_path = tmp.name

    elif resume_input_mode == "Load sample":
        try:
            with open("sample_data/sample_resume.txt") as f:
                resume_text = f.read()
            st.success("Sample resume loaded")
            with st.expander("Preview"):
                st.text(resume_text[:500] + "...")
        except FileNotFoundError:
            st.warning("sample_data/sample_resume.txt not found")

with col2:
    st.subheader("About the Scores")
    st.markdown("""
| Score | Weight | What it measures |
|-------|--------|-----------------|
| **Exact Match** | 30% | Verbatim keyword overlap with JD |
| **Semantic Similarity** | 30% | Embedding-based match (catches Kafka↔RabbitMQ) |
| **Achievement** | 25% | Quantified impact and measurable results |
| **Ownership** | 15% | Leadership, initiative, and accountability signals |

**Tier Thresholds:**
- 🟢 **Tier A** (≥72): Fast-track
- 🟡 **Tier B** (48–71): Technical Screen  
- 🔴 **Tier C** (<48): Needs Evaluation
    """)

# ─── Run Evaluation ───────────────────────────────────────────────────────────
st.divider()
run_btn = st.button("▶ Run Evaluation", type="primary", use_container_width=True)

if run_btn:
    has_resume = resume_text or resume_pdf_path
    has_jd = jd_text_input.strip()

    if not has_resume:
        st.error("Please provide a resume (paste text, upload PDF, or load sample)")
        st.stop()
    if not has_jd:
        st.error("Please provide a job description")
        st.stop()

    with st.spinner("Analyzing... (this takes ~20-40 seconds)"):
        try:
            # Handle JD: could be raw JSON (from sample) or plain text
            jd_dict = None
            try:
                jd_dict = json.loads(jd_text_input)
            except json.JSONDecodeError:
                pass  # treat as raw text

            report = evaluate(
                resume_text=resume_text,
                resume_pdf_path=resume_pdf_path,
                jd_text=jd_text_input if not jd_dict else None,
                jd_dict=jd_dict,
                skip_verification=skip_verification,
            )
        except Exception as e:
            st.error(f"Evaluation failed: {e}")
            st.exception(e)
            st.stop()

    # ─── Results ──────────────────────────────────────────────────────────────
    TIER_COLOR = {"A": "🟢", "B": "🟡", "C": "🔴"}
    tier_icon = TIER_COLOR.get(report.tier.value, "⚪")

    st.success("Evaluation complete!")

    # Header
    hdr_col1, hdr_col2, hdr_col3 = st.columns([2, 1, 1])
    with hdr_col1:
        st.markdown(f"### {report.candidate_name}")
        st.caption(f"Applying for: **{report.job_title}**")
    with hdr_col2:
        st.metric("Overall Score", f"{report.scores.overall}/100")
    with hdr_col3:
        st.metric("Tier", f"{tier_icon} Tier {report.tier.value}")

    st.info(report.overall_recommendation)

    # Tier explanation
    with st.expander("📊 Tier Rationale", expanded=True):
        st.write(report.tier_explanation)

    # Scores breakdown
    st.subheader("Score Breakdown")
    sc = report.scores
    score_cols = st.columns(4)
    dims = [
        ("Exact Match", sc.exact_match),
        ("Semantic Similarity", sc.semantic_similarity),
        ("Achievement", sc.achievement),
        ("Ownership", sc.ownership),
    ]
    for col, (label, dim) in zip(score_cols, dims):
        with col:
            st.metric(label, f"{dim.score:.0f}/100")
            st.progress(dim.score / 100)

    # Detailed score explanations
    st.subheader("Score Explanations")
    for label, dim in dims:
        with st.expander(f"**{label}** — {dim.score:.0f}/100"):
            st.write(dim.explanation)
            if dim.evidence:
                st.markdown("**Evidence:**")
                for e in dim.evidence:
                    st.markdown(f"- {e}")

    # Strengths & Red Flags
    str_col, flag_col = st.columns(2)
    with str_col:
        st.subheader("✅ Strengths")
        for s in report.strengths or ["No major strengths flagged"]:
            st.markdown(f"- {s}")
    with flag_col:
        st.subheader("⚠️ Red Flags")
        for f in report.red_flags or ["No major red flags"]:
            st.markdown(f"- {f}")

    # Verification Results
    if report.verification_results:
        st.subheader("🔍 Claim Verification")
        for vr in report.verification_results:
            status = "✅ Verified" if vr.verified else "❌ Unverified"
            with st.expander(f"{vr.platform} — {status}"):
                if vr.details:
                    st.json(vr.details)
                if vr.positive_signals:
                    st.markdown("**Positive Signals:**")
                    for p in vr.positive_signals:
                        st.markdown(f"- ✅ {p}")
                if vr.red_flags:
                    st.markdown("**Red Flags:**")
                    for r in vr.red_flags:
                        st.markdown(f"- ⚠️ {r}")

    # Interview Questions
    st.subheader("📝 Interview Questions")
    categories = list(dict.fromkeys(q.category for q in report.interview_questions))
    tabs = st.tabs(categories) if len(categories) > 1 else [st.container()]

    for tab, cat in zip(tabs, categories):
        with tab:
            cat_questions = [q for q in report.interview_questions if q.category == cat]
            for i, q in enumerate(cat_questions, 1):
                with st.expander(f"Q{i}: {q.question[:80]}..."):
                    st.markdown(f"**Question:** {q.question}")
                    st.caption(f"*Rationale: {q.rationale}*")
                    if q.follow_up:
                        st.markdown(f"**Follow-up:** {q.follow_up}")

    # Raw JSON export
    with st.expander("📦 Export Full Report (JSON)"):
        st.json(report.model_dump())
