# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**
Searches the mock listings dataset for items matching the user's description, with optional size and price-ceiling filters. It scores each listing by keyword overlap with the description and returns the matches ranked best-first.

**Input parameters:**
- `description` (str): Keywords describing what the user is looking for (e.g., "vintage graphic tee"). Used to score relevance.
- `size` (str | None): Size string to filter by, or `None` to skip size filtering. Matching is case-insensitive (e.g., "M" matches "S/M").
- `max_price` (float | None): Maximum price, inclusive, or `None` to skip price filtering.

**What it returns:**
A list of matching listing dicts, sorted by relevance (best match first). Each dict contains: `id`, `title`, `description`, `category`, `style_tags` (list), `size`, `condition`, `price` (float), `colors` (list), `brand`, `platform`. Listings with a keyword-overlap score of 0 are dropped before returning.

**What happens if it fails or returns nothing:**
Returns an empty list — it does NOT raise an exception. When the agent receives an empty list, it skips `suggest_outfit`/`create_fit_card` and returns early with a "no matches found" message to the user.

---

### Tool 2: suggest_outfit

**What it does:**
Given a thrifted item and the user's wardrobe, it asks the LLM to suggest 1–2 complete outfits. If the wardrobe has items, it pairs the new item with specific named pieces from the closet; if empty, it gives general styling advice instead.

**Input parameters:**
- `new_item` (dict): A listing dict — the item the user is considering buying (the top result from `search_listings`).
- `wardrobe` (dict): A wardrobe dict with an `items` key holding a list of wardrobe item dicts. May be empty — handled gracefully.

**What it returns:**
A non-empty string with outfit suggestions. When the wardrobe has items, the suggestions reference specific pieces by name; when empty, it returns general styling advice for the item.

**What happens if it fails or returns nothing:**
Never returns an empty string or raises an exception. If `wardrobe['items']` is empty, it falls back to a general-styling prompt (what kinds of pieces pair well, what vibe the item suits) so the agent always has a usable outfit string to pass into `create_fit_card`.

---

### Tool 3: create_fit_card

**What it does:**
Generates a short, shareable OOTD-style caption for the thrifted find. It feeds the item details and the outfit suggestion to the LLM (via `_get_groq_client()`, at a higher temperature for variety) and asks for a casual, authentic Instagram/TikTok caption.

**Input parameters:**
- `outfit` (str): The outfit suggestion string returned by `suggest_outfit()`.
- `new_item` (dict): The listing dict for the thrifted item — its `title`, `price`, and `platform` are woven into the caption.

**What it returns:**
A 2–4 sentence string usable as an Instagram/TikTok caption. It feels casual and authentic (not a product description), mentions the item name, price, and platform naturally (once each), captures the outfit vibe in specific terms, and reads differently each time thanks to the higher temperature.

**What happens if it fails or returns nothing:**
Never raises an exception. If `outfit` is empty, missing, or whitespace-only, it returns a descriptive error-message string instead of calling the LLM. This is the guard against `suggest_outfit` having failed upstream.

---

### Additional Tools (if any)

<!-- Copy the block above for any tools beyond the required three -->

---

## Planning Loop

**How does your agent decide which tool to call next?**
<!-- Describe the logic your planning loop uses. What does it look at? What conditions change its behavior? How does it know when it's done? -->

First, initialize the session with _new_session(), then parse the user's query to extract a description, an optional size, and an optional max_price (e.g., "under $30" → max_price=30), storing them in session["parsed"]. Then call search_listings(description, size, max_price).

After search_listings runs, check if results is empty. If yes, set an error message in the session and return early.  If no, set selected_item = results[0] and proceed to suggest_outfit. 

Take selected_item and  get_example_wardrobe dict (or empty_wardrobe) as inputs for suggest_outift(). It should return a non-empty string with outfit suggestions. When the example wardrobe is used, the suggestions reference specific pieces by name. When the wardrobe is empty, it returns general styling advice for the item. 

Use what suggest_outfit returns and the selected_item as inputs for create_fit_card. The output should be a 2–4 sentence string usable as an Instagram/TikTok caption. If suggest_outfit return is empty, missing, or whitespace-only, it returns a descriptive error-message string instead of calling the LLM. This is the guard against suggest_outfit having failed upstream.


---

## State Management

**How does information from one tool get passed to the next?**
<!-- Describe how your agent stores and accesses state within a session. What data is tracked? How is it passed between tool calls? -->

All state lives in one `session` dict created by `_new_session()` at the start of the run. The tools do not call each other directly — the planning loop reads inputs from the session and writes each tool's output back into it before the next call.

The session tracks: `query` (the original text), `parsed` (the extracted description, size, and max_price), `search_results` (the list from `search_listings`), `selected_item` (the top result), `wardrobe` (the chosen wardrobe dict), `outfit_suggestion` (the string from `suggest_outfit`), `fit_card` (the string from `create_fit_card`), and `error` (set only if the run ends early).

