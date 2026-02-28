import json
import re
from bs4 import BeautifulSoup

def audit_premium_ebook(html_path):
    print(f"Auditing {html_path} exhaustively...")
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f, "html.parser")
    except Exception as e:
        print(f"Failed to load {html_path}: {e}")
        return
    
    pages = soup.find_all("article", class_="page-container")
    
    if len(pages) != 204:
        print(f"WARNING: Found {len(pages)} pages, expected 204.")
        
    issues = {}
    
    code_indicators = [
        "grIncident", "grUser", "GlideRecord", "getValue", "setValue", 
        "current.update", "addQuery", "while(gr", "gs.info", "gs.error", "getRowCount"
    ]
    
    for i, p in enumerate(pages, start=1):
        en_blocks = p.find_all("p", class_="en")
        ko_blocks = p.find_all("p", class_="ko")
        
        en_text = " ".join([b.get_text() for b in en_blocks])
        ko_text = " ".join([b.get_text() for b in ko_blocks])
        
        code_blocks = p.find_all("div", class_="code-box")
        has_code_block = len(code_blocks) > 0
        
        page_issues = []
        
        # 1. Missing or highly incomplete Korean translation
        if not ko_text.strip() and en_text.strip():
            page_issues.append("Missing Korean translation.")
        elif len(ko_text) < len(en_text) * 0.3 and len(en_text) > 100:
            page_issues.append("Korean translation is suspiciously short.")
        elif en_text.strip() and en_text.strip() == ko_text.strip():
            page_issues.append("Korean translation is identical to English (untranslated).")
            
        # 2. Source code mixed in paragraph (no code block but contains code keywords)
        if not has_code_block:
            code_hits = sum(1 for ind in code_indicators if ind in en_text)
            if code_hits >= 2 or re.search(r"\}\s*else\s*\{", en_text) or "Cincident;" in en_text:
                page_issues.append("Source code appears mixed in paragraph text.")
                
        # 3. Indentation check for code blocks
        if has_code_block:
            for cb in code_blocks:
                code_text = cb.get_text()
                lines = code_text.split('\n')
                if len(lines) > 3:
                    # Check if any line has leading spaces (indicating indentation)
                    has_indent = any(line.startswith(' ') and line.strip() for line in lines)
                    if not has_indent and any(kw in code_text for kw in ['function', 'if', 'while', '{']):
                        page_issues.append("Code block lacks indentation.")
                        break

        # 4. OCR garbage
        garbage_patterns = [r"\bO1\b", r"\bnextO\b", r"\bqueryO\b;", r"\bCincident\b"]
        for gp in garbage_patterns:
            if re.search(gp, en_text):
                page_issues.append(f"OCR garbage detected: '{gp}'")
                break
                
        if page_issues:
            issues[i] = {
                "issues": page_issues,
                "en_sample": en_text[:150] + "..." if len(en_text) > 150 else en_text,
                "ko_sample": ko_text[:150] + "..." if len(ko_text) > 150 else ko_text
            }
            
    with open("audit_report_full.json", "w", encoding="utf-8") as f:
        json.dump(issues, f, ensure_ascii=False, indent=2)
        
    print(f"Exhaustive audit complete. Found issues on {len(issues)} pages.")
    print("See audit_report_full.json for details.")

if __name__ == "__main__":
    audit_premium_ebook("ServiceNow_Handbook_Premium_Ebook.html")
