"""
app.py
──────
Streamlit front-end for the Gen AI Content Transformation platform.
Cyber-defense dark UI with neon/cyan accents.
"""

from __future__ import annotations

import datetime
import json
import os
import tempfile
from typing import Any

import streamlit as st

from core_engine import (
    MasterContext,
    AdvisoryArtifact,
    ExecSummaryArtifact,
    SlidesArtifact,
    VideoStoryboardArtifact,
    SocialPostsArtifact,
    extract_text,
    extract_master_context,
    transform_artifact,
    overall_grounding,
)
from file_exporters import generate_pptx, generate_advisory_pdf, generate_srt

# ═══════════════════════════════════════════════════════════════════════
# PAGE  CONFIG  &  CSS
# ═══════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="CyberTransform · Gen AI Platform",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

_CSS = """
<style>
/* ── Global dark theme ─────────────────────────────────────────── */
html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
    background-color: #0B0F17 !important;
    color: #E2E8F0;
}
[data-testid="stSidebar"] {
    background-color: #111827 !important;
    border-right: 1px solid #1E293B;
}
[data-testid="stHeader"] {
    background-color: #0B0F17 !important;
}

/* ── Cards ─────────────────────────────────────────────────────── */
.cyber-card {
    background: #111827;
    border: 1px solid #1E293B;
    border-radius: 12px;
    padding: 1.2rem 1.5rem;
    margin-bottom: 1rem;
}
.cyber-card h3 {
    color: #06B6D4;
    margin-top: 0;
}

/* ── Accent elements ───────────────────────────────────────────── */
.badge-airgap {
    display: inline-block;
    background: #065F46;
    color: #34D399;
    padding: 3px 10px;
    border-radius: 6px;
    font-size: 0.8rem;
    font-weight: 600;
    letter-spacing: 0.5px;
}
.badge-score {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 6px;
    font-size: 0.8rem;
    font-weight: 600;
    letter-spacing: 0.5px;
}
.score-high   { background: #065F46; color: #34D399; }
.score-med    { background: #78350F; color: #FBBF24; }
.score-low    { background: #7F1D1D; color: #FCA5A5; }

/* ── Tabs & Buttons ────────────────────────────────────────────── */
button[data-baseweb="tab"] {
    color: #94A3B8 !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: #06B6D4 !important;
    border-bottom: 2px solid #06B6D4 !important;
}
.stDownloadButton > button {
    background-color: #06B6D4 !important;
    color: #0B0F17 !important;
    font-weight: 600;
    border: none;
    border-radius: 8px;
}
.stDownloadButton > button:hover {
    background-color: #22D3EE !important;
}

/* ── Inputs ────────────────────────────────────────────────────── */
[data-testid="stTextArea"] textarea,
[data-testid="stFileUploader"],
.stSelectbox > div > div {
    background-color: #1E293B !important;
    color: #E2E8F0 !important;
    border-color: #334155 !important;
}

/* ── Checkbox ──────────────────────────────────────────────────── */
.stCheckbox label span {
    color: #CBD5E1 !important;
}

/* ── Telemetry header ──────────────────────────────────────────── */
.telemetry-bar {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 0.7rem 1.2rem;
    background: linear-gradient(90deg, #111827 0%, #0B0F17 100%);
    border: 1px solid #1E293B;
    border-radius: 10px;
    margin-bottom: 1.2rem;
}
</style>
"""
st.markdown(_CSS, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("## 🛡️ CyberTransform")
    st.caption("Gen AI Platform for Automated Content Transformation")
    st.markdown("---")

    # ── File upload ────────────────────────────────────────────────
    uploaded = st.file_uploader(
        "Upload source document",
        type=["pdf", "docx", "txt"],
        help="Upload a threat report, advisory, or intelligence brief.",
    )
    raw_text_input = st.text_area(
        "…or paste raw text",
        height=130,
        placeholder="Paste threat intel text here as a fallback…",
    )

    st.markdown("---")

    # ── Parameters ─────────────────────────────────────────────────
    audience = st.selectbox("Target Audience", ["Executive", "Analyst", "Public"])
    tone = st.selectbox("Tone", ["Urgent", "Authoritative", "Neutral"])

    st.markdown("---")
    st.markdown("**Select output artifacts**")
    chk_advisory   = st.checkbox("📋 Advisory", value=True)
    chk_exec       = st.checkbox("📊 Exec Summary", value=True)
    chk_ppt        = st.checkbox("📑 PPT Deck", value=True)
    chk_video      = st.checkbox("🎬 Video Storyboard", value=False)
    chk_social     = st.checkbox("📱 Social Posts", value=False)

    st.markdown("---")
    transform_btn = st.button("⚡  Transform", use_container_width=True, type="primary")


# ═══════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════

def _score_class(score: float) -> str:
    if score >= 80:
        return "score-high"
    if score >= 50:
        return "score-med"
    return "score-low"


def _render_telemetry(score: float | None) -> None:
    """Render the operational telemetry header bar."""
    score_html = ""
    if score is not None:
        cls = _score_class(score)
        score_html = (
            f'<span class="badge-score {cls}">Grounding Score: {score:.1f}%</span>'
        )
    airgap_html = '<span style="display:inline-block;background:#065F46;color:#34D399;padding:3px 10px;border-radius:6px;font-size:0.8rem;font-weight:600;letter-spacing:0.5px;">&#128274; Air-Gap Ready</span>'
    st.markdown(
        f'<div class="telemetry-bar">'
        f'<span style="color:#06B6D4;font-weight:700;font-size:1.05rem;">&#9670; Operational Telemetry</span>'
        f'{score_html}'
        f'{airgap_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


def _artifact_to_text(artifact: Any) -> str:
    """Serialise any Pydantic artifact to readable text for grounding check."""
    if hasattr(artifact, "model_dump_json"):
        return artifact.model_dump_json()
    return str(artifact)


# ═══════════════════════════════════════════════════════════════════════
# MAIN  AREA
# ═══════════════════════════════════════════════════════════════════════

st.markdown(
    "<h1 style='color:#06B6D4;margin-bottom:0'>🛡️ CyberTransform</h1>"
    "<p style='color:#94A3B8;margin-top:4px'>"
    "Gen AI Platform for Automated Content Transformation &nbsp;·&nbsp; SIH PS 26154"
    "</p>",
    unsafe_allow_html=True,
)

# Render telemetry bar (score will be None until transformation runs)
grounding_score: float | None = st.session_state.get("grounding_score")
_render_telemetry(grounding_score)

# ── Transformation logic ──────────────────────────────────────────────
if transform_btn:
    # 1. Obtain source text
    source_text = ""
    if uploaded is not None:
        with st.spinner("📄 Extracting text from uploaded file…"):
            source_text = extract_text(uploaded.read(), uploaded.name)
    elif raw_text_input.strip():
        source_text = raw_text_input.strip()
    else:
        st.warning("Please upload a file or paste text before transforming.")
        st.stop()

    if len(source_text) < 20:
        st.warning("Source text is too short for meaningful transformation.")
        st.stop()

    # 2. Build master context
    with st.spinner("🧠 Building master context via LLM…"):
        try:
            master = extract_master_context(source_text)
        except RuntimeError as e:
            st.error(str(e))
            st.stop()
        except Exception as e:
            st.error(f"Master context extraction failed: {e}")
            st.stop()

    st.session_state["master"] = master
    st.session_state["source_text"] = source_text

    # 3. Selected artifact types
    selected: list[str] = []
    if chk_advisory:
        selected.append("Advisory")
    if chk_exec:
        selected.append("Exec Summary")
    if chk_ppt:
        selected.append("PPT Deck")
    if chk_video:
        selected.append("Video Storyboard")
    if chk_social:
        selected.append("Social Posts")

    if not selected:
        st.warning("Select at least one output artifact.")
        st.stop()

    # 4. Generate each artifact
    artifacts: dict[str, Any] = {}
    combined_gen_text = ""
    for art_type in selected:
        with st.spinner(f"🔄 Generating {art_type}…"):
            try:
                art = transform_artifact(master, art_type, audience, tone)
                artifacts[art_type] = art
                combined_gen_text += _artifact_to_text(art) + "\n"
            except Exception as e:
                st.error(f"Failed to generate {art_type}: {e}")

    st.session_state["artifacts"] = artifacts

    # 5. Compute grounding score
    score = overall_grounding(source_text, combined_gen_text)
    st.session_state["grounding_score"] = score

    st.rerun()

# ── Display results ───────────────────────────────────────────────────
artifacts: dict[str, Any] = st.session_state.get("artifacts", {})
source_text: str = st.session_state.get("source_text", "")

if artifacts:
    tab_names = list(artifacts.keys())
    tabs = st.tabs(tab_names)

    for tab, art_name in zip(tabs, tab_names):
        art = artifacts[art_name]
        with tab:
            st.markdown(f"<div class='cyber-card'><h3>{art_name}</h3>", unsafe_allow_html=True)

            # ── Advisory ───────────────────────────────────────────
            if art_name == "Advisory" and isinstance(art, AdvisoryArtifact):
                st.markdown(f"**Severity:** `{art.severity}`")
                st.markdown(f"**Summary:** {art.summary}")
                if art.iocs:
                    st.markdown("**IOCs:**")
                    for ioc in art.iocs:
                        st.code(ioc, language="text")
                if art.actions:
                    st.markdown("**Recommended Actions:**")
                    for i, a in enumerate(art.actions, 1):
                        st.markdown(f"{i}. {a}")

                # Download PDF
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                    tmp_path = tmp.name
                pdf_data = art.model_dump()
                pdf_data.setdefault("date", datetime.date.today().isoformat())
                generate_advisory_pdf(pdf_data, tmp_path)
                with open(tmp_path, "rb") as f:
                    st.download_button(
                        "📥 Download Advisory PDF",
                        data=f.read(),
                        file_name="advisory.pdf",
                        mime="application/pdf",
                    )

            # ── Exec Summary ───────────────────────────────────────
            elif art_name == "Exec Summary" and isinstance(art, ExecSummaryArtifact):
                st.markdown(f"**Title:** {art.title}")
                st.markdown(f"**Audience:** {art.audience}")
                st.markdown(art.summary)
                if art.key_findings:
                    st.markdown("**Key Findings:**")
                    for kf in art.key_findings:
                        st.markdown(f"- {kf}")
                if art.business_impact:
                    st.markdown(f"**Business Impact:** {art.business_impact}")
                if art.recommended_actions:
                    st.markdown("**Recommended Actions:**")
                    for i, a in enumerate(art.recommended_actions, 1):
                        st.markdown(f"{i}. {a}")

            # ── PPT Deck ───────────────────────────────────────────
            elif art_name == "PPT Deck" and isinstance(art, SlidesArtifact):
                for s in art.slides:
                    st.markdown(f"**{s.title}**")
                    for bp in s.bullet_points:
                        st.markdown(f"  - {bp}")
                    if s.speaker_notes:
                        st.caption(f"🗒️ Notes: {s.speaker_notes}")

                # Download PPTX
                slides_data = [s.model_dump() for s in art.slides]
                with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as tmp:
                    tmp_path = tmp.name
                generate_pptx(slides_data, tmp_path)
                with open(tmp_path, "rb") as f:
                    st.download_button(
                        "📥 Download PPTX",
                        data=f.read(),
                        file_name="cybertransform_deck.pptx",
                        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    )

            # ── Video Storyboard ───────────────────────────────────
            elif art_name == "Video Storyboard" and isinstance(art, VideoStoryboardArtifact):
                st.markdown(f"**Title:** {art.title}")
                for sc in art.scenes:
                    st.markdown(
                        f"**Scene {sc.scene_number}** ({sc.duration_seconds}s)\n\n"
                        f"🎥 *{sc.visual_description}*\n\n"
                        f"🎙️ {sc.narration}"
                    )
                    st.markdown("---")

                # Download SRT
                srt_data: list[dict] = []
                t = 0.0
                for sc in art.scenes:
                    srt_data.append(
                        {"start": t, "end": t + sc.duration_seconds, "text": sc.narration}
                    )
                    t += sc.duration_seconds
                with tempfile.NamedTemporaryFile(suffix=".srt", delete=False) as tmp:
                    tmp_path = tmp.name
                generate_srt(srt_data, tmp_path)
                with open(tmp_path, "rb") as f:
                    st.download_button(
                        "📥 Download SRT",
                        data=f.read(),
                        file_name="storyboard.srt",
                        mime="text/plain",
                    )

            # ── Social Posts ───────────────────────────────────────
            elif art_name == "Social Posts" and isinstance(art, SocialPostsArtifact):
                for post in art.posts:
                    st.markdown(
                        f"**{post.platform}**\n\n"
                        f"{post.content}\n\n"
                        f"*{' '.join('#' + h for h in post.hashtags)}*"
                    )
                    st.markdown("---")

            st.markdown("</div>", unsafe_allow_html=True)

elif not transform_btn:
    # Landing state
    st.markdown(
        """
        <div class="cyber-card">
        <h3>Getting Started</h3>
        <ol style="color:#CBD5E1">
            <li>Upload a threat report (<code>.pdf</code>, <code>.docx</code>, <code>.txt</code>) or paste text in the sidebar.</li>
            <li>Choose <b>Audience</b>, <b>Tone</b>, and desired output formats.</li>
            <li>Click <b>⚡ Transform</b> to generate intelligence artifacts.</li>
        </ol>
        <p style="color:#64748B;font-size:0.85rem">
            Requires <code>OPENAI_API_KEY</code> or <code>ANTHROPIC_API_KEY</code> in a <code>.env</code> file.
        </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
