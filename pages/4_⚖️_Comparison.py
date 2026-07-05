"""IngreLens AI — ⚖️ Compare · Fixed preset buttons"""
import streamlit as st, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from shared_ui import (inject_css, init_state, render_top_nav, render_page_header, add_history,
                        render_verdict_card, render_health_score, render_nutriscore,
                        render_allergen_pills, render_ingredient_cards,
                        verdict_emoji, verdict_color, get_logo_b64, SAGE,
                        cached_analyze, log_activity, render_nutrition_pie, render_dietary_alerts,
                        render_consumption_checker,
                        enter_page)
from backend.services.analysis_service import IngredientAnalysisService
from backend.services.product_service import ProductFetchService

st.set_page_config(page_title="Compare · IngreLens AI", page_icon="⚖️", layout="wide")
inject_css(); init_state(); render_top_nav()
enter_page("comparison")

@st.cache_resource(show_spinner=False)
def get_svc(): return IngredientAnalysisService(), ProductFetchService()
svc, prod_svc = get_svc()

render_page_header("⚖️", "Product Comparison",
    "Side-by-side vegan status, allergens, and health score comparison")

# ── Quick compare preset buttons ──────────────────────────────────────────────
PRESETS = [
    ("🥤 Coke vs Coke Zero",        "Coca-Cola",        "Coke Zero"),
    ("🌾 Silk vs Oatly",            "Silk oat",         "Alpro oat"),
    ("🍫 Nutella vs 🌾 Oat Milk",   "Nutella",          "Alpro oat"),
    ("🍪 Oreo vs 🥛 Almond Milk",   "Oreo",             "almond milk"),
    ("🥤 Coke vs 🥤 Pepsi",         "Coca-Cola",        "Pepsi"),
    ("🌿 Impossible vs 🥛 Whey",    "Impossible burger","whey protein"),
    ("🍬 Kit Kat vs 🍫 Nutella",    "Kit Kat",          "Nutella"),
    ("🌾 Oat Milk vs 🥛 Soy Milk",  "Alpro oat",        "Silk soy"),
]

st.markdown(
    f'<div style="font-size:0.65rem;font-weight:700;letter-spacing:0.1em;'
    f'text-transform:uppercase;color:{SAGE["stone"]};margin-bottom:6px">'
    f'Quick Compare — click any pair to load & compare instantly</div>',
    unsafe_allow_html=True,
)

# ── THE FIX: preset buttons set state + trigger compare flag + rerun ──────────
pcols = st.columns(4)
for i, (lbl, a, b) in enumerate(PRESETS):
    with pcols[i % 4]:
        if st.button(lbl, key=f"pr_{i}", use_container_width=True):
            st.session_state["cmp_a"]       = a
            st.session_state["cmp_b"]       = b
            st.session_state["cmp_trigger"] = True  # auto-run compare
            st.rerun()

st.markdown("")

# ── Text inputs — pre-filled from session state ───────────────────────────────
c1, c2, c3 = st.columns([2, 2, 1])
with c1:
    qa = st.text_input(
        "Product A", value=st.session_state.get("cmp_a", ""),
        placeholder="e.g. Nutella", key="cmp_prod_a_in",
    )
with c2:
    qb = st.text_input(
        "Product B", value=st.session_state.get("cmp_b", ""),
        placeholder="e.g. Alpro oat milk", key="cmp_prod_b_in",
    )
with c3:
    st.markdown('<div style="height:28px"></div>', unsafe_allow_html=True)
    cmp_btn = st.button("⚖️ Compare", type="primary", use_container_width=True, key="cmp_btn")

# Auto-trigger if preset was clicked
if st.session_state.get("cmp_trigger") and qa and qb:
    st.session_state.pop("cmp_trigger", None)
    cmp_btn = True

