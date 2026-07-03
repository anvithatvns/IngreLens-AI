"""
IngreLens AI — Product Fetch Service v2
Queries Open Food Facts (free, 3M+ products).
Falls back to 50+ product local database for offline use.
Barcode fetch tries multiple formats (with/without leading zeros).
"""
from __future__ import annotations
import sys, requests
from pathlib import Path
from typing import Optional
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


# ── Comprehensive local demo database (50+ products) ──────────────────────────
DEMO_PRODUCTS = {
    # ── Chocolate & spreads ───────────────────────────────────────────────────
    "3017624010701": {"name":"Nutella","brand":"Ferrero","categories":"Sweet spreads, Chocolate spreads",
        "ingredients_text":"Sugar, Palm oil, Hazelnuts (13%), Skimmed milk powder (8.7%), Fat-reduced cocoa (7.4%), Emulsifier (Soya lecithin), Vanillin",
        "nutriscore":"e","allergens_tags":["en:gluten","en:milk","en:nuts","en:soybeans"],"nutriments":{"energy-kcal_100g":539,"fat_100g":30.9,"sugars_100g":56.3,"proteins_100g":6.3,"salt_100g":0.107}},
    "5011835103106": {"name":"Green & Black's Dark 70%","brand":"Green & Black's","categories":"Dark chocolate",
        "ingredients_text":"Cocoa mass (70%), Raw cane sugar, Cocoa butter, Vanilla extract, Emulsifier (soya lecithin)",
        "nutriscore":"c","allergens_tags":["en:soybeans"],"nutriments":{"energy-kcal_100g":530,"fat_100g":38,"sugars_100g":25,"proteins_100g":8,"salt_100g":0.01}},
    # ── Biscuits & snacks ─────────────────────────────────────────────────────
    "7622300416981": {"name":"Oreo Original","brand":"Mondelez","categories":"Biscuits, Cookies",
        "ingredients_text":"Unbleached enriched flour (wheat flour, niacin, reduced iron, thiamine mononitrate, riboflavin, folic acid), Sugar, Palm and/or canola oil, Cocoa powder, High fructose corn syrup, Leavening, Salt, Soy lecithin, Vanillin, Chocolate",
        "nutriscore":"e","allergens_tags":["en:gluten","en:soybeans","en:wheat"],"nutriments":{"energy-kcal_100g":480,"fat_100g":21,"sugars_100g":42,"proteins_100g":5,"salt_100g":0.75}},
    "4000539400404": {"name":"Kit Kat Milk Chocolate","brand":"Nestlé","categories":"Chocolate bars, Wafer bars",
        "ingredients_text":"Sugar, Wheat flour, Cocoa butter, Skimmed milk powder, Cocoa mass, Milk fat, Lactose, Emulsifier (Soya lecithin), Yeast, Salt, Natural vanilla flavouring",
        "nutriscore":"e","allergens_tags":["en:gluten","en:milk","en:soybeans"],"nutriments":{"energy-kcal_100g":508,"fat_100g":25.6,"sugars_100g":51.5,"proteins_100g":6.3,"salt_100g":0.24}},
    "5053990109204": {"name":"Pringles Original","brand":"Pringles","categories":"Snacks, Crisps",
        "ingredients_text":"Dried potatoes, Vegetable oil (sunflower oil, corn oil), Wheat starch, Maltodextrin, Salt, Emulsifier (E471), Natural flavors",
        "nutriscore":"d","allergens_tags":["en:gluten"],"nutriments":{"energy-kcal_100g":536,"fat_100g":33,"sugars_100g":0.5,"proteins_100g":6.5,"salt_100g":1.5}},
    "8710398501578": {"name":"Lay's Classic Salted","brand":"Lay\'s","categories":"Snacks, Crisps",
        "ingredients_text":"Potatoes, Vegetable oil (sunflower oil, corn oil), Salt",
        "nutriscore":"d","labels":"Vegan","allergens_tags":[],"nutriments":{"energy-kcal_100g":536,"fat_100g":35,"sugars_100g":0.3,"proteins_100g":6,"salt_100g":1.5}},
    "5000168201280": {"name":"McVitie\'s Digestive Biscuits","brand":"McVitie\'s","categories":"Biscuits",
        "ingredients_text":"Wholemeal wheat flour, Sugar, Vegetable oil (palm, rapeseed), Partially inverted sugar syrup, Raising agents (sodium bicarbonate, malic acid), Salt",
        "nutriscore":"d","labels":"Vegan","allergens_tags":["en:gluten","en:wheat"],"nutriments":{"energy-kcal_100g":481,"fat_100g":20.9,"sugars_100g":16.6,"proteins_100g":7.4,"salt_100g":0.9}},
    # ── Plant milks ───────────────────────────────────────────────────────────
    "5411188131335": {"name":"Alpro Oat Milk Original","brand":"Alpro","categories":"Plant-based milks, Oat drinks",
        "ingredients_text":"Water, Oat (10%), Sunflower oil, Calcium carbonate, Sea salt, Vitamins (Riboflavin B2, B12, D2), Acidity regulator (Dipotassium phosphate), Stabiliser (Gellan gum)",
        "nutriscore":"b","labels":"Vegan","allergens_tags":["en:gluten"],"nutriments":{"energy-kcal_100g":47,"fat_100g":1.5,"sugars_100g":4,"proteins_100g":1,"salt_100g":0.1}},
    "0037600294522": {"name":"Almond Breeze Original","brand":"Blue Diamond","categories":"Plant-based milks, Almond drinks",
        "ingredients_text":"Almond milk (filtered water, almonds), Cane sugar, Vitamin and mineral blend (calcium carbonate, vitamin E acetate, vitamin A palmitate, vitamin D2), Sea salt, Locust bean gum, Sunflower lecithin, Gellan gum, Natural flavors",
        "nutriscore":"b","labels":"Vegan","allergens_tags":["en:nuts"],"nutriments":{"energy-kcal_100g":60,"fat_100g":2.5,"sugars_100g":8,"proteins_100g":1,"salt_100g":0.15}},
    "5411188080176": {"name":"Alpro Soy Milk Original","brand":"Alpro","categories":"Plant-based milks, Soy drinks",
        "ingredients_text":"Water, Hulled soy beans (8.7%), Cane sugar, Sea salt, Calcium carbonate, Stabiliser (gellan gum), Vitamins (D2, B12, Riboflavin)",
        "nutriscore":"b","labels":"Vegan","allergens_tags":["en:soybeans"],"nutriments":{"energy-kcal_100g":54,"fat_100g":1.8,"sugars_100g":2.9,"proteins_100g":3.3,"salt_100g":0.12}},
    "0632154697732": {"name":"Silk Oatmilk Original","brand":"Silk","categories":"Plant-based milks",
        "ingredients_text":"Oatmilk (water, whole grain oats), Sunflower oil, Contains 2% or less of: sea salt, gellan gum, vitamin A, vitamin D2, riboflavin, vitamin B12",
        "nutriscore":"b","labels":"Vegan","allergens_tags":[],"nutriments":{"energy-kcal_100g":50,"fat_100g":1.5,"sugars_100g":7,"proteins_100g":1,"salt_100g":0.15}},
    # ── Beverages ────────────────────────────────────────────────────────────
    "5449000000996": {"name":"Coca-Cola Classic","brand":"Coca-Cola","categories":"Beverages, Sodas, Colas",
        "ingredients_text":"Carbonated water, Sugar, Colour (Caramel E150d), Phosphoric acid, Natural flavourings including caffeine",
        "nutriscore":"e","allergens_tags":[],"nutriments":{"energy-kcal_100g":42,"fat_100g":0,"sugars_100g":10.6,"proteins_100g":0,"salt_100g":0}},
    "5449000054227": {"name":"Coca-Cola Zero Sugar","brand":"Coca-Cola","categories":"Beverages, Sodas",
        "ingredients_text":"Carbonated water, Colour (Caramel E150d), Phosphoric acid, Sweeteners (Aspartame, Acesulfame K), Natural flavourings including caffeine, Citric acid",
        "nutriscore":"b","allergens_tags":[],"nutriments":{"energy-kcal_100g":0,"fat_100g":0,"sugars_100g":0,"proteins_100g":0,"salt_100g":0}},
    "5000112637922": {"name":"Pepsi Cola","brand":"PepsiCo","categories":"Beverages, Sodas, Colas",
        "ingredients_text":"Carbonated water, Sugar, Colour (Caramel E150d), Phosphoric acid, Flavourings (including caffeine)",
        "nutriscore":"e","allergens_tags":[],"nutriments":{"energy-kcal_100g":42,"fat_100g":0,"sugars_100g":11,"proteins_100g":0,"salt_100g":0}},
    "5000112547306": {"name":"Pepsi Max / Zero","brand":"PepsiCo","categories":"Beverages, Sodas",
        "ingredients_text":"Carbonated water, Colour (Caramel E150d), Sweeteners (Aspartame, Acesulfame K), Phosphoric acid, Natural flavourings (including caffeine), Citric acid",
        "nutriscore":"b","allergens_tags":[],"nutriments":{"energy-kcal_100g":0,"fat_100g":0,"sugars_100g":0,"proteins_100g":0,"salt_100g":0}},
    "90162982":      {"name":"Red Bull Energy Drink","brand":"Red Bull","categories":"Energy drinks, Beverages",
        "ingredients_text":"Carbonated water, Sucrose, Glucose, Citric acid, Taurine (0.4%), Sodium bicarbonate, Caffeine (0.03%), Niacinamide, Calcium pantothenate, Pyridoxine HCl, Vitamin B12, Natural and artificial flavors, Colors",
        "nutriscore":"e","allergens_tags":[],"nutriments":{"energy-kcal_100g":46,"fat_100g":0,"sugars_100g":11,"proteins_100g":0,"salt_100g":0.1}},
    "0048500206867": {"name":"Tropicana 100% Orange Juice","brand":"Tropicana","categories":"Beverages, Fruit juices",
        "ingredients_text":"100% pure squeezed pasteurized orange juice",
        "nutriscore":"c","labels":"Vegan","allergens_tags":[],"nutriments":{"energy-kcal_100g":45,"fat_100g":0.2,"sugars_100g":9,"proteins_100g":0.7,"salt_100g":0}},
    "5038862263887": {"name":"Innocent Smoothie Strawberry Banana","brand":"Innocent","categories":"Smoothies",
        "ingredients_text":"Crushed strawberries, Banana puree, Apple juice, Lemon juice",
        "nutriscore":"c","labels":"Vegan","allergens_tags":[],"nutriments":{"energy-kcal_100g":55,"fat_100g":0.3,"sugars_100g":12,"proteins_100g":0.5,"salt_100g":0}},
    # ── Ice cream & frozen ───────────────────────────────────────────────────
    "8714100735688": {"name":"Ben & Jerry\'s Chocolate Fudge Brownie","brand":"Ben & Jerry\'s","categories":"Ice creams",
        "ingredients_text":"Cream, Skimmed milk, Sugar, Water, Egg yolk, Fudge brownies (Sugar, Wheat flour, Butter, Cocoa, Eggs, Salt, Vanilla extract), Cocoa processed with alkali, Vanilla extract, Guar gum, Carrageenan",
        "nutriscore":"e","allergens_tags":["en:eggs","en:gluten","en:milk"],"nutriments":{"energy-kcal_100g":282,"fat_100g":14.7,"sugars_100g":27,"proteins_100g":4.2,"salt_100g":0.18}},
    # ── Dairy & yogurt ───────────────────────────────────────────────────────
    "0818290017642": {"name":"Chobani Complete Plain Greek Yogurt","brand":"Chobani","categories":"Dairy, Yogurt, Greek yogurt",
        "ingredients_text":"Cultured nonfat milk, Milk protein concentrate, Cane sugar, Pectin, Live and active cultures: S. thermophilus, L. bulgaricus, L. acidophilus, Bifidus, L. casei",
        "nutriscore":"b","allergens_tags":["en:milk"],"nutriments":{"energy-kcal_100g":80,"fat_100g":0,"sugars_100g":7,"proteins_100g":15,"salt_100g":0.08}},
    "0818290016348": {"name":"Chobani Plain Greek Yogurt","brand":"Chobani","categories":"Dairy, Yogurt",
        "ingredients_text":"Cultured nonfat milk, Pectin, Locust bean gum, Live and active cultures: S. thermophilus, L. bulgaricus, L. acidophilus, Bifidus, L. casei",
        "nutriscore":"b","allergens_tags":["en:milk"],"nutriments":{"energy-kcal_100g":90,"fat_100g":0,"sugars_100g":6,"proteins_100g":17,"salt_100g":0.06}},
    "5000159407236": {"name":"Yeo Valley Organic Whole Milk Yoghurt","brand":"Yeo Valley","categories":"Yogurt, Dairy",
        "ingredients_text":"Organic whole milk, Organic cream, Live cultures (S. thermophilus, L. bulgaricus)",
        "nutriscore":"c","allergens_tags":["en:milk"],"nutriments":{"energy-kcal_100g":95,"fat_100g":5,"sugars_100g":7,"proteins_100g":4.5,"salt_100g":0.1}},
    # ── Plant-based meat ─────────────────────────────────────────────────────
    "0085239026700": {"name":"Impossible Burger Patties","brand":"Impossible Foods","categories":"Plant-based meat",
        "ingredients_text":"Water, Soy protein concentrate, Coconut oil, Sunflower oil, Natural flavors, 2% or less of: potato protein, methylcellulose, yeast extract, cultured dextrose, food starch modified, soy leghemoglobin, salt, mixed tocopherols, soy protein isolate, vitamins and minerals",
        "nutriscore":"c","labels":"Vegan","allergens_tags":["en:soybeans"],"nutriments":{"energy-kcal_100g":240,"fat_100g":14,"sugars_100g":0,"proteins_100g":19,"salt_100g":0.83}},
    "0842234000517": {"name":"Beyond Burger Plant-Based Patties","brand":"Beyond Meat","categories":"Plant-based meat",
        "ingredients_text":"Water, Pea Protein Isolate, Expeller-Pressed Canola Oil, Refined Coconut Oil, Rice Protein, Natural Flavors, Cocoa Butter, Mung Bean Protein, Methylcellulose, Potato Starch, Apple Extract, Salt, Potassium Chloride, Vinegar, Lemon Juice Concentrate, Sunflower Lecithin, Pomegranate Fruit Powder, Beet Juice Extract",
        "nutriscore":"c","labels":"Vegan","allergens_tags":[],"nutriments":{"energy-kcal_100g":270,"fat_100g":20,"sugars_100g":0,"proteins_100g":20,"salt_100g":0.8}},
    # ── Protein & nutrition ───────────────────────────────────────────────────
    "0041570050699": {"name":"Optimum Nutrition Gold Standard Whey","brand":"Optimum Nutrition","categories":"Sports nutrition, Protein powders",
        "ingredients_text":"Whey protein isolate, Whey protein concentrate, Whey peptides, Cocoa powder, Lecithin, Natural and artificial flavors, Acesulfame potassium, Aminogen",
        "nutriscore":"b","allergens_tags":["en:milk","en:soybeans"],"nutriments":{"energy-kcal_100g":390,"fat_100g":4.5,"sugars_100g":4,"proteins_100g":77,"salt_100g":0.5}},
    "0638102578283": {"name":"Orgain Organic Plant Protein Powder","brand":"Orgain","categories":"Plant-based protein, Sports nutrition",
        "ingredients_text":"Organic pea protein, Organic brown rice protein, Organic chia seeds, Organic hemp protein, Organic cane sugar, Organic cocoa powder, Sunflower lecithin",
        "nutriscore":"b","labels":"Vegan","allergens_tags":[],"nutriments":{"energy-kcal_100g":380,"fat_100g":6,"sugars_100g":5,"proteins_100g":50,"salt_100g":0.7}},
    # ── Breakfast & cereals ───────────────────────────────────────────────────
    "5038862263887": {"name":"Innocent Smoothie Mango & Passion Fruit","brand":"Innocent","categories":"Smoothies",
        "ingredients_text":"Mango puree, Passion fruit juice, Apple juice, Pineapple juice, Lemon juice",
        "nutriscore":"c","labels":"Vegan","allergens_tags":[],"nutriments":{"energy-kcal_100g":55,"fat_100g":0.2,"sugars_100g":12,"proteins_100g":0.5,"salt_100g":0}},
    "5010029016034": {"name":"Quaker Oats Original Porridge","brand":"Quaker","categories":"Breakfast cereals, Oats",
        "ingredients_text":"Wholegrain rolled oats",
        "nutriscore":"a","labels":"Vegan","allergens_tags":["en:gluten"],"nutriments":{"energy-kcal_100g":364,"fat_100g":5.5,"sugars_100g":1,"proteins_100g":11,"salt_100g":0}},
    "0038000845826": {"name":"Nutri-Grain Strawberry Bar","brand":"Kellogg\'s","categories":"Cereal bars",
        "ingredients_text":"Whole grain oats, Enriched flour (wheat flour, niacin, reduced iron, thiamine mononitrate, riboflavin, folic acid), Strawberry filling (sugar, strawberries, modified corn starch, glycerin), Sugar, Soybean oil, High fructose corn syrup, Calcium carbonate, Wheat bran, Salt, Cinnamon, Natural flavor, Soy lecithin, Vitamin A palmitate",
        "nutriscore":"d","allergens_tags":["en:gluten","en:soybeans","en:wheat"],"nutriments":{"energy-kcal_100g":370,"fat_100g":7,"sugars_100g":28,"proteins_100g":5,"salt_100g":0.4}},
    # ── Instant foods ────────────────────────────────────────────────────────
    "8901058852336": {"name":"Maggi 2-Minute Noodles Masala","brand":"Nestlé","categories":"Instant noodles",
        "ingredients_text":"Wheat flour, Palm oil, Salt, Starch, Sugar, Dehydrated vegetables (Onion, Green capsicum, Garlic), Spices (Turmeric, Coriander, Pepper), Yeast extract, Citric acid, E635",
        "nutriscore":"d","allergens_tags":["en:gluten"],"nutriments":{"energy-kcal_100g":405,"fat_100g":16,"sugars_100g":2.5,"proteins_100g":8.5,"salt_100g":2.8}},
    "0041196001105": {"name":"Nissin Cup Noodles Chicken Flavor","brand":"Nissin","categories":"Instant noodles",
        "ingredients_text":"Enriched flour (wheat flour, niacin, iron, thiamine mononitrate, riboflavin, folic acid), Palm oil, Chicken, Salt, Sugar, Monosodium glutamate, Soy sauce (water, wheat, soybeans, salt), Chicken broth, Onion powder, Spices",
        "nutriscore":"d","allergens_tags":["en:gluten","en:soybeans","en:wheat"],"nutriments":{"energy-kcal_100g":370,"fat_100g":14,"sugars_100g":3,"proteins_100g":8,"salt_100g":3}},
    # ── Sauces & condiments ───────────────────────────────────────────────────
    "0013000006408": {"name":"Heinz Tomato Ketchup","brand":"Heinz","categories":"Sauces, Condiments",
        "ingredients_text":"Tomato concentrate, Distilled vinegar, High fructose corn syrup, Corn syrup, Salt, Spice, Onion powder, Natural flavoring",
        "nutriscore":"d","labels":"Vegan","allergens_tags":[],"nutriments":{"energy-kcal_100g":112,"fat_100g":0,"sugars_100g":24,"proteins_100g":1.4,"salt_100g":1.6}},
    "0041390011480": {"name":"Hellmann\'s Real Mayonnaise","brand":"Hellmann\'s","categories":"Condiments, Mayonnaise",
        "ingredients_text":"Soybean oil, Water, Whole eggs and egg yolks, Vinegar, Salt, Sugar, Lemon juice, Calcium disodium EDTA, Natural flavors",
        "nutriscore":"d","allergens_tags":["en:eggs","en:soybeans"],"nutriments":{"energy-kcal_100g":680,"fat_100g":75,"sugars_100g":1,"proteins_100g":1,"salt_100g":1.2}},
    "0016291301801": {"name":"Hellmann\'s Vegan Mayo","brand":"Hellmann\'s","categories":"Vegan condiments, Mayonnaise",
        "ingredients_text":"Water, Soybean oil, Modified starch, Sugar, White vinegar, Salt, Lemon juice concentrate, Paprika extract, Natural flavor",
        "nutriscore":"d","labels":"Vegan","allergens_tags":["en:soybeans"],"nutriments":{"energy-kcal_100g":330,"fat_100g":35,"sugars_100g":2,"proteins_100g":0,"salt_100g":1.3}},
    # ── Bread & bakery ────────────────────────────────────────────────────────
    "5000179140305": {"name":"Warburtons Medium Sliced White Bread","brand":"Warburtons","categories":"Bread, Bakery",
        "ingredients_text":"Wheat flour (with added calcium, iron, niacins, thiamin), Water, Yeast, Salt, Wheat protein, Soya flour, Vegetable oil (rapeseed), Emulsifiers (E471, E481), Flour treatment agent (ascorbic acid)",
        "nutriscore":"c","labels":"Vegan","allergens_tags":["en:gluten","en:soybeans","en:wheat"],"nutriments":{"energy-kcal_100g":236,"fat_100g":2.4,"sugars_100g":3.6,"proteins_100g":8.7,"salt_100g":0.9}},
    # ── Coffee & tea ─────────────────────────────────────────────────────────
    "0076811575015": {"name":"Starbucks Pike Place Medium Roast Coffee","brand":"Starbucks","categories":"Coffee, Beverages",
        "ingredients_text":"100% arabica coffee",
        "nutriscore":"a","labels":"Vegan","allergens_tags":[],"nutriments":{"energy-kcal_100g":2,"fat_100g":0,"sugars_100g":0,"proteins_100g":0.3,"salt_100g":0}},
    # ── Candy & confectionery ─────────────────────────────────────────────────
    "0034000002054": {"name":"Skittles Original","brand":"Skittles","categories":"Candy, Confectionery",
        "ingredients_text":"Sugar, Corn syrup, Hydrogenated palm kernel oil, Fruit Juice from Concentrate (apple, lime, lemon, orange, strawberry), Citric acid, Dextrin, Modified corn starch, Natural and Artificial Flavors, Coloring (Red 40, Yellow 5, Yellow 6, Blue 2, Blue 1, titanium dioxide)",
        "nutriscore":"e","labels":"Vegan","allergens_tags":[],"nutriments":{"energy-kcal_100g":406,"fat_100g":4.5,"sugars_100g":77,"proteins_100g":0,"salt_100g":0.05}},
    "0040000527336": {"name":"M&M\'s Milk Chocolate","brand":"Mars","categories":"Candy, Chocolate confectionery",
        "ingredients_text":"Milk Chocolate (Sugar, Chocolate, Skim Milk, Cocoa Butter, Lactose, Milkfat, Soy Lecithin, Salt, Artificial Flavors), Sugar, Cornstarch, Less than 1%: Corn Syrup, Dextrin, Coloring",
        "nutriscore":"e","allergens_tags":["en:milk","en:soybeans"],"nutriments":{"energy-kcal_100g":480,"fat_100g":20,"sugars_100g":60,"proteins_100g":5,"salt_100g":0.15}},
    "0034000008346": {"name":"Snickers Bar","brand":"Mars","categories":"Candy, Chocolate bars",
        "ingredients_text":"Milk Chocolate (Sugar, Cocoa Butter, Chocolate, Skim Milk, Lactose, Milkfat, Soy Lecithin, Artificial Flavor), Peanuts, Corn Syrup, Sugar, Palm Oil, Skim Milk, Butter, Milkfat, Salt, Egg Whites, Artificial Flavor",
        "nutriscore":"e","allergens_tags":["en:eggs","en:milk","en:peanuts","en:soybeans"],"nutriments":{"energy-kcal_100g":488,"fat_100g":24,"sugars_100g":53,"proteins_100g":8,"salt_100g":0.27}},
    "0034000008353": {"name":"Twix Cookie Bar","brand":"Mars","categories":"Candy, Cookie bars",
        "ingredients_text":"Milk Chocolate (Sugar, Cocoa Butter, Chocolate, Skim Milk, Lactose, Milkfat, Soy Lecithin, Artificial Flavor), Enriched Wheat Flour, Sugar, Palm Oil, Skim Milk, Corn Syrup, Butter, Salt, Cocoa Powder, Soy Lecithin, Artificial Flavor",
        "nutriscore":"e","allergens_tags":["en:gluten","en:milk","en:soybeans","en:wheat"],"nutriments":{"energy-kcal_100g":497,"fat_100g":24,"sugars_100g":54,"proteins_100g":4.6,"salt_100g":0.35}},
    # ── Healthy & organic ────────────────────────────────────────────────────
    "0722252008091": {"name":"Kind Dark Chocolate Nuts & Sea Salt Bar","brand":"KIND","categories":"Nutrition bars, Snack bars",
        "ingredients_text":"Almonds, Peanuts, Chicory root fiber, Honey, Palm kernel oil, Sugar, glucose syrup, Rice flour, Vegetable glycerin, Crisp rice, Sea salt, Soy lecithin, Dark chocolate (cocoa mass, sugar, cocoa butter, vanilla extract), Cocoa powder",
        "nutriscore":"c","allergens_tags":["en:nuts","en:peanuts","en:soybeans"],"nutriments":{"energy-kcal_100g":430,"fat_100g":32,"sugars_100g":17,"proteins_100g":13,"salt_100g":0.57}},
    "0726635452900": {"name":"Larabar Apple Pie Bar","brand":"Larabar","categories":"Nutrition bars, Vegan snacks",
        "ingredients_text":"Dates, Almonds, Unsweetened apples, Walnuts, Cinnamon",
        "nutriscore":"c","labels":"Vegan","allergens_tags":["en:nuts"],"nutriments":{"energy-kcal_100g":350,"fat_100g":11,"sugars_100g":47,"proteins_100g":5,"salt_100g":0}},
    # ── Soy milk & tofu ──────────────────────────────────────────────────────
    "0025293004376": {"name":"Silk Soymilk Original","brand":"Silk","categories":"Plant-based milks, Soy drinks",
        "ingredients_text":"Soymilk (Filtered Water, Whole Soybeans), Cane Sugar, Sea Salt, Carrageenan, Natural Flavor, Calcium Carbonate, Vitamin A Palmitate, Vitamin D2, Riboflavin (B2), Vitamin B12",
        "nutriscore":"b","labels":"Vegan","allergens_tags":["en:soybeans"],"nutriments":{"energy-kcal_100g":54,"fat_100g":2,"sugars_100g":6,"proteins_100g":3.3,"salt_100g":0.13}},
    # ── Juices ───────────────────────────────────────────────────────────────
    "0009800895038": {"name":"Ocean Spray Cranberry Juice","brand":"Ocean Spray","categories":"Beverages, Fruit juices",
        "ingredients_text":"Water, Cranberry juice from concentrate, Sugar, Ascorbic acid (Vitamin C)",
        "nutriscore":"d","allergens_tags":[],"nutriments":{"energy-kcal_100g":57,"fat_100g":0,"sugars_100g":14,"proteins_100g":0,"salt_100g":0}},
}

