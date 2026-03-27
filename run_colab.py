# ============================================================
# run_colab.py
# Standalone CLI runner — use this in Google Colab or terminal
# without needing to start the FastAPI server.
#
# Usage:
#   python run_colab.py                    # full pipeline
#   python run_colab.py --agent market     # single agent
#   python run_colab.py --agent env
#   python run_colab.py --agent inventory
#   python run_colab.py --agent social
# ============================================================

# ── Install block (uncomment in Colab) ──────────────────────
# import subprocess, sys
# subprocess.run([sys.executable, "-m", "pip", "install", "-q",
#     "anthropic", "yfinance", "requests", "numpy", "pandas",
#     "fastapi", "uvicorn", "python-dotenv", "tabulate", "colorama"
# ])

import argparse
import json
import logging
import os
import sys

# Allow imports from project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from colorama import Fore, Style, init
init(autoreset=True)

# ── Load .env if present ─────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass   # dotenv optional

# ── Set API key (Colab: use userdata or direct assignment) ───
# from google.colab import userdata
# os.environ["ANTHROPIC_API_KEY"] = userdata.get("ANTHROPIC_API_KEY")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("OptiStock")


def banner():
    print(f"""
{Fore.CYAN}╔══════════════════════════════════════════════════════════════╗
║        OptiStock AI — Multi-Agent Manufacturing System       ║
║          Automotive Parts Plant  |  Chennai, India           ║
╚══════════════════════════════════════════════════════════════╝{Style.RESET_ALL}
""")


def print_production_plan(plan: dict):
    print(f"\n{Fore.YELLOW}{'─'*72}")
    print(f"  PRODUCTION PLAN — ALL PARTS")
    print(f"{'─'*72}{Style.RESET_ALL}")
    print(f"  {'Part ID':<10} {'Name':<38} {'Score':>7} {'Qty/Day':>8} {'Priority'}")
    print(f"  {'─'*70}")

    for pid, p in sorted(plan.items(), key=lambda x: -x[1]["combined_score"]):
        col = (Fore.GREEN  if p["priority"] == "HIGH"   else
               Fore.RED    if p["priority"] == "LOW"    else
               Fore.YELLOW)
        print(
            f"  {pid:<10} {p['name'][:36]:<38} "
            f"{p['combined_score']:>7.4f} {p['rec_daily_qty']:>8d} "
            f"{col}{p['priority']}{Style.RESET_ALL}"
        )


def print_exec_summary(summary: dict):
    if not summary or "error" in summary:
        print(f"{Fore.RED}  Executive summary unavailable: {summary}{Style.RESET_ALL}")
        return

    decision = summary.get("plant_decision", "UNKNOWN")
    col = (Fore.GREEN  if decision == "RAMP_UP"  else
           Fore.RED    if decision == "HALT"      else
           Fore.YELLOW)

    print(f"\n{Fore.CYAN}{'═'*72}")
    print(f"  EXECUTIVE SUMMARY")
    print(f"{'═'*72}{Style.RESET_ALL}")
    print(f"\n  {Style.BRIGHT}Decision  : {col}{decision}{Style.RESET_ALL}")
    print(f"  {Style.BRIGHT}Confidence: {summary.get('confidence','?')}{Style.RESET_ALL}")
    print(f"\n  Headline  : {summary.get('one_liner','')}")
    print(f"\n  Rationale :\n    {summary.get('decision_rationale','')}")

    if summary.get("top_production_priorities"):
        print(f"\n  {Fore.GREEN}▲ TOP PRODUCTION PRIORITIES:{Style.RESET_ALL}")
        for p in summary["top_production_priorities"][:5]:
            print(f"    • [{p['part_id']}] {p['name']} — {p['reason']}")

    if summary.get("parts_to_reduce"):
        print(f"\n  {Fore.RED}▼ PARTS TO REDUCE:{Style.RESET_ALL}")
        for p in summary["parts_to_reduce"][:3]:
            print(f"    • [{p['part_id']}] {p['name']} — {p['reason']}")

    if summary.get("immediate_actions"):
        print(f"\n  {Fore.YELLOW}⚡ IMMEDIATE ACTIONS:{Style.RESET_ALL}")
        for a in summary["immediate_actions"]:
            print(f"    → {a}")

    if summary.get("risk_flags"):
        print(f"\n  {Fore.RED}⚠  RISK FLAGS:{Style.RESET_ALL}")
        for r in summary["risk_flags"]:
            print(f"    ⚠  {r}")

    if summary.get("revenue_opportunities"):
        print(f"\n  {Fore.CYAN}💰 REVENUE OPPORTUNITIES:{Style.RESET_ALL}")
        for o in summary["revenue_opportunities"]:
            print(f"    💰 {o}")

    print(f"\n{Fore.CYAN}{'═'*72}{Style.RESET_ALL}")


def run_full():
    from agents.orchestrator_agent import StrategicOrchestrator
    orch   = StrategicOrchestrator()
    result = orch.run()

    # Print stats
    meta = result["metadata"]
    stats= result["plan_stats"]
    print(f"\n  ✔  Pipeline completed in {meta['duration_s']:.1f}s")
    print(f"  📦  Parts: {stats['high_priority_parts']} HIGH | "
          f"{stats['medium_priority_parts']} MEDIUM | "
          f"{stats['low_priority_parts']} LOW")
    print(f"  🔧  Total recommended units/day: {stats['total_rec_daily_units']}")

    print_production_plan(result["production_plan"])
    print_exec_summary(result["executive_summary"])

    # Save JSON report
    out_file = "optistock_report.json"
    with open(out_file, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\n  📄  Full report saved → {out_file}")
    return result


def run_single(agent_name: str):
    agents = {
        "market":    ("agents.market_agent",    "MarketIntelligenceAgent"),
        "env":       ("agents.env_agent",        "EnvironmentalSafetyAgent"),
        "inventory": ("agents.inventory_agent",  "InventoryIntelligenceAgent"),
        "social":    ("agents.social_agent",     "SocialPulseAgent"),
    }
    if agent_name not in agents:
        print(f"Unknown agent: {agent_name}. Choose from: {list(agents)}")
        sys.exit(1)

    module_path, class_name = agents[agent_name]
    import importlib
    mod    = importlib.import_module(module_path)
    cls    = getattr(mod, class_name)
    result = cls().run()
    print(json.dumps(result.get("llm_output", result), indent=2, default=str))
    return result


if __name__ == "__main__":
    banner()

    parser = argparse.ArgumentParser(description="OptiStock AI Runner")
    parser.add_argument("--agent", type=str, default=None,
                        help="Run a single agent: market | env | inventory | social")
    args = parser.parse_args()

    if args.agent:
        run_single(args.agent)
    else:
        run_full()
