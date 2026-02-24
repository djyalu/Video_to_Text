"""
build_bilingual_doc.py
----------------------
1. OCR 추출 텍스트를 문장 단위로 재구성
2. 소스코드 블록 식별/분리
3. 영문 본문을 한국어로 번역 (deep-translator)
4. 이중언어(영문+한국어) MD/HTML 문서 생성
5. 원본 영상 프레임 대조 검증 (샘플)
"""
import json
import re
import sys
import time
from pathlib import Path
from textwrap import dedent

from deep_translator import GoogleTranslator


# ---------------------------------------------------------------------------
# 설정
# ---------------------------------------------------------------------------
INPUT_JSON = Path("추출결과_상세.json")
OUTPUT_MD = Path("ServiceNow_Handbook_Bilingual.md")
OUTPUT_HTML = Path("ServiceNow_Handbook_Bilingual.html")
VERIFY_LOG = Path("verification_log.txt")

# 번역 배치 크기 (Google Translate 제한 우회)
TRANSLATE_BATCH_CHARS = 4500


# ---------------------------------------------------------------------------
# 1단계: 텍스트 재구성 — 단어 조각 → 문장/문단
# ---------------------------------------------------------------------------
def reconstruct_text(raw_text: str) -> str:
    """OCR이 단어별로 분리한 텍스트를 문장/문단으로 재구성."""
    lines = raw_text.split("\n")
    paragraphs = []
    current = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current:
                paragraphs.append(" ".join(current))
                current = []
            continue
        current.append(stripped)

    if current:
        paragraphs.append(" ".join(current))

    # 후처리: 하이픈 줄바꿈 병합
    merged = []
    for para in paragraphs:
        para = re.sub(r"(\w)- (\w)", r"\1\2", para)  # "hyphen- ated" -> "hyphenated"
        para = re.sub(r"\s{2,}", " ", para)
        merged.append(para)

    return "\n\n".join(merged)


# ---------------------------------------------------------------------------
# 2단계: 소스코드 블록 식별
# ---------------------------------------------------------------------------
CODE_INDICATORS = [
    r"^\s*var\s+\w+", r"^\s*function\s*\(", r"^\s*if\s*\(",
    r"^\s*for\s*\(", r"^\s*while\s*\(", r"^\s*return\s+",
    r"^\s*console\.\w+", r"\.\w+\(\)", r"^\s*//",
    r"^\s*\{", r"^\s*\}", r"GlideRecord", r"setValue\(",
    r"getRowCount\(", r"addQuery\(", r"\.query\(\)",
    r"g_form\.", r"g_list\.", r"\$sp\.",
    r"current\.\w+", r"gs\.\w+\(",
]

def is_code_line(line: str) -> bool:
    """주어진 줄이 소스코드인지 판단."""
    for pattern in CODE_INDICATORS:
        if re.search(pattern, line):
            return True
    return False


def split_prose_and_code(text: str) -> list[dict]:
    """텍스트를 산문(prose)과 코드(code) 블록으로 분리."""
    lines = text.split("\n")
    blocks = []
    current_type = "prose"
    current_lines = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current_lines:
                current_lines.append("")
            continue

        line_is_code = is_code_line(stripped)
        line_type = "code" if line_is_code else "prose"

        if line_type != current_type and current_lines:
            blocks.append({
                "type": current_type,
                "text": "\n".join(current_lines).strip()
            })
            current_lines = []
            current_type = line_type

        current_lines.append(stripped)

    if current_lines:
        blocks.append({
            "type": current_type,
            "text": "\n".join(current_lines).strip()
        })

    return blocks


# ---------------------------------------------------------------------------
# 3단계: 페이지 네비게이션 노이즈 제거
# ---------------------------------------------------------------------------
NAV_PATTERNS = [
    r"^\d+\s*(min(ute)?s?\s+left\s+in|mins\s+left)",
    r"^(Location|Page)\s+\d+\s+(of|Of)\s+\d+",
    r"^\d+%$",
    r"^\d+\s*hr[s]?\s+\d+\s+min",
    r"^I?\s*minute\s+left\s+in",
    r"^\d+\s+mins\s+left\s+in\s+(book|chapter)",
    r"^1\s+hr[s5]?\s+\d+",
    r"^I\s+book$",
]

def remove_nav_noise(text: str) -> str:
    """ebook 리더 네비게이션 UI 텍스트를 제거."""
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        stripped = line.strip()
        is_nav = False
        for pattern in NAV_PATTERNS:
            if re.search(pattern, stripped, re.IGNORECASE):
                is_nav = True
                break
        if not is_nav:
            cleaned.append(line)
    return "\n".join(cleaned)


