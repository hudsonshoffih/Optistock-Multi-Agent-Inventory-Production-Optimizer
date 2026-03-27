# ============================================================
# agents/social_agent.py
# Agent 4 — Social Pulse Agent
#
# DATA SOURCES (all free, no keys required):
#   • Reddit public JSON API — r/cars, r/electricvehicles, r/india
#   • HackerNews Algolia API — automotive industry signals
#   • Wikimedia pageview API — interest proxy for car topics
#   • NewsAPI free tier (optional, 100 req/day) — headlines
#     Set NEWSAPI_KEY in .env for headlines; works without it too.
#
# LLM ROLE:
#   Claude reads social signals and maps public buzz to
#   production demand multipliers per part category.
# ============================================================

import json
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from config.settings import NEWSAPI_KEY, NEWSAPI_URL, HN_API_URL, WIKI_PAGEVIEWS, PARTS_CATALOGUE
from core.base_agent import BaseAgent

SUBREDDITS = ["cars", "electricvehicles", "india", "AutoMechanic", "Chennai"]

KEYWORDS = [
    "electric vehicle", "EV", "SUV", "car shortage", "auto parts",
    "supply chain", "engine", "turbo", "car recall", "fuel price",
    "hybrid car", "car launch", "Tata", "Mahindra", "Maruti",
    "car sales", "automobile", "ADAS", "self driving",
]

WIKI_ARTICLES = [
    "Electric_vehicle", "Sport_utility_vehicle",
    "Automotive_industry_in_India", "Turbocharger",
    "Hybrid_vehicle", "Advanced_driver-assistance_systems",
]

SYSTEM_PROMPT = """
You are a social media and trend analyst for an automotive parts manufacturer.

You receive aggregated data from Reddit, HackerNews, Wikipedia, and news headlines.
Your task is to determine how strong the PUBLIC DEMAND SIGNAL is for each car-part
category based on:
  - Mention frequency and upvotes for automotive keywords
  - Wikipedia page views (interest proxy)
  - News article frequency and sentiment
  - EV vs ICE discussion split (indicates which part categories are trending)

For each part_id in the catalogue, output a social_signal (float):
  > 1.20 = viral buzz — strong demand signal → ramp up production
  1.0–1.20 = positive buzz → moderate increase
  0.90–1.0 = neutral
  < 0.90 = low buzz → hold or reduce

Return ONLY this JSON:
{
  "social_signals": {
    "<part_id>": <float 0.5–1.8>,
    ...
  },
  "buzz_summary": {
    "overall_sentiment": "Positive | Neutral | Negative",
    "buzz_score": <float 0–100>,
    "trending_topics": ["topic1", "topic2"],
    "ev_vs_ice_split_pct": {"ev": <int>, "ice": <int>},
    "top_reddit_mentions": ["keyword1", ...],
    "key_news_themes": ["theme1", ...]
  },
  "hottest_category": "<category name>",
  "coldest_category": "<category name>"
}
"""


