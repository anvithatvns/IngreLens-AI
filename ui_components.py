"""
IngreLens AI — Shared UI utilities for Streamlit pages.
"""
from __future__ import annotations
import streamlit as st
from datetime import datetime


# ── Global CSS ─────────────────────────────────────────────────────────────────
GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
* { font-family: 'Inter', sans-serif; }

/* Verdict cards */
.verdict-vegan    { background:#d8f3dc; border-left:5px solid #2d6a4f; border-radius:12px; padding:1.2rem 1.5rem; margin:0.5rem 0; }
.verdict-notvegan { background:#ffe0e0; border-left:5px solid #c1121f; border-radius:12px; padding:1.2rem 1.5rem; margin:0.5rem 0; }
.verdict-uncertain{ background:#fff3b0; border-left:5px solid #f4a261; border-radius:12px; padding:1.2rem 1.5rem; margin:0.5rem 0; }
.verdict-unknown  { background:#e9ecef; border-left:5px solid #6c757d; border-radius:12px; padding:1.2rem 1.5rem; margin:0.5rem 0; }
.verdict-title    { font-size:1.6rem; font-weight:700; margin:0 0 0.3rem; }
.verdict-sub      { font-size:0.95rem; opacity:0.85; margin:0; }
.verdict-conf     { font-size:0.8rem; font-weight:600; margin-top:0.4rem; }

/* Ingredient pills */
.pill            { display:inline-block; border-radius:99px; padding:3px 12px; font-size:0.82rem; margin:2px; font-weight:500; }
.pill-nonvegan   { background:#ffcccc; color:#7d0000; }
.pill-uncertain  { background:#fff3b0; color:#6b4c00; }
.pill-vegan      { background:#d8f3dc; color:#1a472a; }
.pill-allergen   { background:#ffe0f0; color:#6b0035; border:1px solid #e63946; }
.pill-additive   { background:#e8f4fd; color:#0c447c; }

/* Stat cards */
.metric-card     { background:white; border:1px solid #e9ecef; border-radius:12px; padding:1rem; text-align:center; }
.metric-num      { font-size:1.8rem; font-weight:700; }
.metric-lbl      { font-size:0.78rem; color:#6c757d; margin-top:2px; }

/* Agent badges */
.agent-badge     { display:inline-block; background:#f0f4ff; color:#364fc7; border:1px solid #c5d0fa; border-radius:6px; padding:2px 10px; font-size:0.75rem; font-weight:500; margin:2px; }

/* Section headers */
.section-hdr     { font-size:0.72rem; font-weight:600; letter-spacing:0.08em; text-transform:uppercase; color:#6c757d; margin:1.2rem 0 0.6rem; }

/* Nutri-score display */
.ns-a { background:#1a7a4a; color:white; }
.ns-b { background:#85bb2f; color:white; }
.ns-c { background:#fecb02; color:#333; }
.ns-d { background:#ee8100; color:white; }
.ns-e { background:#c1121f; color:white; }
.ns-badge { display:inline-block; border-radius:8px; padding:6px 20px; font-size:1.4rem; font-weight:700; }

/* Health score bar */
.health-bar-wrap { background:#e9ecef; border-radius:99px; height:12px; margin:0.3rem 0; }
.health-bar      { height:12px; border-radius:99px; transition:width 0.3s; }

/* Comparison table */
.cmp-yes  { color:#2d6a4f; font-weight:600; }
.cmp-no   { color:#c1121f; font-weight:600; }
.cmp-unk  { color:#f4a261; font-weight:600; }

/* Demo chip buttons */
.demo-row { display:flex; flex-wrap:wrap; gap:6px; margin:0.5rem 0 1rem; }
</style>
"""


def inject_css():
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def render_verdict(verdict: str, reason: str, confidence: float = 0.0):
    cls = {
        "Vegan": ("verdict-vegan", "🌱", "VEGAN"),
        "Not Vegan": ("verdict-notvegan", "❌", "NOT VEGAN"),
        "Uncertain": ("verdict-uncertain", "⚠️", "UNCERTAIN"),
    }.get(verdict, ("verdict-unknown", "❓", "UNKNOWN"))

    conf_text = f"Confidence: {confidence:.0%}" if confidence > 0 else ""
    st.markdown(
        f'<div class="{cls[0]}">'
        f'<div class="verdict-title">{cls[1]} {cls[2]}</div>'
        f'<div class="verdict-sub">{reason}</div>'
        f'<div class="verdict-conf">{conf_text}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_agent_badges():
    st.markdown(
        '<span class="agent-badge">🔍 Product Agent</span>'
        '<span class="agent-badge">🧬 Analysis Agent</span>'
        '<span class="agent-badge">🏷️ Classification Agent</span>'
        '<span class="agent-badge">📊 Nutrition Agent</span>'
        '<span class="agent-badge">🤖 AI Analyst Agent</span>',
        unsafe_allow_html=True,
    )
    st.markdown("")


def render_pills(items: list[str], css_class: str):
    if items:
        st.markdown(
            " ".join(f'<span class="pill {css_class}">{i}</span>' for i in items),
            unsafe_allow_html=True,
        )


def render_health_score(score: int):
    color = "#2d6a4f" if score >= 70 else "#f4a261" if score >= 45 else "#c1121f"
    label = "Good" if score >= 70 else "Moderate" if score >= 45 else "Poor"
    st.markdown(
        f'<div class="section-hdr">Health Score</div>'
        f'<div style="display:flex;align-items:center;gap:12px">'
        f'<div style="font-size:1.6rem;font-weight:700;color:{color}">{score}/100</div>'
        f'<div style="font-size:0.85rem;color:{color};font-weight:600">{label}</div>'
        f'</div>'
        f'<div class="health-bar-wrap"><div class="health-bar" style="width:{score}%;background:{color}"></div></div>',
        unsafe_allow_html=True,
    )


def render_nutriscore(ns: str):
    if not ns:
        return
    ns = ns.upper()
    cls = f"ns-{ns.lower()}" if ns in "ABCDE" else ""
    st.markdown(
        f'<div class="section-hdr">Nutri-Score</div>'
        f'<span class="ns-badge {cls}">{ns}</span>',
        unsafe_allow_html=True,
    )


def render_nutrition_table(nutriments: dict):
    if not any(nutriments.values()):
        return
    def fmt(v, unit="g"):
        return f"{float(v):.1f} {unit}" if v is not None else "—"

    rows = [
        ("🔥 Energy", fmt(nutriments.get("energy"), "kcal")),
        ("🫀 Fat", fmt(nutriments.get("fat"))),
        ("↳ Saturated fat", fmt(nutriments.get("saturated_fat"))),
        ("🍬 Sugars", fmt(nutriments.get("sugars"))),
        ("🌾 Carbohydrates", fmt(nutriments.get("carbs"))),
        ("💪 Protein", fmt(nutriments.get("protein"))),
        ("🧂 Salt", fmt(nutriments.get("salt"))),
        ("🌿 Fiber", fmt(nutriments.get("fiber"))),
    ]
    for label, val in rows:
        c1, c2 = st.columns([3, 2])
        c1.caption(label)
        c2.markdown(f"**{val}**")


def init_session_state():
    defaults = {
        "history": [],
        "chat_messages": [],
        "current_result": None,
        "user_prefs": {
            "diet": "None",
            "allergens": [],
            "health_goals": [],
        },
        "compare_results": [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def add_to_history(product_name: str, verdict: str, ingredients: str, result=None):
    entry = {
        "product": product_name,
        "verdict": verdict,
        "ingredients_snippet": ingredients[:80] + "..." if len(ingredients) > 80 else ingredients,
        "time": datetime.now().strftime("%H:%M"),
        "date": datetime.now().strftime("%d %b %Y"),
        "result": result,
    }
    if "history" not in st.session_state:
        st.session_state.history = []
    # Avoid exact duplicates
    st.session_state.history.insert(0, entry)
    if len(st.session_state.history) > 50:
        st.session_state.history = st.session_state.history[:50]


def render_full_result(result, show_nutrition: bool = True):
    """Render a complete analysis result."""
    from ui_components import (render_verdict, render_agent_badges, render_pills,
                                render_health_score, render_nutriscore, render_nutrition_table)

    render_verdict(result.overall_vegan, result.reasoning, result.vegan_confidence)
    render_agent_badges()
    st.markdown("")

    col_a, col_b = st.columns([3, 2])

    with col_a:
        st.markdown('<div class="section-hdr">Ingredient Breakdown</div>', unsafe_allow_html=True)

        nv = [r for r in result.ingredient_results if "non-vegan" in r.vegan_status]
        unc = [r for r in result.ingredient_results if r.vegan_status == "uncertain"]
        ok = [r for r in result.ingredient_results if r.vegan_status == "vegan"]
        veg_only = [r for r in result.ingredient_results if r.vegetarian_status == "vegetarian" and r.vegan_status != "non-vegan"]

        if nv:
            st.markdown("**❌ Non-vegan ingredients:**")
            render_pills([r.name for r in nv], "pill-nonvegan")
        if unc:
            st.markdown("**⚠️ Uncertain ingredients:**")
            render_pills([r.name for r in unc], "pill-uncertain")
        if ok:
            shown = ok[:12]
            st.markdown(f"**✅ Vegan ingredients ({len(ok)}):**")
            extra = f'+{len(ok)-12} more' if len(ok) > 12 else ""
            render_pills([r.name for r in shown] + ([extra] if extra else []), "pill-vegan")

        if result.allergens_detected:
            st.markdown('<div class="section-hdr">⚠️ Allergens Detected</div>', unsafe_allow_html=True)
            render_pills(result.allergens_detected, "pill-allergen")

        if result.health_flags:
            st.markdown('<div class="section-hdr">Health Flags</div>', unsafe_allow_html=True)
            for flag in result.health_flags:
                st.warning(f"⚠️ {flag}")

        if result.recommendations:
            st.markdown('<div class="section-hdr">Recommendations</div>', unsafe_allow_html=True)
            for rec in result.recommendations:
                st.info(f"💡 {rec}")

    with col_b:
        if show_nutrition:
            st.markdown('<div class="section-hdr">Nutrition per 100g</div>', unsafe_allow_html=True)
            render_health_score(result.health_score)

        if result.ultra_processed_markers:
            st.markdown('<div class="section-hdr">Additives Detected</div>', unsafe_allow_html=True)
            render_pills(result.ultra_processed_markers[:6], "pill-additive")

        if result.preservatives:
            st.markdown('<div class="section-hdr">Preservatives</div>', unsafe_allow_html=True)
            render_pills(result.preservatives, "pill-additive")