The data flows in order: `search_listings` writes `search_results`, then the loop sets `selected_item = search_results[0]`. `suggest_outfit` reads `selected_item` and `wardrobe` and writes `outfit_suggestion`. `create_fit_card` reads `outfit_suggestion` and `selected_item` and writes `fit_card`. The loop returns the completed session, and the caller checks `session["error"]` first to know whether the run succeeded.

If `search_results` is empty, the loop sets `error` and returns immediately — it does not call `suggest_outfit` or `create_fit_card`, so `outfit_suggestion` and `fit_card` stay `None`.

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | Returns `[]` (never raises). The loop sets `session["error"]` to an actionable message and stops before the other tools. Verified: `search_listings('designer ballgown', size='XXS', max_price=5)` → `[]`. It does **not** call `suggest_outfit` or `create_fit_card`. |
| suggest_outfit | Wardrobe is empty | Detects `wardrobe["items"]` is empty and returns general styling advice instead of named-piece outfits (never empty, never raises). Verified with `get_empty_wardrobe()` on the Y2K baby tee — it returns advice with no `w_***` references, e.g. *"That Y2K baby tee is adorable… Since it's a fitted, cropped graphic tee, you'll want to balance it out with some flowy or high-waisted bottoms. **Outfit 1: Casual Day Out** — Pair the butterfly tee with high-waisted, light-washed jeans and Converse… **Outfit 2: Garden Party Chic** — try a flowy, pastel-colored skirt and sandals…"* |
| create_fit_card | Outfit input is missing or incomplete | Guards against an empty or whitespace-only `outfit` and returns an actionable string instead of calling the LLM (never raises). Verified: `create_fit_card('', results[0])` → *"Couldn't write a fit card — no outfit was generated. Try searching again so I have a look to caption."* |

---

## Architecture

<!-- Draw a diagram of your agent showing how the components connect:
     User input → Planning Loop → Tools (search_listings, suggest_outfit, create_fit_card)
                                                                          ↕
                                                                   State / Session
     Show what triggers each tool, how state flows between them, and where error paths branch off.
     ASCII art, a Mermaid diagram (https://mermaid.js.org/syntax/flowchart.html), or an embedded
     sketch are all fine. You'll share this diagram with an AI tool when asking it to implement
     the planning loop and each individual tool. -->

```
User query  ("vintage graphic tee under $30, size M")  +  wardrobe dict
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ PLANNING LOOP  (run_agent)                                                    │
│                                                                               │
│  Step 0:  _new_session(query, wardrobe)                                       │
│           Session created  ◄──────────────────────────────────┐              │
│             │                                                  │              │
│             ▼                                                  │              │
│  Step 1:  parse query → description, size, max_price           │              │
│           Session: parsed = {description, size, max_price}     │              │
│             │                                                  │              │
│             ├─► search_listings(description, size, max_price)  │              │
│             │        │                                         │ writes to    │
│             │        │ results = []                            │ Session      │
│             │        ├──► [ERROR] error = "No listings found"  │ (state)      │
│             │        │           └────────────────────────────┼──► return ───┼──► early exit
│             │        │                                         │              │
│             │        │ results = [item, ...]                   │              │
│             │        ▼                                         │              │
│           Session: search_results = [...]                      │              │
│           Session: selected_item   = results[0]  ─────────────►│              │
│             │                                                  │              │
│             ├─► suggest_outfit(selected_item, wardrobe)        │              │
│             │        │  (wardrobe items → named-piece outfits) │              │
│             │        │  (empty wardrobe → general advice)      │              │
│             │        ▼                                         │              │
│           Session: outfit_suggestion = "..."  ────────────────►│              │
│             │                                                  │              │
│             └─► create_fit_card(outfit_suggestion,             │              │
│                                 selected_item)                 │              │
│                      │  (empty/blank outfit → error string)    │              │
│                      ▼                                         │              │
│           Session: fit_card = "..."  ─────────────────────────►┘              │
│             │                                                                 │
│             ▼                                                                 │
│           return session  ────────────────────────────────────────────────► success exit
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
User sees:  selected_item.title  +  outfit_suggestion  +  fit_card
            (on error: session["error"] message, other fields are None)
```

**State flow:** the `session` dict (`_new_session`) is the single source of truth. Each tool reads its inputs from the session (`parsed`, `selected_item`, `outfit_suggestion`) and the loop writes each tool's output back into it before the next call. `session["error"]` is checked first by the caller — if set, the run ended early and `outfit_suggestion` / `fit_card` are `None`.

**Error branch:** the only early-exit is when `search_listings` returns `[]` — the loop sets `session["error"]` and returns immediately, never calling `suggest_outfit` or `create_fit_card`. The empty-wardrobe and blank-outfit cases are handled *inside* their tools (graceful fallback strings), so they do not terminate the loop.

---

## AI Tool Plan

<!-- For each part of the implementation below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, your agent diagram)
     - What you expect it to produce
     - How you'll verify the output matches your spec before moving on

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Tool 1 spec (inputs, return value, failure mode) and ask it to implement
     search_listings() using load_listings() from the data loader — then test it against 3 queries
     before trusting it" is a plan. -->

