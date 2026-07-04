"""IngreLens AI — 🤖 AI Assistant · Sage & Stone"""
import streamlit as st, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from shared_ui import inject_css, init_state, render_sidebar, render_page_header, get_logo_b64, SAGE
from backend.services.llm_service import IngredientAnalystAgent
from backend.services.analysis_service import IngredientAnalysisService

st.set_page_config(page_title="AI Assistant · IngreLens AI", page_icon="🤖", layout="wide")
inject_css(); init_state(); render_sidebar()

@st.cache_resource(show_spinner=False)
def get_agent():
    svc = IngredientAnalysisService()
    return IngredientAnalystAgent(svc), svc
agent, svc = get_agent()

# Logo handled by render_page_header()
render_page_header("🤖", "AI Food Assistant", "Ask anything about ingredients, vegan diets, allergens, or food health")

# ── Suggestion pills (in main area — sidebar stays clean) ─────────────────────
SUGGESTIONS = [
    "Is gelatin vegan?", "Why is honey not vegan?", "What is carmine E120?",
    "Is Nutella vegan?", "Are Oreos vegan?", "Is vitamin D3 vegan?",
    "What is whey protein?", "What is tapioca starch?",
    "Is L-cysteine vegan?", "Is sugar always vegan?",
]
st.markdown(
    f'<div style="font-size:0.7rem;font-weight:600;color:{SAGE["stone"]};'
    f'text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px">'
    f'Suggested questions — click any to ask:</div>',
    unsafe_allow_html=True,
)
# Render as 2 rows of 5 buttons
cols_r1 = st.columns(5)
cols_r2 = st.columns(5)
for i, q in enumerate(SUGGESTIONS):
    col = cols_r1[i] if i < 5 else cols_r2[i - 5]
    with col:
        if st.button(q, key=f"sq_{i}", use_container_width=True):
            st.session_state.chat_messages.append({"role": "user", "content": q})
            with st.spinner("Thinking…"):
                ans = agent.answer(q)
            st.session_state.chat_messages.append({"role": "assistant", "content": ans})
            st.rerun()

# Clear chat button (right-aligned)
_, clear_col = st.columns([5, 1])
with clear_col:
    if st.button("🗑️ Clear chat", use_container_width=True, key="clear_chat"):
        st.session_state.chat_messages = []
        st.rerun()

st.markdown("---")

# ── Initialize welcome message ────────────────────────────────────────────────
if not st.session_state.chat_messages:
    st.session_state.chat_messages = [{"role": "assistant", "content":
        "👋 Hello! I'm your **IngreLens AI Food Assistant**.\n\n"
        "I can help with:\n"
        "- 🌱 **Vegan classification** — Is this ingredient vegan?\n"
        "- ⚠️ **Allergens** — dairy, eggs, gluten, soy, nuts, shellfish\n"
        "- 🔬 **Ingredient explanations** — What is E120, gelatin, casein?\n"
        "- 💡 **Vegan alternatives** — Plant-based swaps\n\n"
        "Try: *'Is gelatin vegan?'* or click a suggestion above!"}]

# ── Chat history ──────────────────────────────────────────────────────────────
for msg in st.session_state.chat_messages:
    with st.chat_message(msg["role"],
                         avatar="assets/logo_square.png" if msg["role"] == "assistant" else "👤"):
        st.markdown(msg["content"])

# ── Analyze specific ingredients panel ───────────────────────────────────────
with st.expander("🧬 Analyze specific ingredients & discuss"):
    ci1, ci2 = st.columns([3, 1])
    with ci1:
        chat_ing = st.text_area(
            "Paste ingredient list:", height=65,
            label_visibility="collapsed",
            placeholder="Sugar, Palm oil, Milk powder, Soy lecithin…",
        )
    with ci2:
        chat_pn = st.text_input(
            "Product name:", label_visibility="collapsed", placeholder="e.g. Nutella"
        )
    if st.button("Analyze & discuss", key="chat_an"):
        if chat_ing:
            r = svc.analyze(chat_ing, chat_pn or "Product")
            ctx = (f"Product: {chat_pn}\nVegan: {r.overall_vegan}\n"
                   f"Non-vegan: {', '.join(r.non_vegan_ingredients) or 'None'}\n"
                   f"Allergens: {', '.join(r.allergens_detected) or 'None'}\n"
                   f"Health: {r.health_score}/100")
            q = f"Please explain the vegan status and health profile of: {chat_ing}"
            st.session_state.chat_messages.append({"role": "user", "content": q})
            ans = agent.answer(q, ctx)
            st.session_state.chat_messages.append({"role": "assistant", "content": ans})
            st.rerun()

# ── Chat input ────────────────────────────────────────────────────────────────
if prompt := st.chat_input("Ask about any ingredient or food question…"):
    st.session_state.chat_messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)
    with st.chat_message("assistant", avatar="assets/logo_square.png"):
        with st.spinner("Thinking…"):
            ans = agent.answer(prompt)
        st.markdown(ans)
    st.session_state.chat_messages.append({"role": "assistant", "content": ans})
