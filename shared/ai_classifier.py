import json
import logging
import os
import re

import requests

logger = logging.getLogger("core-service.ai")

INTENT_VALUES = {"spam", "ask_price", "complaint", "praise", "general", "escalate_admin"}
SENTIMENT_VALUES = {"positive", "negative", "neutral"}


def classify_with_rules(message):
    text = (message or "").lower()
    if "http://" in text or "https://" in text or "www." in text:
        return "spam", "negative"
    if any(word in text for word in ("lua dao", "scam", "complain", "khieu nai")):
        return "complaint", "negative"
    if "te" in text or "tệ" in text or "bad" in text:
        return "complaint", "negative"
    if "gia" in text or "price" in text or "bao nhieu" in text:
        return "ask_price", "neutral"
    if any(word in text for word in ("hay", "tot", "tuyet", "cam on", "thank")):
        return "praise", "positive"
    return "general", "neutral"


def _parse_ai_json(content):
    match = re.search(r"\{.*\}", content, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    intent = str(data.get("intent", "general")).lower()
    sentiment = str(data.get("sentiment", "neutral")).lower()
    if intent not in INTENT_VALUES:
        intent = "general"
    if sentiment not in SENTIMENT_VALUES:
        sentiment = "neutral"
    return intent, sentiment


def _build_prompt(message):
    return (
        "Classify this Facebook page message. "
        "Return JSON only: {\"intent\": \"...\", \"sentiment\": \"...\"}. "
        "intent one of: spam, ask_price, complaint, praise, general, escalate_admin. "
        "sentiment one of: positive, negative, neutral. "
        f"Message: {message}"
    )


def classify_with_openai(message):
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return None
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": _build_prompt(message)}],
                "temperature": 0,
            },
            timeout=15,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return _parse_ai_json(content)
    except Exception:
        logger.exception("OpenAI classification failed")
        return None


def classify_with_gemini(message):
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return None
    model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    try:
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            params={"key": api_key},
            json={"contents": [{"parts": [{"text": _build_prompt(message)}]}]},
            timeout=15,
        )
        response.raise_for_status()
        content = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        return _parse_ai_json(content)
    except Exception:
        logger.exception("Gemini classification failed")
        return None


def classify_intent_and_sentiment(message):
    provider = os.getenv("AI_PROVIDER", "").lower()
    ai_result = None
    if provider == "openai":
        ai_result = classify_with_openai(message)
    elif provider == "gemini":
        ai_result = classify_with_gemini(message)
    else:
        ai_result = classify_with_openai(message) or classify_with_gemini(message)

    if ai_result:
        logger.info("AI classification intent=%s sentiment=%s", ai_result[0], ai_result[1])
        return ai_result

    return classify_with_rules(message)
