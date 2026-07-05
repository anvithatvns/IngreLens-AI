"""IngreLens AI — Home · Sage & Stone · Real Logo"""
import streamlit as st, sys, time, base64
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

st.set_page_config(
    page_title="IngreLens AI — Scan, Analyse & Eat Smarter",
    page_icon="assets/logo_square.png", layout="wide", initial_sidebar_state="expanded",
)

from shared_ui import (inject_css, init_state, render_top_nav, render_page_header, add_history,
                        render_verdict_card, render_agent_row, render_metrics,
                        render_health_score, render_nutriscore,
                        render_ingredient_cards, render_allergen_pills,
                        full_analysis_display, get_logo_b64, render_logo_hero,
                        verdict_emoji, verdict_color, SAGE, enter_page,
                        cached_analyze, log_activity, scroll_sequence)
from backend.services.analysis_service import IngredientAnalysisService
from backend.services.product_service import ProductFetchService

inject_css()
init_state()
render_top_nav()
_prev_page = st.session_state.get("_current_page")
enter_page("home")
_fresh_home_arrival = _prev_page != "home"

@st.cache_resource(show_spinner=False)
def get_svc():
    return IngredientAnalysisService(), ProductFetchService()

svc, ps = get_svc()

# ── HOME HERO — premium animated hero (Home only) ─────────────────────────────
render_page_header(
    "🏠", "IngreLens AI: Scan, Analyze & Eat Smarter",
    "AI-powered ingredient intelligence, simplified. Know your ingredients, instantly. Bridging the gap between complex labels and personalized, safer food choices.",
    mega=True,
)

# ── Landing gate — first visit this session shows only the cinematic hero
# above; "Get Started" reveals the dashboard below via session_state (no
# reload, no state reset — sidebar/nav are unaffected either way). ──────────
if "entered_app" not in st.session_state:
    st.session_state.entered_app = False

if not st.session_state.entered_app:
    st.markdown('<div id="il-get-started-anchor"></div>', unsafe_allow_html=True)
    _g1, _g2, _g3 = st.columns([1, 1, 1])
    with _g2:
        if st.button("Get Started", key="get_started_cta", use_container_width=True, type="primary"):
            st.session_state.entered_app = True
            st.session_state["_scroll_to_quick_actions"] = True
            st.rerun()
    if _fresh_home_arrival:
        # Focus the hero first, hold there briefly, then draw the eye down
        # to the Get Started button so it's guaranteed visible on arrival.
        scroll_sequence([("il-hero-anchor", 400), ("il-get-started-anchor", 2500)])
    st.stop()

# ── Quick actions — large square glass cards with transparent line-art icons ──
st.markdown(f'<div id="il-quick-actions-anchor" style="font-size:0.75rem;font-weight:600;color:{SAGE["stone"]};text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px">Quick Actions</div>', unsafe_allow_html=True)

if st.session_state.pop("_scroll_to_quick_actions", False):
    scroll_sequence([("il-quick-actions-anchor", 300)])

_QA_ICON_SCANNER = f'''<svg viewBox="0 0 120 100" width="100%" height="72" style="display:block;margin:0 auto">
  <rect x="20" y="18" width="80" height="64" rx="8" fill="none" stroke="{SAGE['stone']}" stroke-width="4"/>
  <g stroke="{SAGE['charcoal']}" stroke-width="3" opacity="0.75">
    <line x1="34" y1="34" x2="34" y2="66"/><line x1="41" y1="34" x2="41" y2="66"/>
    <line x1="50" y1="34" x2="50" y2="66"/><line x1="55" y1="34" x2="55" y2="66"/>
    <line x1="64" y1="34" x2="64" y2="66"/><line x1="70" y1="34" x2="70" y2="66"/>
    <line x1="78" y1="34" x2="78" y2="66"/><line x1="86" y1="34" x2="86" y2="66"/>
  </g>
  <line x1="24" y1="50" x2="96" y2="50" stroke="{SAGE['accent']}" stroke-width="3" opacity="0.9"/>
</svg>'''

_QA_ICON_SEARCH = f'''<svg viewBox="0 0 120 100" width="100%" height="72" style="display:block;margin:0 auto">
  <circle cx="52" cy="46" r="26" fill="none" stroke="{SAGE['accent']}" stroke-width="5"/>
  <line x1="71" y1="65" x2="92" y2="86" stroke="{SAGE['accent']}" stroke-width="6" stroke-linecap="round"/>
</svg>'''

