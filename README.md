# Video to Text Document Builder

ebook 화면을 한 장씩 넘기며 캡처한 동영상에서 텍스트를 추출해 `Markdown`, `HTML`, `PDF`로 문서화하는 CLI 앱입니다.

## 주요 기능

- 페이지 전환 상태 감지(Stable -> Transition -> Stable)
- 넘김 속도 변화(빠름/느림)에 대응하는 페이지 인식
- 페이지별 대표 프레임 자동 선택(선명도 기반)
- OCR 추출(`auto`, `paddle`, `tesseract`)
- 페이지별 OCR JSON 저장
- `book.md`, `book.html`, `book.pdf`, `report.json` 생성

## 프로젝트 구조

```text
video_to_text/
  __main__.py
  cli.py
  pipeline.py
  video_processing.py
  ocr_engine.py
  exporters.py
  models.py
requirements.txt
```

## 설치

### 1) Python 의존성

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2) OCR 엔진 준비

기본 권장:
- `paddleocr` (한국어 품질이 일반적으로 더 좋음)

대안:
- `pytesseract + tesseract`

#### PaddleOCR 사용 시

```powershell
pip install paddleocr paddlepaddle
```

#### Tesseract 사용 시

- Tesseract 설치 후 실행 파일이 PATH에 있어야 합니다.
- 한국어 OCR을 위해 `kor.traineddata`를 설치해야 합니다.

## 실행 예시

```powershell
python -m video_to_text --input "source/capture video.mp4" --output output --ocr-engine auto --ocr-lang kor+eng
```

정상 실행 시 `output` 폴더에 다음 파일이 생성됩니다.

```text
output/
  pages/page_0001.jpg
  ocr/page_0001.json
  book.md
  book.html
  book.pdf
  report.json
```

## 자주 쓰는 옵션

- `--sample-fps`: 초당 분석 프레임 수 (기본 6.0)
- `--transition-threshold`: 페이지 넘김 시작 감지 임계값 (기본 18.0)
- `--stable-threshold`: 새 페이지 정착 감지 임계값 (기본 4.0)
- `--min-transition-samples`: 연속 transition 샘플 수 (기본 2)
- `--min-stable-samples`: 연속 stable 샘플 수 (기본 3)
- `--min-focus`: 흐린 프레임 제외 기준 (기본 15.0)
- `--max-pages`: 최대 처리 페이지 제한
- `--no-pdf`, `--no-html`, `--no-markdown`: 특정 출력 비활성화
- `--min-page-gap-sec`: 동일 페이지 중복 저장 방지 최소 시간 간격 (기본 0.5)

## 권장 파라미터 프리셋

| 환경 | `--sample-fps` | `--transition-threshold` | `--min-transition-samples` | 비고 |
| :--- | :---: | :---: | :---: | :--- |
| **빠른 넘김** (1초에 1-2장) | 10.0 | 12.0 | 1 | 페이지 전환이 매우 빠를 때 |
| **일반적인 넘김** (기본) | 6.0 | 18.0 | 2 | 대부분의 ebook 뷰어 |
| **느리거나 애니메이션** | 4.0 | 25.0 | 3 | 넘김 효과가 길고 화려할 때 |
| **고해상도/정밀** | 8.0 | 15.0 | 2 | 글자가 작고 레이아웃이 복잡할 때 |

예시:

```powershell
python -m video_to_text \
  --input "source/capture video.mp4" \
  --output output \
  --sample-fps 8 \
  --transition-threshold 16 \
  --stable-threshold 3.5 \
  --ocr-engine paddle
```

## 품질 튜닝 가이드

- 페이지가 누락되면:
  - `--transition-threshold`를 낮추세요.
  - `--sample-fps`를 높이세요.
- 중복 페이지가 많으면:
  - `--transition-threshold`를 높이세요.
  - `--min-transition-samples`를 3 이상으로 올리세요.
- 새 페이지가 늦게 잡히면:
  - `--min-stable-samples`를 낮추세요.
- OCR 품질이 낮으면:
  - `paddleocr` 사용 + 원본 영상 해상도 향상 권장.

## 문제 해결

- `No OCR engine available`:
  - `paddleocr`를 설치하거나
  - `tesseract`와 `pytesseract`를 함께 설치하세요.
- `No page frames were extracted`:
  - `--transition-threshold`를 낮추고 `--sample-fps`를 올려 재실행하세요.
