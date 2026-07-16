"""RecallBite knowledge activation workspace."""

from __future__ import annotations

import html
import re
from datetime import datetime

import streamlit as st

from src.activation import generate_activation_output, generate_apply_suggestion
from src.generator import generate_card, ingest_material
from src.i18n import t, set_locale, get_locale
from src.knowledge_base import search_knowledge_base
from src.llm_client import create_llm_client
from src.parsers.document_parser import parse_document
from src.parsers.url_parser import is_valid_url, parse_url
from src.retrieval import retrieve_relevant_cards
from src.storage import delete_card, load_cards, update_card


st.set_page_config(page_title="RecallBite", page_icon="🍞", layout="wide", initial_sidebar_state="collapsed")


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
    settings_col1, settings_col2, settings_col3 = st.columns(3)
    with settings_col1:
        interface_lang = st.selectbox(
            t("settings.interface_lang"),
            ["\u4e2d\u6587", "English"],
            index=0 if get_locale() == "zh-CN" else 1,
            key="interface_lang_selector",
        )
        new_locale = "zh-CN" if interface_lang == "\u4e2d\u6587" else "en"
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
        output_lang_global = st.selectbox(
            t("settings.output_lang"),
            [t("add.lang_auto"), t("add.lang_zh"), t("add.lang_en"), t("add.lang_bilingual")],
            index=0,
            key="global_output_lang",
        )

# Inject theme via JavaScript
_theme_map = {t("theme.system"): "system", t("theme.light"): "light", t("theme.dark"): "dark"}
_theme_value = _theme_map.get(theme_choice, "system")
st.markdown(
    f"""<script>
    (function() {{
        var theme = '{_theme_value}';
        var root = document.documentElement;
        if (theme === 'system') {{
            var prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            root.setAttribute('data-theme', prefersDark ? 'dark' : 'light');
        }} else {{
            root.setAttribute('data-theme', theme);
        }}
    }})();
    </script>""",
    unsafe_allow_html=True,
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

            if st.button(t("add.submit"), type="primary"):
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
                        )
                        st.session_state["last_generated_card"] = new_card
                        meta = new_card.get("_analysis_meta", {})
                        if meta.get("fallback"):
                            st.warning(f"{t('add.success_saved')} {new_card['card_type']} · {new_card['fog_index']['level']} · {t('add.fallback_reason')}: {meta.get('reason', 'AI unavailable')}")
                        else:
                            st.success(f"{t('add.success_saved')} {new_card['card_type']} · {new_card['fog_index']['level']} · {t('add.mode_label')}: {meta.get('mode', 'unknown')}")
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
    clear_count = sum(1 for card in cards if card.get("fog_index", {}).get("level") == "Clear")
    foggy_count = sum(1 for card in cards if card.get("fog_index", {}).get("level") == "Foggy")
    very_foggy_count = sum(1 for card in cards if card.get("fog_index", {}).get("level") == "Very Foggy")

    with st.container(border=True):
        st.markdown(f'<div class="rb-section-heading">{t("memory.title")}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="rb-section-subtext">{t("memory.subtitle")}</div>', unsafe_allow_html=True)
        stats = [
            _chip(f"{t('memory.total')} {total}", "blue"),
            _chip(f"Insight Pack {insight_count}", "violet"),
            _chip(f"Use Card {use_count}", "teal"),
            _chip(f"Clue Card {clue_count}", "amber"),
            _chip(f"{t('fog.clear')} {clear_count}", "teal"),
            _chip(f"{t('fog.foggy')} {foggy_count}", "amber"),
            _chip(f"{t('fog.very_foggy')} {very_foggy_count}", "rose"),
        ]
        st.markdown("".join(stats), unsafe_allow_html=True)
        search_query = st.text_input(t("memory.search"), placeholder=t("memory.search_placeholder"))

    filtered_cards = _search_cards(cards, search_query)
    if not filtered_cards:
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


