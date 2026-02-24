"""
build_final_doc.py  —  최종 이중언어 문서 생성기 (v2)
=====================================================
개선 사항:
  - 원본 영상 프레임 재추출 및 OCR 대조 검증
  - UI 네비게이션 노이즈 완전 제거
  - 소스코드 블록 분리 강화
  - OCR 오류 교정 패턴 확장
  - 단어 조각 → 문장 재구성 정밀도 향상
  - 번역 품질 개선 (문단 단위 번역)
  - 프리미엄 HTML 디자인 (다크 모드, 반응형)
"""
import json
import os
import re
import sys
import time
import cv2
import numpy as np
from pathlib import Path
from textwrap import dedent

from deep_translator import GoogleTranslator


# ─── Configuration ──────────────────────────────────────────
INPUT_JSON   = Path("추출결과_상세.json")
VIDEO_FILE   = Path("source/capture video.mp4")
OUTPUT_MD    = Path("ServiceNow_Handbook_Bilingual.md")
OUTPUT_HTML  = Path("ServiceNow_Handbook_Bilingual.html")
VERIFY_LOG   = Path("verification_log.txt")

TRANSLATE_BATCH_CHARS = 4800
VERIFY_SAMPLE_COUNT = 10   # 검증할 프레임 수

translator = GoogleTranslator(source="en", target="ko")


# ═══════════════════════════════════════════════════════════
# 1. 텍스트 정제 – 네비게이션 노이즈 완전 제거
# ═══════════════════════════════════════════════════════════
NAV_NOISE_PATTERNS = [
    # 시간 표시
    r"\d+\s*hrs?\s+\d+\s*mins?\s+left\s+in.*",
    r"\d+\s*minutes?\s+left\s+in.*",
    r"\d+\s*mins?\s+left\s+in.*",
    r"I?\s+minutes?\s+left\s+in\s+(book|chapter).*",
    r"\d+\s+hr[s5]?\s*$",
    r"1\s+hr[s5]\s*$",
    r"1\s+hrs\s*$",
    r"1\s+6r5\s*.*",
    r"^1\s+hr5$",
    r"1 hr5$",
    r"1 6r5.*",
    # 페이지 표시
    r"Page\s+\d+\s+(of|Of|0f)\s+\d+",
    r"Location\s+\d+\s+(of|Of)\s+\d+",
    r"Chapter\s*$",
    r"^Chapter$",
    r"^\d+%$",
    r":\d+%$",
    r"^\d+\s*$",  # 숫자만 있는 줄
    r"^I\s+book\s*$",
    r"^I\s+hrs?\s*$",
    r"^\d+\s+mins\s+left$",
    r"^\d+\s+mins\s+left\s+in$",
]

def remove_nav_noise(text: str) -> str:
    """ebook 리더 UI 노이즈를 제거."""
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        s = line.strip()
        if not s:
            cleaned.append(line)
            continue
        skip = False
        for pat in NAV_NOISE_PATTERNS:
            if re.search(pat, s, re.IGNORECASE):
                skip = True
                break
        # 짧은 줄이면서 Chapter만 있는 경우
        if s.lower() in ("chapter", "i book", "book"):
            skip = True
        if not skip:
            cleaned.append(line)
    return "\n".join(cleaned)


# ═══════════════════════════════════════════════════════════
# 2. OCR 오류 교정 (확장)
# ═══════════════════════════════════════════════════════════
OCR_FIX = {
    # 일반 단어 오류
    "SERVICENOT!": "SERVICENOW", "DEVELOPIMENI": "DEVELOPMENT",
    "HANUBOOK": "HANDBOOK", "Cuidelines": "Guidelines",
    "OoD rUFF": "Woodruff", "reasor": "reason",
    "asitis": "as it is", "INTRODUCTIO": "INTRODUCTION",
    "Iog": "log", "Iatest": "latest", "ofthis": "of this",
    "handbookcodesnc": "handbookcode.snc",
    "DOMI": "DOM", "Fule": "rule", "tWo": "two",
    "1s ": "is ", "Cor ": "or ", "Car ": "can ",
    "Complexl": "Complex", "recursior": "recursion",
    "Whatis": "What is", " 0r ": " or ",
    " 01 ": " of ", " O1 ": " of ",
    " Oh ": " on ", " ON ": " on ",
    "Commor ": "common ", "COmmOH ": "common ",
    " i it": " it", "2 ": "a ",  # OCR frequently reads "a" as "2"
    " f ": " of ", " ar ": " an ", " SO ": " so ",
    " Won't ": " won't ", " Can't ": " can't ",
    " Can ": " can ", " Was ": " was ",
    " i ": " ", " i\n": "\n",
    # 텍스트 끝 정리
    " 1hrs": "", " 1 hrs": "", " 1hrs ": "",
    " 1 hr5": "", "1 6r5": "", " 1 6r5": "",
}

