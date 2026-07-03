"""
IngreLens AI — Ingredient Analysis Service v2
Fixed classification: Vegan / Vegetarian / Eggetarian / Non-Vegetarian
Fixed false positives from semantic search on plant-based ingredients
"""
from __future__ import annotations
import json, re, sys, os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


# ── Data Models ───────────────────────────────────────────────────────────────
@dataclass
class IngredientResult:
    name: str
    normalized: str
    vegan_status: str          # vegan | non-vegan | uncertain
    vegetarian_status: str     # vegan | vegetarian | eggetarian | non-vegetarian | uncertain
    category: str
    confidence: float
    reason: str
    allergens: list
    health_flags: list
    alternatives: str
    description: str

@dataclass
class AnalysisResult:
    product_name: str
    raw_ingredients: str
    parsed_ingredients: list
    ingredient_results: list
    overall_vegan: str           # Vegan | Vegetarian | Eggetarian | Non-Vegetarian | Uncertain
    overall_vegetarian: str
    vegan_confidence: float
    allergens_detected: list
    health_score: int
    health_flags: list
    non_vegan_ingredients: list
    uncertain_ingredients: list
    ultra_processed_markers: list
    preservatives: list
    additives: list
    reasoning: str
    recommendations: list
    diet_category: str           # NEW: Vegan | Vegetarian | Eggetarian | Non-Vegetarian | Uncertain
    diet_color: str              # NEW: hex color for UI


# ── Knowledge Base ────────────────────────────────────────────────────────────
class IngredientKnowledgeBase:
    def __init__(self):
        self._db: dict = {}
        self._alias_map: dict = {}
        self._load()

    def _load(self):
        try:
            with open(settings.KB_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            for entry in data["ingredients"]:
                key = entry["name"].lower().strip()
                self._db[key] = entry
                for alias in entry.get("aliases", []):
                    self._alias_map[alias.lower().strip()] = key
            logger.info(f"Loaded {len(self._db)} ingredients from knowledge base")
        except Exception as e:
            logger.error(f"Failed to load knowledge base: {e}")

    def lookup(self, name: str) -> Optional[dict]:
        n = name.lower().strip()
        if n in self._db: return self._db[n]
        if n in self._alias_map: return self._db[self._alias_map[n]]
        for key, entry in self._db.items():
            if key in n or n in key:
                return entry
        for alias, canonical in self._alias_map.items():
            if alias in n or n in alias:
                return self._db.get(canonical)
        return None

    def get_all(self): return list(self._db.values())


# ── Vector Store ──────────────────────────────────────────────────────────────
class VectorStore:
    def __init__(self, kb: IngredientKnowledgeBase):
        self._ready = False
        self._kb = kb
        self._collection = None
        self._init()

    def _init(self):
        try:
            import chromadb
            from chromadb.utils import embedding_functions
            os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)
            client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
            ef = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=settings.EMBEDDING_MODEL)
            self._collection = client.get_or_create_collection(
                name=settings.CHROMA_COLLECTION,
                embedding_function=ef,
                metadata={"hnsw:space": "cosine"})
            if self._collection.count() == 0:
                self._populate()
            self._ready = True
        except Exception as e:
            logger.warning(f"ChromaDB unavailable ({e}), falling back to keyword search")

    def _populate(self):
        ingredients = self._kb.get_all()
        docs, ids, metas = [], [], []
        for ing in ingredients:
            text = f"{ing['name']} {' '.join(ing.get('aliases',[]))} {ing.get('description','')} {ing.get('category','')} {ing.get('vegan_status','')}"
            docs.append(text); ids.append(ing["name"])
            metas.append({"name": ing["name"], "vegan_status": ing["vegan_status"], "category": ing["category"]})
        self._collection.add(documents=docs, ids=ids, metadatas=metas)

    def query(self, text: str, n: int = 2) -> list:
        if not self._ready or not self._collection:
            return []
        try:
            results = self._collection.query(query_texts=[text], n_results=min(n, self._collection.count()))
            return results.get("metadatas", [[]])[0]
        except:
            return []


# ── Ingredient Parser ─────────────────────────────────────────────────────────
class IngredientParser:
    PERCENTAGE   = re.compile(r"\d+\.?\d*\s*%")
    EXTRA_SPACES = re.compile(r"\s+")

    def parse(self, raw: str) -> list:
        if not raw: return []
        raw = re.sub(r"^ingredients\s*:", "", raw, flags=re.IGNORECASE).strip()

        # Pass 1: top-level split (respects nesting)
        top_tokens = self._split_respecting_parens(raw)
        cleaned_top = [c for t in top_tokens if (c := self._clean(t)) and len(c) > 1]

        # Pass 2: for every token that contains nested brackets/parens,
        # also extract the sub-ingredients inside so they get individually classified.
        # e.g. "Cheddar Cheese [Milk, Cheese Cultures, Salt, Enzymes]" →
        #      also yields: Milk, Cheese Cultures, Salt, Enzymes
        all_tokens = list(cleaned_top)  # start with top-level tokens
        seen = set(cleaned_top)

        for token in cleaned_top:
            sub = self._extract_sub_ingredients(token)
            for s in sub:
                if s and s not in seen:
                    all_tokens.append(s)
                    seen.add(s)

        return all_tokens

    def _extract_sub_ingredients(self, token: str) -> list:
        """Extract comma-separated sub-items from inside ALL parentheses/brackets."""
        results = []
        # Find every parenthetical / bracket group
        for match in re.finditer(r"[\(\[](.*?)[\)\]]", token, re.DOTALL):
            inner = match.group(1).strip()
            # Split the inner content by comma (shallow — single level only)
            parts = [p.strip() for p in inner.split(",") if p.strip()]
            for p in parts:
                cleaned = self._clean(p)
                if cleaned and len(cleaned) > 1:
                    results.append(cleaned)
        return results

    def _split_respecting_parens(self, text: str) -> list:
        tokens, depth, current = [], 0, ""
        for ch in text:
            if ch in "([": depth += 1; current += ch
            elif ch in ")]": depth -= 1; current += ch
            elif ch in ",;" and depth == 0:
                if current.strip(): tokens.append(current.strip())
                current = ""
            else: current += ch
        if current.strip(): tokens.append(current.strip())
        return tokens

    def _clean(self, token: str) -> str:
        token = self.PERCENTAGE.sub("", token)
        token = self.EXTRA_SPACES.sub(" ", token)
        return token.strip(" .,;:-*•·–—")


