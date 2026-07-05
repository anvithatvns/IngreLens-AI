"""IngreLens AI — 🔍 Analyzer · Fuzzy search + Did you mean?"""
import streamlit as st, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from shared_ui import (inject_css, init_state, render_top_nav, render_page_header, add_history,
                        full_analysis_display, get_logo_b64, SAGE, cached_analyze, log_activity,
                        enter_page)
from backend.services.analysis_service import IngredientAnalysisService
from backend.services.product_service import ProductFetchService

st.set_page_config(page_title="Analyzer · IngreLens AI", page_icon="🔍", layout="wide")
inject_css(); init_state(); render_top_nav()
enter_page("analyzer")

@st.cache_resource(show_spinner=False)
def get_svc(): return IngredientAnalysisService(), ProductFetchService()
svc, prod_svc = get_svc()

# ── Local product database ─────────────────────────────────────────────────────
LOCAL_PRODUCTS = {
    "nutella":           {"name":"Nutella","brand":"Ferrero","barcode":"3017624010701","categories":"Sweet spreads, Chocolate spreads","ingredients_text":"Sugar, Palm oil, Hazelnuts (13%), Skimmed milk powder (8.7%), Fat-reduced cocoa (7.4%), Emulsifier (Soya lecithin), Vanillin","labels":"","allergens":["milk","nuts","soy"],"image":"","nutriscore":"E","nutriments":{"energy":539,"fat":30.9,"sugars":56.3,"protein":6.3,"salt":0.107,"fiber":0}},
    "oreo":              {"name":"Oreo Original","brand":"Mondelez","barcode":"7622300416981","categories":"Biscuits, Cookies","ingredients_text":"Unbleached enriched flour, Sugar, Palm and/or canola oil, Cocoa powder, High fructose corn syrup, Leavening, Salt, Soy lecithin, Vanillin, Chocolate","labels":"","allergens":["gluten","soy"],"image":"","nutriscore":"E","nutriments":{"energy":480,"fat":21,"sugars":42,"protein":5,"salt":0.75,"fiber":2}},
    "alpro oat":         {"name":"Alpro Oat Milk Original","brand":"Alpro","barcode":"5411188131335","categories":"Plant-based milks, Oat drinks","ingredients_text":"Water, Oat (10%), Sunflower oil, Calcium carbonate, Sea salt, Riboflavin B2, Vitamin B12, Vitamin D2, Dipotassium phosphate, Gellan gum","labels":"Vegan","allergens":["gluten"],"image":"","nutriscore":"B","nutriments":{"energy":47,"fat":1.5,"sugars":4,"protein":1,"salt":0.1,"fiber":0.5}},
    "silk oat":          {"name":"Silk Oatmilk Original","brand":"Silk","barcode":"0632154697732","categories":"Plant-based milks, Oat drinks","ingredients_text":"Oatmilk (water, whole grain oats), Sunflower oil, Contains 2% or less of: sea salt, gellan gum, vitamin A, vitamin D2, riboflavin, vitamin B12","labels":"Vegan","allergens":[],"image":"","nutriscore":"B","nutriments":{"energy":50,"fat":1.5,"sugars":7,"protein":1,"salt":0.15,"fiber":0}},
    "almond milk":       {"name":"Almond Breeze Original","brand":"Blue Diamond","barcode":"0037600294522","categories":"Plant-based milks, Almond drinks","ingredients_text":"Almond milk (filtered water, almonds 2%), Cane sugar, Calcium carbonate, Vitamin D2, Sea salt, Locust bean gum, Sunflower lecithin, Gellan gum, Natural flavors","labels":"Vegan","allergens":["tree nuts"],"image":"","nutriscore":"B","nutriments":{"energy":60,"fat":2.5,"sugars":8,"protein":1,"salt":0.15,"fiber":0}},
    "alpro soy":         {"name":"Alpro Soy Milk Original","brand":"Alpro","barcode":"5411188080176","categories":"Plant-based milks, Soy drinks","ingredients_text":"Water, Hulled soy beans (8.7%), Cane sugar, Sea salt, Calcium carbonate, Stabiliser (gellan gum), Vitamins (D2, B12, Riboflavin)","labels":"Vegan","allergens":["soy"],"image":"","nutriscore":"B","nutriments":{"energy":54,"fat":1.8,"sugars":2.9,"protein":3.3,"salt":0.12,"fiber":0}},
    "silk soy":          {"name":"Silk Soymilk Original","brand":"Silk","barcode":"0025293004376","categories":"Plant-based milks, Soy drinks","ingredients_text":"Soymilk (Filtered Water, Whole Soybeans), Cane Sugar, Sea Salt, Carrageenan, Natural Flavor, Calcium Carbonate, Vitamin A Palmitate, Vitamin D2, Riboflavin (B2), Vitamin B12","labels":"Vegan","allergens":["soy"],"image":"","nutriscore":"B","nutriments":{"energy":54,"fat":2,"sugars":6,"protein":3.3,"salt":0.13,"fiber":0}},
    "kit kat":           {"name":"Kit Kat Milk Chocolate","brand":"Nestlé","barcode":"4000539400404","categories":"Chocolate bars","ingredients_text":"Sugar, Wheat flour, Cocoa butter, Skimmed milk powder, Cocoa mass, Milk fat, Lactose, Emulsifier (Soya lecithin), Yeast, Salt, Natural vanilla flavouring","labels":"","allergens":["gluten","milk","soy"],"image":"","nutriscore":"E","nutriments":{"energy":508,"fat":25.6,"sugars":51.5,"protein":6.3,"salt":0.24,"fiber":1.5}},
    "coca-cola":         {"name":"Coca-Cola Classic","brand":"Coca-Cola","barcode":"5449000000996","categories":"Beverages, Sodas, Colas","ingredients_text":"Carbonated water, Sugar, Colour (Caramel E150d), Phosphoric acid, Natural flavourings including caffeine","labels":"","allergens":[],"image":"","nutriscore":"E","nutriments":{"energy":42,"fat":0,"sugars":10.6,"protein":0,"salt":0,"fiber":0}},
    "coke zero":         {"name":"Coca-Cola Zero Sugar","brand":"Coca-Cola","barcode":"5449000054227","categories":"Beverages, Sodas","ingredients_text":"Carbonated water, Colour (Caramel E150d), Phosphoric acid, Sweeteners (Aspartame, Acesulfame K), Natural flavourings including caffeine, Citric acid","labels":"","allergens":[],"image":"","nutriscore":"B","nutriments":{"energy":0,"fat":0,"sugars":0,"protein":0,"salt":0,"fiber":0}},
    "pepsi":             {"name":"Pepsi Cola","brand":"PepsiCo","barcode":"5000112637922","categories":"Beverages, Sodas, Colas","ingredients_text":"Carbonated water, Sugar, Colour (Caramel E150d), Phosphoric acid, Flavourings (including caffeine)","labels":"","allergens":[],"image":"","nutriscore":"E","nutriments":{"energy":42,"fat":0,"sugars":11,"protein":0,"salt":0,"fiber":0}},
    "pepsi max":         {"name":"Pepsi Max / Zero","brand":"PepsiCo","barcode":"5000112547306","categories":"Beverages, Sodas","ingredients_text":"Carbonated water, Colour (Caramel E150d), Sweeteners (Aspartame, Acesulfame K), Phosphoric acid, Natural flavourings (including caffeine), Citric acid","labels":"","allergens":[],"image":"","nutriscore":"B","nutriments":{"energy":0,"fat":0,"sugars":0,"protein":0,"salt":0,"fiber":0}},
    "ben jerry":         {"name":"Ben & Jerry's Chocolate Fudge Brownie","brand":"Ben & Jerry's","barcode":"8714100735688","categories":"Ice creams, Frozen desserts","ingredients_text":"Cream, Skimmed milk, Sugar, Water, Egg yolk, Fudge brownies (Sugar, Wheat flour, Butter, Cocoa, Eggs, Salt, Vanilla extract), Cocoa, Vanilla extract, Guar gum, Carrageenan","labels":"Vegetarian","allergens":["eggs","gluten","milk"],"image":"","nutriscore":"E","nutriments":{"energy":282,"fat":14.7,"sugars":27,"protein":4.2,"salt":0.18,"fiber":1}},
    "impossible burger": {"name":"Impossible Burger Patties","brand":"Impossible Foods","barcode":"0085239026700","categories":"Plant-based meat","ingredients_text":"Water, Soy protein concentrate, Coconut oil, Sunflower oil, Natural flavors, Potato protein, Methylcellulose, Yeast extract, Soy leghemoglobin, Salt, Mixed tocopherols","labels":"Vegan","allergens":["soy"],"image":"","nutriscore":"C","nutriments":{"energy":240,"fat":14,"sugars":0,"protein":19,"salt":0.83,"fiber":0}},
    "beyond burger":     {"name":"Beyond Burger Plant-Based","brand":"Beyond Meat","barcode":"0842234000517","categories":"Plant-based meat","ingredients_text":"Water, Pea Protein Isolate, Expeller-Pressed Canola Oil, Refined Coconut Oil, Rice Protein, Natural Flavors, Cocoa Butter, Mung Bean Protein, Methylcellulose, Potato Starch, Apple Extract, Salt, Potassium Chloride, Vinegar","labels":"Vegan","allergens":[],"image":"","nutriscore":"C","nutriments":{"energy":270,"fat":20,"sugars":0,"protein":20,"salt":0.8,"fiber":0}},
    "whey protein":      {"name":"Gold Standard Whey Protein","brand":"Optimum Nutrition","barcode":"0041570050699","categories":"Sports nutrition, Protein powders","ingredients_text":"Whey protein isolate, Whey protein concentrate, Whey peptides, Cocoa powder, Lecithin, Natural and artificial flavors, Acesulfame potassium","labels":"","allergens":["milk","soy"],"image":"","nutriscore":"B","nutriments":{"energy":390,"fat":4.5,"sugars":4,"protein":77,"salt":0.5,"fiber":0}},
    "plant protein":     {"name":"Orgain Organic Plant Protein","brand":"Orgain","barcode":"0638102578283","categories":"Plant-based protein, Sports nutrition","ingredients_text":"Organic pea protein, Organic brown rice protein, Organic chia seeds, Organic hemp protein, Organic cane sugar, Organic cocoa powder, Sunflower lecithin","labels":"Vegan","allergens":[],"image":"","nutriscore":"B","nutriments":{"energy":380,"fat":6,"sugars":5,"protein":50,"salt":0.7,"fiber":0}},
    "maggi":             {"name":"Maggi 2-Minute Noodles","brand":"Nestlé","barcode":"8901058852336","categories":"Instant noodles","ingredients_text":"Wheat flour, Palm oil, Salt, Starch, Sugar, Dehydrated vegetables (Onion, Capsicum, Garlic), Spices, Yeast extract, Citric acid, E635","labels":"Vegetarian","allergens":["gluten"],"image":"","nutriscore":"D","nutriments":{"energy":405,"fat":16,"sugars":2.5,"protein":8.5,"salt":2.8,"fiber":2}},
    "cup noodles":       {"name":"Nissin Cup Noodles Chicken","brand":"Nissin","barcode":"0041196001105","categories":"Instant noodles","ingredients_text":"Enriched flour, Palm oil, Chicken, Salt, Sugar, Monosodium glutamate, Soy sauce, Chicken broth, Onion powder, Spices","labels":"","allergens":["gluten","soy"],"image":"","nutriscore":"D","nutriments":{"energy":370,"fat":14,"sugars":3,"protein":8,"salt":3,"fiber":0}},
    "pringles":          {"name":"Pringles Original","brand":"Pringles","barcode":"5053990109204","categories":"Snacks, Crisps","ingredients_text":"Dried potatoes, Vegetable oil (sunflower oil, corn oil), Wheat starch, Maltodextrin, Salt, Emulsifier (E471), Natural flavors","labels":"","allergens":["gluten"],"image":"","nutriscore":"D","nutriments":{"energy":536,"fat":33,"sugars":0.5,"protein":6.5,"salt":1.5,"fiber":4.8}},
    "lays":              {"name":"Lay's Classic Salted","brand":"Lay's","barcode":"8710398501578","categories":"Snacks, Crisps","ingredients_text":"Potatoes, Vegetable oil (sunflower oil, corn oil), Salt","labels":"Vegan","allergens":[],"image":"","nutriscore":"D","nutriments":{"energy":536,"fat":35,"sugars":0.3,"protein":6,"salt":1.5,"fiber":0}},
    "dark chocolate":    {"name":"Green & Black's Dark 70%","brand":"Green & Black's","barcode":"5011835103106","categories":"Dark chocolate","ingredients_text":"Cocoa mass (70%), Raw cane sugar, Cocoa butter, Vanilla extract, Emulsifier (soya lecithin)","labels":"Vegan","allergens":["soy"],"image":"","nutriscore":"C","nutriments":{"energy":530,"fat":38,"sugars":25,"protein":8,"salt":0.01,"fiber":10}},
    "red bull":          {"name":"Red Bull Energy Drink","brand":"Red Bull","barcode":"90162982","categories":"Energy drinks, Beverages","ingredients_text":"Carbonated water, Sucrose, Glucose, Citric acid, Taurine (0.4%), Sodium bicarbonate, Caffeine (0.03%), Niacinamide, Calcium pantothenate, Pyridoxine HCl, Vitamin B12, Natural and artificial flavors","labels":"","allergens":[],"image":"","nutriscore":"E","nutriments":{"energy":46,"fat":0,"sugars":11,"protein":0,"salt":0.1,"fiber":0}},
    "digestive":         {"name":"McVitie's Digestive Biscuits","brand":"McVitie's","barcode":"5000168201280","categories":"Biscuits","ingredients_text":"Wholemeal wheat flour, Sugar, Vegetable oil (palm, rapeseed), Partially inverted sugar syrup, Raising agents (sodium bicarbonate, malic acid), Salt","labels":"Vegan","allergens":["gluten","wheat"],"image":"","nutriscore":"D","nutriments":{"energy":481,"fat":20.9,"sugars":16.6,"protein":7.4,"salt":0.9,"fiber":3.5}},
    "snickers":          {"name":"Snickers Bar","brand":"Mars","barcode":"0034000008346","categories":"Candy, Chocolate bars","ingredients_text":"Milk Chocolate (Sugar, Cocoa Butter, Chocolate, Skim Milk, Lactose, Milkfat, Soy Lecithin, Artificial Flavor), Peanuts, Corn Syrup, Sugar, Palm Oil, Skim Milk, Butter, Milkfat, Salt, Egg Whites","labels":"","allergens":["eggs","milk","peanuts","soy"],"image":"","nutriscore":"E","nutriments":{"energy":488,"fat":24,"sugars":53,"protein":8,"salt":0.27,"fiber":0}},
    "twix":              {"name":"Twix Cookie Bar","brand":"Mars","barcode":"0034000008353","categories":"Candy, Cookie bars","ingredients_text":"Milk Chocolate (Sugar, Cocoa Butter, Chocolate, Skim Milk, Lactose, Milkfat, Soy Lecithin), Enriched Wheat Flour, Sugar, Palm Oil, Skim Milk, Corn Syrup, Butter, Salt, Cocoa Powder, Soy Lecithin","labels":"","allergens":["gluten","milk","soy","wheat"],"image":"","nutriscore":"E","nutriments":{"energy":497,"fat":24,"sugars":54,"protein":4.6,"salt":0.35,"fiber":0}},
    "ketchup":           {"name":"Heinz Tomato Ketchup","brand":"Heinz","barcode":"0013000006408","categories":"Sauces, Condiments","ingredients_text":"Tomato concentrate, Distilled vinegar, High fructose corn syrup, Corn syrup, Salt, Spice, Onion powder, Natural flavoring","labels":"Vegan","allergens":[],"image":"","nutriscore":"D","nutriments":{"energy":112,"fat":0,"sugars":24,"protein":1.4,"salt":1.6,"fiber":0}},
    "mayonnaise":        {"name":"Hellmann's Real Mayonnaise","brand":"Hellmann's","barcode":"0041390011480","categories":"Condiments, Mayonnaise","ingredients_text":"Soybean oil, Water, Whole eggs and egg yolks, Vinegar, Salt, Sugar, Lemon juice, Calcium disodium EDTA, Natural flavors","labels":"","allergens":["eggs","soy"],"image":"","nutriscore":"D","nutriments":{"energy":680,"fat":75,"sugars":1,"protein":1,"salt":1.2,"fiber":0}},
    "vegan mayo":        {"name":"Hellmann's Vegan Mayo","brand":"Hellmann's","barcode":"0016291301801","categories":"Vegan condiments, Mayonnaise","ingredients_text":"Water, Soybean oil, Modified starch, Sugar, White vinegar, Salt, Lemon juice concentrate, Paprika extract, Natural flavor","labels":"Vegan","allergens":["soy"],"image":"","nutriscore":"D","nutriments":{"energy":330,"fat":35,"sugars":2,"protein":0,"salt":1.3,"fiber":0}},
    "chobani":           {"name":"Chobani Complete Greek Yogurt","brand":"Chobani","barcode":"0818290017642","categories":"Dairy, Yogurt, Greek yogurt","ingredients_text":"Cultured nonfat milk, Milk protein concentrate, Cane sugar, Pectin, Live and active cultures: S. thermophilus, L. bulgaricus, L. acidophilus, Bifidus, L. casei","labels":"","allergens":["milk"],"image":"","nutriscore":"B","nutriments":{"energy":80,"fat":0,"sugars":7,"protein":15,"salt":0.08,"fiber":0}},
    "quaker oats":       {"name":"Quaker Oats Original Porridge","brand":"Quaker","barcode":"5010029016034","categories":"Breakfast cereals, Oats","ingredients_text":"Wholegrain rolled oats","labels":"Vegan","allergens":["gluten"],"image":"","nutriscore":"A","nutriments":{"energy":364,"fat":5.5,"sugars":1,"protein":11,"salt":0,"fiber":8}},
    "tropicana":         {"name":"Tropicana 100% Orange Juice","brand":"Tropicana","barcode":"0048500206867","categories":"Beverages, Fruit juices","ingredients_text":"100% pure squeezed pasteurized orange juice","labels":"Vegan","allergens":[],"image":"","nutriscore":"C","nutriments":{"energy":45,"fat":0.2,"sugars":9,"protein":0.7,"salt":0,"fiber":0}},
    "innocent smoothie": {"name":"Innocent Smoothie Strawberry Banana","brand":"Innocent","barcode":"5038862263887","categories":"Smoothies, Beverages","ingredients_text":"Crushed strawberries, Banana puree, Apple juice, Lemon juice","labels":"Vegan","allergens":[],"image":"","nutriscore":"C","nutriments":{"energy":55,"fat":0.3,"sugars":12,"protein":0.5,"salt":0,"fiber":1}},
    "larabar":           {"name":"Larabar Apple Pie Bar","brand":"Larabar","barcode":"0726635452900","categories":"Nutrition bars, Vegan snacks","ingredients_text":"Dates, Almonds, Unsweetened apples, Walnuts, Cinnamon","labels":"Vegan","allergens":["tree nuts"],"image":"","nutriscore":"C","nutriments":{"energy":350,"fat":11,"sugars":47,"protein":5,"salt":0,"fiber":4}},
    "kind bar":          {"name":"Kind Dark Chocolate Nuts & Sea Salt","brand":"KIND","barcode":"0722252008091","categories":"Nutrition bars, Snack bars","ingredients_text":"Almonds, Peanuts, Chicory root fiber, Honey, Palm kernel oil, Sugar, Rice flour, Vegetable glycerin, Crisp rice, Sea salt, Soy lecithin, Dark chocolate (cocoa mass, sugar, cocoa butter, vanilla extract), Cocoa powder","labels":"","allergens":["nuts","peanuts","soy"],"image":"","nutriscore":"C","nutriments":{"energy":430,"fat":32,"sugars":17,"protein":13,"salt":0.57,"fiber":6}},
}

