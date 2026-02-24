import cv2
import json
import os
from pathlib import Path

def extract_frames():
    video_path = "source/capture video.mp4"
    json_path = "추출결과_상세.json"
    output_dir = Path("pages")
    output_dir.mkdir(exist_ok=True)
    
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        pages = data.get("pages", [])
        
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("Error: Could not open video.")
        return
        
    for i, p in enumerate(pages):
        ts = p['timestamp'] # format "MM:SS"
        try:
            m, s = map(int, ts.split(':'))
            msec = (m * 60 + s) * 1000
            cap.set(cv2.CAP_PROP_POS_MSEC, msec)
            ret, frame = cap.read()
            if ret:
                out_path = output_dir / f"page_{i+1:03d}.jpg"
                cv2.imwrite(str(out_path), frame)
                if (i+1) % 20 == 0:
                    print(f"Extracted {i+1}/{len(pages)} frames...")
            else:
                print(f"Warning: Could not read frame at {ts}")
        except Exception as e:
            print(f"Error at page {i+1} ({ts}): {e}")
            
    cap.release()
    print("Done! All frames extracted.")

if __name__ == "__main__":
    extract_frames()