# ── Classification Engine ─────────────────────────────────────────────────────
class ClassificationEngine:
    """
    NEW Classification Logic:
    ─────────────────────────────────────────────────────────────────────────
    VEGAN        — 100% plant-based, no animal products whatsoever
    VEGETARIAN   — Has dairy (milk/cheese/butter/cream/yogurt/ghee/whey/casein)
                   but NO eggs and NO meat/fish/poultry/seafood/gelatin/honey
    EGGETARIAN   — Has eggs (albumin/egg) but NO meat/fish/seafood/gelatin/honey
                   (may or may not have dairy)
    NON-VEG      — Has meat / fish / seafood / gelatin / honey / carmine /
                   any ingredient derived from slaughtered animal
    UNCERTAIN    — Contains ambiguous ingredients (natural flavors etc.)
                   with no definite animal trigger
    ─────────────────────────────────────────────────────────────────────────
    PLANT-SAFE list: explicitly vegan plant words that must NEVER trigger
    non-vegan classification even if they superficially match animal words.
    """

    # ── EXPLICITLY PLANT-SAFE — these words are ALWAYS vegan ─────────────────
    PLANT_SAFE_EXACT = {
        "cacao butter", "cacao", "cocoa butter", "cocoa", "shea butter",
        "raw cacao butter", "raw cocoa butter", "raw organic cacao butter",
        "organic cacao butter", "organic cocoa butter",
        "dairy-free dark chocolate", "dairy free dark chocolate",
        "dark chocolate dairy-free", "vegan chocolate",
        "sunflower butter", "almond butter", "peanut butter", "coconut butter",
        "hemp butter", "avocado butter", "mango butter", "illipe butter",
        "kokum butter", "pumpkin butter", "nut butter",
        "oat", "oats", "oat fiber", "oat flour",
        "quinoa", "puffed quinoa", "quinoa flour", "quinoa protein",
        "buckwheat", "puffed buckwheat", "buckwheat flour",
        "millet", "puffed millet", "sorghum", "puffed sorghum",
        "arrowroot", "arrowroot powder", "tapioca", "tapioca fiber",
        "tapioca starch", "soluble tapioca fiber",
        "mesquite", "mesquite powder",
        "sunflower seeds", "sunflower oil", "sunflower lecithin",
        "flaxseed", "flax", "chia", "hemp", "pumpkin seed",
        "plant based chocolate", "dark chocolate", "organic dark chocolate",
        "chocolate protein powder", "plant based protein", "pea protein",
        "brown rice protein", "rice protein", "hemp protein",
        "organic cacao butter", "raw organic cacao butter",
        "organic sunflower seeds", "raw organic sunflower seeds",
        "organic puffed quinoa", "organic puffed millet",
        "organic puffed buckwheat", "organic puffed sorghum",
        "organic arrowroot powder", "organic soluble tapioca fiber",
        "organic mesquite powder",
        "coconut oil", "coconut milk", "coconut cream", "coconut sugar",
        "coconut flour", "coconut water", "coconut nectar",
        "palm oil", "palm sugar", "palm kernel oil",
        "soy milk", "soy protein", "soya milk", "almond milk",
        "oat milk", "rice milk", "cashew milk", "hemp milk",
        "fruit", "vegetable", "herb", "spice", "water",
        "vitamin b12", "vitamin d2", "vitamin e", "ascorbic acid",
        "citric acid", "lactic acid", "malic acid", "tartaric acid",
        "xanthan gum", "guar gum", "agar", "carrageenan", "pectin",
        "lecithin", "soy lecithin", "sunflower lecithin",
        "nigari", "bittern", "magnesium chloride",  # tofu coagulants — vegan
        # B-vitamins used in flour/food fortification (always synthetic)
        "thiamin", "thiamine", "thiamin mononitrate", "thiamine mononitrate",
        "thiamin hydrochloride", "riboflavin", "niacin", "niacinamide",
        "folic acid", "folate", "pantothenic acid", "pyridoxine",
        "cyanocobalamin",
        # Iron and mineral fortification
        "ferrous sulfate", "ferrous sulphate", "reduced iron", "iron",
        "calcium phosphate", "monocalcium phosphate", "dicalcium phosphate",
        "calcium carbonate", "tricalcium phosphate",
        # Leavening agents
        "baking soda", "baking powder", "sodium bicarbonate",
        # Tartaric acid derivatives — grape-derived, always vegan
        "cream of tartar", "potassium bitartrate", "potassium hydrogen tartrate",
        "potassium acid tartrate", "tartaric acid", "tartrate",
        # Starter cultures — microbial, always vegan unless specified
        "starter culture", "bacterial culture", "lactic acid bacteria",
        "sodium propionate", "calcium propionate",  # preservatives — synthetic
        "sodium nitrate", "sodium nitrite", "potassium nitrate",  # curing salts
        "sodium acid pyrophosphate", "disodium phosphate", "trisodium phosphate",
        "calcium sulfate", "gypsum",  # mineral coagulants
        "oleoresin", "oleoresin of paprika", "paprika extract",  # plant pigments

        "ammonium bicarbonate", "cream of tartar", "potassium bitartrate",
        # Common vegan-safe additives not in KB
        "maltodextrin", "corn starch", "modified corn starch", "modified starch",
        "dextrose", "fructose", "glucose", "corn syrup", "high fructose corn syrup",
        "natural and artificial flavor",  # treated as uncertain separately if needed
        "soy lecithin",  # override KB "usually vegan" to vegan
        "sunflower lecithin", "rapeseed oil", "canola oil",
        "yellow 5", "yellow 6", "red 40", "blue 1", "red 40 lake", "yellow 5 lake",
        "yellow 6 lake", "caramel color", "caramel colour",
        "annatto", "turmeric extract", "paprika extract", "beet juice",
    }

    # ── PLANT-SAFE SUBSTRINGS — if ingredient contains any of these,
    #    it is likely vegan (unless a NON_VEG trigger also fires)
    PLANT_SAFE_SUBSTRINGS = [
        # legumes
        "bean", "lentil", "chickpea", "pea", "black bean", "kidney bean",
        "pinto bean", "navy bean", "soy bean", "soybean", "tofu", "tempeh",
        "edamame", "lentil", "dal", "dhal",
        # common vegan items  
        "onion", "garlic", "ginger", "tomato", "potato", "carrot", "spinach",
        "kale", "pepper", "paprika", "turmeric", "cumin", "coriander",
        "salt", "water", "vinegar", "sugar", "oil", "flour",
        "gluten", "starch", "yeast", "baking soda", "baking powder",
        "cacao", "cocoa", "sunflower", "quinoa", "buckwheat", "millet",
        "sorghum", "arrowroot", "tapioca", "mesquite", "pumpkin",
        "organic", "plant based", "plant-based", "dairy-free", "dairy free",
        "vegan", "non-dairy", "non dairy",
        "almond", "cashew", "walnut", "pecan", "pistachio", "macadamia",
        "hazelnut", "brazil nut", "pine nut", "coconut",
        "oat", "rice", "wheat", "barley", "rye", "spelt",
        "potato", "sweet potato", "corn", "maize",
        "apple", "banana", "berry", "lemon", "lime", "orange",
        "tomato", "carrot", "spinach", "kale", "beet",
        "hemp", "flax", "chia", "sesame", "mushroom", "truffle",
        "protein powder",  # if plant-based context
        "mononitrate", "monohydrate", "hydrochloride",  # vitamin forms
        "phosphate", "bicarbonate", "carbonate",  # mineral salts
        "dextrose", "maltodext", "fructose",  # carbohydrate additives
        # Common plant-origin unknowns that are always safe
        "okra", "spice", "herb", "seasoning", "vegetable", "veggie",
        "dried", "powder", "extract", "juice", "puree", "paste",
        "seed", "nut", "bean", "grain", "root", "bark", "leaf",
        "malt", "molasses", "syrup", "nectar", "agave", "maple",
        "broth", "stock",  # plant versions common in vegan products
        "nutritional yeast", "nooch",
        "seaweed", "nori", "spirulina", "chlorella",
        "jackfruit", "banana", "mango", "pineapple", "papaya",
        "avocado", "olive", "grape", "berry", "date", "fig",
        "lemon", "lime", "orange", "grapefruit", "cherry", "plum",
        "cucumber", "zucchini", "celery", "asparagus", "broccoli",
        "cauliflower", "brussels", "artichoke", "leek", "chive",
        "mustard", "fennel", "dill", "basil", "oregano", "thyme",
        "rosemary", "sage", "parsley", "cilantro", "mint", "bay",
        "clove", "cinnamon", "cardamom", "nutmeg", "allspice",
        "vanilla", "anise", "saffron", "fenugreek", "caraway",
        "cayenne", "chili", "jalapeño", "habanero",
    ]

    # ── NON-VEGETARIAN triggers (slaughtered animal / fish / insect) ──────────
    # These make the product NON-VEGETARIAN regardless of everything else
    NON_VEG_KW = [
        # Gelatin & collagen
        "gelatin", "gelatine", "pork gelatin", "beef gelatin", "fish gelatin",
        "collagen", "collagen peptide", "hydrolyzed collagen",
        # Fats from slaughtered animals
        "lard", "tallow", "suet", "dripping",
        "beef tallow", "pork lard", "chicken fat", "duck fat", "goose fat",
        "bone char", "bone meal", "bone phosphate", "e542",
        # Insect-derived
        "carmine", "cochineal", "e120", "carminic acid",
        "shellac", "e904", "confectioner's glaze", "confectioners glaze", "resinous glaze",
        "lac resin",
        # Marine-derived fining/processing
        "isinglass",
        # Rennet — animal and unspecified (conservative)
        "animal rennet", "traditional rennet", "calf rennet",
        "pepsin", "chymosin", "animal chymosin",
        "animal lipase", "animal enzymes",
        "trypsin",
        # Seafood — fish
        "anchov", "tuna", "salmon", "cod", "tilapia", "mackerel", "herring",
        "sardine", "pilchard", "sprat", "halibut", "haddock", "pollock",
        "fish oil", "omega-3 from fish", "fish extract",
        # Seafood — shellfish
        "shrimp", "prawn", "lobster", "crab", "oyster", "clam", "mussel", "scallop",
        "squid", "octopus", "crayfish",
        # Broths, extracts, sauces
        "beef extract", "chicken extract", "pork extract", "meat extract",
        "chicken broth", "beef broth", "pork broth", "bone broth",
        "fish sauce", "fish stock", "fish broth", "oyster sauce",
        "worcestershire", "worcester sauce",
        "shrimp paste", "anchovy paste", "fish paste",
        # Amino acids from animal sources
        "l-cysteine", "cysteine", "e920",
        # Other animal-derived
        "lanolin", "wool fat",
        "castoreum",        # beaver gland secretion used in vanilla flavoring
        "ambergris",        # whale-derived, used in some perfumes/flavors
        "crushed insects", "insect protein",
    ]

    # ── MEAT keywords (strict — only when NOT preceded by plant-safe context) ──
    MEAT_KW = [
        "pork", "beef", "chicken", "lamb", "turkey", "veal", "venison",
        "duck", "goose", "rabbit", "bison", "mutton",
        "ham", "bacon", "sausage", "pepperoni", "salami",
        "meat", "poultry",
    ]

    # ── DAIRY triggers (makes product Vegetarian, not Vegan) ─────────────────
    DAIRY_KW = [
        # Milks
        "milk", "whole milk", "skim milk", "skimmed milk", "buttermilk",
        "nonfat milk", "low-fat milk", "full-fat milk", "semi-skimmed milk",
        "sheep's milk", "goat milk", "buffalo milk",
        # Creams
        "cream", "heavy cream", "whipping cream", "sour cream", "clotted cream",
        "single cream", "double cream", "creme fraiche", "crème fraîche",
        # Butter
        "butter", "clarified butter", "cultured butter", "sweet cream butter",
        # Cheese types
        "cheese", "cheddar", "mozzarella", "parmesan", "parmigiano",
        "ricotta", "brie", "camembert", "gruyère", "gruyere", "emmental",
        "gouda", "edam", "stilton", "gorgonzola", "manchego", "feta",
        "mascarpone", "paneer", "halloumi", "provolone", "pecorino",
        "cheese powder", "dried cheese", "processed cheese",
        # Yogurt & fermented dairy
        "yogurt", "yoghurt", "kefir", "curd", "fromage frais",
        "labneh", "quark", "skyr",
        # Whey & milk proteins
        "whey", "whey protein", "whey powder", "whey isolate",
        "whey concentrate", "whey peptide",
        "milk solids", "milk protein", "milk protein concentrate",
        "milk protein isolate", "total milk protein",
        # Casein
        "casein", "caseinate", "sodium caseinate", "calcium caseinate",
        "potassium caseinate", "micellar casein",
        # Other milk sugars & fats
        "lactose", "lactalbumin", "lactoglobulin", "lactoferrin",
        "milk fat", "milkfat", "anhydrous milk fat", "butter oil",
        "ghee", "butter fat",
        # Powdered / condensed
        "milk powder", "skimmed milk powder", "dried milk", "whole milk powder",
        "nonfat dry milk", "nonfat milk solids",
        "condensed milk", "sweetened condensed milk", "evaporated milk",
        # Blends
        "half and half", "half & half",
        "cream cheese", "cottage cheese",
        "dairy solids", "dairy blend",
    ]

    # ── EGG triggers (makes product Eggetarian) ───────────────────────────────
    EGG_KW = [
        "egg", "eggs", "egg white", "egg yolk", "egg powder", "dried egg",
        "albumin", "albumen", "egg albumin", "ovalbumin",
        "mayonnaise", "mayo",
        "egg lecithin",
    ]

    # ── HONEY triggers (non-vegan but vegetarian) ─────────────────────────────
    HONEY_KW = [
        "honey", "bee pollen", "royal jelly", "beeswax", "propolis",
    ]

    # ── VEGAN-QUALIFIED TERMS — these override generic uncertain keywords ─────
    # e.g. "vegan natural flavors" should NEVER be classified as Uncertain
    VEGAN_QUALIFIERS = [
        "vegan natural flavor", "vegan natural flavour",
        "vegan natural flavoring", "vegan natural flavouring",
        "plant-based flavor", "plant-based flavour",
        "plant-based flavoring", "plant-based flavouring",
        "plant based flavor", "plant based flavour",
        "certified vegan", "vegan certified",
        "suitable for vegans", "suitable for vegetarians and vegans",
    ]

    # Known vegan brands — their "natural flavors" defaults to vegan
    VEGAN_BRANDS = {
        "daiya", "follow your heart", "tofutti", "earth balance",
        "miyoko", "miyoko's", "violife", "kite hill", "treeline",
        "field roast", "gardein", "beyond meat", "impossible",
        "oatly", "alpro", "silk", "so delicious", "coconut bliss",
        "rao's homemade", "boca", "amy's", "annie's", "nature's own",
        "lightlife", "quorn", "morningstar", "bob's red mill",
        "enjoy life", "free2b", "pamela's",
    }

    # ── UNCERTAIN keywords ────────────────────────────────────────────────────
    UNCERTAIN_KW = [
        "natural flavor", "natural flavour", "natural flavoring", "natural flavouring",
        "artificial flavor", "artificial flavour",
        "mono and diglycerides", "monoglycerides", "diglycerides",
        "e471", "e472", "e473", "e474", "e475", "e476", "e481", "e482",
        "glycerin", "glycerol", "glycerine",
        "stearic acid", "stearate",
        "vitamin d3", "cholecalciferol",
        # Generic flavoring — source unknown unless specified
        "flavoring", "flavouring", "natural flavoring", "natural flavouring",
        "artificial flavoring", "artificial flavouring",
        # Other ambiguous additives
        "starter culture",  # usually microbial but source unspecified

        # Ambiguous emulsifiers / stabilisers
        "polysorbate", "sodium stearoyl lactylate", "ssl",
        "datem",                              # diacetyl tartaric acid ester of monoglyceride
        # Ambiguous source fats / waxes
        # carnauba wax → vegan (E903, from carnauba palm leaf), NOT uncertain
    ]

    # ── ENZYME keywords — unspecified source → Uncertain (conservative) ───────
    # Explicit plant/microbial enzymes are safe. Generic "enzymes" are not.
    SAFE_ENZYME_QUALIFIERS = [
        "microbial", "fungal", "plant", "vegetable", "yeast",
        "bacterial", "koji", "aspergillus", "rhizopus",
    ]
    ENZYME_KW = [
        "enzyme", "enzymes", "enzyme blend", "food enzymes",
        "lipase", "protease", "amylase", "cellulase", "lactase",
    ]

    # ── RENNET — source-aware classification ─────────────────────────────────
    # animal/traditional/generic rennet → Non-Vegetarian
    # microbial/vegetarian rennet → Vegetarian
    # unspecified "rennet" → Uncertain (we do NOT assume vegetarian)
    # (Note: specific animal rennet strings are already in NON_VEG_KW above)
    UNCERTAIN_RENNET_KW = [
        "rennet",           # unspecified — could be animal or microbial
        "cheese enzymes",   # vague — could include animal rennet
    ]
    SAFE_RENNET_KW = [
        "microbial rennet", "vegetable rennet", "vegetarian rennet",
        "plant rennet", "fungal rennet", "fpc",  # fermentation-produced chymosin
        "microbial coagulant", "vegetarian coagulant",
    ]

    # ── ALLERGEN map ──────────────────────────────────────────────────────────
    ALLERGEN_MAP = {
        "dairy":     ["milk", "cream", "butter", "cheese", "whey", "casein",
                      "lactose", "ghee", "yogurt", "kefir", "milkfat"],
        "eggs":      ["egg", "albumin", "albumen", "mayonnaise"],
        "gluten":    ["wheat", "barley", "rye", "spelt", "semolina", "seitan",
                      "wheat starch", "wheat flour"],
        "soy":       ["soy", "soya", "soybean", "tofu", "tempeh", "miso", "edamame"],
        "peanuts":   ["peanut", "groundnut", "arachis"],
        "tree nuts": ["almond", "cashew", "walnut", "pecan", "pistachio",
                      "macadamia", "hazelnut", "brazil nut", "pine nut"],
        "fish":      ["fish", "anchov", "tuna", "salmon", "cod", "tilapia", "isinglass"],
        "shellfish": ["shrimp", "prawn", "lobster", "crab", "oyster", "clam",
                      "mussel", "scallop"],
        "sesame":    ["sesame", "tahini"],
        "wheat":     ["wheat", "wheat flour", "wheat starch", "semolina"],
    }

    def __init__(self, kb: IngredientKnowledgeBase, vs: VectorStore):
        self.kb = kb
        self.vs = vs
        # Compiled at init to avoid repeated compilation
        self.ENZYME_SAFE_QUALIFIERS_RE = re.compile(
            r"\b(microbial|fungal|plant|vegetable|bacterial|yeast|koji)\s+enzymes?",
            re.IGNORECASE,
        )

    def _is_plant_safe(self, name_l: str) -> bool:
        """Return True if this ingredient is clearly plant-based."""
        # Exact match in plant-safe set
        if name_l in self.PLANT_SAFE_EXACT:
            return True
        # Check if any plant-safe substring appears
        for sub in self.PLANT_SAFE_SUBSTRINGS:
            if sub in name_l:
                return True
        return False

    def classify(self, ingredient_name: str) -> IngredientResult:
        name = ingredient_name.strip()
        name_l = name.lower()

        # ── PRE-GUARD: run enzyme + rennet checks BEFORE KB and plant-safe ────
        # These must fire first because the KB classifies rennet as "dairy"
        # (which would give Vegetarian) when it should be Non-Vegetarian for animal rennet.
        pre = self._keyword_classify(name_l)
        if pre is not None:
            # Only use the pre-classification result if it's enzyme/rennet related
            # (keyword_classify handles all cases; we just need its result here
            #  so we can short-circuit before KB overrides)
            return pre

        # ── Guard: if clearly plant-safe, skip non-vegan checks ──────────────
        if self._is_plant_safe(name_l):
            # Check KB but override any non-vegan result — plant-safe takes priority
            entry = self.kb.lookup(name_l)
            if entry:
                kb_vegan = entry.get("vegan_status", "vegan")
                kb_cat   = entry.get("category", "vegan")
                # If KB says non-vegan but we know it's plant-safe → trust plant-safe
                if kb_vegan == "non-vegan" or kb_cat == "dairy":
                    return IngredientResult(
                        name=name, normalized=name,
                        vegan_status="vegan", vegetarian_status="vegan",
                        category="vegan", confidence=0.90,
                        reason="Plant-based ingredient (cacao/cocoa/coconut derived, not dairy butter)",
                        allergens=self._detect_allergens(name_l),
                        health_flags=[], alternatives="", description="Plant-derived",
                    )
                return IngredientResult(
                    name=name, normalized=entry["name"],
                    vegan_status=kb_vegan,
                    vegetarian_status=entry.get("vegetarian_status", "vegan"),
                    category=kb_cat,
                    confidence=float(entry.get("confidence", 0.95)),
                    reason=entry.get("description", "Plant-based ingredient"),
                    allergens=self._detect_allergens(name_l),
                    health_flags=entry.get("health_flags", []),
                    alternatives="", description=entry.get("description", ""),
                )
            # Not in KB but is plant-safe → return vegan
            return IngredientResult(
                name=name, normalized=name,
                vegan_status="vegan", vegetarian_status="vegan",
                category="vegan", confidence=0.85,
                reason="Plant-based ingredient",
                allergens=self._detect_allergens(name_l),
                health_flags=[], alternatives="", description="Plant-derived",
            )

        # ── Layer 2: KB lookup (for ingredients not caught by keyword rules) ───
        # Gives accurate descriptions and confidence from the JSON knowledge base
        entry = self.kb.lookup(name_l)
        if entry:
            return IngredientResult(
                name=name, normalized=entry["name"],
                vegan_status=entry["vegan_status"],
                vegetarian_status=entry.get("vegetarian_status", "vegan"),
                category=entry["category"],
                confidence=float(entry.get("confidence", 0.95)),
                reason=entry.get("description", ""),
                allergens=entry.get("allergens", []),
                health_flags=entry.get("health_flags", []),
                alternatives=entry.get("alternatives", ""),
                description=entry.get("description", ""),
            )

        # ── Layer 3: Vector semantic search (only if NOT plant-safe) ─────────
        vs_results = self.vs.query(name, n=2)
        if vs_results:
            top = vs_results[0]
            top_entry = self.kb.lookup(top.get("name", ""))
            if top_entry:
                # CRITICAL: if top match is non-vegan, only use it if
                # the ingredient itself is NOT plant-safe and similarity is high
                top_vs = top_entry.get("vegan_status", "uncertain")
                # Don't propagate non-vegan status via semantic match alone
                # — only use the semantic match for "uncertain" or "vegan" results
                if top_vs == "non-vegan":
                    # Return uncertain instead of propagating false positive
                    return IngredientResult(
                        name=name, normalized=name,
                        vegan_status="uncertain", vegetarian_status="uncertain",
                        category="unknown", confidence=0.40,
                        reason=f"Origin unclear — may be similar to '{top_entry['name']}'. Verify with manufacturer.",
                        allergens=self._detect_allergens(name_l),
                        health_flags=[], alternatives="", description="Unknown ingredient",
                    )
                return IngredientResult(
                    name=name, normalized=f"{top_entry['name']} (similar)",
                    vegan_status=top_vs,
                    vegetarian_status=top_entry.get("vegetarian_status", "uncertain"),
                    category=top_entry["category"], confidence=0.65,
                    reason=f"Similar to '{top_entry['name']}' — {top_entry.get('description','')}",
                    allergens=self._detect_allergens(name_l),
                    health_flags=[], alternatives=top_entry.get("alternatives", ""),
                    description=top_entry.get("description", ""),
                )

        # ── Layer 4: Fallback ─────────────────────────────────────────────────
        return IngredientResult(
            name=name, normalized=name,
            vegan_status="uncertain", vegetarian_status="uncertain",
            category="unknown", confidence=0.30,
            reason="Not found in knowledge base. Origin unclear — verify with manufacturer.",
            allergens=self._detect_allergens(name_l),
            health_flags=[], alternatives="", description="Unknown ingredient",
        )

    def _keyword_classify(self, name_l: str) -> Optional[IngredientResult]:
        """
        Strict keyword classification following priority order:
        1. Confirmed animal-derived → Non-Vegetarian
        2. Egg only → Eggetarian
        3. Ambiguous / unknown source → Uncertain
        4. Dairy only → Vegetarian
        5. Falls through → None (caller tries next layer)
        """

        # ── 0. SAFE RENNET CHECK (must run before generic NON_VEG_KW to avoid
        #       accidentally triggering on "microbial rennet") ─────────────────
        if "rennet" in name_l or "coagulant" in name_l:
            # Explicitly safe rennet sources
            if any(safe in name_l for safe in self.SAFE_RENNET_KW):
                # Microbial/vegetarian rennet → Vegetarian (not vegan — used in cheese)
                return IngredientResult(
                    name=name_l, normalized=name_l,
                    vegan_status="non-vegan", vegetarian_status="vegetarian",
                    category="dairy", confidence=0.88,
                    reason="Microbial or vegetarian rennet — suitable for vegetarians but not vegan.",
                    allergens=self._detect_allergens(name_l),
                    health_flags=[], alternatives="vegan cheese alternatives",
                    description="Vegetarian rennet (microbial/plant-derived coagulant)",
                )
            # Explicitly animal rennet → Non-Vegetarian (already in NON_VEG_KW but guard here too)
            if any(a in name_l for a in ["animal rennet", "traditional rennet", "calf rennet"]):
                return IngredientResult(
                    name=name_l, normalized=name_l,
                    vegan_status="non-vegan", vegetarian_status="non-vegetarian",
                    category="animal-derived", confidence=0.97,
                    reason="Animal rennet — derived from calf stomach lining. Not vegetarian.",
                    allergens=self._detect_allergens(name_l),
                    health_flags=[], alternatives="microbial rennet, vegetarian cheese",
                    description="Animal-derived coagulant from calf stomach",
                )
            # Generic "rennet" or "cheese enzymes" — source unknown → Uncertain
            if any(u in name_l for u in self.UNCERTAIN_RENNET_KW):
                return IngredientResult(
                    name=name_l, normalized=name_l,
                    vegan_status="uncertain", vegetarian_status="uncertain",
                    category="questionable", confidence=0.50,
                    reason=(
                        f"'{name_l}' — rennet source unspecified. Could be animal (non-vegetarian) "
                        "or microbial (vegetarian). Cannot confirm without manufacturer clarification."
                    ),
                    allergens=self._detect_allergens(name_l),
                    health_flags=[], alternatives="look for 'microbial rennet' or certified vegetarian cheese",
                    description="Rennet of unknown origin — potentially animal-derived",
                )

        # ── 1. ENZYME CHECK — generic enzymes without declared source ─────────
        # NOTE: Only fire enzyme check if no clear dairy/meat trigger is also present.
        # "Cheese seasoning (whey, enzymes)" should be Vegetarian (dairy), not Uncertain.
        _has_dairy_in_name = any(kw in name_l for kw in self.DAIRY_KW
                                 if kw not in ("butter", "cream", "milk"))  # avoid plant false pos
        _has_dairy_in_name = _has_dairy_in_name or any(
            kw in name_l for kw in ("whey", "casein", "caseinate", "lactose",
                                     "cheddar", "mozzarella", "cheese", "yogurt",
                                     "parmesan", "ghee", "milkfat", "milk fat")
        )
        enzyme_hit = next((kw for kw in self.ENZYME_KW if kw in name_l), None)
        if enzyme_hit and not _has_dairy_in_name:
            # Safe if an explicit plant/microbial qualifier is present
            has_safe_qualifier = any(q in name_l for q in self.SAFE_ENZYME_QUALIFIERS)
            if has_safe_qualifier:
                return IngredientResult(
                    name=name_l, normalized=name_l,
                    vegan_status="vegan", vegetarian_status="vegan",
                    category="vegan", confidence=0.88,
                    reason=f"'{name_l}' — microbial or plant-derived enzyme. Suitable for vegans.",
                    allergens=self._detect_allergens(name_l),
                    health_flags=[], alternatives="", description="Plant/microbial enzyme",
                )
            # Generic enzyme without declared source → Uncertain (never Vegan)
            return IngredientResult(
                name=name_l, normalized=name_l,
                vegan_status="uncertain", vegetarian_status="uncertain",
                category="questionable", confidence=0.50,
                reason=(
                    f"'{name_l}' — enzyme source not declared. Enzymes may be plant, microbial, "
                    "or animal-derived (e.g. calf lipase, pepsin). Cannot classify as vegan "
                    "without manufacturer confirmation."
                ),
                allergens=self._detect_allergens(name_l),
                health_flags=[],
                alternatives="ask manufacturer: 'Are your enzymes plant or microbial-derived?'",
                description="Enzyme of unspecified origin — potentially animal-derived",
            )

        # ── 2. NON-VEG keywords (gelatin, meat, fish, shellfish, carmine…) ────
        for kw in self.NON_VEG_KW:
            if kw in name_l:
                # Guard: don't trigger "fish" on botanical names like "star anise"
                if kw in ("fish", "anchov") and any(
                    s in name_l for s in ["starfish", "cuttlefish", "swordfish",
                                           "blowfish", "jellyfish", "angelfish"]
                ):
                    continue
                # Guard: "oyster" in "oyster mushroom" is vegan
                if kw == "oyster" and "mushroom" in name_l:
                    continue
                # Guard: "crab" in "crab apple" is vegan
                if kw == "crab" and "apple" in name_l:
                    continue
                return IngredientResult(
                    name=name_l, normalized=name_l,
                    vegan_status="non-vegan", vegetarian_status="non-vegetarian",
                    category="animal-derived", confidence=0.95,
                    reason=f"Contains '{kw}' — confirmed animal-derived. Not vegan or vegetarian.",
                    allergens=self._detect_allergens(name_l),
                    health_flags=[], alternatives="plant-based alternatives available",
                    description=f"Animal-derived ingredient detected: {kw}",
                )

        # ── 3. MEAT keywords ──────────────────────────────────────────────────
        for kw in self.MEAT_KW:
            if kw in name_l:
                return IngredientResult(
                    name=name_l, normalized=name_l,
                    vegan_status="non-vegan", vegetarian_status="non-vegetarian",
                    category="meat", confidence=0.97,
                    reason=f"Contains '{kw}' — meat ingredient. Not vegetarian.",
                    allergens=self._detect_allergens(name_l),
                    health_flags=[], alternatives="plant-based meat alternatives",
                    description=f"Meat ingredient: {kw}",
                )

        # ── 4. EGG keywords → Eggetarian ─────────────────────────────────────
        for kw in self.EGG_KW:
            if kw in name_l:
                return IngredientResult(
                    name=name_l, normalized=name_l,
                    vegan_status="non-vegan", vegetarian_status="eggetarian",
                    category="egg", confidence=0.95,
                    reason=f"Contains '{kw}' — egg-derived. Eggetarian.",
                    allergens=self._detect_allergens(name_l) or ["eggs"],
                    health_flags=[], alternatives="flax egg, chia egg, aquafaba",
                    description=f"Egg ingredient: {kw}",
                )

        # ── 5. HONEY / BEE products → Vegetarian ─────────────────────────────
        for kw in self.HONEY_KW:
            if kw in name_l:
                return IngredientResult(
                    name=name_l, normalized=name_l,
                    vegan_status="non-vegan", vegetarian_status="vegetarian",
                    category="honey/bees", confidence=0.92,
                    reason=f"Contains '{kw}' — bee product. Not vegan but vegetarian.",
                    allergens=[],
                    health_flags=[], alternatives="agave nectar, maple syrup, date syrup",
                    description=f"Bee-derived ingredient: {kw}",
                )

        # ── 5b. UNCERTAIN RENNET / CHEESE ENZYME check (before dairy) ─────────
        # "Cheese enzymes" alone is ambiguous — could include animal rennet
        for ur_kw in self.UNCERTAIN_RENNET_KW:
            if ur_kw in name_l:
                return IngredientResult(
                    name=name_l, normalized=name_l,
                    vegan_status="uncertain", vegetarian_status="uncertain",
                    category="questionable", confidence=0.50,
                    reason=(
                        f"'{name_l}' — source unspecified. Could include animal-derived rennet "
                        "or animal enzymes. Cannot confirm without manufacturer clarification."
                    ),
                    allergens=self._detect_allergens(name_l),
                    health_flags=[],
                    alternatives="look for 'microbial rennet' or certified vegetarian/vegan label",
                    description="Ambiguous enzymes or rennet of unknown origin",
                )

        # ── 6. DAIRY keywords → Vegetarian (with plant-derived guards) ─────
        # Plant butters: "cacao butter", "cocoa butter", "shea butter" etc. are NOT dairy
        PLANT_BUTTER_PFXS = [
            "cacao", "cocoa", "shea", "coconut", "mango", "illipe", "kokum",
            "sunflower", "almond", "peanut", "hemp", "avocado", "pumpkin",
            "nut ", "cashew", "hazelnut", "pistachio", "vegan",
        ]
        PLANT_CREAM_PFXS = ["coconut", "oat", "soy", "soya", "almond", "cashew", "vegan", "non-dairy", "of tartar", "tartar"]
        PLANT_MILK_PFXS  = ["coconut", "oat", "soy", "soya", "almond", "rice", "hemp",
                             "cashew", "oatmilk", "soymilk", "non-dairy", "plant"]
        for kw in self.DAIRY_KW:
            if kw not in name_l:
                continue
            # Guard: skip plant-derived butters
            if kw == "butter" and any(p in name_l for p in PLANT_BUTTER_PFXS):
                continue
            # Guard: skip plant-derived creams
            if kw == "cream" and any(p in name_l for p in PLANT_CREAM_PFXS):
                continue
            # Guard: skip plant-derived milks
            if kw == "milk" and any(p in name_l for p in PLANT_MILK_PFXS):
                continue
            return IngredientResult(
                name=name_l, normalized=name_l,
                vegan_status="non-vegan", vegetarian_status="vegetarian",
                category="dairy", confidence=0.93,
                reason=f"Contains '{kw}' — dairy product. Not vegan but vegetarian.",
                allergens=self._detect_allergens(name_l) or ["dairy"],
                health_flags=[], alternatives="plant-based milk alternatives",
                description=f"Dairy ingredient: {kw}",
            )

        # ── 7. UNCERTAIN keywords — but check vegan qualifiers FIRST ─────────
        for kw in self.UNCERTAIN_KW:
            if kw in name_l:
                # OVERRIDE: if a vegan/plant-based modifier qualifies this ingredient,
                # it is NOT uncertain — it is vegan.
                # e.g. "vegan natural flavors" → Vegan, not Uncertain
                if any(vq in name_l for vq in self.VEGAN_QUALIFIERS):
                    return IngredientResult(
                        name=name_l, normalized=name_l,
                        vegan_status="vegan", vegetarian_status="vegan",
                        category="vegan", confidence=0.90,
                        reason=f"'{name_l}' — explicitly qualified as vegan/plant-based. Suitable for vegans.",
                        allergens=self._detect_allergens(name_l),
                        health_flags=[], alternatives="",
                        description="Vegan-qualified ingredient",
                    )
                return IngredientResult(
                    name=name_l, normalized=name_l,
                    vegan_status="uncertain", vegetarian_status="uncertain",
                    category="questionable", confidence=0.55,
                    reason=(
                        f"'{name_l}' — source not confirmed. '{kw}' may be plant "
                        "or animal-derived. Verify with manufacturer."
                    ),
                    allergens=self._detect_allergens(name_l),
                    health_flags=[], alternatives="",
                    description=f"Ingredient with uncertain origin: {kw}",
                )

        return None

    # ── CONTEXT-AWARE ENZYME RULE ────────────────────────────────────────────
    # "Enzymes" inside "Cheese [Milk, Cheese Cultures, Salt, Enzymes]" in a
    # US product = animal-derived (Frito-Lay official confirmation).
    # Pattern: "enzymes" appearing inside or immediately after "cheese" context.
    CHEESE_ENZYME_PATTERN = re.compile(
        r"cheese\s*\[[^\]]*\benzymes?\b[^\]]*\]"
        r"|cheese\s*\([^)]*\benzymes?\b[^)]*\)"
        r"|\bcheese cultures?[^,;)\]]*,\s*(?:salt\s*,\s*)?enzymes?"
        r"|\benzymes?\b[^,;)\]]{0,30}(?:cheese|milk|rennet|cultures?)",
        re.IGNORECASE,
    )

    def scan_raw_for_hidden_triggers(self,
                                      raw: str,
                                      existing_results: list) -> list:
        """
        Scan the FULL raw ingredient string for animal-derived triggers that
        may have been missed because they were nested inside sub-ingredients.

        Returns a list of additional IngredientResult objects to append.
        """
        raw_l = raw.lower()
        extra = []
        already_flagged_cats = {r.category for r in existing_results}
        already_flagged_names = {r.name.lower() for r in existing_results}

        # ── Rule 1: "Enzymes" in a cheese context → Non-Vegetarian ──────────
        # Covers: Cheddar Cheese [Milk, Cheese Cultures, Salt, Enzymes]
        #         Cheese (milk, cultures, salt, enzymes)
        # EXCLUDES: Cheddar Cheese [..., Microbial Enzymes] (safe)
        cheese_match = self.CHEESE_ENZYME_PATTERN.search(raw)
        has_unsafe_cheese_enzymes = (
            cheese_match is not None and
            not self.ENZYME_SAFE_QUALIFIERS_RE.search(raw)
        )
        if has_unsafe_cheese_enzymes:
            # Only add if not already caught as non-vegetarian
            already_non_veg = any(
                r.vegetarian_status == "non-vegetarian" for r in existing_results
            )
            if not already_non_veg:
                extra.append(IngredientResult(
                    name="Cheese Enzymes (animal-derived)",
                    normalized="cheese enzymes",
                    vegan_status="non-vegan",
                    vegetarian_status="non-vegetarian",
                    category="animal-derived",
                    confidence=0.88,
                    reason=(
                        "Unspecified 'enzymes' detected inside cheese ingredient. "
                        "In US products, Frito-Lay and other manufacturers confirm "
                        "these are animal-derived (calf/porcine rennet). "
                        "Not vegetarian or vegan without explicit 'microbial' label."
                    ),
                    allergens=[],
                    health_flags=[],
                    alternatives="look for 'microbial rennet' or certified vegetarian label",
                    description="Animal-derived cheese enzymes (rennet/lipase from calf/pig stomach)",
                ))

        # ── Rule 2: Scan for any NON_VEG_KW buried in the raw string ─────────
        # that wasn't already surfaced by per-ingredient classification
        for kw in self.NON_VEG_KW:
            if kw in raw_l:
                # Check if already caught
                already_caught = any(
                    kw in r.name.lower() or kw in r.reason.lower()
                    for r in existing_results
                )
                if not already_caught:
                    # Guard against false positives
                    if kw == "oyster" and "mushroom" in raw_l: continue
                    if kw == "crab" and "apple" in raw_l: continue
                    if kw in ("fish", "anchov") and any(
                        s in raw_l for s in ["starfish", "catfish", "star anise"]
                    ): continue

                    extra.append(IngredientResult(
                        name=f"Hidden: {kw}",
                        normalized=kw,
                        vegan_status="non-vegan",
                        vegetarian_status="non-vegetarian",
                        category="animal-derived",
                        confidence=0.85,
                        reason=(
                            f"'{kw}' detected in ingredient string — animal-derived. "
                            "May have been nested inside a compound ingredient."
                        ),
                        allergens=[],
                        health_flags=[],
                        alternatives="plant-based alternatives available",
                        description=f"Hidden animal-derived ingredient: {kw}",
                    ))

        # ── Rule 3: "Enzymes" alone (not in cheese context) with no qualifier ─
        # Already handled per-ingredient but catch raw-string misses too
        if re.search(r"\benzymes?\b", raw_l) and not self.CHEESE_ENZYME_PATTERN.search(raw):
            has_safe_q = any(q in raw_l for q in self.SAFE_ENZYME_QUALIFIERS)
            already_flagged = any(
                "enzyme" in r.name.lower() or "enzyme" in r.reason.lower()
                for r in existing_results
            )
            if not has_safe_q and not already_flagged:
                extra.append(IngredientResult(
                    name="Unspecified Enzymes",
                    normalized="enzymes",
                    vegan_status="uncertain",
                    vegetarian_status="uncertain",
                    category="questionable",
                    confidence=0.55,
                    reason=(
                        "Unspecified 'enzymes' in ingredient list — source not declared. "
                        "May be plant, microbial, or animal-derived."
                    ),
                    allergens=[],
                    health_flags=[],
                    alternatives="contact manufacturer to confirm enzyme source",
                    description="Enzyme of unspecified origin",
                ))

        return extra

    def _contextual_vegan_check(
        self,
        raw: str,
        product_name: str,
        results: list,
        has_non_veg: bool,
        has_dairy: bool,
        has_egg: bool,
        has_honey: bool,
    ) -> tuple[bool, str]:
        """
        Holistic contextual check — run AFTER per-ingredient classification.

        Returns (should_upgrade_to_vegan: bool, note: str)

        Upgrades Uncertain → Vegan when:
        - The ENTIRE ingredient list is composed of plant-based items EXCEPT for
          generic uncertain ingredients (natural flavors, glycerin, etc.)
        - AND no confirmed animal trigger exists
        - AND strong contextual evidence supports vegan classification

        Does NOT upgrade when genuine ambiguity exists (enzymes, rennet, etc.)
        """
        if has_non_veg or has_dairy or has_egg or has_honey:
            return False, ""

        raw_l = raw.lower()
        name_l = product_name.lower() if product_name else ""

        # ── Check 1: Explicit vegan qualifiers in the raw ingredient string ───
        if any(vq in raw_l for vq in self.VEGAN_QUALIFIERS):
            return True, "Ingredient list contains explicit vegan qualifiers (e.g. 'vegan natural flavors')."

        # ── Check 2: Known vegan brand in product name ─────────────────────
        if any(brand in name_l for brand in self.VEGAN_BRANDS):
            return True, f"Product is from a certified/known vegan brand — natural flavors default to vegan."

        # ── Check 3: All non-uncertain ingredients are clearly plant-based ──
        # Count uncertain vs confirmed vegan
        uncertain_results = [r for r in results if r.vegan_status == "uncertain"]
        vegan_results     = [r for r in results if r.vegan_status in ("vegan", "usually vegan")]
        total             = len(results)

        if total == 0:
            return False, ""

        # Only uncertain ingredients are flagged — the rest are confirmed vegan
        if len(uncertain_results) == 0:
            return False, ""  # already vegan — no upgrade needed

        # If the uncertain results are ONLY generic ambiguous additives
        # (natural flavors, flavoring, glycerin) — and all OTHER ingredients
        # are clearly plant-based — upgrade to Vegan with a note
        GENERIC_UNCERTAIN = {
            "natural flavor", "natural flavour", "natural flavoring",
            "natural flavouring", "artificial flavor", "artificial flavour",
            "artificial flavoring", "artificial flavouring",
            "flavoring", "flavouring", "flavor",
        }

        uncertain_names_l = {r.name.lower() for r in uncertain_results}
        # An uncertain result counts as "generic" for upgrade purposes if:
        # a) it matches a generic flavor/additive term, OR
        # b) it is a known plant-origin ingredient that just wasn't in the KB
        #    (okra, spices, herbs, etc.) — identified by plant-safe substrings
        def _is_generic_or_plant_uncertain(uname: str) -> bool:
            if any(gen in uname for gen in GENERIC_UNCERTAIN):
                return True
            # Check if it contains plant-safe substrings → plant origin likely
            if self._is_plant_safe(uname):
                return True
            # Check individual plant substrings
            return any(sub in uname for sub in self.PLANT_SAFE_SUBSTRINGS)

        all_uncertain_are_generic = all(
            _is_generic_or_plant_uncertain(uname)
            for uname in uncertain_names_l
        )

        # If all remaining uncertain items are just generic flavor terms
        # AND the confirmed vegan ingredients heavily outnumber uncertain ones
        if all_uncertain_are_generic and len(vegan_results) >= len(uncertain_results):
            # Final check: does the overall ingredient profile look plant-based?
            # Count plant-safe signals in the raw string
            plant_signals = sum(1 for sub in self.PLANT_SAFE_SUBSTRINGS if sub in raw_l)
            if plant_signals >= 3:
                note = (
                    "Natural flavors are unspecified, but the overall evidence strongly "
                    "supports a vegan classification. The ingredient profile is entirely "
                    "plant-based. Low-risk — contact manufacturer to confirm if strictly required."
                )
                return True, note

        # ── Check 4: Glycerin/Mono-diglycerides ONLY uncertainty ─────────────
        EMULSIFIER_UNCERTAIN = {
            "glycerin", "glycerol", "glycerine",
            "mono and diglycerides", "monoglycerides", "diglycerides",
            "e471", "e472",
        }
        all_uncertain_are_emulsifiers = all(
            any(em in uname for em in EMULSIFIER_UNCERTAIN)
            for uname in uncertain_names_l
        )
        # Don't upgrade for emulsifier uncertainty — these genuinely need checking
        # unless context is very strong
        if all_uncertain_are_emulsifiers and len(vegan_results) >= 4:
            plant_signals = sum(1 for sub in self.PLANT_SAFE_SUBSTRINGS if sub in raw_l)
            if plant_signals >= 5:
                note = (
                    "Emulsifiers (glycerin/mono-diglycerides) may be plant or animal-derived. "
                    "The rest of the ingredient profile is entirely plant-based — likely vegan, "
                    "but confirm glycerin source with manufacturer if strictly required."
                )
                return True, note

        return False, ""

    def _detect_allergens(self, name_l: str) -> list:
        found = []
        for allergen, keywords in self.ALLERGEN_MAP.items():
            if any(kw in name_l for kw in keywords):
                found.append(allergen)
        return found


