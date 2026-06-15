"""
verify_state.py — proves state passes between tools by reference, with no re-entry.

It wraps the three tools to record the exact objects each one receives and
returns (by id()), runs one full interaction, and then checks:

  1. the item returned by search_listings IS the item passed into suggest_outfit
  2. the outfit returned by suggest_outfit IS the outfit passed into create_fit_card

Two objects with the same id() are the same object in memory, so matching ids
prove nothing was copied, re-fetched, or re-entered between steps.

Run:  python verify_state.py   (needs GROQ_API_KEY in .env)
"""

import agent
from utils.data_loader import get_example_wardrobe

ids = {}
_real_search = agent.search_listings
_real_suggest = agent.suggest_outfit
_real_fitcard = agent.create_fit_card


def short(obj_id):
    """Last 6 digits of an id, enough to compare at a glance."""
    return str(obj_id)[-6:]


def block(text):
    """Indent a multi-line output block so it reads cleanly under a step."""
    for line in text.splitlines():
        print(f"          | {line}")


def spy_search_listings(description, size=None, max_price=None):
    results = _real_search(description, size, max_price)
    top = results[0] if results else None
    ids["search_top_item"] = id(top)
    print(f"STEP 1  search_listings  ->  {len(results)} match(es)")
    for rank, item in enumerate(results):
        print(f"        [{rank}] {item['title']} (${item['price']}, size {item['size']})")
    if top:
        print(f"        OUTPUT  top item  id=...{short(id(top))}")
    return results


def spy_suggest_outfit(new_item, wardrobe):
    ids["suggest_in_item"] = id(new_item)
    print("\nSTEP 2  suggest_outfit")
    print(f"        INPUT   item     id=...{short(id(new_item))}   {new_item['title']}")
    result = _real_suggest(new_item, wardrobe)
    ids["suggest_out_outfit"] = id(result)
    print(f"        OUTPUT  outfit   id=...{short(id(result))}")
    block(result)
    return result


def spy_create_fit_card(outfit, new_item):
    ids["fitcard_in_outfit"] = id(outfit)
    ids["fitcard_in_item"] = id(new_item)
    print("\nSTEP 3  create_fit_card")
    print(f"        INPUT   outfit   id=...{short(id(outfit))}")
    print(f"        INPUT   item     id=...{short(id(new_item))}   {new_item['title']}")
    result = _real_fitcard(outfit, new_item)
    print(f"        OUTPUT  fit card id=...{short(id(result))}")
    block(result)
    return result


agent.search_listings = spy_search_listings
agent.suggest_outfit = spy_suggest_outfit
agent.create_fit_card = spy_create_fit_card

QUERY = "vintage graphic tee under $30"

print("=" * 64)
print("FitFindr — State Flow Proof")
print(f'Query: "{QUERY}"')
print("=" * 64)

agent.run_agent(QUERY, get_example_wardrobe())

# --- the two requirement checks ----------------------------------------------
req1 = ids["search_top_item"] == ids["suggest_in_item"]
req2 = ids["suggest_out_outfit"] == ids["fitcard_in_outfit"]

print("=" * 64)
print("REQUIREMENT CHECKS")
print(f"  [{'PASS' if req1 else 'FAIL'}]  item from search_listings IS the item passed into suggest_outfit")
print(f"         (id ...{short(ids['search_top_item'])} == id ...{short(ids['suggest_in_item'])})")
print(f"  [{'PASS' if req2 else 'FAIL'}]  outfit from suggest_outfit IS the outfit passed into create_fit_card")
print(f"         (id ...{short(ids['suggest_out_outfit'])} == id ...{short(ids['fitcard_in_outfit'])})")
print("=" * 64)

assert req1, "item was not passed through by reference"
assert req2, "outfit was not passed through by reference"
print("Both requirements proven: state flows by reference, no re-entry.")
