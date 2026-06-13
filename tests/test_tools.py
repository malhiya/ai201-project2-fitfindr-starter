"""
Tests for the three FitFindr tools. Run from the project root with:  pytest

search_listings is offline, so we test it directly (your template style).
suggest_outfit and create_fit_card call the Groq API, so the `fake_llm` fixture
swaps in a tiny fake client — no API key needed, no cost, fast, and predictable.
The fake stands in only for the LLM; the rest of each tool's logic runs for real.
"""

import os
import sys

import pytest

# Make `import tools` work no matter where pytest is launched from.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tools
from tools import create_fit_card, search_listings, suggest_outfit


# ── search_listings ──────────────────────────────────────────────────────────

def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0


def test_search_empty_results():
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []   # empty list, no exception


def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=45)
    assert len(results) > 0
    assert all(item["price"] <= 45 for item in results)


def test_search_size_filter():
    # lowercase "m" should still match listings sized "S/M", "M", etc.
    results = search_listings("tee", size="m", max_price=None)
    assert len(results) > 0
    assert all("m" in item["size"].lower() for item in results)


# ── a tiny fake Groq client for the two LLM-backed tools ─────────────────────

class _FakeCompletions:
    def __init__(self):
        self.calls = []          # records each create() call so tests can check it

    def create(self, **kwargs):
        self.calls.append(kwargs)
        message = type("Msg", (), {"content": "Pair it with dark-wash jeans."})()
        choice = type("Choice", (), {"message": message})()
        return type("Resp", (), {"choices": [choice]})()


@pytest.fixture
def fake_llm(monkeypatch):
    completions = _FakeCompletions()
    client = type("Client", (), {"chat": type("Chat", (), {"completions": completions})()})()
    monkeypatch.setattr(tools, "_get_groq_client", lambda: client)
    return completions


ITEM = {
    "title": "Y2K Baby Tee", "description": "Cute baby tee.", "category": "tops",
    "style_tags": ["y2k"], "colors": ["pink"], "price": 18.0, "platform": "depop",
}


# ── suggest_outfit ───────────────────────────────────────────────────────────

def test_suggest_outfit_populated_wardrobe(fake_llm):
    wardrobe = {"items": [
        {"id": "w_001", "name": "Dark-wash jeans", "category": "bottoms",
         "colors": ["indigo"], "style_tags": ["denim"]},
    ]}
    result = suggest_outfit(ITEM, wardrobe)
    assert isinstance(result, str) and result != ""
    # the wardrobe piece's name was passed into the prompt
    assert "Dark-wash jeans" in fake_llm.calls[0]["messages"][-1]["content"]


def test_suggest_outfit_empty_wardrobe(fake_llm):
    # empty wardrobe → still a non-empty string (general advice), never raises
    result = suggest_outfit(ITEM, {"items": []})
    assert isinstance(result, str) and result.strip() != ""


# ── create_fit_card ──────────────────────────────────────────────────────────

def test_create_fit_card_happy_path(fake_llm):
    result = create_fit_card("White tee tucked into dark-wash jeans.", ITEM)
    assert isinstance(result, str) and result.strip() != ""
    assert len(fake_llm.calls) == 1


def test_create_fit_card_empty_outfit_guard(fake_llm):
    # whitespace-only outfit → error string, and the LLM is never called
    result = create_fit_card("   ", ITEM)
    assert isinstance(result, str) and result.strip() != ""
    assert len(fake_llm.calls) == 0
