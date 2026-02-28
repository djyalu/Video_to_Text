import re, sys, os
sys.stdout.reconfigure(encoding='utf-8')

html = open('ServiceNow_Handbook_Premium_Ebook.html', 'r', encoding='utf-8').read()

print(f"File: {os.path.getsize('ServiceNow_Handbook_Premium_Ebook.html')/1024/1024:.1f} MB")
print(f"Pages: {len(re.findall(r'<article class=.page-container.', html))}")

# Font check
print(f"\nPretendard CDN: {'pretendard' in html}")
print(f"Pretendard font-family: {'Pretendard' in html}")

# Page 11 paragraph verification
print("\n=== P11 Paragraph Structure ===")
m = re.search(r'id="page-11".*?<div class="content-body">(.*?)</article>', html, re.DOTALL)
if m:
    content = m.group(1)
    en_paras = re.findall(r'<p class="en">(.*?)</p>', content, re.DOTALL)
    ko_paras = re.findall(r'<p class="ko">(.*?)</p>', content, re.DOTALL)
    print(f"  EN <p> tags: {len(en_paras)}")
    for i, p in enumerate(en_paras[:4]):
        print(f"    EN[{i}]: {p.strip()[:100]}...")
    print(f"  KO <p> tags: {len(ko_paras)}")
    for i, p in enumerate(ko_paras[:4]):
        print(f"    KO[{i}]: {p.strip()[:100]}...")

# Page 3
print("\n=== P3 ===")
m = re.search(r'id="page-3".*?<div class="content-body">(.*?)</article>', html, re.DOTALL)
if m:
    content = m.group(1)
    en_paras = re.findall(r'<p class="en">(.*?)</p>', content, re.DOTALL)
    ko_paras = re.findall(r'<p class="ko">(.*?)</p>', content, re.DOTALL)
    print(f"  EN <p>: {len(en_paras)}, KO <p>: {len(ko_paras)}")
    if en_paras:
        print(f"    EN[0]: {en_paras[0].strip()[:120]}...")
    if len(en_paras)>1:
        print(f"    EN[1]: {en_paras[1].strip()[:120]}...")