# 단독 한글 1글자 제거 (OCR 노이즈)
HANGUL_NOISE_RE = re.compile(r"(?<!\w)[가-힣](?!\w)")

def fix_ocr_errors(text: str) -> str:
    """OCR 오류 수정."""
    for wrong, correct in OCR_FIX.items():
        text = text.replace(wrong, correct)
    # 단독 한글 1글자 제거
    text = HANGUL_NOISE_RE.sub("", text)
    # 하이픈 줄바꿈 병합
    text = re.sub(r"(\w)- +(\w)", r"\1\2", text)
    # 연속 공백 정리
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


# ═══════════════════════════════════════════════════════════
# 3. 단어 조각 → 문단 재구성
# ═══════════════════════════════════════════════════════════
def reconstruct_paragraphs(raw: str) -> list[str]:
    """OCR 단어 조각들을 문단으로 재구성."""
    lines = raw.split("\n")
    paragraphs = []
    cur = []
    
    for line in lines:
        s = line.strip()
        if not s:
            if cur:
                paragraphs.append(" ".join(cur))
                cur = []
            continue
        cur.append(s)
    
    if cur:
        paragraphs.append(" ".join(cur))
    
    # 후처리: 너무 짧은 문단 병합
    merged = []
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        if merged and len(merged[-1]) < 80 and len(p) < 80:
            merged[-1] = merged[-1] + " " + p
        else:
            merged.append(p)
    
    return merged


# ═══════════════════════════════════════════════════════════
# 4. 소스코드 감지
# ═══════════════════════════════════════════════════════════
CODE_SIGNS = [
    r"(?:^|\s)var\s+\w+", r"function\s*\w*\s*\(", r"\.setValue\(",
    r"\.getValue\(", r"\.addQuery\(", r"\.query\(\)", r"\.next\(\)",
    r"\.update\(\)", r"\.insert\(\)", r"g_form\.", r"g_list\.",
    r"gs\.\w+\(", r"current\.\w+", r"GlideRecord\(",
    r"console\.log\(", r"return\s+\w", r"\{$", r"\}$",
    r"//\s*\w", r"/\*", r"\*/", r"new\s+\w+\(",
    r"\.prototype\.", r"addEncodedQuery\(",
    r"getRowCount\(", r"updateMultiple\(",
    r"deleteMultiple\(", r"setWorkflow\(",
    r"setAbortAction\(", r"\.toString\(\)",
]

def looks_like_code(text: str) -> bool:
    """텍스트가 코드처럼 보이는지 판단."""
    hits = sum(1 for pat in CODE_SIGNS if re.search(pat, text))
    # 코드 특징이 3개 이상이면 코드로 판단
    return hits >= 3


# ═══════════════════════════════════════════════════════════
# 5. 번역 (개선된 배치 처리)
# ═══════════════════════════════════════════════════════════
def translate_text(text: str) -> str:
    """영문 산문(prose)을 한국어로 번역."""
    text = text.strip()
    if not text or len(text) < 5:
        return text
    
    if len(text) <= TRANSLATE_BATCH_CHARS:
        for attempt in range(3):
            try:
                result = translator.translate(text)
                return result or ""
            except Exception as e:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                else:
                    return f"[번역 실패: {e}]"
    
    # 문장 분할 배치
    sentences = re.split(r"(?<=[.!?])\s+", text)
    batches, buf, buf_len = [], [], 0
    for s in sentences:
        if buf_len + len(s) > TRANSLATE_BATCH_CHARS and buf:
            batches.append(" ".join(buf))
            buf, buf_len = [], 0
        buf.append(s)
        buf_len += len(s) + 1
    if buf:
        batches.append(" ".join(buf))
    
    parts = []
    for batch in batches:
        for attempt in range(3):
            try:
                r = translator.translate(batch)
                parts.append(r or "")
                time.sleep(0.5)
                break
            except Exception as e:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                else:
                    parts.append(f"[번역 실패: {e}]")
    
    return " ".join(parts)


