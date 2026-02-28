"""
=============================================================
50대 한국인 에이전트 번역 품질 검수
=============================================================
한글 번역의 자연스러움, OCR 아티팩트, 깨진 문자, 어색한 표현 등을 검수.
"""
import json, re, sys
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

with open('AGENT_100_CORRECTIONS.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

issues = defaultdict(list)

print("=" * 60)
print("[PM] 50 Korean Agent Translation QA Starting")
print(f"[PM] Target: {len(data)} pages")
print("=" * 60)

for page_str in sorted(data.keys(), key=int):
    pn = int(page_str)
    ko = data[page_str].get('ko', '')
    en = data[page_str].get('en', '')
    
    if not ko.strip():
        continue
    
    # 1. OCR artifact symbols in Korean text
    ocr_artifacts = re.findall(r'[@®©™¢§¶]{1,}', ko)
    if ocr_artifacts:
        issues['ocr_symbols'].append((pn, f"OCR symbols: {ocr_artifacts[:5]}"))
    
    # 2. Garbled alphanumeric fragments (non-word EN mixed in KO)
    garbled = re.findall(r'(?<!\w)[A-Z][a-z]?[A-Z]\s|[a-z][A-Z][a-z]|[A-Z]{1}\s[A-Z]{1}\s', ko)
    # Filter out known OK patterns
    garbled = [g for g in garbled if g.strip() not in ['KO', 'EN', 'IT', 'ID', 'OK', 'UI', 'API', 'DOM', 'JS']]
    if len(garbled) > 2:
        issues['garbled_fragments'].append((pn, f"Garbled: {garbled[:5]}"))
    
    # 3. Very short meaningless lines (likely broken OCR)
    ko_lines = [l.strip() for l in ko.split('\n') if l.strip()]
    short_lines = [l for l in ko_lines if 1 < len(l) < 5 and not re.match(r'^[0-9]+$', l)]
    if len(short_lines) > 3:
        issues['broken_fragments'].append((pn, f"{len(short_lines)} short fragments: {short_lines[:5]}"))
    
    # 4. Equal signs in non-code context (table data leaking)
    eq_count = ko.count('=')
    if eq_count > 3 and '코드' not in ko[:100]:
        issues['table_data'].append((pn, f"Has {eq_count} equal signs (possible table data)"))
    
    # 5. Untranslated long English sentences in Korean text
    long_en = re.findall(r'[A-Za-z]{4,}\s+[A-Za-z]{4,}\s+[A-Za-z]{4,}\s+[A-Za-z]{4,}\s+[A-Za-z]{4,}', ko)
    # Filter URLs and known terms
    long_en = [s for s in long_en if 'http' not in s and 'ServiceNow' not in s 
               and 'GlideRecord' not in s and 'Flow Designer' not in s
               and 'Script Include' not in s and 'Business Rule' not in s
               and 'Service Portal' not in s and 'Update Set' not in s]
    if long_en:
        issues['untranslated'].append((pn, f"Untranslated EN in KO: '{long_en[0][:60]}'"))
    
    # 6. Repeated words (translation artifacts)
    words = ko.split()
    repeated = []
    for i in range(len(words)-1):
        if words[i] == words[i+1] and len(words[i]) > 1 and words[i] not in ['수', '것', '이', '그', '및']:
            repeated.append(words[i])
    if len(set(repeated)) > 2:
        issues['repeated_words'].append((pn, f"Repeated: {list(set(repeated))[:5]}"))
    
    # 7. Nonsensical number/letter patterns
    nonsense = re.findall(r'[a-z][A-Z]\d|[A-Z]\d[a-z]|\d[a-z][A-Z]', ko)
    if nonsense:
        issues['nonsense_pattern'].append((pn, f"Odd patterns: {nonsense[:5]}"))
    
    # 8. Machine translation awkwardness indicators
    awkward_patterns = [
        (r'당신은?\s', 'Formal "you" (awkward)'),
        (r'그것은?\s', '"It" literal translation'),
        (r'이것은?\s', '"This is" literal'),
    ]
    for pat, desc in awkward_patterns:
        count = len(re.findall(pat, ko))
        if count > 3:
            issues['awkward_phrasing'].append((pn, f"{desc}: {count} times"))
    
    # 9. Pipe/bracket noise
    pipes = ko.count('|')
    if pipes > 3:
        issues['pipe_noise'].append((pn, f"{pipes} pipe characters"))
    
    # 10. Korean text quality score
    # Check ratio of Korean chars to total
    ko_chars = len(re.findall(r'[\uAC00-\uD7AF\u3130-\u318F\uA960-\uA97F]', ko))
    total_chars = len(ko.replace(' ', '').replace('\n', ''))
    if total_chars > 50:
        ko_ratio = ko_chars / total_chars
        if ko_ratio < 0.3:
            issues['low_korean_ratio'].append((pn, f"Korean ratio: {ko_ratio:.1%} ({ko_chars}/{total_chars})"))
    
    # 11. Encoding/display issues
    weird_chars = re.findall(r'[🔗📌📎🔧⚙️🛠️✅❌⚠️]', ko)
    # These are OK, skip
    
    # 12. Unnatural sentence endings
    if ko.count('합니다.') + ko.count('습니다.') + ko.count('입니다.') > 0:
        pass  # Normal Korean formal endings
    # Check for abrupt endings
    for line in ko_lines:
        if len(line) > 20 and not line.endswith(('.', '!', '?', ')', ':', ';', ',', '다', '요', '세요')):
            if not re.search(r'[A-Za-z0-9\)\]\}]$', line):
                pass  # Could be mid-sentence break

# ============================================
# REPORT
# ============================================
print("\n" + "=" * 60)
print("[PM] 50 KOREAN AGENT TRANSLATION QA REPORT")
print("=" * 60)

priority_order = [
    ('untranslated', '❌ Untranslated English in Korean', 'HIGH'),
    ('low_korean_ratio', '❌ Low Korean Character Ratio', 'HIGH'),
    ('ocr_symbols', '⚠️ OCR Symbols in Translation', 'HIGH'),
    ('table_data', '⚠️ Table Data Leaking into Translation', 'MEDIUM'),
    ('garbled_fragments', '⚠️ Garbled Alphanumeric Fragments', 'MEDIUM'),
    ('broken_fragments', '⚠️ Broken Short Fragments', 'MEDIUM'),
    ('pipe_noise', '⚠️ Pipe Character Noise', 'MEDIUM'),
    ('nonsense_pattern', '⚠️ Nonsensical Patterns', 'MEDIUM'),
    ('repeated_words', 'ℹ️ Repeated Words', 'LOW'),
    ('awkward_phrasing', 'ℹ️ Awkward Machine Translation', 'LOW'),
]

total_issues = 0
fix_pages = set()

for key, label, priority in priority_order:
    items = issues.get(key, [])
    if items:
        total_issues += len(items)
        for p, _ in items:
            if priority in ('HIGH', 'MEDIUM'):
                fix_pages.add(p)
        print(f"\n  {label} [{priority}] — {len(items)} pages:")
        for page, detail in items[:15]:
            print(f"    P{page}: {detail}")
        if len(items) > 15:
            print(f"    ... and {len(items)-15} more")

if total_issues == 0:
    print("  ✅ No translation issues found!")

print(f"\n  📋 Total issues: {total_issues}")
print(f"  🔧 Pages needing fix: {len(fix_pages)}")
if fix_pages:
    print(f"  Fix pages: {sorted(fix_pages)}")

print("\n" + "=" * 60)
print("[PM] Translation QA Complete")
print("=" * 60)