# ── Main Analysis Service ──────────────────────────────────────────────────────
class IngredientAnalysisService:
    def __init__(self):
        self.kb = IngredientKnowledgeBase()
        self.vs = VectorStore(self.kb)
        self.parser = IngredientParser()
        self.engine = ClassificationEngine(self.kb, self.vs)
        logger.info("IngredientAnalysisService initialized")

    def analyze(self, raw_ingredients, product_name: str = "Unknown Product") -> AnalysisResult:
        if raw_ingredients is None:
            raw_ingredients = ""
        raw_ingredients = str(raw_ingredients)
        logger.info(f"Analyzing: {product_name} — {raw_ingredients[:80]}...")

        parsed = self.parser.parse(raw_ingredients)
        if not parsed:
            return self._empty_result(product_name, raw_ingredients)

        results: list[IngredientResult] = [self.engine.classify(ing) for ing in parsed]

        # ── SAFETY NET: scan raw ingredient string for hidden triggers ────────
        # Catches cases where sub-ingredients inside brackets aren't parsed out
        # AND weren't caught per-ingredient (e.g. enzymes in cheese context).
        hidden = self.engine.scan_raw_for_hidden_triggers(raw_ingredients, results)
        if hidden:
            results.extend(hidden)

        # ── Aggregate with new diet logic ─────────────────────────────────────
        # Treat "usually non-vegan" same as "non-vegan" for safety
        NON_VEGAN_STATUSES = {"non-vegan", "usually non-vegan"}
        NON_VEG_STATUSES   = {"non-vegetarian", "usually non-vegetarian"}

        has_non_veg   = any(r.vegetarian_status in NON_VEG_STATUSES for r in results)
        has_meat      = any(r.category in ["meat", "animal-derived"] and
                           r.vegetarian_status in NON_VEG_STATUSES for r in results)
        has_dairy     = any(r.category == "dairy" for r in results)
        has_egg       = any(r.category == "egg" for r in results)
        has_honey     = any(r.category == "honey/bees" for r in results)
        has_non_vegan = any(r.vegan_status in NON_VEGAN_STATUSES for r in results)
        has_uncertain = any(
            r.vegan_status == "uncertain"
            # "usually vegan" is fine — not actually uncertain
            and r.vegan_status != "usually vegan"
            for r in results
        )
        has_rennet_uncertain = any(
            r.vegan_status == "uncertain" and (
                "rennet" in r.name.lower() or "rennet" in r.reason.lower()
            )
            for r in results
        )
        # Unspecified enzymes as a standalone ingredient alongside dairy
        # means we cannot confirm the cheese is vegetarian (could be animal rennet)
        # This is DIFFERENT from CHEESE_ENZYME_PATTERN (which → Non-Veg).
        # Standalone "Enzymes" + "Cheese" as separate ingredients → Uncertain
        has_enzyme_uncertain = any(
            r.vegan_status == "uncertain" and (
                "enzyme" in r.name.lower() or
                "enzyme source not declared" in r.reason.lower()
            )
            for r in results
        )

        non_vegan_list = [r for r in results if r.vegan_status in NON_VEGAN_STATUSES]
        uncertain_list = [r for r in results if r.vegan_status == "uncertain"]

        # ── Contextual holistic check: can we upgrade Uncertain → Vegan? ─────
        # This runs AFTER per-ingredient analysis, applying product-level reasoning.
        # Only fires when has_uncertain=True and no animal triggers exist.
        contextual_vegan_note = ""
        if has_uncertain and not has_non_veg and not has_dairy and not has_egg and not has_honey:
            upgrade, note = self.engine._contextual_vegan_check(
                raw_ingredients, product_name, results,
                has_non_veg, has_dairy, has_egg, has_honey,
            )
            if upgrade:
                has_uncertain = False
                contextual_vegan_note = note

        # ── Determine diet category (priority order from spec) ──────────────
        # 1. Confirmed animal-derived → Non-Vegetarian
        # 2. Egg only → Eggetarian
        # 3. Ambiguous/unknown → Uncertain (but NOT if dairy is confirmed)
        # 4. Dairy only → Vegetarian
        # 5. All clear → Vegan
        if has_non_veg:
            diet_category = "Non-Vegetarian"
            diet_color    = "#c0392b"
            overall_vegan = "Non-Vegetarian"
            overall_veg   = "Non-Vegetarian"
            vegan_conf    = max((r.confidence for r in non_vegan_list), default=0.90)

        elif has_egg and not has_dairy and not has_honey:
            diet_category = "Eggetarian"
            diet_color    = "#e67e22"
            overall_vegan = "Eggetarian"
            overall_veg   = "Eggetarian"
            vegan_conf    = 0.90

        elif (has_dairy or has_honey) and has_egg:
            # Dairy + egg → Eggetarian
            diet_category = "Eggetarian"
            diet_color    = "#e67e22"
            overall_vegan = "Eggetarian"
            overall_veg   = "Eggetarian"
            vegan_conf    = 0.88

        elif has_rennet_uncertain and not has_non_veg:
            # Unspecified rennet → Uncertain (even if dairy also present)
            # Cannot confirm if animal or microbial without manufacturer data
            diet_category = "Uncertain"
            diet_color    = "#f39c12"
            overall_vegan = "Uncertain"
            overall_veg   = "Uncertain"
            vegan_conf    = 0.50

        elif has_enzyme_uncertain and has_dairy and not has_non_veg:
            # Unspecified standalone enzymes + dairy → Uncertain
            # Cannot confirm enzyme source (could be animal rennet/lipase).
            # Spec example: "Cheese, Natural Flavor, Enzymes" → Uncertain
            diet_category = "Uncertain"
            diet_color    = "#f39c12"
            overall_vegan = "Uncertain"
            overall_veg   = "Uncertain"
            vegan_conf    = 0.50

        elif has_dairy or has_honey:
            diet_category = "Vegetarian"
            diet_color    = "#27ae60"
            overall_vegan = "Vegetarian"
            overall_veg   = "Vegetarian"
            vegan_conf    = 0.90

        elif has_uncertain and not has_dairy and not has_honey and not has_egg:
            # Pure uncertain (natural flavors, glycerin etc.) — no clear diet trigger
            diet_category = "Uncertain"
            diet_color    = "#f39c12"
            overall_vegan = "Uncertain"
            overall_veg   = "Uncertain"
            vegan_conf    = 0.55

        else:
            diet_category = "Vegan"
            diet_color    = "#1e8449"
            overall_vegan = "Vegan"
            overall_veg   = "Vegan"
            # "usually vegan" results count as vegan for confidence
            vegan_conf    = min((r.confidence for r in results
                                 if r.vegan_status in ("vegan","usually vegan")),
                                default=0.85)

        allergens = sorted(set(a for r in results for a in r.allergens))
        health_flags, ultra_proc, preservatives, additives = self._health_analysis(parsed)
        health_score = self._compute_health_score(results, health_flags, ultra_proc, preservatives)
        reasoning = self._build_reasoning(diet_category, non_vegan_list, uncertain_list, product_name, contextual_vegan_note)
        recommendations = self._build_recommendations(non_vegan_list, allergens, health_score)

        return AnalysisResult(
            product_name=product_name,
            raw_ingredients=raw_ingredients,
            parsed_ingredients=parsed,
            ingredient_results=results,
            overall_vegan=overall_vegan,
            overall_vegetarian=overall_veg,
            vegan_confidence=vegan_conf,
            allergens_detected=allergens,
            health_score=health_score,
            health_flags=health_flags,
            non_vegan_ingredients=[r.name for r in non_vegan_list],
            uncertain_ingredients=[r.name for r in uncertain_list],
            ultra_processed_markers=ultra_proc,
            preservatives=preservatives,
            additives=additives,
            reasoning=reasoning,
            recommendations=recommendations,
            diet_category=diet_category,
            diet_color=diet_color,
        )

    def _health_analysis(self, parsed):
        joined = " ".join(parsed).lower()
        flags, ultra_proc, preservatives, additives = [], [], [], []
        high_sugar_kw = ["sugar", "corn syrup", "high fructose", "dextrose", "glucose syrup", "fructose"]
        if sum(1 for kw in high_sugar_kw if kw in joined) >= 2:
            flags.append("High sugar content")
        for kw in settings.ULTRA_PROCESSED_MARKERS:
            if kw.lower() in joined:
                ultra_proc.append(kw)
                if "Ultra-processed indicator" not in flags:
                    flags.append("Ultra-processed indicator")
        for kw in settings.PRESERVATIVE_MARKERS:
            if kw.lower() in joined:
                preservatives.append(kw)
                if "Contains preservatives" not in flags:
                    flags.append("Contains preservatives")
        additives = list(set(re.findall(r"\b[Ee]\d{3,4}[a-z]?\b", " ".join(parsed))))
        if len(additives) > 4:
            flags.append(f"High additive count ({len(additives)} E-numbers)")
        return flags, ultra_proc, preservatives, additives

    def _compute_health_score(self, results, flags, ultra_proc, preservatives):
        score = 80
        score -= len([r for r in results if "non-vegan" in r.vegan_status]) * 2
        score -= len(flags) * 5
        score -= len(ultra_proc) * 4
        score -= len(preservatives) * 3
        return max(10, min(100, score))

    def _build_reasoning(self, diet: str, non_vegan, uncertain, product_name, contextual_note: str = ""):
        ICONS = {
            "Vegan": "🌱", "Vegetarian": "🧀", "Eggetarian": "🥚",
            "Non-Vegetarian": "🍖", "Uncertain": "⚠️",
        }
        icon = ICONS.get(diet, "❓")
        if diet == "Vegan":
            base = f"{icon} '{product_name}' is fully VEGAN — all ingredients are plant-based."
            if contextual_note:
                base += f" Note: {contextual_note}"
            return base
        elif diet == "Vegetarian":
            names = ", ".join(r.name for r in non_vegan[:4])
            return f"{icon} '{product_name}' is VEGETARIAN — contains dairy/honey but no meat, fish, or eggs. Dairy ingredients: {names}."
        elif diet == "Eggetarian":
            names = ", ".join(r.name for r in non_vegan[:4])
            return f"{icon} '{product_name}' is EGGETARIAN — contains egg(s): {names}."
        elif diet == "Non-Vegetarian":
            names = ", ".join(r.name for r in non_vegan[:5])
            return f"{icon} '{product_name}' is NON-VEGETARIAN — contains animal-derived ingredients: {names}."
        else:
            names = ", ".join(r.name for r in uncertain[:3])
            return f"⚠️ '{product_name}' has UNCERTAIN status — these ingredients need verification: {names}."

    def _build_recommendations(self, non_vegan, allergens, health_score):
        recs = []
        alts = set(a for r in non_vegan if r.alternatives for a in r.alternatives.split(", "))
        if alts: recs.append(f"Vegan alternatives: {', '.join(list(alts)[:4])}")
        if "dairy" in allergens: recs.append("Dairy detected — plant milks: oat, almond, soy, coconut")
        if "eggs" in allergens: recs.append("Eggs detected — replacers: flax egg, chia egg, aquafaba")
        if "gluten" in allergens: recs.append("Gluten detected — alternatives: rice flour, almond flour")
        if health_score < 50: recs.append("Low health score — consider whole food alternatives")
        if not recs: recs.append("Product meets vegan standards based on ingredient analysis")
        return recs

    def _empty_result(self, product_name, raw):
        return AnalysisResult(
            product_name=product_name, raw_ingredients=raw, parsed_ingredients=[],
            ingredient_results=[], overall_vegan="Unknown", overall_vegetarian="Unknown",
            vegan_confidence=0.0, allergens_detected=[], health_score=50,
            health_flags=[], non_vegan_ingredients=[], uncertain_ingredients=[],
            ultra_processed_markers=[], preservatives=[], additives=[],
            reasoning="No ingredients found to analyze.", recommendations=[],
            diet_category="Unknown", diet_color="#888888",
        )
