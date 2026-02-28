
import os
import re
import base64
import json
from pathlib import Path
from bs4 import BeautifulSoup
from textwrap import dedent

# ─── Configuration ──────────────────────────────────────────
INPUT_HTML = Path("ServiceNow_Handbook_Bilingual.html")
IMAGE_DIR = Path("pages_compressed") # 초경량 이미지 사용
OUTPUT_HTML = Path("ServiceNow_Handbook_Premium_Ebook.html")
BLOCK_CONFIG = {
    "preserve_whitespace": True  # 코드 블록 인덴트 유지를 위해 추가
}


def get_base64_image(image_file):
    if not image_file.exists():
        return ""
    with open(image_file, "rb") as f:
        return f"data:image/jpeg;base64,{base64.b64encode(f.read()).decode('utf-8')}"

def clean_text_aggressive(text):
    """E-Book 가독성을 위해 노이즈를 강력하게 제거."""
    # OCR 노이즈 패턴 (줄 단위로 제거)
    line_patterns = [
        r"\d+\s*minute[s]?\s*left\s*in\s*chapter",
        r"\d+\s*hrs?\s*\d*\s*mins?\s*left\s*in\s*book",
        r"Location\s*\d+\s*of\s*\d+",
        r"Page\s*\d+\s*of\s*\d+",
        r"^\s*\d+\s*%\s*$",
        r"^\s*I\s*book\s*$",
        r"^\s*1\s*hrs?\s*$",
        r"^\s*1\s*hr5\s*$",
        # 줄 끝 OCR 쓰레기 패턴들
        r"\s*[Ff]\d*\s*%\s*$",
        r"\s*F\d+\s*[%]?\s*$",
        r"\s*P\d+\s*\d*\s*%?\s*$",
        r"\s*Fege\s*\d*\s*$",
        r"\s*Feg[e#]?\s*\d+.*$",
        r"\s*Fee\d*\s*%?\s*$",
        r"\s*Fg#?\s*\d+.*$",
        r"\s*Fxg\d*.*$",
        r"\s*[Ll]acato?r?\s*\d+.*$",
        r"\s*[Mm]rt\s*\d+.*(?:tool|soo[l)]?)\s*$",
        r"\s*[Hh]rt\s*\d+.*(?:tool|soo[l)]?)\s*$",
        r"\s*\d+\s*h(?:rs?|es)\s*\d*\s*(?:nves|eves|ovins?|ovns|aves|vns|ins|minde?)\s*(?:let|lef|teft|tet|lt).*$",
        r"\s*rt\s*\d+\s*(?:is|ies|es|eves|evies|nves|nies)\s*(?:et|e|ef|eft|left)\s*.*(?:tool|soo[l)]?|tol|too)\s*$",
        r"\s*remhe\s*tef.*$",
        r"\s*mhe\s*(?:teft|wft|wt).*$",
        r"\s*rent?\s*he(?:ft)?.*$",
        r"\s*tht\s*h[eo]f.*$",
        r"\s*[Mm]ownt\s*astn.*$",
        r"\s*remle\s*tef.*$",
        r"\s*mant\s*et\s*sn.*$",
        r"\s*me\s*\d+\s*$",
        r"\s*[Ll]acaor\d+.*$",
        r"\s*rem,?he\s*teft.*$",
        r"\s*t\s+es\s+t\s+soo\s*$",
        r"\s*ㅋ\s*ㅋ\s*ㅋ\s*$",
        r"\s*나\s*wf\s*ces\s*$",
        r"\s*에프씨\s*$",
        r"\s*오\s*$",
        r"\s*나\s*4\s*$",
        r"\s*E\s*$",
        r"\s*o\s*$",
        r"\s*C\s*$",
        r"\s*H\s*$",
        r"\s*1\s*$",
    ]
    
    # 줄별로 처리하되 문단 구조 보존
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        cleaned = line
        for p in line_patterns:
            cleaned = re.sub(p, "", cleaned, flags=re.IGNORECASE | re.MULTILINE)
        # 줄 내 연속 공백 정리 (줄바꿈은 유지)
        cleaned = re.sub(r"  +", " ", cleaned).strip()
        if cleaned:  # 비어있지 않은 줄만 유지
            cleaned_lines.append(cleaned)
    
    return '\n'.join(cleaned_lines)

