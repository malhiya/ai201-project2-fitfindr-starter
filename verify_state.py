"""
verify_state.py — temporary check that state flows by reference through run_agent.

Wraps suggest_outfit / create_fit_card so each one PRINTS the exact objects it
receives and returns as the interaction runs, then confirms those objects ARE
the ones stored in the session. If anything were re-prompted or hardcoded
between steps, the identities (id(...)) would differ.
"""

import agent
from utils.data_loader import get_example_wardrobe

# --- capture + print what each tool actually receives / returns ---------------
captured = {}

_real_search = agent.search_listings
_real_suggest = agent.suggest_outfit
_real_fitcard = agent.create_fit_card


def spy_search_listings(description, size=None, max_price=None):
    print("\n" + "-" * 70)
    print(">> search_listings() CALLED")
    print(f"   description={description!r}  size={size!r}  max_price={max_price!r}")
    results = _real_search(description, size, max_price)
    print(f"<< search_listings() RETURNED  id={id(results)}  ->  {len(results)} option(s)")
    for rank, listing in enumerate(results):
        print(f"   [{rank}] id={id(listing)}  {listing}")
    captured["search_return_id"] = id(results)
    captured["search_result_ids"] = [id(r) for r in results]
    print("-" * 70)
    return results


def spy_suggest_outfit(new_item, wardrobe):
    print("\n" + "-" * 70)
    print(">> suggest_outfit() CALLED")
    print(f"   new_item  id={id(new_item)}  ->  {new_item['title']} (${new_item['price']})")
    print(f"   wardrobe  id={id(wardrobe)}  ->  {len(wardrobe.get('items', []))} items")
    captured["suggest_new_item_id"] = id(new_item)
    captured["suggest_wardrobe_id"] = id(wardrobe)
    result = _real_suggest(new_item, wardrobe)
    print(f"<< suggest_outfit() RETURNED  id={id(result)}")
    print(f"   {result}")
    captured["suggest_return_id"] = id(result)
    print("-" * 70)
    return result


def spy_create_fit_card(outfit, new_item):
    print("\n" + "-" * 70)
    print(">> create_fit_card() CALLED")
    print(f"   outfit    id={id(outfit)}")
    print(f"   {outfit[:120]}{'...' if len(outfit) > 120 else ''}")
    print(f"   new_item  id={id(new_item)}  ->  {new_item['title']} (${new_item['price']})")
    captured["fitcard_outfit_id"] = id(outfit)
    captured["fitcard_new_item_id"] = id(new_item)
    result = _real_fitcard(outfit, new_item)
    print(f"<< create_fit_card() RETURNED  id={id(result)}")
    print(f"   {result}")
    print("-" * 70)
    return result


agent.search_listings = spy_search_listings
agent.suggest_outfit = spy_suggest_outfit
agent.create_fit_card = spy_create_fit_card

# --- run the planning.md walkthrough query ------------------------------------
QUERY = (
    "I'm looking for a vintage graphic tee under $30. "
    "I mostly wear baggy jeans and chunky sneakers. "
    "What's out there and how would I style it?"
)
print("QUERY:", QUERY)
wardrobe = get_example_wardrobe()
session = agent.run_agent(QUERY, wardrobe)

print("\n" + "=" * 70)
print("FINAL SESSION STATE")
print("=" * 70)
print("PARSED:", session["parsed"])
print("-" * 70)
print(f"SELECTED ITEM  id={id(session['selected_item'])}:")
print(session["selected_item"])
print("-" * 70)
print(f"OUTFIT SUGGESTION  id={id(session['outfit_suggestion'])}:")
print(session["outfit_suggestion"])
print("-" * 70)
print(f"FIT CARD  id={id(session['fit_card'])}:")
print(session["fit_card"])
print("=" * 70)

# --- identity assertions: same object in == same object stored ----------------
sel_id = id(session["selected_item"])
out_id = id(session["outfit_suggestion"])

print("\nSTATE-FLOW CHECKS (by object identity)")
print(f"  selected_item IS search_results[0] from search_listings:"
      f"{sel_id == captured['search_result_ids'][0]}")
print(f"  selected_item IS the dict passed to suggest_outfit:    "
      f"{sel_id == captured['suggest_new_item_id']}")
print(f"  selected_item IS the dict passed to create_fit_card:   "
      f"{sel_id == captured['fitcard_new_item_id']}")
print(f"  suggest_outfit's return IS session['outfit_suggestion']:"
      f"{out_id == captured['suggest_return_id']}")
print(f"  outfit_suggestion IS the string passed to fit_card:    "
      f"{out_id == captured['fitcard_outfit_id']}")
print(f"  wardrobe passed to suggest_outfit IS session wardrobe: "
      f"{captured['suggest_wardrobe_id'] == id(session['wardrobe'])}")

assert sel_id == captured["search_result_ids"][0]
assert sel_id == captured["suggest_new_item_id"]
assert sel_id == captured["fitcard_new_item_id"]
assert out_id == captured["suggest_return_id"]
assert out_id == captured["fitcard_outfit_id"]
assert captured["suggest_wardrobe_id"] == id(session["wardrobe"])
print("\nALL CHECKS PASSED — state flows by reference, nothing re-prompted/hardcoded.")
