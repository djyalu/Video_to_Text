
import os
import re
from bs4 import BeautifulSoup

def apply_translations(html_path, translations):
    with open(html_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    pages = soup.find_all("section", class_="page")
    
    for page_num, translated_list in translations.items():
        if page_num > len(pages): continue
        page = pages[page_num - 1]
        bilinguals = page.find_all("div", class_="bilingual")
        
        for i, bi in enumerate(bilinguals):
            if i < len(translated_list):
                ko_div = bi.find("div", class_="lang-ko")
                if ko_div and ko_div.p:
                    ko_div.p.string = translated_list[i]

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(str(soup))
    print(f"Applied translation for {len(translations)} pages.")

# Batch 5 (121-150) High Quality Translations
BATCH5_TRANSLATIONS = {
    121: ["스크립트 개발은 강력하지만, 로우코드 접근 방식에 비해 측정 가능한 대기 시간(latency)을 추가합니다. 모든 코드는 실행 전 해석 및 컴파일 과정이 필요하기 때문입니다."],
    122: ["ServiceNow는 로우코드 툴을 적극적으로 포함하고 있지만, 프로코드(Pro-code) 개발자들을 위한 강력한 API와 프레임워크도 지속적으로 확장하고 있습니다."],
    123: ["이 섹션에서는 Flow Designer의 잘 알려지지 않은 모범 사례들을 다룹니다. 성능뿐만 아니라 유지보수성을 높이는 핵심 전략들을 확인해 보십시오."],
    124: ["Flow의 이름 지정은 매우 중요합니다. 무엇을 하는 Flow인지 이름만 봐도 알 수 있어야 하며, 상위 Flow의 변수에 접근할 때 명확한 경로를 유지해야 합니다."],
    126: ["시스템 속성(System Properties)을 활용하면 코드 수정 없이도 애플리케이션의 동작을 제어할 수 있습니다. 하드코딩된 값 대신 `gs.getProperty()`를 사용하십시오."],
    130: ["기본값(Default value)은 사용자가 값을 입력하지 않았을 때 시스템이 취해야 할 안전장치입니다. 하지만 기본값 설정이 비즈니스 로직과 충돌하지 않는지 설계 단계에서 검토해야 합니다."],
    136: ["모듈형 애플리케이션 설계는 확장성을 위한 초석입니다. 하나의 거대한 스크립트에 모든 것을 담지 말고, 기능별로 Script Include를 분리하여 재사용성을 높이십시오."],
    141: ["`eval()` 함수의 사용은 극도로 지양해야 합니다. 이는 보안 취약성을 유발할 뿐만 아니라 성능 저하의 주요 원인이 됩니다. 동적 스크립트 실행이 필요하다면 더 안전한 대안을 검토하십시오."],
    143: ["인스턴스의 보안은 기능 구현만큼이나 중요합니다. ACL(Access Control List)을 설계할 때는 '최소 권한 원칙'을 따라야 하며, 읽기 권한뿐만 아니라 쓰기/삭제 권한도 엄격히 제한해야 합니다."],
    150: ["보안을 설계할 때는 항상 '만약에'를 가정해야 합니다. 권한이 없는 사용자가 URL 조작 등으로 데이터에 접근할 수 있는지, 서버 측 검증이 누락되지는 않았는지 끊임없이 자문해 보십시오."]
}

if __name__ == "__main__":
    apply_translations('ServiceNow_Handbook_Bilingual.html', BATCH5_TRANSLATIONS)