# ── ALIAS MAP — all the alternate names a user might type ─────────────────────
ALIASES = {
    "coke":            "coca-cola",  "coca cola":       "coca-cola",
    "coco cola":       "coca-cola",  "cooca cola":      "coca-cola",
    "coke classic":    "coca-cola",  "cola":            "coca-cola",
    "coke zero":       "coke zero",  "coca-cola zero":  "coke zero",
    "zero coke":       "coke zero",  "diet coke":       "coke zero",
    "pepsi max":       "pepsi max",  "pepsi zero":      "pepsi max",
    "pepsi cola":      "pepsi",      "pepsi original":  "pepsi",
    "oat milk":        "alpro oat",  "oatly":           "alpro oat",
    "silk oatmilk":    "silk oat",   "silk oat milk":   "silk oat",
    "soy milk":        "alpro soy",  "silk soymilk":    "silk soy",
    "soymilk":         "silk soy",   "soya milk":       "alpro soy",
    "almond breeze":   "almond milk","blue diamond":    "almond milk",
    "nutella hazelnut":"nutella",     "ferrero nutella": "nutella",
    "oreo cookies":    "oreo",       "oreo biscuit":    "oreo",
    "kit kat":         "kit kat",    "kitkat":          "kit kat",
    "ben jerrys":      "ben jerry",  "ben and jerrys":  "ben jerry",
    "ben & jerrys":    "ben jerry",  "ice cream":       "ben jerry",
    "impossible":      "impossible burger","beyond meat":"beyond burger",
    "beyond":          "beyond burger","plant burger":  "beyond burger",
    "whey":            "whey protein","protein powder":  "whey protein",
    "plant protein":   "plant protein","orgain":        "plant protein",
    "dark choc":       "dark chocolate","70% chocolate": "dark chocolate",
    "green blacks":    "dark chocolate",
    "pringles chips":  "pringles",   "chips":           "pringles",
    "lays chips":      "lays",       "lays crisps":     "lays",
    "digestive biscuit":"digestive", "mcvities":        "digestive",
    "snickers bar":    "snickers",   "mars snickers":   "snickers",
    "twix bar":        "twix",       "twix chocolate":  "twix",
    "heinz ketchup":   "ketchup",    "tomato ketchup":  "ketchup",
    "mayo":            "mayonnaise", "hellmanns":        "mayonnaise",
    "vegan mayo":      "vegan mayo", "hellmanns vegan":  "vegan mayo",
    "red bull energy": "red bull",   "energy drink":    "red bull",
    "chobani yogurt":  "chobani",    "greek yogurt":    "chobani",
    "oats":            "quaker oats","porridge":        "quaker oats",
    "tropicana oj":    "tropicana",  "orange juice":    "tropicana",
    "innocent":        "innocent smoothie","smoothie":  "innocent smoothie",
    "cup noodles":     "cup noodles","nissin":          "cup noodles",
    "maggi noodles":   "maggi",      "instant noodles": "maggi",
    "larabar bar":     "larabar",    "lara bar":        "larabar",
    "kind bar nuts":   "kind bar",   "kind chocolate":  "kind bar",
}


