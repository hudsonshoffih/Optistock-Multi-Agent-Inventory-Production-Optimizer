# ============================================================
# core/base_agent.py
# Abstract base class for all OptiStock agents
# ============================================================

import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from core.llm_client import get_llm_client

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Every agent:
      1. Fetches raw data from its source(s)
      2. Calls Claude to reason over that data
      3. Returns a typed result dict
    """

    name: str = "BaseAgent"

    def __init__(self):
        self.llm    = get_llm_client()
        self.logger = logging.getLogger(self.__class__.__name__)
        self._result: dict[str, Any] = {}

    # ── Must implement ───────────────────────────────────────
    @abstractmethod
    def fetch_data(self) -> dict[str, Any]:
        """Pull raw data from APIs / DB / files."""
        ...

    @abstractmethod
    def analyse(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """Call LLM with agent-specific system prompt and raw data."""
        ...

    # ── Run pipeline ─────────────────────────────────────────
    def run(self) -> dict[str, Any]:
        start = time.perf_counter()
        self.logger.info("▶  %s starting", self.name)

        raw   = self.fetch_data()
        llm_r = self.analyse(raw)

        elapsed = round(time.perf_counter() - start, 2)
        self.logger.info("✔  %s done in %.2fs", self.name, elapsed)

        self._result = {
            "agent":     self.name,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "elapsed_s": elapsed,
            "raw_data":  raw,
            "llm_output":llm_r,
        }
        return self._result

    @property
    def result(self) -> dict[str, Any]:
        return self._result

    # ── Helpers ──────────────────────────────────────────────
    @staticmethod
    def safe_get(url: str, timeout: int = 12, **kwargs) -> dict:
        import requests
        try:
            r = requests.get(
                url, timeout=timeout,
                headers={"User-Agent": "OptiStockAI/2.0"},
                **kwargs,
            )
            r.raise_for_status()
            return r.json()
        except Exception as exc:
            logger.warning("HTTP GET failed: %s — %s", url, exc)
            return {"_error": str(exc)}
