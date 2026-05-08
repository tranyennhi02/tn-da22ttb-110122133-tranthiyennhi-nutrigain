# NutriGain 🥗

> **NutriGain** là hệ thống web gợi ý thực đơn tăng cân lành mạnh cho người thiếu cân, kết hợp **React**, **FastAPI**, **MySQL**, **Docker** và thuật toán gợi ý dựa trên nội dung (**Content-based Filtering**).

<p align="left">
  <strong>Build Healthy Calories.</strong><br/>
  Cá nhân hóa mục tiêu dinh dưỡng, sinh thực đơn hằng ngày và theo dõi quá trình tăng cân khoa học.
</p>

---

## Mục lục

- [Giới thiệu](#giới-thiệu)
- [Tính năng nổi bật](#tính-năng-nổi-bật)
- [Kiến trúc công nghệ](#kiến-trúc-công-nghệ)
- [Luồng hoạt động chính](#luồng-hoạt-động-chính)
- [Thuật toán gợi ý](#thuật-toán-gợi-ý)
- [Cơ sở dữ liệu](#cơ-sở-dữ-liệu)
- [Cài đặt và chạy dự án](#cài-đặt-và-chạy-dự-án)
- [CLI và xử lý dữ liệu](#cli-và-xử-lý-dữ-liệu)
- [Cấu trúc thư mục](#cấu-trúc-thư-mục)
- [API chính](#api-chính)
- [Ghi chú phát triển](#ghi-chú-phát-triển)

---

## Giới thiệu

**NutriGain** được xây dựng nhằm hỗ trợ người thiếu cân thiết lập hồ sơ dinh dưỡng, tính toán nhu cầu năng lượng và nhận thực đơn tăng cân lành mạnh theo từng ngày.

Hệ thống sử dụng hồ sơ người dùng như cân nặng, chiều cao, tuổi, giới tính, mức độ vận động, mục tiêu tăng cân và các ràng buộc cá nhân để:

- ước lượng **BMI**, **BMR**, **TDEE**;
- xác định **calories mục tiêu**;
- tính mục tiêu **protein / fat / carbs**;
- lọc món không phù hợp;
- sinh thực đơn theo bữa;
- ghi nhận món đã ăn và theo dõi tiến độ.

---

## Tính năng nổi bật

### 1. Dashboard người dùng hiện đại

- Tổng quan calories, macro và tình trạng hồ sơ.
- Giao diện React + Tailwind CSS, responsive trên nhiều kích thước màn hình. Áp dụng phong cách thiết kế hiện đại (Glassmorphism) cho trải nghiệm người dùng cao cấp, đặc biệt tại các màn hình Đăng nhập và Onboarding.
- Các màn chính:
  - Tổng quan
  - Kế hoạch bữa ăn
  - Nhật ký ăn uống
  - Biểu đồ dinh dưỡng
  - Tài khoản
  - Thông báo
  - Hỗ trợ

### 2. Gợi ý thực đơn cá nhân hóa

- Sinh thực đơn dựa trên hồ sơ dinh dưỡng.
- Ưu tiên món phù hợp mục tiêu tăng cân lành mạnh.
- Hỗ trợ cấu trúc bữa ăn theo nhóm món:
  - tinh bột,
  - đạm,
  - rau/trái cây,
  - món phụ tăng năng lượng.

### 3. Theo dõi ăn uống

- Người dùng có thể đánh dấu món đã ăn.
- Hệ thống ghi nhận dữ liệu vào nhật ký ăn uống.
- Biểu đồ hỗ trợ theo dõi calories, macro, cân nặng và mức độ tuân thủ.

### 4. Cá nhân hóa theo sở thích

- Đánh dấu món yêu thích.
- Đánh dấu món không thích.
- Loại trừ món theo dị ứng hoặc từ khóa không mong muốn.
- Hỗ trợ học sở thích theo nhóm món thông qua lịch sử người dùng.

### 5. Kiểm định an toàn dinh dưỡng

- Chỉ sinh thực đơn tăng cân khi người dùng thuộc nhóm thiếu cân. Tích hợp cảnh báo y tế đối với các trường hợp suy dinh dưỡng nặng (BMI < 16).
- Loại bỏ món dị ứng bằng hard-filter.
- Kiểm tra độ lệch calories và macro. Áp dụng mức sàn năng lượng nghiêm ngặt (TDEE + 350 kcal) đảm bảo tăng cân an toàn.
- Hạn chế trùng nhóm món trong cùng ngày và chống lặp món qua các ngày liên tiếp (anti-repetition).
- Fallback linh hoạt để tránh trả danh sách rỗng.

---

## Kiến trúc công nghệ

NutriGain áp dụng mô hình **MVC mở rộng** kết hợp service/repository để tách biệt giao diện, nghiệp vụ và dữ liệu.

### Frontend

| Thành phần | Công nghệ |
|---|---|
| Framework | React + Vite |
| Styling | Tailwind CSS |
| State/UI logic | React state, controller layer |
| Giao diện chính | Dashboard, Meal Plan, Food Journal, Charts, Account |

### Backend

| Thành phần | Công nghệ |
|---|---|
| API framework | FastAPI |
| ORM | SQLAlchemy |
| Validation | Pydantic |
| Recommender | Python service layer |
| ML / ranking | Content-based filtering, cosine similarity |

### Database

| Thành phần | Công nghệ |
|---|---|
| Database | MySQL |
| Local port | `3307` |
| Dữ liệu lưu trữ | users, profiles, foods, meal plans, food logs |

### Deployment

| Thành phần | Công nghệ |
|---|---|
| Containerization | Docker |
| Orchestration | Docker Compose |

---

## Luồng hoạt động chính

```text
Người dùng nhập hồ sơ
        ↓
Hệ thống tính BMI / BMR / TDEE / kcal mục tiêu
        ↓
Kiểm tra điều kiện BMI và ràng buộc cá nhân
        ↓
Lọc món từ database foods
        ↓
Xếp hạng bằng content-based filtering
        ↓
Sinh meal plan trong ngày
        ↓
Lưu vào meal_plans -> meals -> meal_plan_items
        ↓
Người dùng check-in món đã ăn
        ↓
Ghi nhận vào food_logs -> food_log_items
```

### Phân biệt dữ liệu gợi ý và dữ liệu đã ăn

| Nhóm dữ liệu | Ý nghĩa |
|---|---|
| `meal_plan_items` | Món hệ thống gợi ý trong kế hoạch bữa ăn |
| `food_log_items` | Món người dùng đã xác nhận ăn trong nhật ký |

---

## Thuật toán gợi ý

NutriGain sử dụng **Content-based Filtering** với các bước chính:

1. Đọc dữ liệu món ăn dạng raw và scaled.
2. Ghép dữ liệu theo `food_id`.
3. Xây dựng vector dinh dưỡng mục tiêu từ hồ sơ người dùng.
4. Đưa vector mục tiêu về cùng không gian đặc trưng đã scale.
5. Tính **cosine similarity** giữa vector người dùng và vector món ăn.
6. Lọc món theo rule an toàn.
7. Xếp hạng lại theo:
   - similarity score,
   - độ phù hợp calories,
   - độ cân bằng macro,
   - nhóm món,
   - lịch sử yêu thích / không thích.

### Các rule quan trọng

| Rule | Mục đích |
|---|---|
| BMI gate & Medical Warning | Chỉ sinh thực đơn cho người thiếu cân. Hiện cảnh báo y tế và áp dụng sàn năng lượng nghiêm ngặt (TDEE + 350 kcal) cho BMI < 16 |
| Allergy hard-filter | Loại bỏ món có từ khóa dị ứng |
| Energy tolerance | Giữ món có kcal gần mục tiêu từng slot |
| Macro validation | Phát hiện macro bất thường và tối ưu mật độ protein |
| Duplicate group & item check | Hạn chế lặp món cùng nhóm và chống lặp món giữa các ngày |
| Backtracking fallback | Nới lỏng điều kiện khi danh sách hợp lệ quá ít |
| Image fallback | Dùng ảnh minh họa nếu thiếu ảnh thật |

---

## Cơ sở dữ liệu

Các bảng chính trong hệ thống:

| Bảng | Vai trò |
|---|---|
| `users` | Tài khoản người dùng |
| `user_profiles` | Hồ sơ dinh dưỡng |
| `foods` | Kho dữ liệu món ăn |
| `food_categories` | Nhóm thực phẩm |
| `recommendation_requests` | Lịch sử yêu cầu gợi ý |
| `meal_plans` | Kế hoạch thực đơn |
| `meals` | Các bữa trong kế hoạch |
| `meal_plan_items` | Món trong từng bữa |
| `food_logs` | Nhật ký ăn uống theo ngày |
| `food_log_items` | Món đã ăn |
| `food_ratings` | Đánh giá món ăn |
| `user_favorite_foods` | Món yêu thích |
| `user_disliked_foods` | Món không thích |

---

## Cài đặt và chạy dự án

### Yêu cầu

- Docker Desktop
- Node.js
- Python 3.11+
- MySQL hoặc MySQL container

### Chạy bằng Docker

Tại thư mục gốc dự án:

```bash
docker compose up --build
```

Nếu muốn chạy nền:

```bash
docker compose up -d --build
```

### Truy cập dịch vụ

| Dịch vụ | Địa chỉ |
|---|---|
| Frontend | [http://localhost:5173](http://localhost:5173) |
| Backend API Docs | [http://localhost:8000/docs](http://localhost:8000/docs) |
| MySQL | `localhost:3307` |

### Dừng hệ thống

```bash
docker compose down
```

---

## CLI và xử lý dữ liệu

NutriGain hỗ trợ các script CLI để nạp dữ liệu, xử lý dataset và huấn luyện model sở thích.

### Nạp dữ liệu món ăn vào MySQL

```bash
cd backend

python app/scripts/import_foods_csv.py --dry-run
python app/scripts/import_foods_csv.py --truncate
```

Nếu không muốn ghi đè dữ liệu cũ, bỏ `--truncate`.

### Xử lý dataset và sinh template

```bash
cd backend

python app/scripts/process_food_dataset.py --dry-run
python app/scripts/process_food_dataset.py --truncate --weight 48 --height 162 --activity moderate --top-n 10
```

Script này thực hiện:

1. chuẩn hóa tên món,
2. ép kiểu dữ liệu số,
3. gán nhóm món,
4. đánh dấu món hợp lệ,
5. sinh `meal_template.json`,
6. có thể sinh thử thực đơn theo hồ sơ mẫu.

### Huấn luyện preference model

```bash
python train_preference_model.py   --history-path user_history.csv   --raw-path final_food_dataset_raw.csv   --output-path preference_model.joblib
```

Sau khi train, backend có thể nạp `preference_model.joblib` để cộng thêm tín hiệu sở thích vào điểm xếp hạng.

---

## Cấu trúc thư mục

```text
NutriGain/
├── backend/                       # Backend FastAPI và logic gợi ý
│   ├── app/
│   │   ├── api/                   # REST endpoints
│   │   ├── controllers/           # Điều phối request
│   │   ├── models/                # SQLAlchemy entities
│   │   ├── repositories/          # Truy vấn database
│   │   ├── scripts/               # CLI import/xử lý dataset
│   │   ├── services/              # Recommender và nghiệp vụ
│   │   └── views/                 # Pydantic schemas
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/                      # Frontend React
│   ├── src/
│   │   ├── components/            # Component tái sử dụng
│   │   ├── controllers/           # Logic kết nối View - API
│   │   ├── models/                # Model/schema phía frontend
│   │   ├── utils/                 # Helper validate, format dinh dưỡng
│   │   └── views/                 # Dashboard, Login, Account
│   ├── Dockerfile
│   ├── package.json
│   └── tailwind.config.cjs
│
├── data/                          # Dataset gốc / đã xử lý
├── docker-compose.yml             # Cấu hình Docker Compose
└── README.md                      # Tài liệu dự án
```

---

## API chính

| Method | Endpoint | Mô tả |
|---|---|---|
| `POST` | `/api/v1/auth/register` | Đăng ký tài khoản |
| `POST` | `/api/v1/auth/login` | Đăng nhập |
| `POST` | `/api/v1/recommendations` | Sinh thực đơn theo hồ sơ |
| `GET` | `/api/v1/recommendations/history` | Lấy lịch sử gợi ý |
| `GET` | `/api/v1/meal-plans/today` | Lấy thực đơn hôm nay |
| `POST` | `/api/v1/meal-plan-items/{id}/check-in` | Đánh dấu món đã ăn |
| `GET` | `/api/v1/foods` | Lấy danh sách món ăn nếu endpoint được bật |

---

## Ghi chú phát triển

### Nguyên tắc dữ liệu

- `foods.id` là khóa chính dùng để liên kết giữa các bảng.
- `foods.food_id` là mã món từ dataset.
- `meal_plan_items` lưu món được hệ thống đề xuất.
- `food_log_items` lưu món người dùng đã ăn.
- `food_logs` không nên phụ thuộc trực tiếp vào `meal_plans`.

### Nguyên tắc giao diện người dùng

Giao diện người dùng nên tập trung vào:

- Tổng quan tiến độ.
- Kế hoạch bữa ăn.
- Nhật ký ăn uống.
- Biểu đồ dinh dưỡng.
- Tài khoản.
- Thông báo.
- Hỗ trợ.

Các phần như dataset, rule kiểm định, export hệ thống và quản lý món ăn nâng cao nên thuộc về giao diện admin.

---

## Định hướng mở rộng

Một số hướng phát triển tiếp theo:

- Tách riêng dashboard admin.
- Thêm API đổi mật khẩu.
- Bổ sung notification settings.
- Tối ưu thuật toán tránh món lặp nhiều ngày.
- Cải thiện chất lượng ảnh món ăn.
- Thêm báo cáo PDF cho quá trình tăng cân.
- Nâng cấp mô hình học sở thích khi dữ liệu người dùng đủ lớn.

---

## License

Dự án được phát triển phục vụ mục đích học tập, nghiên cứu và đồ án tốt nghiệp.

---

## Tác giả

**NutriGain** — Build Healthy Calories.