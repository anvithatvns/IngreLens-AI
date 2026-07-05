"""IngreLens AI — ℹ️ About · Platform features overview"""
import streamlit as st, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from shared_ui import inject_css, init_state, render_top_nav, render_page_header, SAGE, enter_page

st.set_page_config(page_title="About · IngreLens AI", page_icon="ℹ️", layout="wide")
inject_css(); init_state(); render_top_nav()
enter_page("about")

render_page_header("", "About IngreLens App",
    "What's inside the platform — scanning, classification, and personalization")

features = [
    ("📷", "Ingredient Scanner", "Upload any food label — OCR extracts and classifies instantly"),
    ("🔍", "Product Search", "Search 3M+ products by name or barcode"),
    ("🧬", "AI Classification", "5-layer pipeline: KB → aliases → keywords → vector → fallback"),
    ("⚠️", "Allergy Detection", "10 allergen groups: dairy, eggs, gluten, soy, nuts, shellfish…"),
    ("🏥", "Health Insights", "0–100 health score, Nutri-Score A→E, ultra-processed markers"),
    ("⚖️", "Compare Products", "Side-by-side vegan & nutrition comparison"),
    ("🤖", "AI Chat", "Ask anything about any ingredient"),
    ("👤", "Personalization", "Diet mode, allergen alerts, health goals"),
    ("📚", "History", "All past scans with Plotly charts & JSON export"),
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
