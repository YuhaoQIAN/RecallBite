"""Advanced PDF parser using PyMuPDF for coordinate-level text extraction.

Supports:
- Dual-column layout detection
- Bilingual (Chinese/English) content separation
- Header/footer/copyright filtering
- Page number preservation
- Evidence span tracking
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


# ── Noise patterns to filter ────────────────────────────────────────────

_NOISE_PATTERNS = [
    # Headers / branding
    re.compile(r"^healthy\s+for\s+good$", re.I),
    re.compile(r"^\s*TM\s*$", re.I),
    re.compile(r"american\s+heart\s+association", re.I),
    # Copyright / legal
    re.compile(r"copyright\s+\d{4}", re.I),
    re.compile(r"501\(c\)\(3\)", re.I),
    re.compile(r"not-for-profit", re.I),
    re.compile(r"all\s+rights\s+reserved", re.I),
    # URLs
    re.compile(r"heart\.org", re.I),
    re.compile(r"https?://", re.I),
    re.compile(r"www\.", re.I),
    # Page markers
    re.compile(r"^page\s+\d+", re.I),
    # Tiny trademark / TM symbols
    re.compile(r"^[\u2122\u00ae\u00a9\u200b\s]+$"),
    # Decorative / layout text that pollutes reading order
    re.compile(r"^TIPS\s+FOR\s*$", re.I),
    re.compile(r"^CHANGE\s+YOUR\s+MINDSET\s*$", re.I),
    re.compile(r"^DID\s+YOU\s+KNOW", re.I),
    re.compile(r"^FAST\s+FACT", re.I),
    re.compile(r"^KEY\s+TAKEAWAY", re.I),
    re.compile(r"^WHAT\s+YOU\s+CAN\s+DO", re.I),
    re.compile(r"^GET\s+STARTED", re.I),
    re.compile(r"^MY\s+ACTION", re.I),
    re.compile(r"^MY\s+CHECKLIST", re.I),
    re.compile(r"^MY\s+GOAL", re.I),
    re.compile(r"^TRACK\s+YOUR", re.I),
    re.compile(r"^CHECK\s+YOUR", re.I),
    re.compile(r"^KNOW\s+YOUR", re.I),
    re.compile(r"^MANAGE\s+YOUR", re.I),
    re.compile(r"^LIFE.?S?\s+ESSENTIAL", re.I),
    re.compile(r"^\d+\s*$"),  # Standalone numbers (page decorations)
]

_NOISE_KEYWORDS_LOWER = {
    "american heart association",
    "healthy for good",
    "heart-check",
    "learn more at",
    "copyright",
    "all rights reserved",
    "not-for-profit",
    "heart.org",
    "tips for",
    "change your mindset",
    "did you know",
    "fast fact",
    "key takeaway",
    "life's essential",
    "lifes essential",
}


# ── Data structures ──────────────────────────────────────────────────────

@dataclass
class TextBlock:
    """A text block with position and language info."""
    text: str
    bbox: tuple[float, float, float, float]  # (x0, y0, x1, y1)
    page: int
    font_size: float = 0.0
    language: str = ""  # "zh", "en", "mix"
    column: int = 0     # 0=left/single, 1=right


@dataclass
class PageSection:
    """A section within a page."""
    language: str
    title: str
    text: str
    page: int
    column: int = 0


@dataclass
class ParsedPDF:
    """Complete parsed PDF result."""
    pages: list[PageSection] = field(default_factory=list)
    page_count: int = 0
    is_bilingual: bool = False
    detected_languages: list[str] = field(default_factory=list)
    # Flat text for backward compatibility
    full_text: str = ""


# ── Language detection ───────────────────────────────────────────────────

_CJK_RANGE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]")
_LATIN_WORD = re.compile(r"[a-zA-Z]{2,}")


def _detect_language(text: str) -> str:
    """Detect if text is Chinese, English, or mixed."""
    cjk_chars = len(_CJK_RANGE.findall(text))
    latin_words = len(_LATIN_WORD.findall(text))
    total = cjk_chars + latin_words
    if total == 0:
        return "other"
    zh_ratio = cjk_chars / total
    if zh_ratio > 0.3:
        if latin_words >= 3:
            return "mix"
        return "zh"
    if latin_words >= 2:
        return "en"
    return "other"


def _is_noise(text: str) -> bool:
    """Check if text is a header/footer/copyright/URL to be filtered."""
    stripped = text.strip()
    if not stripped:
        return True
    if len(stripped) < 2:
        return True
    lower = stripped.lower()
    for pat in _NOISE_PATTERNS:
        if pat.search(stripped):
            return True
    for kw in _NOISE_KEYWORDS_LOWER:
        if kw in lower:
            return True
    # Filter if mostly punctuation/symbols
    alpha_count = sum(1 for c in stripped if c.isalpha() or _CJK_RANGE.match(c))
    if alpha_count < 3 and len(stripped) < 10:
        return True
    return False


# ── Column detection ─────────────────────────────────────────────────────

def _detect_columns(blocks: list[TextBlock], page_width: float) -> int:
    """Detect number of columns on a page based on x-coordinate clustering.
    
    Returns 1 for single-column, 2 for dual-column.
    """
    if not blocks:
        return 1
    
    # Collect x-centers
    x_centers = []
    for b in blocks:
        cx = (b.bbox[0] + b.bbox[2]) / 2
        x_centers.append(cx)
    
    if not x_centers:
        return 1
    
    # Find natural split point: look for a gap in x-centers
    mid = page_width / 2
    left_count = sum(1 for cx in x_centers if cx < mid - 50)
    right_count = sum(1 for cx in x_centers if cx > mid + 50)
    
    # Dual-column if significant content on both sides
    if left_count >= 5 and right_count >= 5:
        return 2
    return 1


def _assign_columns(blocks: list[TextBlock], num_cols: int, page_width: float) -> None:
    """Assign column index to each block."""
    if num_cols == 1:
        for b in blocks:
            b.column = 0
        return
    
    mid = page_width / 2
    for b in blocks:
        cx = (b.bbox[0] + b.bbox[2]) / 2
        b.column = 0 if cx < mid else 1


# ── Block extraction ─────────────────────────────────────────────────────

def _extract_blocks_from_page(fitz_page, page_num: int) -> list[TextBlock]:
    """Extract text blocks from a single PyMuPDF page."""
    page_dict = fitz_page.get_text("dict")
    blocks_raw = page_dict.get("blocks", [])
    
    result: list[TextBlock] = []
    for block in blocks_raw:
        if block.get("type") != 0:  # text block only
            continue
        
        lines = block.get("lines", [])
        if not lines:
            continue
        
        # Collect all text from spans
        texts = []
        font_sizes = []
        for line in lines:
            for span in line.get("spans", []):
                t = span.get("text", "").strip()
                if t:
                    texts.append(t)
                    font_sizes.append(span.get("size", 0))
        
        text = " ".join(texts).strip()
        if not text:
            continue
        
        bbox = tuple(block.get("bbox", (0, 0, 0, 0)))
        avg_size = sum(font_sizes) / len(font_sizes) if font_sizes else 0
        
        # Filter tiny font sizes (TM marks, superscripts)
        if avg_size < 5.0 and len(text) < 10:
            continue
        
        # Filter noise
        if _is_noise(text):
            continue
        
        lang = _detect_language(text)
        
        result.append(TextBlock(
            text=text,
            bbox=bbox,
            page=page_num,
            font_size=avg_size,
            language=lang,
        ))
    
    return result


def _sort_blocks_reading_order(blocks: list[TextBlock]) -> list[TextBlock]:
    """Sort blocks in reading order: top-to-bottom, left-to-right."""
    return sorted(blocks, key=lambda b: (round(b.bbox[1] / 15) * 15, b.bbox[0]))


def _group_blocks_into_sections(blocks: list[TextBlock], page_num: int) -> list[PageSection]:
    """Group sorted blocks into logical sections by language and column.
    
    Uses font-size clustering to distinguish section headers from body text.
    Decorative text (all-caps short phrases) is filtered out.
    """
    if not blocks:
        return []
    
    # Filter out decorative all-caps short blocks (likely layout elements)
    filtered_blocks = []
    for b in blocks:
        text = b.text.strip()
        # Skip all-caps short decorative text
        if len(text) < 40 and text == text.upper() and not any(c in text for c in '\u4e00\u4e01\u4e02\u4e03\u4e04\u4e05\u4e06\u4e07\u4e08\u4e09'):
            # Allow if it contains numbers (e.g., "150 minutes")
            if not re.search(r'\d', text):
                continue
        filtered_blocks.append(b)
    blocks = filtered_blocks
    if not blocks:
        return []
    
    sections: list[PageSection] = []
    
    # Group by (column, language)
    groups: dict[tuple[int, str], list[TextBlock]] = {}
    for b in blocks:
        lang = b.language if b.language in ("zh", "en") else "other"
        key = (b.column, lang)
        if key not in groups:
            groups[key] = []
        groups[key].append(b)
    
    # Build sections
    for (col, lang), group_blocks in sorted(groups.items()):
        if not group_blocks:
            continue
        
        # Detect section headers by font size clustering
        sizes = sorted(set(round(b.font_size, 1) for b in group_blocks), reverse=True)
        # Header threshold: significantly larger than median
        median_size = sizes[len(sizes) // 2] if sizes else 12
        header_threshold = median_size * 1.3 if median_size > 0 else 16
        
        title = ""
        body_parts = []
        
        for b in group_blocks:
            is_header = b.font_size >= header_threshold and len(b.text) < 80
            if is_header and not title:
                title = b.text
            else:
                body_parts.append(b.text)
        
        body = "\n".join(body_parts)
        if not body.strip() and title:
            body = title
            title = ""
        
        if body.strip():
            sections.append(PageSection(
                language=lang,
                title=title,
                text=body,
                page=page_num,
                column=col,
            ))
    
    return sections


# ── Cross-page section merging ─────────────────────────────────────────

def _merge_cross_page_sections(sections: list[PageSection]) -> list[PageSection]:
    """Merge same-language sections across pages when they share the same topic.
    
    For documents like Life's Essential 8 where each page is a separate topic,
    this keeps them separate. For documents where a topic spans multiple pages,
    this merges them.
    
    Strategy: sections on consecutive pages with the same language and similar
    titles (or no title) are merged. Sections with distinct titles are kept separate.
    """
    if not sections:
        return sections
    
    merged: list[PageSection] = []
    
    for sec in sections:
        # Try to merge with the last section of the same language
        if merged and merged[-1].language == sec.language:
            prev = merged[-1]
            # Merge if: same column, consecutive pages, and either no title change
            # or the previous section has no title (continuation)
            if (prev.column == sec.column 
                and abs(sec.page - prev.page) <= 1
                and (not prev.title or not sec.title or _titles_are_similar(prev.title, sec.title))):
                # Merge text
                merged[-1] = PageSection(
                    language=prev.language,
                    title=prev.title or sec.title,
                    text=prev.text + "\n" + sec.text,
                    page=prev.page,
                    column=prev.column,
                )
                continue
        
        merged.append(sec)
    
    return merged


def _titles_are_similar(a: str, b: str) -> bool:
    """Check if two section titles are similar enough to merge."""
    a_lower = a.lower().strip()
    b_lower = b.lower().strip()
    if a_lower == b_lower:
        return True
    # Check Jaccard similarity of words
    words_a = set(a_lower.split())
    words_b = set(b_lower.split())
    if not words_a or not words_b:
        return False
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union) > 0.6


# ── Main parser ──────────────────────────────────────────────────────────

def parse_pdf_advanced(file_bytes: bytes, filename: str = "") -> ParsedPDF:
    """Parse a PDF with coordinate-level extraction using PyMuPDF.
    
    Returns a ParsedPDF with structured pages, language detection,
    and bilingual content separation.
    """
    try:
        import fitz
    except ImportError as exc:
        raise ImportError(
            "Advanced PDF parsing requires PyMuPDF. Install: pip install PyMuPDF"
        ) from exc
    
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    total_pages = doc.page_count
    
    all_pages: list[PageSection] = []
    all_texts: list[str] = []
    languages_seen: set[str] = set()
    
    for page_idx in range(total_pages):
        page = doc[page_idx]
        page_num = page_idx + 1
        page_width = page.rect.width
        
        # Extract blocks
        blocks = _extract_blocks_from_page(page, page_num)
        if not blocks:
            continue
        
        # Detect columns
        num_cols = _detect_columns(blocks, page_width)
        _assign_columns(blocks, num_cols, page_width)
        
        # Sort in reading order
        blocks = _sort_blocks_reading_order(blocks)
        
        # Track languages
        for b in blocks:
            if b.language in ("zh", "en"):
                languages_seen.add(b.language)
        
        # Group into sections
        sections = _group_blocks_into_sections(blocks, page_num)
        all_pages.extend(sections)
        
        # Build flat text for backward compatibility
        page_text_parts = []
        for sec in sections:
            if sec.title:
                page_text_parts.append(f"[Page {page_num}] {sec.title}")
            page_text_parts.append(sec.text)
        
        if page_text_parts:
            all_texts.append(f"[Page {page_num}]\n" + "\n".join(page_text_parts))
    
    doc.close()
    
    is_bilingual = "zh" in languages_seen and "en" in languages_seen
    
    # Merge same-topic sections across pages for document-level understanding
    all_pages = _merge_cross_page_sections(all_pages)
    
    # Build bilingual-separated output text
    if is_bilingual:
        zh_parts = []
        en_parts = []
        for sec in all_pages:
            label = f"[Page {sec.page}]"
            if sec.language == "zh":
                zh_parts.append(f"{label}\n{sec.title}\n{sec.text}" if sec.title else f"{label}\n{sec.text}")
            elif sec.language == "en":
                en_parts.append(f"{label}\n{sec.title}\n{sec.text}" if sec.title else f"{label}\n{sec.text}")
        
        # For bilingual: interleave by page
        full_text = _build_bilingual_text(all_pages)
    else:
        full_text = "\n\n".join(all_texts)
    
    return ParsedPDF(
        pages=all_pages,
        page_count=total_pages,
        is_bilingual=is_bilingual,
        detected_languages=sorted(languages_seen),
        full_text=full_text.strip(),
    )


def _build_bilingual_text(pages: list[PageSection]) -> str:
    """Build bilingual output text with Chinese and English separated per page."""
    if not pages:
        return ""
    
    page_nums = sorted(set(s.page for s in pages))
    parts = []
    
    for pn in page_nums:
        page_sections = [s for s in pages if s.page == pn]
        zh_sections = [s for s in page_sections if s.language == "zh"]
        en_sections = [s for s in page_sections if s.language == "en"]
        
        parts.append(f"[Page {pn}]")
        
        if zh_sections:
            parts.append("--- 中文 ---")
            for s in zh_sections:
                if s.title:
                    parts.append(s.title)
                parts.append(s.text)
        
        if en_sections:
            parts.append("--- English ---")
            for s in en_sections:
                if s.title:
                    parts.append(s.title)
                parts.append(s.text)
        
        parts.append("")
    
    return "\n".join(parts)


def parse_pdf_simple(file_bytes: bytes, filename: str = "") -> str:
    """Simple wrapper: returns just the flat text for backward compatibility."""
    result = parse_pdf_advanced(file_bytes, filename)
    return result.full_text
