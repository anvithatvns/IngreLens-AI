"""
Tests for the ADK agent layer (backend/adk/).

These deliberately do NOT run a live LLM turn — that needs GOOGLE_API_KEY or
Vertex AI credentials, which CI/local dev may not have (mirrors how the free
tier already works without any LLM key). What's verified here is that the
wiring is correct: every tool/agent/toolset object constructs without error,
the Coordinator's tools and sub-agents are exactly the ones the architecture
doc claims, and the ADK<->MCP connection can genuinely list our 3 MCP tools
(a real subprocess handshake, no model call involved).
"""
import asyncio
import sys

import pytest

from backend.adk.tools import (
    product_fetch_tool,
    ocr_tool,
    classification_tool,
    nutrition_tool,
    fetch_product_by_barcode,
    classify_ingredients,
)
from backend.adk.agents import (
    root_agent,
    classification_agent,
    ai_analyst_agent,
    mcp_backed_coordinator,
)


class TestADKTools:
    def test_all_four_tools_are_function_tools(self):
        for tool in [product_fetch_tool, ocr_tool, classification_tool, nutrition_tool]:
            assert tool.name

    def test_tool_names_match_underlying_functions(self):
        assert product_fetch_tool.name == "fetch_product_by_barcode"
        assert ocr_tool.name == "extract_ingredients_from_label_image"
        assert classification_tool.name == "classify_ingredients"
        assert nutrition_tool.name == "get_nutrition_summary"

    def test_underlying_functions_still_work_directly(self):
        # The ADK wrapper adds no logic — the function must behave exactly
        # like calling the service directly.
        result = classify_ingredients("Sugar, Palm oil, Skimmed milk powder", "Test")
        assert result["overall_vegan"] != "Vegan"

    def test_barcode_tool_never_errors_on_unknown_barcode(self):
        result = fetch_product_by_barcode("0000000000000")
        assert "error" not in result
        assert result.get("ingredients_text")


class TestADKAgents:
    def test_root_agent_is_the_coordinator(self):
        assert root_agent.name == "ingrelens_coordinator"

    def test_root_agent_has_three_deterministic_tools(self):
        tool_names = {t.name for t in root_agent.tools}
        assert tool_names == {
            "fetch_product_by_barcode",
            "extract_ingredients_from_label_image",
            "get_nutrition_summary",
        }

    def test_root_agent_delegates_to_two_reasoning_sub_agents(self):
        sub_agent_names = {a.name for a in root_agent.sub_agents}
        assert sub_agent_names == {"classification_agent", "ai_analyst_agent"}

    def test_classification_agent_only_has_classification_tool(self):
        assert [t.name for t in classification_agent.tools] == ["classify_ingredients"]

    def test_ai_analyst_agent_has_no_tools_pure_reasoning_fallback(self):
        assert ai_analyst_agent.tools == []

    def test_mcp_backed_coordinator_constructs_with_one_mcp_toolset(self):
        agent = mcp_backed_coordinator()
        assert agent.name == "ingrelens_coordinator_mcp"
        assert len(agent.tools) == 1


class TestADKMCPIntegration:
    def test_adk_can_list_tools_from_our_own_mcp_server(self):
        """Real, no-mock proof of the ADK -> MCP -> Tools path: spawn
        mcp_server.py as a subprocess over stdio via ADK's McpToolset and
        confirm it can see our 3 real tools. No LLM call is involved in
        listing tools, so this needs no API key."""
        from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams
        from mcp import StdioServerParameters
        import pathlib

        server_path = str(
            pathlib.Path(__file__).resolve().parent.parent / "mcp_server.py"
        )

        async def _list():
            toolset = McpToolset(
                connection_params=StdioConnectionParams(
                    server_params=StdioServerParameters(
                        command=sys.executable, args=[server_path]
                    ),
                    timeout=30.0,
                ),
            )
            try:
                tools = await toolset.get_tools()
                return {t.name for t in tools}
            finally:
                await toolset.close()

        names = asyncio.run(_list())
        assert names == {"analyze_ingredients", "analyze_barcode", "ask_ingredient_question"}
