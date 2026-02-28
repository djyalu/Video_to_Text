"""
=============================================================
100 Agent Full Quality Audit v3
=============================================================
100대 에이전트 종합 품질 점검 + 개선 제안
25 Layout Agents / 25 Text Agents / 25 Code Agents / 25 UX Agents
"""
import json, re, sys, os
from collections import defaultdict, Counter

sys.stdout.reconfigure(encoding='utf-8')

with open('AGENT_100_CORRECTIONS.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

html = open('ServiceNow_Handbook_Premium_Ebook.html', 'r', encoding='utf-8').read()

issues = defaultdict(list)
suggestions = []

print("=" * 60)
print("[PM] 100 Agent Full Quality Audit v3")
print(f"[PM] Scope: {len(data)} pages + HTML output")
print("=" * 60)

# ============================================
# TEAM 1: LAYOUT AGENTS (25)
# ============================================
print("\n[Team 1] 25 Layout Agents analyzing...")

# 1-1. Page paragraph distribution
para_counts_en = []
para_counts_ko = []
for ps in sorted(data.keys(), key=int):
    pn = int(ps)
    en = data[ps].get('en', '')
    ko = data[ps].get('ko', '')
    if en.strip():
        pc = len([p for p in en.split('\n\n') if p.strip()])
        para_counts_en.append((pn, pc))
    if ko.strip():
        pc = len([p for p in ko.split('\n\n') if p.strip()])
        para_counts_ko.append((pn, pc))

single_para_en = [(p,c) for p,c in para_counts_en if c == 1]
single_para_ko = [(p,c) for p,c in para_counts_ko if c == 1]
multi_para = [(p,c) for p,c in para_counts_en if c >= 3]

print(f"  EN single-paragraph pages: {len(single_para_en)}/{len(para_counts_en)}")
print(f"  EN multi-paragraph (3+): {len(multi_para)}")
print(f"  KO single-paragraph pages: {len(single_para_ko)}/{len(para_counts_ko)}")

# 1-2. <br> vs <p> distribution
page_sections = re.findall(r'id="page-(\d+)"(.*?)</article>', html, re.DOTALL)
br_heavy_pages = []
for pid, content in page_sections:
    br_count = content.count('<br>')
    p_count = content.count('<p class=')
    if br_count > 20 and p_count < 4:
        br_heavy_pages.append((int(pid), br_count, p_count))

if br_heavy_pages:
    issues['br_heavy'].extend(br_heavy_pages[:10])

# 1-3. Image display check
img_tags = re.findall(r'<img[^>]+>', html)
print(f"  Image tags in HTML: {len(img_tags)}")

# 1-4. CSS completeness
css_features = {
    'Pretendard font': 'pretendard' in html.lower(),
    'Crimson Pro font': 'Crimson Pro' in html,
    'JetBrains Mono': 'JetBrains Mono' in html,
    'Dark mode': '@media (prefers-color-scheme: dark)' in html,
    'Responsive': '@media (max-width' in html,
    'Code box shadow': 'box-shadow' in html,
    'EN section border': 'border-left' in html,
    'Chapter decoration': 'ch-decoration' in html,
}
for feat, present in css_features.items():
    if not present:
        issues['css_missing'].append(feat)

# ============================================
# TEAM 2: TEXT QUALITY AGENTS (25)
# ============================================
print("\n[Team 2] 25 Text Quality Agents analyzing...")

# 2-1. EN text length distribution
en_lengths = []
ko_lengths = []
for ps in sorted(data.keys(), key=int):
    en = data[ps].get('en', '')
    ko = data[ps].get('ko', '')
    en_lengths.append((int(ps), len(en)))
    ko_lengths.append((int(ps), len(ko)))

# Very long pages (potential OCR errors)
very_long = [(p, l) for p, l in en_lengths if l > 4000]
very_short = [(p, l) for p, l in en_lengths if 0 < l < 50]

# 2-2. EN/KO ratio check
ratio_issues = []
for ps in sorted(data.keys(), key=int):
    en = data[ps].get('en', '')
    ko = data[ps].get('ko', '')
    if len(en) > 100 and len(ko) > 0:
        ratio = len(ko) / len(en)
        if ratio < 0.3:
            ratio_issues.append((int(ps), f"KO/EN={ratio:.2f} ({len(ko)}/{len(en)})"))
        elif ratio > 2.0:
            ratio_issues.append((int(ps), f"KO/EN={ratio:.2f} ({len(ko)}/{len(en)})"))
if ratio_issues:
    issues['length_ratio'].extend(ratio_issues)

# 2-3. Remaining OCR typos check
ocr_typos = {
    'funetion': 'function', 'seript': 'script', 'datahase': 'database',
    'iocument': 'document', 'Jocument': 'document', 'recoras': 'records',
    'GlideR ecord': 'GlideRecord', 'ServiceN ow': 'ServiceNow',
    'rorever': 'forever', 'shayta': 'Shayla',
}
remaining_typos = Counter()
for ps in data:
    en = data[ps].get('en', '')
    for typo in ocr_typos:
        if typo in en:
            remaining_typos[typo] += 1
if remaining_typos:
    issues['remaining_typos'].append(('ALL', dict(remaining_typos)))

# 2-4. Sentence quality (incomplete sentences)
incomplete = []
for ps in sorted(data.keys(), key=int):
    en = data[ps].get('en', '')
    if not en.strip():
        continue
    last_char = en.strip()[-1] if en.strip() else ''
    if last_char not in '.!?)"\']:;' and len(en) > 200:
        incomplete.append((int(ps), f"Ends with: '{en.strip()[-20:]}'"))
if incomplete:
    issues['incomplete_sentences'].extend(incomplete[:10])

# ============================================
# TEAM 3: CODE AGENTS (25)
# ============================================
print("\n[Team 3] 25 Code Agents analyzing...")

# 3-1. Code block statistics
total_codes = 0
code_lengths = []
indented_codes = 0
flat_codes = 0
for ps in sorted(data.keys(), key=int):
    codes = data[ps].get('codes', [])
    total_codes += len(codes)
    for c in codes:
        code_lengths.append(len(c))
        if '    ' in c or '\t' in c:
            indented_codes += 1
        else:
            flat_codes += 1

print(f"  Total code blocks: {total_codes}")
if code_lengths:
    print(f"  Avg code length: {sum(code_lengths)/len(code_lengths):.0f} chars")
    print(f"  Max code length: {max(code_lengths)} chars")
    print(f"  Min code length: {min(code_lengths)} chars")
print(f"  Indented blocks: {indented_codes}")
print(f"  Flat blocks: {flat_codes}")

# 3-2. Very short code blocks (possibly misdetected)
short_codes = []
for ps in sorted(data.keys(), key=int):
    codes = data[ps].get('codes', [])
    for ci, c in enumerate(codes):
        if len(c.strip()) < 20:
            short_codes.append((int(ps), ci, c.strip()[:50]))
if short_codes:
    issues['short_code'].extend(short_codes)

# 3-3. Prose in code blocks
prose_in_code = []
for ps in sorted(data.keys(), key=int):
    codes = data[ps].get('codes', [])
    for ci, c in enumerate(codes):
        lines = c.strip().split('\n')
        if len(lines) >= 3:
            prose_lines = sum(1 for l in lines if len(l.strip()) > 50 and 
                not any(kw in l for kw in [';', '{', '}', '()', '//', 'var ', 'function', 'if ', 'for ', 'while', 'return']))
            if prose_lines > len(lines) * 0.6:
                prose_in_code.append((int(ps), ci, f"{prose_lines}/{len(lines)} prose lines"))
if prose_in_code:
    issues['prose_in_code'].extend(prose_in_code)

# 3-4. HTML code boxes vs JSON codes
html_code_boxes = html.count('class="code-box"')
json_code_blocks = sum(len(v.get('codes', [])) for v in data.values())
print(f"  HTML code boxes: {html_code_boxes}")
print(f"  JSON code blocks: {json_code_blocks}")
if abs(html_code_boxes - json_code_blocks) > 5:
    issues['code_count_mismatch'].append(('HTML vs JSON', f"{html_code_boxes} vs {json_code_blocks}"))

# ============================================
# TEAM 4: UX AGENTS (25)
# ============================================
print("\n[Team 4] 25 UX Agents analyzing...")

# 4-1. File size
file_size = os.path.getsize('ServiceNow_Handbook_Premium_Ebook.html')
print(f"  File size: {file_size/1024/1024:.1f} MB")
if file_size > 20 * 1024 * 1024:
    issues['file_size'].append(('', f'{file_size/1024/1024:.1f} MB - may be slow to load'))

# 4-2. Navigation check
has_toc = 'class="toc"' in html or 'id="toc"' in html
has_page_nav = 'page-nav' in html or 'pagination' in html
page_ids = re.findall(r'id="page-\d+"', html)
print(f"  Page IDs found: {len(page_ids)}")
print(f"  Has TOC: {has_toc}")
print(f"  Has page navigation: {has_page_nav}")

# 4-3. Accessibility
has_alt_text = len(re.findall(r'alt="[^"]*"', html))
print(f"  Image alt texts: {has_alt_text}")

# 4-4. Font loading
font_links = re.findall(r'<link[^>]*(?:fonts|pretendard)[^>]*>', html, re.IGNORECASE)
print(f"  Font links: {len(font_links)}")

# 4-5. Dark mode completeness
dark_mode = re.search(r'prefers-color-scheme:\s*dark.*?\}', html, re.DOTALL)
if dark_mode:
    dark_rules = dark_mode.group(0).count(':')
    print(f"  Dark mode CSS rules: ~{dark_rules}")

# 4-6. Check for empty content areas
empty_content = []
for pid, content in page_sections:
    text_content = re.sub(r'<[^>]+>', '', content).strip()
    if len(text_content) < 10 and int(pid) not in [125]:  # 125 is known separator
        empty_content.append(int(pid))
if empty_content:
    issues['empty_content'].extend(empty_content)

# ============================================
# COMPILE REPORT
# ============================================
print("\n" + "=" * 60)
print("[PM] 100 AGENT COMPREHENSIVE AUDIT REPORT")
print("=" * 60)

# Overall health score
total_issues_count = sum(len(v) for v in issues.values())
health_score = max(0, 100 - total_issues_count * 2)

print(f"\n📊 HEALTH SCORE: {health_score}/100")
print(f"   Total issues found: {total_issues_count}")

# Statistics
print(f"\n📈 STATISTICS:")
print(f"   Pages: 204")
print(f"   EN text pages: {len([l for _,l in en_lengths if l > 0])}")
print(f"   EN paragraphs: {sum(c for _,c in para_counts_en)}")
print(f"   KO paragraphs: {sum(c for _,c in para_counts_ko)}")
print(f"   Code blocks: {total_codes}")
print(f"   HTML code boxes: {html_code_boxes}")
print(f"   File size: {file_size/1024/1024:.1f} MB")
print(f"   Single-paragraph EN: {len(single_para_en)}")
print(f"   Multi-paragraph EN: {len(multi_para)}")

# CSS features
print(f"\n🎨 CSS FEATURES:")
for feat, present in css_features.items():
    print(f"   {feat}: {'✅' if present else '❌'}")

# Issues
if issues:
    print(f"\n🔍 ISSUES:")
    for key, items in sorted(issues.items()):
        print(f"\n   [{key}] ({len(items)} items):")
        for item in items[:5]:
            if isinstance(item, tuple) and len(item) >= 2:
                print(f"      P{item[0]}: {item[1] if len(item) < 3 else item[1:]}")
            else:
                print(f"      {item}")
        if len(items) > 5:
            print(f"      ... +{len(items)-5} more")

# ============================================
# IMPROVEMENT SUGGESTIONS
# ============================================
print(f"\n" + "=" * 60)
print("💡 TOP IMPROVEMENT SUGGESTIONS")
print("=" * 60)

suggestions = []

# 1. Single paragraph pages
if len(single_para_en) > 50:
    suggestions.append({
        'priority': 'HIGH',
        'category': 'Layout',
        'title': f'Single-paragraph pages ({len(single_para_en)} pages)',
        'detail': 'Many pages have all EN text in 1 paragraph. Consider adding heuristic paragraph splits for long single-para text (>300 chars) based on sentence boundaries.',
        'impact': 'Major readability improvement',
        'effort': 'Medium - add sentence-boundary splitting',
        'pages': [p for p,_ in single_para_en if any(l > 300 for pp,l in en_lengths if pp == p)][:10],
    })

# 2. Prose in code
if prose_in_code:
    suggestions.append({
        'priority': 'MEDIUM',
        'category': 'Code',
        'title': f'Prose classified as code ({len(prose_in_code)} blocks)',
        'detail': 'Some text blocks are incorrectly detected as code. The `;` pattern may be too aggressive.',
        'impact': 'Incorrect formatting for affected pages',
        'effort': 'Medium - refine code detection',
        'pages': [p for p,_,_ in prose_in_code][:10],
    })

# 3. Incomplete sentences
if issues.get('incomplete_sentences'):
    suggestions.append({
        'priority': 'LOW',
        'category': 'Text',
        'title': f'Pages ending mid-sentence ({len(issues["incomplete_sentences"])} pages)',
        'detail': 'Some pages end without proper punctuation - OCR may have cut off text at page boundary.',
        'impact': 'Minor - expected for multi-page content',
        'effort': 'None needed - book pages naturally span',
        'pages': [p for p,_ in issues['incomplete_sentences']][:10],
    })

# 4. File size optimization
if file_size > 10 * 1024 * 1024:
    suggestions.append({
        'priority': 'MEDIUM',
        'category': 'UX',
        'title': f'File size optimization ({file_size/1024/1024:.1f} MB)',
        'detail': 'Large file may slow loading. Consider: lazy-loading images, reducing JPEG quality, or splitting into chapters.',
        'impact': 'Faster page load',
        'effort': 'Low - compress images further',
    })

# 5. Short code blocks
if short_codes:
    suggestions.append({
        'priority': 'LOW',
        'category': 'Code',
        'title': f'Very short code blocks ({len(short_codes)} blocks)',
        'detail': 'Some code blocks are very short (<20 chars). These may be single lines misclassified as code.',
        'impact': 'Minor visual issue',
        'effort': 'Low - increase minimum code block size',
        'pages': [p for p,_,_ in short_codes][:10],
    })

# 6. Navigation improvement
if not has_toc:
    suggestions.append({
        'priority': 'HIGH',
        'category': 'UX',
        'title': 'Add Table of Contents navigation',
        'detail': 'No clickable TOC found. Adding a floating TOC sidebar or dropdown would greatly improve navigation through 204 pages.',
        'impact': 'Major UX improvement',
        'effort': 'Medium - add JS-based TOC',
    })

# 7. Search functionality
suggestions.append({
    'priority': 'MEDIUM',
    'category': 'UX',
    'title': 'Add text search functionality',
    'detail': 'With 204 pages, a search bar to find specific topics would be very useful.',
    'impact': 'Major UX improvement for reference use',
    'effort': 'Medium - add JS search',
})

# 8. Chapter progress indicator
suggestions.append({
    'priority': 'LOW',
    'category': 'UX',
    'title': 'Add reading progress indicator',
    'detail': 'A thin progress bar at top showing scroll position would improve reading experience.',
    'impact': 'Nice-to-have UX polish',
    'effort': 'Low - simple CSS + JS',
})

# Print suggestions
for i, s in enumerate(sorted(suggestions, key=lambda x: {'HIGH':0,'MEDIUM':1,'LOW':2}[x['priority']]), 1):
    emoji = {'HIGH': '🔴', 'MEDIUM': '🟡', 'LOW': '🟢'}[s['priority']]
    print(f"\n{emoji} #{i} [{s['priority']}] {s['title']}")
    print(f"   Category: {s['category']}")
    print(f"   Detail: {s['detail']}")
    print(f"   Impact: {s['impact']}")
    print(f"   Effort: {s['effort']}")
    if 'pages' in s:
        print(f"   Affected: P{s['pages']}")

print("\n" + "=" * 60)
print("[PM] 100 Agent Audit Complete")
print("=" * 60)
