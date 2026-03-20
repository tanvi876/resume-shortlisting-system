import json
import streamlit as st
from src.pipeline import evaluate

st.set_page_config(
    page_title="RecruitAI — Resume Shortlisting",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

h1, h2, h3 {
    font-family: 'Space Grotesk', sans-serif !important;
}

.hero-banner {
    background: linear-gradient(135deg, #1a1a3e 0%, #16213e 50%, #0f3460 100%);
    border: 1px solid rgba(124, 58, 237, 0.3);
    border-radius: 16px;
    padding: 2rem 2.5rem;
    margin-bottom: 2rem;
    position: relative;
    overflow: hidden;
}

.hero-banner::before {
    content: '';
    position: absolute;
    top: -50%;
    right: -10%;
    width: 400px;
    height: 400px;
    background: radial-gradient(circle, rgba(124,58,237,0.15) 0%, transparent 70%);
    pointer-events: none;
}

.hero-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 3.5rem;
    font-weight: 700;
    color: #fff;
    margin: 0 0 0.5rem 0;
    letter-spacing: -0.5px;
}

.hero-subtitle {
    color: #94a3b8;
    font-size: 1rem;
    margin: 0;
    font-weight: 400;
}

.hero-badge {
    display: inline-block;
    background: rgba(124,58,237,0.2);
    border: 1px solid rgba(124,58,237,0.5);
    color: #a78bfa;
    padding: 0.2rem 0.8rem;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.05em;
    margin-bottom: 1rem;
    text-transform: uppercase;
}

.tier-badge {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.4rem;
    font-weight: 700;
    padding: 0.5rem 1.5rem;
    border-radius: 10px;
    display: inline-block;
    letter-spacing: 0.05em;
}

.tier-A {
    background: linear-gradient(135deg, #052e16, #14532d);
    color: #4ade80;
    border: 1px solid #16a34a;
}

.tier-B {
    background: linear-gradient(135deg, #2d1d00, #3d2e00);
    color: #fbbf24;
    border: 1px solid #d97706;
}

.tier-C {
    background: linear-gradient(135deg, #2d0f0f, #3d1515);
    color: #f87171;
    border: 1px solid #dc2626;
}

.score-card {
    background: linear-gradient(135deg, #1a1a2e, #16213e);
    border: 1px solid rgba(124,58,237,0.2);
    border-radius: 12px;
    padding: 1.2rem;
    text-align: center;
    transition: border-color 0.2s;
}

.section-header {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.1rem;
    font-weight: 600;
    color: #e2e8f0;
    border-left: 3px solid #7c3aed;
    padding-left: 0.75rem;
    margin: 1.5rem 0 1rem 0;
}

.strength-item {
    background: rgba(5, 46, 22, 0.4);
    border: 1px solid rgba(22, 163, 74, 0.3);
    border-radius: 8px;
    padding: 0.6rem 1rem;
    margin: 0.4rem 0;
    color: #86efac;
    font-size: 0.9rem;
}

.flag-item {
    background: rgba(45, 15, 15, 0.4);
    border: 1px solid rgba(220, 38, 38, 0.3);
    border-radius: 8px;
    padding: 0.6rem 1rem;
    margin: 0.4rem 0;
    color: #fca5a5;
    font-size: 0.9rem;
}

.question-card {
    background: linear-gradient(135deg, #1a1a2e, #1e1e3f);
    border: 1px solid rgba(124,58,237,0.15);
    border-radius: 10px;
    padding: 1rem 1.2rem;
    margin: 0.6rem 0;
}

.category-pill {
    display: inline-block;
    padding: 0.15rem 0.6rem;
    border-radius: 20px;
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 0.5rem;
}

.pill-Technical { background: rgba(59,130,246,0.2); color: #93c5fd; border: 1px solid rgba(59,130,246,0.3); }
.pill-Behavioral { background: rgba(16,185,129,0.2); color: #6ee7b7; border: 1px solid rgba(16,185,129,0.3); }
.pill-Gap-Probing { background: rgba(245,158,11,0.2); color: #fcd34d; border: 1px solid rgba(245,158,11,0.3); }
.pill-Architecture { background: rgba(139,92,246,0.2); color: #c4b5fd; border: 1px solid rgba(139,92,246,0.3); }

div[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f0f1a 0%, #13131f 100%);
    border-right: 1px solid rgba(124,58,237,0.15);
}

.stButton > button {
    background: linear-gradient(135deg, #7c3aed, #6d28d9) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-weight: 600 !important;
    font-size: 1rem !important;
    padding: 0.6rem 1rem !important;
    transition: opacity 0.2s !important;
}

.stButton > button:hover {
    opacity: 0.9 !important;
}
</style>
""", unsafe_allow_html=True)

# ── Hero Banner ───────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-banner">
    <div class="hero-badge">🤖 AI-Powered · Powered by Groq + Sentence Transformers</div>
    <div class="hero-title">🎯 RecruitAI : Resume Shortlisting System</div>
    <p class="hero-subtitle">
        Multi-dimensional candidate evaluation using semantic similarity, LLM scoring, and automated interview question generation.
    </p>
</div>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📋 Job Description")
    jd_input = st.text_area(
        "Paste JD text or JSON",
        height=280,
        placeholder='{"title": "Senior Backend Engineer", "required_skills": ["Python", "Kafka"]...}\n\nor just paste plain text JD',
        label_visibility="collapsed",
    )
    st.divider()
    st.markdown("### ⚙️ Options")
    skip_verification = st.checkbox("Skip GitHub verification", value=True,
        help="Uncheck to run live GitHub API checks")
    st.divider()
    st.markdown("""
<div style='font-size:0.8rem; color:#64748b; line-height:1.6'>
<b style='color:#94a3b8'>Scoring Weights</b><br>
Exact Match — 30%<br>
Semantic Similarity — 30%<br>
Achievement — 25%<br>
Ownership — 15%
</div>
""", unsafe_allow_html=True)

# ── Resume Input ──────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">Resume Input</div>', unsafe_allow_html=True)
mode = st.radio("Mode", ["Paste text", "Upload PDF"], horizontal=True, label_visibility="collapsed")

resume_text, resume_pdf = None, None
if mode == "Paste text":
    resume_text = st.text_area(
        "Resume",
        height=280,
        placeholder="Paste resume text here...\n\nName, contact, experience, skills, education...",
        label_visibility="collapsed",
    )
else:
    uploaded = st.file_uploader("Upload PDF resume", type=["pdf"])
    if uploaded:
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(uploaded.getbuffer())
            resume_pdf = tmp.name
        st.success(f"✓ {uploaded.name} uploaded")

st.markdown("<br>", unsafe_allow_html=True)

col_info1, col_info2, col_info3 = st.columns(3)
with col_info1:
    st.markdown("""<div class="score-card">
        <div style='font-size:1.5rem'>🔍</div>
        <div style='font-weight:600; font-size:0.85rem; margin-top:0.3rem'>Exact Match</div>
        <div style='color:#64748b; font-size:0.75rem'>Keyword overlap</div>
    </div>""", unsafe_allow_html=True)
with col_info2:
    st.markdown("""<div class="score-card">
        <div style='font-size:1.5rem'>🧠</div>
        <div style='font-weight:600; font-size:0.85rem; margin-top:0.3rem'>Semantic Match</div>
        <div style='color:#64748b; font-size:0.75rem'>Kafka ↔ RabbitMQ</div>
    </div>""", unsafe_allow_html=True)
with col_info3:
    st.markdown("""<div class="score-card">
        <div style='font-size:1.5rem'>🏆</div>
        <div style='font-weight:600; font-size:0.85rem; margin-top:0.3rem'>Impact + Ownership</div>
        <div style='color:#64748b; font-size:0.75rem'>LLM-judged signals</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

run = st.button("▶ Run Evaluation", type="primary", use_container_width=True)

if run:
    if not (resume_text or resume_pdf):
        st.error("Please provide a resume")
        st.stop()
    if not jd_input.strip():
        st.error("Please paste a job description in the sidebar")
        st.stop()

    with st.spinner("Analyzing candidate profile..."):
        try:
            jd_dict = None
            try:
                jd_dict = json.loads(jd_input)
            except json.JSONDecodeError:
                pass
            report = evaluate(
                resume_text=resume_text,
                resume_pdf_path=resume_pdf,
                jd_text=jd_input if not jd_dict else None,
                jd_dict=jd_dict,
                skip_verification=skip_verification,
            )
        except Exception as e:
            error_msg = str(e).lower()
            if "rate limit" in error_msg or "429" in error_msg:
                st.error("⚠️ API rate limit hit. Please wait a moment and try again.")
            elif "invalid api key" in error_msg or "401" in error_msg:
                st.error("⚠️ API key issue. Please check your GROQ_API_KEY.")
            elif "validation" in error_msg:
                st.error("⚠️ Could not process this resume. Try pasting the text directly instead of uploading the PDF.")
            elif "json" in error_msg:
                st.error("⚠️ Could not parse the resume. Please check the format and try again.")
            else:
                st.error("⚠️ Something went wrong. Please try again.")
            with st.expander("Advanced: "):
                st.exception(e)
            st.stop() 
    st.markdown("---")

    # ── Result Header ─────────────────────────────────────────────────────────
    r1, r2, r3, r4 = st.columns([3, 1, 1, 1])
    with r1:
        st.markdown(f"""
        <div style='padding: 0.5rem 0'>
            <div style='font-family: Space Grotesk; font-size: 1.6rem; font-weight: 700; color: #f1f5f9'>{report.candidate_name}</div>
            <div style='color: #94a3b8; font-size: 0.9rem; margin-top: 0.2rem'>Applying for: <b style="color:#c4b5fd">{report.job_title}</b></div>
        </div>
        """, unsafe_allow_html=True)
    with r2:
        st.metric("Overall", f"{report.scores.overall}/100")
    with r3:
        tier_class = {"A": "tier-A", "B": "tier-B", "C": "tier-C"}[report.tier.value]
        tier_label = {"A": "🟢 Tier A", "B": "🟡 Tier B", "C": "🔴 Tier C"}[report.tier.value]
        st.markdown(f'<div class="tier-badge {tier_class}">{tier_label}</div>', unsafe_allow_html=True)
    with r4:
        tier_action = {"A": "Fast-track", "B": "Tech Screen", "C": "Calibrate"}
        st.markdown(f"""<div style='background:rgba(124,58,237,0.1); border:1px solid rgba(124,58,237,0.3);
            border-radius:8px; padding:0.5rem 0.8rem; font-size:0.85rem; color:#c4b5fd; font-weight:600'>
            {tier_action[report.tier.value]}</div>""", unsafe_allow_html=True)

    st.info(report.overall_recommendation)

    with st.expander("📊 Tier Rationale"):
        st.write(report.tier_explanation)

    # ── Score Breakdown ───────────────────────────────────────────────────────
    st.markdown('<div class="section-header">Score Breakdown</div>', unsafe_allow_html=True)
    s1, s2, s3, s4 = st.columns(4)
    for col, (label, dim, icon) in zip([s1, s2, s3, s4], [
        ("Exact Match", report.scores.exact_match, "🎯"),
        ("Semantic Sim", report.scores.semantic_similarity, "🧠"),
        ("Achievement", report.scores.achievement, "🏆"),
        ("Ownership", report.scores.ownership, "👑"),
    ]):
        color = "#4ade80" if dim.score >= 70 else "#fbbf24" if dim.score >= 45 else "#f87171"
        with col:
            st.markdown(f"""<div class="score-card">
                <div style='font-size:1.3rem'>{icon}</div>
                <div style='font-size:1.8rem; font-weight:700; color:{color}; font-family:Space Grotesk'>{dim.score:.0f}</div>
                <div style='font-size:0.75rem; color:#94a3b8'>{label}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    for label, dim in [
        ("🎯 Exact Match", report.scores.exact_match),
        ("🧠 Semantic Similarity", report.scores.semantic_similarity),
        ("🏆 Achievement", report.scores.achievement),
        ("👑 Ownership", report.scores.ownership),
    ]:
        with st.expander(f"{label} — {dim.score:.0f}/100"):
            st.write(dim.explanation)
            if dim.evidence:
                for e in dim.evidence:
                    st.markdown(f"- {e}")

    # ── Strengths & Red Flags ─────────────────────────────────────────────────
    st.markdown('<div class="section-header">Candidate Summary</div>', unsafe_allow_html=True)
    sc, fc = st.columns(2)
    with sc:
        st.markdown("**✅ Strengths**")
        for s in (report.strengths or ["None flagged"]):
            st.markdown(f'<div class="strength-item">✓ {s}</div>', unsafe_allow_html=True)
    with fc:
        st.markdown("**⚠️ Red Flags**")
        for f in (report.red_flags or ["None flagged"]):
            st.markdown(f'<div class="flag-item">⚠ {f}</div>', unsafe_allow_html=True)

    # ── Verification ──────────────────────────────────────────────────────────
    if report.verification_results:
        st.markdown('<div class="section-header">Claim Verification</div>', unsafe_allow_html=True)
        for vr in report.verification_results:
            with st.expander(f"{vr.platform} — {'✅ Verified' if vr.verified else '❌ Unverified'}"):
                if vr.details:
                    st.json(vr.details)
                for p in vr.positive_signals:
                    st.markdown(f"- ✅ {p}")
                for r in vr.red_flags:
                    st.markdown(f"- ⚠️ {r}")

    # ── Interview Questions ───────────────────────────────────────────────────
    st.markdown('<div class="section-header">Interview Questions</div>', unsafe_allow_html=True)
    for i, q in enumerate(report.interview_questions, 1):
        pill_class = f"pill-{q.category.replace(' ', '-')}"
        with st.expander(f"Q{i} — {q.question[:75]}..."):
            st.markdown(f'<span class="category-pill {pill_class}">{q.category}</span>', unsafe_allow_html=True)
            st.markdown(f"**{q.question}**")
            st.caption(f"💡 {q.rationale}")
            if q.follow_up:
                st.markdown(f"*Follow-up: {q.follow_up}*")

    # ── JSON Export ───────────────────────────────────────────────────────────
    with st.expander("📦 Export Full Report (JSON)"):
        st.json(report.model_dump())