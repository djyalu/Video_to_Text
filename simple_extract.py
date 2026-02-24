"""
simple_extract.py
-----------------
2초 간격으로 프레임을 캡처하고 OCR을 수행한 뒤,
중복 텍스트를 제거하고 하나의 텍스트 파일로 통합합니다.
"""
import sys
import json
import time
from pathlib import Path
from difflib import SequenceMatcher

import cv2
import numpy as np


# ---------------------------------------------------------------------------
# 1. OCR 엔진 초기화 (PaddleOCR 2.7.x 호환)
# ---------------------------------------------------------------------------
def create_ocr():
    try:
        from paddleocr import PaddleOCR
        ocr = PaddleOCR(lang="korean")
        return ocr, "paddle"
    except Exception as e:
        print(f"[WARN] PaddleOCR load failed: {e}")

    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        return None, "tesseract"
    except Exception as e:
        print(f"[WARN] Tesseract load failed: {e}")

    print("[ERROR] No OCR engine available. Install paddleocr or tesseract.")
    sys.exit(1)


def ocr_image(image: np.ndarray, ocr_obj, engine_type: str) -> str:
    """이미지에서 텍스트를 추출하여 문자열로 반환."""
    if engine_type == "paddle":
        result = ocr_obj.ocr(image)
        if not result or not result[0]:
            return ""
        lines = []
        for entry in result[0]:
            box, payload = entry
            text = str(payload[0]).strip()
            if text:
                lines.append(text)
        return "\n".join(lines)
    else:
        import pytesseract
        text = pytesseract.image_to_string(image, lang="kor+eng", config="--psm 6")
        return text.strip()


# ---------------------------------------------------------------------------
# 2. 프레임 추출 (interval_sec 초 간격)
# ---------------------------------------------------------------------------
def extract_frames(video_path: str, interval_sec: float = 2.0):
    """비디오에서 interval_sec 초 간격으로 프레임을 추출."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"[ERROR] Cannot open video: {video_path}")
        sys.exit(1)

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps
    frame_interval = int(fps * interval_sec)

    print(f"  Video FPS: {fps:.1f}, Total frames: {total_frames}, Duration: {duration:.1f}s")
    print(f"  Capture interval: {interval_sec}s ({frame_interval} frames)")

    frames = []
    idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % frame_interval == 0:
            timestamp = idx / fps
            frames.append((timestamp, frame.copy()))
        idx += 1

    cap.release()
    print(f"  Captured {len(frames)} frames")
    return frames


# ---------------------------------------------------------------------------
# 3. 텍스트 유사도 기반 중복 제거
# ---------------------------------------------------------------------------
def similarity(a: str, b: str) -> float:
    """두 텍스트의 유사도(0.0 ~ 1.0)를 반환."""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def deduplicate_texts(texts: list[dict], threshold: float = 0.6) -> list[dict]:
    """
    연속된 프레임에서 유사도가 threshold 이상이면 중복으로 판단하여 제거.
    중복 구간에서는 가장 긴(텍스트가 풍부한) 것을 대표로 선택.
    """
    if not texts:
        return []

    unique = [texts[0]]
    for current in texts[1:]:
        prev = unique[-1]
        sim = similarity(prev["text"], current["text"])
        if sim >= threshold:
            # 중복 -> 더 긴 텍스트를 유지
            if len(current["text"]) > len(prev["text"]):
                unique[-1] = current
        else:
            unique.append(current)

    return unique


# ---------------------------------------------------------------------------
# 4. 메인 실행
# ---------------------------------------------------------------------------
def main():
    video_path = "source/capture video.mp4"
    output_txt = Path("추출결과.txt")
    output_json = Path("추출결과_상세.json")
    interval_sec = 2.0

    print("=" * 60)
    print("  Simple Video-to-Text Extractor")
    print("  2-second interval capture + deduplicate")
    print("=" * 60)

    # Step 1: OCR 엔진 초기화
    print("\n[Step 1/4] OCR engine loading...")
    ocr_obj, engine_type = create_ocr()
    print(f"  Engine: {engine_type}")

    # Step 2: 프레임 추출
    print(f"\n[Step 2/4] Extracting frames every {interval_sec}s...")
    frames = extract_frames(video_path, interval_sec)

    # Step 3: 각 프레임에 대해 OCR 수행
    print(f"\n[Step 3/4] Running OCR on {len(frames)} frames...")
    all_texts = []
    start_time = time.time()

    for i, (timestamp, frame) in enumerate(frames):
        text = ocr_image(frame, ocr_obj, engine_type)
        minutes = int(timestamp // 60)
        seconds = int(timestamp % 60)

        all_texts.append({
            "frame_index": i + 1,
            "timestamp": f"{minutes:02d}:{seconds:02d}",
            "timestamp_sec": round(timestamp, 2),
            "text": text,
        })

        # 진행 상황 표시
        progress = (i + 1) / len(frames) * 100
        elapsed = time.time() - start_time
        if i > 0:
            eta = elapsed / (i + 1) * (len(frames) - i - 1)
        else:
            eta = 0
        print(f"  [{i+1}/{len(frames)}] {progress:.0f}% | {minutes:02d}:{seconds:02d} | "
              f"ETA: {eta:.0f}s | chars: {len(text)}", end="\r")

    print(f"\n  OCR complete. Elapsed: {time.time() - start_time:.1f}s")

    # Step 4: 중복 제거 및 통합
    print(f"\n[Step 4/4] Deduplicating texts...")
    # 빈 텍스트 제거
    non_empty = [t for t in all_texts if t["text"].strip()]
    print(f"  Non-empty frames: {len(non_empty)} / {len(all_texts)}")

    unique_texts = deduplicate_texts(non_empty, threshold=0.6)
    print(f"  After deduplication: {len(unique_texts)} unique pages")

    # 텍스트 파일 저장
    with open(output_txt, "w", encoding="utf-8") as f:
        for item in unique_texts:
            f.write(f"\n{'='*50}\n")
            f.write(f"[{item['timestamp']}] Frame #{item['frame_index']}\n")
            f.write(f"{'='*50}\n")
            f.write(item["text"] + "\n")

    # JSON 상세 저장
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump({
            "total_frames_captured": len(all_texts),
            "non_empty_frames": len(non_empty),
            "unique_pages": len(unique_texts),
            "engine": engine_type,
            "interval_sec": interval_sec,
            "pages": unique_texts,
        }, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"  Done!")
    print(f"  Text file  : {output_txt.absolute()}")
    print(f"  Detail JSON: {output_json.absolute()}")
    print(f"  Total unique pages: {len(unique_texts)}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