with tab_activate:
    with st.container(border=True):
        st.markdown(f'<div class="rb-section-heading">{t("activate.title")}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="rb-section-subtext">{t("activate.subtitle")}</div>', unsafe_allow_html=True)
        current_task = st.text_area(
            t("activate.task"),
            placeholder=t("activate.task_placeholder"),
            height=120,
            label_visibility="collapsed",
        )

        with st.expander(t("activate.hint_label")):
            memory_hint = st.text_area(
                t("activate.memory_hint"),
                placeholder=t("activate.hint_placeholder"),
                height=70,
                label_visibility="collapsed",
            )
            save_hint = st.checkbox(t("activate.save_hint"))
        
        if st.button(t("activate.activate_btn"), type="primary"):
            if not current_task.strip():
                st.error(t("activate.error_empty"))
            else:
                # ALWAYS clear previous activation when a new task is submitted
                st.session_state.pop("last_activation", None)

                if memory_hint.strip() and save_hint:
                    try:
                        hinted_card = ingest_material(
                            knowledge_seed=memory_hint,
                            source_type="Hint",
                            topic_tags_text="",
                            source="",
                            input_type="thought",
                        )
                        st.success(t("activate.hint_saved"))
                    except Exception as exc:
                        st.warning(f"{t('activate.hint_failed')} {exc}")
        
                cards = load_cards()
                if not cards:
                    st.warning(t("activate.no_cards"))
                else:
                    # HARD GATE: Check for vague tasks BEFORE retrieval
                    task_lower = current_task.lower().strip()
                    is_vague = (
                        len(task_lower) < 10  # Too short
                        or task_lower in {
                            "\u6211\u8981\u6295\u6807", "\u5199proposal", "\u5199\u62a5\u544a",
                            "\u51c6\u5907meeting", "i need proposal", "write report",
                            "prepare meeting", "\u5199\u6587\u7ae0", "write article",
                        }
                    )
        
                    if is_vague:
                        # HARD STOP: Clear old activation, show clarification
                        st.session_state.pop("last_activation", None)
                        st.warning(t("activate.need_more_info"))
                        st.markdown(f"**{t('activate.clarify_topic')}**")
        
                        # Show available topics from cards
                        all_tags: set[str] = set()
                        for card in cards:
                            all_tags.update(card.get("topic_tags", []))
                        if all_tags:
                            st.markdown(f"**{t('activate.related_topics')}**")
                            tag_chips = [_chip(tag, "slate") for tag in sorted(all_tags)[:12]]
                            st.markdown("".join(tag_chips), unsafe_allow_html=True)
                        st.stop()
        
                    results = retrieve_relevant_cards(current_task, cards, top_k=3)
        
                    # If all scores are 0, no topic match
                    if results and all(score == 0 for _, score in results):
                        # HARD STOP: Clear old activation, show clarification
                        st.session_state.pop("last_activation", None)
                        st.warning(t("activate.need_more_info"))
                        st.markdown(f"**{t('activate.clarify_topic')}**")
        
                        all_tags = set()
                        for card in cards:
                            all_tags.update(card.get("topic_tags", []))
                        if all_tags:
                            st.markdown(f"**{t('activate.related_topics')}**")
                            tag_chips = [_chip(tag, "slate") for tag in sorted(all_tags)[:12]]
                            st.markdown("".join(tag_chips), unsafe_allow_html=True)
                        st.stop()
        
                    # Valid match: store activation
                    st.session_state["last_activation"] = {"task": current_task, "results": results}

    activation_state = st.session_state.get("last_activation")
    if activation_state:
        task = activation_state["task"]
        results = activation_state["results"]
        with st.container(border=True):
            st.markdown(f'<div class="rb-section-heading">{t("activate.knowledge_brief")}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="rb-section-subtext">{t("activate.current_task_label")}{_escape(task)}</div>', unsafe_allow_html=True)

        if results:
            # Multi-card synthesis: show combined output first
            result_dicts = [
                {"card": card, "score": score, "match_strength": "strong" if score >= 5 else "weak" if score > 0 else "fallback"}
                for card, score in results
            ]
            synthesis = generate_activation_output(task, result_dicts)

            if synthesis.get("ready_to_use_output"):
                with st.container(border=True):
                    st.markdown(f"**{t('activate.ready_output')}**")
                    meta = synthesis.get("_analysis_meta", {})
                    if meta.get("fallback"):
                        st.warning(f"{t('activate.fallback_mode')}{meta.get('reason', 'AI unavailable')}")
                    elif meta.get("mode"):
                        st.info(f"{t('activate.analysis_mode')}{meta['mode']}")
                    st.text_area(
                        t("activate.synthesis_label"),
                        value=synthesis["ready_to_use_output"],
                        height=120,
                        label_visibility="collapsed",
                        key="activation_synthesis_output",
                    )
                    if synthesis.get("why_these_memories"):
                        st.markdown(f'<div class="rb-meta-line">{_escape(synthesis["why_these_memories"])}</div>', unsafe_allow_html=True)
                    if synthesis.get("confidence_note"):
                        st.markdown(f'<div class="rb-meta-line">{_escape(synthesis["confidence_note"])}</div>', unsafe_allow_html=True)

            if synthesis.get("questions_to_ask"):
                with st.expander(t("activate.questions_to_ask")):
                    for q in synthesis["questions_to_ask"]:
                        st.markdown(f"- {_escape(q)}")

            if synthesis.get("source_notes"):
                with st.expander(t("activate.source_notes")):
                    for note in synthesis["source_notes"]:
                        st.markdown(f"- {_escape(note)}")

            # Individual cards below
            st.markdown("<div class='rb-divider'></div>", unsafe_allow_html=True)
            st.markdown(f"**{t('activate.individual_cards')}**")
            for index, (card, score) in enumerate(results, 1):
                suggestion = generate_apply_suggestion(task, card, score)
                _render_activation_card(card, score, suggestion, index)
        else:
            st.info(t("activate.no_results"))

# Footer
st.markdown("---")
st.markdown(f'<p class="muted" style="text-align: center; margin-top: 2rem;">{t("footer.tagline")}</p>', unsafe_allow_html=True)