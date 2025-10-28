from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import List, Optional

from seo_pipeline import (
    OpenRouterClient,
    SEOContent,
    ContentGenerationError,
    EnvConfigError,
    KeywordExtractionError,
    SEOEvaluationError,
    export_content_to_csv,
    evaluate_seo_content,
    extract_seo_keywords,
    generate_seo_content,
    load_credentials,
)


def print_usage() -> None:
    print(
        "Usage:\n"
        '  python seo_content_client.py "<website description>"\n'
        '      Extract keywords from a website description.\n'
        '  python seo_content_client.py --generate-content "kw1,kw2" [optional context]\n'
        "      Generate SEO content using the provided keywords.\n"
        '  python seo_content_client.py --evaluate-content content.json "kw1,kw2" [primary keyword]\n'
        "      Evaluate existing content JSON against target keywords.\n"
        '  python seo_content_client.py --export-csv content.json "kw1,kw2" output.csv [category]\n'
        "      Export content JSON and keywords to a CMS-friendly CSV file.\n"
    )


def load_content_from_json(path: Path) -> SEOContent:
    if not path.exists():
        raise FileNotFoundError(f"Content file not found: {path}")
    with path.open("r", encoding="utf-8") as content_file:
        payload = json.load(content_file)
    try:
        return SEOContent(
            title=payload["title"],
            body=payload["body"],
            summary=payload["summary"],
            meta_description=payload["meta_description"],
        )
    except KeyError as exc:
        raise KeyError(f"Content JSON missing field: {exc}") from exc


def handle_generate_content(client: OpenRouterClient, args: List[str]) -> None:
    if not args:
        print("Provide a comma-separated list of keywords after --generate-content.", file=sys.stderr)
        raise SystemExit(1)
    keywords = [kw.strip() for kw in args[0].split(",")]
    topic_context = " ".join(args[1:]) if len(args) > 1 else None
    try:
        content = generate_seo_content(keywords, client, topic_context=topic_context)
    except ContentGenerationError as exc:
        print(f"Content generation failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    print("Generated SEO content:")
    print(f"# {content.title}\n")
    print(f"{content.body}\n")
    print("Summary:")
    print(content.summary)
    print("\nMeta description:")
    print(content.meta_description)


def handle_evaluate_content(args: List[str]) -> None:
    if len(args) < 2:
        print(
            "Usage: python seo_content_client.py --evaluate-content content.json \"kw1,kw2\" [primary keyword]",
            file=sys.stderr,
        )
        raise SystemExit(1)
    content_path = Path(args[0])
    try:
        content = load_content_from_json(content_path)
    except Exception as exc:
        print(f"Failed to load content JSON: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    keywords = [kw.strip() for kw in args[1].split(",")]
    primary_keyword = args[2] if len(args) > 2 else None

    try:
        evaluation = evaluate_seo_content(content, keywords, primary_keyword=primary_keyword)
    except SEOEvaluationError as exc:
        print(f"SEO evaluation failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    print("SEO evaluation results:")
    print(f"Total Score: {evaluation.total_score}/100")
    print(f"- Keyword density: {evaluation.keyword_density:.2%} (Score {evaluation.keyword_density_score})")
    print(f"- Keyword coverage score: {evaluation.keyword_coverage_score}")
    print(f"- First paragraph score: {evaluation.first_paragraph_score}")
    print(f"- Headings score: {evaluation.headings_score}")
    print(f"- Readability score: {evaluation.readability_score}")
    print(f"- Meta description score: {evaluation.meta_description_score}")
    if evaluation.notes:
        print("Recommendations:")
        for note in evaluation.notes:
            print(f"- {note}")
    else:
        print("Great job! Content meets all key SEO checks.")


def handle_export_csv(args: List[str]) -> None:
    if len(args) < 3:
        print(
            "Usage: python seo_content_client.py --export-csv content.json \"kw1,kw2\" output.csv [category]",
            file=sys.stderr,
        )
        raise SystemExit(1)

    content_path = Path(args[0])
    keywords = [kw.strip() for kw in args[1].split(",")]
    output_path = Path(args[2])
    category = args[3] if len(args) > 3 else None

    try:
        content = load_content_from_json(content_path)
    except Exception as exc:
        print(f"Failed to load content JSON: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    try:
        destination = export_content_to_csv(content, keywords, output_path, category=category)
    except Exception as exc:
        print(f"CSV export failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    print(f"Content exported to CSV at: {destination}")


def handle_keyword_extraction(client: OpenRouterClient, description: str) -> None:
    try:
        keywords = extract_seo_keywords(description, client)
    except KeywordExtractionError as exc:
        print(f"Keyword extraction failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    print("Extracted keywords:")
    for keyword in keywords:
        print(f"- {keyword}")


def _mask_secret(secret: str, visible: int = 4) -> str:
    if len(secret) <= visible * 2:
        return "*" * len(secret)
    return f"{secret[:visible]}...{secret[-visible:]}"


def _init_client() -> OpenRouterClient:
    try:
        credentials = load_credentials()
    except EnvConfigError as exc:
        print(f"Failed to load OpenRouter credentials: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    api_key = credentials["api_key"]
    model = credentials["model"]
    masked_key = _mask_secret(api_key)
    print(f"Loaded OpenRouter API key: {masked_key}")
    print(f"Loaded OpenRouter model: {model}")

    return OpenRouterClient(api_key=api_key, model=model)


def main(argv: Optional[List[str]] = None) -> None:
    args = argv or sys.argv[1:]

    if not args or args[0] in ("-h", "--help"):
        print_usage()
        return

    command = args[0]
    remaining = args[1:]

    if command == "--generate-content":
        client = _init_client()
        handle_generate_content(client, remaining)
    elif command == "--evaluate-content":
        handle_evaluate_content(remaining)
    elif command == "--export-csv":
        handle_export_csv(remaining)
    else:
        client = _init_client()
        description = " ".join(args)
        handle_keyword_extraction(client, description)


if __name__ == "__main__":
    main()
