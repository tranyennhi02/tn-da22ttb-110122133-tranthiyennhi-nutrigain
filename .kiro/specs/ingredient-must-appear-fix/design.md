# Ingredient Must Appear Fix — Bugfix Design

## Overview

Hệ thống gợi ý thực đơn (recommender) hiện xử lý nguyên liệu bắt buộc của người dùng
như **soft constraint**: cố gắng đưa nguyên liệu vào thực đơn, nhưng bỏ qua âm thầm
(silent skip) nếu không tìm được món phù hợp hoặc không còn slot trống. Kết quả: người
dùng nhập "Thịt bò" và "Thịt lợn" nhưng nhận về thực đơn chỉ chứa một trong hai, kèm
cảnh báo *"Chưa tìm được món phù hợp cho: Thịt bò"*.

Bản fix này chuyển cơ chế thành **hard constraint** với ba thay đổi cốt lõi:

1. **Force-inject**: vòng injection loop phải thử tất cả cơ chế dự phòng trước khi bỏ qua
   — bao gồm nới lỏng ngưỡng chất lượng, mở rộng vùng tìm kiếm sang toàn bộ catalog,
   và **append** item vào slot mới thay vì `continue` khi tất cả slot đã đầy.
2. **Post-injection validator**: sau vòng injection, kiểm tra tường minh từng nguyên liệu
   bắt buộc; chỉ phát cảnh báo (soft) cho nguyên liệu thực sự không tồn tại trong DB —
   không phải cho nguyên liệu "không fit vào plan".
3. **Final coverage check** (line ~13130–13215): chỉ ghi `ingredientWarnings` cho
   nguyên liệu không tìm được trong toàn bộ food catalog, không phải do pipeline bỏ qua.

Hành vi hiện tại đối với người dùng không nhập nguyên liệu, scoring dinh dưỡng, alias
group mapping, và preference bonus **không thay đổi**.

---

## Glossary

- **Bug_Condition (C)**: Điều kiện kích hoạt bug — tồn tại ít nhất một nguyên liệu bắt buộc
  trong `required_ingredients` mà không xuất hiện trong bất kỳ món ăn nào của thực đơn
  được trả về, dù nguyên liệu đó có tồn tại trong food catalog.
- **Property (P)**: Hành vi đúng khi C(X) đúng — mọi nguyên liệu trong
  `required_ingredients` phải được bao phủ bởi ít nhất một `meal item` trong thực đơn kết
  quả.
- **Preservation**: Hành vi hiện tại không liên quan đến bug phải giữ nguyên — bao gồm
  gợi ý không nguyên liệu, scoring dinh dưỡng, alias mapping, preference bonus.
- **`isBugCondition(X)`**: Hàm giả mã kiểm tra xem input `X` có kích hoạt bug không.
- **`find_best_candidate_for_required_ingredient`**: Hàm tại line ~2512 trong
  `recommender_service.py` — tìm món ăn tốt nhất từ `candidate_pool` cho một nguyên liệu.
- **`ingredient_match_quality(item, ingredient)`**: Hàm trả về điểm chất lượng 0–5 xác định
  xem `item` có bao phủ `ingredient` không.
- **`INGREDIENT_ALIAS_GROUPS`**: Dict ánh xạ tên nguyên liệu sang canonical group key
  (vd: "Thịt heo" → "pork").
- **`_repair_missing_injected_items`**: Hàm cố gắng thay thế item không bắt buộc bằng item
  đã inject trước đó.
- **`missing_before_injection`**: Danh sách nguyên liệu bắt buộc chưa được bao phủ trước
  vòng injection.
- **`missing_after_injection`**: Danh sách nguyên liệu bắt buộc vẫn chưa được bao phủ sau
  vòng injection — trong trạng thái buggy, luôn có thể chứa nguyên liệu tồn tại trong DB.
- **`candidate_source` / `ranked`**: Tập hợp item ứng viên từ food catalog dùng trong
  vòng injection.
- **`ENABLE_HARD_INGREDIENT_COVERAGE`**: Env flag kiểm soát chế độ hard coverage.

---

## Bug Details

### Bug Condition

Bug xảy ra khi người dùng nhập ít nhất một nguyên liệu bắt buộc (`required_ingredients`)
và pipeline injection bỏ qua nguyên liệu đó vì một trong hai lý do:
- `find_best_candidate_for_required_ingredient` trả về `None` (không tìm được trong
  `candidate_source` với ngưỡng chất lượng hiện tại).
