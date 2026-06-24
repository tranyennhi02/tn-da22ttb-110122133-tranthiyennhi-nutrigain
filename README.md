
<div align="center">
  
# 🥗 NutriGain

### *Build Healthy Calories*

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.8-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.3-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev/)
[![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)

**Hệ thống gợi ý thực đơn tăng cân lành mạnh thông minh dành cho người thiếu cân**

Kết hợp AI, Machine Learning và khoa học dinh dưỡng để cá nhân hóa hành trình tăng cân an toàn

[Tính năng](#-tính-năng-nổi-bật) • [Demo](#-demo-screenshots) • [Cài đặt](#-cài-đặt-nhanh) • [Tài liệu](#-tài-liệu)

</div>

---

## 📑 Mục lục

- [Giới thiệu](#-giới-thiệu)
- [Vấn đề và Giải pháp](#-vấn-đề-và-giải-pháp)
- [Tính năng nổi bật](#-tính-năng-nổi-bật)
- [Demo Screenshots](#-demo-screenshots)
- [Kiến trúc hệ thống](#-kiến-trúc-hệ-thống)
- [Công nghệ sử dụng](#-công-nghệ-sử-dụng)
- [Thuật toán AI & ML](#-thuật-toán-ai--ml)
- [Cài đặt nhanh](#-cài-đặt-nhanh)
- [Tài liệu](#-tài-liệu)
- [Đóng góp](#-đóng-góp)

---

## 🌟 Giới thiệu

**NutriGain** là một hệ thống web application toàn diện được thiết kế đặc biệt để hỗ trợ người **thiếu cân** (BMI < 18.5) tăng cân một cách **lành mạnh** và **khoa học**.

### 🎯 Sứ mệnh

Trong khi thị trường công nghệ sức khỏe tập trung chủ yếu vào giảm cân, NutriGain hướng đến việc giải quyết vấn đề thiếu cân - một tình trạng ảnh hưởng đến hàng triệu người và có thể dẫn đến:

- 🦠 **Suy giảm hệ miễn dịch** - Tăng nguy cơ nhiễm trùng
- 💊 **Thiếu hụt dinh dưỡng** - Thiếu vitamin, khoáng chất thiết yếu
- 💪 **Giảm khối lượng cơ** - Ảnh hưởng sức mạnh và vận động
- 🦴 **Loãng xương** - Tăng nguy cơ gãy xương
- 😔 **Vấn đề tâm lý** - Lo âu, mất tự tin

### ⚡ Điểm khác biệt

- **🔬 Khoa học**: Áp dụng các công thức dinh dưỡng quốc tế (Mifflin-St Jeor, TDEE)
- **🤖 AI-Powered**: Tích hợp Machine Learning và CLIP model cho gợi ý thông minh
- **🎮 Gamification**: Hệ thống động lực hóa với EXP, Level, Achievement
- **🏥 An toàn y tế**: Cảnh báo refeeding syndrome cho BMI < 16
- **📊 Theo dõi chi tiết**: Dashboard, biểu đồ, báo cáo PDF

---

## 💡 Vấn đề và Giải pháp

### 🎯 Bài toán

**Người thiếu cân gặp phải những thách thức:**

| Thách thức | Hậu quả |
|------------|---------|
| Thiếu hướng dẫn cá nhân hóa | Khó xác định lượng calories phù hợp |
| Tăng cân không lành mạnh | Tích mỡ nội tạng từ junk food |
| Thiếu động lực duy trì | Quá trình kéo dài, dễ nản chí |
| Nguy cơ Refeeding Syndrome | BMI < 16 tăng cân quá nhanh gây sốc chuyển hóa |
| Khó lựa chọn thực phẩm | Không biết món nào giàu dinh dưỡng |

### ✨ Giải pháp của NutriGain

```mermaid
graph LR
    A[Người dùng] --> B[Nhập hồ sơ]
    B --> C[AI tính toán dinh dưỡng]
    C --> D[Gợi ý thực đơn cá nhân hóa]
    D --> E[Theo dõi tiến độ]
    E --> F[Gamification động viên]
    F --> G[Đạt mục tiêu tăng cân]
    
    style A fill:#e1f5ff
    style C fill:#fff4e1
    style D fill:#e8f5e9
    style G fill:#f3e5f5
```

**Quy trình 6 bước:**

1. **📝 Profile Setup**: Nhập thông tin cơ thể, mục tiêu, sở thích
2. **🧮 AI Calculation**: Tính BMI, BMR, TDEE, Target Calories & Macros
3. **🤖 Smart Recommendation**: ML + Content-based filtering gợi ý thực đơn
4. **🍽️ Meal Planning**: Thực đơn 4 bữa/ngày với món ăn đa dạng
5. **📊 Progress Tracking**: Theo dõi cân nặng, calories, macros
6. **🎮 Gamification**: Nhận EXP, Level Up, Unlock Achievements

---

## 🚀 Tính năng nổi bật

### 🎨 1. Giao diện người dùng hiện đại

- ✨ **Modern UI/UX**: React 18 + Tailwind CSS với Glassmorphism design
- 📱 **Fully Responsive**: Tối ưu cho desktop, tablet, mobile
- 🎨 **8 màn hình chính**:
  - 🏠 **Dashboard**: Tổng quan calories, macros, tiến độ tăng cân
  - 🍽️ **Meal Plans**: Kế hoạch bữa ăn với regenerate từng bữa riêng biệt
  - 📖 **Food Journal**: Nhật ký ăn uống chi tiết theo ngày
  - 📊 **Charts**: Biểu đồ cân nặng, nutrition trends
  - 👤 **Account**: Quản lý hồ sơ, mục tiêu, preferences
  - 🎮 **Gamification**: Streaks, achievements, levels
  - 🔔 **Notifications**: Nhắc nhở bữa ăn
  - 💬 **AI Chat**: Trợ lý AI tư vấn dinh dưỡng (đang phát triển)

### 🤖 2. AI-Powered Recommendation Engine

**Content-based Filtering với Cosine Similarity**

- 📊 **Cosine Similarity**: Tính độ tương đồng giữa vector dinh dưỡng người dùng và món ăn
- 🎯 **Smart Balancing**: Tự động cân bằng macros ±10% calories, ±15% protein/fat/carbs
- 🔄 **Anti-repetition**: Tránh lặp món giữa các ngày, hạn chế trùng nhóm món
- 🍎 **Ingredient Coverage**: Đảm bảo nguyên liệu yêu cầu xuất hiện đầy đủ
- 🧮 **Nutrition Targeting**: Tính toán chính xác BMR (Mifflin-St Jeor), TDEE, và calorie surplus phù hợp

### 👁️ 3. Nhận diện nguyên liệu bằng AI (CLIP)

- 📸 **Upload ảnh nguyên liệu**: Chụp tủ lạnh/nguyên liệu, tìm món phù hợp
- 🧠 **CLIP Model**: OpenAI's `clip-vit-base-patch32` với PyTorch
- 🎯 **High Accuracy**: Multi-threshold confidence scoring (High ≥0.25, Medium 0.18-0.24, Low 0.12-0.17)
- 🗳️ **Majority Voting**: Kết hợp nhiều prompts để tăng độ chính xác
- 🍳 **Smart Safety**: Validation gates chặt chẽ cho thịt/hải sản (score ≥0.34-0.36)
- ✅ **Ingredient Coverage**: Tự động sinh thực đơn từ nguyên liệu đã nhận diện

### 🎮 4. Gamification System

- ⭐ **EXP & Leveling**: Tích lũy điểm kinh nghiệm với công thức `100 × level`
  - Mark món đã ăn: +5 EXP
  - Check-in bữa ăn: +10-30 EXP (tùy bữa)
  - Log cân nặng: +15 EXP
  
- 🏆 **Achievement System**: 12+ huy hiệu mở khóa tự động
  - **Weight Milestones**: First Kilogram, Halfway There, Goal Achieved
  - **Consistency**: Week Warrior (7 ngày), Month Master (30 ngày)
  - **Meal Streaks**: Perfect Day (3 bữa chính/ngày), Meal Century (100 bữa)
  - **Food Variety**: Food Explorer (50 món), Variety King (100 món)
  
- 🔥 **Streak Counter**: Đếm ngày liên tục hoàn thành 3 bữa chính
- 💬 **Gentle Motivation**: Động viên tích cực, không áp lực

### 📊 5. Theo dõi tiến độ chi tiết

- 📈 **Weight Tracking**: 
  - Line chart với trend line & target line
  - Milestones (gộp 3-7 ngày)
  - Anti-fraud: Từ chối thay đổi >2kg/ngày
  
- 🍽️ **Consumption Tracking**:
  - Mark as Eaten cho từng món
  - Check-in cả bữa
  - Lịch sử món đã ăn
  
- 📉 **Statistics Dashboard**:
  - Current weight vs Starting weight
  - Weight change & Weekly average
  - Progress to goal (%)
  - Days tracking
  
- 📄 **Export PDF Report**: 
  - Biểu đồ cân nặng
  - Meal plans & eating history
  - Nutrition summary (jsPDF + html2canvas)

### 🔔 6. Smart Meal Reminders

- 📧 **SMS Reminders**: Tích hợp SMSGate API với JWT authentication
- ⏰ **Auto Scheduler**: Gửi nhắc nhở đúng giờ bữa ăn đã thiết lập
- 📝 **Reminder Log**: Lưu lịch sử sent/failed/skipped
- 🧪 **Test Feature**: Gửi test SMS kiểm tra cấu hình

### 🤝 7. Cá nhân hóa theo sở thích

- ❤️ **Favorite Foods**: Đánh dấu món yêu thích, ưu tiên trong gợi ý
- 👎 **Disliked Foods**: Loại bỏ món không thích
- 🚫 **Allergen Filter**: Hard-filter loại món dị ứng
- 💰 **Budget Constraint**: Lọc theo ngân sách (low/medium/high)
- 🥗 **Diet Type**: Vegetarian, High-protein, Balanced

### 🏥 8. An toàn y tế (Medical Safety)

- ⚠️ **BMI Gate (Asian Standards)**: Chỉ phục vụ người BMI < 23 (thiếu cân hoặc bình thường theo chuẩn Châu Á)
- 🚨 **Severe Underweight Warning**: Cảnh báo BMI < 16 nên theo dõi với chuyên gia dinh dưỡng
- 🛡️ **Ramp-up Phase**: Giới hạn calorie surplus cho BMI < 16 (max TDEE + 350 kcal)
- 🔒 **Weight Validation**: Từ chối cập nhật cân nặng thay đổi >2kg trong cùng ngày (water weight fluctuation safety)
- 🎯 **Target Weight Limit**: Không cho phép mục tiêu BMI ≥ 23 (giữ trong phạm vi underweight–normal)

### 👨‍💼 9. Admin Dashboard

- 📊 **Overview Stats**: Total users, active users, meal plans, weight logs
- 👥 **User Management**: Xem chi tiết profiles, meal plans, logs
- 🍕 **Food Management**: CRUD foods, upload ảnh, exclude/restore
- 📂 **Category Management**: Quản lý nhóm thực phẩm
- 📋 **Meal Plans**: Xem danh sách, test recommendation
- 🐛 **Error Logs**: System errors với filter & pagination
- 🔧 **Maintenance**: Recalculate EXP & achievements

---

## � Kiến trúc hệ thống

### 🏗️ High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     CLIENT LAYER                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │   React SPA (Frontend) - Port 5173                  │   │
│  │   • Lucide React Icons + Tailwind CSS                │   │
│  │   • React Router + State Management                  │   │
│  │   • Services Layer (API Client)                      │   │
│  └──────────────────────┬──────────────────────────────┘   │
└─────────────────────────┼────────────────────────────────────┘
                          │ HTTP/REST + JWT Bearer Token
┌─────────────────────────┼────────────────────────────────────┐
│                     API GATEWAY                              │
│  ┌──────────────────────┴──────────────────────────────┐   │
│  │   FastAPI Backend (Python 3.13) - Port 8000         │   │
│  │   • CORS Middleware + JWT Authentication            │   │
│  │   • Routes → Controllers → Services → Repositories   │   │
│  └──────────────────────┬──────────────────────────────┘   │
└─────────────────────────┼────────────────────────────────────┘
                          │ SQLAlchemy ORM
┌─────────────────────────┼────────────────────────────────────┐
│                     DATA LAYER                               │
│  ┌──────────────────────┴──────────────────────────────┐   │
│  │   MySQL 8.4 - Port 3306 (container) / 3307 (host)   │   │
│  │   • 25+ tables (users, foods, meal_plans, logs...)   │   │
│  │   • Indexes & Foreign Keys for performance           │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

### 🔄 Request Flow

## 🛠 Thuật toán AI & ML

### Content-based Filtering Engine

NutriGain sử dụng **Content-based Filtering** kết hợp với **vector similarity** để gợi ý thực đơn:

#### 1. Vector Construction
- Xây dựng vector dinh dưỡng từ hồ sơ người dùng (BMR, TDEE, target calories, macros)
- Chuẩn hóa vector món ăn về cùng không gian đặc trưng (scaled features)
- Features: calories, protein, fat, carbs, fiber, vitamin, mineral, food category

#### 2. Similarity Scoring
- **Cosine Similarity**: Tính độ tương đồng giữa user vector và food vectors
- Xếp hạng món ăn theo similarity score
- Áp dụng diversity jitter (0.18) để tăng đa dạng

#### 3. Rule-based Filtering
| Rule | Mục đích |
|---|---|
| **BMI Gate** | Chỉ hỗ trợ người BMI < 23 (Asian BMI standards: underweight + normal range) |
| **Medical Warning** | Cảnh báo + giới hạn surplus cho BMI < 16 (TDEE + 350 kcal max) |
| **Allergy Hard-filter** | Loại bỏ 100% món chứa allergen |
| **Energy Tolerance** | ±10% calories target per meal slot |
| **Macro Balance** | ±15% protein/fat/carbs target |
| **Anti-repetition** | Chống lặp món giữa các ngày, limit group duplication |
| **Category Balance** | Đảm bảo đủ tinh bột/protein/rau/trái cây mỗi bữa |
| **Ingredient Coverage** | Ưu tiên món có nguyên liệu yêu cầu (must-have ingredients) |

#### 4. Personalization Layers
- **Favorite Foods**: Boost score +18% cho món yêu thích
- **Disliked Foods**: Loại bỏ món không thích
- **Diet Type**: Áp dụng filter cho vegetarian/eat-clean/high-protein
- **Budget Constraint**: Lọc theo ngân sách (low/medium/high)

#### 5. CLIP-based Ingredient Recognition
- **Model**: OpenAI `clip-vit-base-patch32`
- **Confidence Thresholds**:
  - High: ≥0.25 (auto-accept)
  - Medium: 0.18-0.24 (suggest with warning)
  - Low: 0.12-0.17 (manual confirmation)
- **Majority Voting**: Combine 10+ prompts per ingredient
- **Safety Gates**: Strict validation for meat/seafood (0.34-0.36 min score)
- **Supported Ingredients**: 25+ types (thịt bò, gà, lợn, cá hồi, tôm, cua, trứng, khoai, rau, trái cây...)

### Nutrition Calculation Service

#### BMR Formula (Mifflin-St Jeor)
```
Nam: BMR = 10×weight(kg) + 6.25×height(cm) - 5×age(years) + 5
Nữ: BMR = 10×weight(kg) + 6.25×height(cm) - 5×age(years) - 161
```

#### TDEE Calculation
```
TDEE = BMR × Activity Multiplier
- sedentary: 1.2
- lightly_active: 1.375
- moderately_active: 1.55
- very_active: 1.725
- extremely_active: 1.9
```

#### Calorie Surplus Strategy
```
slow (chậm): TDEE + 250 kcal
moderate (vừa phải): TDEE + 500 kcal
fast (nhanh): TDEE + 750 kcal

Special case BMI < 16: max TDEE + 350 kcal (ramp-up phase)
```

#### Macro Distribution
```
Protein: 1.6-2.0g/kg body weight
Fat: 25-35% total calories
Carbs: Remaining calories after protein + fat
```

---

## 🏗 Kiến trúc hệ thống

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     CLIENT LAYER                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │   React SPA (Frontend) - Port 5173                  │   │
│  │   • Lucide React Icons + Tailwind CSS                │   │
│  │   • React Router + Context API State                 │   │
│  │   • Recharts + jsPDF Export                          │   │
│  └──────────────────────┬──────────────────────────────┘   │
└─────────────────────────┼────────────────────────────────────┘
                          │ HTTP/REST + JWT Bearer Token
┌─────────────────────────┼────────────────────────────────────┐
│                     API GATEWAY                              │
│  ┌──────────────────────┴──────────────────────────────┐   │
│  │   FastAPI Backend (Python 3.13) - Port 8000         │   │
│  │   • JWT Authentication + bcrypt hashing              │   │
│  │   • Routes → Controllers → Services → Repositories   │   │
│  │   • CLIP Model (PyTorch) + Recommender Engine       │   │
│  └──────────────────────┬──────────────────────────────┘   │
└─────────────────────────┼────────────────────────────────────┘
                          │ SQLAlchemy ORM
┌─────────────────────────┼────────────────────────────────────┐
│                     DATA LAYER                               │
│  ┌──────────────────────┴──────────────────────────────┐   │
│  │   PostgreSQL 15+ (hoặc MySQL 8.4+)                   │   │
│  │   • 25+ tables (users, foods, meal_plans, logs...)   │   │
│  │   • Composite indexes for performance                │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

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

## Cách chạy dự án

### Yêu cầu

- Docker Desktop
- Node.js
- Python 3.11+
- MySQL hoặc MySQL container

### Cách A: Docker deploy/dev

Docker vẫn là flow deploy/dev chính của dự án. Không xóa hoặc đổi `Dockerfile`, `docker-compose.yml`.

Tại thư mục gốc dự án:

```bash
docker compose up --build
```

Hoặc dùng script PowerShell:

```powershell
.\scripts\dev-docker.ps1
```

Nếu muốn chạy nền:

```bash
docker compose up -d --build
```

Docker mode frontend proxy dùng `http://backend:8000`, còn DB trong container dùng `db:3306`.

### Cách B: Local dev không Docker

Local dev dùng backend chạy bằng `uvicorn`, frontend chạy bằng `npm run dev`.

Chuẩn bị env mẫu:

```powershell
Copy-Item .env.local.example .env
```

Trong `.env`, cấu hình database local:

```env
DATABASE_URL=mysql+pymysql://nutrigain:<password>@127.0.0.1:3306/food_recommender
VITE_API_TARGET=http://127.0.0.1:8000
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Nếu bạn dùng MySQL Docker expose ra host thì đổi `DATABASE_URL` sang `127.0.0.1:3307`. Nếu dùng MySQL local thật thì giữ `127.0.0.1:3306`.

Quy tắc môi trường:

- Frontend Docker không dùng `127.0.0.1:8000` để gọi backend.
- Frontend local dùng `127.0.0.1:8000`.

Chạy local:

```powershell
.\scripts\dev-local.ps1
```

Script này sẽ mở 2 terminal:

- Backend: `cd backend`, activate `..\.venv-1\Scripts\activate`, chạy `python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 --log-level debug`.
- Frontend: `cd frontend`, chạy `npm run dev`.

### Cấu hình database

| Trường hợp | Host trong config | Ghi chú |
|---|---|---|
| Docker backend -> Docker DB | `db:3306` | Dùng trong container, ví dụ `.env.docker.example`. |
| Host machine -> Docker DB | `127.0.0.1:3307` | `docker-compose.yml` map `${DB_PORT:-3307}:3306`. |
| Local backend -> Local MySQL | `127.0.0.1:3306` | Khuyến nghị cho local dev ổn định khi Docker Desktop hay lỗi. |

Nếu muốn backend local dùng DB container Docker, đổi `DATABASE_URL` thành:

```env
DATABASE_URL=mysql+pymysql://nutrigain:<password>@127.0.0.1:3307/food_recommender
```

Lưu ý: nếu Docker Desktop chết thì DB container cũng chết. Local dev ổn định nên dùng MySQL local tại `127.0.0.1:3306`.

### Chạy tính năng nhận diện ảnh AI (CLIP) local

Tính năng nhận diện nguyên liệu từ ảnh sử dụng CLIP model cần thêm PyTorch. Để cài đặt nhanh:

**Cách 1: Dùng script tự động (Windows)**
```powershell
cd backend
.\install-clip-cpu.bat
```

**Cách 2: Cài thủ công**
```bash
# CPU-only (nhẹ hơn, khuyến nghị cho local dev)
python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Hoặc GPU (CUDA 11.8)
python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

Sau khi cài xong, restart backend. Kiểm tra log:
```
[CLIP ENABLED] Ingredient image recognition enabled
[CLIP MODEL LOADING] model=openai/clip-vit-base-patch32
[CLIP MODEL STATUS] loaded=True
[CLIP TEXT PROMPTS BUILT]
[CLIP WARMUP DONE]
```

Nếu thiếu torch, backend sẽ báo:
```
[CLIP UNAVAILABLE] PyTorch not installed. Install with: pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

Và khi upload ảnh sẽ trả message:
```
"Thiếu thư viện torch nên chưa thể nhận diện ảnh. Vui lòng cài dependency hoặc nhập thủ công."
```


### Truy cập dịch vụ

| Dịch vụ | Địa chỉ |
|---|---|
| Frontend | [http://localhost:5173](http://localhost:5173) |
| Backend API Docs | [http://localhost:8000/docs](http://localhost:8000/docs) |
| MySQL local | `127.0.0.1:3306` |
| MySQL Docker DB từ host machine | `127.0.0.1:3307` |

### Dừng hệ thống

```bash
docker compose down
```

---

## Thiết lập CI/CD và Deploy tự động

Dự án NutriGain được tích hợp sẵn hệ thống **CI/CD hoàn chỉnh** qua **GitHub Actions**. Hệ thống sẽ tự động kiểm tra code (lint/build), đóng gói Docker và deploy trực tiếp lên máy chủ Linux (Production Server) của bạn khi có thay đổi trên nhánh `main`.

### Luồng Hoạt Động của Pipeline

1. **Backend Check**: Cài đặt dependencies, tự động chạy kiểm tra compile (`python -m compileall`).
2. **Frontend Check**: Cài đặt node modules bằng `npm ci` và biên dịch production build (`npm run build`).
3. **Docker Build Check**: Kiểm tra tính hợp lệ của cấu trúc `docker compose config` và thử nghiệm đóng gói container (`docker compose build`) để loại bỏ rủi ro vỡ build trên server.
4. **Automated Deploy (chỉ chạy trên push to main)**: Kết nối an toàn qua SSH vào server, pull code mới, tự động sinh tệp `.env` cấu hình từ GitHub Secrets, tái khởi động các container (`docker compose up -d --build`) và kiểm tra độ phản hồi thông qua Post-Deployment Health Check (`/api/v1/health`).

### Danh sách GitHub Repository Secrets cần cấu hình

Để kích hoạt tính năng deploy tự động, hãy truy cập kho lưu trữ GitHub của bạn: `Settings` -> `Secrets and variables` -> `Actions` -> `New repository secret` và thêm các biến sau:

| Secret Key | Giá trị mẫu | Ý nghĩa |
|---|---|---|
| `SERVER_HOST` | `123.45.67.89` | Địa chỉ IP Public của VPS/Server |
| `SERVER_USER` | `root` hoặc `ubuntu` | Tên tài khoản SSH của Server |
| `SERVER_SSH_KEY` | `-----BEGIN OPENSSH PRIVATE KEY-----...` | Khóa SSH Private dùng để xác thực không mật khẩu |
| `SERVER_PORT` | `22` | Cổng SSH trên server (mặc định: 22) |
| `MYSQL_DATABASE` | `food_recommender` | Tên cơ sở dữ liệu MySQL |
| `MYSQL_USER` | `nutrigain` | Tài khoản kết nối MySQL |
| `MYSQL_PASSWORD` | `your_secure_password` | Mật khẩu truy cập MySQL |
| `MYSQL_ROOT_PASSWORD` | `your_root_password` | Mật khẩu tài khoản Root MySQL |
| `JWT_SECRET_KEY` | `6c1071424b9e782e4e16...` | Chuỗi ký tự bảo mật cho JWT (sinh bằng `openssl rand -hex 32`) |
| `BACKEND_PORT` | `8000` | Cổng Public cho backend API (mặc định: 8000) |
| `FRONTEND_PORT` | `5173` | Cổng Public cho frontend (mặc định: 5173) |
| `VITE_API_BASE_URL` | `http://123.45.67.89:8000` | URL API công khai của API để Frontend kết nối |
| `APP_ENV` | `production` | Môi trường ứng dụng (`production` / `development`) |

### Chuẩn bị Máy Chủ (Server) trước khi Deploy

Trước khi chạy deploy lần đầu tiên, hãy đảm bảo rằng:
1. Server đã được cài đặt sẵn **Docker** và **Docker Compose**.
2. Người dùng SSH có quyền chạy lệnh `docker` và `git` không cần `sudo` (hoặc cấu hình docker daemon không sudo).
3. Đã tạo sẵn thư mục `~/NutriGain` trên máy chủ, hoặc pipeline sẽ tự động clone dự án vào thư mục này lần đầu tiên.

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
