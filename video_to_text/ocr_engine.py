from __future__ import annotations

from collections import defaultdict
from typing import Protocol

import numpy as np

from .models import OcrPageResult, OcrWord

try:
    import pytesseract
    from pytesseract import Output as TesseractOutput
except Exception:  # pragma: no cover - optional dependency loading
    pytesseract = None
    TesseractOutput = None

try:
    from paddleocr import PaddleOCR
except Exception:  # pragma: no cover - optional dependency loading
    PaddleOCR = None


class OcrEngine(Protocol):
    @property
    def name(self) -> str:
        ...

    def recognize(self, image: np.ndarray) -> OcrPageResult:
        ...


class TesseractOcrEngine:
    def __init__(self, lang: str) -> None:
        if pytesseract is None or TesseractOutput is None:
            raise RuntimeError("pytesseract is not installed")
        self.lang = lang
        self._name = "tesseract"
        try:
            pytesseract.get_tesseract_version()
        except Exception as exc:
            raise RuntimeError("Tesseract binary is not available") from exc

    @property
    def name(self) -> str:
        return self._name

    def recognize(self, image: np.ndarray) -> OcrPageResult:
        data = pytesseract.image_to_data(
            image,
            lang=self.lang,
            output_type=TesseractOutput.DICT,
            config="--psm 6",
        )

        grouped_words: dict[tuple[int, int, int, int], list[str]] = defaultdict(list)
        words: list[OcrWord] = []
        confidences: list[float] = []

        total = len(data["text"])
        for idx in range(total):
            text = data["text"][idx].strip()
            try:
                conf = float(data["conf"][idx])
            except Exception:
                conf = -1.0

            if not text or conf < 0:
                continue

            left = int(data["left"][idx])
            top = int(data["top"][idx])
            width = int(data["width"][idx])
            height = int(data["height"][idx])
            bbox = [left, top, left + width, top + height]

            key = (
                int(data["block_num"][idx]),
                int(data["par_num"][idx]),
                int(data["line_num"][idx]),
                int(data["word_num"][idx]),
            )
            grouped_words[key[:-1]].append(text)
            words.append(OcrWord(text=text, confidence=conf / 100.0, bbox=bbox))
            confidences.append(conf / 100.0)

        ordered_lines = [
            " ".join(grouped_words[key])
            for key in sorted(grouped_words.keys(), key=lambda item: (item[0], item[1], item[2]))
        ]

        joined_text = "\n".join(line for line in ordered_lines if line.strip())
        avg_conf = float(np.mean(confidences)) if confidences else 0.0
        return OcrPageResult(text=joined_text, confidence=avg_conf, words=words)


class PaddleOcrEngine:
    def __init__(self, lang: str) -> None:
        if PaddleOCR is None:
            raise RuntimeError("paddleocr is not installed")

        self.ocr = PaddleOCR(
            use_angle_cls=True,
            lang=_map_lang_to_paddle(lang),
        )
        self._name = "paddle"

    @property
    def name(self) -> str:
        return self._name

    def recognize(self, image: np.ndarray) -> OcrPageResult:
        result = self.ocr.ocr(image)
        if not result or not result[0]:
            return OcrPageResult(text="", confidence=0.0, words=[])

        lines: list[str] = []
        words: list[OcrWord] = []
        confidences: list[float] = []

        for entry in result[0]:
            box, payload = entry
            text = str(payload[0]).strip()
            conf = float(payload[1])
            if not text:
                continue

            xs = [int(point[0]) for point in box]
            ys = [int(point[1]) for point in box]
            bbox = [min(xs), min(ys), max(xs), max(ys)]

            lines.append(text)
            words.append(OcrWord(text=text, confidence=conf, bbox=bbox))
            confidences.append(conf)

        avg_conf = float(np.mean(confidences)) if confidences else 0.0
        return OcrPageResult(text="\n".join(lines), confidence=avg_conf, words=words)


def available_ocr_backends() -> list[str]:
    engines: list[str] = []

    if PaddleOCR is not None:
        engines.append("paddle")

    if pytesseract is not None and TesseractOutput is not None:
        try:
            pytesseract.get_tesseract_version()
            engines.append("tesseract")
        except Exception:
            pass

    return engines


def create_ocr_engine(engine_name: str, lang: str) -> OcrEngine:
    normalized = engine_name.lower().strip()

    if normalized == "auto":
        errors = []
        for candidate in ("paddle", "tesseract"):
            try:
                return create_ocr_engine(candidate, lang)
            except Exception as e:
                errors.append(f"{candidate}: {e}")
                continue
        raise RuntimeError(
            f"No OCR engine available. Errors: {'; '.join(errors)}"
        )

    if normalized == "paddle":
        return PaddleOcrEngine(lang)
    if normalized == "tesseract":
        return TesseractOcrEngine(lang)

    raise RuntimeError(f"Unsupported OCR engine: {engine_name}")


def _map_lang_to_paddle(lang: str) -> str:
    lowered = lang.lower()
    if "kor" in lowered or "ko" in lowered:
        return "korean"
    if "chi" in lowered or "zh" in lowered:
        return "ch"
    if "jpn" in lowered or "ja" in lowered:
        return "japan"
    return "en"