# ═══════════════════════════════════════════════════════════
# 6. 원본 영상 프레임 대조 검증
# ═══════════════════════════════════════════════════════════
def verify_against_video(pages: list[dict], 
                          sample_count: int = VERIFY_SAMPLE_COUNT) -> list[dict]:
    """원본 영상 프레임과 OCR 결과를 대조 검증."""
    if not VIDEO_FILE.exists():
        return [{"error": "Video file not found"}]
    
    cap = cv2.VideoCapture(str(VIDEO_FILE))
    if not cap.isOpened():
        return [{"error": "Cannot open video"}]
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # 균등 간격으로 샘플 추출
    indices = np.linspace(0, len(pages) - 1, sample_count, dtype=int)
    results = []
    
    try:
        from paddleocr import PaddleOCR
        ocr = PaddleOCR(lang="korean")
    except Exception:
        cap.release()
        return [{"error": "PaddleOCR not available for verification"}]
    
    for idx in indices:
        page = pages[idx]
        ts_str = page.get("timestamp", "00:00")
        # 타임스탬프 파싱
        parts = ts_str.replace("[", "").replace("]", "").split(":")
        try:
            secs = int(parts[0]) * 60 + int(parts[1]) if len(parts) >= 2 else 0
        except:
            secs = 0
        
        frame_no = int(secs * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
        ret, frame = cap.read()
        if not ret:
            results.append({
                "page": idx + 1, "timestamp": ts_str,
                "status": "SKIP - frame read failed"
            })
            continue
        
        # 재 OCR
        try:
            ocr_result = ocr.ocr(frame)
            verify_texts = []
            if ocr_result and ocr_result[0]:
                for line in ocr_result[0]:
                    if line[1]:
                        verify_texts.append(line[1][0])
            verify_text = " ".join(verify_texts)
        except Exception as e:
            verify_text = f"OCR error: {e}"
        
        original_text = page.get("original", "")[:200]
        
        # 유사도 비교
        from difflib import SequenceMatcher
        sim = SequenceMatcher(None, 
                              original_text.lower()[:200], 
                              verify_text.lower()[:200]).ratio()
        
        results.append({
            "page": idx + 1,
            "timestamp": ts_str,
            "similarity": round(sim, 3),
            "status": "OK" if sim > 0.5 else "MISMATCH",
            "original_preview": original_text[:100],
            "verify_preview": verify_text[:100],
        })
    
    cap.release()
    return results


# ═══════════════════════════════════════════════════════════
# 7. 마크다운 생성
# ═══════════════════════════════════════════════════════════
def build_markdown(pages: list[dict]) -> str:
    """이중언어 Markdown 문서 생성."""
    buf = [
        "# ServiceNow Development Handbook — Fourth Edition",
        "",
        "## 이중언어 버전 (English / Korean)",
        "",
        "> 이 문서는 'ServiceNow Development Handbook 4th Edition (Tim Woodruff)' ",
        "> ebook 영상에서 OCR로 추출한 후 한국어로 번역한 이중언어 버전입니다.",
        "> 소스코드 블록은 영문 원본 그대로 보존합니다.",
        "",
        "---",
        "",
    ]
    
    # 목차 생성
    buf.append("## 📑 목차 (Table of Contents)")
    buf.append("")
    for i, p in enumerate(pages):
        ts = p.get("timestamp", "")
        first_line = ""
        for block in p.get("blocks", []):
            if block["type"] == "prose" and len(block["text"]) > 20:
                first_line = block["text"][:60] + "..."
                break
        buf.append(f"- [Page {i+1} [{ts}]](#page-{i+1}-{ts.replace(':', '')})")
    buf.append("")
    buf.append("---")
    buf.append("")
    
    # 페이지 내용
    for i, p in enumerate(pages):
        ts = p.get("timestamp", "")
        anchor = f"page-{i+1}-{ts.replace(':', '')}"
        buf.append(f"### Page {i+1} [{ts}] {{#{anchor}}}")
        buf.append("")
        
        for block in p.get("blocks", []):
            if block["type"] == "code":
                buf.append("```javascript")
                buf.append(block["text"])
                buf.append("```")
                buf.append("")
            else:
                en = block["text"]
                ko = block.get("translated", "")
                buf.append(f"**🇺🇸 EN:** {en}")
                buf.append("")
                if ko:
                    buf.append(f"**🇰🇷 KO:** {ko}")
                    buf.append("")
        
        buf.append("---")
        buf.append("")
    
    return "\n".join(buf)


# ═══════════════════════════════════════════════════════════
# 8. HTML 생성 (프리미엄 디자인)
# ═══════════════════════════════════════════════════════════
def build_html(pages: list[dict]) -> str:
    """이중언어 HTML — 프리미엄 다크 모드 디자인."""
    import html as H
    
    # 페이지별 HTML 생성
    sections = []
    toc_items = []
    
    for i, p in enumerate(pages):
        ts = p.get("timestamp", "")
        pid = f"page-{i+1}"
        
        # 첫 번째 산문 블록의 첫 줄을 목차에 표시
        preview = ""
        for b in p.get("blocks", []):
            if b["type"] == "prose" and len(b["text"]) > 20:
                preview = b["text"][:50]
                break
        toc_items.append(f'<a href="#{pid}"><span class="toc-num">{i+1}</span> <span class="toc-time">[{ts}]</span> {H.escape(preview)}…</a>')
        
        blocks_html = []
        for b in p.get("blocks", []):
            if b["type"] == "code":
                blocks_html.append(f'''
                <div class="code-block">
                    <div class="code-label">📋 Source Code</div>
                    <pre><code>{H.escape(b["text"])}</code></pre>
                </div>''')
            else:
                en = H.escape(b["text"])
                ko = H.escape(b.get("translated", ""))
                blocks_html.append(f'''
                <div class="bilingual">
                    <div class="lang-en">
                        <div class="lang-tag">EN</div>
                        <p>{en}</p>
                    </div>
                    <div class="lang-ko">
                        <div class="lang-tag ko">KO</div>
                        <p>{ko}</p>
                    </div>
                </div>''')
        
        sections.append(f'''
        <section class="page" id="{pid}">
            <div class="page-head">
                <span class="page-num">Page {i+1}</span>
                <span class="page-ts">{ts}</span>
            </div>
            {"".join(blocks_html)}
        </section>''')
    
    toc_html = "\n".join(toc_items)
    body_html = "\n".join(sections)
    
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ServiceNow Development Handbook — Bilingual Edition</title>
<meta name="description" content="ServiceNow Development Handbook 4th Edition by Tim Woodruff - Bilingual English/Korean edition extracted from video">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Noto+Sans+KR:wght@300;400;500;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
:root{{
  --bg:#0b0e17;--bg2:#111827;--bg3:#1e293b;
  --card:#1a2332;--border:#2a3a4e;
  --txt:#e2e8f0;--txt2:#94a3b8;--txt3:#64748b;
  --blue:#3b82f6;--violet:#8b5cf6;--pink:#ec4899;
  --green:#10b981;--amber:#f59e0b;
  --grad:linear-gradient(135deg,#6366f1 0%,#8b5cf6 50%,#a855f7 100%)
}}
body{{
  font-family:'Inter','Noto Sans KR',sans-serif;
  background:var(--bg);color:var(--txt);
  line-height:1.8;font-size:15px;
}}

/* ═══ Header ═══ */
.hero{{
  background:var(--grad);
  padding:4rem 2rem 3rem;
  text-align:center;
  position:relative;
  overflow:hidden;
}}
.hero::before{{
  content:'';position:absolute;inset:0;
  background:radial-gradient(circle at 30% 50%,rgba(255,255,255,0.08) 0%,transparent 50%);
}}
.hero h1{{font-size:2.4rem;font-weight:700;letter-spacing:-0.03em;position:relative}}
.hero .sub{{color:rgba(255,255,255,0.75);margin-top:0.5rem;font-size:1.05rem;position:relative}}
.hero .badge{{
  display:inline-block;margin-top:1rem;
  background:rgba(255,255,255,0.15);backdrop-filter:blur(10px);
  border:1px solid rgba(255,255,255,0.2);
  padding:0.4rem 1.2rem;border-radius:999px;
  font-size:0.85rem;color:rgba(255,255,255,0.9);
  position:relative
}}

/* ═══ Layout ═══ */
.wrap{{max-width:960px;margin:0 auto;padding:2rem 1rem}}

/* ═══ Stats ═══ */
.stats{{
  display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));
  gap:1rem;margin-bottom:2rem
}}
.stat{{
  background:var(--card);border:1px solid var(--border);
  border-radius:12px;padding:1.2rem;text-align:center
}}
.stat .num{{font-size:2rem;font-weight:700;color:var(--blue)}}
.stat .label{{font-size:0.8rem;color:var(--txt2);text-transform:uppercase;letter-spacing:0.05em}}