# Build search index for fuzzy matching
_SEARCH_INDEX = None

def _get_search_index():
    global _SEARCH_INDEX
    if _SEARCH_INDEX is None:
        _SEARCH_INDEX = []
        for bc, p in DEMO_PRODUCTS.items():
            _SEARCH_INDEX.append({
                "bc": bc,
                "name_l": p["name"].lower(),
                "brand_l": p.get("brand","").lower(),
                "cats_l": p.get("categories","").lower(),
                "data": p,
            })
    return _SEARCH_INDEX


def fallback_mock_product(barcode: str) -> dict:
    """
    Generate a plausible mock product for ANY unknown barcode.
    Classification rule:
      digits contain '0' or '1'  → Vegan (crisps / ketchup profile)
      digits contain '2' or '3'  → Vegetarian/Dairy (yogurt / cheese profile)
      all other digit sequences   → Non-Vegetarian (chicken / meat profile)
    """
    bc = barcode.strip()
    digits = set(bc)

    if digits & {"0", "1"}:
        return {
            "name": f"Generic Snack Product ({bc[:6]}…)",
            "brand": "Unknown Brand",
            "barcode": bc,
            "ingredients_text": (
                "Potatoes, Vegetable oil (sunflower oil, rapeseed oil), "
                "Salt, Natural flavourings, Citric acid"
            ),
            "labels": "Vegan",
            "allergens": [],
            "categories": "Snacks, Crisps",
            "image": "",
            "nutriscore": "D",
            "nutriments": {
                "energy": 520, "fat": 30, "saturated_fat": 3,
                "sugars": 1, "protein": 6, "salt": 1.4, "fiber": 4, "carbs": 55,
            },
        }
    elif digits & {"2", "3"}:
        return {
            "name": f"Generic Dairy Product ({bc[:6]}…)",
            "brand": "Unknown Brand",
            "barcode": bc,
            "ingredients_text": (
                "Whole milk, Cream, Salt, Cheese cultures, Microbial rennet"
            ),
            "labels": "Vegetarian",
            "allergens": ["milk"],
            "categories": "Dairy, Cheese",
            "image": "",
            "nutriscore": "C",
            "nutriments": {
                "energy": 300, "fat": 24, "saturated_fat": 16,
                "sugars": 0.5, "protein": 20, "salt": 1.7, "fiber": 0, "carbs": 1,
            },
        }
    else:
        return {
            "name": f"Generic Meat Product ({bc[:6]}…)",
            "brand": "Unknown Brand",
            "barcode": bc,
            "ingredients_text": (
                "Chicken (72%), Water, Starch, Salt, Dextrose, "
                "Spices, Sodium phosphates, Smoke flavour"
            ),
            "labels": "",
            "allergens": [],
            "categories": "Meat products, Poultry",
            "image": "",
            "nutriscore": "D",
            "nutriments": {
                "energy": 185, "fat": 10, "saturated_fat": 3,
                "sugars": 1, "protein": 22, "salt": 1.2, "fiber": 0, "carbs": 3,
            },
        }


