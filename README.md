# NutriGain

Hệ thống gợi ý món ăn tăng cân lành mạnh theo phương pháp lọc dựa trên nội dung (content-based filtering).

## Ý tưởng

Hệ thống sử dụng:

- Dữ liệu gốc để hiển thị thông tin món ăn cho người dùng
- Dữ liệu đã scale để tính toán độ tương đồng
- Cosine similarity để xếp hạng món ăn
- Hồ sơ người dùng để ước lượng nhu cầu dinh dưỡng mục tiêu

## Cấu trúc tệp

- `final_food_dataset_raw.csv`: dữ liệu món ăn dạng gốc, dễ đọc
- `final_food_dataset_scaled.csv`: dữ liệu đã chuẩn hóa dùng cho mô hình
- `nutrigain_recommender.py`: script chính của hệ thống gợi ý
- `user_history.csv`: tệp lịch sử thông tin người dùng và sở thích

## Cách hệ thống hoạt động

1. Đọc cả hai bộ dữ liệu (raw và scaled).
2. Ghép dữ liệu theo `food_id`.
3. Xây dựng vector dinh dưỡng mục tiêu từ hồ sơ người dùng (cân nặng, chiều cao, mức vận động, mục tiêu).
4. Đưa vector mục tiêu về cùng không gian đặc trưng đã scale.
5. Tính cosine similarity giữa người dùng và toàn bộ món ăn.
6. Trả về các món có điểm cao nhất, hiển thị bằng dữ liệu raw.

## Cập nhật an toàn và chính xác dinh dưỡng

Hệ thống đã được cập nhật theo hướng ưu tiên an toàn và tính chính xác của dinh dưỡng với các điểm chính:

- Allergy hard-filter: loại bỏ hoàn toàn các thực phẩm có từ khóa dị ứng trước khi xếp hạng.
- Energy tolerance pre-filter: chỉ giữ lại các thực phẩm có calories nằm trong sai số cho phép so với mục tiêu kcal trên mỗi slot của người dùng.
- Backtracking fallback: nếu danh sách hợp lệ bị rỗng sau khi lọc, hệ thống tự động nới lỏng ngưỡng theo nhiều mức và cuối cùng lấy nhóm món gần mục tiêu kcal nhất để tránh trả về rỗng.
- Re-ranking cơ bản: xếp hạng lại bằng điểm nền (similarity + calorie alignment + macro alignment), mặc định chưa cộng các tín hiệu nâng cao theo lịch sử/sở thích.

## Nhập dữ liệu người dùng

Bạn có thể nhập dữ liệu theo 2 cách:

- Chạy bằng tham số dòng lệnh (CLI): weight, height, activity, age, sex...
- Dùng chế độ tương tác với `--interactive` để nhập trực tiếp

Khi lưu dữ liệu với `--save-user-data` hoặc `--interactive`, hệ thống sẽ thêm bản ghi vào `user_history.csv`.

## Hướng dẫn lưu và học từ lịch sử

Lịch sử người dùng được dùng để học thêm sở thích theo nhóm món (category).

- Category được ưu tiên trong lịch sử sẽ được cộng điểm gợi ý
- Category bị loại trừ trong lịch sử sẽ bị trừ điểm gợi ý

Nhập dữ liệu mới và lưu lại sẽ giúp hệ thống phù hợp hơn với tập người dùng đã quan sát.

## Cách chạy

```bash
python nutrigain_recommender.py --weight 48 --height 162 --activity moderate --top-n 10
```

Lưu dữ liệu người dùng:

```bash
python nutrigain_recommender.py --weight 48 --height 162 --activity moderate --save-user-data --top-n 10
```

Chế độ tương tác:

```bash
python nutrigain_recommender.py --interactive --save-user-data --top-n 10
```

Tùy chọn thêm tuổi và giới tính:

```bash
python nutrigain_recommender.py --weight 48 --height 162 --activity moderate --age 21 --sex female --top-n 10
```

## Kết quả đầu ra

Script sẽ in ra:

- BMI ước lượng
- Calories duy trì (maintenance) ước lượng
- Calories mục tiêu để tăng cân lành mạnh
- Mục tiêu protein / fat / carbs
- Danh sách món gợi ý có điểm cao
- Thực đơn 1 ngày (Sáng 1 món, Trưa 2 món, Tối 2 món)
- Báo cáo đánh giá đơn giản:
  - So sánh calories mục tiêu và calories từ thực đơn gợi ý
  - Sai số calories tuyệt đối và sai số phần trăm
  - Precision theo preferred categories (nếu có)

