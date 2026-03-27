# ============================================================
# agents/orchestrator_agent.py
# Agent 5 — Strategic Orchestrator
#
# This agent:
#   1. Runs agents 1–4 in parallel (ThreadPoolExecutor)
#   2. Combines all signals using a weighted scoring model
#   3. Calls Claude (heavy model) to write the executive summary
#   4. Returns a single unified production plan + summary
# ============================================================

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any

from config.settings import AGENT_WEIGHTS, BASE_DAILY_UNITS, PARTS_CATALOGUE
from core.llm_client import get_llm_client

from agents.market_agent    import MarketIntelligenceAgent
from agents.env_agent       import EnvironmentalSafetyAgent
from agents.inventory_agent import InventoryIntelligenceAgent
from agents.social_agent    import SocialPulseAgent

logger = logging.getLogger(__name__)


class StrategicOrchestrator:
    """
    Master orchestrator that:
      - Launches sub-agents in parallel
      - Merges outputs via weighted combination
      - Generates executive summary via LLM
    """

    def __init__(self):
        self.llm = get_llm_client()

    # ── Run all agents in parallel ───────────────────────────
    def run_agents(self) -> dict[str, Any]:
        agents = {
            "market":    MarketIntelligenceAgent(),
            "env":       EnvironmentalSafetyAgent(),
            "inventory": InventoryIntelligenceAgent(),
            "social":    SocialPulseAgent(),
        }

        results     = {}
        llm_outputs = {}

        logger.info("▶  Launching all agents in parallel")
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(agent.run): key
                for key, agent in agents.items()
            }
            for future in as_completed(futures):
                key = futures[future]
                try:
                    result          = future.result()
                    results[key]    = result
                    llm_outputs[key]= result.get("llm_output", {})
                    logger.info("  ✔  %s completed in %.2fs", key, result.get("elapsed_s", 0))
                except Exception as exc:
                    logger.error("  ✖  %s failed: %s", key, exc)
                    results[key]    = {"error": str(exc)}
                    llm_outputs[key]= {}

        return results, llm_outputs

    # ── Merge into production plan ───────────────────────────
    def compute_production_plan(self, llm_outputs: dict) -> dict:
        market_llm  = llm_outputs.get("market",    {})
        env_llm     = llm_outputs.get("env",       {})
        inv_llm     = llm_outputs.get("inventory", {})
        social_llm  = llm_outputs.get("social",    {})

        market_factors = market_llm.get("demand_factors",      {})
        social_signals = social_llm.get("social_signals",      {})
        inv_pressure   = inv_llm.get("production_pressure",    {})
        env_factor     = float(env_llm.get("production_factor", 1.0))

        plan = {}
        base_per_part = BASE_DAILY_UNITS / max(len(PARTS_CATALOGUE), 1)

        for pid, info in PARTS_CATALOGUE.items():
            mkt  = float(market_factors.get(pid, 1.0))
            soc  = float(social_signals.get(pid, 1.0))

            # Inventory pressure: map −1..+1 → 0.5..1.5
            inv_p = float(inv_pressure.get(pid, 0.0))
            inv_f = 1.0 + inv_p * 0.5   # −1→0.5, 0→1.0, +1→1.5

            # Weighted combined signal
            combined = (
                mkt   * AGENT_WEIGHTS["market"]    +
                soc   * AGENT_WEIGHTS["social"]    +
                inv_f * AGENT_WEIGHTS["inventory"] +
                1.0   * AGENT_WEIGHTS["env"]
            )

            # Environment is a hard cap multiplier
            final   = round(combined * env_factor, 4)
            rec_qty = max(0, round(base_per_part * final))

            plan[pid] = {
                "part_id":       pid,
                "name":          info["name"],
                "category":      info["category"],
                "unit_cost":     info["unit_cost"],
                "mkt_factor":    round(mkt, 3),
                "social_factor": round(soc, 3),
                "inv_factor":    round(inv_f, 3),
                "env_factor":    round(env_factor, 3),
                "combined_score":round(final, 4),
                "rec_daily_qty": rec_qty,
                "priority": (
                    "HIGH"   if final > 1.10 else
                    "LOW"    if final < 0.85 else
                    "MEDIUM"
                ),
            }

        return plan

    # ── Full pipeline ─────────────────────────────────────────
    def run(self) -> dict[str, Any]:
        start_ts = datetime.utcnow()

        # Step 1: Run all sub-agents
        agent_results, llm_outputs = self.run_agents()

        # Step 2: Compute production plan
        plan = self.compute_production_plan(llm_outputs)

        # Step 3: Build combined context for executive summary
        combined = {
            "market_analysis":    llm_outputs.get("market", {}),
            "environmental":      llm_outputs.get("env", {}),
            "inventory":          llm_outputs.get("inventory", {}),
            "social_trends":      llm_outputs.get("social", {}),
            "production_plan_top5": sorted(
                plan.values(), key=lambda x: x["combined_score"], reverse=True
            )[:5],
            "env_risk_level":     llm_outputs.get("env", {}).get("risk_level", "UNKNOWN"),
            "total_parts":        len(plan),
        }

        # Step 4: Generate executive summary via Claude (heavy model)
        logger.info("▶  Generating executive summary via Claude")
        exec_summary = self.llm.executive_summary(combined)

        # Step 5: Assemble final output
        end_ts   = datetime.utcnow()
        duration = (end_ts - start_ts).total_seconds()

        return {
            "metadata": {
                "system":       "OptiStock AI v2.0",
                "generated_at": start_ts.isoformat() + "Z",
                "duration_s":   round(duration, 2),
                "plant":        "Chennai, India",
            },
            "agent_outputs": {
                key: {
                    "elapsed_s":  r.get("elapsed_s"),
                    "llm_output": r.get("llm_output", {}),
                    "error":      r.get("error"),
                }
                for key, r in agent_results.items()
            },
            "production_plan":  plan,
            "executive_summary":exec_summary,
            "plan_stats": {
                "high_priority_parts":   sum(1 for p in plan.values() if p["priority"] == "HIGH"),
                "medium_priority_parts": sum(1 for p in plan.values() if p["priority"] == "MEDIUM"),
                "low_priority_parts":    sum(1 for p in plan.values() if p["priority"] == "LOW"),
                "total_rec_daily_units": sum(p["rec_daily_qty"] for p in plan.values()),
            },
        }
