"""Tests for the local knowledge base (documents, chunks, search)."""

from __future__ import annotations

import pytest

from src.knowledge_base import (
    _clear_all,
    chunk_document,
    delete_document,
    find_duplicate_document,
    get_document,
    list_documents,
    save_document,
    search_knowledge_base,
)


class TestDocumentStorage:
    def test_save_and_get_document(self):
        doc_id = save_document(
            content="Test content about AI governance.",
            title="AI Governance Report",
            source_kind="article",
            source_reference="https://example.com/ai",
        )
        assert doc_id
        doc = get_document(doc_id)
        assert doc is not None
        assert doc["title"] == "AI Governance Report"
        assert doc["source_kind"] == "article"
        assert "AI governance" in doc["content"]

    def test_list_documents(self):
        docs = list_documents()
        assert isinstance(docs, list)

    def test_delete_document(self):
        doc_id = save_document(content="To be deleted", title="Delete Me")
        assert delete_document(doc_id) is True
        assert get_document(doc_id) is None


class TestChunking:
    def test_chunk_document_creates_chunks(self):
        doc_id = save_document(content="This is paragraph one.\n\nThis is paragraph two.", title="Chunk Test")
        chunks = chunk_document(doc_id, "This is paragraph one.\n\nThis is paragraph two.")
        assert len(chunks) >= 2
        for chunk in chunks:
            assert "id" in chunk
            assert chunk["document_id"] == doc_id
            assert chunk["chunk_text"]

    def test_chunk_preserves_location_markers(self):
        text = "[Page 1] Introduction.\n\n[Page 2] Main content here."
        doc_id = save_document(content=text, title="Location Test")
        chunks = chunk_document(doc_id, text)
        locations = [c.get("location", "") for c in chunks]
        assert any("Page" in loc for loc in locations)


class TestSearch:
    def test_search_finds_relevant_chunks(self):
        text = "Climate risk is increasing. Financial institutions must report Scope 1, 2, and 3 emissions."
        doc_id = save_document(content=text, title="Climate Report")
        chunk_document(doc_id, text)
        results = search_knowledge_base("climate risk emissions", top_k=3)
        assert len(results) > 0
        assert any("climate" in r["chunk"]["chunk_text"].lower() for r in results)

    def test_search_returns_citations(self):
        text = "AI governance requires cross-functional accountability."
        doc_id = save_document(content=text, title="AI Report", source_reference="ref123")
        chunk_document(doc_id, text)
        results = search_knowledge_base("AI governance", top_k=3)
        assert len(results) > 0
        assert results[0].get("citation")
        assert "AI Report" in results[0]["citation"]

    def test_search_empty_query(self):
        results = search_knowledge_base("", top_k=3)
        assert results == []

    def test_search_no_match(self):
        results = search_knowledge_base("xyznonexistent12345", top_k=3)
        assert results == []


class TestDeduplication:
    def test_duplicate_content_detected(self):
        doc_id1 = save_document(content="Unique content for dedup test.", title="First")
        doc_id2 = save_document(content="Unique content for dedup test.", title="Second")
        assert doc_id1 == doc_id2  # Should return same doc_id

    def test_different_content_not_deduped(self):
        doc_id1 = save_document(content="Content A about governance.", title="A")
        doc_id2 = save_document(content="Content B about climate.", title="B")
        assert doc_id1 != doc_id2

    def test_find_duplicate_document(self):
        save_document(content="Findable content here.", title="Findable")
        result = find_duplicate_document("Findable content here.")
        assert result is not None
        result2 = find_duplicate_document("Completely different content.")
        assert result2 is None
