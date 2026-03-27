# OptiStock AI — Multi-Agent Manufacturing Intelligence System
## Backend v2.0 | Automotive Parts Plant | Chennai, India

---

## Project Structure

```
optistock/
│
├── main.py                        # FastAPI app entry point
├── run_colab.py                   # CLI runner (use in Google Colab)
├── requirements.txt
├── .env.example                   # copy → .env and fill keys
│
├── config/
│   └── settings.py                # all config, API URLs, catalogue, weights
│
├── core/
│   ├── base_agent.py              # abstract BaseAgent all agents extend
│   └── llm_client.py             # Anthropic Claude wrapper (shared)
│
├── agents/
│   ├── market_agent.py            # Agent 1 — Stock market → parts demand
│   ├── env_agent.py               # Agent 2 — Weather + disasters → safety factor
│   ├── inventory_agent.py         # Agent 3 — Inventory health → sell/produce signals
│   ├── social_agent.py            # Agent 4 — Reddit/HN/Wiki → social buzz
│   └── orchestrator_agent.py      # Agent 5 — Combines all → LLM executive summary
│
└── api/
    └── routes.py                  # FastAPI REST endpoints
```

---

## Architecture & Data Flow

```
┌──────────────────────────────────────────────────────────────────┐
│                     OptiStock AI Backend                          │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────┐ │
│  │   Agent 1    │  │   Agent 2    │  │   Agent 3    │  │ Ag.4 │ │
│  │   Market     │  │  Environment │  │  Inventory   │  │Social│ │
│  │ Intelligence │  │  & Safety    │  │ Intelligence │  │Pulse │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──┬───┘ │
│         │                 │                  │              │     │
│  Yahoo  │          Open-  │          ERP /   │      Reddit  │     │
│  Finance│          Meteo  │          DB /    │      HN      │     │
│  yf     │          GDACS  │          Seeded  │      Wiki    │     │
│         │                 │          Data    │      News    │     │
│         │ Claude          │ Claude   │ Claude│      │ Claude│     │
│         │ (Haiku)         │ (Haiku)  │(Haiku)│      │(Haiku)│    │
│         └────────┬────────┘          └───────┴──────┘       │    │
│                  │        Parallel execution                 │    │
│                  └──────────────────────────────────────────┘    │
│                                    │                              │
│                          ┌─────────▼──────────┐                  │
│                          │     Agent 5         │                  │
│                          │  Strategic          │                  │
│                          │  Orchestrator       │                  │
│                          │                     │                  │
│                          │  Weighted model:    │                  │
│                          │  Market    35%      │                  │
│                          │  Social    25%      │                  │
│                          │  Inventory 25%      │                  │
│                          │  Env (hard) 15%     │                  │
│                          │                     │                  │
│                          │  Claude Opus        │                  │
│                          │  Executive Summary  │                  │
│                          └─────────┬───────────┘                  │
│                                    │                              │
│                    ┌───────────────▼──────────────┐              │
│                    │    FastAPI REST Response       │              │
│                    │  /api/v1/run                  │              │
│                    │                               │              │
│                    │  • production_plan (per part) │              │
│                    │  • executive_summary          │              │
│                    │  • agent_outputs              │              │
│                    │  • plan_stats                 │              │
│                    └───────────────────────────────┘              │
└──────────────────────────────────────────────────────────────────┘
```

---

## APIs Used (All Free)

| Agent | API | Key Required? | Rate Limit |
|-------|-----|:---:|-----------|
| Market | Yahoo Finance (yfinance) | No | Generous |
| Environment | Open-Meteo weather | No | Unlimited |
| Environment | GDACS disaster alerts | No | Unlimited |
| Social | Reddit public JSON | No | ~60 req/min |
| Social | HackerNews Algolia | No | Unlimited |
| Social | Wikimedia pageviews | No | Unlimited |
| Social | NewsAPI (optional) | Yes (free) | 100 req/day |
| LLM | Anthropic Claude | **Yes** | Pay-as-you-go |

---

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Set your Anthropic API key
```bash
cp .env.example .env
# Edit .env and paste your ANTHROPIC_API_KEY
```

### 3a. Run via CLI (Colab / terminal)
```bash
python run_colab.py                   # full 5-agent pipeline
python run_colab.py --agent market    # single agent test
python run_colab.py --agent env
python run_colab.py --agent inventory
python run_colab.py --agent social
```

### 3b. Run via FastAPI server
```bash
python main.py
# API docs at: http://localhost:8000/docs
```

---

## Google Colab Setup

