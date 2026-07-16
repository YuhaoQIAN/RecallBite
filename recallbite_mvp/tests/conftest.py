"""Shared pytest fixtures for RecallBite tests.

Ensures all tests use an isolated temporary SQLite database
so the production knowledge base is never polluted.
"""

from __future__ import annotations

import pytest

import src.knowledge_base as kb_module


@pytest.fixture(autouse=True)
def isolated_kb(tmp_path):
    """Redirect the knowledge base to a temp database for every test."""
    temp_db = tmp_path / "test_knowledge_base.db"
    kb_module.set_db_path(temp_db)
    yield
    kb_module.reset_db_path()
