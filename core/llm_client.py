# ============================================================
# core/llm_client.py
# Groq LLM client — shared by all agents
# ============================================================

import json
import logging
from typing import Any

from groq import Groq

from config.settings import (
    GROQ_API_KEY,
    LLM_MODEL,
    LLM_MODEL_HEAVY,
    LLM_MAX_TOKENS,
    LLM_TEMPERATURE,
)

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Groq LLM wrapper.
    Each agent calls .analyse() to get structured JSON reasoning.
    """

    def __init__(self):
        # Configure Groq
        self.client = Groq(api_key=GROQ_API_KEY)

    # ── Generic structured call ──────────────────────────────
    def analyse(
        self,
        system_prompt: str,
        user_content: str,
        use_heavy_model: bool = False,
        max_tokens: int = LLM_MAX_TOKENS,
    ) -> dict[str, Any]:

        model_name = LLM_MODEL_HEAVY if use_heavy_model else LLM_MODEL

        full_prompt = (
            system_prompt.strip()
            + "\n\nIMPORTANT: Respond ONLY with a single valid JSON object. "
              "Do not include markdown, explanation, or extra text.\n\n"
            + "User Input:\n"
            + user_content
        )

        try:
            response = self.client.chat.completions.create(
                model=model_name,
                max_tokens=max_tokens,
                temperature=LLM_TEMPERATURE,
                messages=[
                    {
                        "role": "user",
                        "content": full_prompt,
                    }
                ],
            )

            raw = response.choices[0].message.content.strip()

            # Clean markdown if present
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]

            return json.loads(raw)

        except json.JSONDecodeError as e:
            logger.error("LLM JSON parse error: %s | raw=%s", e, raw[:300])
            return {"error": "json_parse_failed", "raw": raw[:500]}

        except Exception as e:
            logger.error("Groq API error: %s", e)
            return {"error": str(e)}

    # ── Executive summary ────────────────────────────────────
    def executive_summary(self, combined_data: dict) -> dict:
        system = """
You are the Chief Operating Officer's AI advisor for an automotive parts
manufacturing plant in Chennai, India.

You receive structured intelligence from four specialised agents:
  1. market_agent   – stock market signals and parts demand factors
  2. env_agent      – weather forecast and disaster alerts
  3. inventory_agent– current stock levels, surplus, and reorder needs
  4. social_agent   – Reddit, HackerNews, news sentiment

Your job: synthesise everything into a concise, actionable executive summary.

Return a JSON object with exactly these keys:
{
  "plant_decision": "RAMP_UP | MAINTAIN | REDUCE | HALT",
  "decision_rationale": "<2-3 sentence explanation>",
  "top_production_priorities": [
    {"part_id": "...", "name": "...", "reason": "..."}
  ],
  "parts_to_reduce": [
    {"part_id": "...", "name": "...", "reason": "..."}
  ],
  "immediate_actions": ["action1", "action2", ...],
  "risk_flags": ["flag1", "flag2", ...],
  "revenue_opportunities": ["opp1", ...],
  "confidence": "HIGH | MEDIUM | LOW",
  "one_liner": "<punchy headline>"
}
        """

        user_msg = f"Agent intelligence data:\n{json.dumps(combined_data, indent=2)}"

        return self.analyse(
            system,
            user_msg,
            use_heavy_model=True,
            max_tokens=1500,
        )


# Singleton
_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    global _client
    if _client is None:
        _client = LLMClient()
    return _client