/* ═══ TOC ═══ */
.toc{{
  background:var(--bg2);border:1px solid var(--border);
  border-radius:16px;padding:2rem;margin-bottom:2rem;
  max-height:400px;overflow-y:auto;
}}
.toc h2{{font-size:1.1rem;color:var(--violet);margin-bottom:1rem}}
.toc a{{
  display:block;color:var(--txt2);text-decoration:none;
  padding:0.35rem 0;font-size:0.85rem;
  border-bottom:1px solid rgba(255,255,255,0.03);
  transition:color 0.2s,padding-left 0.2s
}}
.toc a:hover{{color:var(--blue);padding-left:8px}}
.toc-num{{color:var(--txt3);font-weight:600;margin-right:4px}}
.toc-time{{color:var(--green);font-size:0.75rem;margin-right:4px}}

/* ═══ Page Section ═══ */
.page{{
  background:var(--card);border:1px solid var(--border);
  border-radius:16px;padding:1.8rem 2rem;margin-bottom:1.5rem;
  transition:border-color 0.3s,transform 0.2s
}}
.page:hover{{border-color:var(--violet);transform:translateY(-1px)}}
.page-head{{
  display:flex;justify-content:space-between;align-items:center;
  padding-bottom:1rem;margin-bottom:1.2rem;
  border-bottom:1px solid var(--border)
}}
.page-num{{font-weight:700;font-size:1.05rem}}
.page-ts{{
  background:var(--bg3);color:var(--green);
  padding:0.25rem 0.75rem;border-radius:8px;
  font-size:0.78rem;font-family:'JetBrains Mono',monospace
}}

