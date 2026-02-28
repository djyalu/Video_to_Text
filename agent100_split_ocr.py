"""
=======================================================
100 Agents 2-Column OCR Pipeline v2 (Tesseract)
=======================================================
Original images contain 2 pages side-by-side (Kindle screenshots).
Split at center: Left half OCR top-to-bottom, then Right half.
"""

import os
import sys
import json
import logging
import concurrent.futures
import time
import re
from pathlib import Path
from PIL import Image
import pytesseract

# Windows stdout encoding fix
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# Tesseract path
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('agent100_split_ocr.log', encoding='utf-8')
    ]
)

# --- Configuration ---
PAGES_DIR = Path("f:/projects/Video_to_Text/pages")
OUTPUT_JSON = Path("f:/projects/Video_to_Text/AGENT_100_CORRECTIONS.json")
TOTAL_PAGES = 204
MAX_WORKERS = 8  # Tesseract is lightweight, can run more threads

# Single-column pages (cover, blank, chapter dividers)
SINGLE_COLUMN_PAGES = {1, 2, 3, 4, 5, 9, 12, 39, 48, 51, 52, 61, 70, 76, 118, 125, 158, 181, 194}

# OCR noise patterns
NOISE_PATTERNS = [
    r"\d+\s*minute[s]?\s*left\s*in\s*chapter",
    r"\d+\s*hrs?\s*\d*\s*mins?\s*left\s*in\s*book",
    r"Location\s*\d+\s*of\s*\d+",
    r"Page\s*\d+\s*of\s*\d+",
    r"^\s*\d+\s*%\s*$",
    r"^\s*[Ff]\d*\s*%\s*$",
    r"^\s*F\d+\s*[%]?\s*$",
    r"^\s*Fege\s*\d*\s*$",
    r"^\s*Feg[e#]?\s*\d+.*$",
    r"^\s*Fg#?\s*\d+.*$",
    r"^\s*Fxg\d*.*$",
    r"^\s*[Ll]acato?r?\s*\d+.*$",
    r"^\s*[Mm]rt\s*\d+.*$",
    r"^\s*[Hh]rt\s*\d+.*$",
    r"^\s*remhe\s*tef.*$",
    r"^\s*mhe\s*(?:teft|wft|wt).*$",
    r"^\s*rent?\s*he(?:ft)?.*$",
    r"^\s*tht\s*h[eo]f.*$",
    r"^\s*remle\s*tef.*$",
    r"^\s*rem,?he\s*teft.*$",
    r"^\s*\d+\s*h(?:rs?|es)\s*\d*\s*(?:nves|eves|ovins?|ovns|aves|vns|ins).*$",
    r"^\s*rt\s*\d+\s*(?:is|ies|es|eves).*$",
    r"^\s*[Pp]age\s*\d+.*$",
]


def clean_ocr_text(text):
    """Clean OCR noise from text while preserving paragraph structure."""
    lines = text.split('\n')
    cleaned = []
    for line in lines:
        cl = line.rstrip()
        # Apply noise patterns
        skip = False
        for p in NOISE_PATTERNS:
            if re.match(p, cl, re.IGNORECASE):
                skip = True
                break
        if skip:
            continue
        # Skip very short garbage lines (single chars)
        stripped = cl.strip()
        if len(stripped) <= 1 and not stripped.isalnum():
            continue
        if stripped:
            cleaned.append(stripped)
    return '\n'.join(cleaned)


def detect_code_block(text):
    """Detect if a text block is source code."""
    code_indicators = [
        "var ", "function ", "if (", "while (", "for (", "return ",
        "GlideRecord", ".query(", ".next(", "gs.", "current.",
        ".setValue(", ".getValue(", ".addQuery(", ".addEncodedQuery(",
        "new ", "this.", "console.log", "typeof ", "try {", "catch (",
        "= function", "=>", "===", "!==", "||", "&&"
    ]
    lines = text.strip().split('\n')
    code_score = 0
    for line in lines:
        for kw in code_indicators:
            if kw in line:
                code_score += 1
                break
        if line.strip().startswith('//') or line.strip().startswith('/*'):
            code_score += 1
        if re.match(r'^\s*[\{\};\)]\s*$', line.strip()):
            code_score += 1
    # If more than 30% of lines look like code
    ratio = code_score / max(len(lines), 1)
    return ratio > 0.3


def split_prose_and_code(text):
    """Split text into prose and code blocks."""
    lines = text.split('\n')
    blocks = []
    current_type = None
    current_lines = []
    
    for line in lines:
        is_code_line = any(kw in line for kw in [
            "var ", "function", ".query(", ".next(", "gs.", "current.",
            ".setValue(", ".getValue(", "GlideRecord", "//", "/*",
        ]) or re.match(r'^\s*[\{\};\)]\s*$', line.strip())
        
        line_type = "code" if is_code_line else "prose"
        
        if line_type != current_type and current_lines:
            blocks.append({
                "type": current_type,
                "text": '\n'.join(current_lines)
            })
            current_lines = []
        
        current_type = line_type
        current_lines.append(line)
    
    if current_lines:
        blocks.append({
            "type": current_type,
            "text": '\n'.join(current_lines)
        })
    
    return blocks


