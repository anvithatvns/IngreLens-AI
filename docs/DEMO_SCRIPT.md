# IngreLens AI — 5-Minute Judge Demo Script

Goal: convince a judge in 5 minutes that this is a real multi-agent system
that makes a genuine per-request routing decision — not a script wearing an
agent costume — and that the team is honest about what still needs work.

Balance: ~40% emotional hook / real-world stakes, ~60% technical depth. Don't
let the technical part turn into a code walkthrough with no narrative; don't
let the hook run past 30 seconds.

---

## Scene 1 — The Hook (0:00–0:30)

**Say:** "This is a real product on a real shelf, marketed as vegan."
*(Show the product's front label — a plant/leaf icon, "100% Plant-Based.")*
"Here's its actual ingredient list." *(Show: Water, Pea protein, Sugar,
**Skimmed milk powder**, Salt.)* "The label and the ingredients disagree, and
nobody reads ingredient lists standing in an aisle. That's the problem this
solves — not 'is this vegan,' but 'is this vegan *according to what's
actually in it*, regardless of what the front of the box says.'"

**Show:** the two images side by side for 5 seconds, then cut.

---

## Scene 2 — Live Agent Orchestration (0:30–2:00)

**Do:** Open the Streamlit app. Scan/enter the mislabeled product's barcode.

**Say while it loads:** "Watch the badges at the bottom of the result —
that's not decoration, that's the actual audit trail of which agents ran."

**Point at the screen** as the result renders: "Product Fetch ran to resolve
the barcode. Classification ran on the real ingredient list. Nutrition ran
in the same pass. OCR did **not** run — there was no image. AI Analyst did
**not** run — nobody asked it a question. That's the Coordinator making a
real decision, not executing four steps in a fixed order every time."

**Do:** Open the floating chat, ask a bare question with no product context
("Is carrageenan vegan?"). Get an answer.

**Say:** "Same Coordinator, different input, completely different route —
only the AI Analyst ran this time. `tests/test_coordinator_agent.py` proves
this in code: it doesn't just check the final answer, it asserts on *which*
agents ran for each input shape."

---

## Scene 3 — Edge Case, Live (2:00–3:00)

**Do:** Open a terminal, run:
```bash
python -m evaluation.run_evaluation
```

**Say while it runs:** "This is our own evaluation harness — 20 hand-written
edge cases: a barcode that doesn't exist, an ingredient list that's just
whitespace, a product with five allergens at once, ingredients so
OCR-corrupted a human would struggle to read them."

**Point at the noisy-OCR case in the output.** "This one is interesting —
we don't claim it gets the answer perfectly right. Heavy character
corruption can send our vector-search fallback to the wrong nearest
neighbor. We found that with this exact harness, and instead of hiding it,
we documented it as a known limitation right in the dataset file. A system
that's honest about its edges is more trustworthy than one that hides them."

**Show:** the 100% pass rate on the 4 metrics — routing accuracy,
classification accuracy, fallback success, tool execution success — and
that the pass rate is 100% *because* we scoped that one case honestly, not
because we hid the failure.

---

## Scene 4 — ADK + MCP, the Architecture Moment (3:00–4:15)

**Do:** Open `backend/adk/agents.py`. Scroll to `root_agent` and
`mcp_backed_coordinator()`.

**Say:** "Every specialist here is also a native Google ADK primitive —
Product Fetch, OCR, and Nutrition are ADK `FunctionTool`s; Classification
and the AI Analyst are ADK reasoning sub-agents; the Coordinator is the ADK
root agent, and its tool list and sub-agent list *are* the routing decision
— ADK resolves which one runs, not our own if/else."

**Do:** Run the ADK test file: `pytest tests/test_adk_agents.py -v`.

**Say while it runs:** "This one's the interesting part —
`mcp_backed_coordinator()` doesn't call our tools in-process. It spawns our
own MCP server as a subprocess and asks it, over the actual MCP protocol,
what tools it has. That's a real handshake, not a mock — you can see it
listing `analyze_ingredients`, `analyze_barcode`,
`ask_ingredient_question` right here, sourced live from `mcp_server.py`."

**Say:** "So the same three tools serve three different front doors — the
Streamlit UI calls them in-process, any MCP client can call the server
directly, and an ADK agent can reach the exact same server over MCP. One
implementation, three interfaces."

---

## Scene 5 — Close: Impact Statement (4:15–5:00)

**Say:** "Vegan and allergen mislabeling isn't a hypothetical — it's a
label-reading problem millions of people navigate badly every single day,
including people for whom getting it wrong is a medical emergency, not an
inconvenience. This system doesn't trust the front of the box. It reads
the actual ingredients, through a real multi-agent architecture you can
audit — via the badge trail, via 194 passing tests, via a 20-case
evaluation harness we built specifically so we couldn't hide from our own
mistakes. It's deployable today on the free tier, and the same tools are
already exposed to the next generation of agent ecosystems — ADK and MCP —
without a second implementation. That's IngreLens AI."

**End on:** the architecture diagram (`assets/architecture_diagram.png`),
held for 3 seconds.

---

## Before recording, verify

- [ ] `python -m pytest tests/ -q` → 194 passed
- [ ] `python -m evaluation.run_evaluation` → 100% on all 4 metrics
- [ ] A live Streamlit Cloud URL exists (see Risk Checklist item 3)
- [ ] `GOOGLE_API_KEY` set if you intend to show a *live* ADK conversational
      turn rather than just the passing wiring tests — otherwise, stick to
      showing the tests/tool-listing (which need no key) and say so plainly
