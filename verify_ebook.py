import re, sys
sys.stdout.reconfigure(encoding='utf-8')

html = open('ServiceNow_Handbook_Premium_Ebook.html', 'r', encoding='utf-8').read()

# P13 code verification
m = re.search(r'id="page-13".*?</article>', html, re.DOTALL)
if m:
    content = m.group(0)
    code_count = content.count('class="code-box"')
    print(f'P13 code-boxes: {code_count}')
    codes = re.findall(r'<code>(.*?)</code>', content, re.DOTALL)
    for i, cc in enumerate(codes):
        print(f'  Code[{i}]:')
        for line in cc.split('\n')[:5]:
            print(f'    | {line}')

# Overall stats
total_code_boxes = html.count('class="code-box"')
print(f'\nTotal code boxes in ebook: {total_code_boxes}')

# Check P14
m = re.search(r'id="page-14".*?</article>', html, re.DOTALL)
if m:
    content = m.group(0)
    code_box_count = content.count('code-box')
    print(f'\nP14 code-boxes: {code_box_count}')
    codes = re.findall(r'<code>(.*?)</code>', content, re.DOTALL)
    for i, cc in enumerate(codes):
        print(f'  Code[{i}] ({len(cc)}c): {cc[:100]}...')
