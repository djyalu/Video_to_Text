from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class FrameCandidate:
    page_number: int
    image_path: Path
    frame_index: int
    timestamp_sec: float
    focus_score: float


@dataclass(slots=True)
class OcrWord:
    text: str
    confidence: float
    bbox: list[int]


@dataclass(slots=True)
class OcrPageResult:
    text: str
    confidence: float
    words: list[OcrWord] = field(default_factory=list)


@dataclass(slots=True)
class DocumentPage:
    page_number: int
    image_path: Path
    text: str
    confidence: float
    timestamp_sec: float
    raw_text: str