def levenshtein(a: str, b: str) -> int:
    """Simple Levenshtein distance for fuzzy matching."""
    if len(a) < len(b): return levenshtein(b, a)
    if not b: return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            curr.append(min(prev[j + 1] + 1, curr[j] + 1,
                            prev[j] + (0 if ca == cb else 1)))
        prev = curr
    return prev[-1]


def fuzzy_search(query: str, top_k: int = 6) -> tuple[list, list]:
    """
    Returns (exact_results, suggestions).
    exact_results: products that match confidently.
    suggestions: top-3 "Did you mean?" alternatives if no exact match.
    """
    q = query.lower().strip()

    # 0. Resolve alias first
    if q in ALIASES:
        q = ALIASES[q]

    # Check aliases — longest match wins (sort desc to prevent "coke" stealing "coke zero")
    q_resolved = q
    best_alias_len = 0
    for alias, canonical in ALIASES.items():
        # Exact match gets highest priority
        if q == alias:
            q_resolved = canonical
            best_alias_len = 9999
            break
        # Alias is substring of query AND longer than previous match
        if alias in q and len(alias) > best_alias_len:
            q_resolved = canonical
            best_alias_len = len(alias)

    results = []
    scored  = []

    for key, prod in LOCAL_PRODUCTS.items():
        name_l  = prod["name"].lower()
        brand_l = prod["brand"].lower()
        cats_l  = prod.get("categories", "").lower()
        key_l   = key.lower()

        # Exact / contains match → high confidence result
        exact = (
            q_resolved == key_l or
            q_resolved == name_l or
            q_resolved in name_l or
            q_resolved in brand_l or
            name_l.startswith(q_resolved) or
            brand_l.startswith(q_resolved) or
            q_resolved in cats_l
        )

        # Token match: all query words found somewhere in name/brand
        tokens = [t for t in q_resolved.split() if len(t) > 1]
        token_hits = sum(1 for t in tokens if t in name_l or t in brand_l or t in key_l)
        token_match = len(tokens) > 0 and token_hits == len(tokens)

        # Partial token match (at least half the tokens match)
        partial_match = len(tokens) > 0 and token_hits >= max(1, len(tokens) // 2)

        if exact or token_match:
            results.append(prod)
        elif partial_match:
            # Still score for "did you mean?"
            dist = levenshtein(q_resolved, name_l[:len(q_resolved)+3])
            scored.append((dist, prod))
        else:
            # Levenshtein on short queries
            if len(q_resolved) >= 3:
                dist = levenshtein(q_resolved, key_l)
                if dist <= max(3, len(q_resolved) // 3):
                    scored.append((dist, prod))
                else:
                    # Try against each word in the name
                    for word in name_l.split():
                        if len(word) >= 3:
                            d = levenshtein(q_resolved, word)
                            if d <= 2:
                                scored.append((d + 1, prod))
                                break

    scored.sort(key=lambda x: x[0])
    suggestions = []
    seen = {id(p) for p in results}
    for _, p in scored:
        if id(p) not in seen and len(suggestions) < 3:
            suggestions.append(p)
            seen.add(id(p))

    # Deduplicate results
    seen2: set = set()
    deduped = []
    for p in results:
        pid = id(p)
        if pid not in seen2:
            seen2.add(pid)
            deduped.append(p)

    return deduped[:top_k], suggestions


# ── Page header ───────────────────────────────────────────────────────────────
render_page_header("🔍", "Product Analyzer",
    "Search 3M+ products from Open Food Facts — instant vegan &amp; health analysis")

# ── Show analysis result first if one exists ──────────────────────────────────
if "ar" in st.session_state and "ap" in st.session_state:
    result = st.session_state["ar"]
    prod   = st.session_state["ap"]
    st.markdown(f"## 📋 Analysis: {prod['name']}")
    st.caption(f"Brand: {prod.get('brand','—')}  ·  Barcode: {prod.get('barcode','—')}")
    full_analysis_display(result, prod, key_suffix="analyzer_main")
    if st.button("✕ Clear & search again", key="clear_result"):
        del st.session_state["ar"], st.session_state["ap"]
        st.session_state.pop("analyzer_products", None)
        st.session_state.pop("analyzer_suggestions", None)
        st.rerun()
    st.stop()

# ── Search bar ────────────────────────────────────────────────────────────────
cq, cb = st.columns([5, 1])
with cq:
    query = st.text_input(
        "Search",
        placeholder="e.g. coco cola, coke zero, nutella, silk oat milk, impossible burger…",
        label_visibility="collapsed", key="analyzer_q",
    )
with cb:
    go = st.button("🔍 Search", type="primary", use_container_width=True, key="analyzer_go")

# ── Popular quick-search buttons ──────────────────────────────────────────────
popular = [
    ("🍫 Nutella","nutella"),   ("🍪 Oreo","oreo"),
    ("🥤 Coca-Cola","coca-cola"),("🥤 Coke Zero","coke zero"),
    ("🌾 Alpro Oat","alpro oat"),("🌿 Impossible","impossible burger"),
    ("🥛 Whey","whey protein"), ("🍦 Ben & Jerry's","ben jerry"),
]
st.markdown(
    f'<div style="font-size:0.65rem;font-weight:700;letter-spacing:0.1em;'
    f'text-transform:uppercase;color:{SAGE["stone"]};margin:10px 0 6px">'
    f'Popular searches</div>', unsafe_allow_html=True,
)
pcols = st.columns(4)
for i, (lbl, val) in enumerate(popular):
    with pcols[i % 4]:
        if st.button(lbl, key=f"pop_{i}", use_container_width=True):
            st.session_state["analyzer_pending_query"] = val
            st.rerun()

# Pick up query set by popular buttons
if "analyzer_pending_query" in st.session_state:
    query = st.session_state.pop("analyzer_pending_query")
    go = True

# ── Run search ────────────────────────────────────────────────────────────────
if go and query:
    # 1. Try Open Food Facts API first
    with st.spinner(f"🔍 Searching for '{query}'…"):
        api_products = prod_svc.search_by_name(query)

    if api_products:
        st.session_state["analyzer_products"]    = api_products
        st.session_state["analyzer_suggestions"] = []
        st.session_state["analyzer_query"]       = query
    else:
        # 2. Fuzzy local search
        results, suggestions = fuzzy_search(query)
        st.session_state["analyzer_products"]    = results
        st.session_state["analyzer_suggestions"] = suggestions
        st.session_state["analyzer_query"]       = query

# ── Handle "Did you mean?" button clicks ─────────────────────────────────────
if "analyzer_suggest_pick" in st.session_state:
    pick = st.session_state.pop("analyzer_suggest_pick")
    results, suggestions = fuzzy_search(pick)
    st.session_state["analyzer_products"]    = results
    st.session_state["analyzer_suggestions"] = suggestions
    st.session_state["analyzer_query"]       = pick

# ── Display results ───────────────────────────────────────────────────────────
if "analyzer_products" in st.session_state:
    products    = st.session_state["analyzer_products"]
    suggestions = st.session_state.get("analyzer_suggestions", [])
    last_q      = st.session_state.get("analyzer_query", "")

    if not products:
        # Total miss — show "Did you mean?" or generic tip
        if suggestions:
            st.warning(f"❓ No exact results for **'{last_q}'**. Did you mean one of these?")
            sc = st.columns(len(suggestions))
            for i, s in enumerate(suggestions):
                with sc[i]:
                    st.markdown(
                        f'<div style="background:{SAGE["offwhite"]};border:1px solid {SAGE["pale"]};'
                        f'border-radius:10px;padding:10px;text-align:center;margin-bottom:4px">'
                        f'<div style="font-weight:700;font-size:0.9rem;color:{SAGE["charcoal"]}">{s["name"]}</div>'
                        f'<div style="font-size:0.72rem;color:{SAGE["stone"]}">{s["brand"]}</div></div>',
                        unsafe_allow_html=True,
                    )
                    if st.button(f'Search "{s["name"]}"', key=f"suggest_btn_{i}",
                                 use_container_width=True):
                        st.session_state["analyzer_suggest_pick"] = s["name"].lower()
                        st.rerun()
        else:
            st.error(
                f"❌ **'{last_q}'** not found.\n\n"
                "**Try:** Nutella · Oreo · Coca-Cola · Coke Zero · Alpro Oat · "
                "Impossible Burger · Whey Protein · Pringles · Pepsi · Kit Kat"
            )
    else:
        st.success(f"✅ Found **{len(products)}** result(s) for **'{last_q}'**")

        # Show "Did you mean?" alongside if we have suggestions too
        if suggestions and len(products) < 3:
            st.markdown(
                f'<div style="font-size:0.78rem;color:{SAGE["stone"]};margin:2px 0 8px">'
                f'🔎 Also consider: '
                + " · ".join(
                    f'<b>{s["name"]}</b>' for s in suggestions
                )
                + "</div>",
                unsafe_allow_html=True,
            )
            sug_cols = st.columns(len(suggestions))
            for i, s in enumerate(suggestions):
                with sug_cols[i]:
                    if st.button(f'Try "{s["name"]}"', key=f"sug_extra_{i}",
                                 use_container_width=True):
                        st.session_state["analyzer_suggest_pick"] = s["name"].lower()
                        st.rerun()

        st.markdown("")
        for idx, prod in enumerate(products[:6]):
            with st.container():
                pa, pb = st.columns([1, 6])
                with pa:
                    if prod.get("image"):
                        st.image(prod["image"], use_container_width=True)
                    else:
                        name_l = prod["name"].lower()
                        emoji = ("🍫" if any(x in name_l for x in ["nutella","chocolate","kit kat","twix","snickers"]) else
                                 "🍪" if any(x in name_l for x in ["oreo","biscuit","cookie","digestive"]) else
                                 "🌾" if any(x in name_l for x in ["oat","almond","silk","alpro","soy milk"]) else
                                 "🌿" if any(x in name_l for x in ["impossible","beyond","plant burger"]) else
                                 "🥛" if any(x in name_l for x in ["whey","protein","orgain"]) else
                                 "🍦" if any(x in name_l for x in ["jerry","ice cream"]) else
                                 "🥤" if any(x in name_l for x in ["cola","pepsi","bull","coke"]) else
                                 "🍟" if any(x in name_l for x in ["pringles","lays","crisp","chip"]) else
                                 "🥫")
                        st.markdown(
                            f'<div style="font-size:2.8rem;text-align:center;padding:8px">{emoji}</div>',
                            unsafe_allow_html=True,
                        )
                with pb:
                    st.markdown(f"**{prod['name']}**")
                    st.caption(f"Brand: {prod.get('brand','—')}  ·  Barcode: {prod.get('barcode','—')}")
                    cats = prod.get("categories","")[:70]
                    if cats:
                        st.caption(f"Category: {cats}")
                    ing = prod.get("ingredients_text","")
                    if ing:
                        preview = ing[:150] + "…" if len(ing) > 150 else ing
                        st.markdown(
                            f'<div style="font-size:0.78rem;color:{SAGE["stone"]};'
                            f'background:{SAGE["offwhite"]};border-radius:8px;padding:6px 10px;margin:4px 0">'
                            f'<b>Ingredients:</b> {preview}</div>',
                            unsafe_allow_html=True,
                        )
                    if st.button(f"🧬 Analyze {prod['name']}", key=f"analyze_btn_{idx}",
                                 type="primary"):
                        with st.spinner(f"🤖 Analyzing {prod['name']}…"):
                            result = cached_analyze(svc, prod.get("ingredients_text",""), prod["name"],
                                                     barcode=prod.get("barcode"))
                        st.session_state["ar"] = result
                        st.session_state["ap"] = prod
                        add_history(prod["name"], result.overall_vegan,
                                    prod.get("ingredients_text",""), result, barcode=prod.get("barcode"))
                        log_activity("Product Search", "Analyzer")
                        st.rerun()
            st.divider()
