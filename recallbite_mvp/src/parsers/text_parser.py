"""Parse plain text input into structured material."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MaterialDocument:
    """Internal representation of a material document."""

    text: str
    source_kind: str = "pasted_text"
    source_title: str = ""
    source_reference: str = ""
    location_info: str = ""
    # Structured fields for advanced PDF parsing
    structured_pages: list[dict] = field(default_factory=list)
    detected_language: str = ""  # "zh", "en", "bilingual"
    is_bilingual: bool = False


def parse_text(raw_text: str, source_note: str = "") -> MaterialDocument:
    """Parse pasted or typed text into a MaterialDocument."""
    text = raw_text.strip()
    if not text:
        raise ValueError("Empty material")

    # Detect if the first line looks like a title
    lines = text.splitlines()
    title = ""
    if lines and len(lines[0]) < 120 and not lines[0].endswith((".", "。", "!", "?")):
        title = lines[0].strip()

    return MaterialDocument(
        text=text,
        source_kind="pasted_text",
        source_title=title,
        source_reference=source_note,
    )
