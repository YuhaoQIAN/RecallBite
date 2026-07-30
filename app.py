"""RecallBite knowledge activation workspace."""

from __future__ import annotations

import html
import re
from datetime import datetime

import streamlit as st

from src.activation import generate_activation_output, generate_apply_suggestion
from src.activation_unit import load_units, list_active_units, activate_unit, delete_unit
from src.depth_router import route_depth
from src.feedback import record_feedback, record_activation, FEEDBACK_TYPES
from src.generator import generate_card, ingest_material
from src.i18n import t, set_locale, get_locale
from src.knowledge_base import search_knowledge_base
from src.llm_client import create_llm_client
from src.parsers.document_parser import parse_document
from src.parsers.url_parser import is_valid_url, parse_url
from src.retrieval import retrieve_relevant_cards
from src.storage import delete_card, load_cards, update_card
from src.trigger_engine import evaluate_triggers, run_decoy_test, is_vague_task
from src.demo_workspace import (
    is_demo_mode_env, apply_demo_mode, demo_units_available,
    seed_demo_workspace,
    DEMO_TASK_EN, DEMO_TASK_ZH,
)
from src.au_output import generate_au_deliverable, parse_task_understanding


st.set_page_config(page_title="RecallBite", page_icon="🍞", layout="wide", initial_sidebar_state="collapsed")

# ── Demo Mode initialization (must run before any unit loading) ─────────
# Demo mode is ON if: env var set, or user toggled it in a previous run.
if "demo_mode" not in st.session_state:
    st.session_state["demo_mode"] = is_demo_mode_env()
apply_demo_mode(st.session_state["demo_mode"])


st.markdown(
    """
<style>
/* ═══════════════════════════════════════════════════════════════
   Theme System — CSS Variables
   ═══════════════════════════════════════════════════════════════ */

:root,
[data-theme="dark"] {
    --rb-bg-primary: #07111f;
    --rb-bg-secondary: #0b1628;
    --rb-bg-surface: rgba(9, 16, 31, 0.72);
    --rb-bg-card: rgba(15, 23, 42, 0.7);
    --rb-bg-input: rgba(8, 15, 28, 0.9);
    --rb-bg-hover: rgba(14, 165, 233, 0.08);
    
    --rb-text-primary: #f8fbff;
    --rb-text-secondary: #d8e2f1;
    --rb-text-muted: #9fb4d1;
    --rb-text-body: #e5eefb;
    --rb-text-meta: #9bb0ca;
    
    --rb-border: rgba(148, 163, 184, 0.18);
    --rb-border-focus: rgba(125, 211, 252, 0.8);
    
    --rb-accent-primary: #0ea5e9;
    --rb-accent-secondary: #6366f1;
    --rb-accent-teal: #14b8a6;
    --rb-accent-amber: #f59e0b;
    --rb-accent-rose: #f43f5e;
    --rb-accent-violet: #8b5cf6;
    
    --rb-pill-teal-bg: rgba(20, 184, 166, 0.12);
    --rb-pill-teal-text: #8de7dc;
    --rb-pill-blue-bg: rgba(59, 130, 246, 0.12);
    --rb-pill-blue-text: #9bd0ff;
    --rb-pill-violet-bg: rgba(139, 92, 246, 0.12);
    --rb-pill-violet-text: #cab8ff;
    --rb-pill-amber-bg: rgba(245, 158, 11, 0.13);
    --rb-pill-amber-text: #ffd38a;
    --rb-pill-rose-bg: rgba(244, 63, 94, 0.13);
    --rb-pill-rose-text: #ffb0bd;
    --rb-pill-slate-bg: rgba(148, 163, 184, 0.12);
    --rb-pill-slate-text: #d7e2f0;
    
    --rb-shadow: rgba(2, 6, 23, 0.45);
    --rb-shadow-sm: rgba(2, 6, 23, 0.2);
}

[data-theme="light"] {
    --rb-bg-primary: #f8fafc;
    --rb-bg-secondary: #f1f5f9;
    --rb-bg-surface: rgba(255, 255, 255, 0.95);
    --rb-bg-card: rgba(255, 255, 255, 0.9);
    --rb-bg-input: #ffffff;
    --rb-bg-hover: rgba(14, 165, 233, 0.06);
    
    --rb-text-primary: #0f172a;
    --rb-text-secondary: #334155;
    --rb-text-muted: #64748b;
    --rb-text-body: #1e293b;
    --rb-text-meta: #64748b;
    
    --rb-border: rgba(148, 163, 184, 0.25);
    --rb-border-focus: rgba(14, 165, 233, 0.8);
    
    --rb-accent-primary: #0284c7;
    --rb-accent-secondary: #4f46e5;
    --rb-accent-teal: #0d9488;
    --rb-accent-amber: #d97706;
    --rb-accent-rose: #e11d48;
    --rb-accent-violet: #7c3aed;
    
    --rb-pill-teal-bg: rgba(20, 184, 166, 0.15);
    --rb-pill-teal-text: #0f766e;
    --rb-pill-blue-bg: rgba(59, 130, 246, 0.15);
    --rb-pill-blue-text: #1d4ed8;
    --rb-pill-violet-bg: rgba(139, 92, 246, 0.15);
    --rb-pill-violet-text: #5b21b6;
    --rb-pill-amber-bg: rgba(245, 158, 11, 0.15);
    --rb-pill-amber-text: #b45309;
    --rb-pill-rose-bg: rgba(244, 63, 94, 0.15);
    --rb-pill-rose-text: #be123c;
    --rb-pill-slate-bg: rgba(148, 163, 184, 0.15);
    --rb-pill-slate-text: #475569;
    
    --rb-shadow: rgba(100, 116, 139, 0.12);
    --rb-shadow-sm: rgba(100, 116, 139, 0.08);
}

/* ── Light-mode overrides for Streamlit's NATIVE widgets ──────────────
   Streamlit (emotion) bakes the dark palette into hashed classes, so for a
   coherent light mode we override the stable structural selectors. The dark
   mode is untouched because these rules only apply under [data-theme=light]. */
[data-theme="light"] body {
    background-color: #f8fafc !important;
    color: #1e293b !important;
}
[data-theme="light"] [data-testid="stAppViewContainer"],
[data-theme="light"] [data-testid="stMain"],
[data-theme="light"] [data-testid="stMainBlockContainer"],
[data-theme="light"] [data-testid="stHeader"] {
    background-color: #f8fafc !important;
    color: #1e293b !important;
}
[data-theme="light"] h1, [data-theme="light"] h2, [data-theme="light"] h3,
[data-theme="light"] h4, [data-theme="light"] h5, [data-theme="light"] h6,
[data-theme="light"] [data-testid="stMarkdownContainer"],
[data-theme="light"] [data-testid="stMarkdownContainer"] p,
[data-theme="light"] [data-testid="stMarkdownContainer"] li,
[data-theme="light"] [data-testid="stMarkdownContainer"] span,
[data-theme="light"] [data-testid="stWidgetLabel"],
[data-theme="light"] label {
    color: #1e293b !important;
}
[data-theme="light"] [data-testid="stExpander"] {
    background-color: #ffffff !important;
    border-color: rgba(148, 163, 184, 0.35) !important;
    color: #1e293b !important;
}
[data-theme="light"] [data-testid="stExpander"] summary,
[data-theme="light"] [data-testid="stExpanderDetails"] {
    color: #1e293b !important;
}
[data-theme="light"] [data-testid="stButton"] button,
[data-theme="light"] [data-testid="stBaseButton-secondary"] {
    background-color: #ffffff !important;
    color: #1e293b !important;
    border-color: rgba(148, 163, 184, 0.45) !important;
}
[data-theme="light"] [data-testid="stTextAreaRootElement"],
[data-theme="light"] [data-testid="stTextInputRootElement"] {
    background-color: #ffffff !important;
    border-color: rgba(148, 163, 184, 0.45) !important;
}
[data-theme="light"] [data-testid="stTextAreaRootElement"] textarea,
[data-theme="light"] [data-testid="stTextInputRootElement"] input {
    background-color: #ffffff !important;
    color: #1e293b !important;
}
[data-theme="light"] [data-testid="stSelectbox"] [data-baseweb="select"] > div,
[data-theme="light"] [data-baseweb="popover"] {
    background-color: #ffffff !important;
    color: #1e293b !important;
    border-color: rgba(148, 163, 184, 0.45) !important;
}
[data-theme="light"] [data-baseweb="popover"] li,
[data-theme="light"] [data-baseweb="menu"] li {
    background-color: #ffffff !important;
    color: #1e293b !important;
}
[data-theme="light"] [data-testid="stAlert"] {
    background-color: #eef4fb !important;
    color: #1e293b !important;
}
[data-theme="light"] [data-testid="stTab"] {
    color: #334155 !important;
}
[data-theme="light"] [data-testid="stVerticalBlockBorderWrapper"] {
    background-color: #ffffff !important;
    border-color: rgba(148, 163, 184, 0.35) !important;
}
[data-theme="light"] [data-testid="stHorizontalBlock"] {
    background-color: transparent !important;
}
[data-theme="light"] [data-testid="stButtonGroup"] button {
    background-color: #ffffff !important;
    color: #1e293b !important;
    border-color: rgba(148, 163, 184, 0.45) !important;
}

/* ═══════════════════════════════════════════════════════════════
   Base styles using CSS variables
   ═══════════════════════════════════════════════════════════════ */

.stApp {
    background:
        radial-gradient(circle at top left, color-mix(in srgb, var(--rb-accent-teal) 14%, transparent), transparent 30%),
        radial-gradient(circle at top right, color-mix(in srgb, var(--rb-accent-primary) 16%, transparent), transparent 26%),
        linear-gradient(180deg, var(--rb-bg-primary) 0%, var(--rb-bg-secondary) 55%, var(--rb-bg-primary) 100%);
    color: var(--rb-text-body);
    font-family: "Segoe UI", "Aptos", "Inter", sans-serif;
}

.block-container {
    max-width: 1280px;
    padding-top: 2rem;
    padding-bottom: 4rem;
}

/* Hero */
.rb-hero {
    border: 1px solid var(--rb-border);
    border-radius: 28px;
    padding: 2rem;
    background: var(--rb-bg-surface);
    box-shadow: 0 18px 60px var(--rb-shadow);
    margin-bottom: 1.25rem;
}

.rb-kicker {
    color: var(--rb-accent-primary);
    text-transform: uppercase;
    letter-spacing: 0.18em;
    font-size: 0.72rem;
    margin-bottom: 0.65rem;
}

.rb-title {
    font-size: 2.45rem;
    line-height: 1.05;
    font-weight: 750;
    letter-spacing: -0.05em;
    color: var(--rb-text-primary);
    margin: 0;
}

.rb-subtitle {
    margin-top: 0.75rem;
    font-size: 1.08rem;
    color: var(--rb-text-secondary);
}

.rb-principle {
    margin-top: 0.5rem;
    color: var(--rb-text-muted);
    font-size: 0.95rem;
}

/* Pills */
.rb-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    border-radius: 999px;
    padding: 0.3rem 0.72rem;
    font-size: 0.78rem;
    line-height: 1;
    margin: 0 0.35rem 0.35rem 0;
    border: 1px solid var(--rb-border);
    background: var(--rb-bg-card);
    color: var(--rb-text-secondary);
}

.rb-pill--teal { background: var(--rb-pill-teal-bg); color: var(--rb-pill-teal-text); }
.rb-pill--blue { background: var(--rb-pill-blue-bg); color: var(--rb-pill-blue-text); }
.rb-pill--violet { background: var(--rb-pill-violet-bg); color: var(--rb-pill-violet-text); }
.rb-pill--amber { background: var(--rb-pill-amber-bg); color: var(--rb-pill-amber-text); }
.rb-pill--rose { background: var(--rb-pill-rose-bg); color: var(--rb-pill-rose-text); }
.rb-pill--slate { background: var(--rb-pill-slate-bg); color: var(--rb-pill-slate-text); }

/* Grid */
.rb-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0.9rem;
    margin-top: 1rem;
}

.rb-mini-card {
    border-radius: 20px;
    padding: 1rem 1rem 0.95rem;
    border: 1px solid var(--rb-border);
    background: var(--rb-bg-card);
    min-height: 120px;
}

.rb-mini-title {
    font-size: 0.95rem;
    font-weight: 650;
    margin-bottom: 0.35rem;
    color: var(--rb-text-primary);
}

.rb-mini-body {
    color: var(--rb-text-muted);
    font-size: 0.9rem;
    line-height: 1.5;
}

/* Container borders */
.stVerticalBlockBorderWrapper {
    border-radius: 22px !important;
    border: 1px solid var(--rb-border) !important;
    background: var(--rb-bg-surface) !important;
    box-shadow: 0 16px 40px var(--rb-shadow-sm) !important;
    padding: 1.2rem 1.2rem 1rem !important;
    margin-bottom: 1rem !important;
}

/* Section headings */
.rb-section-heading {
    font-size: 1.08rem;
    font-weight: 700;
    color: var(--rb-text-primary);
    margin-bottom: 0.25rem;
}

.rb-section-subtext {
    color: var(--rb-text-muted);
    font-size: 0.92rem;
    line-height: 1.5;
    margin-bottom: 1rem;
}

.rb-meta-line {
    color: var(--rb-text-meta);
    font-size: 0.88rem;
}

.rb-divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--rb-border), transparent);
    margin: 1rem 0;
}

/* Inputs */
.stTextArea textarea,
.stTextInput input,
.stSelectbox div[data-baseweb="select"] > div {
    background: var(--rb-bg-input) !important;
    border: 1px solid var(--rb-border) !important;
    color: var(--rb-text-primary) !important;
    border-radius: 16px !important;
}

.stTextArea textarea:focus,
.stTextInput input:focus {
    border-color: var(--rb-border-focus) !important;
    box-shadow: 0 0 0 1px color-mix(in srgb, var(--rb-border-focus) 35%, transparent) !important;
}

/* Buttons */
.stButton > button {
    border-radius: 14px !important;
    background: linear-gradient(135deg, var(--rb-accent-primary), var(--rb-accent-secondary)) !important;
    color: var(--rb-text-primary) !important;
    border: 0 !important;
    font-weight: 650 !important;
    padding: 0.7rem 1.1rem !important;
    box-shadow: 0 10px 24px color-mix(in srgb, var(--rb-accent-secondary) 25%, transparent);
}

.stButton > button:hover {
    filter: brightness(1.05);
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 0.45rem;
}

.stTabs [data-baseweb="tab"] {
    background: var(--rb-bg-card);
    border: 1px solid var(--rb-border);
    border-radius: 999px;
    color: var(--rb-text-secondary);
    padding: 0.65rem 1rem;
}

.stTabs [aria-selected="true"] {
    background: color-mix(in srgb, var(--rb-accent-primary) 16%, transparent) !important;
    color: var(--rb-text-primary) !important;
}

/* Remove default container padding */
.stVerticalBlockBorderWrapper > div {
    padding: 0 !important;
}

/* Labels */
.stLabel, .stMarkdown p, .stMarkdown li {
    color: var(--rb-text-body) !important;
}

/* Expander */
.streamlit-expanderHeader {
    color: var(--rb-text-secondary) !important;
}

/* Segmented control */
.stSegmentedControl > div {
    background: var(--rb-bg-card) !important;
    border: 1px solid var(--rb-border) !important;
}

/* Hide Streamlit chrome (header, footer, menu, toolbar) */
header[data-testid="stHeader"] {
    display: none !important;
}

#MainMenu {
    display: none !important;
}

footer {
    display: none !important;
}

.stDeployButton {
    display: none !important;
}

/* Streamlit 1.57+ toolbar and app manager */
[data-testid="stToolbar"] {
    display: none !important;
}

[data-testid="stAppManager"] {
    display: none !important;
}

/* Hide the status widget / rerun indicator */
[data-testid="stStatusWidget"] {
    display: none !important;
}

/* Hide any remaining Streamlit branding */
.stApp > header {
    display: none !important;
}

[data-testid="collapsedControl"] {
    display: none !important;
}

/* Custom product header */
.rb-product-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.75rem 1.25rem;
    border-radius: 18px;
    background: var(--rb-bg-surface);
    border: 1px solid var(--rb-border);
    margin-bottom: 1rem;
    box-shadow: 0 4px 16px var(--rb-shadow-sm);
}

.rb-product-header .rb-brand {
    font-size: 1.15rem;
    font-weight: 750;
    color: var(--rb-accent-primary);
    letter-spacing: -0.02em;
}

.rb-product-header .rb-mode-pill {
    font-size: 0.75rem;
    padding: 0.25rem 0.6rem;
    border-radius: 999px;
    border: 1px solid var(--rb-border);
    background: var(--rb-bg-card);
    color: var(--rb-text-muted);
}
</style>
""",
    unsafe_allow_html=True,
)


