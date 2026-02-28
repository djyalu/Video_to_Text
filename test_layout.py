import cv2
import json

def test_heuristic():
    print("Testing OCR heuristic...")
    img = cv2.imread("f:/projects/Video_to_Text/pages_compressed/page_139.jpg")
    if img is None:
        print("Image not found")
        return
    h, w = img.shape[:2]
    print(f"Image 139 shape: {w}x{h}")
    
    from paddleocr import PaddleOCR
    ocr = PaddleOCR(use_angle_cls=False, lang='en')
    res = ocr.ocr(img, cls=False)
    
    if not res or not res[0]:
        print("No OCR output")
        return
        
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
        if width > w * 0.6:  # somewhat large threshold for full width
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
            "width": width
        })
        
    # Sort primarily by Y
    boxes.sort(key=lambda b: b["y"])
    
    # Create bands
    bands = []
    current_band = {"left": [], "right": []}
    
    for b in boxes:
        if b["col"] == "full":
            # flush current band if not empty
            if current_band["left"] or current_band["right"]:
                bands.append(current_band)
                current_band = {"left": [], "right": []}
            bands.append({"full": [b]})
        else:
            current_band[b["col"]].append(b)
            
    if current_band["left"] or current_band["right"]:
        bands.append(current_band)
        
    # Reconstruct text
    final_text_lines = []
    for band in bands:
        if "full" in band:
            for b in band["full"]:
                final_text_lines.append(b["text"])
        else:
            for b in band["left"]:
                final_text_lines.append(b["text"])
            for b in band["right"]:
                final_text_lines.append(b["text"])
                
    print("\n--- RECONSTRUCTED TEXT ---")
    for t in final_text_lines:
        print(t)
        
if __name__ == "__main__":
    test_heuristic()
