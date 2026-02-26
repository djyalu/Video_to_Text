import re

def check_blocks(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    pages = re.findall(r'<section class="page" id="page-(\d+)">(.*?)</section>', content, re.DOTALL)
    
    for page_num_str, page_content in pages:
        page_num = int(page_num_str)
        if 61 <= page_num <= 90:
            blocks = len(re.findall(r'<div class="bilingual">', page_content))
            print(f"Page {page_num}: {blocks} blocks")

if __name__ == "__main__":
    check_blocks(r'F:\projects\Video_to_Text\ServiceNow_Handbook_Bilingual.html')