- Tất cả meal slot đã đầy item bắt buộc → điều kiện `swap_index is None` và
  `len(target_items) >= expected` → `continue` (bỏ qua hoàn toàn).

Kết quả: nguyên liệu tồn tại trong DB nhưng vẫn không xuất hiện trong thực đơn.

**Formal Specification:**

```
FUNCTION isBugCondition(X)
  INPUT: X của kiểu RecommendationInput
         (bao gồm X.required_ingredients: list[str] và X.result: MealPlan)
  OUTPUT: boolean

  // Bug xảy ra khi có ít nhất 1 nguyên liệu bắt buộc không được bao phủ trong kết quả,
  // mặc dù nguyên liệu đó tồn tại trong food catalog
  RETURN EXISTS ingredient IN X.required_ingredients WHERE
    ingredient_exists_in_catalog(ingredient)         // tồn tại trong DB
    AND NOT EXISTS meal IN X.result.meals WHERE
      ingredient_match_quality(meal_item, ingredient) >= 2.0  // nhưng không có trong thực đơn
END FUNCTION
```

### Examples

- **Ví dụ 1 — Bug kích hoạt (hai nguyên liệu)**:
  Người dùng nhập `["Thịt bò", "Thịt lợn"]`.
  Thực đơn trả về chỉ chứa "Thịt lợn". "Thịt bò" tồn tại trong catalog nhưng bị bỏ qua.
  Kết quả mong đợi: cả hai nguyên liệu đều có mặt trong thực đơn.

- **Ví dụ 2 — Bug kích hoạt (slot đầy)**:
  Người dùng nhập `["Thịt bò", "Cá hồi", "Thịt gà"]`. Sau khi inject "Cá hồi" và "Thịt
  gà", tất cả slot của tất cả bữa đã đầy bởi item bắt buộc. Pipeline bỏ qua "Thịt bò"
  với `continue`. Kết quả mong đợi: "Thịt bò" được append vào một bữa dưới dạng slot bổ
  sung.

- **Ví dụ 3 — Không phải bug (nguyên liệu không tồn tại trong DB)**:
  Người dùng nhập `["Nguyên liệu lạ XYZ"]`. Không tồn tại trong catalog.
  Hệ thống trả về cảnh báo "Chưa tìm được món phù hợp cho: Nguyên liệu lạ XYZ". **Đây là
  hành vi đúng** — không phải lỗi.

- **Ví dụ 4 — Không phải bug (không có nguyên liệu)**:
  Người dùng không nhập nguyên liệu. Hệ thống gợi ý dựa trên hồ sơ dinh dưỡng. **Hành vi
  giữ nguyên**, không bị ảnh hưởng.

---

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- Gợi ý thực đơn cho người dùng không nhập nguyên liệu phải tiếp tục hoạt động bình thường
  dựa trên hồ sơ dinh dưỡng và mục tiêu sức khỏe.
- Khi người dùng nhập một nguyên liệu duy nhất đã tồn tại trong DB, hệ thống phải tiếp
  tục đảm bảo nguyên liệu đó xuất hiện trong thực đơn như trước.
- `INGREDIENT_PREFERENCE_BONUS` và preference scoring cho nguyên liệu yêu thích phải tiếp
  tục boost điểm cho món chứa nguyên liệu ưa thích.
- Cân bằng dinh dưỡng (calories, protein, fat, carbs) theo hồ sơ người dùng phải tiếp
  tục được tính toán đúng sau khi fix.
- Alias group mapping qua `INGREDIENT_ALIAS_GROUPS` (vd: "Thịt heo" → "pork") phải tiếp
  tục nhận diện và ánh xạ đúng.

**Scope:**
Tất cả input KHÔNG kích hoạt `isBugCondition` — bao gồm người dùng không nhập nguyên
liệu, nguyên liệu không tồn tại trong catalog, và thực đơn đã đủ tất cả nguyên liệu —
phải cho kết quả tương đương với phiên bản hiện tại về cấu trúc và chất lượng.

**Lưu ý:** Hành vi đúng khi bug condition thỏa mãn (tất cả nguyên liệu phải xuất hiện
trong thực đơn) được mô tả chi tiết trong Correctness Properties bên dưới.

---

## Hypothesized Root Cause

Dựa trên phân tích source code tại `recommender_service.py`:

