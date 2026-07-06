"""
IngreLens AI — Coordinator Agent.

This is the multi-agent decision point for the whole system. Every other
"agent" (Product Fetch, OCR, Classification, AI Analyst) is a specialist
that knows how to do exactly one thing. The Coordinator is the one piece
that looks at what the caller actually gave it — a barcode, an image, raw
ingredient text, a free-form question, or some combination — and decides
which specialist(s) to invoke and in what order, before handing back a
single unified result.

This is deliberately NOT a fixed pipeline. A barcode request never touches
OCR; an image never re-fetches from Open Food Facts; a bare question never
runs classification at all. The branch actually taken depends on the input,
which is what separates this from a script that always calls A -> B -> C -> D.

It is used by two independent callers that both need this same routing
decision:
  - the in-app floating assistant (shared_ui.ask_assistant)
  - the MCP server (mcp_server.py), which exposes it as a tool for any
    MCP-compatible client (Claude Desktop, an IDE agent, etc.)

Both call through this one class, so the decision logic only exists once.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CoordinatorResult:
    """Unified response shape regardless of which path was taken, so callers
    (UI, MCP server) don't need to know which specialists ran."""
    kind: str                      # "chat" | "analysis" | "error"
    message: Optional[str] = None  # chat answer, or error message
    product_name: Optional[str] = None
    analysis: Optional[object] = None      # AnalysisResult, when kind == "analysis"
    explanation: Optional[str] = None      # AI Analyst's natural-language explanation
    agents_used: list = field(default_factory=list)  # audit trail of which specialists ran


class CoordinatorAgent:
    """Routes a request to the right specialist agent(s) based on input type.

    Decision rules (in priority order):
      1. A bare question with no product input -> AI Analyst Agent only
         (chat/FAQ-style answer, no product data to reason about).
      2. A barcode -> Product Fetch Agent, then Classification Agent, then
         (only if a question was also asked) AI Analyst Agent to explain.
      3. Raw image bytes -> OCR Agent, then the same downstream chain as above.
      4. Raw ingredient text -> Classification Agent directly, then AI Analyst
         only if a question was also asked.
    """

    def __init__(self, product_service, ocr_service, analysis_service, analyst_agent):
        self.product_service = product_service
        self.ocr_service = ocr_service
        self.analysis_service = analysis_service
        self.analyst_agent = analyst_agent

    def handle(
        self,
        *,
        barcode: str = None,
        image_file=None,
        ingredients_text: str = None,
        product_name: str = "",
        question: str = None,
    ) -> CoordinatorResult:
        agents_used = []

        # Whitespace-only text is the same as no text — a pasted blank/blank
        # OCR read shouldn't silently run classification on nothing.
        if ingredients_text is not None and not ingredients_text.strip():
            ingredients_text = None

        # Rule 1: a bare question, nothing to analyze -> AI Analyst only.
        if question and not (barcode or image_file or ingredients_text):
            agents_used.append("ai_analyst")
            answer = self.analyst_agent.answer(question)
            return CoordinatorResult(kind="chat", message=answer, agents_used=agents_used)

        # Rule 2: barcode -> Product Fetch Agent resolves it to raw ingredients.
        if barcode:
            agents_used.append("product_fetch")
            product = self.product_service.fetch_by_barcode(barcode)
            if not product or not product.get("ingredients_text"):
                return CoordinatorResult(
                    kind="error",
                    message=f"No ingredient data found for barcode {barcode!r}.",
                    agents_used=agents_used,
                )
            ingredients_text = product["ingredients_text"]
            product_name = product.get("name") or product_name

        # Rule 3: an image -> OCR Agent extracts the ingredient text.
        elif image_file is not None:
            agents_used.append("ocr")
            extracted = self.ocr_service.extract_text(image_file)
            if not extracted:
                return CoordinatorResult(
                    kind="error",
                    message="Could not read any ingredient text from that image.",
                    agents_used=agents_used,
                )
            ingredients_text = extracted

        # Rule 4: still nothing to analyze -> nothing left to do.
        if not ingredients_text:
            return CoordinatorResult(
                kind="error",
                message="No ingredients to analyze — provide a barcode, image, or ingredient list.",
                agents_used=agents_used,
            )

        # Classification Agent always runs once we have ingredient text,
        # regardless of which path produced it.
        agents_used.append("classification")
        result = self.analysis_service.analyze(ingredients_text, product_name or "Unknown Product")

        explanation = None
        if question:
            agents_used.append("ai_analyst")
            explanation = self.analyst_agent.analyze_and_explain(ingredients_text, product_name)

        return CoordinatorResult(
            kind="analysis",
            product_name=result.product_name,
            analysis=result,
            explanation=explanation,
            agents_used=agents_used,
        )
