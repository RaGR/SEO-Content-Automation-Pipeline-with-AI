(this is it!)[./images/Agent_Pipeline_in_Action.png]

# SEO Content Automation Pipeline

Automate the full SEO content workflow—from keyword discovery to publish-ready exports—using OpenRouter-hosted LLMs. The project is organised as a modular Python package so each stage (keywords, content generation, quality scoring, exporting) can be reused, swapped, or extended independently for multilingual or multi-CMS environments.

---

## Quick Start

1. **Prerequisites**
   - Python 3.10+
   - An OpenRouter account and API key
   - `pip install -r requirements.txt`

2. **Configure credentials**
   - Create a `.env` file in the project root:

     ```ini
     OPENROUTER_API_KEY=sk-or-xxx
     OPENROUTER_MODEL=tngtech/deepseek-r1t2-chimera:free
     ```

     (Aliases such as `api-key` and `LLM-model` are also recognised.)

3. **Run the automated pipeline**

   ```bash
   python run_pipeline.py
   ```

   This reads `config.json`, executes the steps listed in `database/commands.json`, and writes outputs to `output/`.

4. **Manual CLI (optional)**

   ```bash
   python seo_content_client.py "Website description goes here"
   ```

   By default this extracts keywords. Additional subcommands are described below.

---

## Architecture

```
seo_pipeline/
├── openrouter.py   # Credential loading + OpenRouter client wrapper
├── keywords.py     # Keyword extraction via LLM
├── content.py      # Article generation with headings, summary, meta
├── evaluation.py   # Yoast-style SEO scoring + recommendations
└── exporter.py     # CSV exporter for CMS ingestion
```

- `seo_pipeline/__init__.py` re-exports the core APIs for easier imports.
- `seo_content_client.py` is a thin orchestration/CLI layer that keeps the library clean and easily testable.
- `config_handler.py` demonstrates loading structured configuration (e.g., tone, length) which can feed into generation calls.

Each module is intentionally independent so you can:

- Swap the LLM backend while keeping the same interfaces.
- Plug different exporters (e.g., Markdown, direct WordPress API).
- Inject additional evaluation rules without touching generation.

---

## CLI Usage

| Command | Description |
| --- | --- |
| `python seo_content_client.py "<website description>"` | Extract SEO keywords ranked by relevance and estimated volume. |
| `python seo_content_client.py --generate-content "kw1,kw2,kw3" [context]` | Generate a structured article (H1/H2, bullets, call-to-action, meta description). |
| `python seo_content_client.py --evaluate-content article.json "kw1,kw2" [primary keyword]` | Score existing content from 0–100 and list optimisation tips. |
| `python seo_content_client.py --export-csv article.json "kw1,kw2" output.csv [category]` | Produce a UTF‑8 CSV ready for WordPress or other CMS bulk import. |

All commands enforce robust error handling (missing fields, invalid JSON, API issues) and return actionable messages.

### Automated Workflow (`run_pipeline.py`)

- Reads project settings from `config.json`.
- Executes the ordered steps defined in `database/commands.json` (load config → extract keywords → generate content → evaluate → export).
- Persists outputs to `output/`:
  - `article.json` — generated markdown content and metadata.
  - `evaluation.json` — SEO score, metric breakdown, recommendations.
  - `article.csv` — WordPress-ready CSV for import or scheduling.

Customise the automation by editing `database/commands.json` to add, remove, or reorder steps—no Python changes needed.

---

## Module Reference

### `openrouter.py`

| Function/Class | Purpose |
| --- | --- |
| `load_credentials()` | Reads `.env` and environment variables, normalising common aliases. |
| `OpenRouterClient.chat_completion()` | Minimal wrapper over OpenRouter's `/chat/completions` endpoint with consistent headers and error reporting. |

### `keywords.py`

| Function | Purpose |
| --- | --- |
| `extract_seo_keywords(description, client, max_keywords=12)` | Requests a short JSON array of high-value keywords. Validates empties and malformed responses. |

### `content.py`

| Entity | Purpose |
| --- | --- |
| `SEOContent` | Dataclass bundling title, body, summary, and meta description. |
| `generate_seo_content(keywords, client, description=None, topic_context=None, tone="Professional", length="Medium")` | Produces markdown-formatted copy using an enhanced prompt that enforces a strict JSON response (`title`, `body`, `summary`, `meta_description`) with SEO density guidance. |

