from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class SEOPreferences:
    keywords: List[str]


@dataclass
class ContentSettings:
    tone: str
    length: int


@dataclass
class SEOConfig:
    website_description: str
    content_category: str
    content_type: str
    seo_preferences: SEOPreferences
    content_settings: ContentSettings

    @classmethod
    def from_dict(cls, data: dict) -> "SEOConfig":
        expected_fields = {
            "website_description",
            "content_category",
            "content_type",
            "seo_preferences",
            "content_settings",
        }
        missing = sorted(expected_fields.difference(data))
        if missing:
            raise ValueError(f"Missing configuration fields: {', '.join(missing)}")

        seo_data = data["seo_preferences"]
        if not isinstance(seo_data, dict):
            raise ValueError("seo_preferences must be an object")
        keywords = seo_data.get("keywords")
        if not isinstance(keywords, list) or not all(isinstance(k, str) for k in keywords):
            raise ValueError("seo_preferences.keywords must be a list of strings")

        content_settings = data["content_settings"]
        if not isinstance(content_settings, dict):
            raise ValueError("content_settings must be an object")

        tone = content_settings.get("tone")
        if not isinstance(tone, str):
            raise ValueError("content_settings.tone must be a string")

        length = content_settings.get("length")
        if not isinstance(length, int) or length <= 0:
            raise ValueError("content_settings.length must be a positive integer")

        return cls(
            website_description=str(data["website_description"]),
            content_category=str(data["content_category"]),
            content_type=str(data["content_type"]),
            seo_preferences=SEOPreferences(keywords=keywords),
            content_settings=ContentSettings(tone=tone, length=length),
        )


def load_config(config_path: Path | str) -> SEOConfig:
    """Load configuration from disk and return it as a structured object."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")

    with path.open("r", encoding="utf-8") as config_file:
        raw_data = json.load(config_file)

    if not isinstance(raw_data, dict):
        raise ValueError("Root of configuration file must be a JSON object")

    return SEOConfig.from_dict(raw_data)


def main() -> None:
    config_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("config.json")
    config = load_config(config_path)

    # Store values in variables for downstream use.
    website_description = config.website_description
    content_category = config.content_category
    content_type = config.content_type
    seo_keywords = config.seo_preferences.keywords
    tone = config.content_settings.tone
    length = config.content_settings.length

    print("Configuration loaded successfully:")
    print(f"- Website description: {website_description}")
    print(f"- Content category: {content_category}")
    print(f"- Content type: {content_type}")
    print(f"- SEO keywords: {', '.join(seo_keywords)}")
    print(f"- Content tone: {tone}")
    print(f"- Content length: {length} words")


if __name__ == "__main__":
    main()
