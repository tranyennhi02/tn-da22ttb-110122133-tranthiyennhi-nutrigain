# CLIP Accuracy Improvement Plan

**Baseline Accuracy**: 74.44%  
**Current Accuracy**: 76.26%
**Target Accuracy**: 85-90%

**ROUND 5 IMPROVEMENTS** (28/06/2026):
- **Cơm (50%)**: Thêm 25 prompts nhấn mạnh "soft wet rice grains" vs "dry solid potato"
- **Nấm (30%)**: Thêm 23 prompts nhấn mạnh "brown/white cap fungus" vs "red round tomato"
- **Đậu hũ (20%)**: Thêm 20 prompts nhấn mạnh "solid block with edges" vs "liquid milk"
- **Rau cải (60%)**: Thêm 17 prompts nhấn mạnh "green leaves with white stems"

**Strategy**: Focus on TEXTURE and STRUCTURE differences rather than just color/name variations.

Dựa trên kết quả evaluation, các nguyên liệu cần cải thiện:

---

## 📊 Phân Tích Chi Tiết Lỗi

### Nguyên liệu có vấn đề:

| Nguyên liệu | Accuracy | Vấn đề chính |
|-------------|----------|--------------|
| Bí đỏ | 0% | Nhầm thành Khoai lang (7/9), Cà rốt (1/9), Khoai tây (1/9) |
| Hàu | 0% | Recognition failed (10/10) |
| Sò | 0% | Recognition failed (9/10) |
| Thịt lợn | 20% | Chỉ 2/10 đúng, thiếu prompts |
| Đậu hũ | 20% | Nhầm thành Sữa (5/10), Khoai tây (3/10) |
| Nấm | 20% | Nhầm thành Cà chua (5/10), Khoai tây (2/10) |
| Đậu nành | 40% | Nhầm thành Sữa (3/10), Khoai tây (2/10) |
| Rau cải | 50% | Nhầm thành Cà chua (3/10), Khoai lang (2/10) |
| Cơm | 60% | Nhầm thành Khoai tây (4/10) |
| Thịt gà | 60% | Thiếu prompts cụ thể |
| Xúc xích | 60% | Nhầm thành Khoai tây (2/10), Khoai lang (1/10) |

---

## 🔧 Giải Pháp Cải Thiện

### 1. Thêm Prompts Cho Nguyên Liệu Yếu

#### A. Bí đỏ (0% → Target: 80%+)
**Vấn đề**: Nhầm toàn bộ thành củ (khoai lang, khoai tây, cà rốt)

**Giải pháp**: Thêm prompts nhấn mạnh màu cam đậm và hình dạng tròn

```python
"Bí đỏ": [
    "pumpkin",
    "pumpkin pieces",
    "squash",
    "pumpkin slices",
    "bí đỏ",
    # THÊM MỚI:
    "orange pumpkin",
    "orange squash",
    "winter squash",
    "butternut squash",
    "kabocha squash",
    "cubed pumpkin",
    "raw pumpkin",
    "fresh pumpkin",
    "whole pumpkin",
    "pumpkin chunks",
    "round orange pumpkin",
    "cooking pumpkin",
    "deep orange pumpkin",
    "a photo of orange pumpkin",
    "a photo of squash",
    "a raw ingredient photo of pumpkin",
    "a food ingredient photo of pumpkin",
    "a photo of pumpkin pieces",
    "a photo of cut pumpkin",
    "bi do",
    "bí đỏ nguyên quả",
    "bí đỏ thái khối",
    "bí ngô",
    "bi ngo",
    "bí đỏ cam",
    "bí đỏ tròn",
],
```

#### B. Thịt lợn (20% → Target: 70%+)
**Vấn đề**: Hiện chỉ có 29 prompts, cần thêm prompts cụ thể

