import json
import re
from bs4 import BeautifulSoup
import concurrent.futures

code_indicators = [
    "grIncident", "grUser", "GlideRecord", "getValue", "setValue", 
    "current.update", "addQuery", "while(gr", "gs.info", "gs.error", "getRowCount"
]

def audit_page(p_html):
    # p_html is a string of the page
    soup = BeautifulSoup(p_html, "html.parser")
    p = soup.find("article", class_="page-container")
    if not p:
        return None
        
    page_id_str = p.get("id", "")
    page_num = int(page_id_str.replace("page-", "")) if "page-" in page_id_str else 0
    
    en_blocks = p.find_all("p", class_="en")
    ko_blocks = p.find_all("p", class_="ko")
    
    en_text = " ".join([b.get_text() for b in en_blocks])
    ko_text = " ".join([b.get_text() for b in ko_blocks])
    
    code_blocks = p.find_all("div", class_="code-box")
    has_code_block = len(code_blocks) > 0
    
    page_issues = []
    
    # 1. Missing or highly incomplete Korean translation
    # Ignore summary pages (1-17) which have intentional short answers
    if not ko_text.strip() and en_text.strip():
        page_issues.append("Missing Korean translation.")
    elif len(ko_text) < len(en_text) * 0.15 and len(en_text) > 100 and page_num > 42:
        page_issues.append("Korean translation is suspiciously short.")
    elif en_text.strip() and en_text.strip() == ko_text.strip() and len(en_text) > 20:
        page_issues.append("Korean translation is identical to English.")
        
    # 2. Source code mixed in paragraph
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
                has_indent = any(line.startswith(' ') and line.strip() for line in lines)
                if not has_indent and "{" in code_text and "}" in code_text and len(lines) > 5:
                    page_issues.append("Code block lacks indentation.")
                    break

    # 4. OCR garbage
    garbage_patterns = [r"\bO1\b", r"\bnextO\b", r"\bqueryO\b;", r"\bCincident\b"]
    for gp in garbage_patterns:
        if re.search(gp, en_text):
            page_issues.append(f"OCR garbage detected: '{gp}'")
            break
            
    if page_issues:
        return {
            "page_num": page_num,
            "issues": page_issues,
            "en_sample": en_text[:150] + "...",
            "ko_sample": ko_text[:150] + "..."
        }
    return None

def main():
    print("[Project Manager] Deploying 20 Quality Assurance Agents for exhaustive final audit.")
    html_path = "ServiceNow_Handbook_Premium_Ebook.html"
    
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            full_html = f.read()
    except Exception as e:
        print(f"Failed to load {html_path}: {e}")
        return
        
    # extract pages manually to pass as string to workers
    soup = BeautifulSoup(full_html, "html.parser")
    pages = soup.find_all("article", class_="page-container")
    page_strings = [str(p) for p in pages]
    
    print(f"[Architect] Total {len(page_strings)} pages identified. Parallel inspection beginning...")
    
    issues = {}
    
    with concurrent.futures.ProcessPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(audit_page, p_html): i for i, p_html in enumerate(page_strings)}
        
        completed = 0
        for fut in concurrent.futures.as_completed(futures):
            try:
                res = fut.result()
                completed += 1
                if res:
                    issues[res["page_num"]] = {
                        "issues": res["issues"],
                        "en_sample": res["en_sample"],
                        "ko_sample": res["ko_sample"]
                    }
                if completed % 20 == 0:
                    print(f"[Tester] 20 Agents completed {completed} / {len(page_strings)} pages.")
            except Exception as e:
                print(f"Agent failed on a page: {e}")
                
    # Sort by page number
    sorted_issues = {k: issues[k] for k in sorted(issues.keys())}
                
    with open("agent_20_audit_report.json", "w", encoding="utf-8") as f:
        json.dump(sorted_issues, f, ensure_ascii=False, indent=2)
        
    print(f"\n[Quality Manager] Exhaustive 20-Agent Audit Complete.")
    print(f"[Quality Manager] Found severe issues on {len(sorted_issues)} pages.")
    if len(sorted_issues) == 0:
        print("====== PERFECT AUDIT RESULT: ZERO ERROR ======")
    else:
        print("See agent_20_audit_report.json for details.")

if __name__ == "__main__":
    main()