_QA_ICON_COMPARE = f'''<svg viewBox="0 0 120 100" width="100%" height="72" style="display:block;margin:0 auto">
  <line x1="60" y1="14" x2="60" y2="78" stroke="{SAGE['stone']}" stroke-width="4"/>
  <line x1="24" y1="30" x2="96" y2="30" stroke="{SAGE['stone']}" stroke-width="4"/>
  <path d="M24 30 L14 54 A14 10 0 0 0 34 54 Z" fill="none" stroke="{SAGE['accent']}" stroke-width="3.5"/>
  <path d="M96 30 L86 54 A14 10 0 0 0 106 54 Z" fill="none" stroke="{SAGE['accent']}" stroke-width="3.5"/>
  <line x1="42" y1="82" x2="78" y2="82" stroke="{SAGE['stone']}" stroke-width="5" stroke-linecap="round"/>
</svg>'''

_QA_ICON_BARCODE = f'''<svg viewBox="0 0 120 100" width="100%" height="72" style="display:block;margin:0 auto">
  <rect x="16" y="28" width="88" height="46" rx="8" fill="none" stroke="{SAGE['stone']}" stroke-width="4"/>
  <g fill="none" stroke="{SAGE['accent']}" stroke-width="3">
    <rect x="26" y="38" width="10" height="8" rx="2"/><rect x="42" y="38" width="10" height="8" rx="2"/>
    <rect x="58" y="38" width="10" height="8" rx="2"/><rect x="74" y="38" width="10" height="8" rx="2"/>
    <rect x="26" y="52" width="58" height="8" rx="2"/>
  </g>
</svg>'''

QUICK_ACTIONS = [
    (_QA_ICON_SCANNER, "Scanner", "pages/1_📷_Scanner.py", "qa_scanner"),
    (_QA_ICON_SEARCH, "Search Product", "pages/2_🔍_Analyzer.py", "qa_search"),
    (_QA_ICON_COMPARE, "Compare Products", "pages/4_⚖️_Comparison.py", "qa_compare"),
    (_QA_ICON_BARCODE, "Barcode Lookup", "pages/3_🔢_Barcode_Lookup.py", "qa_barcode"),
]
qa_cols = st.columns(4)
for i, (icon_svg, label, target, key) in enumerate(QUICK_ACTIONS):
    with qa_cols[i]:
        with st.container(key=key):
            st.markdown(icon_svg, unsafe_allow_html=True)
            st.markdown(f'<div class="il-qa-pill">{label}</div>', unsafe_allow_html=True)
            if st.button(label, key=f"btn_{key}", use_container_width=True):
                st.switch_page(target)
# ── DEMO MODE ─────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("## 🎯 Live AI Analysis")
st.markdown("Click any product for a live AI analysis:")