# ── Helper: search with broader fallback ─────────────────────────────────────
def smart_search(query: str) -> list:
    """Search product — tries API then broad local fuzzy match."""
    results = prod_svc.search_by_name(query)
    if results:
        return results

    # Broader fuzzy match against all demo products
    q = query.lower().strip()
    from backend.services.product_service import DEMO_PRODUCTS
    matches = []
    for p in DEMO_PRODUCTS.values():
        name_l = p["name"].lower()
        brand_l = p.get("brand","").lower()
        cats_l = p.get("categories","").lower()
        # Score: exact > starts > contains > category
        if name_l == q or brand_l == q:
            matches.insert(0, p)
        elif name_l.startswith(q) or q in name_l or q in brand_l:
            matches.append(p)
        elif any(w in name_l or w in brand_l or w in cats_l
                 for w in q.split() if len(w) > 2):
            matches.append(p)
    return [prod_svc._normalize_demo(p) for p in matches[:6]] if matches else []

# ── Compare function ──────────────────────────────────────────────────────────
def show_comparison(ra, rb, pa, pb):
    st.markdown("---")
    import pandas as pd

    DIET_ICONS = {
        "Vegan":"🌱 Vegan","Vegetarian":"🧀 Vegetarian",
        "Eggetarian":"🥚 Eggetarian","Non-Vegetarian":"🍖 Non-Veg",
        "Uncertain":"⚠️ Uncertain","Not Vegan":"❌ Not Vegan",
    }
    DIET_COLORS = {
        "Vegan":"#2ecc71","Vegetarian":"#4cd787","Eggetarian":"#f39c4a",
        "Non-Vegetarian":"#ff6b5a","Uncertain":"#ffc247","Not Vegan":"#ff6b5a",
    }

    def diet_label(r):
        cat = getattr(r, "diet_category", r.overall_vegan)
        return DIET_ICONS.get(cat, cat)

    def nf(nm, k, u="g"):
        v = (nm or {}).get(k)
        return f"{float(v):.1f}{u}" if v is not None else "—"

    nma = pa.get("nutriments", {}) or {}
    nmb = pb.get("nutriments", {}) or {}
    na, nb = pa.get("name","A"), pb.get("name","B")

    # ── Comparison table ──────────────────────────────────────────────────────
    rows = {
        "Metric": [
            "Diet Category","Health Score","Allergens","Non-vegan ingredients",
            "Nutri-Score","Energy (per 100g)","Fat","Sugars","Protein","Salt"
        ],
        na[:20]: [
            diet_label(ra),
            f"{ra.health_score}/100",
            ", ".join(ra.allergens_detected) or "None",
            ", ".join(ra.non_vegan_ingredients) or "None",
            (pa.get("nutriscore") or "—").upper(),
            nf(nma,"energy","kcal"), nf(nma,"fat"),
            nf(nma,"sugars"), nf(nma,"protein"), nf(nma,"salt"),
        ],
        nb[:20]: [
            diet_label(rb),
            f"{rb.health_score}/100",
            ", ".join(rb.allergens_detected) or "None",
            ", ".join(rb.non_vegan_ingredients) or "None",
            (pb.get("nutriscore") or "—").upper(),
            nf(nmb,"energy","kcal"), nf(nmb,"fat"),
            nf(nmb,"sugars"), nf(nmb,"protein"), nf(nmb,"salt"),
        ],
    }
    st.dataframe(pd.DataFrame(rows).set_index("Metric"), use_container_width=True)

    # ── Side-by-side detail cards ─────────────────────────────────────────────
    col_l, col_r = st.columns(2)
    for tag, col, result, prod in [("a", col_l, ra, pa), ("b", col_r, rb, pb)]:
        with col:
            render_dietary_alerts(result)
            cat = getattr(result, "diet_category", result.overall_vegan)
            dc  = DIET_COLORS.get(cat, SAGE["stone"])
            di  = DIET_ICONS.get(cat, cat)
            st.markdown(
                f'<div style="background:{dc}22;border-left:4px solid {dc};'
                f'border-radius:12px;padding:14px 16px;margin-bottom:12px">'
                f'<div style="font-size:1.4rem;font-weight:700;color:{dc}">{di}</div>'
                f'<div style="font-size:1.1rem;font-weight:700;color:{SAGE["charcoal"]};margin-top:2px">'
                f'{prod.get("name","")}</div>'
                f'<div style="font-size:0.78rem;color:{SAGE["stone"]}">'
                f'Conf: {int(result.vegan_confidence*100)}% · '
                f'Health: {result.health_score}/100</div></div>',
                unsafe_allow_html=True,
            )
            if prod.get("image"):
                st.image(prod["image"], width=90)

            nv = [r for r in result.ingredient_results if "non-vegan" in r.vegan_status]
            if nv:
                st.markdown("**❌ Non-vegan ingredients:**")
                render_ingredient_cards(nv[:3], None)
            else:
                st.success("✅ No non-vegan ingredients detected")

            if result.allergens_detected:
                st.markdown("**⚠️ Allergens:**")
                render_allergen_pills(result.allergens_detected)

            render_health_score(result.health_score)

            if prod.get("nutriscore"):
                st.markdown(
                    f'<div style="font-size:0.65rem;font-weight:700;letter-spacing:0.1em;'
                    f'text-transform:uppercase;color:{SAGE["stone"]};margin:10px 0 5px">'
                    f'Nutri-Score</div>',
                    unsafe_allow_html=True,
                )
                render_nutriscore(prod["nutriscore"])

            nm_side = prod.get("nutriments", {}) or {}
            if any(nm_side.values()):
                render_nutrition_pie(nm_side, key_suffix=tag)

            render_consumption_checker(result, prod, key_suffix=tag)

    # ── Summary ───────────────────────────────────────────────────────────────
    st.markdown("---\n### 🏆 Summary")
    cat_a = getattr(ra, "diet_category", ra.overall_vegan)
    cat_b = getattr(rb, "diet_category", rb.overall_vegan)
    vegan_rank = ["Vegan","Vegetarian","Eggetarian","Uncertain","Not Vegan","Non-Vegetarian","Unknown"]

    if ra.health_score > rb.health_score:
        st.info(f"🏥 **Healthier choice:** {na} (score {ra.health_score} vs {rb.health_score})")
    elif rb.health_score > ra.health_score:
        st.info(f"🏥 **Healthier choice:** {nb} (score {rb.health_score} vs {ra.health_score})")
    else:
        st.info(f"🏥 **Equal health score:** Both score {ra.health_score}/100")

    rank_a = vegan_rank.index(cat_a) if cat_a in vegan_rank else 99
    rank_b = vegan_rank.index(cat_b) if cat_b in vegan_rank else 99
    if rank_a < rank_b:
        st.info(f"🌱 **More vegan-friendly:** {na} ({cat_a} vs {cat_b})")
    elif rank_b < rank_a:
        st.info(f"🌱 **More vegan-friendly:** {nb} ({cat_b} vs {cat_a})")
    else:
        st.info(f"🌱 **Same diet category:** Both are {cat_a}")

    if len(ra.allergens_detected) < len(rb.allergens_detected):
        st.info(f"⚠️ **Fewer allergens:** {na} ({len(ra.allergens_detected)} vs {len(rb.allergens_detected)})")
    elif len(rb.allergens_detected) < len(ra.allergens_detected):
        st.info(f"⚠️ **Fewer allergens:** {nb} ({len(rb.allergens_detected)} vs {len(ra.allergens_detected)})")


