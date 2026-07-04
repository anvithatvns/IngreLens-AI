"""IngreLens AI — Home · Sage & Stone · Real Logo"""
import streamlit as st, sys, time, base64
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

st.set_page_config(
    page_title="IngreLens AI — Scan, Analyse & Eat Smarter",
    page_icon="assets/logo_square.png", layout="wide", initial_sidebar_state="expanded",
)

from shared_ui import (inject_css, init_state, render_sidebar, render_page_header, add_history,
                        render_verdict_card, render_agent_row, render_metrics,
                        render_health_score, render_nutriscore,
                        render_ingredient_cards, render_allergen_pills,
                        full_analysis_display, get_logo_b64, render_logo_hero,
                        verdict_emoji, verdict_color, SAGE)
from backend.services.analysis_service import IngredientAnalysisService
from backend.services.product_service import ProductFetchService

inject_css()
init_state()
render_sidebar()

@st.cache_resource(show_spinner=False)
def get_svc():
    return IngredientAnalysisService(), ProductFetchService()

svc, ps = get_svc()

# ── HOME HERO — uses shared render_page_header ───────────────────────────────
render_page_header(
    "🏠", "IngreLens AI: Scan, Analyze & Eat Smarter",
    "AI-powered ingredient intelligence, simplified. Know your ingredients, instantly. Bridging the gap between complex labels and personalized, safer food choices."
)

