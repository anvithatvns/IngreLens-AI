"""
IngreLens AI — ADK agent definitions.

Maps the existing 5 specialists onto native ADK primitives:

    Product Fetch  -> ADK FunctionTool  (deterministic data fetch, no reasoning)
    OCR            -> ADK FunctionTool  (deterministic extraction, no reasoning)
    Nutrition      -> ADK FunctionTool  (deterministic computation, no reasoning)
    Classification -> ADK LlmAgent      (reasoning sub-agent: explains *why*,
                                          not just classify_ingredients' raw output)
    AI Analyst     -> ADK LlmAgent      (fallback reasoning sub-agent for
                                          free-form questions with no product data)

`root_agent` is the ADK Coordinator — the same routing decision
CoordinatorAgent.handle() makes in Python is here expressed natively: an
LlmAgent whose instruction tells it which tool or sub-agent to use for a
given input, and whose `tools`/`sub_agents` ARE that decision's real options
(ADK, not our own if/else, resolves which one actually gets called).

This module additionally exposes the same 3 capabilities as an McpToolset
pointed at our own mcp_server.py over stdio — i.e. the Coordinator can reach
its tools two ways: directly (in-process FunctionTools, above) or via MCP
(out-of-process, the same server any other MCP client uses). See
`mcp_backed_coordinator()` below.

Running a live turn requires GOOGLE_API_KEY (or Vertex AI credentials) to be
set — LlmAgent is inherently model-backed. Without a key, every object here
still constructs correctly (verified in tests/test_adk_agents.py), which is
what proves the wiring is right; it just can't process a live request. This
mirrors the project's existing free-tier pattern for llm_service.py: the
deterministic CoordinatorAgent (backend/services/coordinator_agent.py)
remains the zero-configuration path the Streamlit app and MCP server use by
default. This ADK layer is an additional, opt-in interface onto the same
underlying tools, not a replacement for the working one.
"""
import sys
from pathlib import Path

from google.adk.agents import Agent
from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams
from mcp import StdioServerParameters

from backend.adk.tools import (
    product_fetch_tool,
    ocr_tool,
    classification_tool,
    nutrition_tool,
)

_MCP_SERVER_PATH = str(Path(__file__).resolve().parent.parent.parent / "mcp_server.py")
_MODEL = "gemini-2.0-flash"


# ── Classification: reasoning sub-agent ───────────────────────────────────────
classification_agent = Agent(
    name="classification_agent",
    model=_MODEL,
    description=(
        "Explains WHY a product's ingredients are vegan/vegetarian/eggetarian/"
        "non-vegetarian/uncertain, and what allergens it contains — reasons "
        "about the classify_ingredients tool's output rather than just "
        "returning it verbatim."
    ),
    instruction=(
        "You classify food ingredient lists. Always call classify_ingredients "
        "first, then explain the result in plain language: state the diet "
        "category, name the specific ingredient(s) responsible for that "
        "category, list any allergens, and note the health score. Be factual "
        "and concise."
    ),
    tools=[classification_tool],
)

# ── AI Analyst: fallback reasoning sub-agent ─────────────────────────────────
ai_analyst_agent = Agent(
    name="ai_analyst_agent",
    model=_MODEL,
    description=(
        "Answers free-form questions about ingredients, diets, or food "
        "labeling that aren't tied to a specific product to classify — the "
        "fallback for anything the Classification agent's tool can't answer."
    ),
    instruction=(
        "You are a food ingredient expert. Answer the user's question "
        "directly and concisely. If the question is really about analyzing a "
        "specific ingredient list rather than a general question, say so and "
        "suggest the user provide the ingredient list instead."
    ),
    tools=[],
)

# ── Coordinator: ADK root agent ───────────────────────────────────────────────
root_agent = Agent(
    name="ingrelens_coordinator",
    model=_MODEL,
    description="Routes food/ingredient requests to the right IngreLens AI specialist.",
    instruction=(
        "You are the Coordinator for IngreLens AI. Decide which tool or "
        "sub-agent actually applies to the user's request — do not run all "
        "of them:\n"
        "- A barcode (a string of 8-14 digits) -> call fetch_product_by_barcode, "
        "then hand its ingredients_text to the classification_agent sub-agent.\n"
        "- A path to a label image -> call extract_ingredients_from_label_image, "
        "then hand its ingredients_text to the classification_agent sub-agent.\n"
        "- A raw ingredient list -> hand it directly to the classification_agent "
        "sub-agent.\n"
        "- A free-form question with no product/ingredients given -> hand it "
        "to the ai_analyst_agent sub-agent.\n"
        "- If the user also wants a nutrition/health breakdown, call "
        "get_nutrition_summary as well.\n"
        "Never call classification on an image or barcode directly — resolve "
        "it to ingredient text first."
    ),
    tools=[product_fetch_tool, ocr_tool, nutrition_tool],
    sub_agents=[classification_agent, ai_analyst_agent],
)


def mcp_backed_coordinator(timeout: float = 30.0) -> Agent:
    """Alternate Coordinator whose tools come from our MCP server over stdio
    instead of in-process FunctionTools — demonstrates the ADK -> MCP ->
    Tools path explicitly (see README's Architecture section). Functionally
    equivalent to `root_agent` for analyze_ingredients/analyze_barcode/
    ask_ingredient_question; it does not get the Nutrition/OCR/split-agent
    granularity above, since the MCP server exposes 3 coarser tools rather
    than the 4 fine-grained ones. A fresh instance is returned per call
    (the toolset spawns its own subprocess, so it isn't meant to be a
    module-level singleton read by multiple callers).
    """
    mcp_toolset = McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(command=sys.executable, args=[_MCP_SERVER_PATH]),
            timeout=timeout,
        ),
    )
    return Agent(
        name="ingrelens_coordinator_mcp",
        model=_MODEL,
        description="Same Coordinator role as root_agent, sourcing its tools from mcp_server.py over MCP instead of in-process.",
        instruction=(
            "You are the Coordinator for IngreLens AI. Use analyze_barcode for "
            "a barcode, analyze_ingredients for a raw ingredient list, and "
            "ask_ingredient_question for a free-form question with no product "
            "data. Only call one, based on what the user actually gave you."
        ),
        tools=[mcp_toolset],
    )
