#!/usr/bin/env python3
"""
ServiceNow Development Handbook - 한국어 번역 품질 개선 스크립트
각 페이지의 OCR 기반 저품질 번역을 전문 수준의 한국어 번역으로 교체합니다.
"""
import re
import html

# 고품질 번역 사전: page_number -> 번역 텍스트
TRANSLATIONS = {
    1: "SERVICENOW 개발 핸드북\n\nServiceNow 개발자를 위한 지침 및 모범 사례 모음집\n제4판\n\nTIM WOODRUFF 저",

    2: "SERVICENOW 개발 핸드북\n제4판\n\nServiceNow 개발자, 관리자 및 설계자를 위한 전문가 팁, 지침 및 모범 사례 모음집\n\nTim Woodruff 저\n기여자 포함",

    3: "~헌정~\n\nShayla, 영원히 나의 모든 것.\n\nCiel, Casey, 그리고 Bill에게 — 가족이란 어떤 바보짓을 하든 떼려야 뗄 수 없는 사이라는 것을 보여준 이들.\nRoger만 빼고.\n꺼져, 아빠.\n\nServiceNow Discord 커뮤니티 — 만 명 이상의 회원으로 성장하면서도 오랜 친구 모임 같은 느낌을 유지해온 커뮤니티.\n함께해요! https://discord.snc.guru\n\n독자 여러분 — 읽어주셔서, 제 작업을 지원해주셔서, 이 멋진 커뮤니티의 일원이 되어주셔서 감사합니다.",

    4: "이 페이지는 의도적으로 비워둔 페이지입니다.\n이 부분을 제외하고요.\n그리고 저 부분을 설명하는 이 부분도요.",

    5: "버전 4.0.5\n\n이 단행본을 구매하셨다면 출판 이후 중요한 업데이트가 있는 섹션의 디지털 사본을 LinkedIn을 통해 연락하여 받으실 수 있습니다: https://li.snc.guru\n\n이 책에 링크된 페이지들은 비공개 URL 단축기 'snc.guru'의 하위 도메인인 짧은 링크에서 리디렉션됩니다. 따라서 이 책에서 참조된 링크가 업데이트되면, 전체를 다시 게시하지 않고도 하위 도메인 포워딩 규칙을 업데이트하여 링크를 '수정'할 수 있습니다.\n\n이 책의 짧은 링크가 더 이상 작동하지 않는 경우, LinkedIn을 통해 연락해 주세요.\n\nKindle로 이 책을 구매하셨다면, http://update.snc.guru로 이동하여 최신 버전이 있는지 무료로 확인하실 수 있습니다.",

    6: "목차\n\n저자 소개 / 소개 / 코드 및 코딩 지침\n순수 함수 / DRY 코드 작성 / 참조에 의한 전달 / 필드 값 가져오기 및 설정 / 일관성 / 필드 보안 vs. 필드 가림 / 클라이언트 스크립트 및 필드 수준 보안 / setVisible() vs. setDisplay() / 비즈니스 규칙 순서 및 .update()\n이전(Before) / 이후(After) / 비동기(Async) / 표시(Display) / AJAX 및 표시 비즈니스 규칙 / DOM 조작 / 코딩하지 않아야 할 때 / 스타일 및 표준\n디버깅\n서버 측 디버깅 / 디버거 콘솔 / 클라이언트 측 디버깅 / 일반적인 버그 / 비즈니스 규칙에서의 .update() / .update()는 삽입도 가능 / .setWorkflow(false) vs. .autoSysFields(false) / 쿼리 결과 제한\n명명 규칙\n테이블 / 필드 이름 및 레이블 / 변수 / 객체 속성",

    7: "목차 (계속)\n\n테이블 및 목록 / 대규모 데이터베이스 작업\n이벤트 기반 재귀 / 멀티스레딩\n대형 테이블\n데이터베이스 인덱스(Indices? Indexes?) / 테이블 회전\n불필요한 로그 구문\nFlow Designer\n플레이북 / 흐름(Flows) / 하위 흐름(Subflows) / 작업(Actions) / 단계(Steps) / 트리거(Triggers) / 결정 테이블(Decision Tables) / 입력/출력(Inputs/Outputs) / 데이터 필(Data Pills)\nFlow Designer의 문제점\n입력 룰렛 / 복잡한 입력 / 누락된 버전 기록 / 보안 / 흐름 실행 오버헤드\n오류 처리\n기본 오류 처리기 / 재사용 가능한 오류 처리기 구축 / Flow를 쓸 것인가, 말 것인가? / fd_data 객체 사용 / 인라인 스크립트\n구성 가능성(Configurability)\n구성 가능성 계획 / 시스템 속성 / 시스템 속성 카테고리 / 사용자 기본 설정\n사용자 기본 설정 설정 / 사용자 기본 설정 검색 / 기본(글로벌) 사용자 기본 설정\n세션 변수 및 클라이언트 데이터 / 모듈성",

    8: "목차 (계속)\n\n기본 함수 매개변수 / 레코드 스크립트\n보안\nACL(보안 규칙) / 쿼리 비즈니스 규칙 / 관리자 역할 / 보안 시스템 속성\n비공개 시스템 속성\nGlideRecord vs. GlideRecordSecure\n서비스 포털(Service Portal)\n클라이언트 스크립트 / 위젯 및 카탈로그 / 포털 레코드 / 위젯: 인스턴스 및 옵션\n업데이트 관리\n업데이트 세트 배치 처리 / 기본 업데이트 세트\n추적되는 항목과 추적되지 않는 항목\n비공개 시스템 속성 / 범위 지정된 레코드 추적\n승격 / 복제\n복제 주기(Cadences)\n앱 게시\n계획 / 일반 요구 사항\n필수 목록 아티팩트\n기술 부채(Technical Debt)\n우선순위 지정 및 해결 / 기술 부채 감소\n무료 도구 및 기사\n위험한 비즈니스 식별 / 가이드가 되세요! / 더 빠르고 효율적인 GlideRecord / 스마트한 업데이트 세트 / 저널 편집기 / URL을 통한 카탈로그 변수 설정 / 시간대 유틸리티 / 업데이트 세트에 포함",

    9: "목차 (계속)\n\n맞춤형 Chrome 엔진 / ServiceNow를 직업으로 / 이벤트 기반 재귀 / 결론",

    10: "소개\n\nServiceNow 개발 핸드북은 가르치고 설명하는 정신으로 작성되었습니다. 단순히 '모범 사례'라는 제목 아래 일련의 규칙을 나열하는 것이 아니라, 그 이유까지 설명합니다.\n\n이것은 책 형태의 완전한 ServiceNow 교육 과정이 아닌, 요약된 '개발자 가이드'입니다. 독자가 ServiceNow 플랫폼에 대해 이미 어느 정도 익숙하고, JavaScript에 대한 최소한의 실무 지식을 보유하고 있다고 가정합니다.\n\nServiceNow에 대해 아직 잘 모른다면, 제 다른 책 「Learning ServiceNow, 제2판」(ISBN-13: 978-1788837040)을 읽어보시기 바랍니다. URL http://lsn.snc.guru/에서 찾으실 수 있습니다.\n\nServiceNow 플랫폼과 JavaScript에 대한 기본적인 이해가 있다면, 이 책을 ServiceNow에서의 작업을 깔끔하고, 효과적이고, 안전하고, 견고하게 만들기 위한 로드맵으로 활용하시기 바랍니다.\n\n이것은 지침(guidelines)이라는 점을 명심하세요. 이 개요서의 모든 규칙에는 최소 하나의 예외가 있을 수 있습니다. 중요한 것은 주어진 표준이 왜 그런지를 이해하는 것이며, 이를 통해 규칙을 더 잘 따를 뿐만 아니라 적절히 적용할 수 있는 역량을 갖추게 됩니다.",

    11: "소개 (계속)\n\n모범 사례에서 벗어나는 것이 더 나은 이유가 있을 때도 있지만, 그 이유를 문서화하는 것이 중요합니다. 이후의 개발자가 추측할 필요가 없도록 하세요. 당신이 시도한 것과 그 결과를 문서화하세요.\n\n모범 사례가 항상 가능하지는 않은 예외의 한 가지 좋은 사례는 DOM(Document Object Model) 조작입니다. 이는 지원되지 않으며 향후 버전에서 깨질 수 있으므로 피해야 합니다. 그러나 Service Portal 개발에서는 대부분의 DOM 접근이 차단되지만, 클라이언트 측 스크립트에서 DOM 조작을 활용할 때 작동하는 경우도 있습니다.\n\n이 핸드북에 포함된 코드 조각 및 예제는 GitHub에서도 제공되므로, 더 자세히 검토하고 복사/붙여넣기할 수 있습니다. 이 코드는 https://handbookcode.snc.guru/에서 찾을 수 있습니다.\n\n이 작업에서 오류나 누락을 발견하면 연락해 주세요! Twitter/X 또는 Threads @TheTimWoodruff, LinkedIn https://www.linkedin.com/in/sn-timw/에서 연락할 수 있습니다.\n\n특히 ServiceNow 기술 설계자나 동료와 가까운 태평양 북서부(포틀랜드, 오리건 지역)에 계시다면, 더 나은 ServiceNow 사용자 그룹(SNUG)에 대해 문의해 보세요! 연락처에 링크된 Slack 및 Discord에서 훌륭한 개발자 커뮤니티를 찾을 수 있습니다.",

    12: "여정의 시작",

    13: "순수 함수 (PURE FUNCTIONS)\n\n순수 함수란 자신의 코드 외의 다른 상태에 의존하지 않으며, '부작용(side-effects)'(예: 자체 외부의 상태 수정)을 일으키지 않는 함수입니다. 순수 함수의 상위 범위에서 무슨 일이 일어나든, 동일한 데이터가 전달되는 한 항상 동일한 결과를 반환합니다.\n\n순수 함수는 상태에 의존하는 함수보다 이해하기 훨씬 쉽습니다. 왜냐하면 관련 상태가 함수 자체 내에만 존재하기 때문입니다. 그리고 훨씬 더 모듈화되는 경향이 있습니다. 항상 순수 함수를 사용할 필요는 없지만, 거의 항상 좋은 아이디어입니다. (이 지침들과 마찬가지로 최선의 판단을 사용하세요.)\n\n순수 함수를 호출할 때, 환경이나 호출 범위의 나머지 상태와 관계없이, 함수에 예측 불가능한 부작용이 있어서는 안 되며, 시간이나 객체 속성과 같은 상태 데이터에 의존해서는 안 됩니다.\n\n다음 함수는 myName이라는 변수를 사용하지만 선언하지 않습니다. 전역 또는 상위 범위에서 선언된 변수가 필요하므로 순수 함수가 아닙니다:\n\nfunction sayHello() {\n  alert('Hello, ' + myName + '!');\n}\n— 비순수 함수\n\n그러나 이 함수를 호출할 때마다 myName을 인수로 전달하면, 동일한 값이 항상 기대되더라도, 함수를 읽고, 업데이트하고, 재활용하기가 훨씬 쉬워집니다. 이것이 바로 순수 함수의 핵심입니다!\n\nfunction sayHello(myName) {\n  alert('Hello, ' + myName + '!');\n}\n— 순수 함수",

    14: "DRY 코드 작성\n\n순수하지 않은 함수의 일반적인 예는 스크립트 포함(Script Include)입니다. 프로그래밍에서 'DRY(Don't Repeat Yourself)'는 중요한 원칙이며, 비즈니스 규칙 내에서 공통 메서드를 호출하기 위해 스크립트 포함 클래스를 사용하는 것은 좋은 코딩 표준입니다.\n\n비즈니스 규칙에서 호출되는 스크립트 포함은 거의 모든 상황에서 current 변수를 사용하지 않아야 합니다. 대신, 인수로 전달된 데이터를 사용해야 합니다. 이는 코드를 다른 컨텍스트의 다른 스크립트에서 재사용할 수 있게 하기 때문입니다.\n\n다음 코드를 고려해 보세요:\n\nvar grIncident = new GlideRecord('incident');\nvar encodedQuery = '여기에 인코딩된 쿼리';\ngrIncident.addEncodedQuery(encodedQuery);\ngrIncident.query();\nwhile (grIncident.next()) {\n  grIncident.setValue('state', 3); // 상태를 '진행 중'으로 설정\n  grIncident.update();\n}",

    15: "DRY 코드 작성 (계속)\n\n위 코드에서 각 테이블(incident, problem, change_request)에 대해 거의 동일한 코드 블록이 반복되며, 테이블 이름과 상태 값만 다릅니다. 이런 유형의 코드는 비효율적이고 읽기 어려우며 오류가 발생하기 쉽습니다.\n\n실행 방식을 변경해야 할 때 한 번이 아닌 세 번 이상 변경해야 합니다. 변경이 필요할 때마다 실수할 가능성이 높아지고, 결과적으로 조건부로만 발생하는 버그로 이어져 문제 해결이 훨씬 어려워집니다.\n\nDRY 코드가 WET(Write Everything Twice) 코드보다 낫다는 점이 분명해지길 바랍니다.",

    16: "DRY 코드 작성 (계속)\n\n전체 코드 블록을 반복하는 대신, 테이블 이름, 인코딩된 쿼리, 상태 값 등 각 코드 블록 간의 차이점을 구성하는 데이터를 포함하는 객체 배열을 구성할 수 있습니다.\n\n일단 해당 데이터를 얻으면, 간단히 반복하면서 각 객체의 값을 사용할 수 있습니다. 한 가지 방법으로 다음과 같이 수행할 수 있습니다:\n\nvar stateChangeDetails = [\n  { table_name: 'incident', encoded_query: 'some_query', state_value: 3 },\n  { table_name: 'problem', encoded_query: 'some_other_query', state_value: 4 },\n  { table_name: 'change_request', encoded_query: 'yet_a_third_query', state_value: 5 }\n];\n\nfor (var i = 0; i < stateChangeDetails.length; i++) {\n  var stateChange = stateChangeDetails[i];\n  var grRecord = new GlideRecord(stateChange.table_name);\n  grRecord.addEncodedQuery(stateChange.encoded_query);\n  grRecord.query();\n  while (grRecord.next()) {\n    grRecord.setValue('state', stateChange.state_value);\n    grRecord.update();\n  }\n}",

    17: "객체 속성 (Object Properties)\n\n객체 생성자(Constructor)에 대해 알아보겠습니다. 예를 들어 'Tim', 나이, 'Extreme to the max'를 전달하면, 결과 객체는 다음과 같이 보입니다:\n\nPerson {name: \"Tim\", age: 30, coolness: \"Extreme to the max\"}\n\n생성자는 함수이므로 기본값을 설정하거나 몇 가지 검증을 수행하는 등의 코드를 추가할 수 있습니다. 주어진 객체를 생성하는 데 사용된 생성자가 무엇인지 아는 것이 유용할 때가 많습니다. constructor.name 속성에 접근하여 찾을 수 있습니다:\n\nSomeObject.constructor.name // 해당 객체의 생성자 이름을 문자열로 반환\n\n참고: 명명 규칙 섹션에서 배우겠지만, 객체 유형에 대한 몇 가지 표시를 이름에 제공하는 것이 좋습니다. 그러면 더 쉽게 식별할 수 있습니다.",

    18: "즉시 실행 함수 표현식 (IIFE) 및 ES6\n\n'();'를 추가하면 즉시 실행됩니다. ServiceNow는 서버 측에서 ES6(ECMAScript 6) JavaScript를 실행할 수 없으며, ES5 코드만 처리할 수 있습니다.\n\nJavaScript의 생성자를 이해했으므로, 이전 예제에서 배운 것을 데이터 객체 배열에 적용해 보겠습니다.\n\n또한 생성자를 사용하여 속성 재정의, 값 검증, 기본 속성 값에 포함된 '메서드' 함수 추가 등 다른 유용한 작업을 수행할 수 있습니다.\n\n자세한 내용은 Mozilla JS 문서를 확인하세요. 단, ServiceNow 서버 측 코드는 ES5만 지원한다는 점을 기억하세요.",

    19: "생성자를 활용한 DRY 코드 최적화\n\nStateChangeDetail 생성자를 선언하여 세 개의 인수(테이블 이름, 쿼리, 상태)를 받고, 세 가지 속성을 가진 새 객체를 구성합니다. 그런 다음 해당 생성자에서 생성된 객체 배열을 빌드하고, 마지막으로 배열을 반복하면서 각 객체 요소에 접근하여 작업을 수행합니다.\n\n위의 코드는 매우 DRY하고 효과적이지만, 이를 작성하는 또 다른 방법이 있습니다. 기능적(functional) 접근 방식을 사용하여, 객체 배열을 구축하는 대신 데이터를 전달할 수 있는 함수를 호출하면 됩니다.",

    20: "함수형 DRY 코드\n\n도우미 함수에 인수를 전달할 수 있습니다! 인코딩된 쿼리를 선택적으로 만들면, 쿼리 없이 호출하여 해당 테이블의 모든 레코드를 업데이트하는 등의 깔끔한 작업도 가능합니다.\n\n/**\n * 제공된 인코딩된 쿼리와 일치하는 제공된 테이블의 모든 레코드 상태를 업데이트합니다.\n * @param {string} tableName - 작업할 테이블의 이름\n * @param {string|number} newState - 상태 필드의 새로운 값\n * @param {string} [encodedQuery] - 레코드 필터링을 위한 인코딩된 쿼리 문자열(선택)\n * @return {number} 업데이트된 레코드 수\n */\nfunction changeState(tableName, newState, encodedQuery) {\n  var grRecord = new GlideRecord(tableName);\n  if (encodedQuery) {\n    grRecord.addEncodedQuery(encodedQuery);\n  }\n  grRecord.setValue('state', newState);\n  grRecord.updateMultiple();\n  return grRecord.getRowCount();\n}\n\nchangeState('incident', 3, 'some_query');\nchangeState('problem', 4, 'some_other_query');\nchangeState('change_request', 5, 'third_query');",

    21: "참조에 의한 전달 (PASS-BY-REFERENCE)\n\n참고: updateMultiple() GlideRecord API는 작업을 훨씬 더 효율적으로 만들어주는 메서드 중 하나입니다. 자세한 내용은 updateMultiple()에 대한 기사 http://multiops.snc.guru/ 및 deleteMultiple()을 참조하세요.\n\n함수를 다루는 한 가지 중요한 사실은 JavaScript의 범위(scope)와 객체가 '참조에 의한 전달(pass-by-reference)' 또는 PBR이라는 것입니다. 이는 JavaScript에만 고유한 것은 아니지만, 변수가 특정 데이터 유형으로 선언되고 유지되어야 하는 '엄격한 타입 지정(strictly typed)' 언어에서는 나타나지 않을 수 있습니다.\n\n다음 코드를 고려해 보세요:\n\nvar coolness = 'Extreme to the max';\nchangeCoolness(coolness);\nconsole.log(coolness); // 여전히 'Extreme to the max'를 출력\n\nfunction changeCoolness(coolness) {\n  var actualCoolnessLevel = 'Total doofus';\n  return actualCoolnessLevel;\n}\n\n이 코드에서 문자열(원시 값)을 전달하고 있으므로, 원래 변수는 변경되지 않습니다.",

    22: "참조에 의한 전달 - 객체의 경우\n\n이번에는 원시 변수가 아닌 비원시(non-primitive) 객체를 사용하여 동일한 작업을 수행해 보겠습니다:\n\nvar me = {\n  name: 'Tim',\n  age: 30,\n  coolness: 'Extreme to the max'\n};\n\nchangeCoolness(me);\nconsole.log('나는 이만큼 멋지다: ' + me.coolness);\n\nfunction changeCoolness(person) {\n  var actualCoolnessLevel = 'Total doofus';\n  person.coolness = actualCoolnessLevel;\n}\n\n위의 코드를 주의 깊게 살펴보세요. 8행에서 coolness 속성의 값을 출력하면 어떤 결과가 나올까요? 값이 변경된 유일한 곳이 함수 내부임에도 불구하고, 놀라울 수도 있습니다.",

    23: "참조에 의한 전달 - 상세 설명\n\n실제로 'Total doofus'라는 문자열이 출력됩니다! 객체에 대한 참조가 전달되었기 때문에, 함수의 person 변수와 상위 범위의 me 변수는 문자 그대로 메모리에 있는 동일한 객체를 참조합니다.\n\n두 변수가 '동일한 값을 갖는 객체를 포함'한다는 의미가 아닙니다. 둘 다 말 그대로 동일한 객체에 대한 참조를 포함한다는 뜻입니다. 하나의 변수에 무엇을 하든 다른 변수에도 영향을 미칩니다. 왜냐하면 그들은 말 그대로 동일한 객체를 참조하기 때문입니다.\n\n이는 GlideRecord와 GlideElement 객체를 사용할 때와 같이, 코드가 '추상 객체'와 일을 수행하는 방식에 중요한 영향을 미칩니다. 특히 객체의 일부 속성을 수정하거나 접근할 수 있는 루프 내에서 작업할 때 중요합니다.\n\n참조에 의한 전달을 사용하는 것은 '잘못'이 아니지만, 원시 값의 경우 값에 의한 전달(pass-by-value)이 일어나고, 객체의 경우 참조에 의한 전달이 일어난다는 동작 차이를 이해하는 것이 중요합니다.",

    24: "필드 값 가져오기 및 설정 (GETTING AND SETTING FIELD VALUES)\n\nGlideRecord 객체의 모든 필드는, 비즈니스 규칙의 current이든 grIncident와 같이 선언된 변수든, 그 자체로 또 다른 객체입니다. 이 객체 유형을 GlideElement라고 합니다.\n\n전문가 팁: 이 주제에 대한 심층 정보는 http://pbr.snc.guru/에서 찾을 수 있습니다.\n\nvar shortDesc = grInc.short_description;\n\n위의 코드에서 실제로는 shortDesc 변수를 GlideElement 객체에 대한 참조로 설정하고 있습니다. 값이 변경되면 참조에 의한 전달(PBR)을 사용하기 때문에 변수도 변경됩니다.\n\n따라서 getValue()를 사용하여 원시 값을 검색하는 것이 가장 효율적이고 최선의 방법입니다. getValue() API가 이를 수행하는 가장 좋은 일관된 방법이며, toString()을 사용할 수도 있습니다.\n\n적어도 하나의 스크립트 항목 내에서 일관성을 유지하는 것이 중요합니다. 그렇지 않으면 JavaScript의 타입 강제 변환으로 인해 문제가 발생할 수 있습니다.",

    25: "필드 값 - 저널 필드와 예외\n\nGlideElement의 getJournalEntry() 메서드는 예기치 않게 동작할 수 있습니다:\n\ngrInc.work_notes.getJournalEntry(1); // 가장 최근 저널 항목만 반환\ngrInc.work_notes.getJournalEntry(-1); // 'nn'으로 구분된 모든 저널 항목을 반환\n\n정말 중요한 점: getValue()를 사용하는 것이 특히 원시 값을 검색할 때 가장 효율적이고 최선의 방법입니다. 얽힌 참조와 예상치 못한 동작의 복잡한 관계를 빠르게 만들 수 있기 때문입니다.\n\n적어도 하나의 스크립트 내에서 일관성을 유지하는 것이 중요합니다. 때때로 grInc.field_name + '' 같은 암묵적 유형 변환에 의존하고 싶은 유혹이 있을 수 있지만, JavaScript의 타입 강제 변환으로 인한 문제가 발생할 수 있습니다.",

    26: "일관성 (CONSISTENCY)\n\n문자열 구분 기호에 대한 일관성도 중요합니다. 작은따옴표('this')와 큰따옴표(\"this\") 사이에서 일관성을 유지하세요.\n\n개인적으로 저자는 작은따옴표(')를 사용합니다. 큰따옴표는 추가 키 입력(SHIFT)이 필요하고, 문자열 내에서 축약형(apostrophe)을 사용할 때 이스케이프해야 하는 불편함이 있습니다.\n\n어떤 것을 선택하든, 일관성이 핵심입니다. 한 스크립트 내에서 따옴표 스타일을 혼합하면, 나중에 코드를 업데이트하려는 다음 개발자에게 매우 짜증나는 경험이 됩니다.",

    27: "필드 보안 vs. 필드 가림 (FIELD SECURITY VS. FIELD OBSCURITY)\n\n코딩 스타일(들여쓰기, 중괄호 배치 등)에 대해서도 일관성이 중요합니다. ServiceNow의 기본 IDE는 들여쓰기가 좋지 않으므로, 반드시 'Code Format(코드 서식)' 버튼을 사용하세요.\n\n필드를 숨기거나 읽기 전용으로 만드는 것이 실제 보안 조치가 아님을 인식하는 것이 중요합니다. 외부 IDE(WebStorm, VS Code, Notepad++, Sublime Text 등) 중 하나를 사용하여 ServiceNow의 브라우저 기반 IDE보다 더 신뢰할 수 있는 서식/미화 도구로 코드를 작성할 수 있습니다.",

    28: "클라이언트 스크립트 및 필드 수준 보안\n\n필드를 숨겨도 해당 값이 자동으로 지워지지 않습니다! 클라이언트 측 필드 보호가 처음에 필드를 표시한 후 조건부로 숨기면, 사용자가 입력한 값이 여전히 필드에 남아 있어 데이터베이스에 저장되고 잠재적으로 로직도 트리거될 수 있습니다.\n\n최신 버전의 ServiceNow에는 UI 정책에서 필드를 숨길 때 자동으로 값을 지우는 체크박스가 있습니다. 그러나 이 보호를 무시하면 어떤 영향이 있는지 자문해 보세요.\n\n데이터 무결성 보호가 중요한 경우, 반드시 ACL, 데이터 정책, 또는 비즈니스 규칙과 같은 서버 측 구성 요소를 사용하세요. 클라이언트 측 보호에만 의존하지 마세요.\n\n일반적으로 클라이언트 스크립트를 사용하여 필드 표시 여부를 제어하는 대신, 비즈니스 규칙, ACL, 또는 데이터 정책과 같은 서버 측 구성 요소를 사용하는 것이 좋습니다. 이는 클라이언트 측 조치가 우회될 수 있기 때문입니다.",

    29: "setVisible() vs. setDisplay()\n\ng_form.setVisible('location', false): 요소를 숨기지만, 해당 요소가 있던 빈 공간은 양식에 남아 있습니다. 일부 상황에서는 바람직할 수 있지만, 대부분의 경우 필드가 차지하던 전체 공간이 사라지기를 원할 것입니다.\n\ng_form.setDisplay('location', false): 요소와 그 공간 모두를 제거합니다.\n\nsetVisible()과 setDisplay()의 차이는 실제 HTML 문서 요소의 'visibility'와 'display' 속성을 각각 사용하기 때문에 발생합니다.\n\n참고: 조건이 너무 복잡하여 조건 빌더에 표시할 수 없는 경우와 같이, 클라이언트 스크립트를 사용하여 필드를 숨기고 표시하는 사용 사례가 있습니다. 그러나 기본적으로는 필드 가시성, 필수 여부, 읽기 전용 설정을 제어하기 위해 클라이언트 스크립트 대신 UI 정책 및 UI 정책 작업을 사용하는 것이 좋습니다.",

    30: "비즈니스 규칙 순서 및 .update() — Before(이전)\n\n비즈니스 규칙의 When 필드에는 Before(이전), After(이후), Async(비동기), Display(표시) 네 가지 옵션이 있으며, 이는 동작과 사용 가능한 기능을 결정합니다.\n\nBefore 옵션은 비즈니스 규칙이 삽입, 업데이트 또는 삭제 작업이 데이터베이스에 커밋되기 전에 실행됨을 의미합니다. 이는 current.setAbortAction(true)를 사용하여 작업을 중지할 수 있음을 의미합니다.\n\nBefore 비즈니스 규칙에서는 current.update()를 호출할 필요가 없습니다. 레코드가 아직 데이터베이스에 커밋되지 않았으므로, 현재 객체의 필드 값만 변경하면 됩니다.",
}

def apply_translations(input_file, output_file):
    """HTML 파일의 번역 텍스트를 고품질 번역으로 교체합니다."""
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    for page_num, translation in TRANSLATIONS.items():
        # 각 페이지의 translation-text 내용을 찾아 교체
        # HTML 엔티티로 변환하여 특수 문자 처리
        safe_translation = translation.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        # 줄바꿈을 <br> 태그로 변환
        safe_translation = safe_translation.replace('\n', '<br>\n')
        
        # 페이지 패턴 찾기
        pattern = (
            r'(<div class="handbook-page" id="page-' + str(page_num) + r'">'
            r'.*?<p class="translation-text">)'
            r'(.*?)'
            r'(</p>)'
        )
        
        replacement = r'\1' + safe_translation + r'\3'
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"번역이 적용되었습니다: {output_file}")
    print(f"총 {len(TRANSLATIONS)}개 페이지 번역 업데이트 완료")

if __name__ == '__main__':
    input_file = r'F:\projects\Video_to_Text\Visual_ServiceNow_Handbook.html'
    output_file = r'F:\projects\Video_to_Text\Visual_ServiceNow_Handbook.html'
    apply_translations(input_file, output_file)