### `evaluation.py`

| Entity | Purpose |
| --- | --- |
| `SEOEvaluation` | Dataclass capturing aggregated score and metric breakdown. |
| `evaluate_seo_content(content, keywords, primary_keyword=None)` | Computes keyword density, coverage, first-paragraph usage, heading quality, readability (Flesch), and meta description health. Returns overall score plus recommendations. |

### `exporter.py`

| Function | Purpose |
| --- | --- |
| `export_content_to_csv(content, keywords, output_path, category=None)` | Writes a single-row CSV with UTF‑8 encoding and WordPress-compatible columns. Creates parent directories as needed. |

---

## Sample Workflow

1. **Keyword extraction**

   ```bash
   python seo_content_client.py "AI-driven platform that automates sustainable e-commerce logistics"
   ```

   Output (abridged):

   ```
   Loaded OpenRouter API key: sk-o...9e43
   Loaded OpenRouter model: tngtech/deepseek-r1t2-chimera:free
   Extracted keywords:
   - sustainable e-commerce
   - ai logistics automation
   - eco-friendly order fulfillment
   ```

2. **Content generation**

   ```bash
   python seo_content_client.py --generate-content "sustainable e-commerce,ai logistics automation" \
     "Platform overview blog post"
   ```

   Produces a JSON payload such as:

   ```json
   {
     "title": "Scaling Sustainable E-Commerce with AI",
     "body": "# Scaling Sustainable E-Commerce...\n## ...",
     "summary": "50-100 word synopsis highlighting how AI supports sustainable fulfilment.",
     "meta_description": "≤160 character snippet featuring the primary keyword."
   }
   ```

   The `body` field contains markdown with H1/H2/H3 headings, lists, and a clear call-to-action.

3. **SEO evaluation**

   ```bash
   python seo_content_client.py --evaluate-content example_article.json \
     "sustainable e-commerce,ai logistics automation"
   ```

   Example output:

   ```
   SEO evaluation results:
   Total Score: 84/100
   - Keyword density: 1.40% (Score 92)
   - Keyword coverage score: 100
   - First paragraph score: 100
   - Headings score: 80
   - Readability score: 72
   - Meta description score: 70
   Recommendations:
   - Optimise meta description length and include the primary keyword.
   ```

4. **CSV export**

   ```bash
   python seo_content_client.py --export-csv example_article.json \
     "sustainable e-commerce,ai logistics automation" dist/article.csv "Logistics"
   ```

   Produces `dist/article.csv`:

   ```csv
   Title,Content,Meta Description,Keywords,Category/Tag
   "Scaling Sustainable E-Commerce with AI","...markdown body...","AI-driven sustainability for e-commerce logistics.","sustainable e-commerce, ai logistics automation","Logistics"
   ```

   Upload directly to WordPress via *Tools → Import → CSV* (or compatible plugins) or feed into other CMS schedulers.

---

## Testing & Validation

- **Unit tests (recommended)**: Each module is decoupled for targeted testing. Mock the `OpenRouterClient` to simulate responses for keyword and content functions.
- **Manual smoke tests**: Run the CLI commands with short descriptions and inspect JSON/CSV outputs.
- **Edge cases covered**:
  - Empty or whitespace-only descriptions/keywords.
  - Invalid JSON returned by the LLM triggers descriptive errors.
  - Keyword density, readability, and meta evaluations guard against division by zero.
  - CSV export ensures directories exist and enforces at least one keyword.

---

## Extensibility Ideas

- **Multi-language support**: Pass locale-specific tone or instructions into `generate_seo_content`, or parameterise the system prompt per language.
- **Additional CMS integrations**: Replace `export_content_to_csv` with WordPress REST uploads, Shopify blog API, or Notion exports without modifying upstream logic.
- **Analytics feedback loop**: Store `SEOEvaluation` history for continuous optimisation or A/B testing pipelines.

---

## Troubleshooting

- Missing credentials → check `.env` naming; `OPENROUTER_API_KEY` takes precedence, but `api-key` is accepted.
- HTTPS / network errors → retry after confirming network access and model availability on OpenRouter.
- Rate limits / cost control → throttle CLI invocations or cache keyword results using a datastore layer.

---

## License

Apache (see `LICENSE`).
