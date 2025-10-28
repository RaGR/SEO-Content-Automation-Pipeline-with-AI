from __future__ import annotations

import json
from typing import List

from .openrouter import OpenRouterClient


class KeywordExtractionError(RuntimeError):
    """Raised when keyword extraction fails."""


def extract_seo_keywords(description: str, client: OpenRouterClient, max_keywords: int = 12) -> List[str]:
    """Use the LLM to extract SEO-friendly keywords from a website description."""
    if not description.strip():
        raise KeywordExtractionError("Website description must not be empty.")

    messages = [
        {
            "role": "system",
            "content": (
                "You are an SEO strategist. Given a website description, return the top keywords "
                "sorted by combined relevance and estimated search volume. Respond with a JSON array "
                "of strings only."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Website description: {description}\n"
                f"Limit the response to {max_keywords} keywords. Do not include explanations."
            ),
        },
    ]

    raw_response = client.chat_completion(messages)
    try:
        parsed = json.loads(raw_response)
    except json.JSONDecodeError as exc:
        raise KeywordExtractionError("Model returned invalid JSON.") from exc

    if isinstance(parsed, dict) and "keywords" in parsed:
        keywords = parsed["keywords"]
    else:
        keywords = parsed

    if not isinstance(keywords, list) or not all(isinstance(item, str) for item in keywords):
        raise KeywordExtractionError("Model response did not contain a list of keyword strings.")

    ordered_keywords = [keyword.strip() for keyword in keywords if keyword.strip()]
    if not ordered_keywords:
        raise KeywordExtractionError("No keywords extracted from the model response.")

    return ordered_keywords