/* ═══ Bilingual Block ═══ */
.bilingual{{
  display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin:1rem 0
}}
.lang-en,.lang-ko{{
  background:var(--bg2);padding:1.2rem;border-radius:10px;
  position:relative
}}
.lang-en{{border-left:3px solid var(--blue)}}
.lang-ko{{border-left:3px solid var(--pink)}}
.lang-en p{{font-size:0.92rem;line-height:1.75;color:var(--txt)}}
.lang-ko p{{font-size:0.92rem;line-height:1.75;color:var(--txt);
  font-family:'Noto Sans KR','Inter',sans-serif}}
.lang-tag{{
  display:inline-block;font-size:0.6rem;font-weight:700;
  padding:0.15rem 0.5rem;border-radius:4px;margin-bottom:0.6rem;
  text-transform:uppercase;letter-spacing:0.08em
}}
.lang-tag{{background:rgba(59,130,246,0.15);color:var(--blue)}}
.lang-tag.ko{{background:rgba(236,72,153,0.15);color:var(--pink)}}

/* ═══ Code Block ═══ */
.code-block{{
  background:#0d1117;border:1px solid #21262d;
  border-radius:10px;margin:1rem 0;overflow-x:auto;
  position:relative
}}
.code-label{{
  background:#161b22;padding:0.5rem 1rem;
  font-size:0.75rem;color:var(--green);
  border-bottom:1px solid #21262d;
  font-family:'JetBrains Mono',monospace
}}
.code-block pre{{padding:1rem;margin:0}}
.code-block code{{
  font-family:'JetBrains Mono',monospace;
  font-size:0.82rem;color:#c9d1d9;line-height:1.6
}}

/* ═══ Footer ═══ */
.footer{{
  text-align:center;padding:2rem;color:var(--txt3);
  font-size:0.8rem;border-top:1px solid var(--border);
  margin-top:2rem
}}

