"""
generate_book_pdf.py (v2 - Recover Translations)
==============================================
기존에 생성된 ServiceNow_Handbook_Bilingual.html에서 번역된 텍스트를 복구하여
매우 빠르게 책 구조로 재구성하고 PDF를 생성합니다.
"""
import json
import re
from pathlib import Path
from textwrap import dedent
from bs4 import BeautifulSoup

# ─── Configuration ──────────────────────────────────────────
INPUT_HTML = Path("ServiceNow_Handbook_Bilingual.html")
OUTPUT_PDF = Path("ServiceNow_Handbook_Bilingual_Expert.pdf")
OUTPUT_BOOK_HTML = Path("book_layout.html")

# ─── Chapter 정의 (목차 기반) ────────────────────────────────
CHAPTERS = [
    {"start": 1, "title": "Title & Front Matter"},
    {"start": 10, "title": "Introduction"},
    {"start": 13, "title": "Code & Coding Guidelines"},
    {"start": 14, "title": "Writing DRY Code"},
    {"start": 21, "title": "Pass-by-Reference (PBR)"},
    {"start": 24, "title": "Getting and Setting Field Values"},
    {"start": 30, "title": "Business Rule Order & update()"},
    {"start": 31, "title": "Async & Display Business Rules"},
    {"start": 35, "title": "When Not to Code"},
    {"start": 38, "title": "Debugging & Tools"},
    {"start": 50, "title": "Tables & Lists"},
    {"start": 100, "title": "Script Includes & Modularity"},
    {"start": 150, "title": "Application Security"},
    {"start": 180, "title": "Performance Optimization"},
]

def get_chapter_title(page_idx):
    current_title = "Preface"
    for ch in CHAPTERS:
        if page_idx >= ch["start"]:
            current_title = ch["title"]
        else:
            break
    return current_title

def main():
    if not INPUT_HTML.exists():
        print("Error: Input HTML not found. Please run build_final_doc.py first.")
        return

    print(f"Reading translations from {INPUT_HTML}...")
    with open(INPUT_HTML, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    pages = soup.find_all("section", class_="page")
    print(f"Found {len(pages)} pages.")

    book_html_parts = []
    current_ch = ""

    for i, page in enumerate(pages, 1):
        ch_title = get_chapter_title(i)
        
        # New Chapter Heading
        if ch_title != current_ch:
            book_html_parts.append(f'<h1 class="chapter-title">{ch_title}</h1>')
            current_ch = ch_title

        # Process blocks in page
        # Bilingual blocks
        bilinguals = page.find_all("div", class_="bilingual")
        for bi in bilinguals:
            en = bi.find("div", class_="lang-en").p.get_text()
            ko = bi.find("div", class_="lang-ko").p.get_text()
            
            # Simple heuristic to merge split sentences: 
            # If paragraph is very short, maybe it's part of the next one.
            # But for now, let's keep it as is for accuracy.
            book_html_parts.append(f'''
            <div class="bilingual-row">
                <p class="en-para">{en}</p>
                <p class="ko-para">{ko}</p>
            </div>''')

        # Code blocks
        codes = page.find_all("div", class_="code-block")
        for code in codes:
            code_text = code.find("code").get_text()
            book_html_parts.append(f'<div class="code-block-wrap"><pre><code>{code_text}</code></pre></div>')

    # Full HTML for PDF
    full_html = dedent(f'''\
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <link href="https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@400;700&family=Noto+Sans+KR:wght@300;400;700&family=JetBrains+Mono&display=swap" rel="stylesheet">
        <style>
            @page {{
                size: A4;
                margin: 25mm 20mm;
                @bottom-center {{
                    content: counter(page);
                    font-family: sans-serif;
                    font-size: 9pt;
                }}
            }}
            body {{
                font-family: 'Noto Serif KR', serif;
                line-height: 1.7;
                color: #222;
                font-size: 10.5pt;
                background: #fff;
            }}
            .title-page {{
                height: 100vh;
                display: flex;
                flex-direction: column;
                justify-content: center;
                text-align: center;
                page-break-after: always;
            }}
            h1.chapter-title {{
                font-family: 'Noto Sans KR', sans-serif;
                font-size: 26pt;
                color: #1a2a40;
                border-bottom: 3px solid #1a2a40;
                margin-top: 60pt;
                margin-bottom: 40pt;
                padding-bottom: 10pt;
                page-break-before: always;
            }}
            .bilingual-row {{
                margin-bottom: 18pt;
                orphans: 3;
                widows: 3;
            }}
            .en-para {{
                font-size: 9.5pt;
                color: #555;
                margin-bottom: 4pt;
                font-style: italic;
                border-left: 2px solid #ddd;
                padding-left: 10pt;
            }}
            .ko-para {{
                font-family: 'Noto Sans KR', sans-serif;
                color: #000;
                font-size: 10.5pt;
                background: #fbfbfb;
                padding: 12pt;
                border-radius: 5pt;
            }}
            .code-block-wrap {{
                background-color: #f4f6f8;
                border: 1px solid #dfe3e8;
                border-radius: 6pt;
                padding: 12pt;
                margin: 20pt 0;
                font-family: 'JetBrains Mono', monospace;
                font-size: 8.5pt;
                white-space: pre-wrap;
                page-break-inside: avoid;
            }}
            pre {{ margin: 0; }}
            h2 {{ font-family: sans-serif; color: #34495e; margin-top: 25pt; }}
        </style>
    </head>
    <body>
        <div class="title-page">
            <h1 style="font-size: 40pt; margin-bottom: 10pt;">ServiceNow Development Handbook</h1>
            <h2 style="font-size: 20pt; font-weight: 300; margin-bottom: 100pt;">Bilingual Expert Edition (영한 통합본)</h2>
            <p style="font-size: 14pt;">Tim Woodruff</p>
            <p style="color: #888; margin-top: 10pt;">Extracted & Translated via AI Orchestration</p>
        </div>
        {{CONTENT_PLACEHOLDER}}
    </body>
    </html>''').replace('{CONTENT_PLACEHOLDER}', "".join(book_html_parts))

    OUTPUT_BOOK_HTML.write_text(full_html, encoding="utf-8")
    print(f"Exported book layout to {OUTPUT_BOOK_HTML}")

    try:
        from weasyprint import HTML
        print("Converting to PDF...")
        HTML(string=full_html).write_pdf(OUTPUT_PDF)
        print(f"🎉 Success! PDF generated: {OUTPUT_PDF}")
    except Exception as e:
        print(f"PDF generation failed: {e}")
        print("Tip: You can open the 'book_layout.html' in Chrome and use 'Print to PDF' for perfect results.")

if __name__ == "__main__":
    main()