**Milestone 3 — Individual tool implementations:**

*search_listings* — I'll give Claude the Tool 1 block from planning.md (inputs, return value, failure mode) and ask it to implement the function using `load_listings()` from the data loader. Before running it, I'll check that the generated code filters by all three parameters and returns an empty list (no exception) on no match, then test it with 3 queries.

*suggest_outfit* — I'll give Claude the Tool 2 block and ask it to implement the function using the existing `_get_groq_client()` helper, branching on whether `wardrobe['items']` is empty. I'll verify the empty-wardrobe path returns general advice and the populated path names real pieces by testing it with both `get_example_wardrobe()` and `get_empty_wardrobe()`.

*create_fit_card* — I'll give Claude the Tool 3 block and ask it to implement the function with a higher LLM temperature, weaving the item `title`, `price`, and `platform` into the caption. I'll verify it guards against a blank `outfit` string (returns an error message, no LLM call) and that repeated calls on the same input produce different captions.

**Milestone 4 — Planning loop and state management:**

*Planning loop* — I'll give Claude the Planning Loop section, the Architecture diagram, and the `run_agent`/`_new_session` stubs in agent.py, and ask it to implement the loop in the documented order (parse → search → select → outfit → fit card). I'll verify it returns early with `session["error"]` when search results are empty and only calls `suggest_outfit`/`create_fit_card` on the happy path.

*State management* — I'll ask Claude to thread all data through the single `session` dict from `_new_session()` (writing `parsed`, `search_results`, `selected_item`, `outfit_suggestion`, `fit_card`, `error`) rather than using separate variables. I'll verify by running both the happy-path and no-results CLI cases in agent.py and confirming the session fields are populated correctly.

---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 0 — Init & parse:**
The agent calls `_new_session(query, wardrobe)` to create the session, then parses the query into `description="vintage graphic tee"`, `size=None` (no size is mentioned in the query), and `max_price=30.0` (pulled from "under $30"), storing them in `session["parsed"]`. The wardrobe is passed in separately (here, the populated `get_example_wardrobe()`).

**Step 1 — Search:**
<!-- What does the agent do first? Which tool is called? With what input? -->
The agent calls `search_listings("vintage graphic tee", size=None, max_price=30.0)`. With no size filter, it just drops anything over $30, scores the rest by keyword overlap, and returns the matches best-first — e.g. 2 listings led by `lst_002` "Y2K Baby Tee — Butterfly Print" ($18, Depop, excellent condition, tags `["y2k","vintage","graphic tee","cottagecore"]`). The loop stores the list in `session["search_results"]` and sets `session["selected_item"] = results[0]` (the Y2K baby tee).

**Step 2 — Suggest outfit:**
<!-- What happens next? What was returned from step 1? What tool is called now? -->
With a non-empty result, the agent calls `suggest_outfit(new_item=<Y2K baby tee dict>, wardrobe=<example wardrobe>)`. Because the wardrobe has items, the LLM returns a string that pairs the tee with real pieces by name — e.g. *"Style it with your baggy straight-leg jeans (w_001) and chunky white sneakers (w_007) for an easy y2k streetwear fit; layer the vintage black denim jacket (w_006) when it's cooler."* This is saved to `session["outfit_suggestion"]`.

*(Note: the "baggy jeans and chunky sneakers" mentioned in the query aren't parsed into the wardrobe — the wardrobe is selected separately via the UI radio in `app.py` (`get_example_wardrobe()` vs `get_empty_wardrobe()`). Those pieces appear in the outfit because they already exist in the example wardrobe as `w_001` and `w_007`.)*

**Step 3 — Fit card:**
<!-- Continue until the full interaction is complete -->
The agent calls `create_fit_card(outfit=<that suggestion>, new_item=<Y2K baby tee dict>)`. Since the outfit string is non-empty, it calls the LLM at a higher temperature and returns a casual caption mentioning the item name, price, and platform once each — e.g. *"Found this y2k butterfly baby tee on depop for $18 and it's already my new favorite. Throwing it on with my baggy jeans + chunky sneakers. Full fit in my stories 💕"* This is saved to `session["fit_card"]`, and the loop returns the completed session.

**Error path:**
If `search_listings` returns `[]` (e.g. "designer ballgown size XXS under $5"), the loop sets `session["error"]` to a helpful "no matches found — try a higher price or broader description" message and **returns early** — it never calls `suggest_outfit` or `create_fit_card` with empty input.

**Final output to user:**
<!-- What does the user actually see at the end? -->
On success, the user sees the matched item (`selected_item["title"]` — the Y2K baby tee at $18), the suggested outfit built from their wardrobe, and the shareable fit-card caption. On the error path, they instead see the `session["error"]` message, and the `outfit_suggestion` / `fit_card` fields are `None`.
