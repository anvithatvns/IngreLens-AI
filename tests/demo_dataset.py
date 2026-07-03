"""
IngreLens AI — Complete Demo Dataset
50+ copy-paste-ready ingredient lists for every scenario.
Run: python tests/demo_dataset.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from backend.services.analysis_service import IngredientAnalysisService

svc = IngredientAnalysisService()

DEMO_DATA = {

    "✅ VEGAN — 100% Plant-Based": [
        ("Oat Milk Barista",
         "Water, Oat (10%), Sunflower oil, Calcium carbonate, Sea salt, Riboflavin, Vitamin B12, Vitamin D2, Dipotassium phosphate, Gellan gum"),
        ("Almond Milk Unsweetened",
         "Filtered water, Almonds (3%), Calcium carbonate, Sea salt, Sunflower lecithin, Vitamin D2, Vitamin B12"),
        ("Vegan Dark Chocolate 72%",
         "Cocoa mass (72%), Raw cane sugar, Cocoa butter, Vanilla extract, Emulsifier (soya lecithin)"),
        ("Coconut Yogurt",
         "Coconut milk, Water, Tapioca starch, Pectin, Vitamin D2, Live bacterial cultures"),
        ("Vegan Protein Bar",
         "Dates (30%), Pea protein isolate, Almonds, Cashews, Cocoa powder, Coconut oil, Vanilla extract, Sea salt"),
        ("Impossible Burger",
         "Water, Soy protein concentrate, Coconut oil, Sunflower oil, Potato protein, Methylcellulose, Yeast extract, Soy leghemoglobin, Salt, Mixed tocopherols"),
        ("Vegan Butter",
         "Water, Coconut oil, Rapeseed oil, Salt, Sunflower lecithin, Lactic acid, Vitamin D2, Natural flavoring (plant-based)"),
        ("Hummus Classic",
         "Chickpeas (60%), Tahini (sesame paste), Water, Lemon juice, Garlic, Salt, Citric acid, Olive oil"),
        ("Oat Porridge Plain",
         "Whole grain rolled oats, Salt"),
        ("Green Smoothie",
         "Banana, Spinach, Water, Flaxseeds, Lemon juice, Ginger extract"),
    ],

    "⚠️ UNCERTAIN — Verify with Brand": [
        ("Oreo Cookies",
         "Unbleached enriched flour, Sugar, Palm and/or canola oil, Cocoa powder, High fructose corn syrup, Leavening, Salt, Soy lecithin, Vanillin, Chocolate"),
        ("Plain Crisps",
         "Potatoes, Sunflower oil, Salt"),
        ("White Bread",
         "Wheat flour, Water, Yeast, Salt, Sugar, Rapeseed oil, Emulsifiers (E471, E481), Flour treatment agent (E300)"),
        ("Red Bull Energy Drink",
         "Carbonated water, Sucrose, Glucose, Citric acid, Taurine (0.4%), Sodium bicarbonate, Magnesium carbonate, Caffeine (0.03%), Niacinamide, Calcium pantothenate, Pyridoxine HCl, Vitamin B12, Natural flavors, Colors"),
        ("Pasta Plain",
         "Durum wheat semolina, Water"),
        ("Pringles Original",
         "Dried potatoes, Vegetable oil, Wheat starch, Maltodextrin, Salt, Emulsifier (E471), Natural flavors"),
        ("Soy Sauce",
         "Water, Soybean, Wheat, Salt, Ethyl alcohol"),
    ],

    "❌ NOT VEGAN — Contains Dairy": [
        ("Nutella",
         "Sugar, Palm oil, Hazelnuts (13%), Skimmed milk powder (8.7%), Fat-reduced cocoa (7.4%), Emulsifier (Soya lecithin), Vanillin"),
        ("Kit Kat Milk Chocolate",
         "Sugar, Wheat flour, Cocoa butter, Skimmed milk powder, Cocoa mass, Milk fat, Lactose, Emulsifier (Soya lecithin), Yeast, Raising agent, Salt, Natural vanilla flavouring"),
        ("Dairy Milk Chocolate",
         "Sugar, Cocoa butter, Whole milk powder, Cocoa mass, Lactose, Emulsifier (Soya lecithin), Vanillin"),
        ("Butter Croissant",
         "Wheat flour, Butter (22%), Water, Sugar, Eggs, Yeast, Salt, Skim milk powder, Emulsifier (E471)"),
        ("Greek Yogurt",
         "Skimmed pasteurised milk, Cream, Live cultures (Streptococcus thermophilus, Lactobacillus bulgaricus)"),
        ("Cheddar Cheese Sauce",
         "Milk, Modified starch, Cheddar cheese (milk, salt, starter culture, rennet), Butter, Salt, Flavouring"),
    ],

    "❌ NOT VEGAN — Contains Eggs": [
        ("Egg Pasta",
         "Durum wheat semolina (75%), Egg (25%), Salt"),
        ("Mayonnaise",
         "Rapeseed oil (79%), Water, Pasteurised free-range egg and egg yolk (8.6%), Spirit vinegar, Sugar, Salt, Lemon juice"),
        ("Classic Sponge Cake",
         "Wheat flour, Sugar, Eggs, Butter, Baking powder, Vanilla extract, Salt"),
        ("Egg Noodles",
         "Wheat flour, Eggs (30%), Water, Salt"),
    ],

    "❌ NOT VEGAN — Contains Honey": [
        ("Honey Granola",
         "Rolled oats, Honey (12%), Sunflower oil, Brown sugar, Almonds, Pumpkin seeds, Cinnamon, Salt"),
        ("Honey Mustard Dressing",
         "Rapeseed oil, Water, Honey (8%), Mustard (mustard seeds, water, vinegar, salt), White wine vinegar, Sugar, Salt, Garlic"),
        ("Honey Nut Cereal",
         "Whole grain oats, Sugar, Honey (3%), Almond pieces, Vegetable oil, Salt, Calcium carbonate, Niacin, Vitamin D3"),
        ("Propolis Throat Spray",
         "Water, Propolis extract (15%), Glycerin, Peppermint oil"),
    ],

    "❌ NOT VEGAN — Contains Gelatin": [
        ("Jelly Sweets",
         "Glucose syrup, Sugar, Beef gelatin, Citric acid, Natural flavors, Fruit juices from concentrate, Colors (E120, E160c)"),
        ("Marshmallows",
         "Sugar, Glucose syrup, Pork gelatin, Water, Dextrose, Natural vanilla flavoring"),
        ("Panna Cotta Mix",
         "Sugar, Dextrose, Pork gelatin, Skimmed milk powder, Modified starch, Vanilla flavor"),
        ("Gummy Vitamins",
         "Glucose syrup, Sucrose, Gelatin, Citric acid, Ascorbic acid, Cholecalciferol (D3), Natural flavors"),
    ],

    "❌ NOT VEGAN — Hidden Animal Ingredients (Shocking!)": [
        ("Red Candy (Carmine)",
         "Sugar, Glucose syrup, Citric acid, Natural flavors, Carmine (E120), Beeswax (E901), Carnauba wax"),
        ("Innocent-Looking Gummies",
         "Glucose syrup, Sugar, Beef gelatin, Citric acid, Natural fruit flavors, Red 40, Carmine (E120)"),
        ("Bread with L-Cysteine",
         "Wheat flour, Water, Yeast, Salt, Sugar, Rapeseed oil, Emulsifiers (E471, E481), L-cysteine (E920), Ascorbic acid"),
        ("Worcestershire Sauce",
         "Malt vinegar (from barley), Molasses, Sugar, Salt, Anchovies, Tamarind extract, Onions, Garlic, Spices, Natural flavourings"),
        ("Some Wines",
         "Cabernet Sauvignon grape juice, Sulphur dioxide, Potassium metabisulphite, Isinglass (fining agent)"),
        ("Rennet Cheese",
         "Pasteurised cows milk, Salt, Starter culture (lactic acid bacteria), Animal rennet"),
        ("Vitamin D3 Supplement",
         "Maltodextrin, Cholecalciferol (Vitamin D3 from lanolin), Silicon dioxide, Magnesium stearate"),
        ("Shellac-Coated Apples",
         "Apple, Shellac (E904), Carnauba wax (E903)"),
        ("Casein Protein Powder",
         "Micellar casein (milk protein), Cocoa powder, Sodium caseinate, Soy lecithin, Sucralose, Natural flavors"),
    ],

    "❌ NOT VEGAN — Contains Whey": [
        ("Whey Protein Isolate",
         "Whey protein isolate (97%), Soy lecithin, Natural vanilla flavor"),
        ("Protein Yogurt",
         "Skimmed milk, Whey protein concentrate, Milk protein concentrate, Sugar, Modified starch, Pectin, Live cultures"),
        ("Protein Cereal Bar",
         "Whey protein crisp (whey protein isolate, tapioca starch, calcium carbonate), Glucose syrup, Palm oil, Whey powder, Sugar"),
    ],

    "🔢 E-NUMBER TESTS": [
        ("E120 Carmine (NOT VEGAN)",
         "Sugar, Glucose syrup, E120, E422, E330, E471"),
        ("E904 Shellac (NOT VEGAN)",
         "Dark chocolate, Sugar, Cocoa butter, Glazing agent (E904), Carnauba wax (E903)"),
        ("E441 Gelatin (NOT VEGAN)",
         "Sugar, Glucose syrup, E441, E330, Natural flavors, E129"),
        ("E322 Soy Lecithin (VEGAN)",
         "Cocoa mass, Sugar, Cocoa butter, E322, Vanilla extract"),
        ("E415 Xanthan Gum (VEGAN)",
         "Water, E415, Citric acid, Salt, Natural flavors"),
        ("E406 Agar (VEGAN)",
         "Mango puree, Sugar, E406, Citric acid"),
        ("Mixed E-numbers",
         "Sugar, E322, E471, E120, E415, E440, E330, Citric acid"),
    ],

    "🧪 OCR QUALITY TESTS": [
        ("Clean OCR",
         "Sugar, Palm oil, Hazelnuts (13%), Skimmed milk powder (8.7%), Fat-reduced cocoa (7.4%), Emulsifier (Soya lecithin), Vanillin"),
        ("Noisy OCR — Blurry Scan",
         "Sug@r, P@lm 0il, H@z3lnuts (13%), Sk1mm3d m1lk p0wd3r (8.7%), F@t-r3duc3d c0c0@ (7.4%), Em5ls1fi3r, V@n1ll1n"),
        ("Missing commas OCR",
         "Sugar Palm oil Hazelnuts Skimmed milk powder Fat-reduced cocoa Emulsifier Vanillin"),
        ("Extra spaces OCR",
         "Sugar ,   Palm  oil ,   Hazelnuts   (13%) ,  Skimmed   milk   powder"),
        ("Broken lines OCR",
         "Sugar\nPalm oil\nHazelnuts 13%\nSkimmed milk powder 8.7%\nFat-reduced cocoa"),
        ("Mixed case OCR",
         "SUGAR, Palm OIL, HAZELNUTS, skimmed MILK POWDER, fat-REDUCED cocoa"),
        ("Ingredients prefix OCR",
         "Ingredients: Sugar, Palm oil, Skimmed milk powder, Cocoa, Soy lecithin"),
        ("OCR with random symbols",
         "Sug|ar, Pa|m oi|, Haze|nuts, Ski|mmed mi|k powder, C0coa"),
    ],
}

def run_all_demos():
    print("\n" + "="*70)
    print("  IngreLens AI — COMPLETE DEMO DATASET RESULTS")
    print("="*70)

    totals = {"Vegan": 0, "Not Vegan": 0, "Uncertain": 0}

    for category, items in DEMO_DATA.items():
        print(f"\n{'─'*70}")
        print(f"  {category}")
        print(f"{'─'*70}")
        for name, ingredients in items:
            r = svc.analyze(ingredients, name)
            icon = {"Vegan":"✅","Not Vegan":"❌","Uncertain":"⚠️"}.get(r.overall_vegan,"❓")
            totals[r.overall_vegan] = totals.get(r.overall_vegan, 0) + 1
            nv = f"  → Non-vegan: {', '.join(r.non_vegan_ingredients[:2])}" if r.non_vegan_ingredients else ""
            al = f"  → Allergens: {', '.join(r.allergens_detected[:3])}" if r.allergens_detected else ""
            print(f"  {icon} {name:<35} {r.overall_vegan:<12} {r.vegan_confidence:.0%} conf | H:{r.health_score}/100")
            if nv: print(f"    {nv}")
            if al: print(f"    {al}")

    print(f"\n{'='*70}")
    print(f"  SUMMARY: ✅ {totals.get('Vegan',0)} Vegan  ❌ {totals.get('Not Vegan',0)} Not Vegan  ⚠️ {totals.get('Uncertain',0)} Uncertain")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    run_all_demos()
