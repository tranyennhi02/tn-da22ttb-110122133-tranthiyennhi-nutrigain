#!/usr/bin/env python3
"""
Script test logic nhận diện Khoai tây vs Khoai lang
"""

def strip_accents(text):
    """Remove accents from text"""
    import unicodedata
    text = unicodedata.normalize('NFD', str(text or ""))
    return "".join(c for c in text if unicodedata.category(c) != "Mn").replace("đ", "d").replace("Đ", "D")


def normalize_text(text):
    """Normalize text giống như trong code"""
    import re
    text = str(text or "").lower()
    text = strip_accents(text)
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def has_strong_potato_signal(top_prompts):
    """Test tín hiệu khoai tây - logic đếm prompts"""
    potato_terms = [
        "potato", "potatoes", "raw potato", "fresh potato",
        "yellow potato", "white potato", "brown potato",
        "round potatoes", "oval potatoes", "pile of potatoes",
        "khoai tay", "cu khoai tay", "khoai tay vang"
    ]
    
    sweet_terms = [
        "sweet potato", "khoai lang", "purple sweet potato",
        "orange sweet potato", "long sweet potato"
    ]
    
    # Đếm số lượng prompts trong top 10
    potato_count = 0
    sweet_count = 0
    potato_score_sum = 0.0
    sweet_score_sum = 0.0
    
    for item in top_prompts[:10]:
        prompt = strip_accents(str(item.get("prompt", ""))).lower()
        score = float(item.get("score", 0) or 0)
        
        is_sweet = any(strip_accents(term).lower() in prompt for term in sweet_terms)
        is_potato = any(strip_accents(term).lower() in prompt for term in potato_terms)
        
        if is_sweet:
            sweet_count += 1
            sweet_score_sum += score
        elif is_potato:  # Only count as potato if NOT sweet
            potato_count += 1
            potato_score_sum += score
    
    # Nếu sweet nhiều hơn và điểm cao hơn, không phải potato signal
    if sweet_count >= potato_count and sweet_score_sum >= potato_score_sum:
        return False
    
    # Nếu có đủ potato prompts và điểm đủ cao
    if potato_count >= 3 and potato_score_sum >= 0.7:
        return True
    
    return False


def has_strong_sweet_potato_signal(top_prompts):
    """Test tín hiệu khoai lang"""
    sweet_terms = [
        "sweet potato", "sweet potatoes", "purple sweet potato",
        "red skin sweet potato", "orange sweet potato",
        "long sweet potato", "khoai lang"
    ]
    
    sweet_count = 0
    sweet_score_sum = 0.0
    
    for item in top_prompts[:10]:
        prompt = strip_accents(str(item.get("prompt", ""))).lower()
        score = float(item.get("score", 0) or 0)
        
        is_sweet = any(strip_accents(term).lower() in prompt for term in sweet_terms)
        if is_sweet:
            sweet_count += 1
            sweet_score_sum += score
    
    # Nếu có ít nhất 2 sweet prompts trong top 10 với tổng điểm >= 0.5
    if sweet_count >= 2 and sweet_score_sum >= 0.5:
        return True
    
    return False


def test_case_1():
    """Test Case 1: Ảnh khoai tây vàng/tròn - phải nhận Khoai tây"""
    print("\n=== TEST CASE 1: Ảnh khoai tây vàng/tròn ===")
    
    top_prompts = [
        {"ingredient": "Khoai tây", "prompt": "potato", "score": 0.32},
        {"ingredient": "Khoai tây", "prompt": "yellow potato", "score": 0.30},
        {"ingredient": "Khoai tây", "prompt": "round potatoes", "score": 0.28},
        {"ingredient": "Khoai lang", "prompt": "sweet potato", "score": 0.25},
        {"ingredient": "Cà rốt", "prompt": "carrot", "score": 0.20},
    ]
    
    strong_potato = has_strong_potato_signal(top_prompts)
    strong_sweet = has_strong_sweet_potato_signal(top_prompts)
    
    print(f"Strong Potato Signal: {strong_potato}")
    print(f"Strong Sweet Potato Signal: {strong_sweet}")
    print(f"Potato count: 3, Sweet count: 1")
    print(f"Potato score sum: 0.90, Sweet score sum: 0.25")
    print(f"Expected: Khoai tây")
    print(f"Logic: Should prefer potato due to strong potato signal (3 prompts vs 1)")
    
    assert strong_potato == True, "Should detect potato signal (3 potato prompts with total 0.90)"
    assert strong_sweet == False, "Should NOT detect sweet signal (only 1 prompt with 0.25)"
    print("✓ PASS: Có tín hiệu potato rõ, không có tín hiệu sweet rõ")


def test_case_2():
    """Test Case 2: Ảnh khoai lang vỏ đỏ/dài - phải nhận Khoai lang"""
    print("\n=== TEST CASE 2: Ảnh khoai lang vỏ đỏ/dài ===")
    
    top_prompts = [
        {"ingredient": "Khoai lang", "prompt": "sweet potato", "score": 0.33},
        {"ingredient": "Khoai lang", "prompt": "red skin sweet potato", "score": 0.31},
        {"ingredient": "Khoai lang", "prompt": "long sweet potato tubers", "score": 0.29},
        {"ingredient": "Khoai tây", "prompt": "potato", "score": 0.27},
        {"ingredient": "Cà rốt", "prompt": "carrot", "score": 0.22},
    ]
    
    strong_potato = has_strong_potato_signal(top_prompts)
    strong_sweet = has_strong_sweet_potato_signal(top_prompts)
    
    print(f"Strong Potato Signal: {strong_potato}")
    print(f"Strong Sweet Potato Signal: {strong_sweet}")
    print(f"Expected: Khoai lang")
    print(f"Logic: Should prefer sweet potato due to strong sweet signal")
    
    assert strong_potato == False, "Should NOT detect potato signal (blocked by sweet)"
    assert strong_sweet == True, "Should detect sweet potato signal"
    print("✓ PASS: Có tín hiệu khoai lang rõ")


