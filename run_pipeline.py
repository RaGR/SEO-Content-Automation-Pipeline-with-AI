from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from config_handler import SEOConfig, load_config
from seo_pipeline import (
    ContentGenerationError,
    EnvConfigError,
    KeywordExtractionError,
    SEOEvaluation,
    SEOEvaluationError,
    SEOContent,
    OpenRouterClient,
    export_content_to_csv,
    evaluate_seo_content,
    extract_seo_keywords,
    generate_seo_content,
    load_credentials,
)


def _mask_secret(secret: str, visible: int = 4) -> str:
    if len(secret) <= visible * 2:
        return "*" * len(secret)
    return f"{secret[:visible]}...{secret[-visible:]}"


class PipelineState:
    def __init__(self) -> None:
        self.data: Dict[str, Any] = {}
        self._client: Optional[OpenRouterClient] = None

    @property
    def config(self) -> Optional[SEOConfig]:
        return self.data.get("config")

    @property
    def keywords(self) -> Optional[List[str]]:
        return self.data.get("keywords")

    @property
    def content(self) -> Optional[SEOContent]:
        return self.data.get("content")

    @property
    def evaluation(self) -> Optional[SEOEvaluation]:
        return self.data.get("evaluation")

    def ensure_client(self) -> OpenRouterClient:
        if self._client is not None:
            return self._client
        try:
            credentials = load_credentials()
        except EnvConfigError as exc:
            raise RuntimeError(f"Failed to load OpenRouter credentials: {exc}") from exc

        api_key = credentials["api_key"]
        model = credentials["model"]
        masked_key = _mask_secret(api_key)
        print(f"[Pipeline] OpenRouter API key: {masked_key}")
        print(f"[Pipeline] OpenRouter model: {model}")
        self._client = OpenRouterClient(api_key=api_key, model=model)
        return self._client


def _resolve_value(state: PipelineState, descriptor: Optional[str], default: Any = None) -> Any:
    if not descriptor:
        return default
    parts = descriptor.split(".")
    current: Any
    root_key = parts[0]

    if root_key == "config":
        current = state.config
    else:
        current = state.data.get(root_key)

    for part in parts[1:]:
        if current is None:
            return default
        if isinstance(current, dict):
            current = current.get(part)
        else:
            current = getattr(current, part, None)
    return current if current is not None else default


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)


def _load_commands(commands_path: Path) -> List[Dict[str, Any]]:
    with commands_path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    steps = data.get("steps")
    if not isinstance(steps, list):
        raise ValueError("commands.json must contain a top-level 'steps' array.")
    return steps


def _handle_load_config(step: Dict[str, Any], state: PipelineState) -> None:
    config_path = Path(step.get("config_path", "config.json"))
    config = load_config(config_path)
    state.data["config"] = config
    print(f"[Pipeline] Loaded configuration from {config_path}")
    print(f"            Description: {config.website_description[:80]}...")
    print(f"            Tone: {config.content_settings.tone}, Length: {config.content_settings.length} words")


def _handle_extract_keywords(step: Dict[str, Any], state: PipelineState) -> None:
    config = state.config
    if config is None:
        raise RuntimeError("Configuration must be loaded before extracting keywords.")

    description = _resolve_value(state, step.get("source"), config.website_description)
    max_keywords = step.get("max_keywords", 12)
    fallback_to_config = bool(step.get("fallback_to_config_keywords", False))

    client = state.ensure_client()
    try:
        keywords = extract_seo_keywords(description, client, max_keywords=max_keywords)
        print(f"[Pipeline] Extracted {len(keywords)} keywords via LLM.")
    except KeywordExtractionError as exc:
        if fallback_to_config:
            keywords = config.seo_preferences.keywords
            print("[Pipeline] Keyword extraction failed; falling back to config keywords.")
            print(f"            Reason: {exc}")
        else:
            raise RuntimeError(f"Keyword extraction failed: {exc}") from exc

    state.data["keywords"] = keywords


