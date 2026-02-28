"""
=============================================================
100 Agent Final Audit v4 — Post-UX Upgrade
=============================================================
"""
import json, re, sys, os
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

with open('AGENT_100_CORRECTIONS.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

html = open('ServiceNow_Handbook_Premium_Ebook.html', 'r', encoding='utf-8').read()
file_size = os.path.getsize('ServiceNow_Handbook_Premium_Ebook.html')

print("=" * 60)
print("[PM] 100 Agent Final Audit v4")
print("=" * 60)

score = 100
deductions = []

# ====== CONTENT (40 points) ======
print("\n[A] CONTENT (40 pts)")
pages_with_text = sum(1 for v in data.values() if v.get('en','').strip())
pages_total = len(data)
print(f"  Text coverage: {pages_with_text}/{pages_total} ({pages_with_text/pages_total*100:.1f}%)")

en_paras = sum(len([p for p in v.get('en','').split('\n\n') if p.strip()]) for v in data.values())
ko_paras = sum(len([p for p in v.get('ko','').split('\n\n') if p.strip()]) for v in data.values())
print(f"  EN paragraphs: {en_paras}")
print(f"  KO paragraphs: {ko_paras}")

single_para = sum(1 for v in data.values() if v.get('en','').strip() and len([p for p in v['en'].split('\n\n') if p.strip()]) == 1)
print(f"  Single-para pages: {single_para}")
if single_para > 30:
    d = min(5, (single_para - 30) // 10)
    score -= d
    deductions.append(f"-{d} Single-para pages ({single_para})")

code_blocks = sum(len(v.get('codes',[])) for v in data.values())
print(f"  Code blocks: {code_blocks}")

# OCR typos remaining in EN
typo_check = ['funetion', 'seript', 'datahase', 'iocument', 'Jocument', 'rorever']
remaining = {}
for v in data.values():
    en = v.get('en','')
    for t in typo_check:
        if t in en:
            remaining[t] = remaining.get(t, 0) + 1
if remaining:
    d = min(5, len(remaining))
    score -= d
    deductions.append(f"-{d} OCR typos remaining: {remaining}")
    print(f"  ❌ Remaining typos: {remaining}")
else:
    print(f"  ✅ No OCR typos remaining")

# Translation ratio
bad_ratio = 0
for v in data.values():
    en, ko = v.get('en',''), v.get('ko','')
    if len(en) > 100 and len(ko) > 0:
        r = len(ko)/len(en)
        if r < 0.25 or r > 2.5:
            bad_ratio += 1
if bad_ratio > 5:
    d = min(3, bad_ratio // 3)
    score -= d
    deductions.append(f"-{d} Bad EN/KO ratio ({bad_ratio} pages)")
print(f"  Translation ratio issues: {bad_ratio}")

# ====== CODE QUALITY (15 points) ======
print(f"\n[B] CODE QUALITY (15 pts)")
html_code_boxes = html.count('class="code-box"')
print(f"  JSON blocks: {code_blocks}, HTML boxes: {html_code_boxes}")
if abs(code_blocks - html_code_boxes) > 5:
    d = 3
    score -= d
    deductions.append(f"-{d} Code count mismatch ({code_blocks} vs {html_code_boxes})")
    print(f"  ❌ Mismatch: {code_blocks} vs {html_code_boxes}")
else:
    print(f"  ✅ Code count matches (±{abs(code_blocks-html_code_boxes)})")

# Short codes
short_codes = sum(1 for v in data.values() for c in v.get('codes',[]) if len(c.strip()) < 15)
print(f"  Short code blocks (<15 chars): {short_codes}")

# ====== CSS & DESIGN (20 points) ======
print(f"\n[C] CSS & DESIGN (20 pts)")
css_checks = {
    'Pretendard KO font': 'Pretendard' in html,
    'Crimson Pro EN font': 'Crimson Pro' in html,
    'JetBrains Mono code': 'JetBrains Mono' in html,
    'Dark mode CSS': 'prefers-color-scheme: dark' in html,
    'Dark mode toggle': '.dark-mode' in html,
    'Responsive media': '@media (max-width' in html,
    'Code box shadow': 'box-shadow' in html,
    'EN section border': 'border-left: 3px' in html,
    'Chapter decoration': 'ch-decoration' in html,
    'Gradient header': 'linear-gradient' in html,
}
css_pass = 0
for feat, present in css_checks.items():
    status = '✅' if present else '❌'
    print(f"  {status} {feat}")
    if present:
        css_pass += 1
    else:
        score -= 2
        deductions.append(f"-2 Missing CSS: {feat}")
print(f"  CSS Score: {css_pass}/{len(css_checks)}")

# ====== UX FEATURES (25 points) ======
print(f"\n[D] UX FEATURES (25 pts)")
ux_checks = {
    'Search bar': 'searchPages' in html,
    'Search input': 'placeholder="' in html and 'Search' in html,
    'TOC sidebar panel': 'toc-panel' in html,
    'TOC floating button': 'toc-btn' in html,
    'Progress bar': 'progress-bar' in html,
    'Page counter': 'page-counter' in html or 'pcnt' in html,
    'Dark mode button': 'toggleDarkMode' in html,
    'View mode (EN/KO/Both)': "setViewMode" in html,
    'Image toggle': 'toggleImage' in html,
    'Page anchors (204)': html.count('id="page-') >= 200,
}
ux_pass = 0
for feat, present in ux_checks.items():
    status = '✅' if present else '❌'
    print(f"  {status} {feat}")
    if present:
        ux_pass += 1
    else:
        d = 3
        score -= d
        deductions.append(f"-{d} Missing UX: {feat}")
print(f"  UX Score: {ux_pass}/{len(ux_checks)}")

# ====== HTML STRUCTURE ======
print(f"\n[E] HTML STRUCTURE")
print(f"  File size: {file_size/1024/1024:.1f} MB")
pc = html.count('class="page-container"')
imgs = html.count('<img ')
en_p = html.count('<p class="en">')
ko_p = html.count('<p class="ko">')
br_n = html.count('<br>')
print(f"  Page sections: {pc}")
print(f"  Images: {imgs}")
print(f"  EN <p> tags: {en_p}")
print(f"  KO <p> tags: {ko_p}")
print(f"  <br> tags: {br_n}")
print(f"  Code boxes: {html_code_boxes}")

if file_size > 20*1024*1024:
    score -= 3
    deductions.append(f"-3 File too large ({file_size/1024/1024:.1f} MB)")

# ====== FINAL SCORE ======
score = max(0, min(100, score))

print(f"\n{'='*60}")
print(f"📊 FINAL HEALTH SCORE: {score}/100")
print(f"{'='*60}")

if deductions:
    print(f"\n📉 Deductions:")
    for d in deductions:
        print(f"  {d}")
else:
    print(f"\n✅ No deductions!")

# Grade
if score >= 95:
    grade = 'A+'
elif score >= 90:
    grade = 'A'
elif score >= 85:
    grade = 'B+'
elif score >= 80:
    grade = 'B'
elif score >= 70:
    grade = 'C'
else:
    grade = 'D'

print(f"\n🏆 GRADE: {grade}")

print(f"\n📋 Summary:")
print(f"  Content: {pages_with_text}/{pages_total} pages, {en_paras} EN + {ko_paras} KO paragraphs")
print(f"  Code: {code_blocks} blocks → {html_code_boxes} HTML boxes")
print(f"  CSS: {css_pass}/{len(css_checks)} features")
print(f"  UX: {ux_pass}/{len(ux_checks)} features")
print(f"  File: {file_size/1024/1024:.1f} MB")

print(f"\n{'='*60}")
print(f"[PM] 100 Agent Audit v4 Complete")
print(f"{'='*60}")
