# Video to Text Document Builder - 프로젝트 현황 (PROJECT_STATUS.md)

이 문서는 멀티 에이전트 기반 개발 프로세스에 따라 현재 구현 상태를 추적하고 향후 계획을 관리합니다.

---

## 1. 프로젝트 요약
- **목표**: ebook 동영상을 분석하여 페이지 넘김을 감지하고, OCR을 통해 Markdown, HTML, PDF 문서로 변환.
- **기술 스택**: Python, OpenCV (영상 처리), PaddleOCR/Tesseract (OCR), Jinja2/ReportLab (문서 생성).

## 2. 역할별 작업 현황

### [분석 설계자 & 아키텍트] (Analysis & Architecture)
- **상태**: ✅ 설계 완료 및 기본 구조 수립
- **내용**: 
    - 영상 처리 엔진(Stable-Transition 상태 머신) 설계 완료.
    - 플러그형 OCR 엔진 인터페이스(`auto`, `paddle`, `tesseract`) 정의.
    - 파이프라인 기반 통합 프로세스 구축.

### [UI/CLI Designer]
- **상태**: ✅ 구현 완료
- **내용**: 
    - `cli.py`를 통한 명령행 인터페이스(CLI) 인자 및 도움말 설계.
    - 사용자 경험을 위한 상세 옵션(fps, threshold 등) 노출.

### [백엔드 개발자] (Backend Development)
- **상태**: ✅ 핵심 모듈 구현 완료
- **내용**: 
    - `video_processing.py`: 프레임 추출 및 중복 제거(pHash), 선명도 기반 프레임 선택 로직.
    - `ocr_engine.py`: PaddleOCR 및 Tesseract 연동.
    - `exporters.py`: 파일별(MD, HTML, PDF) 변환 로직.

### [프론트엔드 개발자] (Output Design)
- **상태**: ✅ 구현 완료
- **내용**: 
    - 생성된 HTML 및 Markdown의 레이아웃 구성.

### [품질 관리자 & 테스터] (QA & Testing)
- **상태**: ✅ 1차 안정화 완료
- **내용**: 
    - `report.json` 확장 (엔진명, 처리시간, 추출 파라미터 등 포함).
    - `tests/` 추가 및 텍스트 정규화 유닛 테스트 작성 완료.

### [배포 담당자] (Deployment)
- **상태**: ✅ 준비 완료
- **내용**: 
    - `requirements.txt` 정의 완료.
    - 실행 매뉴얼(`README.md`) 작성 완료.

---

## 3. 체크포인트 (Checkpoints)
| ID | 날짜 | 작업 내용 | 담당자 | 상태 |
| :--- | :--- | :--- | :--- | :--- |
| CP-001 | 2026-02-23 | 초기 전역 아키텍처 및 핵심 파이프라인 분석 | 아키텍트 | ✅ 완료 |
| CP-002 | 2026-02-23 | OCR 엔진 및 익스포터 연동 완료 | 백엔드 | ✅ 완료 |
| CP-003 | 2026-02-23 | CLI 최종 통합 및 README 작성 | 배포담당자 | ✅ 완료 |
| CP-005 | 2026-02-24 | 영상 처리 보조 신호(SSIM/Histogram) 설계 및 구현 | 아키텍트/백엔드 | ✅ 완료 |
| CP-006 | 2026-02-24 | 다중 파일 배치 처리 기능 추가 | 백엔드 | ✅ 완료 |
| CP-007 | 2026-02-24 | 병렬 OCR 처리(멀티프로세싱) 도입 | 아키텍트/백엔드 | 🗓️ 대기 |

---

## 4. 향후 계획 (Backlog)
- [✅] 에러 처리 강화 (OCR 엔진 미설치 시 가이드 등)
- [✅] 테스트 코드 기본 세트 구축
- [✅] `report.json` 메타데이터 확장
- [✅] 페이지 감지 보조 신호(SSIM/히스토그램) 추가 (Phase 2-1)
- [✅] 다중 비디오 일괄 처리 기능 (Phase 2-2)
- [🏃] 성능 최적화 (멀티프로세싱 도입) (Phase 3-1)
- [ ] OCR 후처리(문단/헤더 인식) 개선
