from __future__ import annotations

import csv
from pathlib import Path
from typing import List, Optional

from .content import SEOContent


def export_content_to_csv(
    content: SEOContent,
    keywords: List[str],
    output_path: Path,
    category: Optional[str] = None,
) -> Path:
    """Export SEO content to a CSV file suitable for CMS import."""
    cleaned_keywords = [kw.strip() for kw in keywords if kw and kw.strip()]
    if not cleaned_keywords:
        raise ValueError("At least one keyword is required to export content.")

    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=["Title", "Content", "Meta Description", "Keywords", "Category/Tag"],
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerow(
            {
                "Title": content.title,
                "Content": content.body,
                "Meta Description": content.meta_description,
                "Keywords": ", ".join(cleaned_keywords),
                "Category/Tag": category or "",
            }
        )

    return output_path
