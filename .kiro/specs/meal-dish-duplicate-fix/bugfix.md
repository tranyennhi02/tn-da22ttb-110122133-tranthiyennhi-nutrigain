# Bugfix Requirements Document

## Introduction

Trong một bữa ăn (meal) được tạo bởi hệ thống gợi ý thực đơn NutriGain, các món ăn có thể bị trùng nhau theo hai cách:

1. **Trùng tên (name duplication)**: Hai món ăn có tên quá giống nhau hoặc giống hệt nhau xuất hiện trong cùng một bữa. Ví dụ: "đậu phụ mềm" và "đậu phụ cứng" cùng xuất hiện trong bữa trưa, hoặc hai biến thể của cùng một loại thực phẩm (ví dụ: hai loại đậu hũ, hai loại gạo).

2. **Trùng ảnh (image duplication)**: Hai hoặc nhiều món ăn có ảnh đại diện giống hệt nhau trong cùng một bữa. Điều này xảy ra khi nhiều món có cùng `clean_category` nhận cùng một ảnh placeholder (ví dụ: cả "đậu phụ mềm" và "đậu phụ cứng" đều nhận `/images/placeholders/protein-plant.svg`).

Trải nghiệm người dùng bị ảnh hưởng tiêu cực vì giao diện hiển thị các món trùng nhau hoặc có cùng hình ảnh, khiến thực đơn trông không đa dạng và thiếu chuyên nghiệp.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN một bữa ăn được tạo và hai món ăn có tên ngữ nghĩa tương tự nhau (ví dụ: "đậu phụ mềm" và "đậu phụ cứng") THEN hệ thống cho phép cả hai cùng xuất hiện trong bữa đó, vì cơ chế deduplication (`seen_food_names`) chỉ kiểm tra khớp tên chính xác sau khi chuẩn hóa, không kiểm tra sự tương đồng ngữ nghĩa.

1.2 WHEN một bữa ăn chứa các món thuộc cùng nhóm ngữ nghĩa (semantic group, ví dụ: nhóm "tofu") THEN hệ thống sử dụng bộ lọc ngữ nghĩa (`selected_semantic_keys`) chỉ ở mức "prefer distinct" (ưu tiên khác nhau) chứ không phải hard constraint, cho phép bypass và thêm món trùng ngữ nghĩa khi pool không còn lựa chọn khác.

1.3 WHEN nhiều món ăn trong cùng một bữa thuộc cùng `clean_category` và không có ảnh thực (`image_source_type != "real"`) THEN hệ thống gán cho tất cả cùng một URL ảnh placeholder theo danh mục (ví dụ: tất cả đều nhận `/images/placeholders/protein-plant.svg`), vì không có cơ chế kiểm tra trùng `image_url` trong một bữa.

1.4 WHEN hàm fill (`_v_fill_to_8` hoặc vòng fill tới `SUGGESTIONS_PER_MEAL`) chạy để bổ sung các món tùy chọn (optional items) THEN hệ thống không kiểm tra trùng ảnh, dẫn đến việc nhiều optional items có cùng `image_url` xuất hiện trong cùng bữa.

### Expected Behavior (Correct)

2.1 WHEN một bữa ăn được tạo THEN hệ thống SHALL đảm bảo không có hai món ăn trong cùng bữa đó có cùng khóa ngữ nghĩa (`normalize_food_similarity_key`), áp dụng ngữ nghĩa deduplication như một hard constraint (không chỉ soft preference) trước khi thêm món vào bữa.

2.2 WHEN hệ thống chọn món cho mỗi slot trong một bữa THEN hệ thống SHALL loại khỏi pool bất kỳ món nào có semantic key đã xuất hiện trong bữa đó (`selected_semantic_keys`), thay vì chỉ ưu tiên tránh (`_prefer_semantic_distinct`).

2.3 WHEN nhiều món ăn trong cùng một bữa sử dụng ảnh placeholder (không phải ảnh thực) và có cùng URL ảnh placeholder THEN hệ thống SHALL đảm bảo không có hai món nào trong bữa đó có cùng `image_url`, bằng cách theo dõi các URL ảnh đã dùng trong bữa (`seen_meal_image_urls`) và bỏ qua món có ảnh trùng.

2.4 WHEN các optional items được điền vào bữa ăn (fill tới `SUGGESTIONS_PER_MEAL`) THEN hệ thống SHALL kiểm tra `image_url` của món được điền không trùng với bất kỳ món nào đã có trong bữa đó trước khi thêm vào.

### Unchanged Behavior (Regression Prevention)

3.1 WHEN pool ứng viên không có đủ món thỏa mãn điều kiện không trùng ngữ nghĩa hoặc không trùng ảnh THEN hệ thống SHALL CONTINUE TO thực hiện fallback để đảm bảo bữa ăn có đủ số lượng món yêu cầu (`requested_slots`), ưu tiên tránh trùng nhưng không để bữa thiếu món.

3.2 WHEN hai món ăn có tên khác nhau hoàn toàn và khóa ngữ nghĩa khác nhau (ví dụ: "cơm trắng" và "thịt gà") THEN hệ thống SHALL CONTINUE TO cho phép cả hai cùng xuất hiện trong bữa bình thường.

3.3 WHEN một món ăn có ảnh thực (`image_source_type == "real"` và `image_verified == True`) THEN hệ thống SHALL CONTINUE TO ưu tiên hiển thị ảnh thực đó bất kể các món khác trong bữa có cùng URL hay không.

3.4 WHEN hệ thống tạo thực đơn cross-meal (nhiều bữa trong ngày) THEN hệ thống SHALL CONTINUE TO áp dụng `seen_food_ids` và `seen_food_names` để tránh trùng món giữa các bữa trong ngày.

3.5 WHEN hệ thống tạo gợi ý phân vai (slot-based) cho các bữa ăn THEN hệ thống SHALL CONTINUE TO đảm bảo mỗi slot được điền đúng danh mục thực phẩm phù hợp (starch, protein, vegetable, extra) theo cấu trúc bữa ăn hiện tại.
