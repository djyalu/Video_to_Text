from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .ocr_engine import available_ocr_backends


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="video-to-text",
        description="Extract text from page-turning videos and export Markdown/HTML/PDF.",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--input", "-i", type=Path, help="Path to input video")
    group.add_argument("--input-dir", type=Path, help="Directory containing multiple videos")
    
    parser.add_argument("--output", "-o", type=Path, default=Path("output"), help="Output directory")
    parser.add_argument("--title", type=str, default=None, help="Document title (for single mode)")

    parser.add_argument("--sample-fps", type=float, default=6.0, help="Frames sampled per second")
    parser.add_argument(
        "--transition-threshold",
        dest="transition_threshold",
        type=float,
        default=18.0,
        help="Threshold for entering page-transition state",
    )
    parser.add_argument(
        "--stable-threshold",
        type=float,
        default=4.0,
        help="Threshold for stable page state",
    )
    parser.add_argument(
        "--use-hist",
        action="store_true",
        default=True,
        help="Use histogram correlation for better transition detection",
    )
    parser.add_argument(
        "--no-hist",
        action="store_false",
        dest="use_hist",
        help="Disable histogram correlation",
    )
    parser.add_argument(
        "--hist-threshold",
        type=float,
        default=0.92,
        help="Histogram correlation threshold (0~1, default 0.92)",
    )
    parser.add_argument(
        "--min-transition-samples",
        type=int,
        default=2,
        help="Consecutive transition samples required to detect page turn",
    )
    parser.add_argument(
        "--min-stable-samples",
        type=int,
        default=3,
        help="Consecutive stable samples required to confirm new page",
    )
    parser.add_argument(
        "--dedupe-hamming-threshold",
        type=int,
        default=6,
        help="pHash hamming threshold to skip near-identical pages",
    )
    parser.add_argument("--min-focus", type=float, default=15.0, help="Minimum sharpness threshold")
    parser.add_argument("--max-pages", type=int, default=None, help="Optional maximum pages to process")

    parser.add_argument(
        "--ocr-engine",
        choices=["auto", "paddle", "tesseract"],
        default="auto",
        help="OCR backend",
    )
    parser.add_argument("--ocr-lang", default="kor+eng", help="OCR language setting")

    parser.add_argument("--no-markdown", action="store_true", help="Disable markdown export")
    parser.add_argument("--no-html", action="store_true", help="Disable html export")
    parser.add_argument("--no-pdf", action="store_true", help="Disable pdf export")

    parser.add_argument(
        "--list-engines",
        action="store_true",
        help="Show available OCR engines in current environment",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_engines:
        engines = available_ocr_backends()
        if engines:
            print("Available OCR engines:", ", ".join(engines))
        else:
            print("No OCR engine is available Install paddleocr or pytesseract + tesseract.")
        return 0

    if not args.input and not args.input_dir:
        parser.error("one of the following arguments is required: --input/-i or --input-dir")

    from .pipeline import PipelineConfig, run_pipeline

    video_files: list[tuple[Path, Path]] = []
    if args.input_dir:
        input_dir = args.input_dir
        if not input_dir.is_dir():
            print(f"[error] Not a directory: {input_dir}", file=sys.stderr)
            return 1
        extensions = (".mp4", ".mkv", ".avi", ".mov", ".ts")
        for f in sorted(input_dir.iterdir()):
            if f.suffix.lower() in extensions:
                # In batch mode, output is subdir
                video_files.append((f, args.output / f.stem))
    else:
        video_files.append((args.input, args.output))

    all_reports = []
    has_error = False

    for video_path, output_dir in video_files:
        print(f"[*] Processing: {video_path}")
        title = args.title if args.title and len(video_files) == 1 else video_path.stem
        config = PipelineConfig(
            input_video=video_path,
            output_dir=output_dir,
            title=title,
            sample_fps=args.sample_fps,
            transition_threshold=args.transition_threshold,
            stable_threshold=args.stable_threshold,
            min_transition_samples=args.min_transition_samples,
            min_stable_samples=args.min_stable_samples,
            dedupe_hamming_threshold=args.dedupe_hamming_threshold,
            min_focus_score=args.min_focus,
            max_pages=args.max_pages,
            ocr_engine=args.ocr_engine,
            ocr_lang=args.ocr_lang,
            use_hist=args.use_hist,
            hist_threshold=args.hist_threshold,
            export_markdown=not args.no_markdown,
            export_html=not args.no_html,
            export_pdf=not args.no_pdf,
        )

        try:
            report = run_pipeline(config)
            all_reports.append(report)
            print(f"[+] Success: {video_path} -> {len(report['generated_files'])} files generated")
        except Exception as exc:
            print(f"[error] {video_path}: {exc}", file=sys.stderr)
            has_error = True

    if args.input_dir and all_reports:
        summary_path = args.output / "batch_report.json"
        args.output.mkdir(parents=True, exist_ok=True)
        summary_json = json.dumps(all_reports, ensure_ascii=False, indent=2)
        summary_path.write_text(summary_json, encoding="utf-8")
        print(f"[*] Batch summary saved to: {summary_path}")

    return 1 if has_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