```python
# Cell 1 — Install
!pip install -q anthropic yfinance requests numpy pandas fastapi uvicorn python-dotenv colorama tabulate

# Cell 2 — Set API key
import os
os.environ["ANTHROPIC_API_KEY"] = "sk-ant-your-key-here"
# OR use Colab secrets:
# from google.colab import userdata
# os.environ["ANTHROPIC_API_KEY"] = userdata.get("ANTHROPIC_API_KEY")

# Cell 3 — Clone / upload project, then run
%cd optistock
!python run_colab.py
```

---

## REST API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/run` | Run full 5-agent pipeline |
| `GET` | `/api/v1/agents/market` | Market agent only |
| `GET` | `/api/v1/agents/environment` | Environmental agent only |
| `GET` | `/api/v1/agents/inventory` | Inventory agent only |
| `GET` | `/api/v1/agents/social` | Social agent only |
| `GET` | `/api/v1/parts` | List parts catalogue |
| `GET` | `/api/v1/health` | Health + LLM status |

---

## Response Schema (`POST /api/v1/run`)

```json
{
  "metadata": {
    "system": "OptiStock AI v2.0",
    "generated_at": "2025-01-01T08:00:00Z",
    "duration_s": 12.4,
    "plant": "Chennai, India"
  },
  "agent_outputs": {
    "market":    { "elapsed_s": 3.1, "llm_output": { ... } },
    "env":       { "elapsed_s": 1.8, "llm_output": { ... } },
    "inventory": { "elapsed_s": 2.2, "llm_output": { ... } },
    "social":    { "elapsed_s": 4.6, "llm_output": { ... } }
  },
  "production_plan": {
    "ENG-001": {
      "name": "Engine Block 1.5L Petrol",
      "combined_score": 1.2341,
      "rec_daily_qty": 28,
      "priority": "HIGH",
      "mkt_factor": 1.12,
      "social_factor": 1.08,
      "inv_factor": 1.40,
      "env_factor": 0.92
    }
  },
  "executive_summary": {
    "plant_decision": "RAMP_UP",
    "decision_rationale": "Strong EV sector momentum ...",
    "top_production_priorities": [ ... ],
    "parts_to_reduce": [ ... ],
    "immediate_actions": [ ... ],
    "risk_flags": [ ... ],
    "revenue_opportunities": [ ... ],
    "confidence": "HIGH",
    "one_liner": "Surge EV electronics output; sell suspension surplus now."
  },
  "plan_stats": {
    "high_priority_parts": 5,
    "medium_priority_parts": 7,
    "low_priority_parts": 3,
    "total_rec_daily_units": 342
  }
}
```

---

## Replacing Simulated Data with Real Data

### Inventory (Agent 3)
Replace `_generate_seeded_inventory()` with your ERP query:
```python
# PostgreSQL / SAP / Oracle / any DB
def _load_from_db(self):
    import psycopg2
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cur  = conn.cursor()
    cur.execute("SELECT part_id, on_hand, ... FROM inventory.parts")
    ...
```

### Social (Agent 4)
For authenticated Reddit (higher rate limits):
```python
import praw
reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent="OptiStockAI/2.0"
)
```

### News (Agent 4)
Register free at https://newsapi.org → set `NEWSAPI_KEY` in `.env`

---

## LLM Cost Estimate

| Operation | Model | Tokens | Est. Cost |
|-----------|-------|--------|-----------|
| Market analysis | claude-3-5-haiku | ~1500 | ~$0.001 |
| Env analysis | claude-3-5-haiku | ~1200 | ~$0.001 |
| Inventory analysis | claude-3-5-haiku | ~2000 | ~$0.002 |
| Social analysis | claude-3-5-haiku | ~1800 | ~$0.002 |
| Executive summary | claude-opus-4 | ~3000 | ~$0.045 |
| **Total per run** | | | **~$0.05** |

Runs every 15 min: ~$5/day · Runs every hour: ~$1.25/day

---

## Production Hardening Checklist

- [ ] Replace seeded inventory with real DB/ERP connection
- [ ] Add Redis caching (15 min TTL) to avoid redundant API calls
- [ ] Add authentication to FastAPI routes (API keys / JWT)
- [ ] Set up scheduled runs (APScheduler / Celery beat / cron)
- [ ] Add Prometheus metrics endpoint
- [ ] Tighten CORS `allow_origins` to your frontend domain
- [ ] Store reports in PostgreSQL for historical trending
- [ ] Add alerting (Slack / email) for CRITICAL decisions
