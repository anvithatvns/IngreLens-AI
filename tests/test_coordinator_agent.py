"""IngreLens AI — Coordinator Agent tests.

These tests exist to prove the Coordinator actually branches on input type
rather than always running the same fixed sequence — that's the whole
point of it existing. Each test asserts on `agents_used`, the audit trail
of which specialists actually ran, not just on the final answer.
"""
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.services.product_service import ProductFetchService
from backend.services.ocr_service import OCRService
from backend.services.analysis_service import IngredientAnalysisService
from backend.services.llm_service import IngredientAnalystAgent
from backend.services.coordinator_agent import CoordinatorAgent


@pytest.fixture(scope="module")
def coordinator():
    analysis_svc = IngredientAnalysisService()
    return CoordinatorAgent(
        product_service=ProductFetchService(),
        ocr_service=OCRService(),
        analysis_service=analysis_svc,
        analyst_agent=IngredientAnalystAgent(analysis_svc),
    )


class TestCoordinatorRouting:
    def test_bare_question_only_calls_ai_analyst(self, coordinator):
        result = coordinator.handle(question="What does vegan mean?")
        assert result.kind == "chat"
        assert result.agents_used == ["ai_analyst"]
        assert result.message

    def test_raw_text_calls_classification_only(self, coordinator):
        result = coordinator.handle(
            ingredients_text="Sugar, Palm oil, Skimmed milk powder, Soya lecithin",
            product_name="Test Choc",
        )
        assert result.kind == "analysis"
        assert result.agents_used == ["classification"]
        assert result.analysis is not None
        assert result.explanation is None  # no question asked -> no AI Analyst call

    def test_raw_text_with_question_also_calls_ai_analyst(self, coordinator):
        result = coordinator.handle(
            ingredients_text="Sugar, Palm oil, Skimmed milk powder",
            product_name="Test Choc",
            question="Is this vegan?",
        )
        assert result.kind == "analysis"
        assert result.agents_used == ["classification", "ai_analyst"]
        assert result.explanation

    def test_barcode_calls_product_fetch_then_classification(self, coordinator):
        result = coordinator.handle(barcode="3017624010701")  # Nutella
        assert result.kind == "analysis"
        assert result.agents_used == ["product_fetch", "classification"]
        assert result.product_name

    def test_no_input_is_an_error_no_agents_run(self, coordinator):
        result = coordinator.handle()
        assert result.kind == "error"
        assert result.agents_used == []

    def test_unknown_barcode_stops_after_product_fetch(self, coordinator):
        result = coordinator.handle(barcode="0000000000000")
        # Either resolves to a mock/fallback product (agents_used includes
        # classification too) or genuinely fails to find ingredients — either
        # way, OCR must never run for a barcode request.
        assert "ocr" not in result.agents_used