def _escape(value: str) -> str:
    return html.escape(value or "")


def _chip(text: str, tone: str = "slate") -> str:
    return f'<span class="rb-pill rb-pill--{tone}">{_escape(text)}</span>'


def _tone_for_fog(level: str) -> str:
    return {
        "Clear": "teal",
        "Foggy": "amber",
        "Very Foggy": "rose",
    }.get(level, "slate")


def _tone_for_card(card_type: str) -> str:
    return {
        "Insight Pack": "violet",
        "Use Card": "blue",
        "Clue Card": "amber",
    }.get(card_type, "slate")


def _preview(text: str, limit: int = 180) -> str:
    cleaned = " ".join((text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "…"


def _format_created_at(value: str) -> str:
    try:
        return datetime.fromisoformat(value).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return value or "Unknown"


def _render_hero() -> None:
    """Render simplified hero section without duplicated navigation cards."""
    st.markdown(
        f"""
        <div class="rb-hero">
            <div class="rb-kicker">RecallBite</div>
            <div class="rb-title">{t("hero.title")}</div>
            <div class="rb-subtitle">{t("hero.subtitle")}</div>
            <div class="rb-principle">{t("hero.slogan")}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_quick_bite(card: dict) -> None:
    """Compact Quick Bite preview: title, takeaway, key insights, meta, and next actions."""
    fog = card.get("fog_index", {}).get("level", "Unknown")
    card_type = card.get("card_type", "Use Card")
    meta = card.get("_analysis_meta", {})

    # Header: card type + fog + mode
    chips = [_chip(fog, _tone_for_fog(fog)), _chip(card_type, _tone_for_card(card_type))]
    mode_label = meta.get("mode", "deterministic")
    chips.append(_chip(f"{t('qb.mode_prefix')}: {mode_label}", "teal" if "AI" in str(mode_label) else "slate"))
    st.markdown("".join(chips), unsafe_allow_html=True)

    # Source line
    source = card.get("source", "") or card.get("source_grounding", {}).get("source_title", "")
    if source:
        st.markdown(f'<div class="rb-meta-line">{t("qb.source_label")}: {_escape(source)}</div>', unsafe_allow_html=True)

    # Core insight (single takeaway)
    st.markdown(f"**{t('qb.takeaway')}**\n\n{_escape(card.get('core_insight', ''))}")

    # Key insights (up to 3)
    insight_pack = card.get("insight_pack", {})
    key_insights = insight_pack.get("key_insights", [])
    if key_insights:
        st.markdown(f"**{t('qb.key_insights')}**")
        for item in key_insights[:3]:
            text = item if isinstance(item, str) else item.get("insight", "")
            st.markdown(f"- {_escape(text)}")

    # Use Card fields
    use_card = card.get("use_card", {})
    if use_card.get("what_it_means"):
        st.markdown(f"**{t('qb.what_it_means')}**\n\n{_escape(use_card['what_it_means'])}")
    if use_card.get("how_to_say_it"):
        st.markdown(f"**{t('qb.how_to_say_it')}**\n\n{_escape(use_card['how_to_say_it'])}")

    # Clue Card fields
    clue_card = card.get("clue_card", {})
    if clue_card.get("possible_direction"):
        st.markdown(f"**{t('qb.possible_direction')}**\n\n{_escape(clue_card['possible_direction'])}")
    if clue_card.get("what_is_missing"):
        st.markdown(f"**{t('qb.what_is_missing')}**\n\n{_escape(str(clue_card['what_is_missing']))}")

    st.markdown("<div class='rb-divider'></div>", unsafe_allow_html=True)

    # Progressive disclosure sections
    use_scenarios = insight_pack.get("use_scenarios", [])
    if use_scenarios:
        with st.expander(t("qb.use_scenarios")):
            for s in use_scenarios:
                st.markdown(f"- {_escape(s)}")

    talking_points = insight_pack.get("talking_points", [])
    questions = insight_pack.get("questions_to_ask", [])
    if talking_points or questions:
        with st.expander(t("qb.talking_points")):
            for tp in talking_points:
                st.markdown(f"- {_escape(tp)}")
            for q in questions:
                st.markdown(f"- {_escape(q)}")

    copy_lines = card.get("copy_ready_lines", {})
    if any(copy_lines.values()):
        with st.expander(t("qb.copy_ready")):
            for label, value in copy_lines.items():
                if value:
                    display_label = label.replace("_", " ").title()
                    st.markdown(f"**{display_label}**\n\n{_escape(value)}")

    source_grounding = card.get("source_grounding", {})
    evidence_spans = source_grounding.get("evidence_spans", [])
    if evidence_spans:
        with st.expander(t("qb.source_evidence")):
            for span in evidence_spans:
                text = span.get("text", "") if isinstance(span, dict) else str(span)
                loc = span.get("location", "") if isinstance(span, dict) else ""
                st.markdown(f"> {_escape(text)}")
                if loc:
                    st.markdown(f'<div class="rb-meta-line">{_escape(loc)}</div>', unsafe_allow_html=True)

    # Trigger map (friendly summary, hidden by default)
    trigger_map = card.get("trigger_map", {})
    keywords = trigger_map.get("keywords", [])
    scenarios = trigger_map.get("scenarios", [])
    if keywords or scenarios:
        with st.expander(t("qb.trigger_map")):
            trigger_chips = [_chip(item, "blue") for item in keywords[:6]] + [_chip(item, "violet") for item in scenarios[:6]]
            st.markdown("".join(trigger_chips), unsafe_allow_html=True)

    # Advanced metadata
    with st.expander(t("qb.advanced_meta")):
        st.markdown(f"**{t('meta.fog_index')}:** {_escape(fog)} — {_escape(card.get('fog_index', {}).get('reason', ''))}")
        st.markdown(f"**{t('meta.evidence_quality')}:** {_escape(card.get('fog_index', {}).get('evidence_quality', ''))}")
        tags = card.get("topic_tags", [])
        if tags:
            st.markdown(f"**{t('meta.tags')}:** {', '.join(_escape(t) for t in tags)}")
        st.markdown(f"**{t('meta.created')}:** {_format_created_at(card.get('created_at', ''))}")
        if card.get("document_id"):
            st.markdown(f"**{t('meta.document_id')}:** {_escape(card['document_id'])}")


def _render_memory_card(card: dict, show_full: bool = False, key_prefix: str = "", render_index: int = 0) -> None:
    fog = card.get("fog_index", {}).get("level", "Unknown")
    card_type = card.get("card_type", "Use Card")
    tags = card.get("topic_tags", [])
    chips = [_chip(fog, _tone_for_fog(fog)), _chip(card_type, _tone_for_card(card_type))]
    chips.extend(_chip(tag, "slate") for tag in tags[:6])
    st.markdown("".join(chips), unsafe_allow_html=True)

    meta = [card.get("source_type", ""), _format_created_at(card.get("created_at", ""))]
    meta = [item for item in meta if item]
    if meta:
        st.markdown(f'<div class="rb-meta-line">{" · ".join(_escape(item) for item in meta)}</div>', unsafe_allow_html=True)

    source = card.get("source", "")
    if source:
        st.markdown(f'<div class="rb-meta-line">{t("mc.source")}: {_escape(source)}</div>', unsafe_allow_html=True)

    st.markdown(f"**{t('mc.core_insight')}**\n\n{_escape(card.get('core_insight', ''))}")

    if card_type == "Insight Pack":
        insight_pack = card.get("insight_pack", {})
        st.markdown(f"**{t('mc.30s_takeaway')}**\n\n{_escape(insight_pack.get('thirty_second_takeaway', card.get('core_insight', '')))}")
        insights = insight_pack.get("key_insights", [])
        if insights:
            st.markdown(f"**{t('mc.key_insights')}**")
            for item in insights[:3]:
                st.markdown(f"- {_escape(item)}")
        scenarios = insight_pack.get("use_scenarios", [])
        if scenarios:
            st.markdown(f"**{t('mc.use_scenarios')}**")
            for item in scenarios[:3]:
                st.markdown(f"- {_escape(item)}")
        if show_full:
            st.markdown(f"**{t('mc.talking_points')}**")
            for item in insight_pack.get("talking_points", [])[:3]:
                st.markdown(f"- {_escape(item)}")
            st.markdown(f"**{t('mc.questions_to_ask')}**")
            for item in insight_pack.get("questions_to_ask", [])[:3]:
                st.markdown(f"- {_escape(item)}")

    elif card_type == "Use Card":
        use_card = card.get("use_card", {})
        st.markdown(f"**{t('mc.what_it_means')}**\n\n{_escape(use_card.get('what_it_means', card.get('core_insight', '')))}")
        st.markdown(f"**{t('mc.where_to_use')}**\n\n{_escape(use_card.get('where_to_use', ''))}")
        st.markdown(f"**{t('mc.how_to_say_it')}**\n\n{_escape(use_card.get('how_to_say_it', ''))}")
        st.markdown(f"**{t('mc.what_to_ask')}**\n\n{_escape(use_card.get('what_to_ask', ''))}")

    else:
        clue_card = card.get("clue_card", {})
        st.markdown(f"**{t('mc.possible_direction')}**\n\n{_escape(clue_card.get('possible_direction', card.get('core_insight', '')))}")
        st.markdown(f"**{t('mc.what_is_missing')}**\n\n{_escape(clue_card.get('what_is_missing', ''))}")
        st.markdown(f"**{t('mc.what_to_add_next')}**\n\n{_escape(clue_card.get('what_to_add_next', ''))}")
        st.markdown(f"**{t('mc.fog_note')}**\n\n{_escape(clue_card.get('very_foggy_note', ''))}")

    st.markdown("<div class='rb-divider'></div>", unsafe_allow_html=True)

    # Copy-ready lines (compact)
    copy_lines = card.get("copy_ready_lines", {})
    if any(copy_lines.values()):
        st.markdown(f"**{t('mc.copy_ready')}**")
        st.text_area(
            t("mc.copy_ready"),
            value=copy_lines.get("professional_sentence", ""),
            height=88,
            label_visibility="collapsed",
            key=f"ta_{key_prefix}_{card['id']}_{render_index}",
        )
        if copy_lines.get("meeting_question"):
            st.markdown(f"**{t('mc.meeting_question')}:** {_escape(copy_lines['meeting_question'])}")

    # Trigger map: friendly summary only, hidden by default
    trigger_map = card.get("trigger_map", {})
    keywords = trigger_map.get("keywords", [])
    scenarios = trigger_map.get("scenarios", [])
    if keywords or scenarios:
        with st.expander(t("mc.recall_trigger")):
            trigger_chunks = [_chip(item, "blue") for item in keywords[:6]] + [_chip(item, "violet") for item in scenarios[:6]]
            st.markdown("".join(trigger_chunks), unsafe_allow_html=True)


def _render_activation_card(card: dict, score: int, suggestion: dict, index: int) -> None:
    fog = card.get("fog_index", {}).get("level", "Unknown")
    card_type = card.get("card_type", "Use Card")
    with st.container(border=True):
        st.markdown(f"### {index}. {_escape(_preview(card.get('knowledge_seed', ''), 96))}")
        st.markdown(
            "".join([
                _chip(fog, _tone_for_fog(fog)),
                _chip(card_type, _tone_for_card(card_type)),
                _chip(f"{t('ac.relevance')} {score}", "teal"),
            ]),
            unsafe_allow_html=True,
        )
        st.markdown(f"**{t('ac.why_relevant')}**\n\n{_escape(suggestion['why_relevant'])}")
        st.markdown(f"**{t('ac.how_to_apply')}**\n\n{_escape(suggestion['how_to_use_now'])}")
        st.markdown(f"**{t('ac.ready_wording')}**")
        st.text_area(
            t("ac.ready_wording"),
            value=suggestion["copy_ready_paragraph"],
            height=100,
            label_visibility="collapsed",
            key=f"activation_copy_{card['id']}_{index}",
        )
        st.markdown(f"**{t('ac.better_question')}**\n\n{_escape(suggestion['question_to_ask'])}")
        trigger_scenarios = card.get("trigger_map", {}).get("scenarios", [])
        if trigger_scenarios:
            st.markdown(f"**{t('ac.future_trigger')}** {_escape(', '.join(trigger_scenarios[:3]))}")
        st.markdown(f'<div class="rb-meta-line">{_escape(suggestion["confidence_note"])}</div>', unsafe_allow_html=True)


def _unit_source_page(unit: dict) -> str:
    """Extract a human-readable source reference (page/section) from a unit."""
    spans = unit.get("evidence_spans", [])
    if spans:
        loc = spans[0].get("location", "")
        if loc:
            return loc
    return unit.get("source_document_ids", [""])[0] if unit.get("source_document_ids") else ""


def _unit_validation_label(unit: dict) -> tuple[str, str]:
    """Return (label, tone) describing a unit's validation status.

    Deliberately avoids showing raw pass-rate percentages as a quality
    certification. Uses 'Internal validation passed' + a note that real-user
    validation is still pending.
    """
    decoy = unit.get("decoy_tests", {})
    if decoy.get("last_tested_at"):
        return t("review.internal_passed"), "teal"
    return t("review.not_user_validated"), "amber"


def _render_distill_review(candidate_ids: list[str], section_count: int, rejected_count: int) -> None:
    """Deep Distill Review: let the user inspect and decide on each candidate unit.

    Candidates are shown collapsed by default (name/type/purpose/source/status).
    Expanding reveals triggers, anti-triggers, diagnostics, steps, boundaries,
    quality checks, evidence and validation results.
    Actions: Activate / Keep as Draft / Reject / Edit. Nothing is auto-activated.
    """
    from src.activation_unit import get_unit, update_unit, activate_unit

    with st.container(border=True):
        st.markdown(f'<div class="rb-section-heading">🔬 {t("review.title")}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="rb-section-subtext">{t("review.subtitle")}</div>', unsafe_allow_html=True)
        summary_chips = []
        if section_count:
            summary_chips.append(_chip(f"{section_count} {t('review.sections_analyzed')}", "blue"))
        summary_chips.append(_chip(f"{len(candidate_ids)} {t('review.candidates_found')}", "violet"))
        if rejected_count:
            summary_chips.append(_chip(f"{rejected_count} {t('review.rejected_note')}", "rose"))
        st.markdown("".join(summary_chips), unsafe_allow_html=True)

    for cid in candidate_ids:
        unit = get_unit(cid)
        if not unit:
            continue
        status = unit.get("status", "draft")
        status_tone = {"active": "teal", "draft": "amber", "archived": "slate", "rejected": "rose"}.get(status, "slate")
        val_label, val_tone = _unit_validation_label(unit)
        source_page = _unit_source_page(unit)

        with st.container(border=True):
            header = (
                f"**{_escape(unit.get('name', 'Untitled').strip())}** "
                f"{_chip(unit.get('type', ''), 'violet')}"
                f"{_chip(status, status_tone)}"
                f"{_chip(val_label, val_tone)}"
            )
            if source_page:
                header += f' <span class="rb-meta-line">{t("review.source_label")}: {_escape(source_page)}</span>'
            st.markdown(header, unsafe_allow_html=True)
            st.markdown(f"{_escape(unit.get('purpose', ''))}")

            with st.expander(t("review.when_to_use") + " / " + t("review.when_not_to_use")):
                st.markdown(f"**{t('review.when_to_use')}:**")
                for tr in unit.get("triggers", []):
                    st.markdown(f"- {_escape(tr.get('scenario', ''))}")
                st.markdown(f"**{t('review.when_not_to_use')}:**")
                for at in unit.get("anti_triggers", []):
                    st.markdown(f"- {_escape(at.get('scenario', ''))}")

            with st.expander(t("review.confirm_first")):
                for q in unit.get("diagnostic_questions", []):
                    st.markdown(f"- {_escape(q)}")

            with st.expander(t("review.how_to_execute")):
                for s in unit.get("execution_steps", []):
                    st.markdown(f"- {_escape(s)}")
                if unit.get("boundaries"):
                    st.markdown(f"**{t('au.boundaries')}:**")
                    for b in unit["boundaries"]:
                        st.markdown(f"- {_escape(b)}")

            with st.expander(t("review.validation")):
                if unit.get("quality_checks"):
                    st.markdown(f"**{t('au.quality_checks')}:**")
                    for qc in unit["quality_checks"]:
                        st.markdown(f"- {_escape(qc)}")
                decoy = unit.get("decoy_tests", {})
                if decoy.get("last_tested_at"):
                    cat = decoy.get("category_rates", {})
                    st.markdown(
                        f'{_chip(t("review.internal_passed"), "teal")}'
                        f'{_chip(t("review.not_user_validated"), "amber")}',
                        unsafe_allow_html=True,
                    )
                    if cat:
                        st.markdown(
                            f'<div class="rb-meta-line">'
                            f'should-trigger {cat.get("should_trigger", 0):.0%} · '
                            f'should-not-trigger {cat.get("should_not_trigger", 0):.0%} · '
                            f'boundary {cat.get("boundary_cases", 0):.0%}</div>',
                            unsafe_allow_html=True,
                        )
                else:
                    st.markdown(f'{_chip(t("review.not_user_validated"), "amber")}', unsafe_allow_html=True)

            with st.expander(t("au.evidence")):
                for span in unit.get("evidence_spans", [])[:3]:
                    st.markdown(f"> {_escape(span.get('text', '')[:250])}")
                    if span.get("location"):
                        st.markdown(f'<div class="rb-meta-line">{_escape(span["location"])}</div>', unsafe_allow_html=True)

            # Actions
            a1, a2, a3, a4 = st.columns(4)
            with a1:
                if status != "active":
                    if st.button(t("review.btn_activate"), key=f"rv_act_{cid}"):
                        ok, issues = activate_unit(cid)
                        if ok:
                            st.success(t("review.activated"))
                            st.rerun()
                        else:
                            st.error(f"{t('au.activate_failed')}: {'; '.join(issues)}")
            with a2:
                if status != "draft":
                    if st.button(t("review.btn_keep_draft"), key=f"rv_draft_{cid}"):
                        update_unit(cid, {"status": "draft"})
                        st.rerun()
            with a3:
                if status != "archived":
                    if st.button(t("review.btn_reject"), key=f"rv_rej_{cid}"):
                        update_unit(cid, {"status": "archived"})
                        st.rerun()
            with a4:
                with st.expander(t("review.btn_edit")):
                    new_name = st.text_input("Name", value=unit.get("name", ""), key=f"rv_name_{cid}")
                    new_purpose = st.text_area("Purpose", value=unit.get("purpose", ""), height=70, key=f"rv_purpose_{cid}")
                    if st.button(t("memory.save_changes"), key=f"rv_save_{cid}"):
                        update_unit(cid, {"name": new_name, "purpose": new_purpose})
                        st.rerun()


def _render_au_library_card(unit: dict) -> None:
    """User-friendly Activation Unit card for the library.

    Default view shows: name, purpose, when to use, when NOT to use, source,
    validation status (worded, not a raw percentage), and usage history.
    Full backend JSON is NOT shown by default.
    """
    from src.activation_unit import activate_unit, update_unit

    status = unit.get("status", "draft")
    status_tone = {"active": "teal", "draft": "amber", "archived": "slate"}.get(status, "slate")
    val_label, val_tone = _unit_validation_label(unit)
    source_page = _unit_source_page(unit)

    st.markdown(
        f"### {_escape(unit.get('name', 'Untitled'))} "
        f"{_chip(unit.get('type', ''), 'violet')}{_chip(status, status_tone)}",
        unsafe_allow_html=True,
    )
    st.markdown(f"{_escape(unit.get('purpose', ''))}")

    # When to use / when NOT to use (the two questions users care about most)
    triggers = unit.get("triggers", [])
    if triggers:
        st.markdown(f"**{t('lib.when_to_use')}:** {_escape(triggers[0].get('scenario', ''))}")
    anti_triggers = unit.get("anti_triggers", [])
    if anti_triggers:
        st.markdown(f"**{t('lib.when_not_to_use')}:** {_escape(anti_triggers[0].get('scenario', ''))}")

    # Source + validation status (worded, not a percentage)
    meta_parts = []
    if source_page:
        meta_parts.append(f"{t('lib.source')}: {_escape(source_page)}")
    if meta_parts:
        st.markdown(f'<div class="rb-meta-line">{" · ".join(meta_parts)}</div>', unsafe_allow_html=True)
    st.markdown(
        f'{_chip(val_label, val_tone)}{_chip(t("review.not_user_validated"), "slate")}',
        unsafe_allow_html=True,
    )

    # Usage history
    usage = unit.get("usage", {})
    act_count = usage.get("activation_count", 0)
    if act_count > 0:
        st.markdown(
            f'<div class="rb-meta-line">{t("lib.usage_history")}: '
            f"{act_count} {t('lib.activations')}, "
            f"{usage.get('useful_count', 0)} {t('lib.useful')}, "
            f"{usage.get('false_trigger_count', 0)} {t('lib.false_triggers')}</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(f'<div class="rb-meta-line">{t("lib.never_used")}</div>', unsafe_allow_html=True)

    # Expandable: execution steps, boundaries, quality checks, evidence
    with st.expander(t("au.steps")):
        for step in unit.get("execution_steps", []):
            st.markdown(f"- {_escape(step)}")
        if unit.get("boundaries"):
            st.markdown(f"**{t('au.boundaries')}:**")
            for b in unit["boundaries"]:
                st.markdown(f"- {_escape(b)}")
        if unit.get("quality_checks"):
            st.markdown(f"**{t('au.quality_checks')}:**")
            for qc in unit["quality_checks"]:
                st.markdown(f"- {_escape(qc)}")
    with st.expander(t("au.evidence")):
        for span in unit.get("evidence_spans", []):
            st.markdown(f"> {_escape(span.get('text', '')[:200])}")

    # Actions
    au_col1, au_col2, au_col3 = st.columns(3)
    with au_col1:
        if status == "draft":
            if st.button(t("au.activate_btn"), key=f"au_activate_{unit['id']}"):
                success, issues = activate_unit(unit["id"])
                if success:
                    st.success(t("au.activate_success"))
                    st.rerun()
                else:
                    st.error(f"{t('au.activate_failed')}: {'; '.join(issues)}")
    with au_col2:
        if st.button(t("au.run_decoy"), key=f"au_decoy_{unit['id']}"):
            test_results = run_decoy_test(unit)
            st.session_state[f"decoy_results_{unit['id']}"] = test_results
            from src.activation_unit import update_unit as _au_update
            unit["decoy_tests"] = test_results
            _au_update(unit["id"], {"decoy_tests": test_results})
    with au_col3:
        if st.button(t("au.delete_btn"), key=f"au_delete_{unit['id']}"):
            delete_unit(unit["id"])
            st.rerun()

    decoy_results = st.session_state.get(f"decoy_results_{unit['id']}")
    if decoy_results:
        st.markdown(f"**{t('au.decoy_test')}** — {t('au.pass_rate')}: {decoy_results['pass_rate']:.0%}")
        for item in decoy_results.get("should_trigger", []):
            icon = "✅" if item["passed"] else "❌"
            st.markdown(f"{icon} Should trigger: {_escape(item['case'][:80])}")
        for item in decoy_results.get("should_not_trigger", []):
            icon = "✅" if item["passed"] else "❌"
            st.markdown(f"{icon} Should NOT trigger: {_escape(item['case'][:80])}")


def _search_cards(cards: list[dict], query: str) -> list[dict]:
    if not query.strip():
        return cards
    query_lower = query.lower().strip()
    filtered: list[dict] = []
    for card in cards:
        searchable = " ".join(
            [
                card.get("knowledge_seed", ""),
                card.get("core_insight", ""),
                " ".join(card.get("topic_tags", [])),
                " ".join(card.get("trigger_map", {}).get("keywords", [])),
                " ".join(card.get("trigger_map", {}).get("scenarios", [])),
            ]
        ).lower()
        if query_lower in searchable:
            filtered.append(card)
    return filtered


# Settings panel - Language and Theme selection
with st.expander(t("settings.title")):
    settings_col1, settings_col2, settings_col3, settings_col4 = st.columns(4)
    with settings_col1:
        interface_lang = st.selectbox(
            t("settings.interface_lang"),
            ["中文", "English"],
            index=0 if get_locale() == "zh-CN" else 1,
            key="interface_lang_selector",
        )
        new_locale = "zh-CN" if interface_lang == "中文" else "en"
        if new_locale != get_locale():
            set_locale(new_locale)
            st.rerun()
    with settings_col2:
        _theme_options = [t("theme.system"), t("theme.light"), t("theme.dark")]
        theme_choice = st.selectbox(
            t("settings.appearance"),
            _theme_options,
            index=2,
            key=f"theme_selector_{get_locale()}",
        )
    with settings_col3:
        # Locale-suffixed key: the options are translated, so a fresh key per
        # locale prevents a stale (old-language) value lingering after a switch.
        output_lang_global = st.selectbox(
            t("settings.output_lang"),
            [t("add.lang_auto"), t("add.lang_zh"), t("add.lang_en"), t("add.lang_bilingual")],
            index=0,
            key=f"global_output_lang_{get_locale()}",
        )
    with settings_col4:
        # Demo workspace toggle
        if st.session_state["demo_mode"]:
            if st.button(t("demo.exit_btn"), key="demo_exit_btn"):
                st.session_state["demo_mode"] = False
                apply_demo_mode(False)
                st.rerun()
        elif demo_units_available():
            if st.button(t("demo.load_btn"), key="demo_load_btn"):
                st.session_state["demo_mode"] = True
                apply_demo_mode(True)
                st.rerun()

# Demo mode banner
if st.session_state["demo_mode"]:
    st.info(f"🧪 {t('demo.badge')} — {t('demo.note')}")
    if st.button(f"♻️ {t('demo.reset_btn')}", key="demo_reset_btn"):
        seed_demo_workspace()
        # Clear any cached activation output so the rebuilt workspace is reflected
        st.session_state.pop("au_activation", None)
        st.session_state["_demo_just_reset"] = True
        st.rerun()
    if st.session_state.pop("_demo_just_reset", False):
        st.success(t("demo.reset_done"))

# Inject theme via JavaScript.
# NOTE: st.markdown strips <script> tags even with unsafe_allow_html=True, so the
# theme attribute would never be applied that way. components.html renders a
# (zero-height) iframe whose script CAN run and reaches the parent document to
# set the data-theme attribute that drives the CSS variables below.
#
# KNOWN LIMITATION (fragile by nature — keep, do not rewrite for "purity"):
# This relies on Streamlit's DOM structure, iframe sandbox permissions, the
# parent-document layout, and version-specific Streamlit behaviour. It works in
# the current pinned Streamlit release but is NOT a long-term stable theme
# architecture. Re-verify after EVERY Streamlit upgrade (see the theme smoke
# tests in tests/test_pdf_i18n_theme.py). Do not rewrite this soon just to make
# it "architecturally perfect".
_theme_map = {t("theme.system"): "system", t("theme.light"): "light", t("theme.dark"): "dark"}
_theme_value = _theme_map.get(theme_choice, "system")
st.components.v1.html(
    f"""<script>
    (function() {{
        var theme = '{_theme_value}';
        var root = window.parent.document.documentElement;
        if (theme === 'system') {{
            var prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            root.setAttribute('data-theme', prefersDark ? 'dark' : 'light');
        }} else {{
            root.setAttribute('data-theme', theme);
        }}
    }})();
    </script>""",
    height=0,
)

_render_hero()

# Mode indicator + privacy notice
client = create_llm_client()
mode_label_raw = client.mode_label
# Translate mode label via i18n
if "Demo" in mode_label_raw:
    mode_label = t("mode.demo")
    mode_tone = "amber"
    privacy_note = t("mode.local_notice")
elif "AI" in mode_label_raw:
    mode_label = mode_label_raw
    mode_tone = "teal"
    privacy_note = t("mode.external_notice")
else:
    mode_label = mode_label_raw
    mode_tone = "teal"
    privacy_note = t("mode.local_notice")
st.markdown(
    f'<div style="text-align:right;margin-bottom:0.5rem;">'
    f'{_chip(mode_label, mode_tone)}'
    f'<span class="rb-meta-line" style="margin-left:0.5rem;">{privacy_note}</span>'
    f'</div>',
    unsafe_allow_html=True,
)

tab_process, tab_ask, tab_library, tab_activate = st.tabs(
    [t("nav.add_knowledge"), t("nav.ask"), t("nav.memory"), t("nav.activate")]
)

# Handle tab switching from CTAs
_ask_scope_doc_id = st.session_state.pop("ask_scope_doc_id", "")
_activate_card_id = st.session_state.pop("activate_card_id", "")
st.session_state.pop("switch_to_tab", None)


with tab_process:
    left, right = st.columns([1.4, 0.9], gap="large")

    with left:
        with st.container(border=True):
            st.markdown(f'<div class="rb-section-heading">{t("add.title")}</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="rb-section-subtext">{t("add.subtitle")}</div>',
                unsafe_allow_html=True,
            )

            # Input mode selector
            input_mode = st.segmented_control(
                t("add.input_type"),
                [t("add.paste_text"), t("add.upload_file"), t("add.public_url")],
                default=t("add.paste_text"),
            )

            material_input = ""
            source_note = ""
            uploaded_filename = ""
            _structured_pages = []  # Structured PDF sections for section-aware analysis

            if input_mode == t("add.paste_text"):
                material_input = st.text_area(
                    t("add.paste_text"),
                    placeholder=t("add.material_placeholder"),
                    height=230,
                    label_visibility="collapsed",
                )

            elif input_mode == t("add.upload_file"):
                uploaded = st.file_uploader(
                    t("add.upload_file"),
                    type=["txt", "md", "pdf", "docx", "pptx"],
                    label_visibility="collapsed",
                )
                if uploaded is not None:
                    try:
                        doc = parse_document(uploaded.getvalue(), uploaded.name)
                        material_input = doc.text
                        uploaded_filename = uploaded.name
                        source_note = doc.source_reference or uploaded_filename
                        _structured_pages = doc.structured_pages or []
                        if doc.location_info:
                            st.caption(f"{t('add.parsed_pages', n=doc.location_info)}")
                            if doc.detected_language:
                                st.caption(f"{t('add.detected_lang', lang=doc.detected_language)}")
                    except ImportError as exc:
                        st.error(f"{t('add.missing_dep')}: {exc}")
                        material_input = ""
                    except Exception as exc:
                        st.error(f"{t('add.processing_error')} {exc}")
                        material_input = ""
                else:
                    material_input = ""

            else:  # Public URL
                url_input = st.text_input(
                    "",
                    placeholder=t("add.url_placeholder"),
                    label_visibility="collapsed",
                )
                if url_input.strip():
                    try:
                        if not is_valid_url(url_input.strip()):
                            st.error(t("add.error_empty") + " " + t("add.url_invalid"))
                            material_input = ""
                        else:
                            doc = parse_url(url_input.strip())
                            material_input = doc.text
                            source_note = doc.source_title or doc.source_reference or url_input.strip()
                            if doc.source_title:
                                st.caption(f"{t('add.url_title')}: {doc.source_title}")
                    except ImportError as exc:
                        st.error(f"{t('add.missing_dep')}: {exc}")
                        material_input = ""
                    except Exception as exc:
                        st.error(f"{t('add.processing_error')} {exc}")
                        material_input = ""
                else:
                    material_input = ""

            input_type_label = st.selectbox(
                t("add.input_type"),
                [t("add.auto_detect"), t("add.article"), t("add.transcript"), t("add.webcast"), t("add.slide"), t("add.link"), t("add.thought")],
                index=0,
            )
            input_type_map = {
                t("add.auto_detect"): "auto-detect",
                t("add.article"): "article",
                t("add.transcript"): "transcript",
                t("add.webcast"): "webcast",
                t("add.slide"): "slide",
                t("add.link"): "link",
                t("add.thought"): "thought",
            }
            input_type_code = input_type_map.get(input_type_label, "auto-detect")

            with st.expander(t("add.optional_details")):
                if not source_note:
                    source_note = st.text_input(t("add.source"), placeholder=t("add.source_placeholder"))
                topic_tags_text = st.text_input(t("add.tags"), placeholder=t("add.tags_placeholder"))
                intended_use = st.text_input(t("add.intended_use"), placeholder=t("add.intended_use_placeholder"))

            # Output language selector
            output_language_label = st.selectbox(
                t("add.output_language"),
                [t("add.lang_auto"), t("add.lang_zh"), t("add.lang_en"), t("add.lang_bilingual")],
                index=0,
                key="output_language_selector",
            )
            language_map = {
                t("add.lang_auto"): "auto",
                t("add.lang_zh"): "zh",
                t("add.lang_en"): "en",
                t("add.lang_bilingual"): "bilingual",
            }
            output_language = language_map.get(output_language_label, "auto")

            # Processing Depth selector
            depth_label = st.selectbox(
                t("depth.label"),
                [t("depth.auto"), t("depth.archive"), t("depth.digest"), t("depth.deep_distill")],
                index=0,
                key="processing_depth_selector",
            )
            depth_map = {
                t("depth.auto"): "auto",
                t("depth.archive"): "archive",
                t("depth.digest"): "digest",
                t("depth.deep_distill"): "deep_distill",
            }
            processing_depth = depth_map.get(depth_label, "auto")

            # Button label adapts to the selected processing depth.
            submit_label_key = {
                "archive": "add.submit_archive",
                "digest": "add.submit_digest",
                "deep_distill": "add.submit_deep_distill",
            }.get(processing_depth, "add.submit")

            if st.button(t(submit_label_key), type="primary"):
                if not material_input.strip():
                    st.error(t("add.error_empty"))
                else:
                    try:
                        new_card = ingest_material(
                            knowledge_seed=material_input,
                            source_type=input_type_label,
                            topic_tags_text=topic_tags_text,
                            source=source_note,
                            input_type=input_type_code,
                            intended_use=intended_use,
                            output_language=output_language,
                            structured_pages=_structured_pages or None,
                            processing_depth=processing_depth,
                        )
                        st.session_state["last_generated_card"] = new_card
                        meta = new_card.get("_analysis_meta", {})
                        depth_info = new_card.get("_depth_decision", {})

                        # Show depth routing info
                        if depth_info:
                            st.info(f"{t('depth.auto_reason')}: {depth_info.get('selected_depth', '')} — {depth_info.get('reason', '')} ({t('depth.confidence')}: {depth_info.get('confidence', '')})")

                        # Archive mode: different message
                        if new_card.get("card_type") == "Archived":
                            st.success(t("depth.archive_note"))
                        elif meta.get("fallback"):
                            st.warning(f"{t('add.success_saved')} {new_card['card_type']} · {new_card['fog_index']['level']} · {t('add.fallback_reason')}: {meta.get('reason', 'AI unavailable')}")
                        else:
                            st.success(f"{t('add.success_saved')} {new_card['card_type']} · {new_card['fog_index']['level']} · {t('add.mode_label')}: {meta.get('mode', 'unknown')}")

                        # Show candidate units if deep distill -> Deep Distill Review
                        candidates = new_card.get("_candidate_units", [])
                        if candidates:
                            dmeta = new_card.get("_distill_meta", {})
                            st.session_state["distill_review"] = {
                                "candidate_ids": [cu["id"] for cu in candidates],
                                "section_count": dmeta.get("sections_processed", 0),
                                "rejected_count": dmeta.get("rejected_count", 0),
                            }
                    except Exception as exc:
                        st.error(f"{t('add.processing_error')} {exc}")

        generated_card = st.session_state.get("last_generated_card")
        if generated_card:
            with st.container(border=True):
                st.markdown(f'<div class="rb-section-heading">{t("add.quick_bite")}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="rb-section-subtext">{t("add.quick_bite_sub")}</div>', unsafe_allow_html=True)
                _render_quick_bite(generated_card)

                st.markdown("<div class='rb-divider'></div>", unsafe_allow_html=True)
                # Next-action CTAs
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button(t("cta.ask_source"), key="cta_ask"):
                        st.session_state["ask_scope_doc_id"] = generated_card.get("document_id", "")
                        st.session_state["switch_to_tab"] = "ask"
                        st.rerun()
                with col2:
                    if st.button(t("cta.activate_task"), key="cta_activate"):
                        st.session_state["activate_card_id"] = generated_card.get("id", "")
                        st.session_state["switch_to_tab"] = "activate"
                        st.rerun()
                with col3:
                    if st.button(t("cta.add_another"), key="cta_add_another"):
                        st.session_state.pop("last_generated_card", None)
                        st.rerun()

        # Deep Distill Review (persists across reruns until a new material is processed)
        distill_review = st.session_state.get("distill_review")
        if distill_review:
            _render_distill_review(
                distill_review["candidate_ids"],
                distill_review["section_count"],
                distill_review["rejected_count"],
            )

    with right:
        with st.container(border=True):
            st.markdown(f'<div class="rb-section-heading">{t("add.what_this_does")}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="rb-section-subtext">{t("add.what_this_does_desc")}</div>', unsafe_allow_html=True)
            st.markdown(_chip(t("fog.clear"), "teal") + _chip(t("fog.foggy"), "amber") + _chip(t("fog.very_foggy"), "rose"), unsafe_allow_html=True)
            st.markdown(
                f'<div class="rb-meta-line">{t("add.clear_desc")}</div>',
                unsafe_allow_html=True,
            )

        with st.container(border=True):
            st.markdown(f'<div class="rb-section-heading">{t("add.input_examples")}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="rb-section-subtext">{t("add.input_examples_hint")}</div>', unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown(f'<div class="rb-section-heading">{t("add.guardrails")}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="rb-section-subtext">{t("add.guardrails_desc")}</div>', unsafe_allow_html=True)


with tab_ask:
    with st.container(border=True):
        st.markdown(f'<div class="rb-section-heading">{t("ask.title")}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="rb-section-subtext">{t("ask.subtitle")}</div>', unsafe_allow_html=True)

    # Source scope selector
    all_docs = []
    try:
        from src.knowledge_base import list_documents
        all_docs = list_documents()
    except Exception:
        pass

    scope_options = {"all": t("ask.scope_all")}
    for doc in all_docs:
        scope_options[doc["id"]] = f"{doc.get('title', 'Untitled')} ({doc.get('source_kind', '')})"

    scope_col1, scope_col2 = st.columns([2, 1])
    with scope_col1:
        query = st.text_input(t("ask.question"), placeholder=t("ask.question_placeholder"))
    with scope_col2:
        default_scope = _ask_scope_doc_id if _ask_scope_doc_id in scope_options else "all"
        scope_keys = list(scope_options.keys())
        default_idx = scope_keys.index(default_scope) if default_scope in scope_keys else 0
        selected_scope = st.selectbox(t("ask.scope"), options=scope_keys, format_func=lambda k: scope_options[k], index=default_idx)

    if st.button(t("ask.search_btn"), type="primary"):
        if not query.strip():
            st.error(t("ask.error_empty"))
        else:
            results = search_knowledge_base(query.strip(), top_k=5)
            # Filter by scope if not "all"
            if selected_scope != "all":
                results = [r for r in results if r.get("document", {}).get("id") == selected_scope]

            if not results:
                st.info(t("ask.no_results"))
            else:
                # Grounded answer synthesis — structured, not passage dump
                with st.container(border=True):
                    st.markdown(f"**{t('ask.grounded_answer')}**")
            
                    # Build synthesis from retrieved passages
                    passages = []
                    citations = []
                    page_refs = []
                    for idx, item in enumerate(results, 1):
                        chunk_text = item["chunk"].get("chunk_text", "")
                        citation = item.get("citation", "Unknown source")
                        score = item.get("score", 0)
                        if chunk_text:
                            passages.append(chunk_text)
                            citations.append((idx, citation, score))
                            # Extract page reference from citation
                            page_match = re.search(r'Page\s+(\d+)', citation)
                            if page_match:
                                page_refs.append(page_match.group(1))
            
                    if len(passages) == 0:
                        st.markdown(f"*{t('ask.insufficient')}*")
                    else:
                        # Extract structured data points from all passages
                        data_points = []
                        for p in passages[:3]:
                            # Find numbers with units (expanded patterns)
                            nums_with_units = re.findall(
                                r'(\d+(?:/\d+)?\s*(?:\(\d+\s*(?:\u514b|g)\))?|\d+(?:[,.]\d+)?\s*(?:%|g|mg|ml|cal|kcal|mmHg|\u514b|\u6beb\u514b|\u5206\u949f|\u5c0f\u65f6|\u5929|\u5468|\u6708|\u5e74|\u4e07|\u4ebf|\u676f|\u76ce\u53f8|\u5361\u8def\u91cc|\u5361|cups?|ounces?|grams?|milligrams?|minutes?|hours?|calories?))',
                                p, re.IGNORECASE
                            )
                            data_points.extend(nums_with_units[:6])
            
                        # Also extract key-value pairs from passages (e.g., "Total Fat: 8g")
                        kv_pairs = []
                        for p in passages[:3]:
                            kvs = re.findall(
                                r'([A-Za-z\u4e00-\u9fff\s]{2,25})\s*[:\uff1a]\s*(\d+(?:[,.]\d+)?\s*(?:%|g|mg|ml|cal|kcal|\u514b|\u6beb\u514b|\u5206\u949f|\u5c0f\u65f6|\u5929|\u5468|\u6708|\u5e74|\u676f|\u5361\u8def\u91cc|cups?|grams?|minutes?|hours?|calories?)?)',
                                p, re.IGNORECASE
                            )
                            kv_pairs.extend(kvs[:4])
            
                        # Build concise answer: topic sentence + key data + recommendation
                        all_text = " ".join(passages[:2])
                        sentences = re.split(r'(?<=[.!?\u3002\uff01\uff1f])\s+', all_text)
                        # Take meaningful sentences (not too short, filter noise)
                        _noise_starts = ('Copyright', 'Source:', '\u6765\u6e90', 'All rights', 'http', 'www.')
                        meaningful = [s.strip() for s in sentences
                                      if len(s.strip()) > 15
                                      and not s.strip().startswith(_noise_starts)
                                      and len(s.strip()) < 300]
            
                        # Structured answer
                        if get_locale() == "zh-CN":
                            answer_parts = []
                            if meaningful:
                                answer_parts.append(meaningful[0])
                                if len(meaningful) > 1:
                                    answer_parts.append(meaningful[1])
                            if kv_pairs:
                                kv_str = "  \u00b7  ".join(f"{k.strip()}: {v.strip()}" for k, v in kv_pairs[:6])
                                answer_parts.append(f"\n\n**\u5173\u952e\u6570\u636e\uff1a**{kv_str}")
                            elif data_points:
                                answer_parts.append(f"\n\n**\u5173\u952e\u6570\u636e\uff1a**{'  \u00b7  '.join(data_points[:6])}")
                            st.markdown("\n".join(answer_parts))
                        else:
                            answer_parts = []
                            if meaningful:
                                answer_parts.append(meaningful[0])
                                if len(meaningful) > 1:
                                    answer_parts.append(meaningful[1])
                            if kv_pairs:
                                kv_str = "  \u00b7  ".join(f"{k.strip()}: {v.strip()}" for k, v in kv_pairs[:6])
                                answer_parts.append(f"\n\n**Key data:** {kv_str}")
                            elif data_points:
                                answer_parts.append(f"\n\n**Key data:** {'  \u00b7  '.join(data_points[:6])}")
                            st.markdown("\n".join(answer_parts))
            
                        # Source citation with page numbers
                        if citations:
                            cite_parts = [f"[{n}] {_escape(c)}" for n, c, _ in citations[:3]]
                            st.markdown(
                                f'<div class="rb-meta-line">{t("common.source")}: {" \u00b7 ".join(cite_parts)}</div>',
                                unsafe_allow_html=True,
                            )
                        if page_refs:
                            unique_pages = list(dict.fromkeys(page_refs))[:3]
                            page_str = ", ".join(f"P{p}" for p in unique_pages)
                            st.markdown(
                                f'<div class="rb-meta-line">\u6765\u81ea\u7b2c {page_str}</div>' if get_locale() == "zh-CN" else
                                f'<div class="rb-meta-line">From {page_str}</div>',
                                unsafe_allow_html=True,
                            )
            
                    # Transparency footer
                    mode_client = create_llm_client()
                    mode_text = t("ask.mode_deterministic") if "Local" in mode_client.mode_label else t("ask.mode_ai")
                    evidence_note = t("ask.evidence_limited") if len(results) < 3 else ""
                    st.markdown(
                        f'<div class="rb-meta-line">'
                        f'{t("ask.passage_count", n=len(results))}. {t("ask.mode_label")}: {mode_text}. '
                        f'{evidence_note}'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
            
                # Evidence passages (collapsible, default closed)
                with st.expander(t("ask.view_evidence", n=len(results))):
                    for idx, item in enumerate(results, 1):
                        chunk_text = item["chunk"].get("chunk_text", "")
                        citation = item.get("citation", "Unknown source")
                        score = item.get("score", 0)
                        st.markdown(f"**[{idx}]** {_escape(chunk_text[:500])}{'...' if len(chunk_text) > 500 else ''}")
                        st.markdown(f'<div class="rb-meta-line">{t("common.citation")}: {_escape(citation)} \u00b7 {t("common.relevance")}: {score:.1f}</div>', unsafe_allow_html=True)
                        st.markdown("---")

with tab_library:
    cards = sorted(load_cards(), key=lambda card: card.get("created_at", ""), reverse=True)
    total = len(cards)
    insight_count = sum(1 for card in cards if card.get("card_type") == "Insight Pack")
    use_count = sum(1 for card in cards if card.get("card_type") == "Use Card")
    clue_count = sum(1 for card in cards if card.get("card_type") == "Clue Card")
    archived_count = sum(1 for card in cards if card.get("card_type") == "Archived")
    # Any card whose type is none of the above — kept separate so the
    # breakdown below always reconciles with the total.
    other_count = total - (insight_count + use_count + clue_count + archived_count)
    clear_count = sum(1 for card in cards if card.get("fog_index", {}).get("level") == "Clear")
    foggy_count = sum(1 for card in cards if card.get("fog_index", {}).get("level") == "Foggy")
    very_foggy_count = sum(1 for card in cards if card.get("fog_index", {}).get("level") == "Very Foggy")

    with st.container(border=True):
        st.markdown(f'<div class="rb-section-heading">{t("memory.title")}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="rb-section-subtext">{t("memory.subtitle")}</div>', unsafe_allow_html=True)
        stats = [
            _chip(f"{t('memory.total')} {total} {t('memory.cards_unit')}", "blue"),
            _chip(f"Insight Pack {insight_count}", "violet"),
            _chip(f"Use Card {use_count}", "teal"),
            _chip(f"Clue Card {clue_count}", "amber"),
            _chip(f"{t('memory.archived')} {archived_count}", "slate"),
        ]
        if other_count > 0:
            stats.append(_chip(f"{t('memory.other')} {other_count}", "slate"))
        stats += [
            _chip(f"{t('fog.clear')} {clear_count}", "teal"),
            _chip(f"{t('fog.foggy')} {foggy_count}", "amber"),
            _chip(f"{t('fog.very_foggy')} {very_foggy_count}", "rose"),
        ]
        st.markdown("".join(stats), unsafe_allow_html=True)
        search_query = st.text_input(t("memory.search"), placeholder=t("memory.search_placeholder"))

    # Top-level library filter: distinguish Memory Cards from Activation Units
    _lib_filter_options = [t("lib.filter_all"), t("lib.filter_cards"), t("lib.filter_au"), t("lib.filter_draft"), t("lib.filter_review")]
    lib_filter = st.segmented_control(
        t("nav.memory"),
        _lib_filter_options,
        default=t("lib.filter_all"),
        key="lib_top_filter",
    )
    _show_memory_cards = lib_filter in (t("lib.filter_all"), t("lib.filter_cards"))
    _show_au = lib_filter in (t("lib.filter_all"), t("lib.filter_au"), t("lib.filter_draft"), t("lib.filter_review"))

    filtered_cards = _search_cards(cards, search_query) if _show_memory_cards else []
    if not filtered_cards and _show_memory_cards:
        st.info(t("memory.no_match") if cards else t("memory.no_cards"))
    else:
        for idx, card in enumerate(filtered_cards):
            with st.container(border=True):
                st.markdown(f"### {_escape(_preview(card.get('knowledge_seed', ''), 96))}")
                _render_memory_card(card, show_full=False, key_prefix="library_", render_index=idx)
                col1, col2 = st.columns([1, 1])
                with col1:
                    with st.expander(t("memory.edit_card")):
                        edit_core = st.text_area(
                            t("memory.core_insight"),
                            value=card.get("core_insight", ""),
                            key=f"edit_core_{card['id']}",
                        )
                        edit_tags = st.text_input(
                            t("memory.topic_tags"),
                            value=", ".join(card.get("topic_tags", [])),
                            key=f"edit_tags_{card['id']}",
                        )
                        edit_source = st.text_input(
                            t("memory.source"),
                            value=card.get("source", ""),
                            key=f"edit_source_{card['id']}",
                        )
                        if st.button(t("memory.save_changes"), key=f"save_{card['id']}"):
                            updates = {"core_insight": edit_core}
                            if edit_tags.strip():
                                updates["topic_tags"] = [tag.strip() for tag in edit_tags.split(",") if tag.strip()]
                            else:
                                updates["topic_tags"] = []
                            updates["source"] = edit_source
                            update_card(card["id"], updates)
                            st.success(t("memory.updated"))
                            st.rerun()
                with col2:
                    if st.button(t("memory.delete_confirm"), key=f"delete_{card['id']}"):
                        delete_card(card["id"])
                        if st.session_state.get("last_generated_card", {}).get("id") == card["id"]:
                            st.session_state.pop("last_generated_card", None)
                        st.rerun()

    # ── Activation Units section ──────────────────────────────────────────
    if _show_au:
        st.markdown("<div class='rb-divider'></div>", unsafe_allow_html=True)
        all_units = load_units()
        active_units = [u for u in all_units if u.get("status") == "active"]
        draft_units = [u for u in all_units if u.get("status") == "draft"]
        # "Needs Review": activated but never used by a real task, or has false triggers
        review_units = [
            u for u in all_units
            if u.get("status") == "active"
            and (
                u.get("usage", {}).get("activation_count", 0) == 0
                or u.get("usage", {}).get("false_trigger_count", 0) > 0
            )
        ]

        with st.container(border=True):
            st.markdown(f'<div class="rb-section-heading">{t("au.title")}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="rb-section-subtext">{t("au.subtitle")}</div>', unsafe_allow_html=True)
            au_stats = [
                _chip(f"{t('au.active')} {len(active_units)}", "teal"),
                _chip(f"{t('au.draft')} {len(draft_units)}", "amber"),
                _chip(f"{t('lib.filter_review')} {len(review_units)}", "rose"),
            ]
            st.markdown("".join(au_stats), unsafe_allow_html=True)

        if not all_units:
            st.info(t("au.no_units"))
        else:
            # Sub-filter driven by the top-level library filter
            if lib_filter == t("lib.filter_draft"):
                display_units = draft_units
            elif lib_filter == t("lib.filter_review"):
                display_units = review_units
            else:  # filter_all or filter_au
                display_units = all_units

            if not display_units:
                st.info(t("au.no_units"))
            for unit in display_units:
                with st.container(border=True):
                    _render_au_library_card(unit)


def _fill_demo_task(task_text: str) -> None:
    """on_click callback: pre-fill the activate task box.

    Runs before the script re-executes, so it may safely set the widget's
    session_state key (setting it after the widget is instantiated raises).
    """
    st.session_state["activate_task_input"] = task_text


with tab_activate:
    with st.container(border=True):
        st.markdown(f'<div class="rb-section-heading">{t("activate.title")}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="rb-section-subtext">{t("activate.subtitle")}</div>', unsafe_allow_html=True)
        current_task = st.text_area(
            t("activate.task"),
            placeholder=t("activate.task_placeholder"),
            height=120,
            label_visibility="collapsed",
            key="activate_task_input",
        )

        # Quick-fill demo tasks (construction firm AI adoption roadmap)
        dcol1, dcol2, _ = st.columns([1, 1, 2])
        with dcol1:
            st.button(
                f"📋 {t('act.demo_task')} · 中文",
                key="demo_task_zh",
                on_click=_fill_demo_task,
                args=(DEMO_TASK_ZH,),
            )
        with dcol2:
            st.button(
                f"📋 {t('act.demo_task')} · English",
                key="demo_task_en",
                on_click=_fill_demo_task,
                args=(DEMO_TASK_EN,),
            )

        if st.button(t("activate.activate_btn"), type="primary"):
            if not current_task.strip():
                st.error(t("activate.error_empty"))
            else:
                # Always clear the previous activation result
                st.session_state.pop("au_activation", None)

                # Hard gate for vague tasks
                if is_vague_task(current_task):
                    st.warning(t("activate.need_more_info"))
                    st.stop()

                active_au = list_active_units()
                decisions = evaluate_triggers(current_task, active_au) if active_au else []
                triggered = [
                    (d, next((u for u in active_au if u.get("id") == d.unit_id), None))
                    for d in decisions
                    if d.decision in ("trigger", "maybe") and d.score > 0
                ]
                triggered = [(d, u) for d, u in triggered if u is not None]

                deliverable = generate_au_deliverable(
                    current_task,
                    [u for _, u in triggered],
                    [d for d, _ in triggered],
                )
                # Record the real activation event: activation_count increments
                # here (once per activation), never on feedback. The returned
                # event id links any later feedback to this activation.
                activation_event_id = (
                    record_activation([u["id"] for _, u in triggered], task=current_task)
                    if triggered else ""
                )
                st.session_state["au_activation"] = {
                    "task": current_task,
                    "triggered": triggered,
                    "deliverable": deliverable,
                    "activation_event_id": activation_event_id,
                }
                st.rerun()

    au_state = st.session_state.get("au_activation")
    if au_state:
        task = au_state["task"]
        triggered = au_state["triggered"]  # list of (TriggerDecision, unit)
        deliverable = au_state["deliverable"]  # AUDeliverable

        # ── 1. Task understanding ────────────────────────────────────────
        understanding = parse_task_understanding(task)
        with st.container(border=True):
            st.markdown(f'<div class="rb-section-heading">1️⃣ {t("act.task_understanding")}</div>', unsafe_allow_html=True)
            tu_c1, tu_c2, tu_c3 = st.columns(3)
            with tu_c1:
                st.markdown(f"**{t('act.goal')}**")
                st.markdown(_escape(understanding.get("goal", "")) or "—")
            with tu_c2:
                st.markdown(f"**{t('act.audience')}**")
                st.markdown(_escape(understanding.get("audience", "")) or "—")
            with tu_c3:
                st.markdown(f"**{t('act.focus')}**")
                focus_items = understanding.get("focus", [])
                st.markdown(", ".join(_escape(f) for f in focus_items) if focus_items else "—")

        # ── 2. Selected methods (why + matched signals + missing context) ─
        with st.container(border=True):
            st.markdown(f'<div class="rb-section-heading">2️⃣ {t("act.selected_methods")}</div>', unsafe_allow_html=True)
            if not triggered:
                st.info(t("act.no_method_note"))
            for td, unit in triggered:
                tone = "teal" if td.decision == "trigger" else "amber"
                st.markdown(f"#### {_escape(unit.get('name', ''))} {_chip(td.decision, tone)}", unsafe_allow_html=True)
                if td.reason:
                    st.markdown(f"**{t('act.why_selected')}:** {_escape(td.reason)}")
                if td.matched_signals:
                    st.markdown(f"**{t('act.matched_signals')}:**")
                    for sig in td.matched_signals:
                        st.markdown(f"- {_escape(str(sig))}")
                if td.missing_context:
                    st.markdown(f"**{t('act.missing_context')}:**")
                    for mc in td.missing_context:
                        st.markdown(f"- {_escape(str(mc))}")
                if td.clarification_question:
                    st.warning(f"{t('activate.clarification_needed')}: {_escape(td.clarification_question)}")

        # ── 3. Ready-to-use deliverable ──────────────────────────────────
        with st.container(border=True):
            st.markdown(f'<div class="rb-section-heading">3️⃣ {t("act.deliverable")}</div>', unsafe_allow_html=True)
            if deliverable.final_deliverable:
                st.markdown(deliverable.final_deliverable)
            elif deliverable.revised_output:
                st.markdown(deliverable.revised_output)
            else:
                st.info(t("act.no_method_note"))

        # ── 4. Quality-check results ─────────────────────────────────────
        if deliverable.quality_check_results:
            with st.container(border=True):
                st.markdown(f'<div class="rb-section-heading">4️⃣ {t("act.qc_results")}</div>', unsafe_allow_html=True)
                for qc in deliverable.quality_check_results:
                    icon = "✅" if qc.get("passed") else "⚠️"
                    st.markdown(f"{icon} {_escape(qc.get('check', ''))} · {_escape(qc.get('unit', ''))}")

        # ── 5. Knowledge boundaries (supported / unsupported / add) ──────
        with st.container(border=True):
            st.markdown(f'<div class="rb-section-heading">5️⃣ {t("act.boundaries")}</div>', unsafe_allow_html=True)
            kb_c1, kb_c2, kb_c3 = st.columns(3)
            with kb_c1:
                st.markdown(f"**✅ {t('act.supported')}**")
                if deliverable.supported_sections:
                    for sec in deliverable.supported_sections:
                        st.markdown(f"- {_escape(sec.get('unit_name', ''))}")
                else:
                    st.markdown("—")
            with kb_c2:
                st.markdown(f"**⚠️ {t('act.unsupported')}**")
                if deliverable.unsupported_sections:
                    for us in deliverable.unsupported_sections:
                        st.markdown(f"- {_escape(us)}")
                else:
                    st.markdown("—")
            with kb_c3:
                st.markdown(f"**➕ {t('act.suggest_add')}**")
                if deliverable.materials_needed:
                    for m in deliverable.materials_needed:
                        st.markdown(f"- {_escape(m)}")
                else:
                    st.markdown("—")

        # ── 6. Sources and evidence ──────────────────────────────────────
        with st.container(border=True):
            st.markdown(f'<div class="rb-section-heading">6️⃣ {t("act.sources")}</div>', unsafe_allow_html=True)
            shown_source = False
            for td, unit in triggered:
                src = _unit_source_page(unit)
                spans = unit.get("evidence_spans", [])
                if src or spans:
                    shown_source = True
                    st.markdown(f"**{_escape(unit.get('name', ''))}**")
                    if src:
                        st.markdown(f'<div class="rb-meta-line">{t("review.source_label")}: {_escape(src)}</div>', unsafe_allow_html=True)
                    for span in spans[:2]:
                        st.markdown(f"> {_escape(span.get('text', '')[:200])}")
            if not shown_source:
                st.markdown("—")

        # ── 7. Feedback (overall output vs. a specific unit) ─────────────
        with st.container(border=True):
            st.markdown(f'<div class="rb-section-heading">7️⃣ {t("act.feedback_title")}</div>', unsafe_allow_html=True)
            if triggered:
                scope_options = [t("act.feedback_overall")] + [u.get("name", "") for _, u in triggered]
            else:
                scope_options = [t("act.feedback_overall")]
            fb_scope = st.selectbox(t("act.feedback_scope"), scope_options, key="fb_scope_select")
            fb_cols = st.columns(5)
            fb_labels = [t("fb.useful"), t("fb.not_useful"), t("fb.false_trigger"), t("fb.missing_context"), t("fb.expression_issue")]
            fb_types = ["useful", "not_useful", "false_trigger", "missing_context", "expression_issue"]
            fb_clicked = None
            for col, label, fb_type in zip(fb_cols, fb_labels, fb_types):
                with col:
                    if st.button(label, key=f"fb_{fb_type}"):
                        fb_clicked = fb_type
            if fb_clicked:
                event_id = au_state.get("activation_event_id", "")
                if fb_scope == t("act.feedback_overall"):
                    # Overall output: record against every triggered unit
                    for td, unit in triggered:
                        record_feedback(unit["id"], fb_clicked, task=task, activation_event_id=event_id)
                else:
                    # A specific unit only
                    target = next((u for _, u in triggered if u.get("name", "") == fb_scope), None)
                    if target:
                        record_feedback(target["id"], fb_clicked, task=task, activation_event_id=event_id)
                st.session_state["_fb_just_recorded"] = True
                st.rerun()

        if st.session_state.pop("_fb_just_recorded", False):
            st.success(t("fb.recorded"))

# Footer
st.markdown("---")
st.markdown(f'<p class="muted" style="text-align: center; margin-top: 2rem;">{t("footer.tagline")}</p>', unsafe_allow_html=True)