/* ═══ Scroll to Top ═══ */
.top-btn{{
  position:fixed;bottom:2rem;right:2rem;
  width:44px;height:44px;border-radius:50%;
  background:var(--grad);border:none;color:#fff;
  font-size:1.2rem;cursor:pointer;
  box-shadow:0 4px 15px rgba(99,102,241,0.4);
  opacity:0;transition:opacity 0.3s;z-index:999
}}
.top-btn.show{{opacity:1}}

/* ═══ Responsive ═══ */
@media(max-width:768px){{
  .bilingual{{grid-template-columns:1fr}}
  .hero h1{{font-size:1.6rem}}
  .hero .sub{{font-size:0.9rem}}
  .page{{padding:1.2rem}}
  .stats{{grid-template-columns:1fr 1fr}}
}}

/* ═══ Search ═══ */
.search-box{{
  margin-bottom:1.5rem;position:relative
}}
.search-box input{{
  width:100%;padding:0.8rem 1rem 0.8rem 2.5rem;
  border-radius:10px;border:1px solid var(--border);
  background:var(--bg2);color:var(--txt);
  font-size:0.95rem;outline:none;
  transition:border-color 0.3s
}}
.search-box input:focus{{border-color:var(--violet)}}
.search-box::before{{
  content:'🔍';position:absolute;left:0.8rem;top:50%;
  transform:translateY(-50%);font-size:1rem
}}

