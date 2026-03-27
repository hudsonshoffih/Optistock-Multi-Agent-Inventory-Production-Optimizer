# ============================================================
# agents/env_agent.py
# Agent 2 — Environmental & Safety Agent
#
# DATA SOURCES (all free, no keys):
#   • Open-Meteo API  — 7-day weather forecast
#   • GDACS RSS feed  — global disaster / alert tracker
#   • India IMD proxy via Open-Meteo current conditions
#
# LLM ROLE:
#   Claude interprets weather + disaster data and decides how
#   much to scale back production (0.0 – 1.0 multiplier).
# ============================================================

import json
import xml.etree.ElementTree as ET
from typing import Any

import requests

from config.settings import (
    PLANT_CITY, PLANT_LATITUDE, PLANT_LONGITUDE, PLANT_TIMEZONE,
    WEATHER_API_URL, GDACS_RSS_URL,
)
from core.base_agent import BaseAgent

SYSTEM_PROMPT = """
You are an environmental safety officer for a car-parts manufacturing plant
in Chennai, India.

You receive:
  1. A 7-day weather forecast (temperature, rainfall, wind speed, weather code)
  2. Active global disaster alerts from GDACS

Your task is to determine how safe and efficient it is to run production
over the NEXT 3 DAYS (most critical window).

Return ONLY this JSON:
{
  "production_factor": <float 0.0–1.0>,
  "risk_level": "LOW | MODERATE | HIGH | CRITICAL",
  "risk_summary": "<1-2 sentences summarising the key risks>",
  "active_alerts": ["alert description 1", ...],
  "safety_actions": ["action 1", "action 2", ...],
  "worker_safety_ok": <true|false>,
  "logistics_disruption": <true|false>,
  "forecast_highlights": {
    "max_rain_mm": <float>,
    "max_wind_kmh": <float>,
    "max_temp_c": <float>,
    "worst_condition": "<weather condition string>"
  }
}

Guidelines for production_factor:
  1.00 = full capacity
  0.80 = slight caution (light rain / moderate heat)
  0.60 = reduced (heavy rain / strong wind / heat >40°C)
  0.40 = severely reduced (extreme storm / red disaster alert)
  0.20 = skeleton crew only (cyclone / flood threat)
  0.00 = halt production (direct life-threatening conditions)
"""


