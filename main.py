# ============================================================
# main.py  — FastAPI application entry point
# ============================================================

import logging
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import API_HOST, API_PORT, API_PREFIX, API_RELOAD, LOG_FORMAT, LOG_LEVEL
from api.routes import router

# ── Logging setup ────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format=LOG_FORMAT,
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


# ── App lifecycle ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀  OptiStock AI backend starting up")
    yield
    logger.info("🛑  OptiStock AI backend shutting down")


# ── FastAPI app ───────────────────────────────────────────────
app = FastAPI(
    title="OptiStock AI — Multi-Agent Manufacturing Intelligence",
    description=(
        "Five specialised AI agents collaborate to produce an optimal "
        "daily production plan for an automotive parts plant in Chennai."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix=API_PREFIX, tags=["OptiStock"])


# ── Dev entry point ───────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=API_HOST,
        port=API_PORT,
        reload=API_RELOAD,
        log_level=LOG_LEVEL.lower(),
    )