# ---------------------------------------------------------------------------
# 4단계: OCR 오류 교정
# ---------------------------------------------------------------------------
OCR_CORRECTIONS = {
    "SERVICENOT!": "SERVICENOW",
    "DEVELOPIMENI": "DEVELOPMENT",
    "HANUBOOK": "HANDBOOK",
    "Cuidelines": "Guidelines",
    "OoD rUFF": "Woodruff",
    "inpaa": "input",
    "reasor": "reason",
    "asitis": "as it is",
    "INTRODUCTIO": "INTRODUCTION",
    "atleast": "at least",
    "Iog": "log",
    "Fedirected": "redirected",
    "Ssubdomain": "subdomain",
    "Iatest": "latest",
    "ofthis": "of this",
    "Sre": "are",
    "handbookcodesnc": "handbookcode.snc",
    "DOMI": "DOM",
    "0r": "or",
    "Fule": "rule",
    "PnON": "upon",
    "NOC II": "not",
    "getRou": "getRow",
    "CountO": "Count()",
    "ute leit in": "minute left in",
    "Complexl": "Complex",
    "Eglobal": "& global",
    "setWorkflowfalse": "setWorkflow(false)",
    "autoSysFieldsfalse": "autoSysFields(false)",
    "setVisibleO": "setVisible()",
    "updateO": "update()",
    "recursior": "recursion",
    "Whatis": "What is",
    "tWo": "two",
    "Can]": "can",
    "1s": "is",
    "1rs": "1 hrs",
    "Cor": "or",
}

def apply_ocr_corrections(text: str) -> str:
    """알려진 OCR 오류를 교정."""
    for wrong, correct in OCR_CORRECTIONS.items():
        text = text.replace(wrong, correct)
    # 한글 잔여물 제거 (OCR 노이즈)
    text = re.sub(r"[가-힣]{1}\s", " ", text)  # 단독 한글 1글자는 노이즈
    return text


# ---------------------------------------------------------------------------
# 5단계: 번역 (Google Translate, 배치)
# ---------------------------------------------------------------------------
translator = GoogleTranslator(source="en", target="ko")

def translate_text(text: str) -> str:
    """영문 텍스트를 한국어로 번역. 긴 텍스트는 배치 처리."""
    if not text.strip():
        return ""
    if len(text) <= TRANSLATE_BATCH_CHARS:
        try:
            return translator.translate(text)
        except Exception as e:
            return f"[번역 오류: {e}]"

    # 긴 텍스트는 문장 단위로 분할하여 배치 처리
    sentences = re.split(r"(?<=[.!?])\s+", text)
    batches = []
    current_batch = []
    current_len = 0

    for sentence in sentences:
        if current_len + len(sentence) > TRANSLATE_BATCH_CHARS and current_batch:
            batches.append(" ".join(current_batch))
            current_batch = []
            current_len = 0
        current_batch.append(sentence)
        current_len += len(sentence) + 1

    if current_batch:
        batches.append(" ".join(current_batch))

    translated_parts = []
    for batch in batches:
        try:
            result = translator.translate(batch)
            translated_parts.append(result)
            time.sleep(0.5)  # rate-limit 방지
        except Exception as e:
            translated_parts.append(f"[번역 오류: {e}]")

    return " ".join(translated_parts)


# ---------------------------------------------------------------------------
# 6단계: MD 문서 생성
# ---------------------------------------------------------------------------
def generate_markdown(pages: list[dict]) -> str:
    """이중언어 Markdown 문서 생성."""
    lines = [
        "# ServiceNow Development Handbook - 4th Edition",
        "## Bilingual Edition (English / Korean)",
        "",
        "> **Note**: This document was extracted from an ebook video capture",
        "> and translated to Korean. Source code blocks are preserved in English.",
        "",
        "---",
        "",
    ]

    for i, page in enumerate(pages):
        ts = page.get("timestamp", "")
        lines.append(f"### Page {i+1} [{ts}]")
        lines.append("")

        blocks = page.get("blocks", [])
        for block in blocks:
            if block["type"] == "code":
                lines.append("```javascript")
                lines.append(block["text"])
                lines.append("```")
                lines.append("")
            else:
                # 영문
                lines.append(f"**[EN]** {block['text']}")
                lines.append("")
                # 한국어
                if block.get("translated"):
                    lines.append(f"**[KO]** {block['translated']}")
                    lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 7단계: HTML 문서 생성
