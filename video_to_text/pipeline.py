from __future__ import annotations

import json
import re
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2

from .exporters import write_html, write_markdown, write_pdf
from .models import DocumentPage, OcrWord
from .ocr_engine import create_ocr_engine
from .video_processing import ExtractionConfig, extract_page_frames, preprocess_for_ocr


@dataclass(slots=True)
class PipelineConfig:
    input_video: Path
    output_dir: Path
    title: str = "Video OCR Document"
    sample_fps: float = 6.0
    transition_threshold: float = 18.0
    stable_threshold: float = 4.0
    min_transition_samples: int = 2
    min_stable_samples: int = 3
    dedupe_hamming_threshold: int = 6
    min_focus_score: float = 15.0
    max_pages: int | None = None
    ocr_engine: str = "auto"
    ocr_lang: str = "kor+eng"
    use_hist: bool = True
    hist_threshold: float = 0.92
    export_markdown: bool = True
    export_html: bool = True
    export_pdf: bool = True


def run_pipeline(config: PipelineConfig) -> dict[str, Any]:
    start_time = time.perf_counter()
    if not config.input_video.exists():
        raise FileNotFoundError(f"Input video not found: {config.input_video}")

    output_dir = config.output_dir
    pages_dir = output_dir / "pages"
    ocr_dir = output_dir / "ocr"
    pages_dir.mkdir(parents=True, exist_ok=True)
    ocr_dir.mkdir(parents=True, exist_ok=True)

    extraction_config = ExtractionConfig(
        sample_fps=config.sample_fps,
        transition_threshold=config.transition_threshold,
        stable_threshold=config.stable_threshold,
        min_transition_samples=config.min_transition_samples,
        min_stable_samples=config.min_stable_samples,
        dedupe_hamming_threshold=config.dedupe_hamming_threshold,
        max_pages=config.max_pages,
        min_focus_score=config.min_focus_score,
        use_hist=config.use_hist,
        hist_threshold=config.hist_threshold,
    )
    frame_candidates = extract_page_frames(config.input_video, pages_dir, extraction_config)

    if not frame_candidates:
        raise RuntimeError(
            "No page frames were extracted. Tune transition/stable thresholds or sample_fps."
        )

    engine = create_ocr_engine(config.ocr_engine, config.ocr_lang)

    pages: list[DocumentPage] = []
    warnings: list[str] = []

    for candidate in frame_candidates:
        image = cv2.imread(str(candidate.image_path))
        if image is None:
            warnings.append(f"Could not load frame image: {candidate.image_path}")
            continue

        preprocessed = preprocess_for_ocr(image)
        ocr_result = engine.recognize(preprocessed)
        cleaned_text = normalize_text(ocr_result.text)

        page = DocumentPage(
            page_number=candidate.page_number,
            image_path=candidate.image_path,
            text=cleaned_text,
            confidence=ocr_result.confidence,
            timestamp_sec=candidate.timestamp_sec,
            raw_text=ocr_result.text,
        )
        pages.append(page)

        ocr_json_path = ocr_dir / f"page_{candidate.page_number:04d}.json"
        _write_ocr_json(ocr_json_path, page, ocr_result.words)

    pages.sort(key=lambda item: item.page_number)

    generated_files: list[str] = []

    if config.export_markdown:
        md_path = output_dir / "book.md"
        write_markdown(md_path, config.title, pages)
        generated_files.append(str(md_path))

    if config.export_html:
        html_path = output_dir / "book.html"
        write_html(html_path, config.title, pages)
        generated_files.append(str(html_path))

    if config.export_pdf:
        pdf_path = output_dir / "book.pdf"
        try:
            write_pdf(pdf_path, config.title, pages)
            generated_files.append(str(pdf_path))
        except RuntimeError as exc:
            warnings.append(str(exc))

    avg_conf = sum(page.confidence for page in pages) / len(pages) if pages else 0.0
    duration = time.perf_counter() - start_time

    report = {
        "input_video": str(config.input_video),
        "title": config.title,
        "engine_name": engine.name,
        "total_pages": len(pages),
        "average_confidence": avg_conf,
        "processing_time_sec": round(duration, 2),
        "extraction_parameters": {
            "sample_fps": config.sample_fps,
            "transition_threshold": config.transition_threshold,
            "stable_threshold": config.stable_threshold,
            "min_focus_score": config.min_focus_score,
            "ocr_lang": config.ocr_lang,
        },
        "generated_files": generated_files,
        "warnings": warnings,
    }

    report_path = output_dir / "report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    return report


def normalize_text(raw_text: str) -> str:
    normalized = unicodedata.normalize("NFKC", raw_text)
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"[ \t]+", " ", normalized)

    merged_lines: list[str] = []
    for line in (line.strip() for line in normalized.split("\n")):
        if not line:
            if merged_lines and merged_lines[-1] != "":
                merged_lines.append("")
            continue

        if merged_lines and merged_lines[-1].endswith("-"):
            merged_lines[-1] = merged_lines[-1][:-1] + line
        else:
            merged_lines.append(line)

    cleaned = "\n".join(merged_lines).strip()
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned


def _write_ocr_json(path: Path, page: DocumentPage, words: list[OcrWord]) -> None:
    payload = {
        "page_number": page.page_number,
        "timestamp_sec": page.timestamp_sec,
        "confidence": page.confidence,
        "image_path": str(page.image_path),
        "raw_text": page.raw_text,
        "cleaned_text": page.text,
        "words": [
            {
                "text": word.text,
                "confidence": word.confidence,
                "bbox": word.bbox,
            }
            for word in words
        ],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