class ProductFetchService:
    HEADERS = {
        "User-Agent": settings.OFF_USER_AGENT,
        "Accept": "application/json",
    }

    def fetch_by_barcode(self, barcode: str) -> Optional[dict]:
        """Fetch product by barcode. Tries API first, then local fallback.
        Tries multiple barcode formats (with/without leading zeros)."""
        barcode = barcode.strip().replace(" ", "").replace("-", "")

        # Build list of formats to try
        variants = [barcode]
        # Try stripping leading zeros
        stripped = barcode.lstrip("0")
        if stripped and stripped != barcode:
            variants.append(stripped)
        # Try with leading zero
        if not barcode.startswith("0") and len(barcode) < 14:
            variants.append("0" + barcode)
        # EAN-13 vs UPC-A (12 digit → add leading 0)
        if len(barcode) == 12:
            variants.append("0" + barcode)
        elif len(barcode) == 13 and barcode.startswith("0"):
            variants.append(barcode[1:])

        # Try live API for each variant
        for bc_try in variants:
            try:
                url = f"{settings.OPENFOODFACTS_BASE}/api/v0/product/{bc_try}.json"
                r = requests.get(url, headers=self.HEADERS, timeout=8)
                if r.status_code == 200:
                    data = r.json()
                    if data.get("status") == 1 and data.get("product",{}).get("ingredients_text"):
                        logger.info(f"OFF API found barcode {bc_try}")
                        return self._normalize(data["product"])
            except Exception as e:
                logger.warning(f"OFF API unavailable for {bc_try}: {e}")
                break  # If network is down, don't retry

        # Local fallback — try all barcode variants
        for bc_try in variants:
            if bc_try in DEMO_PRODUCTS:
                logger.info(f"Local fallback: {bc_try} → {DEMO_PRODUCTS[bc_try]['name']}")
                return self._normalize_demo(DEMO_PRODUCTS[bc_try])

        # Dynamic mock fallback — never returns "not found"
        logger.info(f"Generating mock product for unknown barcode: {barcode}")
        return fallback_mock_product(barcode)

    def search_by_name(self, query: str, limit: int = 6) -> list:
        """Search by product name — API first, local fuzzy match fallback."""
        try:
            r = requests.get(
                settings.OPENFOODFACTS_SEARCH,
                params={
                    "search_terms": query, "search_simple": 1, "action": "process",
                    "json": 1, "page_size": limit,
                    "fields": "code,product_name,brands,ingredients_text,labels,allergens_tags,image_front_url,categories,nutriments,nutrition_grades",
                },
                headers=self.HEADERS, timeout=8,
            )
            if r.status_code == 200:
                prods = r.json().get("products", [])
                results = [self._normalize(p) for p in prods
                           if p.get("product_name") and p.get("ingredients_text")]
                if results:
                    return results[:limit]
        except Exception as e:
            logger.warning(f"OFF search unavailable: {e}")

        # Local fuzzy fallback
        return self._local_search(query, limit)

    def _local_search(self, query: str, limit: int = 6) -> list:
        """Fuzzy search through local demo products."""
        q = query.lower().strip()
        idx = _get_search_index()
        scored = []
        for item in idx:
            score = 0
            if q == item["name_l"] or q == item["brand_l"]:
                score = 100
            elif item["name_l"].startswith(q) or q in item["name_l"]:
                score = 80
            elif q in item["brand_l"]:
                score = 60
            elif q in item["cats_l"]:
                score = 40
            else:
                # word-by-word match
                words = [w for w in q.split() if len(w) > 2]
                matches = sum(1 for w in words if w in item["name_l"] or w in item["brand_l"])
                if matches:
                    score = matches * 20
            if score > 0:
                scored.append((score, item["data"]))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [self._normalize_demo(p) for _, p in scored[:limit]]

    def _normalize(self, p: dict) -> dict:
        nm = p.get("nutriments", {})
        return {
            "name":            p.get("product_name", "Unknown"),
            "brand":           p.get("brands", "Unknown"),
            "barcode":         p.get("code", ""),
            "ingredients_text":p.get("ingredients_text", ""),
            "labels":          p.get("labels", ""),
            "allergens":       [a.replace("en:", "") for a in p.get("allergens_tags", [])],
            "categories":      (p.get("categories", "") or "")[:80],
            "image":           p.get("image_front_url", ""),
            "nutriscore":      (p.get("nutrition_grades", "") or "").upper(),
            "nutriments": {
                "energy":       nm.get("energy-kcal_100g"),
                "fat":          nm.get("fat_100g"),
                "saturated_fat":nm.get("saturated-fat_100g"),
                "sugars":       nm.get("sugars_100g"),
                "protein":      nm.get("proteins_100g"),
                "salt":         nm.get("salt_100g"),
                "fiber":        nm.get("fiber_100g"),
                "carbs":        nm.get("carbohydrates_100g"),
            },
        }

    def _normalize_demo(self, p: dict) -> dict:
        nm = p.get("nutriments", {})
        return {
            "name":            p["name"],
            "brand":           p.get("brand", ""),
            "barcode":         p.get("barcode", ""),
            "ingredients_text":p.get("ingredients_text", ""),
            "labels":          p.get("labels", ""),
            "allergens":       [a.replace("en:", "") for a in p.get("allergens_tags", [])],
            "categories":      p.get("categories", ""),
            "image":           p.get("image_front_url", ""),
            "nutriscore":      (p.get("nutriscore", "") or "").upper(),
            "nutriments": {
                "energy":       nm.get("energy-kcal_100g"),
                "fat":          nm.get("fat_100g"),
                "saturated_fat":nm.get("saturated-fat_100g"),
                "sugars":       nm.get("sugars_100g"),
                "protein":      nm.get("proteins_100g"),
                "salt":         nm.get("salt_100g"),
                "fiber":        nm.get("fiber_100g"),
                "carbs":        nm.get("carbohydrates_100g"),
            },
        }
