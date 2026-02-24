# run_extract.py
import os
import sys
import subprocess
import json
from pathlib import Path

def main():
    print(f"Current Python: {sys.executable}")
    
    # 1. 텍스트 추출 파이프라인 실행
    print("Starting video analysis and OCR extraction...")
    
    output_path = Path("output_final")
    input_video = Path("source/capture video.mp4")
    
    if not input_video.exists():
        print(f"❌ 오류: 입력 영상을 찾을 수 없습니다: {input_video}")
        return

    # 가상 환경의 파이썬을 정확히 호출하도록 sys.executable 사용
    cmd = [
        sys.executable, "-m", "video_to_text",
        "--input", str(input_video),
        "--output", str(output_path),
        "--ocr-lang", "kor+eng"
    ]
    
    try:
        # 진행 상황을 보기 위해 subprocess.run의 출력을 터미널에 그대로 노출
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"\n❌ 오류: 추출 프로세스 실행 중 문제가 발생했습니다 (종료 코드: {e.returncode})")
        print("💡 팁: 'python -m video_to_text --list-engines' 명령어로 엔진 설치 여부를 다시 확인해 보세요.")
        return
    except Exception as e:
        print(f"❌ 예상치 못한 오류 발생: {e}")
        return

    # 2. 추출된 텍스트를 하나의 파일로 통합 저장
    print("\nMerging text files...")
    ocr_dir = output_path / "ocr"
    combined_text_path = Path("전체_추출_텍스트.txt")

    if ocr_dir.exists():
        pages = sorted(ocr_dir.glob("*.json"))
        if not pages:
            print("⚠️ 경고: OCR 결과 JSON 파일이 생성되지 않았습니다.")
            return
            
        with open(combined_text_path, "w", encoding="utf-8") as f:
            for p in pages:
                try:
                    data = json.loads(p.read_text(encoding="utf-8"))
                    f.write(f"\n{'='*20} Page {data['page_number']} {'='*20}\n")
                    f.write(data['cleaned_text'] + "\n")
                except Exception as e:
                    print(f"⚠️ 페이지 {p.name} 읽기 오류: {e}")
                    
        print(f"Success! Merged text saved: {combined_text_path.absolute()}")
        print(f"Detailed results: {output_path.absolute()}")
    else:
        print("❌ 오류: 추출 결과 디렉토리가 생성되지 않았습니다.")

if __name__ == "__main__":
    main()
