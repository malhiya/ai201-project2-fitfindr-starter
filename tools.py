"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform

    TODO:
        1. Load all listings with load_listings().
        2. Filter by max_price and size (if provided).
        3. Score each remaining listing by keyword overlap with `description`.
        4. Drop any listings with a score of 0 (no relevant matches).
        5. Sort by score, highest first, and return the listing dicts.

    Before writing code, fill in the Tool 1 section of planning.md.
    """
    listings = load_listings()

    # Keywords from the description, lowercased (e.g. "vintage graphic tee").
    keywords = {word for word in description.lower().split() if word}

    scored: list[tuple[int, dict]] = []
    for listing in listings:
        # Filter by max_price (inclusive) if provided.
        if max_price is not None and listing["price"] > max_price:
            continue

        # Filter by size (case-insensitive substring) if provided.
        if size is not None and size.lower() not in listing["size"].lower():
            continue

        # Score by keyword overlap against the listing's searchable text.
        haystack = " ".join(
            [
                listing["title"],
                listing["description"],
                listing["category"],
                " ".join(listing["style_tags"]),
                " ".join(listing["colors"]),
                listing["brand"] or "",
            ]
        ).lower()

        score = sum(1 for kw in keywords if kw in haystack)

        # Drop listings that match no keywords.
        if score == 0:
            continue

        scored.append((score, listing))

    # Sort by score, highest first.
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [listing for _, listing in scored]



# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If empty: call the LLM with a prompt for general styling ideas
           (what kinds of items pair well, what vibe it suits, etc.).
        3. If not empty: format the wardrobe items into a prompt and ask
           the LLM to suggest specific outfit combinations using the new item
           and named pieces from the wardrobe.
        4. Return the LLM's response as a string.

    Before writing code, fill in the Tool 2 section of planning.md.
    """
    client = _get_groq_client()

    # Describe the new item the user is considering.
    item_desc = (
        f"{new_item['title']} — {new_item['description']} "
        f"(category: {new_item['category']}, "
        f"style: {', '.join(new_item['style_tags'])}, "
        f"colors: {', '.join(new_item['colors'])})"
    )

    items = wardrobe.get("items", [])

    if not items:
        # Empty wardrobe → general styling advice (never empty, never raises).
        user_prompt = (
            f"A shopper is considering buying this thrifted item:\n{item_desc}\n\n"
            "They haven't told me what's in their closet. Suggest 1-2 complete "
            "outfits as general styling advice: what kinds of pieces pair well "
            "with it, what vibe it suits, and how to make it the centerpiece. "
            "Be concrete about garment types, colors, and occasions, but do not "
            "invent specific items they own."
        )
    else:
        # Populated wardrobe → pair with specific named pieces from the closet.
        wardrobe_lines = "\n".join(
            f"- {it['name']} (id: {it['id']}, category: {it['category']}, "
            f"colors: {', '.join(it['colors'])}, "
            f"style: {', '.join(it['style_tags'])})"
            for it in items
        )
        user_prompt = (
            f"A shopper is considering buying this thrifted item:\n{item_desc}\n\n"
            f"Here is what they already own:\n{wardrobe_lines}\n\n"
            "Suggest 1-2 complete outfits that pair the new item with specific "
            "pieces from their wardrobe. Refer to those pieces by name. Explain "
            "briefly why each outfit works (vibe, color, occasion)."
        )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are FitFindr, a friendly thrift-styling assistant. "
                    "Give practical, specific outfit ideas in a warm, casual tone."
                ),
            },
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
    )

    return response.choices[0].message.content.strip()


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)

    TODO:
        1. Guard against an empty or whitespace-only outfit string.
        2. Build a prompt that gives the LLM the item details and the outfit,
           and asks for a caption matching the style guidelines above.
        3. Call the LLM and return the response.

    Before writing code, fill in the Tool 3 section of planning.md.
    """
    # Guard against a missing/empty/whitespace-only outfit — never call the LLM,
    # never raise. This catches an upstream suggest_outfit failure.
    if not outfit or not outfit.strip():
        return (
            "Couldn't write a fit card — no outfit was generated. "
            "Try searching again so I have a look to caption."
        )

    client = _get_groq_client()

    # Item details woven into the caption (title, price, platform once each).
    user_prompt = (
        f"Item: {new_item['title']}\n"
        f"Price: ${new_item['price']}\n"
        f"Platform: {new_item['platform']}\n\n"
        f"Outfit the shopper is putting together:\n{outfit}\n\n"
        "Write a 2-4 sentence Instagram/TikTok caption for this thrifted find. "
        "Make it feel like a real OOTD post — casual and authentic, not a product "
        "description. Mention the item name, the price, and the platform naturally, "
        "once each. Capture the outfit's vibe in specific terms. Return only the "
        "caption text (emojis welcome, no hashtag dump)."
    )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are FitFindr, writing short, punchy OOTD captions for "
                    "thrifted finds. Sound like a real person sharing a fit."
                ),
            },
            {"role": "user", "content": user_prompt},
        ],
        temperature=1.0,  # higher temp → captions vary across calls
    )

    return response.choices[0].message.content.strip()


# ── Manual test harness ───────────────────────────────────────────────────────

def main() -> None:
    """Quick sanity checks for search_listings. Run with: python tools.py"""

    def show(label: str, results: list[dict]) -> None:
        print(f"\n{label}  →  {len(results)} match(es)")
        for r in results:
            print(f"  - {r['id']}  {r['title']}  (${r['price']}, size {r['size']})")

    # Query 1 — happy path: description + price ceiling, no size filter.
    show(
        "Q1: 'vintage graphic tee', max_price=30",
        search_listings("vintage graphic tee", size=None, max_price=30.0),
    )

    # Query 2 — case-insensitive size filter ('m' should match 'S/M', etc.).
    show(
        "Q2: 'graphic tee', size='m'",
        search_listings("graphic tee", size="m", max_price=None),
    )

    # Query 3 — no matches: should return [] (never raise).
    show(
        "Q3: 'designer ballgown', size='XXS', max_price=5 (expect none)",
        search_listings("designer ballgown", size="XXS", max_price=5.0),
    )

    # ── suggest_outfit checks (hits the Groq API — needs GROQ_API_KEY) ──────────
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    tee = search_listings("vintage graphic tee", max_price=30.0)[0]
    jeans = search_listings("vintage denim jeans")[0]

    # Query 4 — populated wardrobe: should name specific pieces by name.
    print("\n\nQ4: suggest_outfit(graphic tee, example wardrobe)")
    print(suggest_outfit(tee, get_example_wardrobe()))

    # Query 5 — empty wardrobe: should give general styling advice, never empty.
    print("\n\nQ5: suggest_outfit(graphic tee, empty wardrobe)")
    print(suggest_outfit(tee, get_empty_wardrobe()))

    # Query 6 — different item + populated wardrobe.
    print("\n\nQ6: suggest_outfit(jeans, example wardrobe)")
    outfit = suggest_outfit(jeans, get_example_wardrobe())
    print(outfit)

    # ── create_fit_card checks ─────────────────────────────────────────────────

    # Query 7 — happy path: real outfit string → casual OOTD caption.
    print("\n\nQ7: create_fit_card(outfit, jeans)")
    print(create_fit_card(outfit, jeans))

    # Query 8 — variety: same inputs again should read differently (high temp).
    print("\n\nQ8: create_fit_card(outfit, jeans) again — should differ from Q7")
    print(create_fit_card(outfit, jeans))

    # Query 9 — guard: empty/whitespace outfit → error string, no LLM call.
    print("\n\nQ9: create_fit_card('   ', jeans) — expect error message")
    print(create_fit_card("   ", jeans))


if __name__ == "__main__":
    main()
