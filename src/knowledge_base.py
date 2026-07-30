"""Local knowledge base: documents, chunks, and grounded retrieval.

Uses SQLite + FTS5 for fast full-text search with citation-aware results.
Supports injectable DB path for test isolation.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path


DATA_DIR = Path(__file__).parent.parent / "data"
_DEFAULT_DB_PATH = DATA_DIR / "knowledge_base.db"

# Module-level overridable DB path (for test isolation)
_KB_DB_PATH: Path | None = None

# Legacy JSON files (for one-time migration)
_DOCS_FILE = DATA_DIR / "documents.json"
_CHUNKS_FILE = DATA_DIR / "chunks.json"


def _active_db_path() -> Path:
    """Return the currently active DB path."""
    return _KB_DB_PATH if _KB_DB_PATH is not None else _DEFAULT_DB_PATH


def set_db_path(path: Path | str | None) -> None:
    """Override the KB database path. Pass None to reset to default."""
    global _KB_DB_PATH
    if path is None:
        _KB_DB_PATH = None
    else:
        _KB_DB_PATH = Path(path)
        _KB_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _init_db()


def reset_db_path() -> None:
    """Reset to the default DB path."""
    set_db_path(None)


def _get_conn() -> sqlite3.Connection:
    """Open a SQLite connection with row factory."""
    db_path = _active_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _init_db() -> None:
    """Create tables and FTS5 index if they don't exist."""
    conn = _get_conn()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL DEFAULT 'Untitled',
                source_kind TEXT,
                source_reference TEXT,
                content TEXT,
                content_hash TEXT,
                created_at TEXT
            );

            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                chunk_text TEXT NOT NULL,
                location TEXT,
                created_at TEXT,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                chunk_text,
                document_id UNINDEXED,
                chunk_id UNINDEXED
            );
            """
        )
        conn.commit()
    finally:
        conn.close()


def _maybe_migrate_from_json() -> None:
    """One-time migration from legacy JSON files to SQLite."""
    if not _DOCS_FILE.exists() or not _CHUNKS_FILE.exists():
        return
    try:
        with open(_DOCS_FILE, "r", encoding="utf-8") as f:
            docs = json.load(f)
        with open(_CHUNKS_FILE, "r", encoding="utf-8") as f:
            chunks = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return

    if not isinstance(docs, list) or not docs:
        return

    conn = _get_conn()
    try:
        cursor = conn.execute("SELECT COUNT(*) FROM documents")
        if cursor.fetchone()[0] > 0:
            return

        for doc in docs:
            conn.execute(
                """
                INSERT OR IGNORE INTO documents (id, title, source_kind, source_reference, content, content_hash, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    doc.get("id", str(uuid.uuid4())[:12]),
                    doc.get("title", "Untitled"),
                    doc.get("source_kind", ""),
                    doc.get("source_reference", ""),
                    doc.get("content", ""),
                    doc.get("content_hash", ""),
                    doc.get("created_at", datetime.now().isoformat()),
                ),
            )
        for chunk in chunks:
            conn.execute(
                """
                INSERT OR IGNORE INTO chunks (id, document_id, chunk_text, location, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    chunk.get("id", str(uuid.uuid4())[:12]),
                    chunk.get("document_id", ""),
                    chunk.get("chunk_text", ""),
                    chunk.get("location", ""),
                    chunk.get("created_at", datetime.now().isoformat()),
                ),
            )
            conn.execute(
                "INSERT OR IGNORE INTO chunks_fts (chunk_text, document_id, chunk_id) VALUES (?, ?, ?)",
                (
                    chunk.get("chunk_text", ""),
                    chunk.get("document_id", ""),
                    chunk.get("id", ""),
                ),
            )
        conn.commit()
    finally:
        conn.close()


# Initialize on module load
_init_db()
# Only run migration on the default (production) DB, not test DBs
if _KB_DB_PATH is None:
    _maybe_migrate_from_json()


def _clear_all() -> None:
    """Clear all documents and chunks. Used only in tests."""
    conn = _get_conn()
    try:
        conn.execute("DELETE FROM chunks_fts")
        conn.execute("DELETE FROM chunks")
        conn.execute("DELETE FROM documents")
        conn.commit()
    finally:
        conn.close()


# ── Document operations ───────────────────────────────────────────────────


def _content_hash(content: str) -> str:
    """Stable SHA-256 digest of normalized content for deduplication."""
    normalized = re.sub(r"\s+", " ", content.strip())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def find_duplicate_document(content: str) -> str | None:
    """Return doc_id if a document with identical content already exists, else None."""
    h = _content_hash(content)
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT id FROM documents WHERE content_hash = ? LIMIT 1", (h,)
        ).fetchone()
        return dict(row)["id"] if row else None
    finally:
        conn.close()


def save_document(
    content: str,
    title: str = "",
    source_kind: str = "",
    source_reference: str = "",
    *,
    skip_dedup: bool = False,
) -> str:
    """Save a raw document and return its id.

    If skip_dedup is False (default), checks for duplicate content first
    and returns the existing doc_id if found.
    """
    if not skip_dedup:
        existing_id = find_duplicate_document(content)
        if existing_id:
            return existing_id

    doc_id = str(uuid.uuid4())[:12]
    conn = _get_conn()
    try:
        conn.execute(
            """
            INSERT INTO documents (id, title, source_kind, source_reference, content, content_hash, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                doc_id,
                title or "Untitled",
                source_kind,
                source_reference,
                content,
                _content_hash(content),
                datetime.now().isoformat(),
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return doc_id


def get_document(doc_id: str) -> dict | None:
    conn = _get_conn()
    try:
        row = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_documents() -> list[dict]:
    conn = _get_conn()
    try:
        rows = conn.execute("SELECT * FROM documents ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def delete_document(doc_id: str) -> bool:
    conn = _get_conn()
    try:
        # Delete FTS entries first
        old = conn.execute("SELECT id FROM chunks WHERE document_id = ?", (doc_id,)).fetchall()
        for row in old:
            conn.execute("DELETE FROM chunks_fts WHERE chunk_id = ?", (row["id"],))
        conn.execute("DELETE FROM chunks WHERE document_id = ?", (doc_id,))
        cursor = conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


# ── Chunking ──────────────────────────────────────────────────────────────


def _split_into_chunks(text: str, max_chunk_size: int = 800) -> list[tuple[str, str]]:
    """Split text into chunks. Returns list of (chunk_text, location_hint)."""
    paragraphs = re.split(r"\n\s*\n", text.strip())
    chunks: list[tuple[str, str]] = []
    current_location = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        loc_match = re.search(r"\[(Page|Slide)\s*\d+\]", para)
        if loc_match:
            current_location = loc_match.group(0)

        if len(para) <= max_chunk_size:
            chunks.append((para, current_location))
        else:
            sentences = re.split(r"(?<=[。！？.!?])\s+", para)
            current_chunk = ""
            for sent in sentences:
                if len(current_chunk) + len(sent) + 1 <= max_chunk_size:
                    current_chunk = (current_chunk + " " + sent).strip() if current_chunk else sent
                else:
                    if current_chunk:
                        chunks.append((current_chunk, current_location))
                    current_chunk = sent
            if current_chunk:
                chunks.append((current_chunk, current_location))

    return chunks


def chunk_document(doc_id: str, text: str) -> list[dict]:
    """Split a document into chunks and save them. Returns chunk records."""
    raw_chunks = _split_into_chunks(text)
    new_chunks: list[dict] = []

    conn = _get_conn()
    try:
        # Remove existing chunks for this doc (and their FTS entries)
        old = conn.execute("SELECT id FROM chunks WHERE document_id = ?", (doc_id,)).fetchall()
        for row in old:
            conn.execute("DELETE FROM chunks_fts WHERE chunk_id = ?", (row["id"],))
        conn.execute("DELETE FROM chunks WHERE document_id = ?", (doc_id,))

        for idx, (chunk_text, location) in enumerate(raw_chunks, 1):
            if not chunk_text.strip():
                continue
            chunk_id = f"{doc_id}_c{idx}"
            created_at = datetime.now().isoformat()
            conn.execute(
                "INSERT INTO chunks (id, document_id, chunk_text, location, created_at) VALUES (?, ?, ?, ?, ?)",
                (chunk_id, doc_id, chunk_text, location, created_at),
            )
            conn.execute(
                "INSERT INTO chunks_fts (chunk_text, document_id, chunk_id) VALUES (?, ?, ?)",
                (chunk_text, doc_id, chunk_id),
            )
            new_chunks.append({
                "id": chunk_id,
                "document_id": doc_id,
                "chunk_text": chunk_text,
                "location": location,
                "created_at": created_at,
            })
        conn.commit()
    finally:
        conn.close()
    return new_chunks


def get_chunks_for_document(doc_id: str) -> list[dict]:
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM chunks WHERE document_id = ? ORDER BY id",
            (doc_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ── Search ────────────────────────────────────────────────────────────────


def _tokenize(text: str) -> list[str]:
    """Simple tokenization: English words + Chinese characters."""
    words = re.findall(r"[a-zA-Z]{2,}", text.lower())
    chinese = re.findall(r"[\u4e00-\u9fff]{2,}", text)
    return words + chinese


def search_knowledge_base(query: str, top_k: int = 5) -> list[dict]:
    """Search chunks for relevant passages using FTS5 + keyword fallback.

    Each result contains:
    - chunk: the chunk dict
    - document: the parent document dict
    - score: relevance score
    - citation: formatted citation string
    """
    if not query or not query.strip():
        return []

    conn = _get_conn()
    try:
        # Try FTS5 first
        fts_results: list[tuple[str, str, float]] = []
        try:
            # Escape FTS5 special chars: double-quote
            safe_query = query.replace('"', '""')
            rows = conn.execute(
                """
                SELECT chunk_id, document_id, rank
                FROM chunks_fts
                WHERE chunk_text MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (safe_query, top_k * 3),
            ).fetchall()
            fts_results = [(r["chunk_id"], r["document_id"], float(r["rank"])) for r in rows]
        except sqlite3.OperationalError:
            # FTS5 query syntax error; fallback to keyword search
            fts_results = []

        # If FTS5 returned nothing, fall back to token-based keyword search
        if not fts_results:
            query_tokens = _tokenize(query)
            if not query_tokens:
                return []
            all_chunks = conn.execute("SELECT * FROM chunks").fetchall()
            scored = []
            for row in all_chunks:
                chunk = dict(row)
                score = _score_chunk(chunk, query_tokens)
                if score > 0:
                    scored.append((chunk["id"], chunk["document_id"], score))
            scored.sort(key=lambda x: x[2], reverse=True)
            fts_results = scored[:top_k]

        # Build doc map
        doc_ids = {doc_id for _, doc_id, _ in fts_results}
        doc_map: dict[str, dict] = {}
        if doc_ids:
            placeholders = ",".join("?" * len(doc_ids))
            rows = conn.execute(
                f"SELECT * FROM documents WHERE id IN ({placeholders})",
                tuple(doc_ids),
            ).fetchall()
            doc_map = {r["id"]: dict(r) for r in rows}

        results = []
        seen_chunks: set[str] = set()
        for chunk_id, doc_id, score in fts_results:
            if chunk_id in seen_chunks:
                continue
            seen_chunks.add(chunk_id)
            chunk_row = conn.execute(
                "SELECT * FROM chunks WHERE id = ?", (chunk_id,)
            ).fetchone()
            if not chunk_row:
                continue
            chunk = dict(chunk_row)
            doc = doc_map.get(doc_id, {})
            citation = _format_citation(doc, chunk)
            results.append({
                "chunk": chunk,
                "document": doc,
                "score": score,
                "citation": citation,
            })

        return results[:top_k]
    finally:
        conn.close()


def _score_chunk(chunk: dict, query_tokens: list[str]) -> float:
    """Score a chunk by keyword overlap."""
    text = chunk.get("chunk_text", "").lower()
    if not text:
        return 0.0
    score = 0.0
    for token in query_tokens:
        if token in text:
            score += 1.0
            if len(token) >= 4:
                score += 0.5
    return score


def _format_citation(doc: dict, chunk: dict) -> str:
    """Format a citation string for display."""
    title = doc.get("title", "Untitled")
    source = doc.get("source_reference", "")
    location = chunk.get("location", "")
    parts = [p for p in [title, location, source] if p]
    return " | ".join(parts) if parts else "Unknown source"