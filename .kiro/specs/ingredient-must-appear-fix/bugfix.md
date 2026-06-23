# Bugfix Requirements Document

## Introduction

Khi người dùng nhập một hoặc nhiều nguyên liệu (ví dụ: "Thịt bò", "Thịt lợn") để hệ thống gợi ý thực đơn, hệ thống hiện tại chỉ **ưu tiên** (soft constraint) các nguyên liệu đó thay vì **bắt buộc** (hard constraint) chúng xuất hiện trong kết quả.

Hậu quả: người dùng nhập "Thịt bò" và "Thịt lợn" nhưng thực đơn được gợi ý chỉ chứa "Thịt lợn", còn "Thịt bò" bị bỏ qua với thông báo *"Chưa tìm được món phù hợp cho: Thịt bò"*. Điều này vi phạm kỳ vọng của người dùng: tất cả nguyên liệu đã nhập phải xuất hiện trong thực đơn gợi ý.

---

## Bug Analysis

### Current Behavior (Defect)

Khi người dùng cung cấp danh sách nguyên liệu, hệ thống xử lý chúng như điều kiện tùy chọn (soft constraint) — tức là được tăng điểm ưu tiên nhưng không bắt buộc xuất hiện.

1.1 WHEN người dùng nhập nhiều nguyên liệu (ví dụ: ["Thịt bò", "Thịt lợn"]) THEN hệ thống chỉ đảm bảo ưu tiên một phần trong số đó, không đảm bảo tất cả đều xuất hiện trong thực đơn gợi ý

1.2 WHEN không tìm được món phù hợp chứa một nguyên liệu cụ thể (ví dụ: "Thịt bò") THEN hệ thống bỏ qua nguyên liệu đó và trả về thực đơn thiếu nguyên liệu, kèm thông báo "Chưa tìm được món phù hợp cho: Thịt bò"

1.3 WHEN hệ thống áp dụng `ENABLE_HARD_INGREDIENT_COVERAGE=true` THEN cơ chế hard coverage hiện tại vẫn không đảm bảo 100% nguyên liệu xuất hiện, chỉ cố gắng thay thế món (replacement) nếu có thể và bỏ qua nếu không tìm được

### Expected Behavior (Correct)

Tất cả nguyên liệu mà người dùng nhập phải được xem là **hard constraint** — thực đơn gợi ý bắt buộc phải chứa ít nhất một món có nguyên liệu đó trong mỗi ngày.

2.1 WHEN người dùng nhập nhiều nguyên liệu (ví dụ: ["Thịt bò", "Thịt lợn"]) THEN hệ thống SHALL đảm bảo TẤT CẢ nguyên liệu đó đều xuất hiện trong ít nhất một món ăn được gợi ý trong ngày

2.2 WHEN không tìm được món phù hợp chứa một nguyên liệu cụ thể từ database hiện có THEN hệ thống SHALL thông báo rõ ràng cho người dùng rằng nguyên liệu đó không thể được đáp ứng, thay vì âm thầm bỏ qua và trả về thực đơn không đầy đủ

2.3 WHEN hệ thống hoàn tất quá trình gợi ý thực đơn THEN hệ thống SHALL kiểm tra (validate) rằng mỗi nguyên liệu bắt buộc đều được bao phủ bởi ít nhất một món trong thực đơn trước khi trả về kết quả

### Unchanged Behavior (Regression Prevention)

Các hành vi hiện tại không liên quan đến bug phải được giữ nguyên sau khi sửa.

3.1 WHEN người dùng không nhập nguyên liệu nào THEN hệ thống SHALL CONTINUE TO gợi ý thực đơn bình thường dựa trên hồ sơ dinh dưỡng và mục tiêu sức khỏe

3.2 WHEN người dùng nhập một nguyên liệu duy nhất đã được tìm thấy trong database THEN hệ thống SHALL CONTINUE TO đảm bảo nguyên liệu đó xuất hiện trong thực đơn như hiện tại

3.3 WHEN hệ thống áp dụng preference scoring (INGREDIENT_PREFERENCE_BONUS) cho các nguyên liệu yêu thích THEN hệ thống SHALL CONTINUE TO boost điểm cho các món chứa nguyên liệu ưa thích của người dùng

3.4 WHEN thực đơn được gợi ý có đủ tất cả nguyên liệu bắt buộc THEN hệ thống SHALL CONTINUE TO tính toán và cân bằng mục tiêu dinh dưỡng (calories, protein, fat, carbs) theo hồ sơ người dùng

3.5 WHEN người dùng nhập nguyên liệu thuộc nhóm alias (ví dụ: "Thịt heo" → nhóm "pork") THEN hệ thống SHALL CONTINUE TO nhận diện và ánh xạ đúng nguyên liệu sang nhóm tương ứng qua `INGREDIENT_ALIAS_GROUPS`

---

## Bug Condition Pseudocode

### Bug Condition Function

```pascal
FUNCTION isBugCondition(X)
  INPUT: X của kiểu RecommendationInput
  OUTPUT: boolean
  
  // Bug xảy ra khi người dùng nhập từ 2 nguyên liệu trở lên
  // và ít nhất một nguyên liệu không xuất hiện trong thực đơn được trả về
  RETURN LENGTH(X.required_ingredients) >= 1
    AND EXISTS ingredient IN X.required_ingredients WHERE
      NOT EXISTS meal IN result.meals WHERE
        ingredient_covered(meal, ingredient)
END FUNCTION
```

### Property: Fix Checking

```pascal
// Property: Fix Checking — Tất cả nguyên liệu bắt buộc phải xuất hiện trong thực đơn
FOR ALL X WHERE isBugCondition(X) DO
  result ← recommend'(X)
  FOR ALL ingredient IN X.required_ingredients DO
    ASSERT EXISTS meal IN result.meals WHERE ingredient_covered(meal, ingredient)
  END FOR
END FOR
```

### Property: Preservation Checking

```pascal
// Property: Preservation Checking — Hành vi với input không trigger bug phải giữ nguyên
FOR ALL X WHERE NOT isBugCondition(X) DO
  ASSERT recommend(X) ≈ recommend'(X)  // kết quả tương đương về cấu trúc và chất lượng
END FOR
```
