import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from deep_translator import GoogleTranslator

# 에이전트 선언 (사용자 룰 기반)
AGENTS = {
    "PM": "Project Manager",
    "Architect": "아키텍트",
    "Backend": "백엔드 개발자",
    "QA": "품질 관리자",
    "Tester": "테스터",
}

print(f"[{AGENTS['PM']}] 20대의 에이전트를 파견하여 병렬 복구 파이프라인을 가동합니다.")

# OCR 오탈자 수정 사전
OCR_FIXES = {
    r"\bnextO\b": "next()",
    r"\bqueryO\b;?": "query();",
    r"\bO1\b": "Of",
    r"\bCincident\b;?": "('incident');",
    r"\bgetValueC\b'?": "getValue('",
    r"\binsertO\b;?": "insert();",
    r"\bgslogErrorO\b": "gs.logError()",
    r"\bupdateRecordO\b": "updateRecord()",
    r"\bgrIncidentnextO{": "grIncident.next() {",
    r"\bgetRowCountO\b": "getRowCount()",
    r"\baddEncodedQuery'": "addEncodedQuery('",
    r"\bVar\b": "var",
    r" \? ": " a ",
    r"1000\d\s": "",      # 10001 같은 노이즈
    r"10\d+\s+": "",       # 10000 같은 노이즈
    r"O1\s+the\b": "Of the",
}

CODE_KEYWORDS = [
    "var", "function", "if", "while", "for", "return", "GlideRecord", "getValue", "setValue", 
    "current.update", "gs.info", "gs.error", "getRowCount", "addQuery", "updateMultiple"
]

def reconstruct_and_clean(raw_text: str) -> str:
    lines = raw_text.split("\n")
    paragraphs = []
    current = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current:
                paragraphs.append(" ".join(current))
                current = []
            continue
        current.append(stripped)
    if current:
        paragraphs.append(" ".join(current))
    
    text = "\n\n".join(paragraphs)
    # OCR Fixes 적용
    for pattern, replacement in OCR_FIXES.items():
        text = re.sub(pattern, replacement, text)
        
    text = re.sub(r"(\w)- (\w)", r"\1\2", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text

def split_prose_and_code(text: str):
    """최대한 코드를 분리하는 휴리스틱 아키텍처 규칙"""
    sentences = re.split(r'(?<=[.!?]) +', text.replace('\n', ' '))
    prose_blocks = []
    code_blocks = []
    
    current_prose = []
    current_code = []
    is_code_mode = False
    
    for sentence in sentences:
        # 코드스러움(Code-ness) 평가
        code_score = sum(1 for kw in CODE_KEYWORDS if re.search(r'\b'+kw+r'\b', sentence))
        if '{' in sentence or '}' in sentence or ';' in sentence or '//' in sentence:
            code_score += 2
            
        if code_score >= 2 or (is_code_mode and len(sentence) < 40 and not sentence.endswith('.')):
            is_code_mode = True
            current_code.append(sentence)
        else:
            if is_code_mode:
                code_blocks.append(" \n".join(current_code))
                current_code = []
                is_code_mode = False
            current_prose.append(sentence)
            
    if current_prose:
        prose_blocks.append(" ".join(current_prose))
    if current_code:
        code_blocks.append(" \n".join(current_code))
        
    return prose_blocks, code_blocks

def process_page(page_idx):
    """에이전트 단일 작업(Thread) - 페이지당 번역 및 품질 점검 수행"""
    try:
        # 추출결과 상세 로드 (Thread 안에서 안전하게)
        # 이미 로드된 데이터를 사용하지 않고 재로드 (안전한 스레딩)
        page_data = global_pages[page_idx-1]
        raw_text = page_data['text']
        
        # 1. 텍스트 재구성 및 OCR 노이즈 제거
        clean_text = reconstruct_and_clean(raw_text)
        
        # 노이즈 패턴 제거 (페이지 정보 등)
        clean_text = re.sub(r"\d+\s*minute[s]?\s*left.*?\d+%", "", clean_text, flags=re.IGNORECASE)
        clean_text = re.sub(r"Page\s*\d+\s*of\s*\d+", "", clean_text, flags=re.IGNORECASE)
        
        # 2. 코드와 일반 텍스트 분리
        prose_blocks, code_blocks = split_prose_and_code(clean_text)
        
        # 3. 텍스트 번역 (Deep Translator) - 영문이 유효할 때만
        en_text = " ".join(prose_blocks).strip()
        ko_text = ""
        if len(en_text) > 20:
            translator = GoogleTranslator(source="en", target="ko")
            # 최대 길이 분할
            chunks = [en_text[i:i+4000] for i in range(0, len(en_text), 4000)]
            translated_chunks = []
            for chunk in chunks:
                translated_chunks.append(translator.translate(chunk))
            ko_text = " ".join(translated_chunks)
            
        # 4. 포맷팅
        formatted_codes = []
        for c in code_blocks:
            # 기본 세미콜론이나 여는 괄호 뒤에 줄바꿈 추가
            f_code = c.replace("{", "{\n    ").replace(";", ";\n")
            f_code = re.sub(r"\}\s*else", "} else", f_code)
            formatted_codes.append(f_code.strip())
            
        return {
            "page_num": page_idx,
            "success": True,
            "en": en_text,
            "ko": ko_text,
            "codes": formatted_codes
        }
    except Exception as e:
        return {
            "page_num": page_idx,
            "success": False,
            "error": str(e)
        }

if __name__ == "__main__":
    with open('추출결과_상세.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        global_pages = data['pages']
        
    with open('audit_report.json', 'r', encoding='utf-8') as f:
        audit_data = json.load(f)
        bad_pages = [int(k) for k in audit_data.keys()]
        
    print(f"[{AGENTS['Architect']}] 대상 페이지 총 {len(bad_pages)}장 파악 완료. 멀티 스레딩(20 Worker) 분배 시작.")
    
    corrections = {}
    success_count = 0
    fail_count = 0
    
    start_time = time.time()
    
    # 20개 에이전트 동시 구동
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(process_page, p): p for p in bad_pages}
        
        for future in as_completed(futures):
            res = future.result()
            p_num = res["page_num"]
            if res["success"]:
                corrections[p_num] = {
                    "en": res["en"],
                    "ko": res["ko"]
                }
                if res["codes"]:
                    corrections[p_num]["codes"] = res["codes"]
                success_count += 1
                if success_count % 10 == 0:
                    print(f"[{AGENTS['QA']}] {success_count}장 복구 완료. 지속 모니터링 중...")
            else:
                fail_count += 1
                print(f"[{AGENTS['QA']}] 페이지 {p_num} 복구 실패: {res['error']}")
                
    elapsed = time.time() - start_time
    print(f"[{AGENTS['Tester']}] 병렬 작업 완료 (총 소요 시간: {elapsed:.1f}초). 성공: {success_count}, 실패: {fail_count}")
    
    with open("AUTO_RESCUE_CORRECTIONS.json", "w", encoding="utf-8") as f:
        json.dump(corrections, f, ensure_ascii=False, indent=4)
        
    print(f"[{AGENTS['Backend']}] AUTO_RESCUE_CORRECTIONS.json 저장 완료. 다음 단계로 E-Book 통합 작업을 지시하십시오.")
