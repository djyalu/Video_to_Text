
import os
import re
import sys
from pathlib import Path
from bs4 import BeautifulSoup

# Ensure stdout is utf-8 for Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def extract_pages(html_path, start, end):
    with open(html_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')
    
    pages = soup.find_all('section', class_='page')
    for i, page in enumerate(pages, 1):
        if start <= i <= end:
            print(f"--- Page {i} ---")
            bilinguals = page.find_all('div', class_='bilingual')
            for bi in bilinguals:
                en = bi.find('div', class_='lang-en').p.get_text()
                print(f"EN: {en}")
            print()

if __name__ == "__main__":
    extract_pages('ServiceNow_Handbook_Bilingual.html', 151, 204)