def test_case_3():
    """Test Case 3: Prompt generic 'potato' không có sweet - phải nhận Khoai tây"""
    print("\n=== TEST CASE 3: Prompt generic 'potato' không có sweet ===")
    
    top_prompts = [
        {"ingredient": "Khoai tây", "prompt": "potato", "score": 0.30},
        {"ingredient": "Khoai tây", "prompt": "fresh potato", "score": 0.28},
        {"ingredient": "Khoai tây", "prompt": "a photo of potato", "score": 0.26},
        {"ingredient": "Cà rốt", "prompt": "carrot", "score": 0.24},
        {"ingredient": "Cà chua", "prompt": "tomato", "score": 0.22},
    ]
    
    strong_potato = has_strong_potato_signal(top_prompts)
    strong_sweet = has_strong_sweet_potato_signal(top_prompts)
    
    print(f"Strong Potato Signal: {strong_potato}")
    print(f"Strong Sweet Potato Signal: {strong_sweet}")
    print(f"Expected: Khoai tây")
    print(f"Logic: Generic 'potato' without 'sweet' should be Khoai tây")
    
    assert strong_potato == True, "Should detect potato signal"
    assert strong_sweet == False, "Should NOT detect sweet potato signal"
    print("✓ PASS: Generic potato nhận đúng Khoai tây")


def test_case_4():
    """Test Case 4: Điểm gần nhau nhưng có sweet signal - phải nhận Khoai lang"""
    print("\n=== TEST CASE 4: Điểm gần nhau nhưng có sweet signal ===")
    
    top_prompts = [
        {"ingredient": "Khoai lang", "prompt": "sweet potato", "score": 0.29},
        {"ingredient": "Khoai tây", "prompt": "potato", "score": 0.28},
        {"ingredient": "Khoai lang", "prompt": "orange sweet potato", "score": 0.27},
        {"ingredient": "Khoai tây", "prompt": "yellow potato", "score": 0.26},
    ]
    
    strong_potato = has_strong_potato_signal(top_prompts)
    strong_sweet = has_strong_sweet_potato_signal(top_prompts)
    
    print(f"Strong Potato Signal: {strong_potato}")
    print(f"Strong Sweet Potato Signal: {strong_sweet}")
    print(f"Potato count: 2, Sweet count: 2")
    print(f"Potato score sum: 0.54, Sweet score sum: 0.56")
    print(f"Expected: Khoai lang")
    print(f"Logic: Sweet prompts win with equal count but higher total score")
    
    # Khi có cả 2 signal với số lượng bằng nhau, sweet score cao hơn nên potato signal bị block
    assert strong_potato == False, "Potato signal should be blocked (sweet count equal but sweet score higher)"
    assert strong_sweet == True, "Should detect sweet potato signal (2 prompts with total 0.56)"
    print("✓ PASS: Sweet signal ưu tiên khi có số lượng bằng nhau nhưng điểm cao hơn")


def test_case_5():
    """Test Case 5: Chỉ có 'potato' trong top 20 prompts - phải nhận Khoai tây"""
    print("\n=== TEST CASE 5: Chỉ có 'potato' trong top prompts ===")
    
    top_prompts = [
        {"ingredient": "Khoai tây", "prompt": "potato", "score": 0.31},
        {"ingredient": "Khoai tây", "prompt": "raw potato", "score": 0.29},
        {"ingredient": "Khoai tây", "prompt": "pile of potatoes", "score": 0.27},
        {"ingredient": "Khoai tây", "prompt": "unpeeled potatoes", "score": 0.25},
        {"ingredient": "Khoai tây", "prompt": "potato tubers", "score": 0.24},
    ]
    
    strong_potato = has_strong_potato_signal(top_prompts)
    strong_sweet = has_strong_sweet_potato_signal(top_prompts)
    
    print(f"Strong Potato Signal: {strong_potato}")
    print(f"Strong Sweet Potato Signal: {strong_sweet}")
    print(f"Expected: Khoai tây")
    print(f"Logic: Only potato terms without sweet should strongly indicate potato")
    
    assert strong_potato == True, "Should strongly detect potato signal"
    assert strong_sweet == False, "Should NOT detect sweet potato signal"
    print("✓ PASS: Chỉ có potato terms nhận đúng Khoai tây")


if __name__ == "__main__":
    print("=" * 60)
    print("TEST LOGIC NHẬN DIỆN KHOAI TÂY VS KHOAI LANG")
    print("=" * 60)
    
    try:
        test_case_1()
        test_case_2()
        test_case_3()
        test_case_4()
        test_case_5()
        
        print("\n" + "=" * 60)
        print("✓ TẤT CẢ TEST CASE PASS!")
        print("=" * 60)
        print("\nKết luận:")
        print("- Logic phát hiện tín hiệu potato và sweet potato hoạt động đúng")
        print("- Generic 'potato' không bị nhầm thành Khoai lang")
        print("- Sweet potato signal ưu tiên khi rõ ràng")
        print("- Potato signal ưu tiên khi không có sweet signal")
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        exit(1)
