# ============================================================
# agents/inventory_agent.py
# Agent 3 — Inventory Intelligence Agent
#
# DATA SOURCE:
#   • In-memory inventory DB (replace with ERP/SAP/DB query
#     in production — see _load_from_db() stub below)
#   • Seeded with numpy for reproducibility; real stock values
#     would come from your warehouse management system.
#
# LLM ROLE:
#   Claude reads inventory health metrics and identifies:
#     - Parts that are critically low (urgent production needed)
#     - Parts with surplus that can be sold immediately
#     - Reorder recommendations with economic order quantities
# ============================================================

import json
from typing import Any

import numpy as np

from config.settings import PARTS_CATALOGUE
from core.base_agent import BaseAgent

SYSTEM_PROMPT = """
You are an inventory manager for a car-parts manufacturing plant.

You receive the current inventory status of all parts including:
  - on_hand: current stock units
  - safety_stock: minimum buffer required
  - reorder_point: level at which to trigger replenishment
  - avg_daily_demand: historical average daily usage
  - days_of_stock (DOS): on_hand / avg_daily_demand
  - unit_cost: cost per unit in INR
  - last_sale_days: days since last sale (recency)

Your task:
1. Identify parts needing URGENT production (DOS < 10) or LOW production (DOS 10–20)
2. Identify surplus parts (DOS > 45) that should be SOLD rather than produced more
3. Calculate economic order quantities for reorder items
4. Assign a production_pressure score per part (−1.0 to +1.0):
   +1.0 = must produce immediately
   0.0  = balanced
   −1.0 = stop production, sell surplus

Return ONLY this JSON:
{
  "production_pressure": {
    "<part_id>": <float -1.0 to 1.0>,
    ...
  },
  "urgent_production": [
    {"part_id": "...", "name": "...", "dos": <float>, "recommended_qty": <int>}
  ],
  "sellable_surplus": [
    {"part_id": "...", "name": "...", "surplus_units": <int>,
     "revenue_potential_inr": <float>, "sell_priority": "HIGH|MEDIUM|LOW"}
  ],
  "reorder_items": [
    {"part_id": "...", "name": "...", "order_qty": <int>,
     "urgency": "CRITICAL|HIGH|MEDIUM", "estimated_cost_inr": <float>}
  ],
  "inventory_health_score": <float 0–100>,
  "total_surplus_value_inr": <float>,
  "total_reorder_cost_inr": <float>
}
"""


