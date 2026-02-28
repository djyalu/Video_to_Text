import json
import concurrent.futures
from deep_translator import GoogleTranslator

def fix_page(args):
    page_id, data = args
    print(f"[Agent-{page_id}] Starting repair on page {page_id}...")
    
    # Add translation if missing
    if not data.get("ko") and data.get("en"):
        try:
            translator = GoogleTranslator(source='en', target='ko')
            data["ko"] = translator.translate(data["en"])
            print(f"[Agent-{page_id}] Translated missing text.")
        except Exception as e:
            print(f"[Agent-{page_id}] Translation failed: {e}")
            
    # Fix code indentation
    fixed_codes = []
    for code in data.get("codes", []):
        lines = code.split("\n")
        new_lines = []
        indent_level = 0
        
        has_indent = any(line.startswith(" ") for line in lines)
        needs_indent_fix = not has_indent and any(kw in code for kw in ['function', 'if', 'while', '{', '}'])
        
        if needs_indent_fix:
            for line in lines:
                l_strip = line.strip()
                if l_strip.startswith("}"):
                    indent_level = max(0, indent_level - 1)
                    
                indent_str = "    " * indent_level
                new_lines.append(indent_str + l_strip)
                
                if l_strip.endswith("{"):
                    indent_level += 1
            fixed_codes.append("\n".join(new_lines))
            print(f"[Agent-{page_id}] Fixed code indentation.")
        else:
            fixed_codes.append(code)
    
    data["codes"] = fixed_codes
    print(f"[Agent-{page_id}] Repair complete.")
    return str(page_id), data

def main():
    print("[Project Manager] Evaluating 7 flagged pages...")
    
    with open("AGENT_100_CORRECTIONS.json", "r", encoding="utf-8") as f:
        corrections = json.load(f)
        
    with open("agent_20_audit_report.json", "r", encoding="utf-8") as f:
        report = json.load(f)
        
    # Gather tasks
    tasks = []
    for pid in report.keys():
        if pid in corrections:
            tasks.append((pid, corrections[pid]))
            
    print(f"[Architect] Dispatching {len(tasks)} tasks to 20 Agents in parallel...")
    
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(fix_page, t): t for t in tasks}
        for fut in concurrent.futures.as_completed(futures):
            pid, data = fut.result()
            results[pid] = data
            
    # merge back
    for pid, data in results.items():
        corrections[pid] = data
        
    with open("AGENT_100_CORRECTIONS.json", "w", encoding="utf-8") as f:
        json.dump(corrections, f, ensure_ascii=False, indent=2)
        
    print("[Project Manager] Updates saved to DB. Ready for E-Book assembly.")

if __name__ == "__main__":
    main()