class EnvironmentalSafetyAgent(BaseAgent):
    name = "EnvironmentalSafetyAgent"

    # ── Fetch weather + disasters ────────────────────────────
    def fetch_data(self) -> dict[str, Any]:
        weather   = self._fetch_weather()
        disasters = self._fetch_disasters()
        return {"weather": weather, "disasters": disasters}

    def _fetch_weather(self) -> dict:
        params = {
            "latitude":   PLANT_LATITUDE,
            "longitude":  PLANT_LONGITUDE,
            "daily": (
                "temperature_2m_max,temperature_2m_min,"
                "precipitation_sum,windspeed_10m_max,"
                "weathercode,precipitation_probability_max"
            ),
            "timezone":       PLANT_TIMEZONE,
            "forecast_days":  7,
        }
        data = self.safe_get(WEATHER_API_URL, params=params)
        if "_error" in data:
            self.logger.warning("Weather API failed: %s", data["_error"])
            return {}

        d     = data.get("daily", {})
        days  = []
        WMO   = {
            0: "Clear Sky", 1: "Mainly Clear", 2: "Partly Cloudy",
            3: "Overcast", 45: "Foggy", 51: "Light Drizzle",
            61: "Slight Rain", 63: "Moderate Rain", 65: "Heavy Rain",
            71: "Light Snow", 80: "Rain Showers", 95: "Thunderstorm",
            96: "Thunderstorm+Hail", 99: "Violent Thunderstorm",
        }
        for i in range(len(d.get("time", []))):
            code = d["weathercode"][i]
            days.append({
                "date":       d["time"][i],
                "condition":  WMO.get(code, f"Code {code}"),
                "wmo_code":   code,
                "max_temp_c": d["temperature_2m_max"][i],
                "min_temp_c": d["temperature_2m_min"][i],
                "rain_mm":    d["precipitation_sum"][i],
                "wind_kmh":   d["windspeed_10m_max"][i],
                "rain_prob":  d["precipitation_probability_max"][i],
            })
            self.logger.info(
                "  %s  %s  rain:%.1fmm  wind:%.0fkm/h  temp:%.0f°C",
                d["time"][i], WMO.get(code, "?"),
                d["precipitation_sum"][i],
                d["windspeed_10m_max"][i],
                d["temperature_2m_max"][i],
            )

        return {"location": f"{PLANT_CITY}, India", "days": days}

    def _fetch_disasters(self) -> list[dict]:
        """Fetch GDACS global disaster RSS and return recent alerts."""
        try:
            r = requests.get(
                GDACS_RSS_URL, timeout=12,
                headers={"User-Agent": "OptiStockAI/2.0"}
            )
            r.raise_for_status()
            root    = ET.fromstring(r.content)
            ns      = {"gdacs": "http://www.gdacs.org"}
            alerts  = []
            for item in root.findall(".//item")[:15]:
                title   = item.findtext("title", "")
                country = item.find("gdacs:country", ns)
                level   = item.find("gdacs:alertlevel", ns)
                alerts.append({
                    "title":   title,
                    "country": country.text if country is not None else "Global",
                    "level":   level.text   if level   is not None else "Green",
                })
                self.logger.info(
                    "  GDACS [%s] %s (%s)",
                    level.text if level is not None else "?",
                    title[:60],
                    country.text if country is not None else "?",
                )
            return alerts
        except Exception as exc:
            self.logger.warning("GDACS fetch failed: %s", exc)
            return []

    # ── LLM analysis ─────────────────────────────────────────
    def analyse(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        user_msg = (
            f"Plant location: {PLANT_CITY}, India\n\n"
            "7-day weather forecast:\n"
            + json.dumps(raw_data["weather"].get("days", [])[:7], indent=2)
            + "\n\nActive disaster alerts:\n"
            + json.dumps(raw_data["disasters"], indent=2)
        )
        result = self.llm.analyse(SYSTEM_PROMPT, user_msg)

        if "error" in result or "production_factor" not in result:
            self.logger.warning("LLM failed, using rule-based fallback")
            result = self._fallback_impact(raw_data)

        return result

    def _fallback_impact(self, raw_data: dict) -> dict:
        days      = raw_data.get("weather", {}).get("days", [])[:3]
        disasters = raw_data.get("disasters", [])

        factor  = 1.0
        alerts  = []
        max_rain = max((d["rain_mm"] for d in days), default=0)
        max_wind = max((d["wind_kmh"] for d in days), default=0)
        max_temp = max((d["max_temp_c"] for d in days), default=30)

        india_red = any(
            "India" in a.get("country","") and a.get("level") == "Red"
            for a in disasters
        )

        if india_red:
            factor -= 0.40
            alerts.append("Red disaster alert for India")
        if max_rain > 60:
            factor -= 0.35; alerts.append(f"Extreme rain {max_rain:.0f}mm")
        elif max_rain > 30:
            factor -= 0.15; alerts.append(f"Heavy rain {max_rain:.0f}mm")
        if max_wind > 70:
            factor -= 0.25; alerts.append(f"Storm winds {max_wind:.0f}km/h")
        elif max_wind > 50:
            factor -= 0.10; alerts.append(f"Strong winds {max_wind:.0f}km/h")
        if max_temp > 42:
            factor -= 0.15; alerts.append(f"Extreme heat {max_temp:.0f}°C")

        factor = round(max(0.0, factor), 2)
        risk   = ("CRITICAL" if factor < 0.40 else
                  "HIGH"     if factor < 0.60 else
                  "MODERATE" if factor < 0.85 else "LOW")

        return {
            "production_factor":     factor,
            "risk_level":            risk,
            "risk_summary":          "; ".join(alerts) or "No significant hazards",
            "active_alerts":         alerts,
            "safety_actions":        ["Monitor conditions every 2h"] if alerts else [],
            "worker_safety_ok":      factor >= 0.4,
            "logistics_disruption":  factor < 0.7,
            "forecast_highlights": {
                "max_rain_mm":    round(max_rain, 1),
                "max_wind_kmh":   round(max_wind, 1),
                "max_temp_c":     round(max_temp, 1),
                "worst_condition":days[0]["condition"] if days else "Unknown",
            },
        }
