# ============================================================
# config/settings.py
# Central configuration for OptiStock AI Backend
# ============================================================

import os
from pathlib import Path
from dotenv import load_dotenv

# ── Base Directory ──────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

# 🔥 FORCE load .env from project root (VERY IMPORTANT)
env_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=env_path)

# ── LLM (Groq) ──────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# 🔥 Fail fast if key missing (prevents silent bugs)
if not GROQ_API_KEY:
    raise ValueError("❌ GROQ_API_KEY not found. Check your .env file")

LLM_MODEL = "llama-3.1-8b-instant"         # Fast, for agent analysis
LLM_MODEL_HEAVY = "llama-3.1-8b-instant"    # For executive summary
LLM_MAX_TOKENS = 2048
LLM_TEMPERATURE = 0.2

# ── FastAPI Server ──────────────────────────────────────────
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", 8000))
API_RELOAD = os.getenv("API_RELOAD", "true").lower() == "true"
API_PREFIX = "/api/v1"

# ── Plant Location ──────────────────────────────────────────
PLANT_LATITUDE = 13.0827
PLANT_LONGITUDE = 80.2707
PLANT_CITY = "Chennai"
PLANT_COUNTRY = "India"
PLANT_TIMEZONE = "Asia/Kolkata"

# ── Production Capacity ─────────────────────────────────────
MAX_DAILY_UNITS = 500
BASE_DAILY_UNITS = 350
SHIFT_HOURS = 16

# ── External APIs ───────────────────────────────────────────
WEATHER_API_URL = "https://api.open-meteo.com/v1/forecast"
GDACS_RSS_URL = "https://www.gdacs.org/xml/rss.xml"
REDDIT_BASE_URL = "https://www.reddit.com"
HN_API_URL = "https://hn.algolia.com/api/v1/search"
WIKI_PAGEVIEWS = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article"
NEWSAPI_URL = "https://newsapi.org/v2/everything"
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")

# ── Yahoo Finance Stocks ────────────────────────────────────
AUTO_STOCKS = {
    "TATAMOTORS.NS": "Tata Motors",
    "M&M.NS": "Mahindra & Mahindra",
    "MARUTI.NS": "Maruti Suzuki",
    "BOSCHLTD.NS": "Bosch India",
    "TSLA": "Tesla",
    "TM": "Toyota",
}

# ── Parts Catalogue ─────────────────────────────────────────
PARTS_CATALOGUE = {
    "ENG-001": {"name": "Engine Block 1.5L Petrol", "unit_cost": 45000, "category": "Powertrain", "lead_days": 14},
    "ENG-002": {"name": "Turbocharger Assembly", "unit_cost": 28000, "category": "Powertrain", "lead_days": 10},
    "ENG-003": {"name": "Fuel Injector Set 4-cyl", "unit_cost": 8500, "category": "Powertrain", "lead_days": 7},
    "TRN-001": {"name": "Manual Gearbox 5-speed", "unit_cost": 32000, "category": "Transmission", "lead_days": 18},
    "TRN-002": {"name": "CVT Transmission Unit", "unit_cost": 55000, "category": "Transmission", "lead_days": 21},
    "SUS-001": {"name": "MacPherson Strut Assembly", "unit_cost": 6200, "category": "Suspension", "lead_days": 5},
    "SUS-002": {"name": "Anti-Roll Bar Kit", "unit_cost": 3800, "category": "Suspension", "lead_days": 4},
    "BRK-001": {"name": "Disc Brake Rotor Front Pair", "unit_cost": 4500, "category": "Brakes", "lead_days": 3},
    "BRK-002": {"name": "ABS Sensor Module", "unit_cost": 7200, "category": "Brakes", "lead_days": 6},
    "ELE-001": {"name": "ECU Engine Control Unit", "unit_cost": 18500, "category": "Electronics", "lead_days": 9},
    "ELE-002": {"name": "ADAS Camera Module", "unit_cost": 22000, "category": "Electronics", "lead_days": 12},
    "ELE-003": {"name": "Battery Management System", "unit_cost": 35000, "category": "Electronics", "lead_days": 15},
    "EXH-001": {"name": "Catalytic Converter", "unit_cost": 9800, "category": "Exhaust", "lead_days": 6},
    "COO-001": {"name": "Radiator Assembly", "unit_cost": 5500, "category": "Cooling", "lead_days": 5},
    "STR-001": {"name": "Power Steering Rack", "unit_cost": 12000, "category": "Steering", "lead_days": 8},
}

# ── Agent Weights ───────────────────────────────────────────
AGENT_WEIGHTS = {
    "market": 0.35,
    "social": 0.25,
    "inventory": 0.25,
    "env": 0.15,
}

# ── Redis ───────────────────────────────────────────────────
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CACHE_TTL_SECONDS = 900

# ── Logging ─────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

# 🔍 Debug print
print("✅ Groq Key Loaded:", GROQ_API_KEY[:10], "...")