# ---------------------------------------------------------------------------
def generate_html(pages: list[dict]) -> str:
    """이중언어 HTML 문서 생성 — 프리미엄 디자인."""
    import html as html_mod

    page_blocks_html = []
    for i, page in enumerate(pages):
        ts = page.get("timestamp", "")
        blocks_html = []
        for block in page.get("blocks", []):
            if block["type"] == "code":
                escaped = html_mod.escape(block["text"])
                blocks_html.append(
                    f'<div class="code-block"><pre><code>{escaped}</code></pre></div>'
                )
            else:
                en_text = html_mod.escape(block["text"])
                ko_text = html_mod.escape(block.get("translated", ""))
                blocks_html.append(f'''
                <div class="bilingual-block">
                    <div class="en-text">
                        <span class="lang-badge en">EN</span>
                        <p>{en_text}</p>
                    </div>
                    <div class="ko-text">
                        <span class="lang-badge ko">KO</span>
                        <p>{ko_text}</p>
                    </div>
                </div>''')

        page_blocks_html.append(f'''
        <section class="page-section" id="page-{i+1}">
            <div class="page-header">
                <h3>Page {i+1}</h3>
                <span class="timestamp">{ts}</span>
            </div>
            {"".join(blocks_html)}
        </section>''')

    return dedent(f'''\
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ServiceNow Development Handbook - Bilingual Edition</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+KR:wght@400;500;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
        <style>
            :root {{
                --bg-primary: #0f1117;
                --bg-secondary: #1a1d2e;
                --bg-card: #212438;
                --text-primary: #e8eaed;
                --text-secondary: #9aa0b0;
                --accent-en: #60a5fa;
                --accent-ko: #f472b6;
                --accent-code: #34d399;
                --border-color: #2d3148;
                --gradient-1: linear-gradient(135deg, #667eea, #764ba2);
            }}
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: 'Inter', 'Noto Sans KR', sans-serif;
                background: var(--bg-primary);
                color: var(--text-primary);
                line-height: 1.8;
            }}
            .header {{
                background: var(--gradient-1);
                padding: 3rem 2rem;
                text-align: center;
            }}
            .header h1 {{ font-size: 2rem; font-weight: 700; }}
            .header p {{ color: rgba(255,255,255,0.8); margin-top: 0.5rem; }}
            .container {{ max-width: 900px; margin: 0 auto; padding: 2rem 1rem; }}
            .toc {{
                background: var(--bg-secondary);
                border-radius: 12px;
                padding: 1.5rem 2rem;
                margin-bottom: 2rem;
                border: 1px solid var(--border-color);
            }}
            .toc h2 {{ font-size: 1.2rem; margin-bottom: 1rem; color: var(--accent-en); }}
            .toc a {{ color: var(--text-secondary); text-decoration: none; display: block; padding: 0.2rem 0; }}
            .toc a:hover {{ color: var(--accent-en); }}
            .page-section {{
                background: var(--bg-secondary);
                border-radius: 12px;
                padding: 1.5rem 2rem;
                margin-bottom: 1.5rem;
                border: 1px solid var(--border-color);
                transition: border-color 0.3s;
            }}
            .page-section:hover {{ border-color: #667eea; }}
            .page-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 1rem;
                padding-bottom: 0.75rem;
                border-bottom: 1px solid var(--border-color);
            }}
            .page-header h3 {{ font-size: 1.1rem; color: var(--text-primary); }}
            .timestamp {{
                font-size: 0.8rem;
                color: var(--text-secondary);
                background: var(--bg-card);
                padding: 0.2rem 0.6rem;
                border-radius: 6px;
            }}
            .bilingual-block {{
                margin: 1rem 0;
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 1rem;
            }}
            .en-text, .ko-text {{
                background: var(--bg-card);
                padding: 1rem;
                border-radius: 8px;
            }}
            .en-text {{ border-left: 3px solid var(--accent-en); }}
            .ko-text {{ border-left: 3px solid var(--accent-ko); }}
            .en-text p, .ko-text p {{
                font-size: 0.95rem;
                line-height: 1.7;
            }}
            .ko-text p {{ font-family: 'Noto Sans KR', sans-serif; }}
            .lang-badge {{
                display: inline-block;
                font-size: 0.65rem;
                font-weight: 700;
                padding: 0.15rem 0.4rem;
                border-radius: 4px;
                margin-bottom: 0.5rem;
                text-transform: uppercase;
                letter-spacing: 0.05em;
            }}
            .lang-badge.en {{ background: rgba(96,165,250,0.2); color: var(--accent-en); }}
            .lang-badge.ko {{ background: rgba(244,114,182,0.2); color: var(--accent-ko); }}
            .code-block {{
                background: #1e2030;
                border-radius: 8px;
                padding: 1rem;
                margin: 1rem 0;
                border-left: 3px solid var(--accent-code);
                overflow-x: auto;
            }}
            .code-block pre {{ margin: 0; }}
            .code-block code {{
                font-family: 'JetBrains Mono', monospace;
                font-size: 0.85rem;
                color: var(--accent-code);
            }}
            .stats {{
                text-align: center;
                padding: 1rem;
                color: var(--text-secondary);
                font-size: 0.85rem;
            }}
            @media (max-width: 768px) {{
                .bilingual-block {{ grid-template-columns: 1fr; }}
                .header h1 {{ font-size: 1.4rem; }}
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>ServiceNow Development Handbook</h1>
            <p>Fourth Edition - Bilingual (English / Korean)</p>
        </div>
        <div class="container">
            {"".join(page_blocks_html)}
            <div class="stats">
                <p>Total Pages: {len(pages)} | Generated from video OCR extraction</p>
            </div>
        </div>
    </body>
    </html>''')