# ── Run comparison ────────────────────────────────────────────────────────────
if cmp_btn and qa and qb:
    with st.spinner(f"🔍 Searching for '{qa}' and '{qb}'…"):
        pal = smart_search(qa)
        pbl = smart_search(qb)

    if not pal:
        st.error(f"❌ Could not find **'{qa}'**. Try a different name or check spelling.")
    elif not pbl:
        st.error(f"❌ Could not find **'{qb}'**. Try a different name or check spelling.")
    else:
        pa, pb = pal[0], pbl[0]
        st.success(f"✅ Comparing: **{pa['name']}** vs **{pb['name']}**")

        with st.spinner("🤖 Running 5-agent analysis on both products…"):
            ra = cached_analyze(svc, pa.get("ingredients_text",""), pa["name"], barcode=pa.get("barcode"))
            rb = cached_analyze(svc, pb.get("ingredients_text",""), pb["name"], barcode=pb.get("barcode"))

        add_history(pa["name"], ra.overall_vegan, pa.get("ingredients_text",""), ra, barcode=pa.get("barcode"))
        add_history(pb["name"], rb.overall_vegan, pb.get("ingredients_text",""), rb, barcode=pb.get("barcode"))
        log_activity("Product Comparison", "Comparison")
        show_comparison(ra, rb, pa, pb)

elif cmp_btn:
    st.warning("⚠️ Please enter both Product A and Product B to compare.")