# 고품질 수동 교정 데이터 (1-60p 주요 오역 및 노이즈 제거)
MANUAL_CORRECTIONS = {
    1: {
        "en": "SERVICENOW DEVELOPMENT HANDBOOK\nA Compendium of Guidelines and Best Practices for ServiceNow Developers\nFourth Edition\nTIM WOODRUFF",
        "ko": "ServiceNow 개발 핸드북: ServiceNow 개발자를 위한 가이드라인 및 모범 사례 요약본. 제4판. Tim Woodruff 저."
    },
    2: {
        "ko": "ServiceNow 개발자를 위한 전문가 팁과 모범 사례 및 지침서. 제4판. Tim Woodruff 작성. (도움 주신 분들 포함)"
    },
    3: {
        "ko": "Shayla, 나의 영원한 모든 것. 만 명이 넘는 회원으로 성장하면서도 여전히 오랜 친구들의 모임처럼 느껴지는 ServiceNow Discord 커뮤니티에게 이 책을 바칩니다. 함께합시다! https://discord.snc.guru\n\n이 책을 읽어주시고 제 작업을 지원해 주시는 여러분께 감사드립니다. 이 멋진 커뮤니티의 일원이 되어주셔서 고맙습니다. 나의 가족 Ciel, Casey, Bill에게도 사랑을 전합니다. 그들이 아무리 엄청난 괴짜들이라도 가족이란 건 어쨌든 함께 엮여 있는 존재라는 걸 보여주었습니다. (Roger만 빼고. 아빠, 당신은 좀 그래요.)"
    },
    4: {
        "ko": "이 페이지는 의도적으로 비워 두었습니다. (이 문구와 이 문구를 설명하는 문구만 제외하고 말이죠.)"
    },
    5: {
        "ko": "이 종이책을 구매하셨다면 발행 이후의 주요 업데이트 내용을 디지털 버전으로 받아보실 수 있습니다. LinkedIn(https://li.snc.guru)을 통해 연락해 주세요. 책에 포함된 짧은 링크(sncguru 하위 도메인)는 전체 책을 재발행하지 않고도 최신 정보로 리다이렉트하기 위한 것입니다. 만약 링크가 작동하지 않는다면 LinkedIn으로 알려주세요. 정기적인 업데이트는 http://update.sncguru.com 에서 확인 가능합니다."
    },
    6: {
        "ko": "목차: 비동기 표시(Async Display), AJAX, 비즈니스 규칙(Business Rules), DOM 조작, 코딩 지침, 스타일 및 표준, 디버깅 가이드, 순수 함수(Pure Functions), DRY 코드 작성법 등."
    },
    7: {
        "ko": "목차(계속): 데이터베이스 작업, 보안, 이벤트 중심 재귀, Flow Designer, 플레이북(Playbooks), 시스템 속성(System Properties), 사용자 기본 설정 등."
    },
    8: {
        "ko": "목차(계속): 기본 함수 매개변수, 로컬 스코프 변수 추적, ACL 보안, 복제 케이던스(Clone Cadences), 서비스 포털(Service Portal), 위젯 개발, 업데이트 세트(Update Sets) 관리 등."
    },
    10: {
        "ko": "서문: 이 책은 단순한 '모범 사례'의 나열이 아니라, 왜 그러한 표준이 필요한지에 대해 설명하고 가르치는 '개발자 가이드'입니다. ServiceNow 플랫폼과 JavaScript에 대한 기본 지식이 있는 독자를 대상으로 하며, 여러분의 작업물이 깨끗하고 효과적이며 안전하게 유지되도록 돕는 로드맵이 될 것입니다."
    },
    11: {
        "ko": "모범 사례(Best Practice)에서 벗어나야 할 때가 있습니다. 하지만 그럴 때는 반드시 명확한 이유가 있어야 하며, 그 이유를 문서로 남겨야 합니다. 나중에 코드를 보는 다른 개발자가 추측할 필요가 없도록 말이죠.\n\n예를 들어, DOM(Document Object Model) 조작은 플랫폼에서 지원하지 않으며 업그레이드 시 충돌 위험이 커서 피해야 하는 대표적인 모범 사례입니다. 과거 Service Portal 출시 당시 수많은 DOM 접근 코드가 작동하지 않게 되었던 것이 좋은 예입니다."
    },
    13: {
        "ko": "순수 함수(Pure Functions): 외부 상태에 의존하지 않고 전달받은 인수(arguments)만으로 결과를 도출하는 함수입니다. 순수 함수는 사이드 이펙트(부작용)가 없어 코드를 이해하고 테스트하기 훨씬 쉬우며, 모듈화에 유리합니다. 모든 상황에서 순수 함수를 쓸 수는 없겠지만, 가능한 한 이를 지향하는 것이 좋습니다."
    },
    14: {
        "ko": "DRY (Don't Repeat Yourself) 원칙: 동일한 코드 블록을 반복해서 작성하는 것을 피해야 합니다. 거의 모든 상황에서 하나 이상의 코드 덩어리가 중복된다면, 이를 구조화하거나 인수를 받는 함수로 래핑하여 재사용하는 것이 훨씬 효율적입니다."
    },
    15: {
        "ko": "비효율적인 'WET(Write Everything Twice)' 코드 예시: 이미지 103번처럼 각 테이블별로 거의 동일한 GlideRecord 쿼리를 반복하는 코드는 작성하기 번거로울 뿐만 아니라 가독성이 떨어지고 오류가 발생하기 쉽습니다. 로직을 수정해야 할 때 여러 곳을 동시에 고쳐야 하므로 버그의 온상이 됩니다."
    },
    16: {
        "ko": "리팩토링 예시: 반복되는 코드 대신 테이블 이름, 쿼리문, 상태값 등을 객체 배열로 구성하고 이를 루프(Loop)로 처리하면 코드가 훨씬 간결해집니다. 이처럼 데이터를 구조화하면 유지보수가 매우 쉬워집니다."
    },
    17: {
        "ko": "변수 명명 규칙: `gr`로 시작하는 이름(예: `grIncident`)을 사용하면 나중에 수백 줄의 코드를 보더라도 해당 변수가 GlideRecord 개체임을 즉시 알 수 있습니다. 또한 JavaScript 생성자(Constructor)를 사용하여 개체를 생성할 때 기본값을 설정하거나 유효성 검사 로직을 포함할 수 있어 안전한 프로그래밍이 가능합니다."
    },
    20: {
        "en": "Can just pass them into a helper function as arguments! This also allows us to do some neat stuff like having optional arguments, making the encoded query modified optional allows the calling code to not specify a query at all, thus updating all records in the table. Fig 111: Highly optimized DRY and functional-ish code!",
        "ko": "도우미 함수에 단순히 인수로 전달할 수 있습니다! 또한 선택적 인수를 활용하는 등의 깔끔한 작업이 가능해집니다. 인코딩된 쿼리를 선택 사항으로 만들면, 호출 코드에서 별도의 쿼리를 지정하지 않고도 테이블의 모든 레코드를 업데이트할 수 있습니다. 그림 111: 고도로 최적화된 DRY 및 '기능적' 코드 예시!"
    },
    21: {
        "en": "PASS-BY-REFERENCE (PBR): In JavaScript, dealing with functions and objects involves an oddity called pass-by-reference. This is important to understand when mutations happen within functions. Knowledge of PBR, scope, closure, and the 'this' object separates experienced developers from beginners.",
        "ko": "참조에 의한 전달(PASS-BY-REFERENCE, PBR): JavaScript에서 함수와 객체를 다룰 때 가장 중요한 개념 중 하나입니다. 함수 내부에서 객체가 수정될 때 원본에 어떤 영향을 주는지 이해해야 합니다. PBR, 스코프, 클로저, 'this' 객체에 대한 이해는 초급자와 상급자를 나누는 기준이 됩니다."
    },
    24: {
        "ko": "참조 타입과 값 타입: JavaScript에서 개체(Object)를 인수로 전달할 때 참조에 의한 호출(Pass-by-reference) 방식이 작동한다는 점을 명심하십시오. 함수 내부에서 개체의 속성을 변경하면 원본 개체에도 영향을 미칩니다."
    },
    26: {
        "ko": "코드 문서화의 중요성: 주석은 단순히 코드를 설명하는 것이 아니라, 왜(Why) 이렇게 작성했는지를 기록하는 것입니다. 특히 복잡한 비즈니스 로직을 다룰 때는 주석이 미래의 당신과 동료 개발자의 시간을 수십 시간 아껴줄 수 있습니다."
    },
    30: {
        "ko": "비즈니스 규칙(Business Rule)의 순서: Before, After, Async 비즈니스 규칙이 실행되는 순서를 이해하는 것이 성능 최적화의 핵심입니다. 특히 After 규칙에서 `current.update()`를 호출하면 무한 루프에 빠질 위험이 있으므로 주의해야 합니다."
    },
    32: {
        "ko": "Async 비즈니스 규칙: 사용자 대기 시간을 줄이기 위해 즉각적일 필요가 없는 작업은 비동기(Async) 규칙으로 처리하십시오. 이는 시스템 응답성을 높이는 가장 효과적인 방법 중 하나입니다."
    },
    33: {
        "ko": "날짜 및 시간 처리: 클라이언트와 서버 사이의 시간대(Time zone) 차이를 항상 고려해야 합니다. 가능하면 모든 시간 계산은 UTC 기준으로 서버에서 처리하는 것이 좋습니다."
    },
    49: {
        "en": "Because it's using a `while` loop on line 12, this code would actually loop through all of the user's open tickets and return the ticket number of the last ticket the query finds. Even if we switch this `while` to an `if` block though, we would still only return the first such ticket in the database.\n\nIn addition to being extremely inefficient, this code will almost certainly result in unexpected and unpredictable results. This specific use-case is probably something that needs to be re-thought in general, but we can make some drastic improvements with just a few changes:\n\nFirst, significantly refining the query to ensure that if we only expect one record, we actually do only get one record. Adding `.setLimit(1)` and changing the `while` to an `if` block is also a good idea, to ensure that we do indeed only get one record even if more records matching our query exist in the database. This would also drastically improve our performance since the query runner would stop seeking through the database once the limit is reached.",
        "ko": "`12`번째 줄에서 `while` 루프를 사용하기 때문에, 이 코드는 실제로 해당 사용자의 모든 활성 작업(open tickets)을 순회하며 쿼리가 마지막으로 찾은 티켓의 번호를 반환할 것입니다. 이 `while`문을 `if` 블록으로 바꾼다고 해도 여전히 데이터베이스에서 찾은 '첫 번째' 티켓 번호만 반환하게 될 것입니다.\n\n이는 극도로 비효율적일 뿐만 아니라 예상치 못한 결과를 초래할 것이 거의 확실합니다. 이 특정 사용 사례(Use-case)는 전반적으로 처음부터 다시 생각해 보아야 할 문제겠지만, 몇 가지 변경만으로도 대폭적인 개선을 이룰 수 있습니다.\n\n먼저, 단 하나의 레코드만 필요하다면 실제로 단일 레코드만 가져오도록 쿼리를 정교하게 다듬어야 합니다. `.setLimit(1)`을 추가하고 `while`을 `if` 블록으로 변경하는 것도 아주 좋은 방법입니다. 쿼리와 일치하는 여러 레코드가 데이터베이스에 존재하더라도 오직 하나의 레코드만 반환하도록 보장해 주기 때문입니다. 또한 데이터베이스 엔진이 조건에 맞는 레코드를 찾는 즉시 검색을 중단하므로 성능 역시 비약적으로 향상됩니다.",
        "codes": [
            "function getOpenTicketNumberByUser(userSysID) {\n    if (!userSysID) {\n        throw new Error('Invalid user sys_id passed in');\n    }\n\n    var ticketNumber;\n    var grTask = new GlideRecord('task');\n    grTask.addActiveQuery();\n    grTask.addQuery('opened_by', userSysID);\n    grTask.query();\n\n    while (grTask.next()) {\n        ticketNumber = grTask.getValue('number');\n    }\n\n    return ticketNumber;\n}"
        ]
    },
    51: {
        "ko": "가독성을 위한 포맷팅: `if`, `while`, `for`와 같은 제어문 블록은 항상 중괄호`{}`를 사용하십시오. 한 줄짜리 리턴문이라도 중괄호를 쓰는 것이 나중의 실수를 방지하는 모범 사례입니다."
    },
    21: {
        "en": "PASS-BY-REFERENCE (PBR): In JavaScript, dealing with functions and objects involves an oddity called pass-by-reference. This is important to understand when mutations happen within functions. Knowledge of PBR, scope, closure, and the 'this' object separates experienced developers from beginners.",
        "ko": "참조에 의한 전달(PASS-BY-REFERENCE, PBR): JavaScript에서 함수와 객체를 다룰 때 가장 중요한 개념 중 하나입니다. 함수 내부에서 객체가 수정될 때 원본에 어떤 영향을 주는지 이해해야 합니다. PBR, 스코프, 클로저, 'this' 객체에 대한 이해는 초급자와 상급자를 나누는 기준이 됩니다."
    },
    22: {
        "en": "Mutating an Object: When you pass an object into a function, both the local variable and the parent scope variable literally refer to the same object in memory. Modifications to one affect the other.",
        "ko": "객체 수정하기: 객체를 함수로 전달하면, 함수 내부의 변수와 외부의 변수는 문자 그대로 메모리 상의 동일한 객체를 가리킵니다. 따라서 한쪽에서 수정하면 양쪽 모두에 반영됩니다."
    },
    24: {
        "en": "GETTING AND SETTING FIELD VALUES: Use getter (.getValue()) and setter (.setValue()) when working with GlideRecord objects. Avoid direct notation like grInc.field_name as it accesses the GlideElement object directly, which can lead to unexpected PBR behaviors.",
        "ko": "필드 값 읽기 및 설정: GlideRecord 사용 시 반드시 `.getValue()`와 `.setValue()`를 사용하십시오. `grInc.field_name`처럼 직접 접근하면 GlideElement 객체를 참조하게 되어 예상치 못한 부작용(PBR)이 발생할 수 있습니다."
    },
    25: {
        "en": "Retrieving Primitive Values: The most efficient and best-practice way to retrieve a primitive value from a field is nearly always to use .getValue(). It avoids the 'serialized character array' issue common in Mozilla Rhino.",
        "ko": "원시 값 가져오기: 필드에서 순수한 데이터(원시 값)를 가져오는 가장 효율적인 방법은 항상 `.getValue()`를 사용하는 것입니다. 이는 ServiceNow 서버 엔진에서 발생할 수 있는 데이터 타입 충돌 문제를 방지해 줍니다."
    },
    26: {
        "en": "CONSISTENCY: Standardize things like string delimiters. Author prefers single-quotes (') because double-quotes (\") require the SHIFT key. The most important thing is that the entire team follows the same standard.",
        "ko": "일관성(CONSISTENCY): 문자열 구분 기호(' vs \")와 같은 사소한 부분부터 표준화하십시오. 중요한 것은 어떤 방식을 선택하느냐가 아니라, 팀원 전체가 하나의 표준을 일관되게 준수하는 것입니다."
    },
    28: {
        "en": "FIELD SECURITY VS FIELD OBSCURITY: Client-side measures (UI Policies, Client Scripts) can be easily bypassed. They are for convenience, not security. Real security must be enforced on the server-side via ACLs or Business Rules.",
        "ko": "필드 보안 vs 필드 숨김: UI 정책이나 클라이언트 스크립트는 보안 기능이 아니라 편의 기능입니다. 브라우저 수준의 제어는 숙련된 사용자에 의해 쉽게 무력화될 수 있으므로, 진짜 보안은 ACL이나 비즈니스 룰과 같은 서버 측에서 처리해야 합니다."
    },
    30: {
        "en": "BUSINESS RULE EXECUTION: Understanding when to use current.update() depends on knowing the execution phases: Before, After, Async, and Display. Calling current.update() in a 'before' rule is redundant and dangerous.",
        "ko": "비즈니스 룰 실행 시점: `current.update()`를 언제 써야 할지는 실행 단계(Before, After, Async, Display)를 이해하면 명확해집니다. 특히 'Before' 단계에서 이를 호출하는 것은 중복 작업이며 위험할 수 있습니다."
    },
    31: {
        "en": "After Business Rules: These run after the database operation is committed. Never use current.update() here as it can trigger an infinite loop. Use 'After' rules to update RELATED records on other tables.",
        "ko": "After 비즈니스 룰: 데이터베이스 작업이 완료된 후 실행됩니다. 여기서 `current.update()`를 호출하면 무한 루프에 빠질 수 있으므로 절대 금지입니다. 주로 다른 테이블의 연관 레코드를 업데이트할 때 사용합니다."
    },
    32: {
        "en": "ASYNC Business Rules: These run in the background whenever the system scheduler has capacity. They are perfect for long-running tasks that don't need to return control to the user immediately, maximizing system performance.",
        "ko": "ASYNC 비즈니스 룰: 시스템 스케줄러가 여유 있을 때 백그라운드에서 실행됩니다. 사용자 대기 시간을 줄이고 시스템 성능을 최적화하기 위해, 즉각적인 응답이 필요 없는 긴 작업에 적합합니다."
    },
    33: {
        "en": "DISPLAY Business Rules: These run when a record is loaded from the database into a form. They are used to populate the g_scratchpad object, allowing you to pass server-side data to client-side scripts efficiently.",
        "ko": "DISPLAY 비즈니스 룰: 레코드가 로드될 때 실행됩니다. `g_scratchpad` 객체에 데이터를 담아 서버의 정보를 클라이언트 측 스크립트로 효율적으로 전달하는 용도로 사용됩니다."
    },
    41: {
        "en": "SERVER-SIDE DEBUGGING: Use the Script Debugger to step through your code line-by-line. This allows you to inspect variables in the local scope and understand exactly how logic branches are evaluated.",
        "ko": "서버 측 디버깅: 스크립트 디버거를 사용하면 코드를 한 줄씩 실행하며 디버깅할 수 있습니다. 로컬 스코프의 변수 값을 직접 검사하고 로직 분기가 어떻게 실행되는지 정확히 파악하는 가장 좋은 방법입니다."
    },
    42: {
        "ko": "로깅(Logging) 전략: `gs.log()` 대신 용도에 따라 `gs.error()`, `gs.warn()`, `gs.info()`를 구분하여 사용하십시오. 로그 메시지에는 항상 어떤 스크립트의 어느 부분에서 생성된 로그인지 식별할 수 있는 정보를 포함해야 합니다."
    },
    50: {
        "en": "LIMITING QUERY RESULTS: Always use .setLimit(1) when you expect only a single record back from a GlideRecord query. This ensures the database engine stops searching as soon as it finds a match, providing a massive performance boost.",
        "ko": "쿼리 결과 제한: GlideRecord 쿼리에서 단일 레코드만 필요하다면 반드시 `.setLimit(1)`을 사용하십시오. 데이터베이스 엔진이 매칭되는 항목을 찾는 즉시 검색을 멈추게 되어, 비약적인 성능 향상을 얻을 수 있습니다."
    },
    51: {
        "ko": "가독성을 위한 포맷팅: `if`, `while`, `for`와 같은 제어문 블록은 항상 중괄호`{}`를 사용하십시오. 한 줄짜리 리턴문이라도 중괄호를 쓰는 것이 나중의 실수를 방지하는 모범 사례입니다."
    },
    62: {
        "en": "CUSTOM FIELDS: Before adding a new field, ask if it's truly necessary. Use derived or calculated fields where possible. Calculated field scripts run server-side and can impact performance if overused.",
        "ko": "커스텀 필드: 새 필드를 추가하기 전에 정말 필요한지 확인하십시오. 가능하다면 파생 필드나 계산된 필드를 활용하되, 계산된 필드는 서버 측에서 실행되어 성능에 영향을 줄 수 있음을 유의하십시오."
    },
    80: {
        "en": "LOGGING BEST PRACTICES: Log with a purpose. Avoid excessive logging in production. Always remove development-time debug logs before moving your code to maintain a clean environment.",
        "ko": "로그 기록 모범 사례: 목적을 가지고 로그를 기록하십시오. 운영 환경에서 과도한 로그는 성능을 저하시킬 수 있습니다. 배포 전에는 개발용 디버그 로그를 반드시 제거하십시오."
    },
    83: {
        "en": "CODE DOCUMENTATION: Documenting your code is critical. Instead of writing long, repetitive logic, abstract it into functions. This page demonstrates the difference between 'Wet' (repetitive) and 'DRY' (optimized) code.",
        "ko": "코드 문서화: 코드를 문서화하는 것은 매우 중요합니다. 길고 반복적인 로직을 작성하는 대신 함수로 추상화하십시오. 이 페이지는 반복적인 코드(Wet)와 최적화된 코드(DRY)의 차이를 보여줍니다.",
        "codes": [
            "var milSeconds = 3200000;\nvar weeks = getWeeksFromMS(milSeconds);\n\nfunction getWeeksFromMS(milSeconds) {\n    var seconds = milSeconds * 0.001;\n    var minutes = seconds / 60;\n    var hours = minutes / 60;\n    var days = hours / 24;\n    var weeks = days / 7;\n    return weeks;\n}",
            "var milSeconds = 3200000; //3.2 million milliseconds\nvar weeks = getWeeksFromMS(milSeconds);\n\nfunction getWeeksFromMS(milSeconds) {\n    /* Multiply by 0.001 to get seconds, divide by 60 to\n       get minutes, 60 again to get hours, then by 24 to\n       get days, and by 7 to get weeks, which we return. */\n    return milSeconds * 0.001 / 60 / 60 / 24 / 7;\n}"
        ]
    },
    102: {
        "en": "SAVING RESOURCES: Use .initialize() instead of .newRecord() when you don't immediately need default values or sys_id. .initialize() is much faster because it avoids an unnecessary round-trip to the database.",
        "ko": "리소스 절약: 기본값이나 sys_id가 즉시 필요하지 않다면 `.newRecord()` 대신 `.initialize()`를 사용하십시오. 데이터베이스와의 불필요한 통신을 피하기 때문에 성능 면에서 훨씬 유리합니다."
    },
    114: {
        "en": "FLOW DESIGNER BASICS: Use Flow Designer for simple, low-code business logic. It's great for automating standard processes, though you should still follow structured design principles to avoid 'spaghetti flows'.",
        "ko": "Flow Designer 기초: 간단한 로우-코드 비지니스 로직에는 Flow Designer를 활용하십시오. 표준 프로세스를 자동화할 수 있지만, '스파게티 플로우'가 되지 않도록 구조적인 설계 원칙을 준수해야 합니다."
    },
    139: {
        "en": "they be passed in to the function as arguments? Well, as we'll see shortly, these variables are defined by the script that invokes the code in this record. There is an API for executing scripts inside of records like this (GlideScopedEvaluator), and it handles that part for us.\n\nBefore we get to talking about how to invoke our script though, let's write our script field's default value. Using the pattern that Business Rules use as an example, we're going to set our script's default value to something like this:\n\nIn this script, we're passing in four variables: current (the current record for which we're doing the transformation), sourceFieldName (the name of the source field, based on the current transform record), sourceFieldValue (the original value of the source field in ServiceNow), and targetFieldName (the target field name, based on the current transform record). In the transform script, we can use any (or none) of those variables to do our transformation, and then return the final target field value.\n\nNow that we've got a decent default value for our script field, we'll go to that field's dictionary record, and set the Default value field to our script.",
        "ko": "이러한 변수들이 함수에 인수로 어떻게 전달될까요? 곧 알게 되겠지만, 이 변수들은 이 레코드 내부의 코드를 호출하는 스크립트에 의해 정의됩니다. GlideScopedEvaluator와 같이 이와 같은 레코드 내에서 스크립트를 실행하기 위한 API가 존재하며, 이 API가 우리를 위해 해당 부분을 처리해 줍니다.\n\n스크립트를 호출하는 방법에 대해 이야기하기 전에, 스크립트 필드의 기본값을 먼저 작성해 보겠습니다. 비즈니스 규칙(Business Rules)이 사용하는 패턴을 예시로 삼아, 우리 스크립트의 기본값을 다음과 같이 설정해 보겠습니다:\n\n이 스크립트에서는 네 가지 변수를 전달합니다: current(변환을 수행 중인 현재 레코드), sourceFieldName(현재 변환 레코드에 기반한 소스 필드의 이름), sourceFieldValue(ServiceNow에 있는 소스 필드의 원래 값), 그리고 targetFieldName(현재 변환 레코드에 기반한 대상 필드 이름)입니다. 변환 스크립트 내에서는 이러한 변수들 중 일부를 사용하거나 전혀 사용하지 않은 채로 변환을 수행한 다음, 최종 대상 필드 값을 반환할 수 있습니다.\n\n이제 스크립트 필드에 대한 적절한 기본값을 얻었으므로, 해당 필드의 딕셔너리 레코드로 이동하여 Default value 필드를 우리 스크립트로 설정하겠습니다.",
        "codes": [
            "(function doTransform(current,\n                      sourceFieldName,\n                      sourceFieldValue,\n                      targetFieldName) {\n\n    var targetFieldValue = sourceFieldValue.toString();\n    // Add your code here, and return the target field value.\n\n    return targetFieldValue;\n\n})(current, sourceFieldName, sourceFieldValue, targetFieldName);"
        ]
    },
    122: {
        "en": "FLOW LATENCY: Every action in a Flow adds significant overhead compared to native JavaScript. For high-volume transactions, prioritize code-based solutions (Business Rules) to maintain peak performance.",
        "ko": "플로우 지연 시간: 플로우의 각 액션은 상당한 오버헤드를 발생시킵니다. 대량 트랜잭션에서는 성능 유지를 위해 플로우보다 코드 기반 솔루션(Business Rules)을 우선적으로 고려하십시오."
    },
    143: {
        "en": "SECURITY & ACLS: Security is a shared responsibility. Implement proper ACLs to protect your data. Avoid 'open security' and prioritize the principle of least privilege in every application.",
        "ko": "보안 및 ACL: 보안은 공동의 책임입니다. 데이터 보호를 위한 적절한 ACL 구현은 여러분의 몫입니다. '개방형 보안'을 지양하고 모든 애플리케이션에서 최소 권한의 원칙을 우선시하십시오."
    },
    157: {
        "en": "UPDATE SETS: Update Sets track customizations as you build them. Use meaningful names and descriptions to make it easier for others to review and merge your changes efficiently.",
        "ko": "업데이트 세트: 업데이트 세트는 구축 과정의 변경 사항을 추적합니다. 의미 있는 이름과 설명을 사용하여 다른 사람들이 변경 사항을 검토하고 병합하기 쉽게 만드십시오."
    },
    162: {
        "en": "PRIVATE SYSTEM PROPERTIES: Some properties, like API keys, should not be included in Update Sets. Use the 'Private' flag to ensure sensitive information doesn't leak between environments.",
        "ko": "비공개 시스템 속성: API 키와 같은 속성들은 업데이트 세트에 포함되어서는 안 됩니다. '비공개(Private)' 플래그를 사용하여 민감한 정보가 다른 환경으로 유출되지 않도록 하십시오."
    },
    165: {
        "en": "DEPLOYMENT CHECKLISTS: Never rely on memory for complex deployments. Maintain a standardized pre-deployment and post-deployment checklist. This should include manual steps that Update Sets can't handle.",
        "ko": "배포 체크리스트: 복합적인 배포를 진행할 때 육안이나 기억에 의존하지 마십시오. 표준화된 배포 전후 체크리스트를 관리해야 하며, 여기에는 업데이트 세트가 처리할 수 없는 수동 단계들이 포함되어야 합니다."
    },
    172: {
        "en": "APP STORE PLANNING: Before publishing, conduct thorough self-testing for security and performance. A high-quality app listing with clear documentation is key to gaining user trust.",
        "ko": "앱 스토어 계획: 게시 전 보안 및 성능에 대한 철저한 자체 테스트를 수행하십시오. 명확한 문서를 갖춘 고품질의 앱 등록 정보는 사용자 신뢰를 얻는 핵심 요소입니다."
    },
    182: {
        "en": "TECHNICAL DEBT: This is the compound interest accrued from shortcuts and legacy code. It must be tracked and planned for. Ignored debt makes the system riskier to upgrade and more expensive to maintain.",
        "ko": "기술 부채: 임시 처방과 낡은 코드가 쌓여 발생하는 '복리 이자'와 같습니다. 반드시 추적하고 상환 계획을 세워야 하며, 방치된 부채는 유지보수 비용과 업그레이드 위험을 높입니다."
    },
    185: {
        "en": "REDUCTION STRATEGIES: Use Snowball or Opportunistic cleanup. The 'Scout Rule' is key: always leave the codebase better than you found it. This helps pay down technical debt during regular development.",
        "ko": "부채 감소 전략: 스노우볼 방식이나 기회주의적 정리를 활용하십시오. '스카우트 규칙'이 핵심입니다. 개발 과정에서 항상 처음보다 더 깨끗한 코드를 남김으로써 기술 부채를 조금씩 줄여나갈 수 있습니다."
    },
    186: {
        "en": "IDENTIFYING RISKY CODE: Hidden scripts in ACLs are a major risk. Un-checking 'Advanced' hides but doesn't stop the script. Use queries like 'advanced=false^scriptISNOTEMPTY' to find and clean these up.",
        "ko": "위험한 코드 식별: ACL의 숨겨진 스크립트는 큰 위험 요소입니다. 'Advanced' 체크를 해제해도 스크립트는 실행되므로, `advanced=false^scriptISNOTEMPTY`와 같은 쿼리로 찾아 정리하십시오."
    },
    187: {
        "en": "BE THE GUIDE: When clients request risky things, seek to understand 'why'. Your role is to guide them toward a solution that meets their needs while maintaining platform health.",
        "ko": "길잡이가 되십시오: 클라이언트가 위험한 요청을 할 때 그 이유(Why)를 파악하십시오. 플랫폼의 건전성을 유지하면서 그들의 요구를 충족할 수 있는 해법으로 안내하는 것이 여러분의 역할입니다."
    },
    200: {
        "en": "CONCLUSION: ServiceNow development is about building sustainable and robust systems. Follow these guidelines, keep learning, and be the expert guide your organization needs. Happy coding!",
        "ko": "결론: ServiceNow 개발은 지속 가능하고 견고한 시스템을 구축하는 과정입니다. 이 가이드라인을 따르고 끊임없이 배워 조직에 필요한 전문가가 되십시오. 즐거운 코딩 되세요!"
    },
    204: {
        "en": "RESOURCES: Check out the ServiceNow Store for certified apps and tools like the Certification Self-Test Tool to ensure your applications meet best practice standards.",
        "ko": "추가 리소스: ServiceNow 스토어에서 인증된 앱들을 확인하고, 인증 자체 테스트 도구와 같은 도구들을 사용하여 여러분의 애플리케이션이 모범 사례를 준수하는지 점검해 보십시오."
    }
}

