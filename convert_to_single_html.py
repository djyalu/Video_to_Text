
import os
import base64
import re
from pathlib import Path
from bs4 import BeautifulSoup

def embed_images_in_html(html_path, output_path=None):
    """HTML 파일 내의 모든 로컬 이미지 경로를 Base64 데이터로 변환하여 삽입합니다."""
    if not os.path.exists(html_path):
        print(f"Error: {html_path} not found.")
        return

    print(f"Reading {html_path}...")
    with open(html_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')

    images = soup.find_all('img')
    print(f"Found {len(images)} images. Embedding...")

    for img in images:
        src = img.get('src')
        if not src:
            continue
        
        # 이미 base64인 경우 건너뜀
        if src.startswith('data:'):
            continue
            
        # 로컬 경로 확인 (현재 디렉토리 기준)
        img_path = Path(src)
        if not img_path.is_absolute():
            # 상대 경로인 경우 HTML 파일 위치 기준으로 처리 (여기서는 프로젝트 루트 기준)
            img_full_path = Path(os.path.dirname(html_path)) / img_path
        else:
            img_full_path = img_path

        if img_full_path.exists():
            ext = img_full_path.suffix.lower().replace('.', '')
            if ext == 'jpg': ext = 'jpeg'
            
            with open(img_full_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                img['src'] = f"data:image/{ext};base64,{encoded_string}"
                # print(f"  Embedded: {src}")
        else:
            print(f"  Warning: Image not found: {img_full_path}")

    if output_path is None:
        output_path = html_path

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(str(soup))
    
    print(f"Success! Integrated document saved: {output_path}")

if __name__ == "__main__":
    # Visual Handbook 처리
    embed_images_in_html('Visual_ServiceNow_Handbook.html')
