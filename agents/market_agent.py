# ============================================================
# agents/market_agent.py
# Agent 1 — Market Intelligence
#
# DATA SOURCES (all free):
#   • Yahoo Finance via yfinance — live stock prices & momentum
#   • Calculated sector rotation signals
#
# LLM ROLE:
#   Claude reads the stock data and decides which part categories
#   have rising / falling demand based on OEM & EV stock momentum.
# ============================================================

import json
import logging
from typing import Any

from config.settings import AUTO_STOCKS, PARTS_CATALOGUE
from core.base_agent import BaseAgent

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are a market intelligence analyst for an automotive parts manufacturer.

You receive live stock performance data for major automotive OEMs and EV companies.
Your task is to derive DEMAND SIGNALS for each car-part category based on:
  - EV stock momentum   → Electronics, Battery systems demand
  - Traditional OEM momentum → Powertrain, Transmission, Exhaust demand
  - Overall sector trend     → All parts moderate adjustment
  - High trade volume        → Institutional confidence = higher demand signal

For each part_id in the catalogue, output a demand_factor (float):
  > 1.15  = HIGH demand — increase production
  0.85–1.15 = STABLE demand — maintain production  
  < 0.85  = LOW demand — reduce production

Return ONLY this JSON:
{
  "demand_factors": {
    "<part_id>": <float 0.5–2.0>,
    ...
  },
  "sector_summary": {
    "ev_momentum_pct": <float>,
    "oe_momentum_pct": <float>,
    "overall_sentiment": "Bullish | Neutral | Bearish",
    "key_drivers": ["driver1", "driver2"]
  },
  "top_demand_parts": ["part_id1", "part_id2", "part_id3"],
  "low_demand_parts": ["part_id1", "part_id2"]
}
"""


class MarketIntelligenceAgent(BaseAgent):
    name = "MarketIntelligenceAgent"

    # ── Fetch live stock data ────────────────────────────────
    def fetch_data(self) -> dict[str, Any]:
        try:
            import yfinance as yf
        except ImportError:
            self.logger.error("yfinance not installed. Run: pip install yfinance")
            return {"error": "yfinance_missing", "stocks": {}}

        stocks = {}
        for symbol, company in AUTO_STOCKS.items():
            try:
                hist = yf.Ticker(symbol).history(period="1mo", interval="1d")
                if hist.empty:
                    continue

                current    = float(hist["Close"].iloc[-1])
                week_ago   = float(hist["Close"].iloc[-5]) if len(hist) >= 5 else float(hist["Close"].iloc[0])
                month_ago  = float(hist["Close"].iloc[0])
                avg_vol    = int(hist["Volume"].mean())

                week_chg  = (current - week_ago) / week_ago * 100
                month_chg = (current - month_ago) / month_ago * 100
                momentum  = round(week_chg * 3 + month_chg * 1.5, 2)   # composite score

                stocks[symbol] = {
                    "company":     company,
                    "price":       round(current, 2),
                    "week_chg":    round(week_chg, 2),
                    "month_chg":   round(month_chg, 2),
                    "avg_volume":  avg_vol,
                    "momentum":    momentum,
                    "is_ev":       symbol in ("TSLA",),
                }
                self.logger.info(
                    "  %s: %.2f  1W:%+.2f%%  1M:%+.2f%%  mom:%+.2f",
                    symbol, current, week_chg, month_chg, momentum
                )
            except Exception as exc:
                self.logger.warning("  %s skipped: %s", symbol, exc)

        return {
            "stocks":          stocks,
            "parts_catalogue": PARTS_CATALOGUE,
        }

    # ── LLM analysis ─────────────────────────────────────────
    def analyse(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        user_msg = (
            "Stock performance data:\n"
            + json.dumps(raw_data["stocks"], indent=2)
            + "\n\nParts catalogue (part_id → category):\n"
            + json.dumps(
                {k: v["category"] for k, v in raw_data["parts_catalogue"].items()},
                indent=2,
            )
        )
        result = self.llm.analyse(SYSTEM_PROMPT, user_msg)

        # Fallback if LLM fails: compute basic momentum-based factors
        if "error" in result or "demand_factors" not in result:
            self.logger.warning("LLM failed, computing fallback demand factors")
            result = self._fallback_factors(raw_data["stocks"])

        return result

    def _fallback_factors(self, stocks: dict) -> dict:
        """Rule-based fallback when LLM is unavailable."""
        ev_mom  = sum(s["momentum"] for s in stocks.values() if s.get("is_ev"))
        oe_mom  = sum(s["momentum"] for s in stocks.values() if not s.get("is_ev"))
        n_oe    = max(1, sum(1 for s in stocks.values() if not s.get("is_ev")))
        oe_avg  = oe_mom / n_oe

        factors = {}
        for pid, info in PARTS_CATALOGUE.items():
            cat = info["category"]
            if cat == "Electronics":
                f = 1.0 + min(ev_mom / 100 * 0.4, 0.5)
            elif cat in ("Powertrain", "Transmission", "Exhaust"):
                f = 1.0 + min(oe_avg / 100 * 0.35, 0.4)
            else:
                f = 1.0 + min((oe_avg + ev_mom) / 200 * 0.2, 0.3)
            factors[pid] = round(max(0.5, min(2.0, f)), 3)

        return {
            "demand_factors":  factors,
            "sector_summary":  {
                "ev_momentum_pct":    round(ev_mom, 2),
                "oe_momentum_pct":    round(oe_avg, 2),
                "overall_sentiment":  "Bullish" if oe_avg > 2 else ("Bearish" if oe_avg < -2 else "Neutral"),
                "key_drivers":        ["fallback_rule_based"],
            },
            "top_demand_parts": sorted(factors, key=factors.get, reverse=True)[:3],
            "low_demand_parts":  sorted(factors, key=factors.get)[:2],
        }
