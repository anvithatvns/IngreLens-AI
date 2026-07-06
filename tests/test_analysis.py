"""IngreLens AI — Unit Tests"""
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.services.analysis_service import (
    IngredientKnowledgeBase, IngredientParser, ClassificationEngine,
    IngredientAnalysisService, VectorStore
)

# ── Knowledge Base Tests ──────────────────────────────────────────────────────
class TestKnowledgeBase:
    def setup_method(self):
        self.kb = IngredientKnowledgeBase()

    def test_loads_ingredients(self):
        assert len(self.kb.get_all()) > 50

    def test_exact_lookup(self):
        result = self.kb.lookup("milk")
        assert result is not None
        assert result["vegan_status"] == "non-vegan"

    def test_alias_lookup(self):
        result = self.kb.lookup("whey protein")
        assert result is not None
        assert result["vegan_status"] == "non-vegan"

    def test_unknown_returns_none(self):
        result = self.kb.lookup("xyzunknowningredient12345")
        assert result is None

    def test_gelatin_is_non_vegetarian(self):
        result = self.kb.lookup("gelatin")
        assert result["vegetarian_status"] == "non-vegetarian"


# ── Parser Tests ──────────────────────────────────────────────────────────────
class TestIngredientParser:
    def setup_method(self):
        self.parser = IngredientParser()

    def test_basic_parsing(self):
        result = self.parser.parse("Milk, Sugar, Salt")
        assert len(result) == 3
        assert "Milk" in result

    def test_percentage_removal(self):
        result = self.parser.parse("Hazelnuts (13%), Milk (8.7%)")
        assert any("Hazelnuts" in r for r in result)

    def test_handles_semicolons(self):
        result = self.parser.parse("Sugar; Salt; Water")
        assert len(result) == 3

    def test_ingredients_prefix_stripped(self):
        result = self.parser.parse("Ingredients: Milk, Sugar")
        assert "Milk" in result

    def test_empty_input(self):
        result = self.parser.parse("")
        assert result == []


# ── Classification Tests ──────────────────────────────────────────────────────
class TestClassificationEngine:
    def setup_method(self):
        self.kb = IngredientKnowledgeBase()
        self.vs = VectorStore(self.kb)
        self.engine = ClassificationEngine(self.kb, self.vs)

    def test_milk_is_non_vegan(self):
        result = self.engine.classify("Milk")
        assert result.vegan_status == "non-vegan"

    def test_sugar_is_vegan(self):
        result = self.engine.classify("Sugar")
        assert result.vegan_status == "vegan"

    def test_gelatin_is_non_vegetarian(self):
        result = self.engine.classify("Gelatin")
        assert "non-vegetarian" in result.vegetarian_status

    def test_carmine_is_non_vegan(self):
        result = self.engine.classify("Carmine")
        assert result.vegan_status == "non-vegan"

    def test_natural_flavors_are_uncertain(self):
        result = self.engine.classify("Natural Flavors")
        assert result.vegan_status in ["uncertain", "usually vegan"]

    def test_allergen_detection_dairy(self):
        result = self.engine.classify("Skimmed milk powder")
        assert "dairy" in result.allergens

    def test_allergen_detection_nuts(self):
        result = self.engine.classify("Almond flour")
        assert "tree nuts" in result.allergens


# ── Integration Tests ─────────────────────────────────────────────────────────
class TestAnalysisService:
    def setup_method(self):
        self.svc = IngredientAnalysisService()

    def test_nutella_not_vegan(self):
        result = self.svc.analyze(
            "Sugar, Palm oil, Hazelnuts (13%), Skimmed milk powder (8.7%), Cocoa, Soya lecithin, Vanillin",
            "Nutella"
        )
        assert result.overall_vegan != "Vegan"
        assert len(result.non_vegan_ingredients) > 0

    def test_almond_milk_is_vegan(self):
        result = self.svc.analyze(
            "Water, Almonds (2%), Calcium carbonate, Sea salt, Sunflower lecithin, Vitamin D2",
            "Almond Milk"
        )
        assert result.overall_vegan in ["Vegan", "Uncertain"]  # Uncertain due to natural flavors possible

    def test_whey_protein_not_vegan(self):
        result = self.svc.analyze(
            "Whey protein isolate, Whey protein concentrate, Cocoa powder",
            "Whey Protein"
        )
        assert result.overall_vegan != "Vegan"
        assert any("whey" in i.lower() for i in result.non_vegan_ingredients)

    def test_allergen_detection(self):
        result = self.svc.analyze("Milk, Sugar, Almond flour, Eggs, Wheat flour", "Test")
        assert "dairy" in result.allergens_detected
        assert "tree nuts" in result.allergens_detected
        assert "eggs" in result.allergens_detected
        assert "gluten" in result.allergens_detected

    def test_empty_ingredients(self):
        result = self.svc.analyze("", "Empty")
        assert result.overall_vegan == "Unknown"

    def test_vegan_burger(self):
        result = self.svc.analyze(
            "Water, Soy protein concentrate, Coconut oil, Sunflower oil, Potato protein, Salt, Yeast extract",
            "Vegan Burger"
        )
        assert result.overall_vegan in ["Vegan", "Uncertain"]

    def test_health_score_range(self):
        result = self.svc.analyze("Sugar, Water, Salt", "Simple")
        assert 0 <= result.health_score <= 100

    def test_ultra_processed_detection(self):
        result = self.svc.analyze(
            "Sugar, High fructose corn syrup, Artificial flavor, Maltodextrin, Modified starch, Red 40, Yellow 5",
            "Ultra Processed"
        )
        assert len(result.ultra_processed_markers) > 0

    def test_oreo_vegan_uncertainty(self):
        result = self.svc.analyze(
            "Unbleached enriched flour, Sugar, Palm and/or canola oil, Cocoa powder, High fructose corn syrup, Soy lecithin, Vanillin",
            "Oreo"
        )
        # Oreo main ingredients are vegan, but soy lecithin is uncertain
        assert result.overall_vegan in ["Vegan", "Uncertain"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
