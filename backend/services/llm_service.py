"""
IngreLens AI — LLM Service v3
Enhanced rule-based engine covering 80+ topics:
- Ingredient questions (vegan/diet status)
- Product comparisons (Coke vs Coke Zero etc.)
- Diet classification questions (eggetarian, vegan, etc.)
- E-number questions
- General food/health questions
- Nutritional comparisons
Falls back to OpenAI/Anthropic when API key is present.
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class LLMService:
    def __init__(self):
        self.provider  = settings.LLM_PROVIDER
        self.enabled   = settings.USE_LLM
        self._kb       = None
        if self.enabled:
            logger.info(f"LLM enabled — provider: {self.provider}")
        else:
            logger.info("FREE TIER mode — enhanced rule-based AI engine active")

    def _get_kb(self):
        if self._kb is None:
            try:
                from backend.services.analysis_service import IngredientKnowledgeBase
                self._kb = IngredientKnowledgeBase()
            except Exception:
                self._kb = None
        return self._kb

    def chat(self, system_prompt: str, user_message: str, context: str = "") -> str:
        if not self.enabled:
            return self._rule_based_response(user_message, context)
        try:
            if self.provider == "anthropic":
                return self._anthropic(system_prompt, user_message, context)
            return self._openai(system_prompt, user_message, context)
        except Exception as e:
            logger.warning(f"LLM call failed: {e} — falling back to rule-based")
            return self._rule_based_response(user_message, context)

    def _openai(self, system: str, user: str, context: str) -> str:
        from openai import OpenAI
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        full_user = f"Context:\n{context}\n\nQuestion: {user}" if context else user
        resp = client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[{"role":"system","content":system},{"role":"user","content":full_user}],
            max_tokens=settings.LLM_MAX_TOKENS, temperature=settings.LLM_TEMPERATURE,
        )
        return resp.choices[0].message.content.strip()

    def _anthropic(self, system: str, user: str, context: str) -> str:
        import anthropic
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        full_user = f"Context:\n{context}\n\nQuestion: {user}" if context else user
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001", max_tokens=settings.LLM_MAX_TOKENS,
            system=system, messages=[{"role":"user","content":full_user}],
        )
        return resp.content[0].text.strip()

    # ═══════════════════════════════════════════════════════════════════════════
    # RULE-BASED ENGINE — handles 80+ question types
    # ═══════════════════════════════════════════════════════════════════════════
    def _rule_based_response(self, question: str, context: str) -> str:
        q = question.lower().strip()

        # Early catch for 'what does vegan mean'
        if "what does vegan mean" in q or "define vegan" in q or (q.strip() in ["vegan meaning", "what is vegan"]):
            return (
                "\U0001f331 **What Does Vegan Mean?**\n\n"
                "A **vegan** diet excludes all animal products:\n"
                "\u274c Meat, poultry, fish and seafood\n"
                "\u274c Dairy (milk, butter, cheese, yogurt, whey, casein)\n"
                "\u274c Eggs\n"
                "\u274c Honey, beeswax, propolis, royal jelly\n"
                "\u274c Gelatin, isinglass, carmine, shellac, L-cysteine\n\n"
                "\u2705 All plant foods — vegetables, fruits, grains, legumes, nuts, seeds, oils\n\n"
                "**IngreLens AI** classifies into:\n"
                "\U0001f331 Vegan \u2192 \U0001f9c0 Vegetarian \u2192 \U0001f95a Eggetarian \u2192 \U0001f356 Non-Vegetarian"
            )

        # Explicit early catches that must fire BEFORE KB lookup
        if any(x in q for x in ["plant milk", "oat milk", "almond milk", "which milk", "best milk", "dairy free milk", "non-dairy milk", "milk alternative"]):
            return ("\U0001F95B **Plant Milk Comparison \u2014 Which is Best?**\n\n"
                    "| Milk | Calories | Protein | Vegan | Best For |\n"
                    "|---|---|---|---|---|\n"
                    "| **Oat Milk** | ~120 kcal | 3g | \u2705 | Coffee, baking |\n"
                    "| **Almond Milk** | ~30-60 kcal | 1g | \u2705 | Low-cal option |\n"
                    "| **Soy Milk** | ~80-100 kcal | 7g | \u2705 | High protein |\n"
                    "| **Coconut Milk** | ~45 kcal | 0g | \u2705 | Cooking, curries |\n"
                    "| **Rice Milk** | ~120 kcal | 1g | \u2705 | Allergy-friendly |\n"
                    "| **Hemp Milk** | ~80 kcal | 3g | \u2705 | Omega-3 rich |\n\n"
                    "**Best for protein:** Soy milk\n"
                    "**Best for coffee/lattes:** Oat milk (froths best)\n"
                    "**Best for weight loss:** Almond milk (lowest calories)\n\n"
                    "All plant milks are \U0001F331 **Vegan**!")

        if "e150" in q and not "e1500" in q:
            return ("\U0001F36F **Caramel Colour E150 \u2014 Vegan** \u2705\n\n"
                    "Caramel colour is produced by heating sugar \u2014 entirely plant-derived, no animal products.\n\n"
                    "| Code | Name | Used In |\n"
                    "|---|---|---|\n"
                    "| E150a | Plain caramel | General use |\n"
                    "| E150b | Caustic sulphite | Whisky, vinegar |\n"
                    "| E150c | Ammonia caramel | Beer, sauces |\n"
                    "| **E150d** | **Sulphite ammonia caramel** | **Coca-Cola, Pepsi, dark sodas** |\n\n"
                    "\u2705 All four types of caramel colour are **vegan**.\n\n"
                    "\u26a0\ufe0f **Health note:** E150c and E150d contain 4-methylimidazole (4-MEI), "
                    "flagged by WHO as possibly carcinogenic at very high doses. Amounts in food are considered safe.")

        # If context from analysis panel, synthesize from it
        if context and not any(skip in q for skip in ["better","compare","difference","vs","versus"]):
            lines = context.strip().split("\n")
            synth = self._synthesize_from_context(question, lines)
            if synth:
                return synth

        # ── PRODUCT COMPARISONS ───────────────────────────────────────────────
        if self._is_comparison(q):
            return self._handle_comparison(q)

        # ── DIET CLASSIFICATION QUESTIONS ─────────────────────────────────────
        if self._is_diet_question(q):
            return self._handle_diet_question(q)

        # ── E-NUMBER QUESTIONS ────────────────────────────────────────────────
        if self._is_enumber_question(q):
            return self._handle_enumber(q)

        # ── SPECIFIC INGREDIENT ANSWERS ───────────────────────────────────────
        answer = self._ingredient_answer(q)
        if answer:
            return answer

        # ── GENERAL FOOD/HEALTH QUESTIONS ─────────────────────────────────────
        general = self._general_food_answer(q)
        if general:
            return general

        # ── KB LOOKUP ─────────────────────────────────────────────────────────
        # Skip KB lookup for questions about plant milk (would return dairy 'milk' entry)
        if not any(x in q for x in ['plant milk','oat milk','almond milk','soy milk','which milk','best milk','dairy free milk','dairy-free milk','non-dairy milk']):
            kb_answer = self._kb_lookup_answer(q)
        else:
            kb_answer = None
        if kb_answer:
            return kb_answer

        # ── SMART FALLBACK (not the useless generic message) ──────────────────
        return self._smart_fallback(q)

    # ── COMPARISON DETECTION & HANDLING ──────────────────────────────────────
    def _is_comparison(self, q: str) -> bool:
        return any(kw in q for kw in [" vs ", " versus ", "better ", "difference between",
                                       "which is ", "compare ", "healthier ", "worse ",
                                       "coke zero", "diet coke", "zero sugar"])

    def _handle_comparison(self, q: str) -> str:
        # Coca-Cola vs Coke Zero / Diet Coke
        if any(x in q for x in ["coke zero","coke vs","coca cola vs","pepsi vs","diet coke",
                                  "coke or pepsi","pepsi or coke","zero sugar coke"]):
            if "coke zero" in q or "zero" in q or "diet" in q:
                return (
                    "🥤 **Coca-Cola vs Coke Zero — Which is Better?**\n\n"
                    "| | **Coca-Cola Classic** | **Coke Zero Sugar** |\n"
                    "|---|---|---|\n"
                    "| Calories | 140 kcal (355ml) | 0 kcal |\n"
                    "| Sugar | 39g | 0g |\n"
                    "| Sweetener | Cane sugar | Aspartame + Acesulfame K |\n"
                    "| Taste | Classic sweet | Closest to Classic |\n"
                    "| Vegan? | ⚠️ Uncertain (natural flavors) | ⚠️ Uncertain (natural flavors) |\n\n"
                    "**For fewer calories:** Coke Zero wins — zero sugar, zero calories.\n\n"
                    "**For taste:** Coke Zero is formulated to taste closest to Classic Coca-Cola.\n\n"
                    "**For health:** Neither is healthy. Both contain phosphoric acid (bad for teeth) "
                    "and caffeine. Coke Zero's artificial sweeteners (aspartame) are debated — "
                    "some studies suggest they may still trigger insulin response.\n\n"
                    "**Vegan status:** Both are considered *uncertain* — the 'natural flavors' "
                    "could theoretically include animal-derived compounds, though Coca-Cola "
                    "is generally considered vegan by most vegan organizations.\n\n"
                    "**Verdict:** If avoiding sugar, choose Coke Zero. If avoiding artificial "
                    "sweeteners, choose Classic in moderation. Water is always the healthiest choice! 💧"
                )

        # Pepsi vs Coca-Cola
        if "pepsi" in q and ("coke" in q or "coca" in q or "cola" in q):
            return (
                "🥤 **Pepsi vs Coca-Cola — The Classic Debate**\n\n"
                "| | **Pepsi** | **Coca-Cola** |\n"
                "|---|---|---|\n"
                "| Calories (355ml) | 150 kcal | 140 kcal |\n"
                "| Sugar | 41g | 39g |\n"
                "| Taste | Sweeter, lighter citrus | More caramel, slightly drier |\n"
                "| Caffeine | 38mg | 34mg |\n"
                "| Vegan? | ⚠️ Uncertain | ⚠️ Uncertain |\n\n"
                "**Key differences:**\n"
                "- Pepsi is slightly sweeter and has more citrus notes\n"
                "- Coca-Cola has a more distinct caramel, slightly more complex flavor\n"
                "- Both use caramel color (E150d) — vegan\n"
                "- Both have 'natural flavors' — origin unconfirmed\n\n"
                "**Verdict:** Taste is subjective! Pepsi tends to win blind taste tests "
                "(the 'Pepsi Challenge'), but Coca-Cola wins in brand loyalty and overall sales."
            )

        # Vegan milk alternatives
        if any(x in q for x in ["oat milk","almond milk","soy milk","which milk","plant milk","best milk","oat vs","dairy free milk","non dairy milk","non-dairy milk","milk alternative","milk comparison"]):
            return (
                "🥛 **Plant Milk Comparison — Which is Best?**\n\n"
                "| Milk | Calories | Protein | Vegan | Best For |\n"
                "|---|---|---|---|---|\n"
                "| **Oat Milk** | ~120 kcal | 3g | ✅ | Coffee, baking |\n"
                "| **Almond Milk** | ~30-60 kcal | 1g | ✅ | Low-cal option |\n"
                "| **Soy Milk** | ~80-100 kcal | 7g | ✅ | High protein |\n"
                "| **Coconut Milk** | ~45 kcal | 0g | ✅ | Cooking, curries |\n"
                "| **Rice Milk** | ~120 kcal | 1g | ✅ | Allergy-friendly |\n"
                "| **Hemp Milk** | ~80 kcal | 3g | ✅ | Omega-3 rich |\n"
                "| **Cow's Milk** | ~150 kcal | 8g | ❌ | Traditional use |\n\n"
                "**Best for protein:** Soy milk (closest to cow's milk protein content)\n"
                "**Best for coffee/lattes:** Oat milk (froths best, mild taste)\n"
                "**Best for weight loss:** Almond milk (lowest calories)\n"
                "**Best for allergies:** Rice milk (free from top allergens)\n"
                "**Best for omega-3:** Hemp milk\n\n"
                "All plant milks are 🌱 **Vegan**!"
            )

        # Butter vs margarine vs vegan butter
        if "butter" in q and any(x in q for x in ["margarine","vegan","plant"]):
            return (
                "🧈 **Butter vs Margarine vs Vegan Butter**\n\n"
                "| | **Dairy Butter** | **Margarine** | **Vegan Butter** |\n"
                "|---|---|---|---|\n"
                "| Vegan? | ❌ No (dairy) | ⚠️ Often vegan | ✅ Yes |\n"
                "| Fat type | Saturated | Trans/unsaturated | Unsaturated |\n"
                "| Taste | Rich, creamy | Varies | Close to butter |\n"
                "| Calories | ~100/tbsp | ~80-100/tbsp | ~80-100/tbsp |\n\n"
                "**Margarine** may contain whey or milk derivatives — always check the label.\n\n"
                "**Best vegan butter brands:** Miyoko's Creamery, Earth Balance, Violife, "
                "Flora Plant, Naturli Vegan Block."
            )

        # Default comparison response
        return self._smart_comparison_fallback(q)

    def _smart_comparison_fallback(self, q: str) -> str:
        return (
            "🔍 **Product Comparison**\n\n"
            "I can compare these product types — try asking:\n\n"
            "• *'Which is better: Coke or Coke Zero?'*\n"
            "• *'Oat milk vs almond milk — which is healthier?'*\n"
            "• *'Vegan butter vs regular butter — what's the difference?'*\n"
            "• *'Soy protein vs whey protein?'*\n\n"
            "For specific product analysis, use the **Analyzer** or **Compare** tab to get "
            "a full side-by-side breakdown of ingredients, vegan status, and health scores!"
        )

    # ── DIET CLASSIFICATION QUESTIONS ─────────────────────────────────────────
    def _is_diet_question(self, q: str) -> bool:
        diet_kw = ["eggetarian","vegetarian","vegan","non-veg","non veg","diet",
                   "plant based","plant-based","classification","classify",
                   "dairy free","dairy-free","what diet","which diet"]
        return any(kw in q for kw in diet_kw) and any(
            x in q for x in ["mean","what is","how","difference","mayonnaise","mayo",
                              "egg","considered","count","qualify","define"])

    def _handle_diet_question(self, q: str) -> str:

        # Mayonnaise + eggetarian
        if "mayo" in q and any(x in q for x in ["eggetarian","diet","vegan","vegetarian","dairy"]):
            return (
                "🥚 **Mayonnaise & Diet Classification**\n\n"
                "**Traditional mayonnaise** is made from:\n"
                "- Eggs (egg yolks) 🥚\n"
                "- Oil (vegetable/sunflower)\n"
                "- Vinegar or lemon juice\n"
                "- Salt, mustard\n\n"
                "**Is mayonnaise eggetarian?**\n"
                "✅ **Yes** — if it contains eggs but NO dairy and NO meat/fish.\n"
                "Traditional mayo with egg yolks but no dairy = **Eggetarian** 🥚\n\n"
                "**Is mayonnaise vegan?**\n"
                "❌ **No** — traditional mayo contains eggs.\n\n"
                "**Is mayonnaise vegetarian?**\n"
                "✅ **Yes** — eggs are acceptable in vegetarian diets (in most traditions).\n\n"
                "**Vegan mayo options:** Hellmann's Vegan Mayo, Just Mayo (JUST Inc.), "
                "Vegenaise — made with aquafaba (chickpea water) or modified starch instead of eggs."
            )

        # Eggetarian definition
        if "eggetarian" in q:
            return (
                "🥚 **What is Eggetarian?**\n\n"
                "**Eggetarian** (also called Ovo-vegetarian) is a diet that:\n\n"
                "✅ **Allows:**\n"
                "- All plant-based foods\n"
                "- Eggs and egg products (mayonnaise, albumin, egg pasta)\n\n"
                "❌ **Excludes:**\n"
                "- Meat (chicken, beef, pork, lamb)\n"
                "- Fish and seafood\n"
                "- Gelatin (from animal bones)\n"
                "- Other animal-derived products from slaughter\n\n"
                "⚠️ **Dairy:** Eggetarian may or may not include dairy — it varies by person.\n\n"
                "**IngreLens AI Classification:**\n"
                "- 🌱 Vegan = 100% plant-based\n"
                "- 🧀 Vegetarian = Dairy allowed, no eggs, no meat\n"
                "- 🥚 Eggetarian = Eggs allowed (±dairy), no meat/fish\n"
                "- 🍖 Non-Vegetarian = Contains meat, fish, or slaughter-derived ingredients"
            )

        # Vegan vs vegetarian
        if "vegan" in q and "vegetarian" in q and any(x in q for x in ["difference","vs","versus","what"]):
            return (
                "🌱 **Vegan vs Vegetarian — Key Differences**\n\n"
                "| | **Vegan** | **Vegetarian** |\n"
                "|---|---|---|\n"
                "| Meat | ❌ No | ❌ No |\n"
                "| Fish | ❌ No | ❌ No |\n"
                "| Dairy (milk, cheese, butter) | ❌ No | ✅ Yes |\n"
                "| Eggs | ❌ No | ✅ Yes |\n"
                "| Honey | ❌ No | ⚠️ Usually yes |\n"
                "| Gelatin | ❌ No | ❌ No |\n"
                "| Carmine (E120) | ❌ No | ❌ No |\n\n"
                "**Vegan** is stricter — no animal products at all, including dairy and eggs.\n\n"
                "**Vegetarian** allows dairy and eggs (lacto-ovo vegetarian is the most common type).\n\n"
                "**IngreLens AI** classifies products into 4 tiers:\n"
                "🌱 Vegan → 🧀 Vegetarian → 🥚 Eggetarian → 🍖 Non-Vegetarian"
            )

        # Natural flavors question
        if "natural flavor" in q or "natural flavour" in q:
            return (
                "❓ **Does 'Natural Flavors' mean vegan?**\n\n"
                "**No — not necessarily.** 'Natural flavors' is a catch-all term that can legally "
                "include extracts from:\n\n"
                "- 🌿 Plants (fruits, vegetables, herbs, spices) → Vegan ✅\n"
                "- 🐄 Animal sources (meat, seafood, dairy, eggs, insects) → Not vegan ❌\n\n"
                "**The problem:** Manufacturers are not required to specify the exact source.\n\n"
                "**How to handle it:**\n"
                "1. Check if the product is **certified vegan** (logo on pack)\n"
                "2. **Contact the manufacturer** and ask if the natural flavors are plant-derived\n"
                "3. If the rest of the ingredients are vegan, many vegans accept the risk\n\n"
                "**IngreLens AI** marks 'natural flavors' as ⚠️ **Uncertain** unless the product "
                "carries a vegan certification, which is the most honest approach.\n\n"
                "**In Coca-Cola, Pepsi, and most beverages:** The manufacturer has confirmed "
                "the natural flavors are not animal-derived, though not officially certified."
            )

        # Plant-based vs vegan
        if "plant based" in q or "plant-based" in q:
            return (
                "🌿 **'Plant-Based' vs 'Vegan' — Are They the Same?**\n\n"
                "**Not always!** The terms are often used interchangeably but have subtle differences:\n\n"
                "**Vegan:** A strict ethical standard — no animal products in food *or* lifestyle "
                "(no leather, no animal testing). In food: absolutely no dairy, eggs, honey, gelatin, etc.\n\n"
                "**Plant-Based:** A dietary description — primarily or exclusively plants. "
                "Some 'plant-based' products may still contain small amounts of dairy or eggs.\n\n"
                "**Always check labels.** A product labeled 'plant-based' is not guaranteed vegan.\n\n"
                "Look for: **Certified Vegan logo** 🌱, **Vegan Society trademark**, or **V-label**."
            )

        return None

    # ── E-NUMBER QUESTIONS ────────────────────────────────────────────────────
    def _is_enumber_question(self, q: str) -> bool:
        import re
        return bool(re.search(r'\be\d{3,4}\b', q)) or "e number" in q or "e-number" in q or "additive" in q

    def _handle_enumber(self, q: str) -> str:
        import re
        # Specific named caramel color check
        if 'e150' in q or 'caramel color' in q or 'caramel colour' in q:
            caramel_ans = self._ingredient_answer(q)
            return caramel_ans if caramel_ans else (
                "\U0001F36F **Caramel Colour (E150a/b/c/d) \u2014 All Vegan**\n\n"
                "Caramel colour is made by heat-treating sugar \u2014 no animal products.\n\n"
                "E150d (Sulphite Ammonia Caramel) is used in Coca-Cola and most dark sodas. It is vegan."
            )
        match = re.search(r'\be(\d{3,4})\b', q)
        enum = match.group(0).upper() if match else None
        num  = int(match.group(1)) if match else None

        E_NUMBERS = {
            # Colours
            "E100": ("Curcumin (Turmeric)", "✅ Vegan", "Yellow colour from turmeric root"),
            "E101": ("Riboflavin (Vitamin B2)", "✅ Vegan", "Yellow colour — fermentation derived"),
            "E102": ("Tartrazine", "✅ Vegan", "Synthetic yellow dye"),
            "E110": ("Sunset Yellow FCF", "✅ Vegan", "Synthetic orange-yellow dye"),
            "E120": ("Carmine (Cochineal)", "❌ NOT Vegan", "Red dye from crushed cochineal insects — NOT vegan"),
            "E122": ("Carmoisine", "✅ Vegan", "Synthetic red azo dye"),
            "E124": ("Ponceau 4R", "✅ Vegan", "Synthetic red dye"),
            "E129": ("Allura Red AC (Red 40)", "✅ Vegan", "Synthetic red dye"),
            "E131": ("Patent Blue V", "✅ Vegan", "Synthetic blue dye"),
            "E132": ("Indigotine", "✅ Vegan", "Synthetic blue dye"),
            "E140": ("Chlorophyll", "✅ Vegan", "Green colour from plants"),
            "E150a": ("Caramel Colour (Plain)", "✅ Vegan", "Burnt sugar — vegan"),
            "E150b": ("Caustic Sulphite Caramel", "✅ Vegan", "Caramel colour — vegan"),
            "E150c": ("Ammonia Caramel", "✅ Vegan", "Caramel colour used in dark beers — vegan"),
            "E150d": ("Sulphite Ammonia Caramel", "✅ Vegan", "Used in Coca-Cola, soft drinks — vegan"),
            "E150D": ("Sulphite Ammonia Caramel", "✅ Vegan", "Used in Coca-Cola, soft drinks — vegan"),
            "E153": ("Vegetable Carbon", "✅ Vegan", "Black colour from charred plant matter"),
            "E160a": ("Carotenes (Beta-Carotene)", "✅ Vegan", "Orange colour from carrots/algae"),
            "E161": ("Xanthophylls", "⚠️ Usually Vegan", "May be from plant or animal sources"),
            "E162": ("Beetroot Red", "✅ Vegan", "Red/purple colour from beetroot"),
            "E163": ("Anthocyanins", "✅ Vegan", "Red/blue colour from berries and grapes"),
            "E170": ("Calcium Carbonate", "✅ Vegan", "White colour/chalk mineral"),
            "E171": ("Titanium Dioxide", "✅ Vegan", "White colour — mineral"),
            "E172": ("Iron Oxides", "✅ Vegan", "Yellow/red/black — mineral pigments"),
            # Preservatives
            "E200": ("Sorbic Acid", "✅ Vegan", "Preservative from rowan berries (now synthetic)"),
            "E202": ("Potassium Sorbate", "✅ Vegan", "Common preservative — plant/synthetic"),
            "E210": ("Benzoic Acid", "✅ Vegan", "Synthetic preservative"),
            "E211": ("Sodium Benzoate", "✅ Vegan", "Preservative — synthetic"),
            "E220": ("Sulphur Dioxide", "✅ Vegan", "Preservative in wine and dried fruits"),
            "E252": ("Potassium Nitrate", "✅ Vegan", "Preservative — mineral salt"),
            "E270": ("Lactic Acid", "✅ Vegan", "Fermentation-derived preservative"),
            "E280": ("Propionic Acid", "✅ Vegan", "Antifungal preservative — synthetic"),
            # Antioxidants
            "E300": ("Ascorbic Acid (Vitamin C)", "✅ Vegan", "Antioxidant from plant/synthetic sources"),
            "E306": ("Tocopherols (Vitamin E)", "✅ Vegan", "Natural antioxidants from vegetable oils"),
            "E322": ("Lecithin", "⚠️ Usually Vegan", "Usually soy/sunflower — specify if egg lecithin"),
            # Emulsifiers
            "E400": ("Alginic Acid", "✅ Vegan", "Thickener from seaweed"),
            "E401": ("Sodium Alginate", "✅ Vegan", "Thickener from seaweed"),
            "E402": ("Potassium Alginate", "✅ Vegan", "Thickener from seaweed"),
            "E406": ("Agar", "✅ Vegan", "Gelling agent from red algae — great gelatin alternative"),
            "E407": ("Carrageenan", "✅ Vegan", "Stabiliser from red seaweed"),
            "E410": ("Locust Bean Gum", "✅ Vegan", "Thickener from carob seeds"),
            "E412": ("Guar Gum", "✅ Vegan", "Thickener from guar beans"),
            "E415": ("Xanthan Gum", "✅ Vegan", "Stabiliser from bacterial fermentation"),
            "E420": ("Sorbitol", "✅ Vegan", "Sweetener from corn — plant-derived"),
            "E422": ("Glycerol / Glycerin", "⚠️ Usually Vegan", "May be plant-based (palm/soy) or animal-derived (tallow)"),
            "E440": ("Pectins", "✅ Vegan", "Gelling agent from fruit peels"),
            "E450": ("Diphosphates", "✅ Vegan", "Leavening agent — mineral"),
            "E471": ("Mono & Diglycerides", "⚠️ Uncertain", "Emulsifier — may be plant or animal (tallow) derived"),
            "E472": ("Esters of Mono/Diglycerides", "⚠️ Uncertain", "May be plant or animal derived"),
            "E481": ("Sodium Stearoyl Lactylate", "⚠️ Uncertain", "Emulsifier — sodium + stearic acid (may be animal)"),
            "E500": ("Sodium Carbonate (Baking Soda)", "✅ Vegan", "Raising agent — mineral"),
            # Flavour enhancers
            "E620": ("Glutamic Acid", "✅ Vegan", "Amino acid — fermentation derived"),
            "E621": ("Monosodium Glutamate (MSG)", "✅ Vegan", "Fermented from plant starch"),
            "E627": ("Disodium Guanylate", "⚠️ Often NOT Vegan", "Often derived from fish or yeast — check source"),
            "E631": ("Disodium Inosinate", "⚠️ Often NOT Vegan", "Often derived from meat or fish"),
            "E635": ("Disodium 5'-ribonucleotide", "⚠️ Often NOT Vegan", "Mixture of E627+E631 — often animal-derived"),
            # Other notable ones
            "E901": ("Beeswax", "❌ NOT Vegan", "Wax from honeybees — not vegan"),
            "E903": ("Carnauba Wax", "✅ Vegan", "Wax from carnauba palm leaves — vegan"),
            "E904": ("Shellac", "❌ NOT Vegan", "Resin secreted by lac beetles — not vegan"),
            "E920": ("L-Cysteine", "❌ Usually NOT Vegan", "Amino acid usually from poultry feathers — not vegan"),
            "E966": ("Lactitol", "❌ NOT Vegan", "Sweetener derived from lactose (milk sugar)"),
            "E1103": ("Invertase", "⚠️ Usually Vegan", "Enzyme — usually from yeast, sometimes animal"),
        }

        enum_upper = enum.upper() if enum else None
        if enum and (enum in E_NUMBERS or (enum_upper and enum_upper in E_NUMBERS)):
            _key = enum if enum in E_NUMBERS else enum_upper
            name, status, desc = E_NUMBERS[_key]
            icon = "✅" if "✅" in status else ("❌" if "❌" in status else "⚠️")
            return (
                f"{icon} **{enum} — {name}**\n\n"
                f"**Vegan Status:** {status}\n\n"
                f"**What it is:** {desc}\n\n"
                f"**Category:** {'Colour (E100-E199)' if num and 100<=num<200 else 'Preservative (E200-E299)' if num and 200<=num<300 else 'Antioxidant (E300-E399)' if num and 300<=num<400 else 'Emulsifier/Stabiliser (E400-E499)' if num and 400<=num<500 else 'Acidity regulator (E500-E599)' if num and 500<=num<600 else 'Flavour enhancer (E600-E699)' if num and 600<=num<700 else 'Glazing agent/other' if num and 900<=num<1000 else 'Food additive'}"
            )

        # General E-number category question
        if "e number" in q or "e-number" in q or ("what" in q and "additive" in q):
            return (
                "🔢 **E-Numbers — Complete Guide**\n\n"
                "E-numbers are codes for food additives approved in the EU/UK.\n\n"
                "**Categories:**\n"
                "- **E100–E199:** Colours\n"
                "- **E200–E299:** Preservatives\n"
                "- **E300–E399:** Antioxidants\n"
                "- **E400–E499:** Emulsifiers, stabilisers, thickeners\n"
                "- **E500–E599:** Acidity regulators, anti-caking agents\n"
                "- **E600–E699:** Flavour enhancers\n"
                "- **E900–E999:** Glazing agents, sweeteners, propellants\n"
                "- **E1000+:** Additional additives\n\n"
                "**Vegan-UNSAFE E-numbers to watch for:**\n"
                "❌ E120 (Carmine — insects) | E542 (Bone phosphate) | E901 (Beeswax)\n"
                "❌ E904 (Shellac — beetles) | E920 (L-Cysteine — feathers)\n\n"
                "❓ E471, E472, E481 (May be animal-derived fats) | E627, E631, E635 (May be fish)\n\n"
                "**Ask me:** *'What is E120?'* or *'Is E471 vegan?'* for specific answers!"
            )

        return None

    # ── SPECIFIC INGREDIENT ANSWERS ───────────────────────────────────────────
    def _ingredient_answer(self, q: str) -> str:
        # Caramel color / caramel colour
        if "caramel color" in q or "caramel colour" in q or "caramel colou" in q or ("caramel" in q and ("e150" in q or "color" in q or "colour" in q or "vegan" in q)):
            return (
                "🍯 **Caramel Colour — Is It Vegan?**\n\n"
                "✅ **Yes — caramel colour is vegan.**\n\n"
                "Caramel colour is made by heat-treating sugar — no animal products involved.\n\n"
                "**The 4 types (all vegan):**\n"
                "| E-Number | Name | Used In |\n"
                "|---|---|---|\n"
                "| E150a | Plain caramel | General use |\n"
                "| E150b | Caustic sulphite caramel | Whisky, vinegar |\n"
                "| E150c | Ammonia caramel | Beer, sauces |\n"
                "| **E150d** | **Sulphite ammonia caramel** | **Coca-Cola, Pepsi, dark sodas** |\n\n"
                "**Coca-Cola's E150d** has been confirmed as vegan by Coca-Cola — it is made "
                "from sugar treated with ammonia and sulphites, with no animal products.\n\n"
                "⚠️ **Health note:** Some caramel colours (especially E150c and E150d) contain "
                "4-methylimidazole (4-MEI), a compound the WHO has flagged as a possible carcinogen "
                "at very high doses. The amounts in food are considered safe by regulators."
            )

        # Mayonnaise general
        if ("mayo" in q or "mayonnaise" in q) and ("vegan" in q or "vegetarian" in q or "eggetarian" in q or "is it" in q or "contain" in q):
            return (
                "🥚 **Mayonnaise — Diet Classification**\n\n"
                "**Traditional mayonnaise ingredients:**\n"
                "- Egg yolks 🥚\n"
                "- Vegetable oil\n"
                "- Vinegar or lemon juice\n"
                "- Salt, mustard\n\n"
                "**Is mayo vegan?** ❌ No — contains eggs\n\n"
                "**Is mayo vegetarian?** ✅ Yes — eggs are allowed in vegetarian diets\n\n"
                "**Is mayo eggetarian?** ✅ Yes — eggs without dairy/meat = eggetarian\n\n"
                "**Is mayo non-vegetarian?** ❌ No — no meat or fish\n\n"
                "**Vegan mayo options:** Hellmann's Vegan, Vegenaise, Just Mayo — made "
                "with aquafaba (chickpea liquid) or modified starch instead of eggs."
            )

        # Gelatin
        if any(kw in q for kw in ["gelatin", "gelatine"]):
            return ("🐾 **Gelatin is NOT vegan and NOT vegetarian.**\n\n"
                    "Gelatin is a protein derived from collagen in animal bones, skin, "
                    "and connective tissues — typically from pigs or cows.\n\n"
                    "**Common uses:** Gummy sweets, marshmallows, jelly, capsules, panna cotta\n\n"
                    "**Vegan/Vegetarian alternatives:** agar-agar (seaweed), pectin (fruit), carrageenan (seaweed), konjac")

        if "honey" in q and any(x in q for x in ["vegan","vegetarian","is","diet"]):
            return ("🐝 **Honey is NOT vegan** — but IS vegetarian.\n\n"
                    "Honey is produced by bees and considered an animal product by vegan standards. "
                    "Most vegetarians do consume honey.\n\n"
                    "**Vegan alternatives:** agave nectar, maple syrup, date syrup, coconut nectar")

        if "whey" in q:
            return ("🥛 **Whey is NOT vegan** — it is a dairy byproduct.\n\n"
                    "Whey protein is derived from milk during cheese-making.\n\n"
                    "**Diet classification:** 🧀 Vegetarian (not vegan)\n\n"
                    "**Vegan protein alternatives:** pea protein, soy protein, rice protein, hemp protein")

        if "carmine" in q or "cochineal" in q or "e120" in q:
            return ("🐛 **Carmine (E120) is NOT vegan and NOT vegetarian.**\n\n"
                    "Carmine is a red dye made from crushed cochineal insects.\n\n"
                    "**Found in:** Red/pink candies, yogurts, fruit juices, cosmetics\n\n"
                    "**Vegan alternatives:** beet juice powder, paprika extract, lycopene, annatto")

        if "lecithin" in q:
            return ("⚠️ **Lecithin — usually vegan, but check the source.**\n\n"
                    "• **Soy lecithin (E322)** → ✅ Vegan\n"
                    "• **Sunflower lecithin** → ✅ Vegan\n"
                    "• **Egg lecithin** → ❌ Not vegan (eggetarian)\n\n"
                    "In most packaged foods, lecithin is soy or sunflower-derived and vegan.")

        if "natural flavor" in q or "natural flavour" in q:
            return ("❓ **Natural flavors — uncertain for vegans.**\n\n"
                    "The term 'natural flavors' can legally include extracts from plants OR animals "
                    "(meat, seafood, dairy, eggs, insects).\n\n"
                    "Manufacturers are not required to specify the source. IngreLens AI marks "
                    "this as ⚠️ Uncertain.\n\n"
                    "**To confirm:** Contact the manufacturer or look for certified vegan products.")

        if "vitamin d" in q:
            return ("☀️ **Vitamin D status depends on the type:**\n\n"
                    "• **D3 (cholecalciferol):** Usually from lanolin (sheep wool) ❌ Not vegan by default\n"
                    "• **D2 (ergocalciferol):** From yeast/fungi ✅ Always vegan\n"
                    "• **Lichen-derived D3:** ✅ Vegan (rare, but exists)\n\n"
                    "If label just says 'Vitamin D', assume D3 (non-vegan).")

        if "nutella" in q:
            return ("❌ **Nutella is NOT vegan** — contains skimmed milk powder (dairy).\n\n"
                    "**Diet: 🧀 Vegetarian** (dairy, no eggs or meat)\n\n"
                    "**Vegan alternatives:** Nocciolata dairy-free, Justin's Chocolate Hazelnut Butter, "
                    "Pip & Nut Hazelnut Chocolate Spread.")

        if "oreo" in q:
            return ("⚠️ **Oreos — vegan ingredients, but cross-contamination risk.**\n\n"
                    "Main recipe contains no animal ingredients, but Mondelez states shared equipment "
                    "with dairy-containing products.\n\n"
                    "• **Strict vegan:** ❌ Avoid\n"
                    "• **Ingredient-vegan:** ✅ Acceptable\n\n"
                    "Check your local label — formulas vary by country.")

        if "shellac" in q or "e904" in q:
            return ("🐛 **Shellac (E904) is NOT vegan** — secreted by lac beetles.\n\n"
                    "**Found on:** Glazed apples, shiny confectionery, tablet coatings\n\n"
                    "**Vegan alternative:** Carnauba wax (E903) from palm leaves.")

        if "isinglass" in q:
            return ("🐟 **Isinglass is NOT vegan or vegetarian** — made from fish swim bladders.\n\n"
                    "Used to clarify wine and beer. Often not listed as an ingredient.\n\n"
                    "**Vegan beer/wine:** Look for 'unfined' or 'vegan friendly' label.")

        if "casein" in q or "caseinate" in q:
            return ("🥛 **Casein is NOT vegan** — it is a milk protein.\n\n"
                    "⚠️ Caution: Some 'non-dairy' products still contain casein!\n\n"
                    "**Diet: 🧀 Vegetarian** (dairy protein)\n\n"
                    "**Vegan alternatives:** soy protein isolate, pea protein")

        if "l-cysteine" in q or "e920" in q or "cysteine" in q:
            return ("⚠️ **L-Cysteine (E920) is usually NOT vegan** — typically from poultry feathers.\n\n"
                    "Used as a dough conditioner in commercial bread. Synthetic vegan version exists "
                    "but is rarely specified.\n\n"
                    "**Found in:** Commercial bread, bagels, croissants, pizza dough.")

        if "agar" in q:
            return ("✅ **Agar (agar-agar) is 100% vegan** — from red algae/seaweed.\n\n"
                    "The perfect gelatin replacement for vegan cooking.\n\n"
                    "**Tip:** Use ~half the amount of agar vs gelatin — it sets firmer.")

        if "xanthan gum" in q or "xanthan" in q:
            return ("✅ **Xanthan gum is vegan** — produced by bacterial fermentation.\n\n"
                    "**Common uses:** Gluten-free baking, sauces, salad dressings, plant milks.")

        if "tapioca" in q:
            return ("✅ **Tapioca starch is vegan and gluten-free** — from cassava root.\n\n"
                    "**Allergens:** None\n\n"
                    "**Common uses:** Gluten-free baking, bubble tea, thickening sauces, puddings.")

        if "palm oil" in q:
            return ("✅ **Palm oil is technically vegan** — plant-derived.\n\n"
                    "⚠️ However, palm oil production causes massive deforestation and threatens "
                    "orangutans and other wildlife. Many vegans avoid it on ethical grounds.\n\n"
                    "**Look for:** RSPO-certified sustainable palm oil, or palm-free products.")

        if ("cocoa" in q or "cacao" in q) and any(x in q for x in ["vegan","butter","mass","powder"]):
            return ("✅ **Cocoa / Cacao — all forms are vegan.**\n\n"
                    "• Cocoa powder → ✅ Vegan\n"
                    "• Cocoa butter → ✅ Vegan (from cacao bean, NOT dairy butter)\n"
                    "• Cacao butter → ✅ Vegan\n"
                    "• Dark chocolate (check for milk) → Usually ✅\n"
                    "• Milk chocolate → ❌ Contains dairy")

        if "beeswax" in q or "e901" in q:
            return ("❌ **Beeswax (E901) is NOT vegan** — secreted by honeybees.\n\n"
                    "**Vegan alternative:** Carnauba wax (E903) from carnauba palm leaves.")

        if "guar gum" in q:
            return ("✅ **Guar gum is vegan** — from guar beans.\n\n"
                    "**Common uses:** Ice cream, sauces, gluten-free baking, plant milks.")

        if "citric acid" in q:
            return ("✅ **Citric acid is vegan** — produced by fungal fermentation of sugars.\n\n"
                    "Despite the name, commercial citric acid is NOT extracted from citrus fruits. "
                    "It is fermented from corn or beet sugar.")

        if "lactic acid" in q:
            return ("✅ **Lactic acid is almost always vegan** — fermentation-derived.\n\n"
                    "Despite the 'lactic' name (from Latin 'lac' = milk), commercial lactic acid "
                    "is fermented from plant sugars, not dairy.")

        if ("mono" in q and "diglyceride" in q) or "e471" in q:
            return ("⚠️ **Mono and diglycerides (E471) — uncertain.**\n\n"
                    "May be from plant oils (soy, sunflower, palm) ✅ or animal fats (tallow, lard) ❌\n\n"
                    "Contact the manufacturer to confirm. Many major brands use plant-derived versions.")

        if "pectin" in q:
            return ("✅ **Pectin is vegan** — from fruit peel (citrus/apple).\n\n"
                    "The go-to gelatin replacement for vegan jams and gummies.")

        if "maltodextrin" in q:
            return ("✅ **Maltodextrin is vegan** — from plant starch (corn, wheat, potato).\n\n"
                    "⚠️ High glycemic index — can spike blood sugar. Common in processed foods.")

        if "vitamin b12" in q:
            return ("✅ **Vitamin B12 in fortified foods/supplements is vegan** — bacterial fermentation.\n\n"
                    "⚠️ **Important for vegans:** B12 is found naturally only in animal products. "
                    "Vegans MUST supplement or eat B12-fortified foods (plant milks, cereals).")

        if "ascorbic acid" in q or "vitamin c" in q:
            return ("✅ **Ascorbic acid (Vitamin C) is vegan** — plant-derived or synthetic.\n\n"
                    "Used as antioxidant preservative and nutrient supplement.")

        if "carrageenan" in q:
            return ("✅ **Carrageenan is vegan** — from red seaweed.\n\n"
                    "⚠️ Some studies suggest it may cause gut irritation in large quantities, "
                    "though food authorities consider it safe at normal levels.")

        if "glycerin" in q or "glycerol" in q or "e422" in q:
            return ("⚠️ **Glycerin/Glycerol (E422) — check the source.**\n\n"
                    "Can be from plant oils (palm, soy) ✅ or animal fats (tallow) ❌\n\n"
                    "In most modern food products, glycerin is plant-derived. "
                    "Certified vegan products will confirm this.")

        if "msg" in q or "monosodium glutamate" in q:
            return ("✅ **MSG (Monosodium Glutamate, E621) is vegan.**\n\n"
                    "MSG is produced by bacterial fermentation of plant starch (sugar cane, tapioca, corn).\n\n"
                    "Despite myths, MSG is widely considered safe by FDA, WHO, and EU food authorities. "
                    "The 'Chinese Restaurant Syndrome' link has been debunked by research.")

        if "aspartame" in q:
            return ("✅ **Aspartame is vegan** — synthetically produced.\n\n"
                    "Aspartame is an artificial sweetener made from two amino acids (phenylalanine + aspartic acid) "
                    "via synthetic chemical process — no animal products involved.\n\n"
                    "⚠️ **Health note:** People with PKU (phenylketonuria) must avoid aspartame. "
                    "General safety is well-established by regulatory bodies though some controversy remains. "
                    "Found in Coke Zero, Diet Coke, many 'sugar-free' products.")

        if "stevia" in q:
            return ("✅ **Stevia is vegan** — derived from the Stevia rebaudiana plant.\n\n"
                    "A natural zero-calorie sweetener. 200-300x sweeter than sugar.\n\n"
                    "**Found in:** Many 'natural' zero-calorie drinks, some yogurts, supplements.")

        if "sunflower" in q and any(x in q for x in ["vegan","lecithin","oil","seed"]):
            return ("✅ **Sunflower (oil/seeds/lecithin) — all vegan.**\n\n"
                    "• Sunflower oil → ✅ Vegan\n"
                    "• Sunflower seeds → ✅ Vegan\n"
                    "• Sunflower lecithin → ✅ Vegan (excellent alternative to soy lecithin)")

        if "rennet" in q:
            return ("⚠️ **Rennet — depends on the type:**\n\n"
                    "• **Animal rennet:** ❌ NOT vegan or vegetarian — from calf stomachs\n"
                    "• **Microbial rennet:** ✅ Vegan — from fungi\n"
                    "• **Vegetable rennet:** ✅ Vegan — from plant sources\n"
                    "• **Fermentation-produced rennet (FPC):** ✅ Vegan — from GMO fungi\n\n"
                    "Most modern cheese uses microbial or FPC rennet. Check label or contact manufacturer.")

        if "sugar" in q and any(x in q for x in ["vegan","bone char","cane","beet"]):
            return ("🤔 **Sugar — usually vegan, but cane sugar in the US may not be.**\n\n"
                    "• **Beet sugar:** ✅ Always vegan\n"
                    "• **Cane sugar (UK/EU):** ✅ Usually vegan\n"
                    "• **Cane sugar (US):** ⚠️ May be filtered through bone char from cattle\n\n"
                    "Look for: organic sugar, unrefined sugar, or beet sugar to be certain.")

        return None

    # ── GENERAL FOOD & HEALTH QUESTIONS ──────────────────────────────────────
    def _general_food_answer(self, q: str) -> str:

        # Health score explanation
        if "health score" in q:
            return ("🏥 **IngreLens Health Score — How It Works**\n\n"
                    "The health score (0–100) is calculated based on:\n\n"
                    "**Starting point:** 80/100\n\n"
                    "**Deductions:**\n"
                    "- Ultra-processed markers (HFCS, artificial flavors, etc.): −4 each\n"
                    "- Preservatives (sodium benzoate, BHA, BHT, etc.): −3 each\n"
                    "- High sugar content (multiple sugar sources): −5\n"
                    "- Artificial coloring: −5\n"
                    "- High additive count (5+ E-numbers): −5\n\n"
                    "**Score guide:**\n"
                    "- 80–100: 🟢 Excellent — minimal processing\n"
                    "- 60–79: 🟡 Good — some additives\n"
                    "- 40–59: 🟠 Moderate — check ingredients\n"
                    "- <40: 🔴 Poor — heavily processed")

        # What does vegan mean
        if ("what" in q or "define" in q or "meaning" in q or ("mean" in q and "what" in q)) and "vegan" in q and len(q) < 50 and not any(x in q for x in ["is vegan","non-vegan","not vegan","vegan status"]):
            return ("🌱 **What Does Vegan Mean?**\n\n"
                    "A **vegan** diet excludes all animal products:\n"
                    "❌ Meat, poultry, fish and seafood\n"
                    "❌ Dairy (milk, butter, cheese, yogurt, whey, casein)\n"
                    "❌ Eggs\n"
                    "❌ Honey, beeswax, propolis, royal jelly\n"
                    "❌ Gelatin, isinglass, carmine, shellac, L-cysteine\n\n"
                    "✅ All plant foods — vegetables, fruits, grains, legumes, nuts, seeds, oils\n\n"
                    "**IngreLens AI** classifies every ingredient and flags any animal-derived "
                    "substances, including hidden ones like E120 (crushed insects) and E920 "
                    "(amino acid from poultry feathers).")

        # How to read ingredient labels
        if "how to read" in q and "label" in q or ("ingredient" in q and "label" in q and "read" in q):
            return ("📋 **How to Read Ingredient Labels**\n\n"
                    "1. **Ingredients are listed by weight** — heaviest first\n"
                    "2. **Anything in bold** is a major allergen (EU/UK)\n"
                    "3. **E-numbers** are approved food additives (E100–E1500)\n"
                    "4. **'May contain'** = cross-contamination warning (not an ingredient)\n"
                    "5. **'Suitable for vegans'** or **V-label** = certified vegan\n\n"
                    "**Hidden non-vegan ingredients to watch for:**\n"
                    "- E120 (Carmine) — insect dye\n"
                    "- E904 (Shellac) — beetle resin\n"
                    "- E920 (L-Cysteine) — usually poultry feathers\n"
                    "- E901 (Beeswax) — bee product\n"
                    "- Casein/Caseinate — milk protein\n"
                    "- Isinglass — fish bladder (wine/beer)\n\n"
                    "💡 *Paste any ingredient list into the **Scanner** tab for instant analysis!*")

        # Gluten free
        if "gluten" in q and any(x in q for x in ["what","free","vegan","vegetarian","contain","is"]):
            return ("🌾 **Gluten — What Is It?**\n\n"
                    "Gluten is a protein found in wheat, barley, rye, and spelt.\n\n"
                    "**Is gluten vegan?** ✅ Yes — gluten is plant-derived.\n\n"
                    "**Gluten-free ≠ Vegan:** Many gluten-free products contain eggs or dairy.\n\n"
                    "**Who avoids gluten:**\n"
                    "- People with coeliac disease (autoimmune)\n"
                    "- People with non-coeliac gluten sensitivity\n"
                    "- Some choose to avoid it generally\n\n"
                    "**Gluten-free grains:** rice, corn/maize, quinoa, buckwheat, millet, sorghum, teff, oats (certified GF)")

        # Nutri-Score
        if "nutri" in q and "score" in q:
            return ("🏷️ **Nutri-Score — What Does It Mean?**\n\n"
                    "Nutri-Score is a European front-of-pack nutritional label (A–E):\n\n"
                    "| Score | Meaning | Color |\n"
                    "|---|---|---|\n"
                    "| A | Best nutritional quality | 🟢 Dark green |\n"
                    "| B | Good nutritional quality | 🟢 Light green |\n"
                    "| C | Average | 🟡 Yellow |\n"
                    "| D | Poor nutritional quality | 🟠 Orange |\n"
                    "| E | Worst nutritional quality | 🔴 Red |\n\n"
                    "Calculated from: energy, sugar, saturated fat, sodium (negative) vs "
                    "fiber, protein, fruits/vegetables (positive).\n\n"
                    "⚠️ Nutri-Score does NOT indicate if a product is vegan — it only measures nutrition.")

        # Protein sources
        if "protein" in q and any(x in q for x in ["vegan","plant","best","source","complete"]):
            return ("💪 **Best Vegan Protein Sources**\n\n"
                    "| Source | Protein per 100g | Complete? |\n"
                    "|---|---|---|\n"
                    "| Soy protein isolate | 90g | ✅ Yes |\n"
                    "| Seitan (wheat gluten) | 75g | ⚠️ Partial |\n"
                    "| Hemp seeds | 32g | ✅ Yes |\n"
                    "| Pumpkin seeds | 30g | ⚠️ Partial |\n"
                    "| Lentils (cooked) | 9g | ⚠️ Partial |\n"
                    "| Chickpeas (cooked) | 9g | ⚠️ Partial |\n"
                    "| Edamame | 11g | ✅ Yes |\n"
                    "| Quinoa | 14g | ✅ Yes |\n"
                    "| Tofu | 17g | ✅ Yes |\n"
                    "| Tempeh | 19g | ✅ Yes |\n\n"
                    "**Complete protein** = contains all 9 essential amino acids.\n"
                    "**Tip:** Combining rice + beans = complete protein!")

        return None

    # ── KB LOOKUP ─────────────────────────────────────────────────────────────
    def _kb_lookup_answer(self, q: str) -> str:
        kb = self._get_kb()
        if not kb:
            return None

        clean_q = q
        for remove in ["what is","what are","is it","is","are","tell me about","explain",
                        "vegan","vegetarian","eggetarian","?","the","a","an","how","why",
                        "does it","do they","contain"]:
            clean_q = clean_q.replace(remove, " ")
        clean_q = " ".join(clean_q.split()).strip()

        if len(clean_q) < 3:
            return None

        entry = kb.lookup(clean_q)
        if not entry:
            return None

        STATUS_ICONS = {
            "vegan": "🌱", "non-vegan": "❌", "usually vegan": "✅",
            "uncertain": "⚠️", "usually non-vegan": "⚠️"
        }
        DIET_MAP = {
            "vegan": "🌱 Vegan", "non-vegan": "❌ Not Vegan",
            "uncertain": "⚠️ Uncertain", "usually vegan": "✅ Usually Vegan",
            "usually non-vegan": "⚠️ Usually Not Vegan"
        }
        status = entry.get("vegan_status", "unknown")
        icon   = STATUS_ICONS.get(status, "❓")
        diet   = DIET_MAP.get(status, status.title())

        resp = f"{icon} **{entry['name'].title()}**\n\n"
        resp += f"**Diet status:** {diet}\n\n"
        if entry.get("description"):
            resp += f"{entry['description']}\n\n"
        if entry.get("category"):
            resp += f"**Category:** {entry['category'].title()}\n\n"
        if entry.get("allergens"):
            resp += f"**Allergens:** {', '.join(entry['allergens'])}\n\n"
        if entry.get("health_flags"):
            resp += f"**Health notes:** {', '.join(entry['health_flags'])}\n\n"
        if entry.get("alternatives"):
            resp += f"**Vegan alternatives:** {entry['alternatives']}"
        return resp

    # ── SMART FALLBACK ────────────────────────────────────────────────────────
    def _smart_fallback(self, q: str) -> str:
        # Try to give a useful response based on what words are in the question
        words = [w for w in q.split() if len(w) > 3 and w not in
                 {"what","about","vegan","plant","based","food","this","that",
                  "with","have","does","does","will","tell","more","like","also",
                  "some","just","give","from","into","been","they","them"}]

        if words:
            topic = " ".join(words[:3]).title()
            return (
                f"🤔 I don't have specific information about **{topic}** in my knowledge base yet.\n\n"
                f"Here's what you can do:\n\n"
                f"**1. Paste the ingredient list** → Scanner tab → full AI analysis\n"
                f"**2. Search the product** → Analyzer tab → barcode or name search\n"
                f"**3. Ask more specifically:**\n"
                f"   - *'Is [ingredient] vegan?'*\n"
                f"   - *'What is E120?'*\n"
                f"   - *'Is Nutella vegan?'*\n"
                f"   - *'Which is better: Coke or Coke Zero?'*\n"
                f"   - *'Is mayonnaise eggetarian?'*\n"
                f"   - *'Does natural flavors mean vegan?'*\n\n"
                f"I can answer questions about 80+ ingredients, E-numbers, diet classifications, and product comparisons!"
            )

        return ("👋 I'm **IngreLens AI** — your food ingredient intelligence assistant!\n\n"
                "**I can help with:**\n"
                "• 🌱 *'Is [ingredient] vegan?'* — gelatin, honey, lecithin, E120…\n"
                "• 🥚 *'Is mayonnaise eggetarian?'* — diet classification questions\n"
                "• 🔢 *'What is E150d?'* — any E-number explained\n"
                "• 🥤 *'Which is better: Coke or Coke Zero?'* — product comparisons\n"
                "• 🍯 *'Is caramel color vegan?'* — specific food questions\n"
                "• ❓ *'Does natural flavors mean vegan?'* — labeling questions\n\n"
                "Or paste any ingredient list in the **Scanner** tab for a full analysis!")

    def _synthesize_from_context(self, question: str, context_lines: list) -> str:
        q = question.lower()
        verdict  = next((l for l in context_lines if l.startswith("Vegan Status:")), "")
        non_vegan= next((l for l in context_lines if l.startswith("Non-vegan")), "")
        allergens= next((l for l in context_lines if l.startswith("Allergens:")), "")
        health   = next((l for l in context_lines if l.startswith("Health Score:")), "")
        uncertain= next((l for l in context_lines if l.startswith("Uncertain")), "")

        parts = []
        if verdict:  parts.append(f"**{verdict}**")
        if non_vegan and "None" not in non_vegan:  parts.append(f"❌ {non_vegan}")
        if uncertain and "None" not in uncertain:   parts.append(f"⚠️ {uncertain}")
        if allergens and "None" not in allergens:   parts.append(f"🚨 {allergens}")
        if health:   parts.append(f"🏥 {health}")

        if parts:
            return "\n".join(parts)
        relevant = [l for l in context_lines if any(w in l.lower() for w in q.split() if len(w)>3)]
        return "\n".join(relevant[:6]) if relevant else ""


# ── AI Ingredient Analyst Agent ───────────────────────────────────────────────
class IngredientAnalystAgent:
    SYSTEM_PROMPT = """You are IngreLens AI, an expert food ingredient analyst and dietary advisor.
