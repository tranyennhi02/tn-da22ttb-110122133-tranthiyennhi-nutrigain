"""
Script tạo test dataset mẫu cho đánh giá CLIP.

Usage:
    python -m scripts.create_clip_test_dataset --output-dir data/clip_test_images --samples-per-ingredient 10
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                      HƯỚNG DẪN TẠO TEST DATASET CHO CLIP                    ║
╚══════════════════════════════════════════════════════════════════════════════╝

📁 CẤU TRÚC THƯ MỤC TEST:

data/clip_test_images/
├── Thit_bo/          # Ảnh thịt bò (10-20 ảnh)
│   ├── beef_1.jpg
│   ├── beef_2.jpg
│   └── ...
├── Thit_ga/          # Ảnh thịt gà (10-20 ảnh)
│   ├── chicken_1.jpg
│   └── ...
├── Ca_hoi/           # Ảnh cá hồi (10-20 ảnh)
│   ├── salmon_1.jpg
│   └── ...
├── Tom/              # Ảnh tôm (10-20 ảnh)
├── Cua/              # Ảnh cua (10-20 ảnh)
├── Trung/            # Ảnh trứng (10-20 ảnh)
├── Khoai_lang/       # Ảnh khoai lang (10-20 ảnh)
├── Khoai_tay/        # Ảnh khoai tây (10-20 ảnh)
├── Ca_rot/           # Ảnh cà rốt (10-20 ảnh)
├── Ca_chua/          # Ảnh cà chua (10-20 ảnh)
└── ...               # Các nguyên liệu khác

═══════════════════════════════════════════════════════════════════════════════

📝 YÊU CẦU ẢNH TEST:

1. ✅ Ảnh thật, chụp rõ ràng
2. ✅ Đa dạng góc nhìn (từ trên, từ bên, cận cảnh)
3. ✅ Đa dạng nguồn sáng (tự nhiên, đèn trong nhà)
4. ✅ Đa dạng nền (bàn gỗ, bát sứ, thớt)
5. ✅ Format: JPG, JPEG, hoặc PNG
6. ✅ Kích thước: Tối thiểu 300x300px, khuyến nghị 640x640px

═══════════════════════════════════════════════════════════════════════════════

🎯 CÁCH THU THẬP ẢNH:

Cách 1: Tự chụp ảnh
  - Chụp nguyên liệu từ tủ lạnh, chợ, siêu thị
  - Mỗi loại chụp 10-20 ảnh với góc độ khác nhau

Cách 2: Tải từ nguồn public
  - Unsplash: https://unsplash.com/s/photos/raw-chicken
  - Pexels: https://www.pexels.com/search/raw%20beef/
  - Google Images (lọc "free to use")

Cách 3: Sử dụng ảnh từ USDA FoodData Central
  - https://fdc.nal.usda.gov/

═══════════════════════════════════════════════════════════════════════════════

🚀 SAU KHI TẠO TEST DATASET:

1. Chạy đánh giá:
   cd backend
   python -m scripts.evaluate_clip_accuracy --test-dir ../data/clip_test_images

2. Xem kết quả:
   - JSON: results/clip_evaluation.json
   - CSV: results/clip_evaluation_details.csv

3. Phân tích kết quả:
   - Overall Accuracy: Độ chính xác tổng thể
   - Per-ingredient Accuracy: Độ chính xác từng loại nguyên liệu
   - Confusion Matrix: Ma trận nhầm lẫn (món nào bị nhận diện sai thành món nào)

═══════════════════════════════════════════════════════════════════════════════

💡 MẸO TỐI ƯU:

1. Bắt đầu với 5-7 loại nguyên liệu phổ biến nhất
2. Mỗi loại test 10-15 ảnh là đủ để đánh giá
3. Ưu tiên test các nguyên liệu dễ nhầm lẫn:
   - Thịt bò ⇔ Thịt lợn
   - Cá ⇔ Cá hồi
   - Khoai tây ⇔ Khoai lang
   - Cà chua ⇔ Cam

═══════════════════════════════════════════════════════════════════════════════
""")


def create_test_structure(output_dir: str) -> None:
    """Tạo cấu trúc thư mục test."""
    base_path = Path(output_dir)
    
    ingredients = [
        "Thit_bo", "Thit_lon", "Thit_ga", "Xuc_xich",
        "Ca", "Ca_hoi", "Tom", "Cua", "Hau", "So",
        "Trung", "Khoai_lang", "Khoai_tay", "Ca_rot", "Ca_chua",
        "Cam", "Chuoi", "Tao", "Sua", "Dau_hu", "Dau_nanh",
        "Yen_mach", "Rau_cai", "Bi_do", "Nam", "Com"
    ]
    
    for ingredient in ingredients:
        ingredient_path = base_path / ingredient
        ingredient_path.mkdir(parents=True, exist_ok=True)
        
        # Tạo file README trong mỗi thư mục
        readme_path = ingredient_path / "README.txt"
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(f"Thư mục chứa ảnh test cho: {ingredient}\n\n")
            f.write(f"Hãy thêm 10-20 ảnh JPG/PNG vào đây.\n")
            f.write(f"Ví dụ: {ingredient.lower()}_1.jpg, {ingredient.lower()}_2.jpg, ...\n")
    
    print(f"\n✅ Đã tạo cấu trúc thư mục test tại: {base_path.absolute()}")
    print(f"📁 Tổng số thư mục: {len(ingredients)}")
    print(f"\n👉 Tiếp theo: Thêm ảnh vào từng thư mục và chạy evaluation script")


def main():
    parser = argparse.ArgumentParser(
        description="Create test dataset structure for CLIP evaluation"
    )
    parser.add_argument(
        "--output-dir",
        default="data/clip_test_images",
        help="Output directory for test dataset (default: data/clip_test_images)"
    )
    
    args = parser.parse_args()
    
    create_test_structure(args.output_dir)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
