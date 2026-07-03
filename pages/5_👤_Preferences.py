"""IngreLens AI — 👤 Preferences · Sage & Stone"""
import streamlit as st, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from shared_ui import inject_css, init_state, render_sidebar, render_page_header, get_logo_b64, SAGE, log_activity
from backend.db import database as db

st.set_page_config(page_title="Preferences · IngreLens AI", page_icon="👤", layout="wide")
inject_css(); init_state(); render_sidebar()

render_page_header("👤", "My Preferences", "Personalize IngreLens AI for your diet, allergen concerns, and health goals")

prefs=st.session_state.get("user_prefs",{"diet":"None","allergens":[],"health_goals":[]})
cl,cr=st.columns([3,2])
with cl:
    st.markdown("### 🥗 Diet Mode")
    diets=["None","Vegan","Vegetarian","Pescatarian","Keto","Gluten-Free","Low Sugar","Dairy-Free","Nut-Free","Raw Vegan"]
    diet=st.radio("",options=diets,index=diets.index(prefs.get("diet","None")),horizontal=True)
    st.markdown("---\n### ⚠️ Allergen Alerts")
    al_opts=["Dairy","Eggs","Gluten","Soy","Peanuts","Tree Nuts","Fish","Shellfish","Sesame","Wheat","Mustard","Sulphites"]
    sel_al=st.multiselect("",options=al_opts,default=prefs.get("allergens",[]),label_visibility="collapsed")
    st.markdown("---\n### 🎯 Health Goals")
    g_opts=["Weight loss","Muscle gain","Diabetes-friendly","Heart health","Clean eating","Low sodium","Low sugar","High fiber","Anti-inflammatory"]
    sel_g=st.multiselect("",options=g_opts,default=prefs.get("health_goals",[]),label_visibility="collapsed")
    if st.button("💾 Save Preferences", type="primary"):
        st.session_state.user_prefs={"diet":diet,"allergens":sel_al,"health_goals":sel_g}
        db.save_user_preferences(st.session_state.user_id, diet_type=diet, allergies=sel_al)
        log_activity("Preference Update", "Preferences")
        st.success("✅ Preferences saved!")
with cr:
    st.markdown("### 📋 Your Profile")
    p=st.session_state.get("user_prefs",{})
    st.markdown(f'<div style="background:{SAGE["offwhite"]};border-radius:14px;padding:1.4rem;border:1px solid {SAGE["pale"]}"><div style="margin-bottom:0.8rem"><b>Diet Mode</b><br><span style="color:{SAGE["mid"]};font-weight:600">{p.get("diet","Not set")}</span></div><div style="margin-bottom:0.8rem"><b>Allergen Alerts</b><br>{", ".join(p.get("allergens",[])) or "None"}</div><div><b>Health Goals</b><br>{", ".join(p.get("health_goals",[])) or "None"}</div></div>', unsafe_allow_html=True)
    st.markdown("---\n### 📊 Session Stats")
    h=st.session_state.get("history",[])
    c={}
    for i in h: c[i["verdict"]]=c.get(i["verdict"],0)+1
    s1,s2,s3=st.columns(3)
    s1.metric("Total",len(h)); s2.metric("🌱 Vegan",c.get("Vegan",0)); s3.metric("❌ Not Vegan",c.get("Not Vegan",0))