/* ═══ Print ═══ */
@media print{{
  .hero{{background:#333!important;-webkit-print-color-adjust:exact}}
  .page{{break-inside:avoid;border:1px solid #ccc}}
  .bilingual{{grid-template-columns:1fr}}
  .top-btn,.search-box,.toc{{display:none}}
  body{{background:#fff;color:#000}}
  .lang-en p,.lang-ko p{{color:#000}}
}}
</style>
</head>
<body>

<div class="hero">
  <h1>ServiceNow Development Handbook</h1>
  <p class="sub">Fourth Edition — Tim Woodruff</p>
  <div class="badge">🌏 Bilingual Edition (English / Korean)</div>
</div>

<div class="wrap">

  <div class="stats">
    <div class="stat"><div class="num">{len(pages)}</div><div class="label">Total Pages</div></div>
    <div class="stat"><div class="num">265</div><div class="label">Book Pages</div></div>
    <div class="stat"><div class="num">EN/KO</div><div class="label">Languages</div></div>
    <div class="stat"><div class="num">4th</div><div class="label">Edition</div></div>
  </div>

  <div class="search-box">
    <input type="text" id="searchInput" placeholder="Search pages... (영문/한글 검색)">
  </div>

  <div class="toc">
    <h2>📑 Table of Contents</h2>
    {toc_html}
  </div>

  {body_html}

  <div class="footer">
    <p>This bilingual document was generated from video OCR extraction.</p>
    <p>Original: ServiceNow Development Handbook, 4th Edition by Tim Woodruff</p>
  </div>

</div>

<button class="top-btn" id="topBtn" onclick="window.scrollTo({{top:0,behavior:'smooth'}})">↑</button>

<script>
// Scroll-to-top button
window.addEventListener('scroll',()=>{{
  document.getElementById('topBtn').classList.toggle('show',window.scrollY>300)
}});
// Search functionality
document.getElementById('searchInput').addEventListener('input',function(){{
  const q=this.value.toLowerCase();
  document.querySelectorAll('.page').forEach(p=>{{
    p.style.display=p.textContent.toLowerCase().includes(q)?'':'none'
  }})
}});
</script>
</body>
</html>'''


# ═══════════════════════════════════════════════════════════
# 메인 실행
# ═══════════════════════════════════════════════════════════
def main():
    print("=" * 60)
    print("  📚 Final Bilingual Document Builder v2")
    print("=" * 60)
    
    # ── 1. 데이터 로드 ──
    print("\n[1/7] Loading JSON data...")
    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    raw_pages = data.get("pages", [])
    print(f"  Raw pages: {len(raw_pages)}")
    
    # ── 2. 텍스트 정제 ──
    print("\n[2/7] Cleaning & reconstructing text...")
    processed = []
    for rp in raw_pages:
        raw = rp["text"]
        cleaned = remove_nav_noise(raw)
        cleaned = fix_ocr_errors(cleaned)
        paragraphs = reconstruct_paragraphs(cleaned)
        
        if not paragraphs or all(len(p.strip()) < 5 for p in paragraphs):
            continue
        
        # 코드와 산문 분리
        blocks = []
        for para in paragraphs:
            if looks_like_code(para):
                blocks.append({"type": "code", "text": para})
            else:
                blocks.append({"type": "prose", "text": para})
        
        processed.append({
            "timestamp": rp.get("timestamp", ""),
            "original": raw,
            "blocks": blocks,
        })
    
    print(f"  Pages after cleanup: {len(processed)}")
    
    # ── 3. 번역 ──
    print("\n[3/7] Translating prose to Korean...")
    prose_blocks = [(i, j) for i, p in enumerate(processed) 
                    for j, b in enumerate(p["blocks"]) 
                    if b["type"] == "prose"]
    total = len(prose_blocks)
    
    for count, (pi, bi) in enumerate(prose_blocks, 1):
        block = processed[pi]["blocks"][bi]
        pct = count / total * 100
        if count % 10 == 0 or count == total:
            print(f"  [{count}/{total}] {pct:.0f}%")
        block["translated"] = translate_text(block["text"])
        time.sleep(0.3)
    
    print(f"  Translation complete: {total} blocks")
    
    # ── 4. 원본 영상 검증 ──
    print("\n[4/7] Verifying against original video frames...")
    verify_results = verify_against_video(processed, VERIFY_SAMPLE_COUNT)
    ok_count = sum(1 for r in verify_results if r.get("status") == "OK")
    print(f"  Verified: {ok_count}/{len(verify_results)} frames match")
    
    for r in verify_results:
        status = r.get("status", "?")
        sim = r.get("similarity", 0)
        print(f"    Page {r.get('page','?')} [{r.get('timestamp','')}] "
              f"sim={sim:.3f} => {status}")
    
    # ── 5. 검증 로그 ──
    print("\n[5/7] Writing verification log...")
    with open(VERIFY_LOG, "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write("  OCR Verification Log\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Total raw pages: {len(raw_pages)}\n")
        f.write(f"Pages after cleanup: {len(processed)}\n")
        f.write(f"OCR corrections applied: {len(OCR_FIX)} patterns\n")
        f.write(f"Navigation noise patterns: {len(NAV_NOISE_PATTERNS)} patterns\n")
        f.write(f"Translated blocks: {total}\n\n")
        f.write("-" * 60 + "\n")
        f.write("Frame Verification Results:\n")
        f.write("-" * 60 + "\n")
        for r in verify_results:
            f.write(f"  Page {r.get('page','?'):>3} [{r.get('timestamp',''):>6}] "
                    f"similarity={r.get('similarity',0):.3f}  "
                    f"status={r.get('status','?')}\n")
            if r.get("original_preview"):
                f.write(f"    Original: {r['original_preview']}\n")
            if r.get("verify_preview"):
                f.write(f"    Verify  : {r['verify_preview']}\n")
            f.write("\n")
        f.write("-" * 60 + "\n")
        f.write("\nApplied OCR corrections:\n")
        for wrong, correct in OCR_FIX.items():
            f.write(f"  '{wrong}' -> '{correct}'\n")
    print(f"  Saved: {VERIFY_LOG}")
    
    # ── 6. MD 생성 ──
    print("\n[6/7] Generating Markdown...")
    md = build_markdown(processed)
    OUTPUT_MD.write_text(md, encoding="utf-8")
    print(f"  Saved: {OUTPUT_MD} ({len(md):,} bytes)")
    
    # ── 7. HTML 생성 ──
    print("\n[7/7] Generating HTML...")
    html = build_html(processed)
    OUTPUT_HTML.write_text(html, encoding="utf-8")
    print(f"  Saved: {OUTPUT_HTML} ({len(html):,} bytes)")
    
    print(f"\n{'=' * 60}")
    print(f"  ✅ All done!")
    print(f"  📄 MD  : {OUTPUT_MD.absolute()}")
    print(f"  🌐 HTML: {OUTPUT_HTML.absolute()}")
    print(f"  📋 Log : {VERIFY_LOG.absolute()}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
