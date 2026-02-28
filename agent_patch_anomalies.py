import os
import cv2
import json
import logging
import concurrent.futures
from pathlib import Path
from paddleocr import PaddleOCR
from deep_translator import GoogleTranslator
import time
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

def get_indent(x_min, col_min_x, char_width, is_code):
    if not is_code: return ""
    diff = x_min - col_min_x
    if diff <= 0 or char_width <= 0: return ""
    spaces = int(round(diff / char_width))
    return " " * min(spaces, 20)

def detect_code(text):
    text = text.strip()
    words = text.split()
    if len(words) > 20: 
        # Usually prose if it's that long, unless it's a huge function signature
        if not ("function" in text and "{" in text):
            return False
            
    # Stricter Code detection
    # Must have typical structure
    if re.search(r"^\s*(var|let|const|function|if\s*\(|while\s*\(|for\s*\(|return)\b", text):
        return True
    if re.search(r"(GlideRecord|getValue|setValue|\.update\(\)|\.query\(\)|\.next\(\)|gs\.[A-Za-z]+)", text):
        return True
    if re.search(r"^[\{\}\[\]\);]+$", text): # standalone brackets
        return True
    if text.startswith("//") or text.startswith("/*"):
        return True
        
    return False

def ocr_page(page_idx, img_path):
    try:
        ocr = PaddleOCR(use_angle_cls=False, lang='en', show_log=False)
        img = cv2.imread(str(img_path))
        if img is None: return None
        h, w = img.shape[:2]
        res = ocr.ocr(img, cls=False)
        if not res or not res[0]: return None
        
        boxes = []
        for entry in res[0]:
            box, (text, score) = entry
            x_min = min(pt[0] for pt in box)
            x_max = max(pt[0] for pt in box)
            y_min = min(pt[1] for pt in box)
            y_max = max(pt[1] for pt in box)
            width = x_max - x_min
            x_center = (x_min + x_max) / 2
            
            col = "full"
            if width > w * 0.55:
                col = "full"
            elif y_min < h * 0.05 or y_max > h * 0.95:
                col = "full"
            elif x_center < w * 0.5:
                col = "left"
            else:
                col = "right"
                
            boxes.append({
                "text": text,
                "y": y_min,
                "x": x_min,
                "col": col,
                "w": width
            })
            
        boxes.sort(key=lambda b: b["y"])
        
        left_min_x = min([b["x"] for b in boxes if b["col"] == "left"] + [w])
        right_min_x = min([b["x"] for b in boxes if b["col"] == "right"] + [w])
        full_min_x = min([b["x"] for b in boxes if b["col"] == "full"] + [w])
        
        bands = []
        current_band = {"left": [], "right": []}
        
        for b in boxes:
            if b["col"] == "full":
                if current_band["left"] or current_band["right"]:
                    bands.append(current_band)
                    current_band = {"left": [], "right": []}
                bands.append({"full": [b]})
            else:
                current_band[b["col"]].append(b)
                
        if current_band["left"] or current_band["right"]:
            bands.append(current_band)
            
        final_lines = []
        for band in bands:
            if "full" in band:
                for b in band["full"]:
                    final_lines.append(b)
            else:
                for b in band["left"]:
                    final_lines.append(b)
                for b in band["right"]:
                    final_lines.append(b)
                    
        parsed_blocks = []
        current_prose = []
        current_code = []
        in_code = False
        
        for b in final_lines:
            text = b["text"].strip()
            # Clean OCR garbage more aggressively
            text = re.sub(r"\bO1\b", "Of", text)
            text = re.sub(r"\bnextO\b", "next()", text)
            text = re.sub(r"\bqueryO\b;?", "query();", text)
            text = re.sub(r"\binsertO\b;?", "insert();", text)
            text = re.sub(r"\bCincident\b", "('incident')", text)
            text = re.sub(r"\bgetValueC\b", "getValue(", text)
            
            b_is_code = detect_code(text)
            
            char_w = b["w"] / max(len(text), 1)
            c_min = left_min_x if b["col"]=="left" else (right_min_x if b["col"]=="right" else full_min_x)
            
            # If prose, no indent. If code, calculate.
            indent = get_indent(b["x"], c_min, char_w, b_is_code)
            
            if b_is_code:
                if current_prose:
                    parsed_blocks.append({"type": "prose", "text": " ".join(current_prose)})
                    current_prose = []
                current_code.append(indent + text)
                in_code = True
            else:
                if current_code:
                    parsed_blocks.append({"type": "code", "text": "\n".join(current_code)})
                    current_code = []
                current_prose.append(text)
                in_code = False
                
        if current_prose:
            parsed_blocks.append({"type": "prose", "text": " ".join(current_prose)})
        if current_code:
            parsed_blocks.append({"type": "code", "text": "\n".join(current_code)})
            
        return {
            "page_num": page_idx,
            "blocks": parsed_blocks
        }
    except Exception as e:
        logging.error(f"Error on page {page_idx}: {e}")
        return None

def translate_prose(en_text):
    if len(en_text) < 10: return ""
    try:
        translator = GoogleTranslator(source="en", target="ko")
        return translator.translate(en_text[:4500])
    except:
        time.sleep(1)
        try:
            translator = GoogleTranslator(source="en", target="ko")
            return translator.translate(en_text[:4500])
        except:
            return ""

def worker_agent(page_idx):
    img_path = f"f:/projects/Video_to_Text/pages_compressed/page_{page_idx:03d}.jpg"
    if not os.path.exists(img_path): return None
    
    res = ocr_page(page_idx, img_path)
    if not res: return None
    
    en_full = []
    ko_full = []
    codes = []
    
    for b in res["blocks"]:
        if b["type"] == "prose":
            en_t = b["text"]
            en_full.append(en_t)
            # Translation
            ko_t = translate_prose(en_t)
            if ko_t: ko_full.append(ko_t)
        elif b["type"] == "code":
            codes.append(b["text"])
            
    final_en = "\n\n".join(en_full)
    final_ko = "\n\n".join(ko_full)
    
    return {
        "page_num": page_idx,
        "en": final_en,
        "ko": final_ko,
        "codes": codes
    }

def main():
    print("[Project Manager] Correcting 46 anomalous pages found in final audit.")
    try:
        with open('audit_report_full.json', 'r', encoding='utf-8') as f:
            audit_data = json.load(f)
            pages_to_process = [int(k) for k in audit_data.keys()]
    except Exception:
        print("Could not load audit_report_full.json")
        return

    # Load existing to overwrite
    try:
        with open('AGENT_100_CORRECTIONS.json', 'r', encoding='utf-8') as f:
            results = json.load(f)
    except:
        results = {}
    
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(worker_agent, p): p for p in pages_to_process}
        
        completed = 0
        for fut in concurrent.futures.as_completed(futures):
            try:
                r = fut.result()
                completed += 1
                if r:
                    p_num = r["page_num"]
                    results[str(p_num)] = {
                        "en": r["en"],
                        "ko": r["ko"],
                        "codes": r["codes"]
                    }
                if completed % 5 == 0:
                    print(f"[QA] Corrected {completed} / {len(pages_to_process)} anomalous pages.")
            except Exception as e:
                print(f"Error on future: {e}")
                
    with open("AGENT_100_CORRECTIONS.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
        
    print("[Architect] Patch completed and grafted onto AGENT_100_CORRECTIONS.json")

if __name__ == "__main__":
    main()
