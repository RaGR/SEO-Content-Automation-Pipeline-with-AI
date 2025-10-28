from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Iterable, Optional

import requests

DEFAULT_ENV_PATH = Path(".env")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


class EnvConfigError(RuntimeError):
    """Raised when required environment settings are missing or invalid."""


def _normalize_key(key: str) -> str:
    return key.strip().upper().replace("-", "_")


def load_dotenv(path: Path = DEFAULT_ENV_PATH) -> Dict[str, str]:
    """Lightweight .env parser that keeps both original and normalized keys."""
    if not path.exists():
        return {}

    env: Dict[str, str] = {}
    with path.open("r", encoding="utf-8") as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            env[key] = value
            env[_normalize_key(key)] = value
    return env


def _get_env_value(env_map: Dict[str, str], candidates: Iterable[str]) -> str:
    for candidate in candidates:
        normalized = _normalize_key(candidate)
        if candidate in os.environ and os.environ[candidate]:
            return os.environ[candidate]
        if normalized in os.environ and os.environ[normalized]:
            return os.environ[normalized]
        if candidate in env_map and env_map[candidate]:
            return env_map[candidate]
        if normalized in env_map and env_map[normalized]:
            return env_map[normalized]
    raise EnvConfigError(f"Missing required environment variable. Tried: {', '.join(candidates)}")


def load_credentials(env_path: Path = DEFAULT_ENV_PATH) -> Dict[str, str]:
    env_map = load_dotenv(env_path)
    api_key = _get_env_value(
        env_map,
        candidates=("OPENROUTER_API_KEY", "API_KEY", "api_key", "API-KEY", "api-key"),
    )
    model = _get_env_value(
        env_map,
        candidates=("OPENROUTER_MODEL", "LLM_MODEL", "LLM-model", "MODEL"),
    )
    os.environ.setdefault("OPENROUTER_API_KEY", api_key)
    os.environ.setdefault("OPENROUTER_MODEL", model)
    return {"api_key": api_key, "model": model}


class OpenRouterClient:
    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        base_url: str = OPENROUTER_BASE_URL,
        timeout: int = 60,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.timeout = timeout

    def chat_completion(
        self,
        messages: Iterable[Dict[str, str]],
        response_format: Optional[Dict[str, str]] = None,
    ) -> str:
        """Call the OpenRouter chat completions endpoint and return the model output."""
        url = f"{self.base_url}/chat/completions"
        payload: Dict[str, object] = {
            "model": self.model,
            "messages": list(messages),
        }
        if response_format:
            payload["response_format"] = response_format

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/",
            "X-Title": "SEO Content Automation Pipeline",
        }

        response = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        choices = data.get("choices")
        if not choices:
            raise RuntimeError("OpenRouter returned no choices in the response.")
        message = choices[0].get("message", {})
        content = message.get("content")
        if not content:
            raise RuntimeError("OpenRouter response message is empty.")
        return str(content).strip()
