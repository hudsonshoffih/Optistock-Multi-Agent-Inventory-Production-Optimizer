# ============================================================
# api/routes.py
# FastAPI REST endpoints
# ============================================================

import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from utils.output_formatter import format_and_save_report

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Response models ──────────────────────────────────────────
class RunResponse(BaseModel):
    status:  str
    message: str
    data:    dict[str, Any] = {}


class FormattedResponse(BaseModel):
    status: str
    message: str
    console_output: str
    json_report: dict[str, Any]
    executive_summary: str
    saved_files: dict[str, str]


# ── Full pipeline (raw JSON) ─────────────────────────────────────────────
@router.post("/run", response_model=RunResponse, summary="Run full 5-agent pipeline (JSON)")
async def run_full_pipeline():
    """
    Executes all 5 agents and returns the complete production plan
    with executive summary (raw JSON format).
    """
    from agents.orchestrator_agent import StrategicOrchestrator
    try:
        orch   = StrategicOrchestrator()
        result = orch.run()
        return RunResponse(
            status="success",
            message="Full pipeline completed",
            data=result,
        )
    except Exception as exc:
        logger.exception("Pipeline error")
        raise HTTPException(status_code=500, detail=str(exc))


# ── Full pipeline (formatted with reports) ─────────────────────────────────────────────
@router.post("/run/formatted", response_model=FormattedResponse, summary="Run full pipeline (formatted reports)")
async def run_full_pipeline_formatted():
    """
    Executes all 5 agents and returns formatted output:
    - Beautiful ASCII console output
    - Clean executive summary
    - Structured JSON report
    - Saves all reports to disk
    """
    from agents.orchestrator_agent import StrategicOrchestrator
    try:
        # Run pipeline
        orch = StrategicOrchestrator()
        raw_result = orch.run()
        
        # Format and save
        output = format_and_save_report(raw_result)
        formatted = output["formatted_output"]
        files = output["saved_files"]
        
        return FormattedResponse(
            status="success",
            message="Pipeline completed and formatted",
            console_output=formatted["console_output"],
            json_report=formatted["json_report"],
            executive_summary=formatted["executive_summary"],
            saved_files=files,
        )
    except Exception as exc:
        logger.exception("Pipeline error")
        raise HTTPException(status_code=500, detail=str(exc))


# ── Individual agent endpoints ────────────────────────────────
@router.get("/agents/market", summary="Run Market Intelligence Agent only")
async def run_market_agent():
    from agents.market_agent import MarketIntelligenceAgent
    try:
        return MarketIntelligenceAgent().run()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/agents/environment", summary="Run Environmental Safety Agent only")
async def run_env_agent():
    from agents.env_agent import EnvironmentalSafetyAgent
    try:
        return EnvironmentalSafetyAgent().run()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/agents/inventory", summary="Run Inventory Intelligence Agent only")
async def run_inventory_agent():
    from agents.inventory_agent import InventoryIntelligenceAgent
    try:
        return InventoryIntelligenceAgent().run()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/agents/social", summary="Run Social Pulse Agent only")
async def run_social_agent():
    from agents.social_agent import SocialPulseAgent
    try:
        return SocialPulseAgent().run()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── Utility endpoints ─────────────────────────────────────────
@router.get("/parts", summary="List all parts in catalogue")
async def list_parts():
    from config.settings import PARTS_CATALOGUE
    return {"parts": PARTS_CATALOGUE, "total": len(PARTS_CATALOGUE)}


@router.get("/health", summary="Health check")
async def health():
    from config.settings import ANTHROPIC_API_KEY, LLM_MODEL
    return {
        "status": "ok",
        "llm_model": LLM_MODEL,
        "llm_configured": bool(ANTHROPIC_API_KEY),
    }
