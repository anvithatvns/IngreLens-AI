"""IngreLens AI — 🔢 Barcode Lookup · Manual lookup + Paste Ingredients"""
import streamlit as st, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from shared_ui import (inject_css, init_state, render_top_nav, render_page_header, add_history,
                        full_analysis_display, get_logo_b64, SAGE,
                        cached_analyze, log_activity, enter_page)
from backend.services.analysis_service import IngredientAnalysisService
from backend.services.product_service import ProductFetchService

st.set_page_config(page_title="Barcode Lookup · IngreLens AI", page_icon="🔢", layout="wide")
inject_css(); init_state(); render_top_nav()
enter_page("barcode_lookup")

@st.cache_resource(show_spinner=False)
def get_svc(): return IngredientAnalysisService(), ProductFetchService()
svc, prod_svc = get_svc()

render_page_header("🔢", "Barcode Lookup",
    "Look up a product by barcode, or paste an ingredient list directly")

def clear_lookup_state():
    for k in ["barcode_result", "barcode_prod", "selected_barcode",
              "paste_result", "paste_result_name", "paste_raw", "paste_name_input",
              "paste_product", "_paste_demo_meta"]:
        st.session_state.pop(k, None)

tab1, tab2 = st.tabs(["🔢 Barcode Lookup", "✍️ Paste Ingredients"])

# ══════════════════════════════════════════════════════════════════
# TAB 1 — BARCODE LOOKUP (manual + 12 verified demos)
# ══════════════════════════════════════════════════════════════════
with tab1:
    st.markdown("### 🔢 Lookup by Barcode (EAN / UPC)")

    if st.session_state.get("barcode_result"):
        prod   = st.session_state.get("barcode_prod", {})
        result = st.session_state["barcode_result"]
        st.markdown(f"## 📋 {prod.get('name','Product')}")
        if prod.get("image"):
            ci2, _ = st.columns([1, 4])
            with ci2:
                st.image(prod["image"], width=100)
        full_analysis_display(result, prod, key_suffix="lookup_barcode")
        if st.button("🔄 Clear & Lookup Again", key="btn_bc_clear", type="secondary"):
            clear_lookup_state()
            st.rerun()
    else:
        bc1, bc2 = st.columns([4, 1])
        with bc1:
            barcode = st.text_input(
                "Barcode", placeholder="e.g. 3017624010701",
                label_visibility="collapsed", key="barcode_input",
            )
        with bc2:
            bc_go = st.button("Lookup →", type="primary",
                              use_container_width=True, key="bc_go_btn")

        st.markdown(
            f'<div style="font-size:0.65rem;font-weight:700;letter-spacing:0.1em;'
            f'text-transform:uppercase;color:{SAGE["stone"]};margin:12px 0 6px">'
            f'✅ Verified barcodes — click to load</div>',
            unsafe_allow_html=True,
        )

        DEMOS = [
            ("🍫 Nutella","3017624010701","Not Vegan"),
            ("🍪 Oreo","7622300416981","Vegan"),
            ("🌾 Alpro Oat","5411188131335","Vegan"),
            ("🍦 Ben & Jerry's","8714100735688","Non-Veg"),
            ("🌿 Impossible","0085239026700","Uncertain"),
            ("🥛 Whey Protein","0041570050699","Vegetarian"),
            ("🍬 Kit Kat","4000539400404","Vegetarian"),
            ("🥤 Coca-Cola","5449000000996","Uncertain"),
            ("🌰 Pringles","5053990109204","Uncertain"),
            ("🍊 Tropicana OJ","0048500206867","Vegan"),
            ("🫐 Innocent Smoothie","5038862263887","Vegan"),
            ("🥜 Nutri-Grain","0038000845826","Vegetarian"),
        ]
        DC = {"Vegan":"#2ecc71","Vegetarian":"#4cd787","Eggetarian":"#f39c4a",
              "Non-Veg":"#ff6b5a","Uncertain":"#ffc247","Not Vegan":"#ff6b5a"}

        for row in range(0, len(DEMOS), 4):
            row_items = DEMOS[row:row+4]
            cols = st.columns(4)
            for ci, (lbl, bc, exp) in enumerate(row_items):
                with cols[ci]:
                    st.markdown(
                        f'<div style="font-size:0.62rem;color:{DC.get(exp,"#888")};'
                        f'font-weight:600;text-align:center;margin-bottom:2px">{exp}</div>',
                        unsafe_allow_html=True,
                    )
                    if st.button(lbl, key=f"dbc_{bc}", use_container_width=True):
                        st.session_state["selected_barcode"] = bc
                        st.rerun()

        active_bc = st.session_state.get("selected_barcode", barcode)
        if st.session_state.get("selected_barcode"):
            st.info(f"📦 Selected: **{active_bc}** — click Lookup →")
            bc_go = True
            barcode = active_bc

        if bc_go and barcode:
            st.session_state.pop("selected_barcode", None)
            bc_clean = barcode.strip()
            with st.spinner(f"🔍 Fetching {bc_clean} from Open Food Facts…"):
                prod = prod_svc.fetch_by_barcode(bc_clean)
            if not prod:
                st.error(
                    f"❌ **{bc_clean}** not found. Try a demo barcode above, "
                    "or use the Paste Ingredients tab to enter manually."
                )
            elif not prod.get("ingredients_text"):
                st.warning(f"Found **{prod['name']}** but no ingredient data available.")
            else:
                st.success(f"✅ Found: **{prod['name']}** · {prod.get('brand','—')}")
                if prod.get("image"):
                    ci3, _ = st.columns([1, 4])
                    with ci3:
                        st.image(prod["image"], width=100)
                with st.spinner("🤖 Analyzing…"):
                    result = cached_analyze(svc, prod["ingredients_text"], prod["name"], barcode=bc_clean)
                st.session_state["barcode_result"] = result
                st.session_state["barcode_prod"]   = prod
                add_history(prod["name"], result.overall_vegan, prod["ingredients_text"], result, barcode=bc_clean)
                log_activity("Barcode Scan", "Barcode Lookup")
                st.rerun()

