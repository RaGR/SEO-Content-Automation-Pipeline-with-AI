from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

from .content import SEOContent


@dataclass
class SEOEvaluation:
    total_score: int
    keyword_density: float
    keyword_density_score: int
    keyword_coverage_score: int
    first_paragraph_score: int
    headings_score: int
    readability_score: int
    meta_description_score: int
    notes: List[str]


class SEOEvaluationError(RuntimeError):
    """Raised when SEO evaluation fails."""


def _count_syllables(word: str) -> int:
    word = word.lower()
    vowels = "aeiouy"
    count = 0
    prev_char_was_vowel = False
    for char in word:
        is_vowel = char in vowels
        if is_vowel and not prev_char_was_vowel:
            count += 1
        prev_char_was_vowel = is_vowel
    if word.endswith("e") and count > 1:
        count -= 1
    return max(count, 1)


def _flesch_reading_ease(text: str) -> float:
    sentences = re.split(r"[.!?]+", text)
    sentences = [s.strip() for s in sentences if s.strip()]
    words = re.findall(r"\b[\w'-]+\b", text)
    syllables = sum(_count_syllables(word) for word in words) or 1
    sentence_count = max(len(sentences), 1)
    word_count = max(len(words), 1)
    return 206.835 - 1.015 * (word_count / sentence_count) - 84.6 * (syllables / word_count)


def _score_range(value: float, low: float, high: float) -> int:
    if value == 0:
        return 0
    if low <= value <= high:
        return 100
    if value < low:
        ratio = value / low
        return max(0, int(ratio * 80))
    overshoot = (value - high) / max(high, 1e-9)
    return max(0, int(100 - overshoot * 120))


def _clamp_score(score: float) -> int:
    return int(min(max(round(score), 0), 100))


def evaluate_seo_content(
    content: SEOContent,
    keywords: List[str],
    primary_keyword: Optional[str] = None,
) -> SEOEvaluation:
    """Evaluate generated content against common SEO heuristics (Yoast-style scoring)."""
    cleaned_keywords = [kw.strip() for kw in keywords if kw and kw.strip()]
    if not cleaned_keywords:
        raise SEOEvaluationError("At least one keyword is required for SEO evaluation.")

    primary = (primary_keyword or cleaned_keywords[0]).strip()
    if not primary:
        raise SEOEvaluationError("Primary keyword cannot be empty.")

    body_lower = content.body.lower()
    words = re.findall(r"\b[\w'-]+\b", body_lower)
    total_words = len(words)
    primary_pattern = re.compile(rf"\b{re.escape(primary.lower())}\b")
    primary_matches = primary_pattern.findall(body_lower)
    keyword_density = (len(primary_matches) / total_words) if total_words else 0.0
    keyword_density_score = _clamp_score(_score_range(keyword_density, low=0.007, high=0.03) * 1.0)

    coverage_hits = 0
    for term in cleaned_keywords:
        pattern = re.compile(rf"\b{re.escape(term.lower())}\b")
        if pattern.search(body_lower):
            coverage_hits += 1
    keyword_coverage_score = _clamp_score((coverage_hits / len(cleaned_keywords)) * 100)

    first_100_text = " ".join(words[:100])
    first_paragraph_score = 100 if primary.lower() in first_100_text else 0

    heading_lines = [line.strip() for line in content.body.splitlines()]
    has_h1 = any(line.startswith("# ") for line in heading_lines)
    h2_count = sum(1 for line in heading_lines if line.startswith("## "))
    headings_score = 0
    if has_h1:
        headings_score += 40
    headings_score += min(h2_count, 3) * 20
    headings_score = min(headings_score, 100)

    readability = _flesch_reading_ease(content.body)
    readability_score = _clamp_score(_score_range(readability, low=50, high=70))

    meta = content.meta_description.strip()
    meta_len = len(meta)
    meta_contains_primary = primary.lower() in meta.lower()
    meta_description_score = 0
    if 120 <= meta_len <= 160:
        meta_description_score += 70
    elif 90 <= meta_len < 120 or 160 < meta_len <= 180:
        meta_description_score += 40
    if meta_contains_primary:
        meta_description_score += 30
    meta_description_score = min(meta_description_score, 100)

    weights = {
        "keyword_density_score": 0.2,
        "keyword_coverage_score": 0.15,
        "first_paragraph_score": 0.1,
        "headings_score": 0.2,
        "readability_score": 0.2,
        "meta_description_score": 0.15,
    }
    weighted_sum = (
        keyword_density_score * weights["keyword_density_score"]
        + keyword_coverage_score * weights["keyword_coverage_score"]
        + first_paragraph_score * weights["first_paragraph_score"]
        + headings_score * weights["headings_score"]
        + readability_score * weights["readability_score"]
        + meta_description_score * weights["meta_description_score"]
    )
    total_score = _clamp_score(weighted_sum)

    notes: List[str] = []
    if keyword_density_score < 60:
        notes.append("Adjust keyword density to stay within 0.7% - 3%.")
    if keyword_coverage_score < 80:
        notes.append("Ensure all target keywords appear at least once.")
    if first_paragraph_score == 0:
        notes.append("Include the primary keyword within the first 100 words.")
    if headings_score < 80:
        notes.append("Use clear H1 and multiple H2 headings for structure.")
    if readability_score < 65:
        notes.append("Simplify language to improve readability (Flesch 50-70 target).")
    if meta_description_score < 90:
        notes.append("Optimize meta description length and include the primary keyword.")

    return SEOEvaluation(
        total_score=total_score,
        keyword_density=keyword_density,
        keyword_density_score=keyword_density_score,
        keyword_coverage_score=keyword_coverage_score,
        first_paragraph_score=first_paragraph_score,
        headings_score=headings_score,
        readability_score=readability_score,
        meta_description_score=meta_description_score,
        notes=notes,
    )
