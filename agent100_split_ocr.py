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

# All pages are Kindle landscape screenshots (1226x822) with 2 pages side-by-side.
# No single-column exceptions needed - even pages with one-sided content benefit from splitting.
SINGLE_COLUMN_PAGES = set()  # Empty - all pages get 2-column split

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
    prev_blank = False
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
        stripped = cl.strip()
        # Skip single-char garbage
        if len(stripped) <= 1 and not stripped.isalnum():
            continue
        if not stripped:
            # Preserve blank lines as paragraph breaks (max 1 consecutive)
            if not prev_blank and cleaned:
                cleaned.append('')
                prev_blank = True
        else:
            cleaned.append(stripped)
            prev_blank = False
    return '\n'.join(cleaned)


def is_code_line(line):
    """Determine if a single line is source code (strict detection).
    Requires syntactic patterns, not just keyword presence in prose.
    """
    stripped = line.strip()
    if not stripped:
        return False
    # Definite code patterns (syntactic)
    code_patterns = [
        r'^var\s+\w+\s*=',            # var x = ...
        r'^let\s+\w+\s*=',            # let x = ...
        r'^const\s+\w+\s*=',          # const x = ...
        r'^function\s+\w+\s*\(',      # function name(...
        r'^if\s*\(.+\)\s*\{',         # if (...) {
        r'^\}\s*else\s*(if)?\s*',      # } else ...
        r'^while\s*\(.+\)\s*\{',      # while (...) {
        r'^for\s*\(.+\)\s*\{',        # for (...) {
        r'^return\s+',                # return ...
        r'^throw\s+new\s+',           # throw new ...
        r'\w+\.\w+\(.*\);?\s*$',     # obj.method(...);
        r'^\s*[\{\}]\s*$',            # { or } alone
        r'^\s*\);?\s*$',              # ) or ); alone
        r'//.*$',                     # // comment at start
        r'^/\*',                      # /* comment
        r'^\*/',                      # */ comment end
        r'\w+\s*=\s*new\s+\w+',      # x = new Class
        r'\w+\.addQuery\(',           # .addQuery(
        r'\w+\.addEncodedQuery\(',    # .addEncodedQuery(
        r'\w+\.setValue\(',           # .setValue(
        r'\w+\.getValue\(',           # .getValue(
        r'\w+\.query\(\)',            # .query()
        r'\w+\.next\(\)',             # .next()
        r'\w+\.hasNext\(\)',          # .hasNext()
        r'gs\.\w+\(',                 # gs.log(, gs.info(
        r'current\.\w+',              # current.field
    ]
    for p in code_patterns:
        if re.search(p, stripped):
            return True
    return False


def split_prose_and_code(text):
    """Split text into prose and code blocks.
    Uses strict code detection - requires 2+ consecutive code lines
    to form a code block. Single code-like lines in prose stay as prose.
    """
    lines = text.split('\n')
    # First pass: label each line
    labels = []
    for line in lines:
        labels.append('code' if is_code_line(line) else 'prose')
    
    # Second pass: isolated code lines (surrounded by prose) -> prose
    # Require at least 2 consecutive code lines to form a block
    for i in range(len(labels)):
        if labels[i] == 'code':
            prev_code = (i > 0 and labels[i-1] == 'code')
            next_code = (i < len(labels)-1 and labels[i+1] == 'code')
            if not prev_code and not next_code:
                labels[i] = 'prose'  # isolated code line -> treat as prose
    
    # Third pass: group consecutive same-type lines
    blocks = []
    current_type = labels[0] if labels else 'prose'
    current_lines = []
    
    for i, line in enumerate(lines):
        if labels[i] != current_type and current_lines:
            blocks.append({
                "type": current_type,
                "text": '\n'.join(current_lines)
            })
            current_lines = []
            current_type = labels[i]
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
    2. Split left/right
    3. Tesseract OCR each half (preserving paragraph breaks)
    4. Combine: left text first, then right text
    5. Translate paragraph by paragraph
    """
    img_path = PAGES_DIR / f"page_{page_idx:03d}.jpg"
    if not img_path.exists():
        return None
    
    try:
        img = Image.open(img_path).convert("RGB")
        w, h = img.size
        
        # All images are landscape Kindle screenshots - always split
        crop_bottom = int(h * 0.94)
        crop_top = int(h * 0.005)
        margin = int(w * 0.015)
        mid = w // 2
        
        # Left half OCR
        left_img = img.crop((margin, crop_top, mid - margin, crop_bottom))
        left_raw = pytesseract.image_to_string(left_img, lang='eng')
        left_text = clean_ocr_text(left_raw)
        
        # Right half OCR
        right_img = img.crop((mid + margin, crop_top, w - margin, crop_bottom))
        right_raw = pytesseract.image_to_string(right_img, lang='eng')
        right_text = clean_ocr_text(right_raw)
        
        # Combine: left first (with paragraph break between halves)
        parts = []
        if left_text.strip():
            parts.append(left_text)
        if right_text.strip():
            parts.append(right_text)
        full_text = '\n\n'.join(parts)
        
        if not full_text.strip():
            logging.warning(f"[Agent {page_idx:03d}] No text extracted")
            return {"page_num": page_idx, "en": "", "ko": "", "codes": []}
        
        # Split into prose and code blocks
        blocks = split_prose_and_code(full_text)
        
        en_prose_parts = []
        code_parts = []
        for b in blocks:
            if b["type"] == "prose":
                en_prose_parts.append(b["text"])
            else:
                code_parts.append(b["text"])
        
        # Join prose with paragraph breaks preserved
        en_full = '\n\n'.join(en_prose_parts)
        
        # Smart line joining: detect list/TOC vs prose
        def smart_join_lines(paragraph_text):
            """Join lines within a paragraph intelligently.
            - Short average line length = list/TOC → preserve line breaks
            - Long average line length = prose → join with spaces
            """
            lines = [l.strip() for l in paragraph_text.split('\n') if l.strip()]
            if not lines:
                return ""
            avg_len = sum(len(l) for l in lines) / len(lines)
            # If avg line < 45 chars AND more than 3 lines → list-style
            if avg_len < 45 and len(lines) > 3:
                return '\n'.join(lines)  # Keep line breaks
            else:
                return ' '.join(lines)  # Join as prose
        
        # Split into paragraphs
        en_paragraphs = [p.strip() for p in en_full.split('\n\n') if p.strip()]
        ko_paragraphs = []
        
        # Translate paragraph by paragraph
        for para in en_paragraphs:
            joined = smart_join_lines(para)
            ko_para = translate_text(joined)
            if ko_para:
                ko_paragraphs.append(ko_para)
        ko_full = '\n\n'.join(ko_paragraphs)
        
        # Format EN lines within paragraphs
        en_formatted = '\n\n'.join(
            smart_join_lines(p)
            for p in en_paragraphs
        )
        
        logging.info(f"[Agent {page_idx:03d}] Done EN={len(en_formatted)}c KO={len(ko_full)}c Paras={len(en_paragraphs)} Codes={len(code_parts)}")
        
        return {
            "page_num": page_idx,
            "en": en_formatted,
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
