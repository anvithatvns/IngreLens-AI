"""IngreLens AI — 📚 History · Fixed View button"""
import streamlit as st, sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from shared_ui import (inject_css, init_state, render_sidebar, render_page_header,
                        verdict_emoji, verdict_color, get_logo_b64,
                        full_analysis_display, SAGE, log_activity)

st.set_page_config(page_title="History · IngreLens AI", page_icon="📚", layout="wide")
inject_css(); init_state(); render_sidebar()
log_activity("History View", "History")

render_page_header("📚", "Scan History", "Review all your previous ingredient analyses and dietary trends")

h = st.session_state.get("history", [])

if not h:
    st.info("📭 No scans yet — go to **Home** and click any demo product to get started!")
    st.stop()

# ── If "View" was clicked, show that item's full result ──────────────────────
# This runs BEFORE the list so it doesn't conflict with list rendering
if "hist_view_item" in st.session_state:
    item = st.session_state["hist_view_item"]
    vc   = verdict_color(item["verdict"])
    emj  = verdict_emoji(item["verdict"])

    st.markdown(f"## 📋 {item['product']}")
    st.markdown(
        f'<div style="background:{vc}22;border-left:4px solid {vc};'
        f'border-radius:10px;padding:12px 16px;margin-bottom:1rem">'
        f'<span style="font-size:1.3rem;font-weight:700;color:{vc}">'
        f'{emj} {item["verdict"]}</span>'
        f'<span style="font-size:0.85rem;color:#555;margin-left:12px">'
        f'{item.get("date","")} {item.get("time","")}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    result = item.get("result")
    if result:
        full_analysis_display(result)
    else:
        snippet = item.get("snippet","")
        if snippet:
            st.markdown(
                f'<div style="background:{SAGE["offwhite"]};border-radius:9px;'
                f'padding:10px 14px;font-size:0.85rem;color:{SAGE["stone"]}">'
                f'<b>Ingredients:</b> {snippet}</div>',
                unsafe_allow_html=True,
            )
        st.info("Full analysis details not available. Re-scan the product to see complete results.")

    if st.button("← Back to History", key="back_to_hist", type="primary"):
        del st.session_state["hist_view_item"]
        st.rerun()

    st.stop()  # Don't render the list while viewing an item

# ── Stats ─────────────────────────────────────────────────────────────────────
counts = {}
for item in h:
    counts[item["verdict"]] = counts.get(item["verdict"], 0) + 1

c1, c2, c3, c4 = st.columns(4)
for col, lbl, val, vc in [
    (c1, "Total Scans",   len(h),                    SAGE["charcoal"]),
    (c2, "🌱 Vegan",      counts.get("Vegan", 0),     SAGE["mid"]),
    (c3, "❌ Not Vegan",  counts.get("Not Vegan", 0), "#b84a3a"),
    (c4, "⚠️ Uncertain",  counts.get("Uncertain", 0), "#c4962a"),
]:
    with col:
        st.markdown(
            f'<div class="stat-card">'
            f'<div style="font-size:1.7rem;font-weight:700;color:{vc}">{val}</div>'
            f'<div style="font-size:0.65rem;color:{SAGE["stone"]};'
            f'text-transform:uppercase;letter-spacing:0.06em">{lbl}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
st.markdown("")

# ── Charts ────────────────────────────────────────────────────────────────────
try:
    import plotly.express as px, pandas as pd
    df = pd.DataFrame(h)
    ch1, ch2 = st.columns(2)
    color_map = {"Vegan": SAGE["mid"], "Not Vegan": "#b84a3a", "Uncertain": "#c4962a"}

    with ch1:
        pie = df["verdict"].value_counts().reset_index()
        pie.columns = ["Verdict", "Count"]
        fig = px.pie(pie, names="Verdict", values="Count", title="Results breakdown",
                     color="Verdict", color_discrete_map=color_map, hole=0.4)
        fig.update_layout(height=250, margin=dict(t=40, b=0, l=0, r=0),
                          paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)

    with ch2:
        df["idx"] = range(len(df))
        vmap = {"Vegan": 3, "Uncertain": 2, "Not Vegan": 1, "Unknown": 0}
        df["score"] = df["verdict"].map(vmap)
        fig2 = px.bar(df, x="idx", y="score", color="verdict", title="Scan timeline",
                      color_discrete_map=color_map, hover_data=["product"])
        fig2.update_yaxes(tickvals=[1, 2, 3], ticktext=["Not Vegan", "Uncertain", "Vegan"])
        fig2.update_layout(height=250, margin=dict(t=40, b=0, l=0, r=0),
                           paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig2, use_container_width=True)
except ImportError:
    st.info("Install plotly for charts: `pip install plotly`")

st.divider()

# ── Filter + Clear ────────────────────────────────────────────────────────────
fc, cc = st.columns([4, 1])
with fc:
    filt = st.selectbox(
        "Filter by verdict", ["All", "Vegan", "Not Vegan", "Uncertain"],
        label_visibility="collapsed", key="hist_filter",
    )
with cc:
    if st.button("🗑️ Clear all", key="clear_hist"):
        st.session_state.history = []
        st.session_state.pop("hist_view_item", None)
        st.rerun()

filtered = h if filt == "All" else [x for x in h if x["verdict"] == filt]

# ── History list ──────────────────────────────────────────────────────────────
for i, item in enumerate(filtered):
    vc  = verdict_color(item["verdict"])
    emj = verdict_emoji(item["verdict"])

    DIET_ICONS  = {"Vegan":"🌱","Vegetarian":"🧀","Eggetarian":"🥚","Non-Vegetarian":"🍖","Uncertain":"⚠️"}
    DIET_COLORS = {"Vegan":"#1e8449","Vegetarian":"#27ae60","Eggetarian":"#e67e22","Non-Vegetarian":"#c0392b","Uncertain":"#f39c12"}
    diet = item.get("diet_category", item.get("verdict",""))
    d_icon  = DIET_ICONS.get(diet, emj)
    d_color = DIET_COLORS.get(diet, vc)
    safe_name = item['product'][:8].replace(' ','_').replace('&','n')

    ha, hb, hc, hd, he = st.columns([3, 2, 2, 1, 1])
    with ha:
        st.markdown(f"**{item['product']}**")
        st.caption(item.get("snippet", ""))
    with hb:
        st.markdown(
            f'<span style="color:{d_color};font-weight:600;font-size:0.88rem">'            f'{d_icon} {diet}</span>',
            unsafe_allow_html=True,
        )
        conf = item.get("confidence", 0)
        hs   = item.get("health_score", 0)
        if conf:
            st.caption(f"Conf: {conf}% · Health: {hs}/100")
    with hc:
        allergens = item.get("allergens", [])
        if allergens:
            st.caption("⚠️ " + ", ".join(allergens[:3]))
        st.caption(f"{item.get('date','')} {item.get('time','')}")
    with hd:
        if st.button("View", key=f"v_{i}_{safe_name}"):
            st.session_state["hist_view_item"] = item
            st.rerun()
    with he:
        if st.button("🗑️", key=f"del_{i}_{safe_name}", help="Remove this entry"):
            try:
                st.session_state.history.remove(item)
            except ValueError:
                pass
            st.rerun()

    st.divider()

# ── Export ────────────────────────────────────────────────────────────────────
if h:
    export = [
        {"product": x["product"], "verdict": x["verdict"],
         "date": x.get("date",""), "time": x.get("time","")}
        for x in h
    ]
    st.download_button(
        "📥 Export History (JSON)",
        data=json.dumps(export, indent=2),
        file_name="ingrelens_history.json",
        mime="application/json",
        key="export_hist",
    )