```python
"Thịt lợn": [
    "pork",
    "raw pork",
    "fresh pork",
    "raw pork meat",
    "fresh pork meat",
    "pork slices",
    "raw pork slices",
    "pork loin",
    "pork tenderloin",
    "pork chop",
    "boneless pork",
    "lean pork",
    "pork meat",
    "raw pork loin",
    "a photo of raw pork",
    "a photo of raw pork slices",
    "a photo of fresh pork meat",
    "thịt lợn",
    "thit lon",
    "thịt lợn sống",
    "thit lon song",
    "miếng thịt lợn",
    "mieng thit lon",
    "thịt heo",
    "thit heo",
    "thịt heo sống",
    "thit heo song",
    "miếng thịt heo",
    "mieng thit heo",
    # THÊM MỚI:
    "pink pork meat",
    "pale pork meat",
    "raw pork on cutting board",
    "uncooked pork",
    "fresh raw pork",
    "pork belly",
    "pork shoulder",
    "ground pork",
    "pork cutlet",
    "sliced pork",
    "thin pork slices",
    "pork meat slices",
    "a photo of pork",
    "a photo of pork meat",
    "a raw ingredient photo of pork",
    "a food ingredient photo of pork",
    "a close-up photo of pork",
    "thịt lợn tươi",
    "thịt lợn thái lát",
    "thịt lợn xay",
    "ba chỉ lợn",
],
```

#### C. Đậu hũ (20% → Target: 70%+)
**Vấn đề**: Nhầm thành Sữa (màu trắng) và Khoai tây (hình khối)

```python
"Đậu hũ": [
    "tofu",
    "tofu blocks",
    "bean curd",
    "đậu hũ",
    "đậu phụ",
    # THÊM MỚI:
    "white tofu",
    "silken tofu",
    "firm tofu",
    "soft tofu",
    "fresh tofu",
    "raw tofu",
    "tofu cubes",
    "cubed tofu",
    "sliced tofu",
    "tofu pieces",
    "soybean curd",
    "pressed tofu",
    "tofu block on plate",
    "white bean curd",
    "a photo of tofu",
    "a photo of tofu blocks",
    "a photo of white tofu",
    "a raw ingredient photo of tofu",
    "a food ingredient photo of tofu",
    "dau hu",
    "dau phu",
    "đậu hũ trắng",
    "đậu hũ non",
    "đậu hũ già",
    "đậu hũ thái khối",
    "miếng đậu hũ",
],
```

#### D. Nấm (20% → Target: 70%+)
**Vấn đề**: Nhầm thành Cà chua (màu đỏ nấm rơm?) và Khoai tây

```python
"Nấm": [
    "mushroom",
    "mushrooms",
    "fresh mushrooms",
    "nấm",
    # THÊM MỚI:
    "white mushroom",
    "white mushrooms",
    "button mushroom",
    "button mushrooms",
    "cremini mushroom",
    "portobello mushroom",
    "shiitake mushroom",
    "oyster mushroom",
    "straw mushroom",
    "raw mushroom",
    "fresh button mushroom",
    "sliced mushroom",
    "whole mushroom",
    "mushroom caps",
    "edible mushroom",
    "cultivated mushroom",
    "a photo of mushrooms",
    "a photo of white mushrooms",
    "a photo of button mushrooms",
    "a raw ingredient photo of mushroom",
    "a food ingredient photo of mushroom",
    "nam",
    "nấm tươi",
    "nấm trắng",
    "nấm rơm",
    "nấm hương",
    "nấm đùi gà",
    "nấm nút",
    "nấm sống",
],
```

#### E. Đậu nành (40% → Target: 75%+)
**Vấn đề**: Nhầm thành Sữa và Khoai tây

```python
"Đậu nành": [
    "soybeans",
    "soy beans",
    "edamame",
    "soy bean ingredient",
    "đậu nành",
    # THÊM MỚI:
    "yellow soybeans",
    "dried soybeans",
    "raw soybeans",
    "fresh soybeans",
    "soybean seeds",
    "whole soybeans",
    "green soybeans",
    "edamame beans",
    "soya beans",
    "legume soybeans",
    "a photo of soybeans",
    "a photo of soy beans",
    "a photo of edamame",
    "a raw ingredient photo of soybeans",
    "a food ingredient photo of soybeans",
    "a close-up photo of soybeans",
    "dau nanh",
    "đậu nành khô",
    "đậu nành vàng",
    "đậu nành tươi",
    "hạt đậu nành",
    "đậu nành xanh",
],
```

