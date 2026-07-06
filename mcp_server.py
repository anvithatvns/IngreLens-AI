"""
IngreLens AI — MCP Server.

Exposes the same Coordinator Agent used inside the Streamlit app (see
backend/services/coordinator_agent.py) as a set of Model Context Protocol
tools, so any MCP-compatible client — Claude Desktop, an IDE agent, a
custom orchestrator — can call into IngreLens AI's ingredient analysis
without going through the web UI at all.

This is not a second copy of the routing logic: every tool below is a thin
wrapper that calls CoordinatorAgent.handle() and reshapes the result into
plain JSON-serializable data for the MCP transport. The decision logic
(which specialist agent runs for which kind of input) lives in exactly one
place — the Coordinator — and both the Streamlit UI and this server share it.

Run it:
    python mcp_server.py                     # stdio transport (for Claude
                                              # Desktop / most MCP clients)

Claude Desktop config (claude_desktop_config.json):
    {
      "mcpServers": {
        "ingrelens-ai": {
          "command": "python",
          "args": ["/absolute/path/to/mcp_server.py"]
        }
      }
    }
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mcp.server.fastmcp import FastMCP

from backend.services.product_service import ProductFetchService
from backend.services.ocr_service import OCRService
from backend.services.analysis_service import IngredientAnalysisService
from backend.services.llm_service import IngredientAnalystAgent
from backend.services.coordinator_agent import CoordinatorAgent

mcp = FastMCP("ingrelens-ai")

_analysis_service = IngredientAnalysisService()
_coordinator = CoordinatorAgent(
    product_service=ProductFetchService(),
    ocr_service=OCRService(),
    analysis_service=_analysis_service,
    analyst_agent=IngredientAnalystAgent(_analysis_service),
)


def _analysis_to_dict(result) -> dict:
    """AnalysisResult -> plain dict, safe to return over MCP's JSON transport."""
    return {
        "product_name": result.product_name,
        "overall_vegan": result.overall_vegan,
        "diet_category": getattr(result, "diet_category", result.overall_vegan),
        "vegan_confidence": round(result.vegan_confidence, 2),
        "health_score": result.health_score,
        "non_vegan_ingredients": result.non_vegan_ingredients,
        "uncertain_ingredients": result.uncertain_ingredients,
        "allergens_detected": result.allergens_detected,
        "health_flags": result.health_flags,
        "recommendations": result.recommendations,
    }


@mcp.tool()
def analyze_ingredients(ingredients_text: str, product_name: str = "") -> dict:
    """Analyze a raw ingredient list for vegan/vegetarian status, allergens,
    and a health score. Routes through the Coordinator Agent, which invokes
    the Classification Agent (5-layer knowledge-base + vector-search engine).

    Args:
        ingredients_text: Comma-separated ingredient list, e.g.
            "Sugar, Palm oil, Skimmed milk powder, Soya lecithin".
        product_name: Optional product name for the result.
    """
    result = _coordinator.handle(ingredients_text=ingredients_text, product_name=product_name)
    if result.kind == "error":
        return {"error": result.message}
    return {"agents_used": result.agents_used, **_analysis_to_dict(result.analysis)}


@mcp.tool()
def analyze_barcode(barcode: str) -> dict:
    """Look up a product by barcode (EAN/UPC) via Open Food Facts and
    analyze its ingredients. Routes through the Coordinator Agent, which
    invokes the Product Fetch Agent, then the Classification Agent.

    Args:
        barcode: EAN-13 or UPC-A barcode, e.g. "3017624010701".
    """
    result = _coordinator.handle(barcode=barcode)
    if result.kind == "error":
        return {"error": result.message}
    return {"agents_used": result.agents_used, **_analysis_to_dict(result.analysis)}


@mcp.tool()
def ask_ingredient_question(question: str) -> str:
    """Ask a free-form question about ingredients, diets, or food labeling
    (e.g. "Is carrageenan vegan?", "What is L-cysteine made from?"). Routes
    through the Coordinator Agent to the AI Analyst Agent — no product
    lookup or classification runs for a bare question.

    Args:
        question: A natural-language question.
    """
    result = _coordinator.handle(question=question)
    if result.kind == "error":
        return result.message
    return result.message


if __name__ == "__main__":
    mcp.run(transport="stdio")