def _handle_generate_content(step: Dict[str, Any], state: PipelineState) -> None:
    config = state.config
    if config is None:
        raise RuntimeError("Configuration must be loaded before content generation.")

    keywords = state.keywords or config.seo_preferences.keywords
    if not keywords:
        raise RuntimeError("No keywords available for content generation.")

    client = state.ensure_client()
    tone = _resolve_value(state, step.get("tone_source"), config.content_settings.tone)
    length_setting = _resolve_value(state, step.get("length_source"), config.content_settings.length)
    topic_context = _resolve_value(state, step.get("topic_context_source"), config.content_category)
    description = config.website_description

    length_text = str(length_setting)
    try:
        content = generate_seo_content(
            keywords=keywords,
            client=client,
            description=description,
            topic_context=topic_context,
            tone=tone,
            length=length_text,
        )
        print(f"[Pipeline] Generated content with title: {content.title}")
    except ContentGenerationError as exc:
        raise RuntimeError(f"Content generation failed: {exc}") from exc

    state.data["content"] = content

    output_path_raw = step.get("output_content_path")
    if output_path_raw:
        output_path = Path(output_path_raw)
        _write_json(output_path, asdict(content))
        state.data["content_json_path"] = output_path
        print(f"[Pipeline] Saved generated content to {output_path}")


def _handle_evaluate_content(step: Dict[str, Any], state: PipelineState) -> None:
    content = state.content
    config = state.config
    if content is None or config is None:
        raise RuntimeError("Content and configuration must be available before evaluation.")

    keywords = state.keywords or config.seo_preferences.keywords
    if not keywords:
        raise RuntimeError("No keywords available for evaluation.")

    primary_source = step.get("primary_keyword_source", "auto")
    if primary_source == "auto":
        primary_keyword = keywords[0]
    else:
        primary_keyword = _resolve_value(state, primary_source, keywords[0])

    try:
        evaluation = evaluate_seo_content(content, keywords, primary_keyword=primary_keyword)
        print(f"[Pipeline] Evaluation score: {evaluation.total_score}/100")
    except SEOEvaluationError as exc:
        raise RuntimeError(f"SEO evaluation failed: {exc}") from exc

    state.data["evaluation"] = evaluation

    output_path_raw = step.get("output_report_path")
    if output_path_raw:
        output_path = Path(output_path_raw)
        payload = asdict(evaluation)
        payload["keywords"] = keywords
        _write_json(output_path, payload)
        state.data["evaluation_json_path"] = output_path
        print(f"[Pipeline] Saved evaluation report to {output_path}")


def _handle_export_csv(step: Dict[str, Any], state: PipelineState) -> None:
    content = state.content
    config = state.config
    if content is None or config is None:
        raise RuntimeError("Content and configuration must be available before exporting.")

    keywords = state.keywords or config.seo_preferences.keywords
    if not keywords:
        raise RuntimeError("No keywords available for export.")

    output_path = Path(step.get("output_csv_path", "output/article.csv"))
    category = _resolve_value(state, step.get("category_source"), config.content_category)

    export_content_to_csv(content, keywords, output_path, category=category)
    state.data["csv_path"] = output_path
    print(f"[Pipeline] Exported CSV to {output_path}")


STEP_HANDLERS = {
    "load_config": _handle_load_config,
    "extract_keywords": _handle_extract_keywords,
    "generate_content": _handle_generate_content,
    "evaluate_content": _handle_evaluate_content,
    "export_csv": _handle_export_csv,
}


def run_pipeline(commands_path: Path = Path("database/commands.json")) -> None:
    if not commands_path.exists():
        raise FileNotFoundError(f"Command definition file not found: {commands_path}")

    steps = _load_commands(commands_path)
    state = PipelineState()

    for index, step in enumerate(steps, start=1):
        operation = step.get("operation")
        if not operation:
            raise ValueError(f"Step #{index} is missing an 'operation' field.")

        handler = STEP_HANDLERS.get(operation)
        if handler is None:
            raise ValueError(f"Unsupported operation '{operation}' in commands.json (step #{index}).")

        print(f"\n[Pipeline] Step {index}/{len(steps)} → {operation.replace('_', ' ').title()}")
        handler(step, state)

    print("\n[Pipeline] Completed all steps successfully.")
    if state.data.get("csv_path"):
        print(f"  • CSV output: {state.data['csv_path']}")
    if state.data.get("content_json_path"):
        print(f"  • Content JSON: {state.data['content_json_path']}")
    if state.data.get("evaluation_json_path"):
        print(f"  • Evaluation report: {state.data['evaluation_json_path']}")


def main(argv: Optional[List[str]] = None) -> None:
    args = argv if argv is not None else sys.argv[1:]
    commands_path = Path(args[0]) if args else Path("database/commands.json")

    try:
        run_pipeline(commands_path)
    except Exception as exc:
        print(f"[Pipeline] Execution failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
