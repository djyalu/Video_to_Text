from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from .models import FrameCandidate


@dataclass(slots=True)
class ExtractionConfig:
    sample_fps: float = 6.0
    transition_threshold: float = 18.0
    stable_threshold: float = 4.0
    min_transition_samples: int = 2
    min_stable_samples: int = 3
    min_page_gap_sec: float = 0.5
    dedupe_hamming_threshold: int = 6
    max_pages: int | None = None
    min_focus_score: float = 15.0
    use_hist: bool = True
    hist_threshold: float = 0.92  # Histogram similarity threshold (0~1, lower means more different)


def extract_page_frames(video_path: Path, pages_dir: Path, config: ExtractionConfig) -> list[FrameCandidate]:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")

    video_fps = cap.get(cv2.CAP_PROP_FPS)
    if not video_fps or np.isnan(video_fps):
        video_fps = 30.0

    sample_every = max(1, int(round(video_fps / max(config.sample_fps, 0.1))))

    frame_index = 0
    previous_sample: np.ndarray | None = None
    previous_hist: np.ndarray | None = None
    results: list[FrameCandidate] = []
    last_hash: np.ndarray | None = None
    last_saved_timestamp = -1e9

    state = "stable"
    stable_best: tuple[float, np.ndarray, int, float] | None = None
    settling_best: tuple[float, np.ndarray, int, float] | None = None
    transition_hits = 0
    stable_hits = 0

    def save_candidate(candidate: tuple[float, np.ndarray, int, float] | None) -> None:
        nonlocal last_hash, last_saved_timestamp
        if candidate is None:
            return
        if config.max_pages is not None and len(results) >= config.max_pages:
            return

        focus, best_frame, best_idx, timestamp = candidate
        if focus < config.min_focus_score:
            return

        if timestamp - last_saved_timestamp < config.min_page_gap_sec:
            return

        current_hash = _phash(best_frame)
        if last_hash is not None:
            dist = _hamming_distance(last_hash, current_hash)
            if dist <= config.dedupe_hamming_threshold:
                return

        page_number = len(results) + 1
        image_path = pages_dir / f"page_{page_number:04d}.jpg"
        cv2.imwrite(str(image_path), best_frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
        results.append(
            FrameCandidate(
                page_number=page_number,
                image_path=image_path,
                frame_index=best_idx,
                timestamp_sec=timestamp,
                focus_score=focus,
            )
        )
        last_hash = current_hash
        last_saved_timestamp = timestamp

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break

            if frame_index % sample_every != 0:
                frame_index += 1
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            small = cv2.resize(gray, (320, 180), interpolation=cv2.INTER_AREA)
            focus = _focus_score(gray)
            timestamp = frame_index / float(video_fps)
            current_candidate = (focus, frame.copy(), frame_index, timestamp)

            if previous_sample is None:
                stable_best = current_candidate
                previous_sample = small
                if config.use_hist:
                    previous_hist = _calc_hist(small)
                frame_index += 1
                continue

            # Signal 1: Pixel Difference
            diff = float(np.mean(cv2.absdiff(small, previous_sample)))
            
            # Signal 2: Histogram Correlation (Optional)
            hist_sim = 1.0
            if config.use_hist:
                current_hist = _calc_hist(small)
                hist_sim = cv2.compareHist(previous_hist, current_hist, cv2.HISTCMP_CORREL)
                previous_hist = current_hist

            # Transition detection: High diff OR Low hist similarity
            # (Note: Hist correlation 1.0 is identical, < 0.95 is different)
            is_transition = diff >= config.transition_threshold or (config.use_hist and hist_sim < config.hist_threshold)
            is_stable = diff <= config.stable_threshold and (not config.use_hist or hist_sim >= 0.99)

            if state == "stable":
                if stable_best is None or focus > stable_best[0]:
                    stable_best = current_candidate

                if is_transition:
                    transition_hits += 1
                else:
                    transition_hits = 0

                if transition_hits >= config.min_transition_samples:
                    save_candidate(stable_best)
                    if config.max_pages is not None and len(results) >= config.max_pages:
                        break
                    state = "transition"
                    stable_best = None
                    settling_best = None
                    transition_hits = 0
                    stable_hits = 0

            else:  # state == "transition"
                if is_stable:
                    stable_hits += 1
                    if settling_best is None or focus > settling_best[0]:
                        settling_best = current_candidate

                    if stable_hits >= config.min_stable_samples:
                        state = "stable"
                        stable_best = settling_best if settling_best is not None else current_candidate
                        settling_best = None
                        stable_hits = 0
                else:
                    stable_hits = 0

            previous_sample = small
            frame_index += 1
    finally:
        cap.release()

    if state == "stable":
        save_candidate(stable_best)
    elif settling_best is not None:
        save_candidate(settling_best)

    return results


def preprocess_for_ocr(image: np.ndarray) -> np.ndarray:
    if image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    gray = _auto_crop_content(gray)
    gray = cv2.resize(gray, None, fx=1.6, fy=1.6, interpolation=cv2.INTER_CUBIC)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    gray = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)
    bw = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        11,
    )
    return bw


def _auto_crop_content(gray: np.ndarray) -> np.ndarray:
    mask = gray < 245
    coords = np.argwhere(mask)
    if coords.size == 0:
        return gray

    y0, x0 = coords.min(axis=0)
    y1, x1 = coords.max(axis=0)
    pad = 20

    y0 = max(0, int(y0) - pad)
    x0 = max(0, int(x0) - pad)
    y1 = min(gray.shape[0] - 1, int(y1) + pad)
    x1 = min(gray.shape[1] - 1, int(x1) + pad)

    return gray[y0 : y1 + 1, x0 : x1 + 1]


def _calc_hist(image: np.ndarray) -> np.ndarray:
    hist = cv2.calcHist([image], [0], None, [256], [0, 256])
    cv2.normalize(hist, hist, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
    return hist


def _focus_score(gray: np.ndarray) -> float:
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def _phash(image: np.ndarray) -> np.ndarray:
    if image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    resized = cv2.resize(gray, (32, 32), interpolation=cv2.INTER_AREA)
    dct = cv2.dct(np.float32(resized))
    low_freq = dct[:8, :8]
    median = np.median(low_freq[1:])
    return (low_freq > median).astype(np.uint8).reshape(-1)


def _hamming_distance(a: np.ndarray, b: np.ndarray) -> int:
    return int(np.count_nonzero(a != b))
