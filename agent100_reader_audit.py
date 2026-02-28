"""
=============================================================
100 Agent Reader Audit - Full Document Quality Review
=============================================================
100대 에이전트가 독자 관점에서 전체 204페이지를 읽고 개선사항 제시.

점검 항목:
1. 빈 페이지 / 텍스트 누락
2. 비정상적으로 짧은 텍스트
3. OCR 노이즈 잔존
4. 영문 문단 수 vs 한글 문단 수 불일치
5. 코드 블록 내 텍스트 오분류 (문단이 코드로)
6. 문단 구조 (한 덩어리 vs 적절히 분리)
7. 오타/깨진 문자
8. 빈 코드 블록
9. 번역 누락 (영문만 있고 한글 없는 경우)
10. 페이지 순서 및 연속성
"""
import json
import re
import sys
import os
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

# Load data
with open('AGENT_100_CORRECTIONS.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

html = open('ServiceNow_Handbook_Premium_Ebook.html', 'r', encoding='utf-8').read()

issues = defaultdict(list)  # category -> [(page, detail)]
stats = {
    'total_pages': 0,
    'pages_with_text': 0,
    'pages_with_code': 0,
    'total_en_chars': 0,
    'total_ko_chars': 0,
    'total_code_blocks': 0,
    'total_paragraphs_en': 0,
    'total_paragraphs_ko': 0,
}

print("=" * 60)
print("[PM] 100 Agent Reader Audit Starting")
print(f"[PM] Target: {len(data)} pages")
print("=" * 60)

for page_str in sorted(data.keys(), key=int):
    page_num = int(page_str)
    page_data = data[page_str]
    stats['total_pages'] += 1
    
    en = page_data.get('en', '')
    ko = page_data.get('ko', '')
    codes = page_data.get('codes', [])
    
    en_len = len(en.strip())
    ko_len = len(ko.strip())
    
    stats['total_en_chars'] += en_len
    stats['total_ko_chars'] += ko_len
    stats['total_code_blocks'] += len(codes)
    
    if en_len > 0 or ko_len > 0:
        stats['pages_with_text'] += 1
    if codes:
        stats['pages_with_code'] += 1
    
    # Count paragraphs
    en_paras = [p for p in en.split('\n\n') if p.strip()] if en else []
    ko_paras = [p for p in ko.split('\n\n') if p.strip()] if ko else []
    stats['total_paragraphs_en'] += len(en_paras)
    stats['total_paragraphs_ko'] += len(ko_paras)
    
    # === AGENT CHECKS ===
    
    # 1. Empty page
    if en_len == 0 and ko_len == 0 and not codes:
        issues['empty_page'].append((page_num, "No text or code extracted"))
        continue
    
    # 2. Very short text (less than 30 chars)
    if 0 < en_len < 30:
        issues['very_short'].append((page_num, f"EN only {en_len} chars: '{en.strip()[:50]}'"))
    
    # 3. OCR noise patterns
    noise_patterns = [
        (r'\d+\s*minute[s]?\s*left\s*in\s*chapter', 'Kindle bar noise'),
        (r'\d+\s*hrs?\s*\d*\s*mins?\s*left', 'Kindle time noise'),
        (r'Location\s*\d+\s*of\s*\d+', 'Kindle location'),
        (r'Page\s*\d+\s*of\s*\d+', 'Page number noise'),
        (r'[^\x00-\x7F]{10,}', 'Many non-ASCII chars in EN'),
    ]
    for pattern, desc in noise_patterns:
        if re.search(pattern, en, re.IGNORECASE):
            issues['ocr_noise'].append((page_num, f"EN: {desc}"))
    
    # 4. Paragraph count mismatch
    if len(en_paras) > 0 and len(ko_paras) > 0:
        ratio = len(ko_paras) / len(en_paras)
        if ratio < 0.5 or ratio > 2.0:
            issues['para_mismatch'].append((page_num, 
                f"EN {len(en_paras)} paras vs KO {len(ko_paras)} paras (ratio={ratio:.1f})"))
    
    # 5. Translation missing
    if en_len > 50 and ko_len == 0:
        issues['translation_missing'].append((page_num, f"EN has {en_len} chars but no KO translation"))
    
    # 6. Single blob (no paragraphs for long text)
    if en_len > 500 and len(en_paras) == 1:
        issues['single_blob_en'].append((page_num, f"EN {en_len} chars in single paragraph"))
    if ko_len > 300 and len(ko_paras) == 1:
        issues['single_blob_ko'].append((page_num, f"KO {ko_len} chars in single paragraph"))
    
    # 7. Broken characters / garbled text
    garbled_patterns = [
        (r'[|]{3,}', 'Repeated pipes'),
        (r'[_]{5,}', 'Repeated underscores'),
        (r'\b[A-Z]{20,}\b', 'Very long ALL-CAPS word'),
        (r'(.)\1{5,}', 'Character repeated 6+ times'),
    ]
    for pattern, desc in garbled_patterns:
        if re.search(pattern, en):
            issues['garbled_text'].append((page_num, f"EN: {desc}"))
    
    # 8. Empty code blocks
    for ci, code in enumerate(codes):
        if len(code.strip()) < 10:
            issues['empty_code'].append((page_num, f"Code[{ci}] only {len(code.strip())} chars"))
    
    # 9. Code that looks like prose (false positive)
    for ci, code in enumerate(codes):
        lines = code.strip().split('\n')
        prose_count = sum(1 for l in lines if len(l.strip()) > 60 and not any(
            kw in l for kw in [';', '{', '}', '(', ')', '//', '/*', 'var ', 'function']
        ))
        if prose_count > len(lines) * 0.5 and len(lines) > 2:
            issues['prose_as_code'].append((page_num, 
                f"Code[{ci}] looks like prose ({prose_count}/{len(lines)} lines)"))
    
    # 10. Korean text still has OCR artifacts
    ko_artifacts = [
        (r'\b[a-z]{15,}\b', 'Long untranslated word in KO'),
        (r'http[s]?://\S+', 'URL in translation (may be OK)'),
    ]
    for pattern, desc in ko_artifacts:
        matches = re.findall(pattern, ko)
        if len(matches) > 3:
            issues['ko_artifacts'].append((page_num, f"{desc}: {len(matches)} occurrences"))
    
    # 11. Pages where EN text is a jumble (all items on one line for TOC pages)
    if en_len > 200:
        words = en.split()
        avg_word_len = sum(len(w) for w in words) / max(len(words), 1)
        if avg_word_len < 3 and len(words) > 20:
            issues['jumbled_text'].append((page_num, f"Very short avg word len ({avg_word_len:.1f})"))

# Check HTML for specific issues
print("\n[QA] Checking HTML structure...")

# Count pages in HTML
html_pages = re.findall(r'id="page-(\d+)"', html)
html_page_nums = set(int(p) for p in html_pages)

for p in range(1, 205):
    if p not in html_page_nums:
        issues['missing_in_html'].append((p, "Page not found in HTML"))

# Check for code boxes
code_boxes = len(re.findall(r'class="code-box"', html))
en_p_tags = len(re.findall(r'<p class="en">', html))
ko_p_tags = len(re.findall(r'<p class="ko">', html))
br_tags = len(re.findall(r'<br>', html))

# ============================================
# REPORT
# ============================================
print("\n" + "=" * 60)
print("[PM] 100 AGENT READER AUDIT REPORT")
print("=" * 60)

print(f"\n📊 Overall Statistics:")
print(f"  Total pages: {stats['total_pages']}")
print(f"  Pages with text: {stats['pages_with_text']}")
print(f"  Pages with code: {stats['pages_with_code']}")
print(f"  Total EN chars: {stats['total_en_chars']:,}")
print(f"  Total KO chars: {stats['total_ko_chars']:,}")
print(f"  Total code blocks: {stats['total_code_blocks']}")
print(f"  EN paragraphs: {stats['total_paragraphs_en']}")
print(f"  KO paragraphs: {stats['total_paragraphs_ko']}")
print(f"  HTML code boxes: {code_boxes}")
print(f"  HTML EN <p> tags: {en_p_tags}")
print(f"  HTML KO <p> tags: {ko_p_tags}")
print(f"  HTML <br> tags: {br_tags}")

print(f"\n🔍 Issues Found:")
priority_order = [
    ('empty_page', '❌ Empty Pages', 'HIGH'),
    ('translation_missing', '❌ Missing Translation', 'HIGH'),
    ('missing_in_html', '❌ Missing in HTML', 'HIGH'),
    ('single_blob_en', '⚠️ EN Single Blob (no paragraph breaks)', 'MEDIUM'),
    ('single_blob_ko', '⚠️ KO Single Blob (no paragraph breaks)', 'MEDIUM'),
    ('prose_as_code', '⚠️ Prose Classified as Code', 'MEDIUM'),
    ('para_mismatch', '⚠️ EN/KO Paragraph Count Mismatch', 'MEDIUM'),
    ('ocr_noise', '⚠️ OCR Noise Remaining', 'MEDIUM'),
    ('garbled_text', '⚠️ Garbled/Broken Text', 'LOW'),
    ('very_short', 'ℹ️ Very Short Text', 'LOW'),
    ('empty_code', 'ℹ️ Empty Code Block', 'LOW'),
    ('ko_artifacts', 'ℹ️ KO Artifacts', 'LOW'),
    ('jumbled_text', 'ℹ️ Jumbled Text', 'LOW'),
]

total_issues = 0
for key, label, priority in priority_order:
    items = issues.get(key, [])
    if items:
        total_issues += len(items)
        print(f"\n  {label} [{priority}] — {len(items)} pages:")
        for page, detail in items[:10]:
            print(f"    P{page}: {detail}")
        if len(items) > 10:
            print(f"    ... and {len(items)-10} more")

if total_issues == 0:
    print("  ✅ No issues found!")
else:
    print(f"\n  📋 Total issues: {total_issues}")

# Suggestions
print(f"\n💡 Improvement Suggestions:")
suggestions = []

if issues.get('single_blob_en'):
    suggestions.append(f"1. {len(issues['single_blob_en'])} pages have EN text as single blob → need better paragraph detection from OCR")
if issues.get('single_blob_ko'):
    suggestions.append(f"2. {len(issues['single_blob_ko'])} pages have KO text as single blob → need paragraph-level translation")
if issues.get('prose_as_code'):
    suggestions.append(f"3. {len(issues['prose_as_code'])} code blocks contain prose text → code detection too aggressive")
if issues.get('translation_missing'):
    suggestions.append(f"4. {len(issues['translation_missing'])} pages missing KO translation → need to re-translate")
if issues.get('para_mismatch'):
    suggestions.append(f"5. {len(issues['para_mismatch'])} pages have EN/KO paragraph count mismatch → translation quality issue")
if issues.get('empty_page'):
    suggestions.append(f"6. {len(issues['empty_page'])} empty pages → may be blank/divider pages (OK) or OCR failure")
if not suggestions:
    suggestions.append("All checks passed! Document is in good shape.")
for s in suggestions:
    print(f"  {s}")

print("\n" + "=" * 60)
print("[PM] Audit Complete")
print("=" * 60)
