# ============================================================
# utils/output_formatter.py
# OptiStock AI Output Formatter & Report Generator
# Converts JSON output to beautiful ASCII + JSON reports
# ============================================================

import json
import logging
from datetime import datetime
from typing import Any
from pathlib import Path

logger = logging.getLogger(__name__)


class OptiStockFormatter:
    """Formats OptiStock pipeline output into beautiful reports"""

    def __init__(self):
        self.base_dir = Path(__file__).resolve().parent.parent

    def format_full_report(self, pipeline_data: dict) -> dict:
        """
        Convert pipeline JSON into formatted console + file outputs
        Returns dict with:
          - console_output: formatted ASCII string
          - json_report: clean JSON structure
          - executive_summary: text summary
        """
        metadata = pipeline_data.get("metadata", {})
        agents = pipeline_data.get("agent_outputs", {})
        production_plan = pipeline_data.get("production_plan", {})
        exec_sum = pipeline_data.get("executive_summary", {})

        console = self._build_console_output(
            metadata, agents, production_plan, exec_sum
        )
        json_report = self._build_json_report(pipeline_data)
        text_summary = self._build_text_summary(exec_sum, production_plan)

        return {
            "console_output": console,
            "json_report": json_report,
            "executive_summary": text_summary,
            "raw_data": pipeline_data,
        }

    def _build_console_output(self, metadata: dict, agents: dict, plan: dict, exec_sum: dict) -> str:
        """Build beautiful ASCII console output"""
        lines = []

        # Header
        lines.append("╔══════════════════════════════════════════════════════════╗")
        lines.append("║        OptiStock AI — Multi-Agent Intelligence          ║")
        lines.append("║      Automotive Parts Manufacturing System v2.0         ║")
        lines.append("╚══════════════════════════════════════════════════════════╝")
        lines.append("")
        lines.append(f"  Started: {metadata.get('generated_at', 'N/A')}")
        lines.append(f"  Plant Location: {metadata.get('plant', 'N/A')}")
        lines.append(f"  Duration: {metadata.get('duration_s', 0):.2f}s")
        lines.append("")

        # Agent 1 - Market
        lines.append("─" * 80)
        lines.append("──────────────────────── AGENT 1 — MARKET INTELLIGENCE ─────────────────────────")
        lines.append("─" * 80)
        market_data = agents.get("market", {}).get("llm_output", {})
        if market_data:
            demand_factors = market_data.get("demand_factors", {})
            lines.append("  ▶ Parts Demand Analysis")
            for part_id, factor in list(demand_factors.items())[:5]:
                status = "HIGH" if factor > 1.15 else "STABLE" if factor > 0.85 else "LOW"
                lines.append(f"    ◆ {part_id:10} Demand Factor: {factor:.3f}  ➡ {status}")
            lines.append(f"  ▶ Agent 1 Summary")
            lines.append(f"    ✔ Overall Market Sentiment  : {market_data.get('sector_summary', {}).get('overall_sentiment', 'N/A')}")
        lines.append("")

        # Agent 2 - Environment
        lines.append("─" * 80)
        lines.append("─────────────────────── AGENT 2 — ENVIRONMENTAL & SAFETY ───────────────────────")
        lines.append("─" * 80)
        env_data = agents.get("env", {}).get("llm_output", {})
        if env_data:
            lines.append(f"  ▶ Environmental Status")
            lines.append(f"    ✔ Production Factor: {env_data.get('production_factor', 1.0):.2f}x")
            lines.append(f"    ✔ Risk Level: {env_data.get('risk_level', 'N/A')}")
            lines.append(f"    ✔ {env_data.get('risk_summary', 'N/A')}")
        lines.append("")

        # Agent 3 - Inventory
        lines.append("─" * 80)
        lines.append("─────────────────────── AGENT 3 — INVENTORY INTELLIGENCE ───────────────────────")
        lines.append("─" * 80)
        inv_data = agents.get("inventory", {}).get("llm_output", {})
        if inv_data:
            lines.append(f"  ▶ Inventory Health")
            lines.append(f"    ✔ Health Score: {inv_data.get('inventory_health_score', 0)}/100")
            lines.append(f"    ✔ Total Surplus Value: ₹ {inv_data.get('total_surplus_value_inr', 0):,.0f}")
            lines.append(f"    ✔ Total Reorder Cost: ₹ {inv_data.get('total_reorder_cost_inr', 0):,.0f}")
            
            urgent = inv_data.get("urgent_production", [])
            if urgent:
                lines.append(f"  ▶ Urgent Production Items ({len(urgent)})")
                for item in urgent[:3]:
                    lines.append(f"    ⚠ [{item.get('part_id')}] {item.get('name')} - Qty: {item.get('recommended_qty')}")
            
            surplus = inv_data.get("sellable_surplus", [])
            if surplus:
                lines.append(f"  ▶ Top Sellable Surplus ({len(surplus)} items)")
                for item in surplus[:3]:
                    lines.append(f"    💰 {item.get('name'):40} {item.get('surplus_units'):6} units ₹{item.get('revenue_potential_inr', 0):12,.0f}")
        lines.append("")

        # Agent 4 - Social
        lines.append("─" * 80)
        lines.append("─────────────────── AGENT 4 — SOCIAL PULSE & TREND ANALYSIS ────────────────────")
        lines.append("─" * 80)
        social_data = agents.get("social", {}).get("llm_output", {})
        if social_data:
            buzz = social_data.get("buzz_summary", {})
            lines.append(f"  ▶ Social Intelligence")
            lines.append(f"    ✔ Overall Sentiment: {buzz.get('overall_sentiment', 'N/A')}")
            lines.append(f"    ✔ Buzz Score: {buzz.get('buzz_score', 0)}/100")
            lines.append(f"    ✔ Hottest Category: {social_data.get('hottest_category', 'N/A')}")
        lines.append("")

        # Agent 5 - Executive Summary
        lines.append("═" * 80)
        lines.append("═══════════════════════ EXECUTIVE SUMMARY — OPTISTOCK AI ═════════════════════════")
        lines.append("═" * 80)
        lines.append("")

        if exec_sum and "error" not in exec_sum:
            lines.append(f"  ▶ Plant Decision: {exec_sum.get('plant_decision', 'MAINTAIN')}")
            lines.append(f"  ▶ Rationale: {exec_sum.get('decision_rationale', 'N/A')}")
            lines.append(f"  ▶ Confidence: {exec_sum.get('confidence', 'MEDIUM')}")
            lines.append(f"  ▶ One-liner: {exec_sum.get('one_liner', 'N/A')}")
            lines.append("")
            
            # Top priorities
            priorities = exec_sum.get("top_production_priorities", [])
            if priorities:
                lines.append(f"  TOP 5 PRODUCTION PRIORITIES")
                for i, item in enumerate(priorities[:5], 1):
                    lines.append(f"    {i}. {item.get('name'):40} [{item.get('part_id')}]")
                    lines.append(f"       Reason: {item.get('reason', 'N/A')}")
            
            # Risks
            risks = exec_sum.get("risk_flags", [])
            if risks:
                lines.append("")
                lines.append(f"  🚨 CRITICAL RISK FLAGS ({len(risks)} items)")
                for risk in risks[:5]:
                    lines.append(f"     • {risk}")
            
            # Opportunities
            opps = exec_sum.get("revenue_opportunities", [])
            if opps:
                lines.append("")
                lines.append(f"  💰 REVENUE OPPORTUNITIES ({len(opps)} items)")
                for opp in opps[:5]:
                    lines.append(f"     • {opp}")
        else:
            lines.append("  ⚠ Executive summary pending...")

        lines.append("")
        lines.append("═" * 80)
        lines.append("════════════════════════ REPORT GENERATION COMPLETE ════════════════════════════")
        lines.append("═" * 80)

        return "\n".join(lines)

    def _build_json_report(self, pipeline_data: dict) -> dict:
        """Build clean JSON report structure"""
        return {
            "metadata": pipeline_data.get("metadata", {}),
            "summary": {
                "market": pipeline_data.get("agent_outputs", {}).get("market", {}).get("llm_output", {}),
                "environment": pipeline_data.get("agent_outputs", {}).get("env", {}).get("llm_output", {}),
                "inventory": pipeline_data.get("agent_outputs", {}).get("inventory", {}).get("llm_output", {}),
                "social": pipeline_data.get("agent_outputs", {}).get("social", {}).get("llm_output", {}),
            },
            "production_plan": pipeline_data.get("production_plan", {}),
            "executive_summary": pipeline_data.get("executive_summary", {}),
            "statistics": pipeline_data.get("plan_stats", {}),
        }

    def _build_text_summary(self, exec_sum: dict, plan: dict) -> str:
        """Build plain text executive summary"""
        lines = []
        lines.append("\n" + "=" * 70)
        lines.append(" OPTISTOCK AI — EXECUTIVE SUMMARY REPORT".center(70))
        lines.append("=" * 70 + "\n")

        if exec_sum and "error" not in exec_sum:
            lines.append(f"PLANT DECISION: {exec_sum.get('plant_decision', 'N/A')}")
            lines.append(f"CONFIDENCE: {exec_sum.get('confidence', 'MEDIUM')}\n")
            
            lines.append(f"RATIONALE:")
            lines.append(f"{exec_sum.get('decision_rationale', 'N/A')}\n")
            
            lines.append(f"KEY INSIGHT:")
            lines.append(f"{exec_sum.get('one_liner', 'N/A')}\n")

            # Production Priorities
            priorities = exec_sum.get("top_production_priorities", [])
            if priorities:
                lines.append("TOP PRODUCTION PRIORITIES:")
                for i, item in enumerate(priorities[:5], 1):
                    lines.append(f"  {i}. {item.get('name')}")
                    lines.append(f"     Part ID: {item.get('part_id')}")
                    lines.append(f"     Reason: {item.get('reason')}\n")

            # Risk Management
            risks = exec_sum.get("risk_flags", [])
            if risks:
                lines.append("\nCRITICAL RISK FLAGS:")
                for risk in risks[:5]:
                    lines.append(f"  ⚠ {risk}")

            # Revenue
            opps = exec_sum.get("revenue_opportunities", [])
            if opps:
                lines.append("\nREVENUE OPPORTUNITIES:")
                for opp in opps[:5]:
                    lines.append(f"  💰 {opp}")

            # Parts to Reduce
            reduce = exec_sum.get("parts_to_reduce", [])
            if reduce:
                lines.append("\nPARTS TO REDUCE/SELL:")
                for item in reduce[:3]:
                    lines.append(f"  • {item.get('name')} ({item.get('part_id')})")
                    lines.append(f"    Reason: {item.get('reason')}")

            # Immediate Actions
            actions = exec_sum.get("immediate_actions", [])
            if actions:
                lines.append("\nIMMEDIATE ACTIONS:")
                for action in actions[:5]:
                    lines.append(f"  → {action}")

        lines.append("\n" + "=" * 70)
        return "\n".join(lines)

    def save_reports(self, formatted_data: dict, report_type: str = "full") -> dict:
        """Save formatted reports to disk"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        reports_dir = self.base_dir / "reports"
        reports_dir.mkdir(exist_ok=True)

        output_files = {}

        # Save JSON report
        json_file = reports_dir / f"optistock_report_{timestamp}.json"
        with open(json_file, "w") as f:
            json.dump(formatted_data["json_report"], f, indent=2)
        output_files["json"] = str(json_file)
        logger.info(f"✅ JSON report saved: {json_file}")

        # Save console output
        console_file = reports_dir / f"optistock_console_{timestamp}.txt"
        with open(console_file, "w") as f:
            f.write(formatted_data["console_output"])
        output_files["console"] = str(console_file)
        logger.info(f"✅ Console output saved: {console_file}")

        # Save executive summary
        summary_file = reports_dir / f"optistock_executive_summary_{timestamp}.txt"
        with open(summary_file, "w") as f:
            f.write(formatted_data["executive_summary"])
        output_files["summary"] = str(summary_file)
        logger.info(f"✅ Executive summary saved: {summary_file}")

        return output_files


def format_and_save_report(pipeline_data: dict) -> dict:
    """Convenience function to format and save"""
    formatter = OptiStockFormatter()
    formatted = formatter.format_full_report(pipeline_data)
    files = formatter.save_reports(formatted)
    return {
        "formatted_output": formatted,
        "saved_files": files,
    }