# 장(Chapter) 정보 정의
CHAPTERS = {
    1: "INTRO & BACKGROUND",
    13: "CODE & CODING GUIDELINES",
    30: "BUSINESS RULES & ASYNC",
    38: "DEBUGGING STRATEGIES",
    48: "REPORTS & DASHBOARDS",
    56: "NAMING & PERFORMANCE",
    107: "FLOW DESIGNER & PLAYBOOKS",
    121: "ADVANCED BEST PRACTICES",
    143: "SECURITY & ACLS",
    157: "UPDATE SETS & CLONING",
    182: "TECHNICAL DEBT",
    195: "APPENDIX & CONCLUSION"
}

def main():
    if not INPUT_HTML.exists():
        print("Error: Input HTML not found.")
        return

    try:
        with open("AGENT_100_CORRECTIONS.json", "r", encoding="utf-8") as f:
            auto_corrections_raw = json.load(f)
            count = 0
            for k, v in auto_corrections_raw.items():
                page_id = int(k)
                if page_id not in MANUAL_CORRECTIONS:
                    MANUAL_CORRECTIONS[page_id] = v
                    count += 1
                else:
                    if "en" not in MANUAL_CORRECTIONS[page_id]:
                        MANUAL_CORRECTIONS[page_id]["en"] = v.get("en", "")
                    if "codes" not in MANUAL_CORRECTIONS[page_id]:
                        MANUAL_CORRECTIONS[page_id]["codes"] = v.get("codes", [])
        print(f"Loaded {count} automated corrections from pipeline (plus partial merges).")
    except Exception as e:
        print(f"No auto corrections loaded: {e}")

    print("Building Premium E-Book...")
    with open(INPUT_HTML, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    pages_data = soup.find_all("section", class_="page")
    total_pages = len(pages_data)
    
    html_sections = []

    for i, page_soup in enumerate(pages_data, 1):
        page_id = f"page-{i}"
        img_file = IMAGE_DIR / f"page_{i:03d}.jpg"
        img_b64 = get_base64_image(img_file)

        # 텍스트 추출 및 정제
        text_blocks = []
        
        # 만약 수동 교정이 있으면 해당 페이지의 모든 텍스트 블록을 교정된 내용으로 대체
        if i in MANUAL_CORRECTIONS:
            en_raw = MANUAL_CORRECTIONS[i].get("en", "")
            ko_raw = MANUAL_CORRECTIONS[i].get("ko", "")
            # 자동 교정 데이터(AGENT_100)도 OCR 노이즈 정제 적용
            en_clean = clean_text_aggressive(en_raw) if en_raw else ""
            ko_clean = clean_text_aggressive(ko_raw) if ko_raw else ""
            text_blocks.append({
                "en": en_clean,
                "ko": ko_clean
            })
        else:
            # 수동 교정이 없을 때만 원본 텍스트 추출
            bilinguals = page_soup.find_all("div", class_="bilingual")
            for bi in bilinguals:
                en_p = bi.find("div", class_="lang-en").p
                ko_p = bi.find("div", class_="lang-ko").p
                
                en_text = clean_text_aggressive(en_p.get_text()) if en_p else ""
                ko_text = clean_text_aggressive(ko_p.get_text()) if ko_p else ""
                
                if en_text or ko_text:
                    text_blocks.append({
                        "en": en_text,
                        "ko": ko_text
                    })

        code_blocks = []
        if i in MANUAL_CORRECTIONS and "codes" in MANUAL_CORRECTIONS[i]:
            code_blocks = MANUAL_CORRECTIONS[i]["codes"]
        else:
            codes = page_soup.find_all("div", class_="code-block")
            for code in codes:
                raw_code = code.find("code")
                if raw_code:
                    # 원본 공백 유지 시도
                    code_text = raw_code.get_text().strip()
                    code_blocks.append(code_text)

        code_html = []
        if code_blocks:
            c_safe = "\n\n".join(code_blocks).replace("<", "&lt;").replace(">", "&gt;")
            code_html.append(f'''
            <div class="code-box">
                <div class="code-label">📋 Source Code</div>
                <pre><code>{c_safe}</code></pre>
            </div>''')

        # 페이지 구성
        blocks_html = []
        for block in text_blocks:
            blocks_html.append(f'''
            <div class="text-block">
                <p class="en">{block['en']}</p>
                <p class="ko">{block['ko']}</p>
            </div>''')
        
        # 장(Chapter) 헤더 추가
        if i in CHAPTERS:
            html_sections.append(f'''
            <div class="chapter-header" id="ch-{i}">
                <span class="ch-label">CHAPTER</span>
                <h2 class="ch-title">{CHAPTERS[i]}</h2>
            </div>''')

        html_sections.append(f'''
        <article class="page-container" id="{page_id}">
            <header class="page-header">
                <span class="page-num">PAGE {i}</span>
                <button class="toggle-img" onclick="toggleImage('{page_id}')">🖼️ 원문 보기</button>
            </header>
            <div class="image-viewer" id="img-{page_id}" style="display:none;">
                <img src="{img_b64}" alt="Source Page {i}">
            </div>
            <div class="content-body">
                {"".join(blocks_html)}
                {"".join(code_html)}
            </div>
        </article>''')

    # Premium E-Book UI Template
    template = dedent(f'''
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ServiceNow Handbook Premium E-Book</title>
        <link href="https://fonts.googleapis.com/css2?family=Crimson+Pro:ital,wght@0,400;0,600;1,400&family=Noto+Sans+KR:wght@300;400;500;700&family=JetBrains+Mono&display=swap" rel="stylesheet">
        <style>
            :root {{
                --bg: #f8fafc; --text-en: #475569; --text-ko: #020617;
                --accent: #3b82f6; --border: #e2e8f0; --code-bg: #1e293b;
                --card-bg: #ffffff; --text-muted: #64748b;
            }}
            body.dark-mode {{
                --bg: #0f172a; --text-en: #94a3b8; --text-ko: #f1f5f9;
                --border: #334155; --card-bg: #1e293b; --text-muted: #94a3b8;
            }}
            body {{
                font-family: 'Noto Sans KR', sans-serif;
                background-color: var(--bg); color: var(--text-ko);
                margin: 0; padding: 0; line-height: 1.8;
                transition: background 0.3s, color 0.3s;
            }}
            .top-bar {{
                position: fixed; top: 0; width: 100%; z-index: 1000;
                background: rgba(255,255,255,0.8); backdrop-filter: blur(8px);
                border-bottom: 1px solid var(--border); padding: 0.8rem 1rem;
                display: flex; justify-content: space-between; align-items: center;
            }}
            .dark-mode .top-bar {{ background: rgba(15,23,42,0.8); }}
            
            .container {{ max-width: 800px; margin: 5rem auto; padding: 0 1.5rem; }}
            
            .chapter-header {{
                margin: 6rem 0 3rem; text-align: center; border-bottom: 2px solid var(--accent);
                padding-bottom: 1rem;
            }}
            .ch-label {{ font-size: 0.7rem; font-weight: 800; color: var(--accent); letter-spacing: 0.3em; }}
            .ch-title {{ font-size: 1.8rem; margin: 0.5rem 0; color: var(--text); }}

            .page-container {{
                background: var(--card-bg); border: 1px solid var(--border);
                border-radius: 12px; margin-bottom: 5rem; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
                overflow: hidden;
            }}
            .page-header {{
                background: var(--bg); padding: 0.8rem 1.5rem;
                display: flex; justify-content: space-between; align-items: center;
                border-bottom: 1px solid var(--border);
            }}
            .page-num {{ font-weight: 800; font-size: 0.8rem; color: var(--accent); letter-spacing: 0.1em; }}
            .toggle-img {{
                background: none; border: 1px solid var(--accent); color: var(--accent);
                padding: 0.2rem 0.6rem; border-radius: 4px; cursor: pointer; font-size: 0.75rem;
            }}
            .image-viewer {{ background: #000; padding: 1rem; text-align: center; }}
            .image-viewer img {{ max-width: 100%; border-radius: 4px; filter: contrast(1.1); }}
            
            .content-body {{ padding: 2.5rem; }}
            .text-block {{ margin-bottom: 2rem; border-bottom: 1px solid rgba(0,0,0,0.03); padding-bottom: 1rem; }}
            .en {{
                font-family: 'Crimson Pro', serif; font-size: 1.2rem; 
                color: var(--text-en); margin-bottom: 0.6rem; line-height: 1.6;
                white-space: pre-wrap; font-style: italic; opacity: 0.85;
                padding: 0.5rem 0.8rem; border-left: 3px solid var(--accent);
                background: rgba(59, 130, 246, 0.03); border-radius: 0 6px 6px 0;
            }}
            .ko {{
                font-size: 1.08rem; color: var(--text-ko); font-weight: 400;
                word-break: keep-all; text-align: justify;
                white-space: pre-wrap; line-height: 1.9;
                padding: 0.3rem 0;
            }}
            /* bilingual 모드에서 영문/한글 시각적 구분 강화 */
            [data-view="bilingual"] .en {{ opacity: 0.8; }}
            [data-view="bilingual"] .ko {{ font-weight: 400; }}
            [data-view="en-only"] .en {{ opacity: 1; font-style: normal; border-left: none; background: none; }}
            [data-view="ko-only"] .ko {{ font-size: 1.15rem; }}
            .code-box {{
                background: var(--code-bg); padding: 0.8rem 1.2rem 1.2rem; border-radius: 8px;
                overflow-x: auto; margin: 1.5rem 0; border: 1px solid var(--border);
            }}
            .code-label {{
                font-size: 0.7rem; color: #94a3b8; margin-bottom: 0.5rem;
                font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;
            }}
            .code-box pre {{ margin: 0; }}
            .code-box code {{
                font-family: 'JetBrains Mono', monospace; font-size: 0.9rem; color: #38bdf8;
                white-space: pre; display: block; line-height: 1.6;
            }}
            
            /* Controls */
            .controls button {{
                background: var(--accent); color: #fff; border: none;
                padding: 0.5rem 1rem; border-radius: 6px; cursor: pointer; font-size: 0.8rem;
            }}
            .view-mode-btns {{ display: flex; gap: 0.5rem; }}
            .view-mode-btns button {{ background: var(--border); color: var(--text); }}
            .view-mode-btns button.active {{ background: var(--accent); color: #fff; }}

            [data-view="en-only"] .ko {{ display: none; }}
            [data-view="ko-only"] .en {{ display: none; }}
        </style>
        <script>
            function toggleDarkMode() {{
                document.body.classList.toggle('dark-mode');
            }}
            function setViewMode(mode) {{
                document.body.setAttribute('data-view', mode);
                document.querySelectorAll('.view-mode-btns button').forEach(b => b.classList.remove('active'));
                event.target.classList.add('active');
            }}
            function toggleImage(id) {{
                const el = document.getElementById('img-' + id);
                el.style.display = (el.style.display === 'none') ? 'block' : 'none';
            }}
        </script>
    </head>
    <body data-view="bilingual">
        <div class="top-bar">
            <div class="title">📖 Handbook Premium</div>
            <div class="view-mode-btns">
                <button onclick="setViewMode('en-only')">EN</button>
                <button onclick="setViewMode('ko-only')">KO</button>
                <button class="active" onclick="setViewMode('bilingual')">모두</button>
            </div>
            <button onclick="toggleDarkMode()">🌒 테마</button>
        </div>
        <div class="container">
            {"".join(html_sections)}
        </div>
    </body>
    </html>
    ''')

    OUTPUT_HTML.write_text(template, encoding="utf-8")
    print(f"Success! Premium E-Book generated: {OUTPUT_HTML} ({total_pages} pages)")

if __name__ == "__main__":
    main()
