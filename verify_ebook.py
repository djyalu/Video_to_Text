import re, sys, os
sys.stdout.reconfigure(encoding='utf-8')

html = open('ServiceNow_Handbook_Premium_Ebook.html', 'r', encoding='utf-8').read()

# 1. File size
size_mb = os.path.getsize('ServiceNow_Handbook_Premium_Ebook.html') / 1024 / 1024
print(f"File size: {size_mb:.1f} MB")
page_count = len(re.findall(r'<article class="page-container"', html))
print(f"Total pages: {page_count}")

# 2. CSS checks
print("\n=== CSS Layout Checks ===")
checks = {
    "en-section border-left": "border-left: 3px solid var(--accent)" in html,
    "ko font-weight 400": "font-weight: 400" in html,
    "ko text-indent": "text-indent: 0.5em" in html,
    "en <p> tags (paragraph)": '<p class="en">' in html,
    "ko <p> tags (paragraph)": '<p class="ko">' in html,
    "en-section wrapper": 'class="en-section"' in html,
    "ko-section wrapper": 'class="ko-section"' in html,
    "chapter gradient bg": "chapter-bg" in html,
    "ch-decoration": "ch-decoration" in html,
    "code box shadow": "box-shadow: 0 4px 12px" in html,
    "pre-wrap REMOVED": "white-space: pre-wrap" not in html,
}
for k, v in checks.items():
    print(f"  {k}: {'✅' if v else '❌'}")

# 3. Page 3 - paragraph structure
print("\n=== P3 Text (paragraph structure) ===")
m = re.search(r'id="page-3".*?<div class="content-body">(.*?)</article>', html, re.DOTALL)
if m:
    content = m.group(1)
    en_paras = re.findall(r'<p class="en">(.*?)</p>', content, re.DOTALL)
    ko_paras = re.findall(r'<p class="ko">(.*?)</p>', content, re.DOTALL)
    print(f"  EN paragraphs: {len(en_paras)}")
    for i, p in enumerate(en_paras[:3]):
        print(f"    EN[{i}]: {p.strip()[:100]}...")
    print(f"  KO paragraphs: {len(ko_paras)}")
    for i, p in enumerate(ko_paras[:3]):
        print(f"    KO[{i}]: {p.strip()[:100]}...")

# 4. Page 14 - code blocks
print("\n=== P14 Code Blocks ===")
m = re.search(r'id="page-14".*?</article>', html, re.DOTALL)
if m:
    content = m.group(0)
    codes = re.findall(r'<code>(.*?)</code>', content, re.DOTALL)
    print(f"  Code blocks: {len(codes)}")
    for i, c in enumerate(codes):
        print(f"  Code[{i}] ({len(c)}chars): {c.strip()[:120]}...")

# 5. OCR typo check
print("\n=== OCR Typo Check ===")
typos = ["shayta", "rorever", "funetion", "seript", "Servicenow"]
for t in typos:
    found = len(re.findall(t, html, re.IGNORECASE))
    print(f"  '{t}': {found} found {'✅' if found == 0 else '❌'}")