def translate_text(en_text):
    """Translate English text to Korean."""
    if len(en_text.strip()) < 10:
        return ""
    try:
        from deep_translator import GoogleTranslator
        translator = GoogleTranslator(source="en", target="ko")
        # Split into chunks of 4500 chars
        chunks = []
        remaining = en_text
        while remaining:
            chunk = remaining[:4500]
            chunks.append(chunk)
            remaining = remaining[4500:]
        
        translated_parts = []
        for chunk in chunks:
            try:
                t = translator.translate(chunk)
                if t:
                    translated_parts.append(t)
            except Exception:
                time.sleep(1)
                try:
                    t = translator.translate(chunk)
                    if t:
                        translated_parts.append(t)
                except Exception:
                    pass
        
        return '\n'.join(translated_parts)
    except Exception:
        return ""


def worker_agent(page_idx):
    """Single page worker agent.
    1. Load image
    2. If 2-column: split left/right
    3. OCR each region top-to-bottom
    4. Combine: left text first, then right text
    5. Translate to Korean
    """
    img_path = PAGES_DIR / f"page_{page_idx:03d}.jpg"
    if not img_path.exists():
        return None
    
    try:
        img = Image.open(img_path).convert("RGB")
        w, h = img.size
        
        # Determine if single or 2-column
        ratio = w / h
        is_single = page_idx in SINGLE_COLUMN_PAGES or ratio < 1.1
        
        if is_single:
            logging.info(f"[Agent {page_idx:03d}] Single-column OCR ({w}x{h})")
            # Crop bottom kindle bar
            cropped = img.crop((0, 0, w, int(h * 0.95)))
            raw_text = pytesseract.image_to_string(cropped, lang='eng')
            full_text = clean_ocr_text(raw_text)
        else:
            logging.info(f"[Agent {page_idx:03d}] 2-column split OCR ({w}x{h})")
            
            # Crop kindle bottom bar
            crop_bottom = int(h * 0.94)
            crop_top = int(h * 0.005)
            margin = int(w * 0.015)
            mid = w // 2
            
            # Left half
            left_img = img.crop((margin, crop_top, mid - margin, crop_bottom))
            left_text = pytesseract.image_to_string(left_img, lang='eng')
            left_clean = clean_ocr_text(left_text)
            
            # Right half
            right_img = img.crop((mid + margin, crop_top, w - margin, crop_bottom))
            right_text = pytesseract.image_to_string(right_img, lang='eng')
            right_clean = clean_ocr_text(right_text)
            
            # Combine: left first, then right
            parts = []
            if left_clean:
                parts.append(left_clean)
            if right_clean:
                parts.append(right_clean)
            full_text = '\n\n'.join(parts)
        
        if not full_text.strip():
            logging.warning(f"[Agent {page_idx:03d}] No text extracted")
            return {"page_num": page_idx, "en": "", "ko": "", "codes": []}
        
        # Split into prose and code
        blocks = split_prose_and_code(full_text)
        
        en_prose_parts = []
        code_parts = []
        for b in blocks:
            if b["type"] == "prose":
                en_prose_parts.append(b["text"])
            else:
                code_parts.append(b["text"])
        
        en_full = '\n'.join(en_prose_parts)
        
        # Translate
        ko_full = translate_text(en_full)
        
        logging.info(f"[Agent {page_idx:03d}] Done EN={len(en_full)}c KO={len(ko_full)}c Codes={len(code_parts)}")
        
        return {
            "page_num": page_idx,
            "en": en_full,
            "ko": ko_full,
            "codes": code_parts
        }
        
    except Exception as e:
        logging.error(f"[Agent {page_idx:03d}] Error: {e}")
        return None


def main():
    print("=" * 60)
    print("[PM] 100 Agents 2-Column OCR Pipeline v2 Starting")
    print(f"[PM] Target: {TOTAL_PAGES} pages")
    print(f"[PM] Workers: {MAX_WORKERS}")
    print("=" * 60)
    
    pages_to_process = list(range(1, TOTAL_PAGES + 1))
    results = {}
    
    start_time = time.time()
    
    # Use ThreadPoolExecutor since tesseract runs as subprocess
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(worker_agent, p): p for p in pages_to_process}
        
        completed = 0
        for fut in concurrent.futures.as_completed(futures):
            page_num = futures[fut]
            try:
                r = fut.result()
                completed += 1
                if r:
                    results[str(r["page_num"])] = {
                        "en": r["en"],
                        "ko": r["ko"],
                        "codes": r["codes"]
                    }
                
                if completed % 20 == 0:
                    elapsed = time.time() - start_time
                    rate = completed / elapsed * 60 if elapsed > 0 else 0
                    print(f"[QA] {completed}/{TOTAL_PAGES} pages done "
                          f"({elapsed:.0f}s, {rate:.1f} pages/min)")
                    
            except Exception as e:
                logging.error(f"[PM] Error page {page_num}: {e}")
    
    # Save results
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    elapsed = time.time() - start_time
    print("=" * 60)
    print(f"[PM] Complete! {len(results)}/{TOTAL_PAGES} pages processed")
    print(f"[PM] Time: {elapsed:.1f}s ({elapsed/60:.1f}min)")
    print(f"[PM] Output: {OUTPUT_JSON}")
    print("=" * 60)


if __name__ == "__main__":
    main()