class SocialPulseAgent(BaseAgent):
    name = "SocialPulseAgent"

    # ── Fetch all social data ────────────────────────────────
    def fetch_data(self) -> dict[str, Any]:
        reddit   = self._fetch_reddit()
        hn       = self._fetch_hackernews()
        wiki     = self._fetch_wiki_views()
        news     = self._fetch_news()
        return {
            "reddit":   reddit,
            "hackernews": hn,
            "wiki":     wiki,
            "news":     news,
            "parts_catalogue": {k: v["category"] for k, v in PARTS_CATALOGUE.items()},
        }

    # ── Reddit (no auth needed for public hot.json) ──────────
    def _fetch_reddit(self) -> dict:
        mentions    = defaultdict(int)
        total_posts = 0
        sample_posts= []

        for sub in SUBREDDITS:
            url  = f"https://www.reddit.com/r/{sub}/hot.json?limit=30"
            data = self.safe_get(url)
            if "_error" in data or "data" not in data:
                self.logger.warning("  r/%s skipped", sub)
                continue

            posts = data["data"].get("children", [])
            total_posts += len(posts)
            matched = 0

            for p in posts:
                text  = (p["data"].get("title", "") + " " +
                         p["data"].get("selftext", "")).lower()
                score = p["data"].get("score", 0)

                for kw in KEYWORDS:
                    if kw.lower() in text:
                        # Weight by post score (popularity)
                        mentions[kw] += 1 + min(score // 100, 5)

                if any(kw.lower() in text for kw in KEYWORDS):
                    matched += 1
                    if len(sample_posts) < 10:
                        sample_posts.append({
                            "subreddit": sub,
                            "title":     p["data"].get("title", "")[:80],
                            "score":     score,
                        })

            self.logger.info("  r/%-20s %d posts, %d matched", sub, len(posts), matched)
            time.sleep(0.5)   # polite delay

        return {
            "mentions":    dict(sorted(mentions.items(), key=lambda x: -x[1])),
            "total_posts": total_posts,
            "sample_posts":sample_posts,
        }

    # ── HackerNews Algolia API ────────────────────────────────
    def _fetch_hackernews(self) -> list[dict]:
        queries = ["electric vehicle India", "automotive supply chain",
                   "car manufacturing", "EV battery"]
        results = []

        for q in queries:
            data = self.safe_get(HN_API_URL, params={
                "query": q,
                "numericFilters": "created_at_i>1700000000",
                "hitsPerPage": 5,
            })
            if "_error" in data:
                continue
            for hit in data.get("hits", []):
                results.append({
                    "query":    q,
                    "title":    hit.get("title", "")[:80],
                    "points":   hit.get("points", 0),
                    "comments": hit.get("num_comments", 0),
                    "url":      hit.get("url", ""),
                })
            time.sleep(0.3)

        results.sort(key=lambda x: x["points"], reverse=True)
        for r in results[:5]:
            self.logger.info("  HN [%d pts] %s", r["points"], r["title"])
        return results[:10]

    # ── Wikipedia page views ──────────────────────────────────
    def _fetch_wiki_views(self) -> dict:
        today  = datetime.utcnow()
        start  = (today - timedelta(days=30)).strftime("%Y%m%d")
        end    = today.strftime("%Y%m%d")
        views  = {}

        for article in WIKI_ARTICLES:
            url  = (f"{WIKI_PAGEVIEWS}/en.wikipedia/all-access/all-agents/"
                    f"{article}/monthly/{start}/{end}")
            data = self.safe_get(url)
            if "_error" in data or "items" not in data:
                continue
            total = sum(i.get("views", 0) for i in data["items"])
            views[article.replace("_", " ")] = total
            self.logger.info("  Wiki %-35s %d views/30d", article, total)

        return views

    # ── NewsAPI (optional free tier) ──────────────────────────
    def _fetch_news(self) -> list[dict]:
        """
        Free tier: 100 requests/day. Set NEWSAPI_KEY in .env.
        Falls back gracefully if key is absent.
        """
        if not NEWSAPI_KEY:
            self.logger.info("  NewsAPI key not set — skipping news fetch")
            return []

        params = {
            "q":        "automotive car parts manufacturing India",
            "sortBy":   "publishedAt",
            "pageSize": 10,
            "language": "en",
            "apiKey":   NEWSAPI_KEY,
        }
        data = self.safe_get(NEWSAPI_URL, params=params)
        if "_error" in data or "articles" not in data:
            return []

        articles = []
        for a in data["articles"][:10]:
            articles.append({
                "title":  a.get("title", "")[:80],
                "source": a.get("source", {}).get("name", ""),
                "date":   a.get("publishedAt", "")[:10],
            })
            self.logger.info("  News: %s", a.get("title","")[:60])
        return articles

    # ── LLM analysis ─────────────────────────────────────────
    def analyse(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        # Compact representation for LLM
        compact = {
            "reddit_mentions":    dict(list(raw_data["reddit"]["mentions"].items())[:20]),
            "reddit_total_posts": raw_data["reddit"]["total_posts"],
            "hn_top_stories":     raw_data["hackernews"][:5],
            "wiki_views_30d":     raw_data["wiki"],
            "news_headlines":     raw_data["news"][:5],
            "parts_categories":   raw_data["parts_catalogue"],
        }

        user_msg = (
            "Social and trend data:\n"
            + json.dumps(compact, indent=2)
        )
        result = self.llm.analyse(SYSTEM_PROMPT, user_msg)

        if "error" in result or "social_signals" not in result:
            self.logger.warning("LLM failed, using rule-based fallback")
            result = self._fallback_signals(raw_data)

        return result

    def _fallback_signals(self, raw_data: dict) -> dict:
        mentions = raw_data["reddit"].get("mentions", {})
        wiki     = raw_data.get("wiki", {})
        total_m  = max(sum(mentions.values()), 1)

        kw_cat = {
            "electric vehicle": "Electronics", "EV": "Electronics",
            "hybrid car": "Electronics", "ADAS": "Electronics",
            "turbo": "Powertrain", "engine": "Powertrain",
            "fuel price": "Exhaust",
            "SUV": "Suspension", "car shortage": "ALL",
            "supply chain": "ALL", "auto parts": "ALL",
        }

        cat_buzz = defaultdict(float)
        for kw, cnt in mentions.items():
            cat = kw_cat.get(kw, "ALL")
            w   = cnt / total_m
            if cat == "ALL":
                for c in set(v["category"] for v in PARTS_CATALOGUE.values()):
                    cat_buzz[c] += w * 0.3
            else:
                cat_buzz[cat] += w

        # Wikipedia EV interest boost
        ev_wiki = wiki.get("Electric vehicle", 0) + wiki.get("Hybrid vehicle", 0)
        if ev_wiki > 80000:
            cat_buzz["Electronics"] += 0.25

        signals = {}
        for pid, info in PARTS_CATALOGUE.items():
            buzz   = cat_buzz.get(info["category"], 0)
            signal = round(1.0 + min(buzz * 2.5, 0.60), 3)
            signals[pid] = signal

        top_cat = max(cat_buzz, key=cat_buzz.get) if cat_buzz else "Electronics"
        low_cat = min(cat_buzz, key=cat_buzz.get) if cat_buzz else "Exhaust"
        buzz_score = min(100, sum(cat_buzz.values()) * 200)

        return {
            "social_signals":   signals,
            "buzz_summary": {
                "overall_sentiment": "Positive" if buzz_score > 30 else "Neutral",
                "buzz_score":        round(buzz_score, 1),
                "trending_topics":   list(mentions.keys())[:5],
                "ev_vs_ice_split_pct": {"ev": 45, "ice": 55},
                "top_reddit_mentions":list(mentions.keys())[:5],
                "key_news_themes":   [],
            },
            "hottest_category": top_cat,
            "coldest_category": low_cat,
        }