#### F. Rau cải (50% → Target: 75%+)
**Vấn đề**: Nhầm thành Cà chua và Khoai lang

```python
"Rau cải": [
    "bok choy",
    "pak choi",
    "mustard greens",
    "leafy greens",
    "rau cải",
    "cải xanh",
    "cải thìa",
    # THÊM MỚI:
    "chinese cabbage",
    "napa cabbage",
    "green bok choy",
    "baby bok choy",
    "asian greens",
    "chinese greens",
    "fresh bok choy",
    "raw bok choy",
    "leafy vegetables",
    "green leafy vegetables",
    "cabbage greens",
    "green cabbage",
    "a photo of bok choy",
    "a photo of pak choi",
    "a photo of leafy greens",
    "a raw ingredient photo of bok choy",
    "a food ingredient photo of bok choy",
    "rau cai",
    "rau cải tươi",
    "cải ngọt",
    "cải bẹ xanh",
    "rau cải xanh",
    "cải bó xôi",
],
```

#### G. Cơm (60% → Target: 80%+)
**Vấn đề**: Nhầm thành Khoai tây (hạt trắng nhỏ?)

```python
"Cơm": [
    "rice",
    "cooked white rice",
    "a bowl of rice",
    "steamed rice",
    "white rice",
    "cơm trắng",
    "cơm",
    # THÊM MỚI:
    "cooked rice",
    "plain white rice",
    "jasmine rice",
    "long grain rice",
    "short grain rice",
    "fluffy rice",
    "steamed white rice",
    "rice in bowl",
    "bowl of white rice",
    "plate of rice",
    "rice grains",
    "sticky rice",
    "hot rice",
    "freshly cooked rice",
    "a photo of cooked rice",
    "a photo of white rice in bowl",
    "a food ingredient photo of rice",
    "a food ingredient photo of cooked rice",
    "com",
    "cơm nấu",
    "cơm chín",
    "cơm tẻ",
    "cơm nóng",
    "bát cơm",
    "đĩa cơm",
],
```

#### H. Hàu & Sò (0% - Recognition Failed)
**Vấn đề**: Nhận diện hoàn toàn thất bại, cần thêm nhiều prompts đa dạng

```python
"Hàu": [
    "oyster",
    "oysters",
    "fresh oysters",
    "raw oysters",
    "oyster shell",
    "oyster on half shell",
    "oyster meat",
    "shucked oyster",
    "pacific oyster",
    "rock oyster",
    "hàu sống",
    "hàu tươi",
    "hàu biển",
    "con hàu",
    "hàu",
    "hau song",
    "hau tuoi",
    # THÊM MỚI:
    "opened oyster",
    "oyster in shell",
    "half shell oyster",
    "fresh oyster on ice",
    "live oyster",
    "oyster seafood",
    "raw oyster on shell",
    "oyster mollusk",
    "shellfish oyster",
    "ocean oyster",
    "sea oyster",
    "edible oyster",
    "a photo of oysters",
    "a photo of raw oysters",
    "a photo of oyster shells",
    "a raw ingredient photo of oyster",
    "a food ingredient photo of oyster",
    "hau",
    "vỏ hàu",
    "hàu mở vỏ",
    "hàu tươi sống",
    "hàu biển sống",
],

"Sò": [
    "clam",
    "clams",
    "fresh clams",
    "shellfish clam",
    "manila clam",
    "littleneck clam",
    "sò",
    "nghêu",
    "so tuoi",
    "ngheu bien",
    # THÊM MỚI:
    "raw clams",
    "live clams",
    "clam shells",
    "clam shellfish",
    "ocean clams",
    "sea clams",
    "fresh shellfish clams",
    "opened clams",
    "clam meat",
    "edible clams",
    "clam seafood",
    "hard shell clams",
    "soft shell clams",
    "a photo of clams",
    "a photo of fresh clams",
    "a photo of clam shells",
    "a raw ingredient photo of clam",
    "a food ingredient photo of clam",
    "so",
    "ngheu",
    "sò tươi",
    "sò biển",
    "nghêu biển",
    "sò lông",
    "sò điệp",
],
```

