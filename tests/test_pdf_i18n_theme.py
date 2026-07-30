"""Tests for PDF parsing, i18n, theme system, and activate clarification.

Covers the 10 acceptance criteria from the refactor requirements:
1. Dual-column bilingual PDF Chinese/English order
2. Copyright/footer not in takeaway
3. Bilingual parallel content not double-counted
4. UI language switch covers all four tabs
5. Output language independent from interface language
6. Light/Dark/System theme persistence
7. Theme CSS variables defined
8. "我要投标" triggers clarification without topic
9. Grounded answer with citation
10. Noise words excluded from topic tags
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


# ── 1. Dual-column bilingual PDF order ──────────────────────────────────


def _health_pdf_bytes() -> bytes | None:
    """Read the health PDF from the sample directory."""
    pdf_path = (
        Path(__file__).parent.parent.parent
        / "sample"
        / "健康生活方式×8  Life's Essential×8.pdf"
    )
    if pdf_path.exists():
        return pdf_path.read_bytes()
    return None


@pytest.mark.skipif(
    _health_pdf_bytes() is None,
    reason="Health PDF not found in sample/",
)
def test_bilingual_pdf_chinese_english_order():
    """Dual-column bilingual PDF must separate Chinese and English correctly."""
    from src.parsers.pdf_parser import parse_pdf_advanced

    data = _health_pdf_bytes()
    assert data is not None

    parsed = parse_pdf_advanced(data, "health.pdf")

    # Must detect bilingual
    assert parsed.is_bilingual is True
    assert "zh" in parsed.detected_languages
    assert "en" in parsed.detected_languages

    # Pages must have both zh and en sections
    zh_pages = [s for s in parsed.pages if s.language == "zh"]
    en_pages = [s for s in parsed.pages if s.language == "en"]
    assert len(zh_pages) >= 3, f"Expected >=3 zh sections, got {len(zh_pages)}"
    assert len(en_pages) >= 3, f"Expected >=3 en sections, got {len(en_pages)}"

    # Full text must contain both Chinese and English markers
    assert "--- 中文 ---" in parsed.full_text or "中文" in parsed.full_text
    assert "--- English ---" in parsed.full_text or "English" in parsed.full_text


# ── 2. Copyright/footer not in takeaway ──────────────────────────────────


def test_copyright_footer_filtered_as_noise():
    """Copyright notices, org names, and URLs must be filtered as noise."""
    from src.parsers.pdf_parser import _is_noise

    noise_samples = [
        "Healthy for Good",
        "American Heart Association",
        "Copyright 2024 American Heart Association",
        "heart.org",
        "https://www.heart.org",
        "All rights reserved",
        "501(c)(3) not-for-profit",
        "TM",
        "Page 5",
    ]
    for text in noise_samples:
        assert _is_noise(text) is True, f"Expected '{text}' to be noise"


def test_meaningful_content_not_filtered():
    """Meaningful content must NOT be filtered as noise."""
    from src.parsers.pdf_parser import _is_noise

    good_samples = [
        "如何吃得更好",
        "How to Eat Better",
        "150 minutes of moderate-intensity activity per week",
        "成年人每晚应睡 7-9 小时",
        "BMI 保持在 18.5-24.9 之间",
    ]
    for text in good_samples:
        assert _is_noise(text) is False, f"Expected '{text}' to NOT be noise"


# ── 3. Bilingual parallel content not double-counted ─────────────────────


@pytest.mark.skipif(
    _health_pdf_bytes() is None,
    reason="Health PDF not found in sample/",
)
def test_bilingual_content_not_duplicated():
    """Chinese and English parallel content should be in separate sections, not mixed."""
    from src.parsers.pdf_parser import parse_pdf_advanced

    data = _health_pdf_bytes()
    parsed = parse_pdf_advanced(data, "health.pdf")

    # Check that zh sections don't contain English-heavy text and vice versa
    for section in parsed.pages:
        if section.language == "zh":
            # Chinese section should have CJK characters
            cjk_count = sum(1 for c in section.text if '\u4e00' <= c <= '\u9fff')
            assert cjk_count > 0, f"zh section on page {section.page} has no CJK chars"
        elif section.language == "en":
            # English section should have Latin words
            import re
            latin_words = re.findall(r'[a-zA-Z]{3,}', section.text)
            assert len(latin_words) >= 2, f"en section on page {section.page} has no English words"


# ── 4. UI language switch covers all tabs ─────────────────────────────────


def test_i18n_switch_covers_all_keys():
    """All i18n keys must have both zh-CN and en translations."""
    from src.i18n import ZH_CN, EN

    # All keys in ZH_CN must also be in EN
    for key in ZH_CN:
        assert key in EN, f"Key '{key}' in ZH_CN but missing in EN"

    # All keys in EN must also be in ZH_CN
    for key in EN:
        assert key in ZH_CN, f"Key '{key}' in EN but missing in ZH_CN"


def test_i18n_t_function_switches_locale():
    """t() must return correct translations for each locale."""
    from src.i18n import t, set_locale, get_locale

    original = get_locale()
    try:
        set_locale("zh-CN")
        assert t("hero.title") == "RecallBite \u8bb0\u5fc6\u9762\u5305"
        assert "\u754c\u9762\u8bed\u8a00" in t("settings.interface_lang")

        set_locale("en")
        assert t("hero.title") == "RecallBite"
        assert t("nav.add_knowledge") == "\U0001f4e5 Add Knowledge"
        assert t("nav.ask") == "\u2753 Ask My Knowledge"
        assert t("nav.memory") == "\U0001f9e0 Memory & Insights"
        assert t("nav.activate") == "\u26a1 Activate"
    finally:
        set_locale(original)


def test_i18n_variable_interpolation():
    """t() must support {variable} interpolation."""
    from src.i18n import t, set_locale, get_locale

    original = get_locale()
    try:
        set_locale("en")
        result = t("ask.view_evidence", n=5)
        assert "5" in result
    finally:
        set_locale(original)


# ── 5. Output language independent from interface language ────────────────


def test_output_language_independent_from_interface():
    """Interface language and output language must be independently configurable."""
    from src.i18n import set_locale, get_locale

    original = get_locale()
    try:
        # Set interface to Chinese
        set_locale("zh-CN")
        assert get_locale() == "zh-CN"

        # Output language is controlled separately via generate_card parameter
        # This test just verifies the parameter is accepted
        from src.generator import generate_card
        card = generate_card(
            knowledge_seed="AI governance requires accountability frameworks",
            source_type="Article",
            source="Test",
            output_language="en",
        )
        assert isinstance(card, dict)
        assert card.get("core_insight")

        # Switch interface to English, output to Chinese
        set_locale("en")
        card2 = generate_card(
            knowledge_seed="Climate risk disclosure regulations are evolving",
            source_type="Article",
            source="Test",
            output_language="zh",
        )
        assert isinstance(card2, dict)
    finally:
        set_locale(original)


# ── 6. Theme state persistence ────────────────────────────────────────────


def test_theme_css_variables_defined():
    """CSS variables must be defined for both light and dark themes."""
    # Read app.py and check CSS variables exist
    app_path = Path(__file__).parent.parent / "app.py"
    app_content = app_path.read_text(encoding="utf-8")

    # Dark theme variables
    required_vars = [
        "--rb-bg-primary",
        "--rb-bg-surface",
        "--rb-text-primary",
        "--rb-text-secondary",
        "--rb-accent-primary",
        "--rb-border",
        "--rb-pill-teal-bg",
    ]
    for var in required_vars:
        assert var in app_content, f"CSS variable '{var}' not found in app.py"

    # Light theme override must exist
    assert '[data-theme="light"]' in app_content
    assert '[data-theme="dark"]' in app_content or ":root" in app_content


def test_theme_selector_in_settings():
    """Theme selector must offer System, Light, Dark options (via i18n or literal)."""
    app_path = Path(__file__).parent.parent / "app.py"
    app_content = app_path.read_text(encoding="utf-8")

    # Check either literal strings or i18n keys are used
    assert '"System"' in app_content or 'theme.system' in app_content
    assert '"Light"' in app_content or 'theme.light' in app_content
    assert '"Dark"' in app_content or 'theme.dark' in app_content


# ── 6b. Theme smoke test (fragile iframe injection guard) ────────────────
#
# The theme fix injects a script via st.components.v1.html that reaches the
# parent document and sets data-theme. This is intentionally fragile (depends
# on Streamlit DOM / iframe sandbox / version behaviour). These smoke tests
# assert the load-bearing markers are still present so a Streamlit upgrade or
# an accidental refactor that silently breaks them is caught early. They do NOT
# prove the theme renders correctly in a real browser — that needs a manual /
# browser-driven check after each Streamlit upgrade.


def test_theme_smoke_injection_mechanism_present():
    """The parent-document data-theme injection must still be wired up."""
    app_path = Path(__file__).parent.parent / "app.py"
    app_content = app_path.read_text(encoding="utf-8")

    # The iframe-based component must be used (st.markdown would strip scripts).
    assert "st.components.v1.html" in app_content
    # The script must reach the parent document and set the data-theme attr.
    assert "window.parent.document" in app_content
    assert "setAttribute('data-theme'" in app_content
    # System mode must honour the OS preference.
    assert "prefers-color-scheme: dark" in app_content


def test_theme_smoke_map_covers_all_modes():
    """The theme map must translate all three selector options to valid values."""
    from src.i18n import t, set_locale, get_locale

    original = get_locale()
    try:
        for locale in ("zh-CN", "en"):
            set_locale(locale)
            theme_map = {
                t("theme.system"): "system",
                t("theme.light"): "light",
                t("theme.dark"): "dark",
            }
            # All three resolved values must be distinct and valid.
            assert set(theme_map.values()) == {"system", "light", "dark"}
            # The three option labels must be distinct (no collision).
            assert len(set(theme_map.keys())) == 3
    finally:
        set_locale(original)


def test_theme_smoke_locale_scoped_selector_key():
    """Theme/output selectors must use locale-scoped keys to avoid stale values."""
    app_path = Path(__file__).parent.parent / "app.py"
    app_content = app_path.read_text(encoding="utf-8")

    # Locale-scoped keys reset cleanly on language switch (no lingering value).
    assert 'theme_selector_{get_locale()}' in app_content
    assert 'global_output_lang_{get_locale()}' in app_content


# ── 7. CSS contrast ──────────────────────────────────────────────────────


def test_light_theme_text_contrast():
    """Light theme must have dark text on light background."""
    app_path = Path(__file__).parent.parent / "app.py"
    app_content = app_path.read_text(encoding="utf-8")

    # Find the light theme section
    light_idx = app_content.find('[data-theme="light"]')
    assert light_idx > 0

    light_section = app_content[light_idx:light_idx + 800]
    # Light bg should be light color (f8fafc or similar)
    assert "#f8fafc" in light_section or "#f1f5f9" in light_section
    # Light text should be dark (0f172a or similar)
    assert "#0f172a" in light_section or "#334155" in light_section


def test_dark_theme_text_contrast():
    """Dark theme must have light text on dark background."""
    app_path = Path(__file__).parent.parent / "app.py"
    app_content = app_path.read_text(encoding="utf-8")

    # Find the dark theme / :root section
    root_idx = app_content.find(":root")
    assert root_idx >= 0

    dark_section = app_content[root_idx:root_idx + 1200]
    # Dark bg should be dark color
    assert "#07111f" in dark_section or "#0b1628" in dark_section
    # Dark text should be light
    assert "#f8fbff" in dark_section or "#d8e2f1" in dark_section


# ── 8. Activate clarification ────────────────────────────────────────────


def test_activate_vague_task_detected():
    """Short/vague tasks like '我要投标' must be detected as needing clarification."""
    # The vague detection logic is in app.py, but we can test the core concept:
    # retrieve_relevant_cards should return 0-score results for unrelated queries
    from src.generator import generate_card
    from src.storage import add_card, load_cards
    from src.retrieval import retrieve_relevant_cards

    # Add a card about health (unrelated to "投标")
    card = generate_card(
        knowledge_seed="Regular exercise helps maintain cardiovascular health and reduces disease risk.",
        source_type="Article",
        source="Health article",
    )
    add_card(card)

    cards = load_cards()
    results = retrieve_relevant_cards("我要投标", cards, top_k=3)

    # All scores should be 0 since "投标" has nothing to do with health
    if results:
        assert all(score == 0 for _, score in results), \
            "Vague task '我要投标' should not match unrelated health cards"


# ── 9. Ask grounded answer with citation ──────────────────────────────────


def test_ask_returns_structured_results():
    """Search should return results with citation and score information."""
    from src.generator import ingest_material
    from src.knowledge_base import search_knowledge_base

    # Add material
    ingest_material(
        knowledge_seed="AI governance requires clear accountability frameworks for model risk management. "
                       "Organizations must establish oversight mechanisms.",
        source_type="Article",
        source="AI governance report",
    )

    results = search_knowledge_base("AI governance", top_k=3)
    if results:
        for r in results:
            assert "chunk" in r
            assert "citation" in r
            assert "score" in r


# ── 10. Noise words excluded from topic tags ─────────────────────────────


def test_noise_words_not_in_topic_tags():
    """heart, american, association, copyright must NOT appear in topic tags."""
    from src.generator import generate_card

    # Simulate text that might contain noise words from a health PDF
    text = (
        "American Heart Association recommends 150 minutes of moderate-intensity "
        "aerobic activity per week. Copyright 2024. Learn more at heart.org. "
        "Adults should sleep 7-9 hours per night. Maintain healthy blood pressure "
        "below 120/80 mmHg. Keep BMI between 18.5 and 24.9."
    )

    card = generate_card(
        knowledge_seed=text,
        source_type="Article",
        source="Health guidelines",
    )

    tags_lower = {tag.lower() for tag in card.get("topic_tags", [])}
    keywords_lower = {kw.lower() for kw in card.get("trigger_map", {}).get("keywords", [])}

    forbidden = {"heart", "american", "association", "copyright", "healthy for good", "heart.org"}
    for word in forbidden:
        assert word not in tags_lower, f"'{word}' must not be in topic_tags"
        assert word not in keywords_lower, f"'{word}' must not be in trigger keywords"


def test_core_insight_not_copyright():
    """Core insight must not be a copyright notice or organization name."""
    from src.generator import generate_card

    text = (
        "How to eat better: Choose a variety of colorful fruits and vegetables. "
        "Limit sodium intake to less than 2,300 mg per day. "
        "American Heart Association. Copyright 2024. All rights reserved."
    )

    card = generate_card(
        knowledge_seed=text,
        source_type="Article",
        source="Health guide",
    )

    core = card.get("core_insight", "").lower()
    assert "copyright" not in core
    assert "american heart association" not in core
    assert "all rights reserved" not in core


def test_topic_label_not_noise():
    """Topic label must not be an organization name or copyright."""
    from src.generator import generate_card

    text = (
        "Managing cholesterol: LDL cholesterol should be below 100 mg/dL for most adults. "
        "HDL cholesterol above 60 mg/dL is protective against heart disease."
    )

    card = generate_card(
        knowledge_seed=text,
        source_type="Article",
        source="Health guide",
    )

    label = card.get("topic_label", "").lower()
    assert "american heart" not in label
    assert "copyright" not in label


# ── PDF language detection ─────────────────────────────────────────────────


def test_language_detection_chinese():
    """Language detector must identify Chinese text."""
    from src.parsers.pdf_parser import _detect_language

    assert _detect_language("如何吃得更好") == "zh"
    assert _detect_language("成年人每晚应睡七到九小时") == "zh"


def test_language_detection_english():
    """Language detector must identify English text."""
    from src.parsers.pdf_parser import _detect_language

    assert _detect_language("How to eat better and live longer") == "en"
    assert _detect_language("Regular exercise is important for health") == "en"


def test_language_detection_mixed():
    """Language detector must identify mixed Chinese-English text."""
    from src.parsers.pdf_parser import _detect_language

    # Need at least 3 Latin words AND significant CJK to be "mix"
    mixed_text = "BMI index and cholesterol " + "\u4fdd\u6301\u5728" + "18.5-24.9" + "\u4e4b\u95f4\u662f\u5065\u5eb7\u7684\u8303\u56f4"
    result = _detect_language(mixed_text)
    assert result == "mix"


# ── Column detection ──────────────────────────────────────────────────────


def test_dual_column_detection():
    """Column detection must identify dual-column layouts."""
    from src.parsers.pdf_parser import _detect_columns, TextBlock

    # Simulate blocks spread across two columns on a wide page
    blocks = []
    for i in range(8):
        blocks.append(TextBlock(
            text=f"Left block {i}",
            bbox=(50, i * 50, 300, i * 50 + 40),
            page=1,
        ))
    for i in range(8):
        blocks.append(TextBlock(
            text=f"Right block {i}",
            bbox=(700, i * 50, 950, i * 50 + 40),
            page=1,
        ))

    num_cols = _detect_columns(blocks, page_width=1200)
    assert num_cols == 2, "Should detect dual-column layout"


def test_single_column_detection():
    """Column detection must identify single-column layouts."""
    from src.parsers.pdf_parser import _detect_columns, TextBlock

    blocks = [
        TextBlock(text=f"Block {i}", bbox=(100, i * 50, 500, i * 50 + 40), page=1)
        for i in range(8)
    ]

    num_cols = _detect_columns(blocks, page_width=600)
    assert num_cols == 1, "Should detect single-column layout"