Nếu có `user_history.csv`, hệ thống sẽ tự động dùng dữ liệu đã lưu để điều chỉnh trọng số category khi gợi ý.

## Phương pháp

Dự án áp dụng pipeline content-based filtering với cosine similarity. Tệp scaled dùng để tính độ tương đồng, còn tệp raw dùng để trình bày kết quả cho người dùng.

## Train model preference (ML)

Ngoài rule-based category preference, dự án đã hỗ trợ train model ML để học xu hướng thích/không thích category từ `user_history.csv`.

Chạy lệnh train:

```bash
python train_preference_model.py --history-path user_history.csv --raw-path final_food_dataset_raw.csv --output-path preference_model.joblib
```

Kết quả:

- Tạo file `preference_model.joblib`
- In báo cáo phân loại (precision/recall/f1)
- Backend tự nạp model này (nếu tồn tại) để cộng thêm tín hiệu học được vào điểm xếp hạng

Lưu ý:

- Nếu dữ liệu lịch sử quá ít, script sẽ tự train trên toàn bộ dữ liệu hiện có và báo rõ rằng validation split bị bỏ qua.
- Muốn chất lượng model ổn định hơn, nên có cả dữ liệu `preferred_categories` và `excluded_categories` từ nhiều user/session.

## Website MVC (React + FastAPI + MySQL + Docker)

Hệ thống web được tách theo mô hình MVC:

- Backend FastAPI:
  - Model: `backend/app/models/entities.py` (SQLAlchemy)
  - View: `backend/app/views/schemas.py` (Pydantic response/request schema)
  - Controller: `backend/app/controllers/recommendation_controller.py`
  - Service/Repository: xử lý nghiệp vụ và lưu dữ liệu trong `backend/app/services` và `backend/app/repositories`
- Frontend React:
  - Model: `frontend/src/models/recommendationModel.js`
  - Controller: `frontend/src/controllers/recommendationController.js`
  - View: `frontend/src/views/DashboardView.jsx`
- Database: MySQL lưu lịch sử yêu cầu và meal plan

### Chạy bằng Docker

Yêu cầu: đã cài Docker Desktop.

```bash
docker compose up --build
```

Sau khi chạy thành công:

- Frontend: http://localhost:5173
- Backend API docs: http://localhost:8000/docs
- MySQL: localhost:3307

### API chính

- `POST /api/v1/recommendations`: trả về target nutrition, top recommendations, meal plan 1 ngày, evaluation
- `GET /api/v1/recommendations/history`: lấy lịch sử đã lưu trong MySQL

## Nạp `foods_clean.csv` vào MySQL

Nếu bạn đã tạo sẵn bảng `foods` trên MySQL, chỉ cần cấu hình biến `DATABASE_URL` trỏ đúng về database đó, sau đó chạy script import:

```bash
cd backend
python app/scripts/import_foods_csv.py --dry-run
python app/scripts/import_foods_csv.py --truncate
```

Script sẽ đọc `foods_clean.csv` ở thư mục gốc project, kiểm tra cột bắt buộc, rồi chèn toàn bộ dữ liệu vào bảng `foods`. Nếu muốn giữ dữ liệu cũ thì bỏ `--truncate`.

## Pipeline xử lý dataset 3 bước

Luồng dữ liệu hiện tại được tổ chức theo 3 bước:

1. Chuẩn hóa & phân loại thực phẩm: làm sạch tên món, ép kiểu số, và gán category phù hợp để meal planner hiểu được.
2. Xây dựng cấu trúc bữa ăn: sinh `meal_template.json` với số slot và tỉ lệ calories cho từng bữa.
3. Sinh thực đơn theo nhu cầu năng lượng người dùng: dùng database đã import để tạo meal plan qua FastAPI/service.

Bạn có thể chạy toàn bộ pipeline bằng script mới:

```bash
cd backend
python app/scripts/process_food_dataset.py --dry-run
python app/scripts/process_food_dataset.py --truncate --weight 48 --height 162 --activity moderate --top-n 10
```

Script sẽ luôn xuất file `meal_template.json` ở thư mục gốc project. Nếu có cung cấp `--weight` và `--height`, nó sẽ sinh luôn thực đơn 1 ngày từ dataset đã nạp.