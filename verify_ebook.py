import re, sys
sys.stdout.reconfigure(encoding='utf-8')

html = open('ServiceNow_Handbook_Premium_Ebook.html', 'r', encoding='utf-8').read()

# P13 - function sayHello()
print("=== P13 Code Blocks (Indentation Check) ===")
m = re.search(r'id="page-13".*?</article>', html, re.DOTALL)
if m:
    codes = re.findall(r'<code>(.*?)</code>', m.group(0), re.DOTALL)
    for i, c in enumerate(codes):
        print(f'\nCode[{i}]:')
        for line in c.split('\n'):
            print(f'  |{line}|')

# P14 - GlideRecord
print("\n=== P14 Code Blocks ===")
m = re.search(r'id="page-14".*?</article>', html, re.DOTALL)
if m:
    codes = re.findall(r'<code>(.*?)</code>', m.group(0), re.DOTALL)
    for i, c in enumerate(codes):
        print(f'\nCode[{i}]:')
        for line in c.split('\n')[:8]:
            print(f'  |{line}|')

# P21 - more complex nesting
print("\n=== P21 Code Blocks ===")
m = re.search(r'id="page-21".*?</article>', html, re.DOTALL)
if m:
    codes = re.findall(r'<code>(.*?)</code>', m.group(0), re.DOTALL)
    for i, c in enumerate(codes):
        print(f'\nCode[{i}]:')
        for line in c.split('\n')[:10]:
            print(f'  |{line}|')
