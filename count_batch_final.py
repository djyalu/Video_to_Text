
from bs4 import BeautifulSoup

def count_blocks(html_path, start, end):
    with open(html_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')
    
    pages = soup.find_all('section', class_='page')
    for i, page in enumerate(pages, 1):
        if start <= i <= end:
            bilinguals = page.find_all('div', class_='bilingual')
            print(f"Page {i}: {len(bilinguals)} blocks")

if __name__ == "__main__":
    count_blocks('ServiceNow_Handbook_Bilingual.html', 151, 204)