---

## 🔄 Cách Áp Dụng

### Bước 1: Backup File Hiện Tại
```bash
copy d:\DOANTOTNGHIEP\NutriGain\backend\app\services\clip_ingredient_service.py d:\DOANTOTNGHIEP\NutriGain\backend\app\services\clip_ingredient_service.py.backup
```

### Bước 2: Mở File và Thêm Prompts
Mở file: `d:\DOANTOTNGHIEP\NutriGain\backend\app\services\clip_ingredient_service.py`

Tìm `INGREDIENT_PROMPT_GROUPS = {` (khoảng dòng 280-650)

Thay thế các prompts cũ bằng prompts mới ở trên cho từng nguyên liệu.

### Bước 3: Test Lại
```bash
cd backend
$env:HF_HOME="D:\DOANTOTNGHIEP\NutriGain\.cache\huggingface"
.\.venv\Scripts\python.exe -m scripts.evaluate_clip_accuracy --test-dir ../data/clip_test_images
```

---

## 📈 Dự Kiến Kết Quả Sau Cải Thiện

| Nguyên liệu | Hiện tại | Target | Cải thiện |
|-------------|----------|--------|-----------|
| Bí đỏ | 0% | 80%+ | +80% |
| Hàu | 0% | 60%+ | +60% |
| Sò | 0% | 60%+ | +60% |
| Thịt lợn | 20% | 70%+ | +50% |
| Đậu hũ | 20% | 70%+ | +50% |
| Nấm | 20% | 70%+ | +50% |
| Đậu nành | 40% | 75%+ | +35% |
| Rau cải | 50% | 75%+ | +25% |
| Cơm | 60% | 80%+ | +20% |
| **Overall** | **74.44%** | **85%+** | **+10.56%** |

---

## 🎯 Điều Chỉnh Thêm (Nếu Cần)

### Option 1: Tăng Confidence Threshold cho Nguyên Liệu Dễ Nhầm

Nếu sau khi thêm prompts mà vẫn có false positive, tăng threshold:

```python
# Trong file clip_ingredient_service.py, thêm vào đầu file:

INGREDIENT_SPECIFIC_THRESHOLDS = {
    "Bí đỏ": 0.28,  # Yêu cầu confidence cao hơn vì dễ nhầm với khoai
    "Đậu hũ": 0.27,  # Yêu cầu confidence cao hơn vì dễ nhầm với sữa
    "Nấm": 0.26,     # Yêu cầu confidence cao hơn vì dễ nhầm với cà chua
}
```

### Option 2: Thêm Validation Rules

Thêm logic kiểm tra đặc biệt cho các cặp dễ nhầm:

```python
def validate_ingredient_prediction(predicted_name, confidence, grouped_candidates):
    """Validate prediction to avoid common confusions"""
    
    # Nếu predict Bí đỏ nhưng Khoai lang cũng cao điểm → reject
    if predicted_name == "Bí đỏ":
        for candidate in grouped_candidates[:3]:
            if candidate['name'] in ['Khoai lang', 'Khoai tây', 'Cà rốt']:
                if confidence - candidate['score'] < 0.05:  # margin quá nhỏ
                    return False, "bi_do_confused_with_tuber"
    
    # Nếu predict Đậu hũ nhưng Sữa cũng cao điểm → reject
    if predicted_name == "Đậu hũ":
        for candidate in grouped_candidates[:3]:
            if candidate['name'] == 'Sữa':
                if confidence - candidate['score'] < 0.04:
                    return False, "tofu_confused_with_milk"
    
    return True, "ok"
```

---

## 📝 Ghi Chú

- Sau khi thêm prompts, PHẢI chạy lại evaluation để đo accuracy mới
- Nếu accuracy không cải thiện đủ, có thể cần thu thập thêm ảnh test chất lượng cao hơn
- Các nguyên liệu Hàu/Sò có thể cần model mạnh hơn (CLIP large) nếu vẫn thất bại

---

**File này chứa tất cả prompts cần thêm. Hãy áp dụng từng bước để cải thiện accuracy lên 85%+!**
