"""
generate_visual_handbook.py (v2 - Fixed Placeholder)
===================================================
치환 로직의 중괄호 오류를 수정하여 이미지와 번역문을 정상적으로 삽입합니다.
"""
import os
import re
from pathlib import Path
from bs4 import BeautifulSoup
from textwrap import dedent

# ─── Configuration ──────────────────────────────────────────
INPUT_HTML = Path("ServiceNow_Handbook_Bilingual.html")
IMAGE_DIR = Path("pages")
OUTPUT_HTML = Path("Visual_ServiceNow_Handbook.html")

def clean_korean_text(text):
    """번역문에서 잔여 OCR 노이즈 및 불필요한 문구를 제거."""
    noise_patterns = [
        r"\d+\s*시간\s*\d+\s*분\s*남음",
        r"\d+\s*분\s*남음",
        r"페이지\s+\d+\s+/\s+\d+",
        r"위치\s+\d+\s+/\s+\d+",
        r"I\s+book",
        r"1\s+hr5",
        r"1\s+hrs",
        r"Chapter",
        r"목차",
        r"^\d+%$",
    ]
    for pat in noise_patterns:
        text = re.sub(pat, "", text, flags=re.IGNORECASE)
    
    # 2. 불필요한 공백 및 줄바꿈 정리
    text = re.sub(r"\s+", " ", text).strip()
    return text

def main():
    if not INPUT_HTML.exists():
        print(f"Error: {INPUT_HTML} not found.")
        return

    print("Parsing translations and images...")
    with open(INPUT_HTML, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    pages = soup.find_all("section", class_="page")
    handbook_html_parts = []

    for i, page in enumerate(pages, 1):
        img_path = f"pages/page_{i:03d}.jpg"
        
        ko_texts = []
        bilinguals = page.find_all("div", class_="bilingual")
        for bi in bilinguals:
            ko_p = bi.find("div", class_="lang-ko").p
            if ko_p:
                cleaned_ko = clean_korean_text(ko_p.get_text())
                if cleaned_ko:
                    ko_texts.append(cleaned_ko)
        
        code_blocks = []
        codes = page.find_all("div", class_="code-block")
        for code in codes:
            code_text = code.find("code").get_text()
            code_blocks.append(code_text)

        full_text = " ".join(ko_texts)
        code_html = "".join([f'<pre class="code-box"><code>{c}</code></pre>' for c in code_blocks])
        
        handbook_html_parts.append(f'''
        <div class="handbook-page" id="page-{i}">
            <div class="page-meta">Page {i} / {len(pages)}</div>
            <div class="content-wrapper">
                <div class="image-section">
                    <img src="{img_path}" alt="Original Frame {i}">
                </div>
                <div class="text-section">
                    <div class="translation-header">🇰🇷 한국어 번역 가이드</div>
                    <p class="translation-text">{full_text if full_text else "번역 텍스트를 구성 중입니다."}</p>
                    {code_html if code_blocks else ''}
                </div>
            </div>
        </div>''')

    # HTML 템플릿 (f-string 대신 일반 문자열 replace 사용으로 안전하게 처리)
    template = dedent('''
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Visual ServiceNow Development Handbook</title>
        <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&family=JetBrains+Mono&display=swap" rel="stylesheet">
        <style>
            :root {
                --bg: #0f172a; --card: #1e293b; --border: #334155; 
                --text: #f1f5f9; --text-muted: #94a3b8; --accent: #38bdf8;
                --code-bg: #000;
            }
            body {
                font-family: 'Noto Sans KR', sans-serif;
                background-color: var(--bg); color: var(--text);
                margin: 0; padding: 0; line-height: 1.6;
            }
            .header {
                text-align: center; padding: 3rem 1rem;
                background: linear-gradient(to bottom, #1e293b, #0f172a);
                border-bottom: 1px solid var(--border);
            }
            .header h1 { margin: 0; font-size: 2.2rem; color: var(--accent); }
            .header p { color: var(--text-muted); margin-top: 0.5rem; }
            .container { max-width: 1000px; margin: 2rem auto; padding: 0 1rem; }
            .handbook-page {
                background: var(--card); border: 1px solid var(--border);
                border-radius: 12px; margin-bottom: 4rem; overflow: hidden;
            }
            .page-meta {
                background: var(--border); padding: 0.5rem 1rem;
                font-size: 0.8rem; font-weight: 700; color: var(--accent);
            }
            .image-section { background: #000; text-align: center; padding: 1.5rem; }
            .image-section img { max-width: 100%; height: auto; border-radius: 4px; border: 1px solid #333; }
            .text-section { padding: 2.5rem; border-top: 1px solid var(--border); }
            .translation-header {
                font-size: 0.95rem; font-weight: 700; color: var(--accent);
                margin-bottom: 1.2rem; display: flex; align-items: center;
            }
            .translation-header::after {
                content: ''; flex: 1; height: 1px; background: var(--border); margin-left: 1rem;
            }
            .translation-text {
                font-size: 1.1rem; word-break: keep-all; text-align: justify;
                color: #e2e8f0; margin-bottom: 1.5rem;
            }
            .code-box {
                background: var(--code-bg); color: #c9d1d9; padding: 1.2rem;
                border-radius: 8px; font-family: 'JetBrains Mono', monospace;
                font-size: 0.85rem; overflow-x: auto; border: 1px solid #222;
                margin-top: 1rem;
            }
            .footer { text-align: center; padding: 4rem; color: var(--text-muted); font-size: 0.85rem; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Visual ServiceNow Development Handbook</h1>
            <p>원본 캡처 이미지와 인공지능 정제 한국어 번역 가이드</p>
        </div>
        <div class="container">
            {{CONTENT_PLACEHOLDER}}
        </div>
        <div class="footer">
            <p>© 2026 ServiceNow Development Handbook - Bilingual AI Edition</p>
        </div>
    </body>
    </html>
    ''')

    final_html = template.replace('{{CONTENT_PLACEHOLDER}}', "".join(handbook_html_parts))

    OUTPUT_HTML.write_text(final_html, encoding="utf-8")
    print(f"Success! Visual handbook regenerated with content: {OUTPUT_HTML}")
    print(f"Total pages included: {len(handbook_html_parts)}")

if __name__ == "__main__":
    main()