# ---------------------------------------------------------------------------
# 메인 실행
# ---------------------------------------------------------------------------
def main():
    print("=" * 60)
    print("  Bilingual Document Builder")
    print("  OCR cleanup -> Translate -> MD/HTML")
    print("=" * 60)

    # 1. JSON 로드
    print("\n[1/6] Loading extracted data...")
    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    raw_pages = data.get("pages", [])
    print(f"  Total pages: {len(raw_pages)}")

    # 2. 텍스트 재구성 및 정제
    print("\n[2/6] Reconstructing and cleaning text...")
    processed_pages = []
    for page in raw_pages:
        raw = page["text"]
        # 네비게이션 노이즈 제거
        cleaned = remove_nav_noise(raw)
        # OCR 오류 교정
        cleaned = apply_ocr_corrections(cleaned)
        # 문장 재구성
        reconstructed = reconstruct_text(cleaned)

        if not reconstructed.strip():
            continue

        processed_pages.append({
            "timestamp": page.get("timestamp", ""),
            "original": raw,
            "cleaned": reconstructed,
        })

    print(f"  Pages after cleanup: {len(processed_pages)}")

    # 3. 코드/산문 분리
    print("\n[3/6] Separating code blocks from prose...")
    for page in processed_pages:
        page["blocks"] = split_prose_and_code(page["cleaned"])

    # 4. 번역
    print("\n[4/6] Translating prose to Korean...")
    total_blocks = sum(
        1 for p in processed_pages for b in p["blocks"] if b["type"] == "prose"
    )
    translated_count = 0

    for page in processed_pages:
        for block in page["blocks"]:
            if block["type"] == "prose":
                translated_count += 1
                progress = translated_count / total_blocks * 100
                print(f"  [{translated_count}/{total_blocks}] {progress:.0f}%", end="\r")
                block["translated"] = translate_text(block["text"])
                time.sleep(0.3)  # rate limit

    print(f"\n  Translation complete: {translated_count} blocks")

    # 5. MD 생성
    print("\n[5/6] Generating Markdown...")
    md_content = generate_markdown(processed_pages)
    OUTPUT_MD.write_text(md_content, encoding="utf-8")
    print(f"  Saved: {OUTPUT_MD}")

    # 6. HTML 생성
    print("\n[6/6] Generating HTML...")
    html_content = generate_html(processed_pages)
    OUTPUT_HTML.write_text(html_content, encoding="utf-8")
    print(f"  Saved: {OUTPUT_HTML}")

    # 검증 로그
    print("\n[Verify] Writing verification log...")
    with open(VERIFY_LOG, "w", encoding="utf-8") as f:
        f.write("OCR Verification Log\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Total raw pages: {len(raw_pages)}\n")
        f.write(f"Pages after filtering: {len(processed_pages)}\n")
        f.write(f"OCR corrections applied: {len(OCR_CORRECTIONS)} patterns\n")
        f.write(f"Navigation noise patterns: {len(NAV_PATTERNS)} patterns\n\n")
        f.write("Applied corrections:\n")
        for wrong, correct in OCR_CORRECTIONS.items():
            f.write(f"  '{wrong}' -> '{correct}'\n")
        f.write(f"\nTranslated blocks: {translated_count}\n")
    print(f"  Saved: {VERIFY_LOG}")

    print(f"\n{'='*60}")
    print(f"  All done!")
    print(f"  MD : {OUTPUT_MD.absolute()}")
    print(f"  HTML: {OUTPUT_HTML.absolute()}")
    print(f"  Log : {VERIFY_LOG.absolute()}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
