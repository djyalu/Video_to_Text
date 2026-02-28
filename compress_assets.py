
import os
from PIL import Image
from pathlib import Path

def compress_images(input_dir, output_dir, quality=30, scale=0.6):
    """이미지를 최저 품질로 압축하고 크기를 줄여 파일 사이즈를 최소화합니다."""
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    print(f"Compressing images in {input_dir} (Quality: {quality}, Scale: {scale})...")
    
    total_size_before = 0
    total_size_after = 0

    for img_file in input_path.glob("*.jpg"):
        size_before = img_file.stat().st_size
        total_size_before += size_before
        
        with Image.open(img_file) as img:
            # 1. 흑백 전환 (텍스트 가독성은 유지하면서 색상 정보 제거)
            img = img.convert('L')
            
            # 2. 리사이즈 (가로 해상도 축소)
            new_width = int(img.width * scale)
            new_height = int(img.height * scale)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # 3. 압축 저장
            output_file = output_path / img_file.name
            img.save(output_file, "JPEG", quality=quality, optimize=True)
            
            size_after = output_file.stat().st_size
            total_size_after += size_after
            # print(f"  {img_file.name}: {size_before/1024:.1f}KB -> {size_after/1024:.1f}KB")

    print(f"\nCompression Result:")
    print(f"  Before: {total_size_before/1024/1024:.2f} MB")
    print(f"  After:  {total_size_after/1024/1024:.2f} MB")
    print(f"  Ratio:  {(1 - total_size_after/total_size_before)*100:.1f}% reduced")

if __name__ == "__main__":
    # pages -> pages_compressed
    compress_images("pages", "pages_compressed", quality=20, scale=0.5)
