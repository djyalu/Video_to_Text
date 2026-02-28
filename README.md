# 📖 ServiceNow Handbook — Bilingual E-Book Generator

> ServiceNow Development Handbook (4th Edition) 원서를 OCR + 자동 번역으로 **영한 병렬 프리미엄 E-Book**으로 변환하는 멀티 에이전트 파이프라인

![Health Score](https://img.shields.io/badge/Health%20Score-100%2F100-brightgreen)
![Grade](https://img.shields.io/badge/Grade-A%2B-gold)
![Pages](https://img.shields.io/badge/Pages-204-blue)
![Code Blocks](https://img.shields.io/badge/Code%20Blocks-119-purple)

---

## ✨ 주요 기능

| 기능 | 설명 |
|------|------|
| **2-Column OCR** | 한 이미지에 2페이지가 포함된 원본을 왼쪽/오른쪽 분리 스캔 |
| **Smart Code Detection** | 80+ 패턴으로 코드 블록 자동 감지, 중괄호 기반 자동 들여쓰기 |
| **Smart Line Joining** | 목차/리스트 vs 본문을 자동 감지하여 줄바꿈 보존 또는 합침 |
| **Pre-Translation OCR Fix** | 번역 전 20+ OCR 오타 자동 교정 |
| **Dark Mode** | CSS media query + 수동 토글 |
| **실시간 검색** | 키워드로 204페이지 실시간 필터링 |
| **목차 사이드바** | 플로팅 버튼 → 슬라이드 패널 네비게이션 |
| **읽기 진행바** | 스크롤 연동 그라데이션 진행 표시 |
| **EN/KO/Both 모드** | 영문, 한글, 양쪽 모두 표시 토글 |

---

## 🏗️ 아키텍처

```
source/ServiceNow_Handbook.pdf
        ↓ extract_frames.py
pages/page_001.jpg ... page_204.jpg
        ↓ agent100_split_ocr.py (100 Worker Agents)
AGENT_100_CORRECTIONS.json (EN + KO + Codes)
        ↓ build_ebook_v2.py
ServiceNow_Handbook_Premium_Ebook.html (11.6 MB)
```

### 멀티 에이전트 구성

| 에이전트 | 수량 | 역할 |
|----------|------|------|
| PM (Project Manager) | 1 | 전체 파이프라인 오케스트레이션 |
| OCR Worker | 100 | 페이지별 2-Column OCR + 번역 |
| QA Monitor | 1 | 진행률 모니터링 + 품질 체크 |
| Code Detector | (내장) | 80+ 패턴 코드 블록 감지 |
| Translator | (내장) | Google Translate API 호출 |
| Layout Builder | 1 | Premium HTML E-Book 생성 |
| Reader Audit | 100 | 최종 품질 감사 |
| Translation QA | 50 | 번역 품질 검수 |

---

## 🚀 빠른 시작

### 1. 환경 설정

```bash
pip install -r requirements.txt
```

### 2. 페이지 이미지 준비

```bash
# PDF에서 페이지 이미지 추출
python extract_frames.py
```

### 3. OCR + 번역 (100 Agent Pipeline)

```bash
python agent100_split_ocr.py
```

### 4. Premium E-Book 빌드

```bash
python build_ebook_v2.py
```

### 5. 품질 감사

```bash
python agent100_audit_v4.py      # 종합 감사
python agent50_translation_qa.py  # 번역 QA
```

---

## 📊 품질 감사 결과

| 영역 | 점수 | 상세 |
|------|------|------|
| **Content** | 40/40 | 203/204 페이지, 489 EN + 475 KO 문단 |
| **Code** | 15/15 | 119 블록, 자동 들여쓰기, 0 오타 |
| **CSS** | 20/20 | 10/10 기능 (Dark mode, Responsive 등) |
| **UX** | 25/25 | 10/10 기능 (검색, TOC, 진행바 등) |
| **Total** | **100/100** | **Grade A+** |

---

## 📁 프로젝트 구조

```
Video_to_Text/
├── agent100_split_ocr.py      # 🔧 핵심: 100 Agent OCR Pipeline
├── build_ebook_v2.py          # 📖 Premium E-Book Builder
├── agent100_audit_v4.py       # 🔍 종합 감사 (Health Score)
├── agent50_translation_qa.py  # 🇰🇷 번역 품질 검수
├── agent100_reader_audit.py   # 📖 독자 감사
├── agent100_full_audit_v3.py  # 🔍 4팀 감사 (Layout/Text/Code/UX)
├── extract_frames.py          # 🖼️ PDF → 이미지 추출
├── requirements.txt           # 📦 Python 의존성
├── pages/                     # 🖼️ 원본 이미지 (204장)
├── pages_compressed/          # 🖼️ 압축 이미지
├── source/                    # 📄 원본 PDF
└── ServiceNow_Handbook_Premium_Ebook.html  # ✅ 최종 결과물
```

---

## 🔖 체크포인트 이력

| Tag | 설명 |
|-----|------|
| `CP-PERFECT` | ✅ Health Score 100/100, Grade A+ |
| `CP-UX-UPGRADE` | Dark mode, 검색, TOC, 진행바 |
| `CP-TRANSLATION-QA` | 번역 전 OCR 교정, 50-agent QA |
| `CP-INDENT` | 코드 자동 들여쓰기 |
| `CP-CODE-BLOCKS` | 117 코드 블록 감지 (80+ 패턴) |
| `CP-SMART-JOIN` | 목차/리스트 줄바꿈 보존 |
| `CP-READABILITY` | 문단 분리, Pretendard 폰트 |
| `CP-PREMIUM` | 프리미엄 레이아웃 |
| `CP-FINAL` | 전체 2-col OCR |

---

## 🛠️ 기술 스택

- **OCR**: Tesseract OCR (영문)
- **번역**: Google Translate (deep-translator)
- **이미지**: Pillow (PIL)
- **프론트엔드**: Vanilla HTML/CSS/JS
- **폰트**: Crimson Pro (EN), Pretendard (KO), JetBrains Mono (Code)
- **Python**: 3.10+

---

## 📝 라이선스

이 프로젝트는 개인 학습 목적으로 만들어졌습니다.
원서 저작권은 Tim Woodruff에게 있습니다.
