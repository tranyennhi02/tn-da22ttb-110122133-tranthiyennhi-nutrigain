# CLIP Evaluation Scripts

Tập hợp các script để đánh giá độ chính xác của CLIP ingredient recognition.

---

## 📁 Files

| File | Mô tả |
|------|-------|
| `evaluate_clip_accuracy.py` | Script chính đánh giá độ chính xác CLIP |
| `create_clip_test_dataset.py` | Tạo cấu trúc thư mục test dataset |
| `quick_test_clip.py` | Test nhanh xem CLIP có hoạt động không |

---

## 🚀 Quick Start

### 1. Test CLIP có hoạt động không

```bash
cd backend
python -m scripts.quick_test_clip
```

**Output:**
```
✅ CLIP model loaded successfully!
✅ Recognition completed!
✅ Total ingredients supported: 25
```

### 2. Tạo test dataset structure

```bash
python -m scripts.create_clip_test_dataset --output-dir ../data/clip_test_images
```

**Kết quả:**
- Tạo 26 thư mục (mỗi thư mục = 1 loại nguyên liệu)
- Mỗi thư mục có file README.txt hướng dẫn

### 3. Thêm ảnh test

Thêm 10-20 ảnh JPG/PNG vào mỗi thư mục. Ví dụ:

```
data/clip_test_images/
├── Thit_bo/
│   ├── beef_raw_1.jpg
│   ├── beef_raw_2.jpg
│   ├── beef_steak_1.jpg
│   └── ... (10-20 ảnh)
├── Thit_ga/
│   ├── chicken_breast_1.jpg
│   └── ... (10-20 ảnh)
└── ...
```

### 4. Chạy evaluation

```bash
python -m scripts.evaluate_clip_accuracy --test-dir ../data/clip_test_images
```

**Output:**
- Console: Bảng kết quả tóm tắt
- JSON: `results/clip_evaluation.json`
- CSV: `results/clip_evaluation_details.csv`

---

## 📊 Metrics

### Overall Metrics
- **Accuracy**: % dự đoán đúng / tổng số ảnh
- **Total Images**: Tổng số ảnh test
- **Correct/Incorrect/Failed**: Số lượng từng loại

### Per-Ingredient Metrics
- **Accuracy**: Độ chính xác từng nguyên liệu
- **Avg Confidence**: Điểm tin cậy trung bình
- **Avg Processing Time**: Thời gian xử lý trung bình (ms)

### Confusion Matrix
Ma trận cho biết nguyên liệu nào bị nhầm lẫn với nguyên liệu nào.

---

## 🎯 Targets

| Metric | Target | Current |
|--------|--------|---------|
| Overall Accuracy | ≥ 88% | TBD |
| Protein Accuracy | ≥ 90% | TBD |
| Vegetable Accuracy | ≥ 85% | TBD |
| Processing Time | < 300ms | TBD |

---

## 📖 Documentation

Chi tiết đầy đủ xem tại: `docs/CLIP_EVALUATION.md`

---

## 🛠 Troubleshooting

### torch not installed
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

### CLIP model not loaded
```bash
# Kiểm tra
python -c "from app.services.clip_ingredient_service import get_clip_model; print(get_clip_model())"
```

### Accuracy quá thấp
1. Kiểm tra chất lượng ảnh test
2. Xem confusion matrix để biết nhầm lẫn gì
3. Điều chỉnh prompts hoặc thresholds

---

## 📝 Example Output

```
================================================================================
CLIP INGREDIENT RECOGNITION - EVALUATION RESULTS
================================================================================

📊 OVERALL RESULTS:
  Total Images: 150
  ✅ Correct: 135
  ❌ Incorrect: 12
  ⚠️  Failed: 3
  🎯 Accuracy: 91.84%

📋 PER-INGREDIENT RESULTS:
--------------------------------------------------------------------------------
Ingredient           Total    Correct    Accuracy     Avg Confidence
--------------------------------------------------------------------------------
Thịt bò              15       14         93.33%          0.3856
Thịt gà              15       15        100.00%          0.4123
Cá hồi               15       14         93.33%          0.3245
Tôm                  15       13         86.67%          0.3012
Khoai lang           15       14         93.33%          0.2987
--------------------------------------------------------------------------------
```

---

## 💡 Tips

1. **Bắt đầu nhỏ**: Test 5-7 nguyên liệu phổ biến nhất trước
2. **Đa dạng ảnh**: Nhiều góc nhìn, nguồn sáng khác nhau
3. **Ưu tiên dễ nhầm lẫn**: Test các cặp nguyên liệu dễ nhầm:
   - Thịt bò ⇔ Thịt lợn
   - Cá ⇔ Cá hồi
   - Khoai tây ⇔ Khoai lang
4. **Phân tích kỹ**: Xem confusion matrix và failed cases để cải thiện

---

## 🔗 Related

- `app/services/clip_ingredient_service.py`: CLIP service code
- `docs/CLIP_EVALUATION.md`: Full documentation
- `data/clip_test_images/`: Test dataset location
- `results/`: Evaluation results output