# ── ABOUT (collapsed Platform Features) ───────────────────────────────────────
with st.expander("ℹ️ About IngreLens App", expanded=False):
    features = [
        ("📷","Ingredient Scanner","Upload any food label — OCR extracts and classifies instantly"),
        ("🔍","Product Search","Search 3M+ products by name or barcode"),
        ("🧬","AI Classification","5-layer pipeline: KB → aliases → keywords → vector → fallback"),
        ("⚠️","Allergy Detection","10 allergen groups: dairy, eggs, gluten, soy, nuts, shellfish…"),
        ("🏥","Health Insights","0–100 health score, Nutri-Score A→E, ultra-processed markers"),
        ("⚖️","Compare Products","Side-by-side vegan & nutrition comparison"),
        ("🤖","AI Chat","Ask anything about any ingredient"),
        ("👤","Personalization","Diet mode, allergen alerts, health goals"),
        ("📚","History","All past scans with Plotly charts & JSON export"),
    ]
    fc = st.columns(3)
    for i, (icon, title, desc) in enumerate(features):
        with fc[i % 3]:
            st.markdown(
                f'<div class="feat-card" style="margin-bottom:10px">'
                f'<div style="font-size:1.5rem;margin-bottom:5px">{icon}</div>'
                f'<div style="font-weight:600;font-size:0.88rem;margin-bottom:3px;color:{SAGE["charcoal"]}">{title}</div>'
                f'<div style="font-size:0.75rem;color:{SAGE["stone"]};line-height:1.5">{desc}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

# ── Quick actions — 2×2 grid ─────────────────────────────────────────────────
st.markdown(f'<div style="font-size:0.75rem;font-weight:600;color:{SAGE["stone"]};text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px">Quick Actions</div>', unsafe_allow_html=True)
_qa1, _qa2 = st.columns(2)
with _qa1:
    if st.button("📷 Scan Ingredient Label", use_container_width=True, key="home_scan"):
        st.switch_page("pages/1_📷_Scanner.py")
with _qa2:
    if st.button("🔍 Search a Product", use_container_width=True, key="home_search"):
        st.switch_page("pages/2_🔍_Analyzer.py")
_qa3, _qa4 = st.columns(2)
with _qa3:
    if st.button("⚖️ Compare Products", use_container_width=True, key="home_compare"):
        st.switch_page("pages/4_⚖️_Comparison.py")
with _qa4:
    if st.button("🤖 Ask AI Assistant", use_container_width=True, key="home_ai"):
        st.session_state.ai_widget_open = True
        st.rerun()
# ── DEMO MODE ─────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("## 🎯 Live AI Analysis")
st.markdown("Click any product for a live AI analysis:")

DEMOS = [
    {"emoji":"🍫","name":"Nutella","brand":"Ferrero",
     "ingredients":"Sugar, Palm oil, Hazelnuts (13%), Skimmed milk powder (8.7%), Fat-reduced cocoa (7.4%), Emulsifier (Soya lecithin), Vanillin",
     "expected":"Not Vegan","note":"Contains dairy"},
    {"emoji":"🍪","name":"Oreo Original","brand":"Mondelez",
     "ingredients":"Unbleached enriched flour, Sugar, Palm and/or canola oil, Cocoa powder, High fructose corn syrup, Leavening, Salt, Soy lecithin, Vanillin, Chocolate",
     "expected":"Uncertain","note":"Cross-contamination risk"},
    {"emoji":"🥛","name":"Whey Protein","brand":"Optimum Nutrition",
     "ingredients":"Whey protein isolate, Whey protein concentrate, Cocoa powder, Natural and artificial flavors, Soy lecithin, Acesulfame potassium",
     "expected":"Not Vegan","note":"Dairy-derived protein"},
    {"emoji":"🌾","name":"Alpro Oat Milk","brand":"Alpro",
     "ingredients":"Water, Oat (10%), Sunflower oil, Calcium carbonate, Sea salt, Riboflavin B2, Vitamin B12, Vitamin D2, Dipotassium phosphate, Gellan gum",
     "expected":"Vegan","note":"100% plant-based"},
    {"emoji":"🌿","name":"Impossible Burger","brand":"Impossible Foods",
     "ingredients":"Water, Soy protein concentrate, Coconut oil, Sunflower oil, Natural flavors, Potato protein, Methylcellulose, Yeast extract, Soy leghemoglobin, Salt",
     "expected":"Vegan","note":"Certified vegan"},
    {"emoji":"🍦","name":"Ben & Jerry's","brand":"Ben & Jerry's",
     "ingredients":"Cream, Skimmed milk, Sugar, Egg yolk, Fudge brownies (Sugar, Wheat flour, Butter, Cocoa, Eggs, Salt, Vanilla), Guar gum, Carrageenan",
     "expected":"Not Vegan","note":"Dairy + eggs"},
]

sc = {"Not Vegan":"#fde8e5","Vegan":"#e2f0ec","Uncertain":"#fdf3e0"}
tc = {"Not Vegan":"#8b2a1e","Vegan":"#2d5a4a","Uncertain":"#8b6210"}

dcols = st.columns(3)
for i, d in enumerate(DEMOS):
    with dcols[i % 3]:
        exp  = d["expected"]
        ec   = tc.get(exp, "#555")
        emj  = {"Not Vegan":"❌","Vegan":"✅","Uncertain":"⚠️"}.get(exp,"❓")
        active = st.session_state.get("active_demo",{}).get("name") == d["name"]
        border = f'border:2px solid {verdict_color(exp)}' if active else f'border:1px solid {SAGE["pale"]}'
        st.markdown(f"""
        <div class="demo-card" style="{border};border-top:3px solid {ec}">
          <div style="font-size:2rem;margin-bottom:5px">{d['emoji']}</div>
          <div style="font-weight:700;font-size:0.9rem;margin-bottom:2px;color:{SAGE['charcoal']}">{d['name']}</div>
          <div style="font-size:0.7rem;color:{SAGE['stone']};margin-bottom:7px">{d['brand']}</div>
          <div style="font-size:0.78rem;font-weight:700;color:{ec}">{emj} {exp}</div>
          <div style="font-size:0.68rem;color:{SAGE['stone']};margin-top:2px">{d['note']}</div>
        </div>""", unsafe_allow_html=True)
        if st.button(f"Analyze {d['emoji']}", key=f"demo_{i}", use_container_width=True):
            st.session_state["active_demo"] = d

# Run active demo
if "active_demo" in st.session_state:
    d = st.session_state["active_demo"]
    st.markdown(f"---\n## 📋 Live Analysis: {d['emoji']} {d['name']}")
    st.caption(f"Brand: {d['brand']}")
    st.markdown(
        f'<div style="background:{SAGE["offwhite"]};border-radius:10px;padding:0.8rem 1rem;'
        f'font-size:0.83rem;color:{SAGE["stone"]};margin-bottom:1rem;border:1px solid {SAGE["pale"]}">'
        f'<b>Ingredients:</b> {d["ingredients"]}</div>',
        unsafe_allow_html=True,
    )
    with st.spinner("🤖 Running 5-agent analysis…"):
        result = svc.analyze(d["ingredients"], d["name"])
        time.sleep(0.15)
    full_analysis_display(result, {"nutriments": {}, "allergens": [], "nutriscore": ""}, key_suffix="home_demo")
    add_history(d["name"], result.overall_vegan, d["ingredients"], result)

    if st.button("✕ Clear", key="clear_demo"):
        del st.session_state["active_demo"]
        st.rerun()

# ── STATS ─────────────────────────────────────────────────────────────────────
st.markdown("---")
h = st.session_state.history
counts = {}
for item in h:
    counts[item["verdict"]] = counts.get(item["verdict"], 0) + 1

s1, s2, s3, s4 = st.columns(4)
for col, num, lbl, col_hex in [
    (s1, "300+", "Ingredients KB", SAGE["charcoal"]),
    (s2, "3M+",  "Products (OFF)", SAGE["mid"]),
    (s3, "5",    "AI Agents",      SAGE["teal"]),
    (s4, str(len(h)), "Session Scans", SAGE["accent"]),
]:
    with col:
        st.markdown(
            f'<div class="stat-card">'
            f'<div style="font-size:1.7rem;font-weight:700;color:{col_hex}">{num}</div>'
            f'<div style="font-size:0.65rem;color:{SAGE["stone"]};text-transform:uppercase;letter-spacing:0.06em">{lbl}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

# ── FOOTER ────────────────────────────────────────────────────────────────────
st.markdown("---")
_footer_logo_b64 = get_logo_b64("icon")
_footer_logo_display = "inline-block" if _footer_logo_b64 else "none"
st.markdown(
    f'<div style="background:linear-gradient(135deg,{SAGE["darkest"]},{SAGE["dark"]});'
    f'color:white;text-align:center;padding:1.2rem 2rem;border-radius:14px;'
    f'margin-top:0.5rem;font-size:0.82rem">'
    f'<div style="display:flex;align-items:center;justify-content:center;gap:8px;margin-bottom:6px"><img src="data:image/png;base64,{_footer_logo_b64}" style="width:28px;height:28px;border-radius:6px;object-fit:contain;vertical-align:middle;display:{_footer_logo_display}"><span style="font-size:1rem;font-weight:700;line-height:28px">IngreLens AI</span></div>'
    f'<div style="opacity:0.85;margin-bottom:4px;font-weight:500;letter-spacing:0.04em">SCAN, ANALYSE & EAT SMARTER</div>'
    f'<div style="opacity:0.6;font-size:0.72rem">'
    f'Powered by Open Food Facts · ChromaDB · Sentence Transformers · 5 AI Agents · Free Tier'
    f'</div></div>',
    unsafe_allow_html=True,
)
