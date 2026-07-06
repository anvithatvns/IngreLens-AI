"""
IngreLens AI — ADK tool definitions.

Each function here is a plain, typed, documented Python function — ADK's
`FunctionTool` wraps a function directly (its docstring becomes the tool
description the LLM sees, and its type hints become the tool's schema).
None of these functions contain new logic: they are thin wrappers around
the exact same service classes the Streamlit app and the MCP server use
(backend/services/*.py), so there is exactly one implementation of each
capability, not a second copy for ADK.
"""
from google.adk.tools import FunctionTool

from backend.services.product_service import ProductFetchService
from backend.services.ocr_service import OCRService
from backend.services.analysis_service import IngredientAnalysisService

_product_service = ProductFetchService()
_ocr_service = OCRService()
_analysis_service = IngredientAnalysisService()


def fetch_product_by_barcode(barcode: str) -> dict:
    """Look up a food product by its barcode (EAN-13 or UPC-A) via Open Food
    Facts, falling back to a clearly-labeled mock product if the barcode is
    unrecognized so the caller always has something to analyze.

    Args:
        barcode: The barcode digits, e.g. "3017624010701".

    Returns:
        A dict with at least "name", "brand", and "ingredients_text".
    """
    product = _product_service.fetch_by_barcode(barcode)
    return product or {"error": f"No product found for barcode {barcode!r}"}


def extract_ingredients_from_label_image(image_path: str) -> dict:
    """Run OCR on a food label image to extract its ingredient text.

    Args:
        image_path: Path to a label image file (jpg/png).

    Returns:
        A dict with "ingredients_text", or "error" if nothing could be read.
    """
    with open(image_path, "rb") as f:
        text = _ocr_service.extract_text(f)
    if not text:
        return {"error": "Could not read any ingredient text from that image."}
    return {"ingredients_text": text}


def classify_ingredients(ingredients_text: str, product_name: str = "Unknown Product") -> dict:
    """Classify a raw ingredient list: vegan/vegetarian/eggetarian/
    non-vegetarian status, allergens, and a 0-100 health score. This is the
    single call that also powers the Nutrition figures (health score,
    Nutri-Score-adjacent flags) — there is no separate nutrition network
    call, the same analysis pass computes both.

    Args:
        ingredients_text: Comma-separated ingredient list.
        product_name: Optional product name for the result.

    Returns:
        A dict with overall_vegan, diet_category, health_score,
        allergens_detected, non_vegan_ingredients, and recommendations.
    """
    result = _analysis_service.analyze(ingredients_text, product_name)
    return {
        "product_name": result.product_name,
        "overall_vegan": result.overall_vegan,
        "diet_category": getattr(result, "diet_category", result.overall_vegan),
        "vegan_confidence": round(result.vegan_confidence, 2),
        "health_score": result.health_score,
        "non_vegan_ingredients": result.non_vegan_ingredients,
        "uncertain_ingredients": result.uncertain_ingredients,
        "allergens_detected": result.allergens_detected,
        "recommendations": result.recommendations,
    }


def get_nutrition_summary(ingredients_text: str, product_name: str = "Unknown Product") -> dict:
    """Get just the nutrition/health slice of an ingredient analysis (health
    score and any health flags), for callers that only care about that and
    not the vegan/allergen classification.

    Args:
        ingredients_text: Comma-separated ingredient list.
        product_name: Optional product name for the result.

    Returns:
        A dict with health_score and health_flags.
    """
    result = _analysis_service.analyze(ingredients_text, product_name)
    return {
        "product_name": result.product_name,
        "health_score": result.health_score,
        "health_flags": result.health_flags,
        "ultra_processed_markers": result.ultra_processed_markers,
        "preservatives": result.preservatives,
    }


product_fetch_tool = FunctionTool(fetch_product_by_barcode)
ocr_tool = FunctionTool(extract_ingredients_from_label_image)
classification_tool = FunctionTool(classify_ingredients)
nutrition_tool = FunctionTool(get_nutrition_summary)