DEMOS = [
    {"emoji":"🍫","name":"Nutella","brand":"Ferrero",
     "ingredients":"Sugar, Palm oil, Hazelnuts (13%), Skimmed milk powder (8.7%), Fat-reduced cocoa (7.4%), Emulsifier (Soya lecithin), Vanillin",
     "expected":"Not Vegan","note":"Contains dairy",
     "barcode":"3017624010701","nutriscore":"E","allergens":["milk","nuts","soy"],
     "nutriments":{"energy":539,"fat":30.9,"sugars":56.3,"protein":6.3,"salt":0.107,"fiber":0}},
    {"emoji":"🍪","name":"Oreo Original","brand":"Mondelez",
     "ingredients":"Unbleached enriched flour, Sugar, Palm and/or canola oil, Cocoa powder, High fructose corn syrup, Leavening, Salt, Soy lecithin, Vanillin, Chocolate",
     "expected":"Uncertain","note":"Cross-contamination risk",
     "barcode":"7622300416981","nutriscore":"E","allergens":["gluten","soy"],
     "nutriments":{"energy":480,"fat":21,"sugars":42,"protein":5,"salt":0.75,"fiber":2}},
    {"emoji":"🥛","name":"Whey Protein","brand":"Optimum Nutrition",
     "ingredients":"Whey protein isolate, Whey protein concentrate, Cocoa powder, Natural and artificial flavors, Soy lecithin, Acesulfame potassium",
     "expected":"Not Vegan","note":"Dairy-derived protein",
     "barcode":"0041570050699","nutriscore":"B","allergens":["milk","soy"],
     "nutriments":{"energy":390,"fat":4.5,"sugars":4,"protein":77,"salt":0.5,"fiber":0}},
    {"emoji":"🌾","name":"Alpro Oat Milk","brand":"Alpro",
     "ingredients":"Water, Oat (10%), Sunflower oil, Calcium carbonate, Sea salt, Riboflavin B2, Vitamin B12, Vitamin D2, Dipotassium phosphate, Gellan gum",
     "expected":"Vegan","note":"100% plant-based",
     "barcode":"5411188131335","nutriscore":"B","allergens":["gluten"],
     "nutriments":{"energy":47,"fat":1.5,"sugars":4,"protein":1,"salt":0.1,"fiber":0.5}},
    {"emoji":"🌿","name":"Impossible Burger","brand":"Impossible Foods",
     "ingredients":"Water, Soy protein concentrate, Coconut oil, Sunflower oil, Natural flavors, Potato protein, Methylcellulose, Yeast extract, Soy leghemoglobin, Salt",
     "expected":"Vegan","note":"Certified vegan",
     "barcode":"0085239026700","nutriscore":"C","allergens":["soy"],
     "nutriments":{"energy":240,"fat":14,"sugars":0,"protein":19,"salt":0.83,"fiber":0}},
    {"emoji":"🍦","name":"Ben & Jerry's","brand":"Ben & Jerry's",
     "ingredients":"Cream, Skimmed milk, Sugar, Egg yolk, Fudge brownies (Sugar, Wheat flour, Butter, Cocoa, Eggs, Salt, Vanilla), Guar gum, Carrageenan",
     "expected":"Not Vegan","note":"Dairy + eggs",
     "barcode":"8714100735688","nutriscore":"E","allergens":["eggs","gluten","milk"],
     "nutriments":{"energy":282,"fat":14.7,"sugars":27,"protein":4.2,"salt":0.18,"fiber":1}},
]

sc = {"Not Vegan":"rgba(229,88,74,0.14)","Vegan":"rgba(23,201,168,0.14)","Uncertain":"rgba(224,171,58,0.14)"}
tc = {"Not Vegan":"#e5584a","Vegan":"#17c9a8","Uncertain":"#e0ab3a"}

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
    demo_product = {
        "name": d["name"], "brand": d.get("brand", ""), "barcode": d.get("barcode"),
        "nutriments": d.get("nutriments", {}), "allergens": d.get("allergens", []),
        "nutriscore": d.get("nutriscore", ""),
    }
    with st.spinner("🤖 Running 5-agent analysis…"):
        result = cached_analyze(svc, d["ingredients"], d["name"], barcode=d.get("barcode"))
        time.sleep(0.15)
    full_analysis_display(result, demo_product, key_suffix="home_demo")
    add_history(d["name"], result.overall_vegan, d["ingredients"], result, barcode=d.get("barcode"))
    log_activity("Live AI Analysis", "Home")

    if st.button("✕ Clear", key="clear_demo"):
        del st.session_state["active_demo"]
        st.rerun()

# ── FOOTER ────────────────────────────────────────────────────────────────────
st.markdown("---")
_footer_logo_b64 = get_logo_b64("icon")
_footer_logo_display = "inline-block" if _footer_logo_b64 else "none"
st.markdown(
    f'<div style="background:linear-gradient(135deg,{SAGE["darkest"]},{SAGE["dark"]});'
    f'color:white;text-align:center;padding:1.2rem 2rem;border-radius:14px;'
    f'margin-top:0.5rem;font-size:0.82rem">'
    f'<div style="display:flex;align-items:center;justify-content:center;gap:10px;margin-bottom:8px">'
    f'<div class="il-logo-wrap" style="display:{_footer_logo_display}"><div class="il-logo-glow" style="inset:-10px"></div>'
    f'<div class="il-logo-glass" style="padding:3px"><img src="data:image/png;base64,{_footer_logo_b64}" style="width:26px;height:26px;object-fit:contain;border-radius:8px;display:block"></div></div>'
    f'<span style="font-size:1.05rem;font-weight:700">IngreLens AI</span></div>'
    f'<div style="opacity:0.85;margin-bottom:4px;font-weight:500;letter-spacing:0.04em">SCAN, ANALYSE & EAT SMARTER</div>'
    f'<div style="opacity:0.6;font-size:0.72rem">'
    f'Powered by Open Food Facts · ChromaDB · Sentence Transformers · 5 AI Agents'
    f'</div></div>',
    unsafe_allow_html=True,
)
