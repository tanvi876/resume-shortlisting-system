import json
import streamlit as st
from src.pipeline import evaluate

st.set_page_config(page_title="Resume Shortlisting System", page_icon="🎯", layout="wide")

st.markdown("""
<style>
.tier-badge { font-size:1.8rem; font-weight:bold; padding:0.4rem 1.2rem; border-radius:8px; display:inline-block; }
.tier-A { background:#1a4731; color:#4ade80; }
.tier-B { background:#3d2e00; color:#fbbf24; }
.tier-C { background:#3d0f0f; color:#f87171; }
</style>
""", unsafe_allow_html=True)

st.title("🎯 AI Resume Shortlisting & Interview Assistant")
st.caption("Upload a resume and job description to get a full candidate evaluation.")

with st.sidebar:
    st.header("Job Description")
    jd_input = st.text_area("Paste job description text", height=250,
        placeholder="We are looking for a Senior Backend Engineer...")
    st.divider()
    skip_verification = st.checkbox("Skip GitHub/LinkedIn verification", value=True)

st.subheader("Resume Input")
mode = st.radio("Mode", ["Paste text", "Upload PDF"], horizontal=True)

resume_text, resume_pdf = None, None
if mode == "Paste text":
    resume_text = st.text_area("Paste resume text", height=300,
        placeholder="John Doe\njohn@example.com\n...")
else:
    uploaded = st.file_uploader("Upload PDF", type=["pdf"])
    if uploaded:
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(uploaded.getbuffer())
            resume_pdf = tmp.name

st.divider()

with st.expander("ℹ️ How scoring works"):
    st.markdown("""
| Dimension | Weight | Method |
|-----------|--------|--------|
| **Exact Match** | 30% | Verbatim keyword overlap |
| **Semantic Similarity** | 30% | Embeddings — catches Kafka↔RabbitMQ |
| **Achievement** | 25% | LLM-judged quantified impact |
| **Ownership** | 15% | LLM-judged leadership signals |

🟢 **Tier A** ≥72 · 🟡 **Tier B** 48–71 · 🔴 **Tier C** <48
""")

if st.button("▶ Run Evaluation", type="primary", use_container_width=True):
    if not (resume_text or resume_pdf):
        st.error("Please provide a resume")
        st.stop()
    if not jd_input.strip():
        st.error("Please provide a job description in the sidebar")
        st.stop()

    with st.spinner("Analyzing candidate... (~30 seconds)"):
        try:
            jd_dict = None
            try:
                jd_dict = json.loads(jd_input)
            except json.JSONDecodeError:
                pass
            report = evaluate(
                resume_text=resume_text, resume_pdf_path=resume_pdf,
                jd_text=jd_input if not jd_dict else None, jd_dict=jd_dict,
                skip_verification=skip_verification,
            )
        except Exception as e:
            st.error(f"Error: {e}")
            st.exception(e)
            st.stop()

    st.success("Evaluation complete!")

    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        st.markdown(f"### {report.candidate_name}")
        st.caption(f"Role: **{report.job_title}**")
    with c2:
        st.metric("Overall Score", f"{report.scores.overall}/100")
    with c3:
        tier_class = {"A": "tier-A", "B": "tier-B", "C": "tier-C"}[report.tier.value]
        st.markdown(f'<div class="tier-badge {tier_class}">Tier {report.tier.value}</div>',
            unsafe_allow_html=True)

    st.info(report.overall_recommendation)

    with st.expander("📊 Tier Rationale", expanded=True):
        st.write(report.tier_explanation)

    st.subheader("Score Breakdown")
    cols = st.columns(4)
    for col, (label, dim) in zip(cols, [
        ("Exact Match", report.scores.exact_match),
        ("Semantic Sim", report.scores.semantic_similarity),
        ("Achievement", report.scores.achievement),
        ("Ownership", report.scores.ownership),
    ]):
        with col:
            st.metric(label, f"{dim.score:.0f}/100")
            st.progress(dim.score / 100)

    st.subheader("Score Explanations")
    for label, dim in [
        ("Exact Match", report.scores.exact_match),
        ("Semantic Similarity", report.scores.semantic_similarity),
        ("Achievement", report.scores.achievement),
        ("Ownership", report.scores.ownership),
    ]:
        with st.expander(f"{label} — {dim.score:.0f}/100"):
            st.write(dim.explanation)
            if dim.evidence:
                for e in dim.evidence:
                    st.markdown(f"- {e}")

    sc, fc = st.columns(2)
    with sc:
        st.subheader("✅ Strengths")
        for s in (report.strengths or ["None flagged"]):
            st.markdown(f"- {s}")
    with fc:
        st.subheader("⚠️ Red Flags")
        for f in (report.red_flags or ["None flagged"]):
            st.markdown(f"- {f}")

    if report.verification_results:
        st.subheader("🔍 Verification")
        for vr in report.verification_results:
            with st.expander(f"{vr.platform} — {'✅' if vr.verified else '❌'}"):
                if vr.details:
                    st.json(vr.details)
                for p in vr.positive_signals:
                    st.markdown(f"- ✅ {p}")
                for r in vr.red_flags:
                    st.markdown(f"- ⚠️ {r}")

    st.subheader("📝 Interview Questions")
    for i, q in enumerate(report.interview_questions, 1):
        with st.expander(f"Q{i} [{q.category}]: {q.question[:80]}..."):
            st.markdown(f"**{q.question}**")
            st.caption(f"Rationale: {q.rationale}")
            if q.follow_up:
                st.markdown(f"*Follow-up: {q.follow_up}*")

    with st.expander("📦 Full JSON Report"):
        st.json(report.model_dump())