class InventoryIntelligenceAgent(BaseAgent):
    name = "InventoryIntelligenceAgent"

    # ── Load inventory ───────────────────────────────────────
    def fetch_data(self) -> dict[str, Any]:
        """
        In production replace with:
            return self._load_from_db()
        or:
            return self._load_from_erp_api()
        """
        inventory = self._generate_seeded_inventory()
        self.logger.info("  Loaded %d parts from inventory store", len(inventory))
        for pid, rec in inventory.items():
            self.logger.info(
                "  %s  on_hand:%d  DOS:%.0fd  status:%s",
                pid, rec["on_hand"], rec["days_of_stock"], rec["status"]
            )
        return {"inventory": inventory, "total_parts": len(inventory)}

    def _generate_seeded_inventory(self) -> dict:
        """
        Deterministic seed=42 inventory.
        In production: replace with DB/ERP call.
        """
        rng = np.random.default_rng(seed=42)
        inventory = {}

        for pid, info in PARTS_CATALOGUE.items():
            on_hand          = int(rng.integers(20, 600))
            safety_stock     = int(rng.integers(30, 100))
            reorder_point    = safety_stock + int(rng.integers(20, 80))
            avg_daily_demand = round(float(rng.uniform(1.5, 25.0)), 2)
            lead_time        = int(info.get("lead_days", 7))
            last_sale_days   = int(rng.integers(0, 45))

            dos = round(on_hand / max(avg_daily_demand, 0.01), 1)

            # Status logic
            if on_hand <= safety_stock:
                status = "CRITICAL"
            elif on_hand <= reorder_point:
                status = "LOW"
            elif dos > 60:
                status = "SURPLUS"
            elif dos > 30:
                status = "ADEQUATE"
            else:
                status = "NORMAL"

            inventory[pid] = {
                **info,
                "part_id":          pid,
                "on_hand":          on_hand,
                "safety_stock":     safety_stock,
                "reorder_point":    reorder_point,
                "avg_daily_demand": avg_daily_demand,
                "lead_time_days":   lead_time,
                "days_of_stock":    dos,
                "last_sale_days":   last_sale_days,
                "status":           status,
                "inventory_value_inr": on_hand * info["unit_cost"],
            }

        return inventory

    # ── Stub for production ERP integration ─────────────────
    def _load_from_db(self) -> dict:
        """
        Example: connect to PostgreSQL / SAP HANA / Oracle ERP
        
        import psycopg2, os
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        cur  = conn.cursor()
        cur.execute(\"\"\"
            SELECT part_id, on_hand, safety_stock, reorder_point,
                   avg_daily_demand, lead_time_days, last_sale_date
            FROM inventory.parts
            WHERE plant_code = 'CHN01'
        \"\"\")
        rows = cur.fetchall()
        ...
        """
        raise NotImplementedError("Connect to your ERP/DB here")

    # ── LLM analysis ─────────────────────────────────────────
    def analyse(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        # Summarise inventory for LLM (avoid token bloat)
        summary = {
            pid: {
                "name":           rec["name"],
                "category":       rec["category"],
                "on_hand":        rec["on_hand"],
                "safety_stock":   rec["safety_stock"],
                "reorder_point":  rec["reorder_point"],
                "avg_daily_demand": rec["avg_daily_demand"],
                "days_of_stock":  rec["days_of_stock"],
                "unit_cost":      rec["unit_cost"],
                "last_sale_days": rec["last_sale_days"],
                "status":         rec["status"],
            }
            for pid, rec in raw_data["inventory"].items()
        }

        user_msg = (
            f"Total parts tracked: {raw_data['total_parts']}\n\n"
            "Inventory status:\n"
            + json.dumps(summary, indent=2)
        )

        result = self.llm.analyse(SYSTEM_PROMPT, user_msg)
        if "error" in result or "production_pressure" not in result:
            self.logger.warning("LLM failed, using rule-based fallback")
            result = self._fallback_analysis(raw_data["inventory"])

        return result

    def _fallback_analysis(self, inventory: dict) -> dict:
        pressure        = {}
        urgent          = []
        surplus         = []
        reorders        = []
        total_surplus_v = 0.0
        total_reorder_c = 0.0

        for pid, rec in inventory.items():
            dos    = rec["days_of_stock"]
            status = rec["status"]

            # Pressure: map DOS to −1..+1
            if dos < 5:        p = 1.0
            elif dos < 10:     p = 0.7
            elif dos < 20:     p = 0.3
            elif dos < 30:     p = 0.0
            elif dos < 60:     p = -0.3
            else:              p = -0.8
            pressure[pid] = round(p, 2)

            if status == "CRITICAL":
                qty = int((rec["reorder_point"] - rec["on_hand"]) * 1.5)
                urgent.append({
                    "part_id": pid, "name": rec["name"],
                    "dos": dos, "recommended_qty": max(1, qty)
                })

            if status in ("CRITICAL", "LOW"):
                qty  = int(rec["reorder_point"] - rec["on_hand"] + rec["safety_stock"])
                cost = qty * rec["unit_cost"]
                total_reorder_c += cost
                reorders.append({
                    "part_id": pid, "name": rec["name"],
                    "order_qty": max(1, qty),
                    "urgency": status,
                    "estimated_cost_inr": round(cost, 2),
                })

            if status == "SURPLUS":
                surplus_units = rec["on_hand"] - rec["reorder_point"]
                rev = surplus_units * rec["unit_cost"] * 0.85  # sell at discount
                total_surplus_v += rev
                surplus.append({
                    "part_id": pid, "name": rec["name"],
                    "surplus_units": surplus_units,
                    "revenue_potential_inr": round(rev, 2),
                    "sell_priority": "HIGH" if rev > 500000 else "MEDIUM",
                })

        # Health score: fewer critical/low = better
        critical_n = sum(1 for r in inventory.values() if r["status"] == "CRITICAL")
        low_n      = sum(1 for r in inventory.values() if r["status"] == "LOW")
        health     = round(100 - critical_n * 15 - low_n * 8, 1)

        return {
            "production_pressure":    pressure,
            "urgent_production":      sorted(urgent, key=lambda x: x["dos"]),
            "sellable_surplus":       sorted(surplus, key=lambda x: x["revenue_potential_inr"], reverse=True),
            "reorder_items":          sorted(reorders, key=lambda x: x["urgency"] == "CRITICAL", reverse=True),
            "inventory_health_score": max(0, health),
            "total_surplus_value_inr": round(total_surplus_v, 2),
            "total_reorder_cost_inr":  round(total_reorder_c, 2),
        }
