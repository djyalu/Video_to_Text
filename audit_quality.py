
import os
from bs4 import BeautifulSoup
from pathlib import Path

INPUT_HTML = Path("ServiceNow_Handbook_Bilingual.html")

def audit_html():
    if not INPUT_HTML.exists():
        print("Input HTML not found.")
        return

    with open(INPUT_HTML, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    pages = soup.find_all("section", class_="page")
    total = len(pages)
    missing_translation = 0
    pages_with_noise = 0
    
    noise_patterns = ["getValue<", "0r", "Var ", "grIncident"] # Common OCR noise markers in prose

    for i, page in enumerate(pages, 1):
        bi = page.find_all("div", class_="bilingual")
        if not bi:
            missing_translation += 1
            print(f"Page {i}: Missing bilingual content.")
        
        text = page.get_text()
        if any(p in text for p in noise_patterns):
            pages_with_noise += 1

    print(f"\nAudit Summary:")
    print(f"Total Pages: {total}")
    print(f"Pages missing translation: {missing_translation}")
    print(f"Pages with likely OCR noise: {pages_with_noise}")

if __name__ == "__main__":
    audit_html()