Classify ingredients as vegan/vegetarian/eggetarian/non-vegetarian, detect allergens, explain WHY,
suggest alternatives, compare products, and answer food labeling questions. Be factual, concise, friendly."""

    def __init__(self, analysis_service=None):
        self.llm = LLMService()
        self.analysis_service = analysis_service

    def answer(self, question: str, ingredient_context: str = "") -> str:
        return self.llm.chat(self.SYSTEM_PROMPT, question, ingredient_context)

    def analyze_and_explain(self, ingredients: str, product_name: str = "") -> str:
        if self.analysis_service:
            result = self.analysis_service.analyze(ingredients, product_name)
            context = self._format_result_for_llm(result)
        else:
            context = f"Ingredients: {ingredients}"
        question = f"Analyze these ingredients for vegan/diet status: {ingredients}"
        return self.llm.chat(self.SYSTEM_PROMPT, question, context)

    def _format_result_for_llm(self, result) -> str:
        return "\n".join([
            f"Product: {result.product_name}",
            f"Vegan Status: {result.overall_vegan}",
            f"Diet Category: {getattr(result,'diet_category',result.overall_vegan)}",
            f"Confidence: {result.vegan_confidence:.0%}",
            f"Non-vegan ingredients: {', '.join(result.non_vegan_ingredients) or 'None'}",
            f"Uncertain ingredients: {', '.join(result.uncertain_ingredients) or 'None'}",
            f"Allergens: {', '.join(result.allergens_detected) or 'None'}",
            f"Health Score: {result.health_score}/100",
        ])
