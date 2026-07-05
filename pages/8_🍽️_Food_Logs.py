"""IngreLens AI — 🍽️ Food Logs · Daily nutrition tracking"""
import streamlit as st, sys
from datetime import date, datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from shared_ui import (inject_css, init_state, render_top_nav, render_page_header,
                        SAGE, log_activity, enter_page, _get_daily_target)
from backend.db import database as db

st.set_page_config(page_title="Food Logs · IngreLens AI", page_icon="🍽️", layout="wide")
inject_css(); init_state(); render_top_nav()
enter_page("food_logs")
log_activity("Food Logs View", "Food Logs")

render_page_header("🍽️", "Food Logs", "Your daily nutrition tracking — see what you've logged and how it adds up")

user_id = st.session_state.get("user_id")

# ── Date picker — defaults to today, lets the user browse past logs ──────────
available_dates = db.get_consumption_dates(user_id)
dc1, dc2 = st.columns([1, 3])
with dc1:
    selected_date = st.date_input("Date", value=date.today(), key="food_log_date")
log_date = selected_date.isoformat()
with dc2:
    if log_date == date.today().isoformat():
        st.caption("Showing **today's** log")
    else:
        st.caption(f"Showing log for **{selected_date.strftime('%B %d, %Y')}**")

entries = db.get_consumption_entries(user_id, log_date)
daily = db.get_daily_consumption(user_id, log_date)
targets = _get_daily_target(user_id)
remaining_cal = max(targets["daily_calories"] - daily["calories"], 0)
pct = min(100, round(daily["calories"] / targets["daily_calories"] * 100)) if targets["daily_calories"] else 0

# ── Daily summary ──────────────────────────────────────────────────────────────
st.markdown("### 📊 Daily Summary")
s1, s2, s3, s4 = st.columns(4)
s1.metric("Total Calories", f'{daily["calories"]:.0f} kcal')
s2.metric("Total Protein", f'{daily["protein"]:.1f}g')
s3.metric("Total Fat", f'{daily["fat"]:.1f}g')
s4.metric("Remaining", f'{remaining_cal:.0f} kcal', f'of {targets["daily_calories"]} target')

st.progress(pct / 100, text=f"{pct}% of daily calorie target used")
st.markdown("")

# ── Entry list — grouped under the selected date ──────────────────────────────
st.markdown(f"### 📋 Entries — {selected_date.strftime('%B %d, %Y')}")

if not entries:
    st.info("📭 No food logged for this date yet. Analyze a product and use **✅ Check Daily Consumption** to add one.")
else:
    for e in entries:
        try:
            t = datetime.fromisoformat(e["timestamp"]).strftime("%I:%M %p")
        except (ValueError, TypeError):
            t = ""
        qty_label = f'{e["quantity"]:g}{e["unit"]}' if e.get("quantity") and e.get("unit") else ""
        ec1, ec2, ec3 = st.columns([3, 2, 1])
        with ec1:
            st.markdown(f"**{e['product_name']}**")
            st.caption(f"{qty_label} · {t}" if qty_label else t)
        with ec2:
            st.caption(
                f'🔥 {e["calories"]:.0f} kcal · 🥩 {e["protein"]:.1f}g protein · 🧈 {e["fat"]:.1f}g fat'
            )
        with ec3:
            if st.button("🗑️", key=f"del_log_{e['log_id']}", help="Remove this entry"):
                db.delete_consumption_entry(e["log_id"], user_id)
                st.rerun()
        st.divider()
