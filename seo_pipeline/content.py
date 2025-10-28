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
    description: Optional[str] = None,
    topic_context: Optional[str] = None,
    tone: str = "Professional",
    length: str = "Medium",
) -> SEOContent:
    """Generate SEO-optimized content that naturally incorporates the provided keywords."""
    cleaned_keywords = [kw.strip() for kw in keywords if kw and kw.strip()]
    if not cleaned_keywords:
        raise ContentGenerationError("At least one keyword is required to generate content.")

    keyword_str = ", ".join(cleaned_keywords)
    description_text = description or topic_context or "No additional description provided."
    context_note = (
        f"Additional context: {topic_context}\n" if topic_context and topic_context != description_text else ""
    )

    messages = [
        {
            "role": "system",
            "content": (
                "You are an advanced AI assistant specialising in SEO content automation. "
                "Always produce clear, structured, search-optimised articles that follow instructions exactly, "
                "returning only valid JSON."
            ),
        },
        {
            "role": "user",
            "content": (
                "Generate an SEO-optimised article based on the provided description and keywords. "
                "Follow these requirements:\n"
                "1. Body: A detailed markdown article with an H1 title line, multiple H2/H3 sections, and natural keyword usage.\n"
                "2. Summary: 50-100 word overview capturing the article's key points.\n"
                "3. Meta description: <=160 characters, compelling and keyword-rich.\n"
                "4. Include concise bullet lists where helpful and a clear conclusion/call-to-action.\n"
                "5. Maintain a professional tone and avoid keyword stuffing (target 1-2% for the primary keyword).\n"
                "6. Output strictly in JSON with the following schema:\n"
                '{\n'
                '  "title": "<catchy H1 title>",\n'
                '  "body": "<full article body in markdown>",\n'
                '  "summary": "<50-100 word summary>",\n'
                '  "meta_description": "<<=160 character meta description>"\n'
                '}\n'
                f"Description: {description_text}\n"
                f"{context_note}"
                f"Keywords: {keyword_str}\n"
                f"Tone: {tone}\n"
                f"Target length guidance: {length} words\n"
                "Do not include any additional fields, commentary, or formatting outside of the JSON."
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
