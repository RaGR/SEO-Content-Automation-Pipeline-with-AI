from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Dict, List, Optional

from .openrouter import OpenRouterClient


@dataclass
class SEOContent:
    title: str
    body: str
    summary: str
    meta_description: str


class ContentGenerationError(RuntimeError):
    """Raised when content generation fails."""


def generate_seo_content(
    keywords: List[str],
    client: OpenRouterClient,
    topic_context: Optional[str] = None,
    tone: str = "Professional",
    length: str = "Medium",
) -> SEOContent:
    """Generate SEO-optimized content that naturally incorporates the provided keywords."""
    cleaned_keywords = [kw.strip() for kw in keywords if kw and kw.strip()]
    if not cleaned_keywords:
        raise ContentGenerationError("At least one keyword is required to generate content.")

    keyword_str = ", ".join(cleaned_keywords)
    context_fragment = f"Context: {topic_context}\n" if topic_context else ""

    messages = [
        {
            "role": "system",
            "content": (
                "You are an SEO-focused content strategist. Craft long-form content with engaging structure, "
                "organic keyword usage, and adherence to SEO best practices. Always return valid JSON."
            ),
        },
        {
            "role": "user",
            "content": (
                f"{context_fragment}"
                f"Target keywords: {keyword_str}\n"
                "Create an article that includes:\n"
                "1. A compelling H1 title.\n"
                "2. An introductory paragraph.\n"
                "3. At least two H2 sections with supporting detail.\n"
                "4. Bullet points or numbered lists where helpful.\n"
                "5. A short conclusion and actionable summary.\n"
                "6. A 155-character meta description optimized for click-through.\n"
                f"Tone: {tone}. Target length: {length}.\n"
                "Use the keywords naturally; avoid keyword stuffing. Ensure markdown uses headings for structure."
            ),
        },
    ]

    response_format: Dict[str, str] = {"type": "json_object"}
    raw_output = client.chat_completion(messages, response_format=response_format)

    try:
        payload = json.loads(raw_output)
    except json.JSONDecodeError as exc:
        raise ContentGenerationError("Model response was not valid JSON.") from exc

    required_fields = ["title", "body", "summary", "meta_description"]
    missing = [field for field in required_fields if field not in payload or not str(payload[field]).strip()]
    if missing:
        raise ContentGenerationError(f"Model response missing required fields: {', '.join(missing)}")

    return SEOContent(
        title=str(payload["title"]).strip(),
        body=str(payload["body"]).strip(),
        summary=str(payload["summary"]).strip(),
        meta_description=str(payload["meta_description"]).strip(),
    )