# ══════════════════════════════════════════════════════════════════
# TAB 2 — PASTE INGREDIENTS
# ══════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("### ✍️ Paste or type ingredient list")

    if st.session_state.get("paste_result"):
        result = st.session_state["paste_result"]
        st.markdown(f"## 📋 {st.session_state.get('paste_result_name','Custom Product')}")
        full_analysis_display(result, st.session_state.get("paste_product"), key_suffix="lookup_paste")
        if st.button("🔄 Clear & Scan Again", key="btn_paste_clear", type="secondary"):
            clear_lookup_state()
            st.rerun()
    else:
        # Each demo carries the same nutrition/nutriscore/allergen metadata the
        # Search/Barcode paths get from Open Food Facts, so loading a demo here
        # produces the same complete analysis UI (nutrition chart, Nutri-Score,
        # Daily Consumption) instead of the ingredients-only view a truly
        # freehand paste (no known nutrition data) still correctly falls back to.
        EXAMPLES = [
            ("🍫 Nutella","Nutella","Sugar, Palm oil, Hazelnuts (13%), Skimmed milk powder (8.7%), Fat-reduced cocoa, Soya lecithin, Vanillin",
             {"barcode":"3017624010701","nutriscore":"E","allergens":["milk","nuts","soy"],
              "nutriments":{"energy":539,"fat":30.9,"sugars":56.3,"protein":6.3,"salt":0.107,"fiber":0}}),
            ("🍪 Oreo","Oreo","Unbleached enriched flour, Sugar, Palm oil, Cocoa powder, High fructose corn syrup, Soy lecithin, Vanillin",
             {"barcode":"7622300416981","nutriscore":"E","allergens":["gluten","soy"],
              "nutriments":{"energy":480,"fat":21,"sugars":42,"protein":5,"salt":0.75,"fiber":2}}),
            ("🥛 Whey","Whey Protein","Whey protein isolate, Whey protein concentrate, Cocoa powder, Natural flavors, Soy lecithin",
             {"barcode":"0041570050699","nutriscore":"B","allergens":["milk","soy"],
              "nutriments":{"energy":390,"fat":4.5,"sugars":4,"protein":77,"salt":0.5,"fiber":0}}),
            ("🌾 Oat Milk","Alpro Oat Milk","Water, Oat (10%), Sunflower oil, Calcium carbonate, Sea salt, Riboflavin B2, Vitamin B12, Vitamin D2",
             {"barcode":"5411188131335","nutriscore":"B","allergens":["gluten"],
              "nutriments":{"energy":47,"fat":1.5,"sugars":4,"protein":1,"salt":0.1,"fiber":0.5}}),
            ("🌿 Impossible","Impossible Burger","Water, Soy protein concentrate, Coconut oil, Sunflower oil, Natural flavors, Potato protein, Yeast extract, Salt",
             {"barcode":"0085239026700","nutriscore":"C","allergens":["soy"],
              "nutriments":{"energy":240,"fat":14,"sugars":0,"protein":19,"salt":0.83,"fiber":0}}),
            ("🍦 Ben & Jerry","Ben & Jerry's","Cream, Skimmed milk, Sugar, Egg yolk, Vanilla extract, Guar gum, Carrageenan",
             {"barcode":"8714100735688","nutriscore":"E","allergens":["eggs","gluten","milk"],
              "nutriments":{"energy":282,"fat":14.7,"sugars":27,"protein":4.2,"salt":0.18,"fiber":1}}),
            ("🍬 Red Candy","Red Candy","Sugar, Glucose syrup, Citric acid, Carmine (E120), Beeswax (E901)",
             {"barcode":"","nutriscore":"E","allergens":[],
              "nutriments":{"energy":390,"fat":0,"sugars":95,"protein":0,"salt":0,"fiber":0}}),
            ("🍗 Butter Chkn","Butter Chicken","Chicken breast, Butter, Cream, Onion, Tomato, Garlic, Ginger, Salt",
             {"barcode":"","nutriscore":"C","allergens":["milk"],
              "nutriments":{"energy":190,"fat":14,"sugars":3,"protein":12,"salt":0.9,"fiber":1}}),
            ("🥚 Egg Rice","Egg Fried Rice","Cooked rice, Eggs, Soy sauce, Sesame oil, Spring onion, Salt, Pepper",
             {"barcode":"","nutriscore":"C","allergens":["eggs","soy"],
              "nutriments":{"energy":170,"fat":5,"sugars":0.5,"protein":5,"salt":0.8,"fiber":0.6}}),
            ("🍕 Pizza","Cheese Pizza","Wheat flour, Mozzarella cheese, Tomato sauce, Olive oil, Yeast, Salt",
             {"barcode":"","nutriscore":"D","allergens":["gluten","milk"],
              "nutriments":{"energy":266,"fat":10,"sugars":3.5,"protein":11,"salt":1.2,"fiber":2}}),
            ("🌱 Vegan Bar","Vegan Protein Bar","Dates, Almonds, Pea protein, Cocoa powder, Coconut oil, Maple syrup, Chia seeds",
             {"barcode":"","nutriscore":"B","allergens":["nuts"],
              "nutriments":{"energy":410,"fat":18,"sugars":29,"protein":14,"salt":0.1,"fiber":8}}),
            ("🍷 Wine","Red Wine","Cabernet Sauvignon grape juice, Sulphur dioxide, Isinglass",
             {"barcode":"","nutriscore":"","allergens":["fish"],
              "nutriments":{"energy":83,"fat":0,"sugars":0.6,"protein":0.1,"salt":0,"fiber":0}}),
        ]

        st.markdown(
            f'<div style="font-size:0.65rem;font-weight:700;letter-spacing:0.1em;'
            f'text-transform:uppercase;color:{SAGE["stone"]};margin-bottom:6px">Load a demo example</div>',
            unsafe_allow_html=True,
        )
        ec = st.columns(4)
        for i, (lbl, name, _, meta) in enumerate(EXAMPLES):
            with ec[i % 4]:
                if st.button(lbl, key=f"ex_{i}", use_container_width=True):
                    # Write straight into the widgets' own session-state keys
                    # (not a separate shadow key) — a keyed widget only reads
                    # its `value=` argument on its very first render, so
                    # updating an intermediary key had no visible effect
                    # here after the first rerun. Setting the widget's own
                    # key directly is what Streamlit actually picks up.
                    st.session_state["paste_raw"] = EXAMPLES[i][2]
                    st.session_state["paste_name_input"] = name
                    st.session_state["_paste_demo_meta"] = {"name": name, **meta}
                    st.rerun()

        ma, mb = st.columns([3, 1])
        with ma:
            raw = st.text_area(
                "Ingredient list", height=130,
                placeholder="Paste ingredient list here…",
                label_visibility="collapsed", key="paste_raw",
            )
        with mb:
            pname = st.text_input(
                "Product name", placeholder="e.g. Nutella",
                label_visibility="collapsed", key="paste_name_input",
            )
            st.markdown('<div style="height:6px"></div>', unsafe_allow_html=True)
            go = st.button("🧬 Analyze", type="primary",
                           use_container_width=True, key="paste_go")

        if go and raw:
            with st.spinner("🤖 Running 5-agent analysis pipeline…"):
                result = svc.analyze(raw, pname or "Custom Product")
            st.session_state["paste_result"] = result
            st.session_state["paste_result_name"] = pname or "Custom Product"
            # Only reuse the demo's nutrition metadata if the name still
            # matches it — if the user changed the name (or typed their own
            # ingredients from scratch), there's genuinely no known nutrition
            # data, so product stays None and the ingredients-only view shows.
            demo_meta = st.session_state.get("_paste_demo_meta")
            if demo_meta and demo_meta.get("name") == pname:
                st.session_state["paste_product"] = {
                    "name": pname, "barcode": demo_meta.get("barcode", ""),
                    "nutriscore": demo_meta.get("nutriscore", ""),
                    "allergens": demo_meta.get("allergens", []),
                    "nutriments": demo_meta.get("nutriments", {}),
                }
            else:
                st.session_state.pop("paste_product", None)
            add_history(pname or "Custom Product", result.overall_vegan, raw, result)
            log_activity("Paste Ingredients", "Barcode Lookup")
            st.rerun()
        elif go:
            st.warning("⚠️ Please enter or paste an ingredient list first.")
