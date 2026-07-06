# 🌿 IngreLens AI

> **AI-powered ingredient intelligence platform** — Vegan classification, allergy detection, health insights & conversational AI assistant.

**Tagline:** *SCAN, ANALYSE & EAT SMARTER*

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue)](https://python.org)
[![Streamlit](https://img.shields.io/badge/streamlit-1.35+-red)](https://streamlit.io)
[![Tests](https://img.shields.io/badge/tests-183%20passing-brightgreen)]()
[![MCP](https://img.shields.io/badge/MCP-server-purple)]()
[![Free Tier](https://img.shields.io/badge/cost-free%20tier-green)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🎯 What It Does

IngreLens AI instantly tells you if any food product is **Vegan, Vegetarian, or contains animal ingredients** — with full explanations, allergen detection, and health scoring.

| Feature | Description |
|---|---|
| 🌱 Vegan classification | Vegan / Vegetarian / Eggetarian / Non-Vegetarian / Uncertain, with confidence % |
| ❌ Non-vegan detection | Exact ingredients flagged with reasons |
| ⚠️ Allergy detection | 10 allergen groups: dairy, eggs, gluten, soy, nuts, shellfish… |
| 🏥 Health scoring | 0–100 score + Nutri-Score A→E |
| 🤖 AI assistant | Chat about any ingredient |
| 📷 OCR scanning | Upload product label images |
| 🔍 Product search | 3M+ products via Open Food Facts |
| ⚖️ Comparison | Side-by-side product analysis |
| 👤 Personalization | Diet mode, allergen alerts, health goals |
| 📚 History | All past scans with charts |

---

## 🏗️ Architecture — Coordinator + 5 Specialist Agents

![IngreLens AI architecture diagram — Coordinator Agent routing to 5 specialist agents](assets/architecture_diagram.png)

A single **Coordinator Agent** (`backend/services/coordinator_agent.py`) is
the multi-agent decision point for the whole system: given a barcode, an
image, raw ingredient text, a free-form question, or some combination, it
decides which specialist(s) to invoke and in what order, then returns one
unified result. It is not a fixed pipeline — a barcode request never touches
OCR, a bare question never runs classification. See `CoordinatorAgent.handle()`
for the actual branching logic, and `tests/test_coordinator_agent.py` for
tests that assert on *which* agents ran for a given input, not just the answer.

Two independent callers route through the same Coordinator instead of each
having their own copy of the decision logic: the in-app floating assistant
(`shared_ui.ask_assistant`) and the **MCP server** (`mcp_server.py`), which
exposes it as MCP tools for any MCP-compatible client (Claude Desktop, an
IDE agent, etc.) to call directly — see [MCP Server](#-mcp-server) below.

```
                              User
                               │
                       ┌───────▼────────┐
                       │  Streamlit UI   │  8 pages
                       └───────┬────────┘         MCP Client
                               │                   (Claude Desktop, etc.)
                       ┌───────▼────────┐              │
                       │  🧭 Coordinator │◄─────────────┘
                       │      Agent      │   mcp_server.py
                       └──┬───┬───┬───┬──┘
              ┌───────────┘   │   │   └───────────┐
              ▼               ▼   ▼               ▼
     📦 Product Fetch    👁️ OCR   🏷️ Classification   🤖 AI Analyst
          Agent          Agent        Agent              Agent
              │                          │                  │
       Open Food Facts             Knowledge Base      LLMService
       (3M+ products)             (300+ ingredients)  (rule-based free
                                        │              tier, or OpenAI/
                                   ChromaDB RAG         Anthropic if a
                                 (Vector Search)        key is set)

                       📊 Nutrition Agent — health score, Nutri-Score,
                          portion math & daily-consumption tracking
                          (analysis_service.py + shared_ui.py)
```

**Classification pipeline (5 layers, inside the Classification Agent):**
1. Exact KB match → 2. Alias match → 3. Keyword rules → 4. Vector semantic search → 5. Fallback

---

## 🚀 Quick Start

### Local (Python)

```bash
# 1. Clone
git clone https://github.com/YOUR_USERNAME/ingrelens-ai.git
cd ingrelens-ai

# 2. Install dependencies
pip install -r requirements.txt

# 3. (Optional) Install Tesseract for OCR
# macOS:  brew install tesseract
# Ubuntu: sudo apt-get install tesseract-ocr
# Windows: https://github.com/UB-Mannheim/tesseract/wiki

# 4. (Optional) Add LLM API key for enhanced AI
cp .env.example .env
# Edit .env — set OPENAI_API_KEY or ANTHROPIC_API_KEY

# 5. Run
streamlit run app.py
# Opens at http://localhost:8501
```

### Docker

```bash
docker-compose up --build
# Opens at http://localhost:8501
```

### Streamlit Cloud (Free — 1 click)

1. Push to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. New app → select repo → `app.py`
4. Deploy ✅ *(No API keys needed — works free)*

---

## 🔌 MCP Server

`mcp_server.py` exposes the same Coordinator Agent the Streamlit app uses as
[Model Context Protocol](https://modelcontextprotocol.io) tools, so any
MCP-compatible client can call into IngreLens AI directly — no web UI needed.

```bash
pip install -r requirements.txt   # includes the mcp SDK
python mcp_server.py              # stdio transport
```

**Tools exposed:**

| Tool | Routes to (via the Coordinator) |
|---|---|
| `analyze_ingredients(ingredients_text, product_name)` | Classification Agent |
| `analyze_barcode(barcode)` | Product Fetch Agent → Classification Agent |
| `ask_ingredient_question(question)` | AI Analyst Agent |

**Claude Desktop config** (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "ingrelens-ai": {
      "command": "python",
      "args": ["/absolute/path/to/mcp_server.py"]
    }
  }
}
```

Verify it directly (no MCP client needed) — this is the same call the tests make:
```bash
python -c "
import asyncio
from mcp_server import mcp
print(asyncio.run(mcp.call_tool('analyze_ingredients', {
    'ingredients_text': 'Sugar, Palm oil, Skimmed milk powder',
    'product_name': 'Test',
})))
"
```

---

## 🧪 Running Tests

```bash
# Full test suite (151 tests)
python -m pytest tests/test_complete_suite.py -v

# Original unit tests (26 tests)
python -m pytest tests/test_analysis.py -v

# Coordinator Agent routing tests (6 tests) — asserts on *which* agents ran
python -m pytest tests/test_coordinator_agent.py -v

# Run all tests
python -m pytest tests/ -v

# Demo dataset (62 products, all categories)
python tests/demo_dataset.py

# With coverage report
pip install pytest-cov
python -m pytest tests/ --cov=backend --cov-report=html
```

**Test results (183 passed, 0 failed):**
```
183 passed in ~24s
✅ Knowledge Base: 19 tests
✅ Ingredient Parser: 15 tests
✅ Classification Engine: 23 tests
✅ Analysis Service: 35 tests
✅ Product Service: 12 tests
✅ OCR Service: 5 tests
✅ AI Agent: 8 tests
✅ Demo Scenarios: 10 tests
✅ OCR Input Scenarios: 7 tests
✅ Security & Validation: 8 tests
✅ Performance: 5 tests
✅ Original unit tests (test_analysis.py): 26 tests
✅ Coordinator Agent routing (test_coordinator_agent.py): 6 tests
```

---

## 📁 Project Structure

```
ingrelens-ai/
│
├── app.py                          ← Home page + Quick Actions + demo mode
├── shared_ui.py                    ← Shared CSS, components, helpers,
│                                      floating AI assistant (routes through
│                                      the Coordinator Agent)
├── mcp_server.py                   ← MCP server — exposes the Coordinator
│                                      Agent as MCP tools
│
├── pages/
│   ├── 1_📷_Scanner.py             ← Image OCR + barcode + manual
│   ├── 2_🔍_Analyzer.py            ← Product search (3M+ products)
│   ├── 3_🔢_Barcode_Lookup.py      ← Manual barcode lookup + paste ingredients
│   ├── 4_⚖️_Comparison.py          ← Side-by-side comparison
│   ├── 5_👤_Preferences.py         ← Diet mode, allergens & health profile
│   ├── 6_📚_History.py             ← Scan history + charts
│   ├── 7_ℹ️_About.py               ← About the app
│   └── 8_🍽️_Food_Logs.py          ← Daily nutrition / food log tracking
│
├── backend/
│   └── services/
│       ├── coordinator_agent.py    ← 🧭 Coordinator Agent — routes a
│       │                             request to whichever specialist(s)
│       │                             it actually needs
│       ├── analysis_service.py     ← 🏷️ Classification Agent (5-layer
│       │                             engine) + 📊 Nutrition Agent
│       │                             (health score / Nutri-Score math)
│       ├── llm_service.py          ← 🤖 AI Analyst Agent (free rule-based
│       │                             or OpenAI/Anthropic if a key is set)
│       ├── product_service.py      ← 📦 Product Fetch Agent — Open Food
│       │                             Facts API + demo fallback
│       └── ocr_service.py          ← 👁️ OCR Agent — Tesseract + preprocessing
│
├── knowledge_base/
│   └── ingredients.json            ← 300+ ingredients with vegan status
│
├── config/
│   └── settings.py                 ← All configuration + env vars
│
├── utils/
│   └── logger.py                   ← Centralized logging
│
├── assets/
│   ├── logo_master.png             ← Source logo (official artwork)
│   ├── logo_header.png             ← Page hero header logo
│   ├── logo_sidebar.png            ← Sidebar logo
│   ├── logo_square.png             ← Page icon / favicon / chat avatar
│   └── logo_icon.png               ← Icon variant
│
├── tests/
│   ├── test_complete_suite.py      ← 151 comprehensive tests
│   ├── test_analysis.py            ← 26 unit tests
│   ├── test_coordinator_agent.py   ← 6 Coordinator routing tests
│   └── demo_dataset.py             ← 62 demo ingredient lists
│
├── vector_store/                   ← ChromaDB persists here (auto-created)
├── .streamlit/config.toml          ← Sage & Stone theme
├── .env.example                    ← Environment variable template
├── Dockerfile                      ← Container build
├── docker-compose.yml              ← Multi-container setup
└── requirements.txt                ← All dependencies (incl. MCP SDK)
```

---

## 🎯 Demo Examples (Copy-Paste Ready)

### ❌ Not Vegan — Nutella
```
Sugar, Palm oil, Hazelnuts (13%), Skimmed milk powder (8.7%), Fat-reduced cocoa (7.4%), Emulsifier (Soya lecithin), Vanillin
```

### ❌ Hidden Animal Ingredient — Red Candy (Carmine E120 = crushed insects!)
```
Sugar, Glucose syrup, Citric acid, Natural flavors, Carmine (E120), Beeswax (E901), Carnauba wax
```

### ❌ Surprising — Bread with L-Cysteine (from poultry feathers)
```
Wheat flour, Water, Yeast, Salt, Sugar, Rapeseed oil, Emulsifiers (E471, E481), L-cysteine (E920), Ascorbic acid
```

### ⚠️ Uncertain — Oreo (technically vegan but cross-contamination)
```
Unbleached enriched flour, Sugar, Palm and/or canola oil, Cocoa powder, High fructose corn syrup, Leavening, Salt, Soy lecithin, Vanillin, Chocolate
```

### ✅ Vegan — Plant-Based Protein Bar
```
Pea protein isolate, Dates (30%), Almonds, Cashews, Cocoa powder, Coconut oil, Vanilla extract, Sea salt
```

### 🧪 OCR Noisy Text — Still detects milk!
```
Sug@r, P@lm 0il, H@z3lnuts (13%), Sk1mm3d m1lk p0wd3r (8.7%), F@t-r3duc3d c0c0@, Em5ls1fi3r, V@n1ll1n
```

---

## ⚙️ Configuration

```env
# .env (copy from .env.example)

# Optional LLM providers (free tier works without these)
# OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...

# Feature flags
ENABLE_OCR=true
ENABLE_RAG=true
LOG_LEVEL=INFO
```

**Free tier (no API keys):** Uses rule-based AI engine + ChromaDB + Sentence Transformers. All features work.

---

## 🔧 Tech Stack

| Component | Free Tier Choice | Production Option |
|---|---|---|
| Frontend | Streamlit | React + Next.js |
| AI/LLM | Rule-based engine | GPT-4o-mini / Claude Haiku |
| Embeddings | Sentence Transformers (local) | OpenAI text-embedding-3-small |
| Vector DB | ChromaDB (local) | Pinecone / Weaviate |
| Products DB | Open Food Facts API (free) | Own PostgreSQL mirror |
| OCR | Tesseract (open source) | Google Vision API |
| Deployment | Streamlit Cloud (free) | AWS ECS / Kubernetes |

---

## 📊 Scalability Path

```
Current MVP:                    Production (1M users):
Streamlit                  →   React + Next.js
Python services            →   FastAPI + Kubernetes
ChromaDB (local)           →   Pinecone vector DB
SQLite/session             →   PostgreSQL cluster
No cache                   →   Redis cache
Single server              →   AWS ECS auto-scaling
```

---

## ✅ Key Concepts Demonstrated

Built for the **AI Agents: Intensive Vibe Coding Capstone Project**. Exact
locations for each concept, so nothing has to be hunted down:

| Key Concept | Where | Details |
|---|---|---|
| **Multi-agent system** | `backend/services/coordinator_agent.py` | `CoordinatorAgent.handle()` — real branching logic (not a fixed pipeline), routes to 5 specialists. Tested in `tests/test_coordinator_agent.py` (asserts on which agents ran). |
| **MCP Server** | `mcp_server.py` | 3 tools (`analyze_ingredients`, `analyze_barcode`, `ask_ingredient_question`), all routed through the same Coordinator — see [MCP Server](#-mcp-server) above. |
| **Security features** | `.gitignore`, `.env.example`, `config/settings.py` | Secrets never committed (`.env`, `.streamlit/secrets.toml` gitignored); no hardcoded keys anywhere in the repo; `IngredientParser` bounds/sanitizes untrusted input before classification; graceful fallback (never crashes) when OCR/LLM/network calls fail. |
| **Deployability** | `Dockerfile`, `docker-compose.yml` | One-command local run (`docker-compose up --build`) or free Streamlit Cloud deploy — see [Quick Start](#-quick-start) above. |
| **Agent skills / tool use** | `backend/services/analysis_service.py`, `backend/services/product_service.py` | Each specialist is itself built from composable tools the Coordinator and Classification Agent call: knowledge-base lookup, alias matching, keyword rules, ChromaDB vector search, Open Food Facts API. |

---

## 🔒 Security

- **No secrets in code.** `.env` and `.streamlit/secrets.toml` are gitignored;
  `.env.example` ships with placeholders only, never real keys. LLM API keys
  are entirely optional — the app is fully functional on the free-tier
  rule-based engine with no keys set at all.
- **Untrusted input is bounded, not trusted.** OCR output and pasted
  ingredient text go through `IngredientParser` before classification, which
  strips/normalizes tokens rather than passing raw user text straight into
  any downstream call.
- **Fails safe, not silent-wrong.** Network calls to Open Food Facts, OCR,
  and (optional) LLM providers are all wrapped so a failure falls back to a
  clearly-labeled default rather than crashing or fabricating a confident
  answer — see `fallback_mock_product` in `product_service.py` and the
  rule-based fallback in `llm_service.py`.
- **Least-privilege by design.** The app never asks for or stores payment
  info, and analysis results are explicitly labeled informational — see the
  disclaimer at the bottom of this README and repeated in the app itself.

---

## 🏆 Kaggle Capstone Highlights

- ✅ **Multi-agent system** — 1 Coordinator + 5 specialist agents, with real per-request branching (see Key Concepts table above)
- ✅ **MCP Server** — Coordinator exposed as 3 callable tools for any MCP client
- ✅ **RAG implementation** — ChromaDB + Sentence Transformers
- ✅ **Real-world impact** — Solves genuine vegan/allergy problem
- ✅ **Production quality** — 183 tests passing, Docker, logging, error handling
- ✅ **Free tier** — Zero paid APIs, deployable instantly
- ✅ **3M+ products** — Open Food Facts integration

---

## 📄 License

MIT — free to use, modify, and deploy.

---

*Built as a production-grade AI capstone project. Analysis is informational — always verify with manufacturers for critical dietary needs.*