1. **Silent skip khi `best_candidate is None` (Bug Point #1 — line ~9496)**:
   Vòng injection gọi `find_best_candidate_for_required_ingredient` với `candidate_source`
   (tập hợp đã được lọc/ranking). Nếu kết quả `None`, có một fallback thứ hai lấy từ
   `candidate_objects_by_ingredient`, nhưng nếu cả hai đều `None` → `continue` thẳng, bỏ
   qua nguyên liệu. Không có fallback nới lỏng ngưỡng chất lượng hay tìm trong toàn bộ
   catalog.

2. **Silent skip khi slot đầy (Bug Point #1 — line ~9556)**:
   Sau khi không tìm được `swap_index` (không có item không bắt buộc để swap), code kiểm
   tra `len(target_items) < expected`. Nếu slot đã đầy → `continue`, bỏ qua hoàn toàn mà
   không append item vào slot bổ sung. Đây là nguyên nhân chính khi có nhiều nguyên liệu
   bắt buộc cùng lúc.

3. **Soft failure ở post-injection validation (Bug Point #2 — line ~9580–9600)**:
   `missing_after_injection` được tính sau vòng injection. Nếu không rỗng, chỉ set
   `ingredient_warning_data` với message cảnh báo, **không retry** với chiến lược khác,
   **không phân biệt** nguyên liệu không tìm được do pipeline skip vs. thực sự không có
   trong DB.

4. **Final coverage check không phân biệt nguyên nhân (Bug Point #3 — line ~13130–13215)**:
   Sau `_repair_missing_injected_items`, nếu vẫn thiếu, ghi
   `ingredientWarnings.message = "Chưa tìm được món phù hợp cho: ..."` — đánh đồng mọi
   nguyên nhân thiếu thành một cảnh báo duy nhất, không phân biệt "không có trong DB" với
   "pipeline đã bỏ qua do slot đầy".

---

## Correctness Properties

Property 1: Bug Condition — Tất cả nguyên liệu bắt buộc phải xuất hiện trong thực đơn

_For any_ input `X` where `isBugCondition(X)` trả về `true` (tồn tại ít nhất một nguyên
liệu bắt buộc trong food catalog nhưng không có trong thực đơn), the fixed
`recommend'(X)` SHALL đảm bảo rằng **TẤT CẢ** nguyên liệu trong `X.required_ingredients`
mà tồn tại trong food catalog đều xuất hiện trong ít nhất một `meal item` của thực đơn
được trả về, với `ingredient_match_quality(item, ingredient) >= 2.0`.

**Validates: Requirements 2.1, 2.2, 2.3**

---

Property 2: Preservation — Hành vi với input không kích hoạt bug

_For any_ input `X` where `isBugCondition(X)` trả về `false` (không nhập nguyên liệu,
nguyên liệu không tồn tại trong catalog, hoặc thực đơn đã đủ nguyên liệu), the fixed
`recommend'(X)` SHALL produce the same result as `recommend(X)`, preserving scoring dinh
dưỡng, alias group mapping, preference bonus, và cấu trúc thực đơn.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

---

## Fix Implementation

### Changes Required

Giả sử root cause analysis là đúng:

**File**: `backend/app/services/recommender_service.py`

**Điểm thay đổi chính**: Vòng injection loop (line ~9479–9570) và post-injection validator
(line ~9580–9600).

**Specific Changes**:

1. **Force-inject với fallback mở rộng (Bug Point #1 — thay thế hai `continue`)**:
   - Khi `best_candidate is None` sau cả hai bước tìm kiếm hiện tại, thêm bước thứ ba:
     tìm trong **toàn bộ food catalog** (`ranked` hoặc `all_food_items`) với ngưỡng chất
     lượng nới lỏng (chấp nhận `quality >= 1.0` thay vì `>= 2.0`).
   - Nếu vẫn `None` sau ba bước → **chỉ khi đó** mới ghi nhận nguyên liệu là không tìm
     được, không `continue` sớm.

2. **Append item khi slot đầy (Bug Point #1 — thay thế `continue` trong nhánh slot đầy)**:
   - Khi `swap_index is None` **và** `len(target_items) >= expected` (slot đầy), thay vì
     `continue`, **append** `injected_item` vào `target_items` của meal phù hợp nhất.
   - Scale kcal theo `slot_kcal` trước khi append để không phá vỡ cân bằng dinh dưỡng.
   - Đánh dấu `is_core = True` và `is_default_selected = True`.

3. **Post-injection validator phân biệt nguyên nhân (Bug Point #2)**:
   - Sau vòng injection, tính `missing_after_injection`.
   - Phân loại: `unavailable_in_catalog` (không tìm được sau ba bước fallback) vs.
     `skipped_by_pipeline` (lẽ ra phải được inject nhưng không được).
   - Với `skipped_by_pipeline`: **log lỗi rõ ràng** và không set `ingredientWarnings`
     (vì đây là lỗi pipeline, không phải lỗi người dùng).
   - Với `unavailable_in_catalog`: set `ingredientWarnings` với message thông báo cho
     người dùng rằng nguyên liệu không tìm được trong hệ thống.

4. **Final coverage check chỉ cảnh báo cho nguyên liệu thực sự không có trong DB
   (Bug Point #3 — line ~13200–13215)**:
   - Kiểm tra `ingredient_exists_in_catalog(ingredient)` trước khi ghi
     `ingredientWarnings`.
   - Chỉ ghi cảnh báo nếu nguyên liệu **không tồn tại** trong catalog.
   - Nếu nguyên liệu tồn tại trong catalog nhưng vẫn thiếu trong thực đơn → đây là lỗi
     pipeline, log ở mức `ERROR` để điều tra, không hiển thị cảnh báo sai cho người dùng.

5. **Bảo vệ hành vi hiện tại**:
   - Kiểm tra `if not selected_ingredients: return early` trước vòng injection giữ nguyên.
   - `INGREDIENT_ALIAS_GROUPS` mapping không thay đổi.
   - `ingredient_match_quality` không thay đổi ngưỡng mặc định — ngưỡng nới lỏng chỉ
     dùng trong fallback bước ba của vòng injection.
   - `_dedupe_selected_ingredients_globally` và `_repair_missing_injected_items` không
     thay đổi logic nội bộ.

---

## Testing Strategy

### Validation Approach

Chiến lược kiểm thử theo hai giai đoạn: **(1) Exploratory** — chạy test trên code CHƯA
SỬA để xác nhận bug xảy ra và hiểu root cause; **(2) Fix + Preservation checking** — sau
khi sửa, xác nhận bug đã được fix và hành vi không liên quan không thay đổi.

---

### Exploratory Bug Condition Checking

**Goal**: Tạo counterexample trực tiếp từ code hiện tại để xác nhận hai bug point trước
khi viết fix.

**Test Plan**: Mock `find_best_candidate_for_required_ingredient` và `candidate_pool` để
kiểm soát kịch bản; sau đó chạy vòng injection với state thực tế và assert nguyên liệu
thiếu.

**Test Cases**:

1. **Hai nguyên liệu, một bị bỏ qua** (sẽ fail trên code chưa sửa):
   Tạo `meal_plan_payload` với slot trống, `required_ingredients = ["Thịt bò", "Thịt lợn"]`.
   Mock `find_best_candidate_for_required_ingredient` trả về `None` cho "Thịt bò" và item
   hợp lệ cho "Thịt lợn". Assert rằng thực đơn kết quả **thiếu** "Thịt bò" → xác nhận
   Bug Point #1 (silent skip khi `None`).

2. **Tất cả slot đầy, nguyên liệu thứ ba bị bỏ qua** (sẽ fail trên code chưa sửa):
   Tạo `meal_plan_payload` với tất cả slot đã đầy item bắt buộc (len >= expected cho mọi
   meal). `required_ingredients = ["Thịt bò", "Cá hồi", "Thịt gà"]`. Assert rằng sau
   vòng injection, "Thịt bò" không xuất hiện trong thực đơn → xác nhận Bug Point #1
   (silent skip khi slot đầy).

3. **Post-injection warning không phân biệt nguyên nhân** (quan sát trên code chưa sửa):
   Quan sát rằng `ingredient_warning_data["missingIngredients"]` chứa cả nguyên liệu có
   trong DB và nguyên liệu không có trong DB sau khi injection bỏ qua → xác nhận Bug
   Point #2.

4. **Final coverage check ghi warning sai** (quan sát trên code chưa sửa):
   Gọi pipeline đầy đủ với `["Thịt bò", "Thịt lợn"]`. Quan sát response payload chứa
   `ingredientWarnings.message = "Chưa tìm được món phù hợp cho: Thịt bò"` dù "Thịt bò"
   tồn tại trong catalog → xác nhận Bug Point #3.

**Expected Counterexamples**:
- Thực đơn trả về thiếu ít nhất một nguyên liệu tồn tại trong catalog.
- `ingredientWarnings` chứa nguyên liệu có trong DB, phân loại sai là "không tìm được".

---

### Fix Checking

**Goal**: Xác nhận rằng với mọi input kích hoạt `isBugCondition`, phiên bản đã sửa trả
về thực đơn bao phủ TẤT CẢ nguyên liệu bắt buộc có trong catalog.

**Pseudocode:**

```
FOR ALL X WHERE isBugCondition(X) DO
  result := recommend'(X)
  FOR ALL ingredient IN X.required_ingredients DO
    IF ingredient_exists_in_catalog(ingredient) THEN
      ASSERT EXISTS item IN flatten(result.meals.items) WHERE
        ingredient_match_quality(item, ingredient) >= 2.0
    END IF
  END FOR
END FOR
```

---

### Preservation Checking

**Goal**: Xác nhận rằng với mọi input KHÔNG kích hoạt `isBugCondition`, phiên bản đã sửa
cho kết quả tương đương với phiên bản gốc.

**Pseudocode:**

```
FOR ALL X WHERE NOT isBugCondition(X) DO
  ASSERT recommend(X) ≈ recommend'(X)
  // "≈" nghĩa là: cùng cấu trúc meal plan, cùng nguyên liệu bắt buộc được bao phủ,
  // không thay đổi scoring dinh dưỡng, alias mapping, preference bonus
END FOR
```

**Testing Approach**: Property-based testing đặc biệt phù hợp cho preservation checking vì:
- Tự động sinh nhiều input đa dạng (có / không nguyên liệu, nguyên liệu alias, nhiều ngày).
- Bắt được edge case mà unit test thủ công dễ bỏ sót.
- Đảm bảo chắc chắn hơn rằng hành vi không thay đổi trên toàn bộ vùng input không bị bug.

**Test Cases**:

1. **Preservation — không nhập nguyên liệu**: Sinh ngẫu nhiên `required_ingredients = []`
   với profile dinh dưỡng đa dạng. Assert rằng thực đơn kết quả từ `recommend'` tương
   đương `recommend` về cấu trúc và cân bằng dinh dưỡng.

2. **Preservation — nguyên liệu alias**: Sinh input với nguyên liệu thuộc
   `INGREDIENT_ALIAS_GROUPS` (vd: "Thịt heo", "Bò", "Gà ta"). Assert rằng alias mapping
   hoạt động đúng cả trước và sau fix.

3. **Preservation — một nguyên liệu tìm được**: Sinh input `required_ingredients = [X]`
   với `X` chắc chắn có trong catalog. Assert rằng nguyên liệu vẫn được inject đúng như
   trước.

4. **Preservation — nguyên liệu không tồn tại trong catalog**: Sinh input với nguyên liệu
   không có trong DB. Assert rằng `ingredientWarnings` vẫn được set đúng như cũ, pipeline
   không crash.

---

### Unit Tests

- Test `find_best_candidate_for_required_ingredient` với `candidate_pool` rỗng → phải
  kích hoạt fallback mở rộng sang full catalog.
- Test injection loop khi `swap_index is None` và `len(target_items) >= expected` → phải
  append item, không `continue`.
- Test post-injection validator phân loại đúng `unavailable_in_catalog` vs.
  `skipped_by_pipeline`.
- Test final coverage check: nguyên liệu tồn tại trong catalog nhưng thiếu trong thực đơn
  → log ERROR, không set `ingredientWarnings`.
- Test edge case: `required_ingredients` rỗng → pipeline không thay đổi hành vi.

### Property-Based Tests

- Sinh ngẫu nhiên `required_ingredients` từ tập nguyên liệu tồn tại trong catalog; assert
  rằng `recommend'` luôn bao phủ tất cả nguyên liệu đó trong thực đơn.
- Sinh ngẫu nhiên `meal_plan_payload` với cấu hình slot đầy / không đầy; assert rằng sau
  injection, không có nguyên liệu tồn tại trong catalog nào bị bỏ qua.
- Sinh ngẫu nhiên input với `required_ingredients = []`; assert rằng kết quả của
  `recommend` và `recommend'` tương đương (preservation property).

### Integration Tests

- Test pipeline đầy đủ với hai nguyên liệu (`["Thịt bò", "Thịt lợn"]`): assert cả hai
  xuất hiện trong thực đơn kết quả, không có `ingredientWarnings`.
- Test pipeline với ba nguyên liệu và meal plan có ít slot: assert tất cả nguyên liệu
  xuất hiện, bao gồm item được append vào slot bổ sung.
- Test chuyển đổi giữa chế độ `ENABLE_HARD_INGREDIENT_COVERAGE = true` và `false`; assert
  hành vi đúng trong cả hai mode.
- Test với nguyên liệu alias ("Thịt heo" → "pork"): assert alias được nhận diện đúng và
  nguyên liệu xuất hiện trong thực đơn.
- Test regression: người dùng không nhập nguyên liệu → thực đơn được gợi ý bình thường,
  không bị ảnh hưởng bởi logic injection mới.
