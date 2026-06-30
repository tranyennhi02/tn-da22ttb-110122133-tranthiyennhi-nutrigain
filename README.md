<div align="center">

# 🥗 NutriGain

### *Hệ Thống Gợi Ý Thực Đơn Tăng Cân Thông Minh*

**Theo Dõi Dinh Dưỡng Bằng AI • Lập Kế Hoạch Bữa Ăn Cá Nhân Hóa • Gamification Động Lực**

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)](https://reactjs.org/)
[![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1?style=for-the-badge&logo=mysql&logoColor=white)](https://mysql.com/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com/)
[![PyTorch](https://img.shields.io/badge/PyTorch-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)](https://pytorch.org/)

[Tính Năng](#-tính-năng) • [Công Nghệ](#-công-nghệ-sử-dụng) • [Cài Đặt](#-hướng-dẫn-cài-đặt) • [Tài Liệu](#-tài-liệu) • [API](#-tài-liệu-api) • [Tác Giả](#-tác-giả)

---

</div>

## 📖 Tổng Quan

**NutriGain** là hệ thống gợi ý thực đơn thông minh được thiết kế để giúp người gầy (BMI < 23) tăng cân một cách an toàn và khoa học thông qua lập kế hoạch dinh dưỡng cá nhân hóa, nhận diện nguyên liệu bằng AI, và theo dõi tiến trình được gamification.

### 🎯 Vấn Đề Chúng Tôi Giải Quyết

Nhiều người gầy gặp khó khăn với:
- **Thiếu hướng dẫn cá nhân hóa** cho tăng cân lành mạnh
- **Khó theo dõi** lượng dinh dưỡng nạp vào một cách chính xác
- **Động lực thấp** để duy trì thói quen ăn uống đều đặn
- **Bối rối** về việc lựa chọn thực phẩm phù hợp

### 💡 Giải Pháp Của Chúng Tôi


NutriGain cung cấp:
- 🤖 **Gợi Ý Thực Đơn Bằng AI** sử dụng content-based filtering và tính toán độ tương đồng dinh dưỡng
- 📸 **Nhận Diện Hình Ảnh** với mô hình CLIP (độ chính xác 76.26% trên 26 nguyên liệu)
- 🎮 **Hệ Thống Gamification** với streak, thành tích và thử thách
- 📊 **Theo Dõi Tiến Trình Thời Gian Thực** với BMI, nhật ký cân nặng và phân tích dinh dưỡng
- 🔐 **Xác Thực An Toàn** với JWT tokens
- 📱 **Thiết Kế Responsive** tối ưu cho mobile và desktop

### 👥 Đối Tượng Sử Dụng

- Người có BMI < 23 muốn tăng cân lành mạnh
- Người cần hướng dẫn dinh dưỡng và lập kế hoạch bữa ăn
- Người muốn theo dõi tiến trình một cách khoa học
- Bất kỳ ai cần động lực để duy trì thói quen ăn uống lành mạnh

---

## ✨ Tính Năng

<div align="center">

| Tính Năng | Mô Tả | Trạng Thái |
|---------|-------------|--------|
| **🍽️ Gợi Ý Thực Đơn Cá Nhân Hóa** | Content-based filtering với tính toán độ tương đồng dinh dưỡng | ✅ Hoạt động |
| **🤖 Nhận Diện Nguyên Liệu AI** | Mô hình CLIP ViT-B/32 nhận diện 26 nguyên liệu | ✅ Hoạt động |
| **📊 Theo Dõi Dinh Dưỡng** | Tự động tính toán calo và chất dinh dưỡng đa lượng | ✅ Hoạt động |
| **⚖️ Ghi Nhận BMI & Cân Nặng** | Theo dõi thay đổi cân nặng với biểu đồ trực quan | ✅ Hoạt động |
| **🎮 Hệ Thống Gamification** | Streak, thành tích, thử thách và cấp độ | ✅ Hoạt động |
| **📈 Bảng Điều Khiển Tiến Trình** | Biểu đồ tương tác với thống kê dinh dưỡng | ✅ Hoạt động |
| **🔐 Xác Thực An Toàn** | Xác thực JWT với mã hóa mật khẩu | ✅ Hoạt động |
| **📱 Giao Diện Responsive** | Thiết kế mobile-first với TailwindCSS | ✅ Hoạt động |
| **🐳 Hỗ Trợ Docker** | Triển khai một lệnh với Docker Compose | ✅ Hoạt động |
| **💾 Xuất Báo Cáo** | Báo cáo dinh dưỡng PDF với biểu đồ | ✅ Hoạt động |

</div>

<details>
<summary><b>🎮 Chi Tiết Gamification</b></summary>

### Hệ Thống Thành Tích
- **Bước Đầu Tiên**: Ghi nhận bữa ăn đầu tiên, cân nặng đầu tiên, hoàn thành ngày đầu tiên
- **Kiên Trì**: Streak 3 ngày, streak 7 ngày, tuần hoàn hảo
- **Đa Dạng**: Thử 10 món ăn khác nhau, ăn từ tất cả nhóm thực phẩm
- **Tiến Bộ**: Đạt mục tiêu calo, ngày dinh dưỡng cân bằng

### Thử Thách
- Mục tiêu calo hàng ngày
- Thử thách cân bằng chất dinh dưỡng đa lượng
- Thử thách đa dạng thực phẩm
- Thử thách duy trì streak

### Hệ Thống Cấp Độ
- 20 cấp độ dựa trên điểm kinh nghiệm
- Kiếm XP bằng cách hoàn thành bữa ăn, duy trì streak, đạt mục tiêu
- Chỉ báo tiến trình cấp độ trực quan

</details>

---


## 🛠 Công Nghệ Sử Dụng

<div align="center">

### Frontend

![React](https://img.shields.io/badge/React-18.3.1-61DAFB?style=flat-square&logo=react&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-5.4.14-646CFF?style=flat-square&logo=vite&logoColor=white)
![TailwindCSS](https://img.shields.io/badge/Tailwind-3.4.8-38B2AC?style=flat-square&logo=tailwind-css&logoColor=white)
![Recharts](https://img.shields.io/badge/Recharts-2.5.0-8884D8?style=flat-square)
![Lucide](https://img.shields.io/badge/Lucide-1.16.0-F56565?style=flat-square)

### Backend

![FastAPI](https://img.shields.io/badge/FastAPI-0.115.8-009688?style=flat-square&logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=flat-square&logo=python&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0.38-red?style=flat-square)
![PyTorch](https://img.shields.io/badge/PyTorch-2.6.0-EE4C2C?style=flat-square&logo=pytorch&logoColor=white)
![Transformers](https://img.shields.io/badge/🤗_Transformers-yellow?style=flat-square)

### Cơ Sở Dữ Liệu & Hạ Tầng

![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1?style=flat-square&logo=mysql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-latest-2496ED?style=flat-square&logo=docker&logoColor=white)
![Nginx](https://img.shields.io/badge/Nginx-latest-009639?style=flat-square&logo=nginx&logoColor=white)
![JWT](https://img.shields.io/badge/JWT-Auth-000000?style=flat-square&logo=json-web-tokens&logoColor=white)

</div>

---


## 🏗️ Kiến Trúc Hệ Thống

```mermaid
graph TB
    subgraph Client["🖥️ Lớp Client"]
        UI["Ứng Dụng React<br/>Port 5173/3000"]
        Upload["Tải Lên Hình Ảnh"]
        Charts["Biểu Đồ Tương Tác"]
    end

    subgraph API["⚙️ Lớp Ứng Dụng"]
        FastAPI["FastAPI Server<br/>Port 8000"]
        Auth["Xác Thực<br/>(JWT)"]
        Meals["API Bữa Ăn"]
        Track["API Theo Dõi"]
        Image["API Nhận Diện Hình Ảnh"]
    end

    subgraph AI["🤖 Lớp AI/ML"]
        CLIP["CLIP ViT-B/32<br/>Độ Chính Xác 76.26%"]
        Rec["Hệ Thống Gợi Ý<br/>(Content-Based)"]
        Nutr["Tính Toán Dinh Dưỡng"]
    end

    subgraph Data["💾 Lớp Dữ Liệu"]
        MySQL["MySQL 8.0<br/>Port 3307"]
        Cache["HuggingFace Cache<br/>~600MB"]
    end

    UI --> FastAPI
    Upload --> Image
    FastAPI --> Auth
    FastAPI --> Meals
    FastAPI --> Track
    Image --> CLIP
    Meals --> Rec
    Track --> Nutr
    FastAPI --> MySQL
    CLIP --> Cache
    Rec --> MySQL
    Nutr --> MySQL

    style UI fill:#61DAFB,stroke:#333,stroke-width:2px,color:#000
    style FastAPI fill:#009688,stroke:#333,stroke-width:2px,color:#fff
    style CLIP fill:#EE4C2C,stroke:#333,stroke-width:2px,color:#fff
    style MySQL fill:#4479A1,stroke:#333,stroke-width:2px,color:#fff
```

---


## 🔄 Luồng Người Dùng

```mermaid
flowchart TD
    Start([👤 Người Dùng Truy Cập]) --> Check{Đã Xác Thực?}
    Check -->|Chưa| Register[📝 Đăng Ký/Đăng Nhập]
    Check -->|Rồi| Profile[👤 Hoàn Thiện Hồ Sơ]
    
    Register --> Profile
    Profile --> BMI{BMI < 23?}
    
    BMI -->|Không| Restrict[❌ Hạn Chế Truy Cập]
    BMI -->|Có| Dashboard[📊 Bảng Điều Khiển]
    
    Dashboard --> Action{Chọn Hành Động}
    
    Action --> Recommend[🍽️ Nhận Gợi Ý<br/>Thực Đơn]
    Action --> Upload[📸 Tải Lên Hình Món Ăn]
    Action --> Log[📝 Ghi Nhận Cân Nặng]
    Action --> View[📈 Xem Tiến Trình]
    
    Recommend --> AI1[🤖 Hệ Thống Gợi Ý AI]
    AI1 --> Display1[📋 Hiển Thị Bữa Ăn]
    
    Upload --> AI2[🤖 Nhận Diện CLIP]
    AI2 --> Display2[🏷️ Nguyên Liệu<br/>Phát Hiện]
    
    Log --> Save[💾 Lưu Vào CSDL]
    Save --> Calculate[🔢 Tính BMI]
    
    View --> Charts[📊 Hiện Phân Tích<br/>& Biểu Đồ]
    
    Display1 --> Track[✅ Theo Dõi Tiêu Thụ]
    Display2 --> Track
    Track --> Gamify[🎮 Cập Nhật Gamification]
    Gamify --> Dashboard
    
    style Start fill:#4CAF50,stroke:#2E7D32,stroke-width:3px,color:#fff
    style Dashboard fill:#2196F3,stroke:#1565C0,stroke-width:2px,color:#fff
    style AI1 fill:#FF9800,stroke:#E65100,stroke-width:2px,color:#fff
    style AI2 fill:#FF9800,stroke:#E65100,stroke-width:2px,color:#fff
    style Gamify fill:#9C27B0,stroke:#4A148C,stroke-width:2px,color:#fff
```

---


## 🎯 Recommendation Workflow

```mermaid
sequenceDiagram
    participant U as 👤 User
    participant F as 🖥️ Frontend
    participant A as ⚙️ API
    participant R as 🤖 Recommender
    participant D as 💾 Database

    U->>F: Request Meal Recommendations
    F->>A: GET /api/v1/meals/recommend
    
    A->>D: Fetch User Profile & History
    D-->>A: Return User Data
    
    A->>D: Get Available Foods
    D-->>A: Return Food Dataset
    
    A->>R: Calculate Similarity Scores
    Note over R: Content-Based Filtering<br/>Nutrition Vector Similarity
    
    R->>R: Apply Filters<br/>- BMI Gate<br/>- User Preferences<br/>- Diversity
    
    R-->>A: Return Top Recommendations
    
    A->>D: Save Recommendation Log
    
    A-->>F: Return Meal List (JSON)
    F-->>U: Display Personalized Meals
    
    U->>F: Select & Track Meal
    F->>A: POST /api/v1/meals/log
    A->>D: Update Consumption History
    A->>D: Update Gamification Stats
    D-->>A: Confirm Save
    A-->>F: Success Response
    F-->>U: Show Updated Dashboard
```

---


## 💾 Database Schema

```mermaid
erDiagram
    USERS ||--o{ USER_PROFILES : has
    USERS ||--o{ WEIGHT_LOGS : tracks
    USERS ||--o{ MEAL_LOGS : logs
    USERS ||--o{ USER_ACHIEVEMENTS : earns
    USERS ||--o{ RECOMMENDATION_LOGS : receives
    
    FOODS ||--o{ MEAL_LOGS : contains
    FOODS ||--o{ USER_FOOD_INTERACTIONS : interacts
    FOODS ||--o{ RECOMMENDATION_LOGS : recommended
    
    USERS {
        int id PK
        string email UK
        string password_hash
        string full_name
        datetime created_at
        datetime updated_at
    }
    
    USER_PROFILES {
        int id PK
        int user_id FK
        float height
        date birth_date
        string gender
        float target_weight
        float target_calories
        text preferences
    }
    
    FOODS {
        int id PK
        string name
        string category
        float calories
        float protein
        float carbs
        float fat
        string image_url
    }
    
    WEIGHT_LOGS {
        int id PK
        int user_id FK
        float weight
        float bmi
        date log_date
    }
    
    MEAL_LOGS {
        int id PK
        int user_id FK
        int food_id FK
        float portion
        datetime consumed_at
    }

    USER_ACHIEVEMENTS {
        int id PK
        int user_id FK
        string achievement_type
        datetime earned_at
    }
```

---


## 📁 Project Structure

```
NutriGain/
├── 📚 docs/                          # Documentation
│   ├── BAOCAOĐATN.docx              # Thesis Report (Word)
│   ├── BAOCAOĐATN.pdf               # Thesis Report (PDF)
│   └── POSTERTN.pdf                 # Project Poster
│
└── 💻 src/                           # Source Code
    ├── 🔧 backend/                   # FastAPI Backend
    │   ├── app/
    │   │   ├── api/                 # API Endpoints
    │   │   │   └── v1/              # API Version 1
    │   │   ├── core/                # Configuration
    │   │   ├── models/              # SQLAlchemy Models
    │   │   ├── services/            # Business Logic
    │   │   │   ├── clip_ingredient_service.py
    │   │   │   ├── recommender_service.py
    │   │   │   └── gamification_service.py
    │   │   └── repositories/        # Database Queries
    │   ├── scripts/                 # Utility Scripts
    │   ├── requirements.txt         # Python Dependencies
    │   ├── Dockerfile              # Docker Image
    │   └── run-local.bat           # Local Run Script
    │
    ├── 🎨 frontend/                  # React Frontend
    │   ├── src/
    │   │   ├── components/          # React Components
    │   │   ├── views/               # Page Components
    │   │   ├── services/            # API Clients
    │   │   ├── utils/               # Utilities
    │   │   └── App.jsx             # Main App
    │   ├── public/                  # Static Assets
    │   ├── package.json            # NPM Dependencies
    │   └── Dockerfile              # Docker Image
    │
    ├── 🗄️ database/                  # Database Scripts
    │   └── init.sql                # Initial Schema
    │
    ├── 💾 data/                      # Test Data
    │   └── clip_test_images/        # 219 Test Images
    │
    ├── 🐳 docker-compose.yml         # Docker Orchestration
    └── 📝 README.md                 # This File
```

---


## 🚀 Hướng Dẫn Cài Đặt

### Yêu Cầu Hệ Thống

| Phần Mềm | Phiên Bản | Mục Đích |
|----------|---------|---------|
| **Python** | 3.13+ | Backend runtime |
| **Node.js** | 18+ | Frontend build tool |
| **Docker** | 20+ | Container runtime |
| **Git** | Mới nhất | Quản lý phiên bản |

### Khởi Động Nhanh Với Docker (Khuyến Nghị)

```bash
# Clone repository
git clone https://github.com/tranyennhi02/tn-da22ttb-110122133-tranthiyennhi-nutrigain.git
cd tn-da22ttb-110122133-tranthiyennhi-nutrigain/src

# Copy file môi trường
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

# Khởi động tất cả services
docker-compose up -d --build

# Kiểm tra trạng thái
docker-compose ps
```

**Truy cập ứng dụng:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Tài liệu API: http://localhost:8000/docs

<details>
<summary><b>🔧 Cài Đặt Phát Triển Local</b></summary>

### Cài Đặt Backend

```bash
# Di chuyển đến thư mục backend
cd src/backend

# Tạo môi trường ảo
python -m venv .venv

# Kích hoạt môi trường ảo
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Cài đặt dependencies
pip install -r requirements.txt

# Khởi động cơ sở dữ liệu MySQL
cd ..
docker-compose up -d db

# Chạy backend server
cd backend
run-local.bat  # Windows
./run-local.sh # Linux/Mac
```


### Cài Đặt Frontend

```bash
# Mở terminal mới, di chuyển đến thư mục frontend
cd src/frontend

# Cài đặt dependencies
npm install

# Khởi động dev server
npm run dev
```

**URL Servers:**
- Backend: http://localhost:8000
- Frontend: http://localhost:5173

</details>

<details>
<summary><b>☁️ Triển Khai Production</b></summary>

### Triển Khai Lên VPS

```bash
# SSH vào server
ssh user@your-server-ip

# Cài đặt Docker
curl -fsSL https://get.docker.com | sh

# Clone và deploy
git clone <repo-url>
cd NutriGain/src

# Cấu hình môi trường production
cp backend/.env.example backend/.env
nano backend/.env  # Chỉnh sửa với giá trị production

# Khởi động services
docker-compose -f docker-compose.prod.yml up -d --build
```

### Triển Khai Lên Cloud Platforms

**Railway.app:**
```bash
railway login
railway init
railway up
```

**Render.com:**
1. Kết nối GitHub repository
2. Chọn `docker-compose.yml`
3. Deploy

</details>

---


## 📡 Tài Liệu API

### Base URL

```
Development: http://localhost:8000/api/v1
Production: https://your-domain.com/api/v1
```

### Xác Thực

Tất cả endpoints được bảo vệ yêu cầu JWT token trong Authorization header:

```bash
Authorization: Bearer <your-jwt-token>
```

### Endpoints

<details>
<summary><b>🔐 Xác Thực</b></summary>

#### Đăng Ký Người Dùng
```http
POST /auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "secure_password",
  "full_name": "Nguyễn Văn A"
}
```

#### Đăng Nhập
```http
POST /auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "secure_password"
}
```

**Phản Hồi:**
```json
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "full_name": "Nguyễn Văn A"
  }
}
```

</details>

<details>
<summary><b>🍽️ Gợi Ý Bữa Ăn</b></summary>

#### Lấy Gợi Ý
```http
GET /meals/recommend?limit=10
Authorization: Bearer <token>
```

**Phản Hồi:**
```json
{
  "recommendations": [
    {
      "food_id": 42,
      "name": "Ức Gà Nướng",
      "calories": 165,
      "protein": 31,
      "carbs": 0,
      "fat": 3.6,
      "similarity_score": 0.92
    }
  ]
}
```


#### Ghi Nhận Tiêu Thụ Bữa Ăn
```http
POST /meals/log
Authorization: Bearer <token>
Content-Type: application/json

{
  "food_id": 42,
  "portion": 1.5,
  "consumed_at": "2024-01-15T12:30:00"
}
```

</details>

<details>
<summary><b>📸 Nhận Diện Hình Ảnh</b></summary>

#### Nhận Diện Nguyên Liệu
```http
POST /ingredients/recognize
Authorization: Bearer <token>
Content-Type: multipart/form-data

image: <binary-file>
```

**Phản Hồi:**
```json
{
  "detected_ingredients": [
    {
      "name": "Cam (Orange)",
      "confidence": 0.89,
      "category": "Fruit"
    },
    {
      "name": "Cà chua (Tomato)",
      "confidence": 0.76,
      "category": "Vegetable"
    }
  ],
  "processing_time_ms": 234
}
```

</details>

<details>
<summary><b>📊 Theo Dõi & Phân Tích</b></summary>

#### Ghi Nhận Cân Nặng
```http
POST /weight-logs
Authorization: Bearer <token>
Content-Type: application/json

{
  "weight": 55.5,
  "log_date": "2024-01-15"
}
```

#### Lấy Thống Kê Dashboard
```http
GET /dashboard/stats
Authorization: Bearer <token>
```

</details>

<details>
<summary><b>🎮 Gamification</b></summary>

#### Lấy Tóm Tắt Gamification
```http
GET /gamification/summary
Authorization: Bearer <token>
```

**Phản Hồi:**
```json
{
  "streak": 7,
  "level": 5,
  "xp": 1250,
  "achievements": [
    {
      "type": "first_meal_plan",
      "earned_at": "2024-01-10T08:00:00"
    }
  ]
}
```

</details>

> 📚 **Tài Liệu API Đầy Đủ:** Truy cập [http://localhost:8000/docs](http://localhost:8000/docs) để xem Swagger UI tương tác

---


## 🤖 Hiệu Suất Mô Hình CLIP

### Tổng Quan

- **Mô Hình:** CLIP ViT-B/32 (OpenAI)
- **Framework:** PyTorch 2.6.0 (CPU)
- **Bộ Dữ Liệu Test:** 219 hình ảnh trên 26 nguyên liệu
- **Độ Chính Xác Tổng Thể:** **76.26%** (167/219 nhận diện đúng)

### Phân Tích Độ Chính Xác

| Mức Hiệu Suất | Nguyên Liệu | Số Lượng | Phạm Vi Độ Chính Xác |
|-----------------|-------------|-------|----------------|
| 🟢 **Xuất Sắc** (100%) | Cam, Cà chua, Cà rốt, Khoai lang, Khoai tây, Trứng | 6 | 100% |
| 🟡 **Rất Tốt** (80-99%) | Cá hồi, Sữa, Táo, Chuối, Cua, Thịt bò | 6 | 80-99% |
| 🟠 **Tốt** (60-79%) | Yến mạch, Tôm, Cá, Đậu nành, Rau cải, Thịt gà | 7 | 60-79% |
| 🔴 **Khá** (<60%) | Cơm, Nấm, Đậu hũ, Thịt lợn, Bí đỏ, Hàu, Sò | 7 | <60% |

### Nguyên Liệu Được Hỗ Trợ

<div align="center">

| Nguyên Liệu | Tiếng Anh | Nhóm |
|---------------------------|---------|----------|
| 🍊 Cam | Orange | Trái cây |
| 🍅 Cà chua | Tomato | Rau củ |
| 🥕 Cà rốt | Carrot | Rau củ |
| 🐟 Cá | Fish | Protein |
| 🦐 Tôm | Shrimp | Protein |
| 🥚 Trứng | Egg | Protein |
| 🍗 Thịt gà | Chicken | Protein |
| 🥩 Thịt bò | Beef | Protein |
| 🍚 Cơm | Rice | Tinh bột |
| 🍌 Chuối | Banana | Trái cây |

*...và 16 nguyên liệu khác*

</div>

> 📖 **Báo Cáo Chi Tiết:** Xem [CLIP_EVALUATION_REPORT_76.26.md](src/backend/CLIP_EVALUATION_REPORT_76.26.md)

---


## 🧪 Kiểm Thử

### Kiểm Thử Backend

```bash
cd src/backend
pytest
```

### Đánh Giá Mô Hình CLIP

```bash
cd src/backend

# Test nhanh với hình ảnh mẫu
python -m scripts.quick_test_clip

# Đánh giá đầy đủ trên bộ dữ liệu test
python -m scripts.evaluate_clip_accuracy --test-dir ../data/clip_test_images

# Test nguyên liệu cụ thể
python -m scripts.test_clip_recognition --ingredient "Cam"
```

### Kiểm Thử Frontend

```bash
cd src/frontend
npm run test
```

---

## 🐛 Khắc Phục Sự Cố

<details>
<summary><b>❌ Mô Hình CLIP Không Tải Được</b></summary>

**Vấn Đề:** Mô hình CLIP không tải được hoặc báo lỗi DLL

**Giải Pháp:**
1. Đảm bảo sử dụng `run-local.bat` để set đúng cache paths
2. Cài đặt Visual C++ Redistributable: https://aka.ms/vs/17/release/vc_redist.x64.exe
3. Kiểm tra cài đặt PyTorch:
   ```bash
   python -c "import torch; print(torch.__version__)"
   ```
4. Xóa cache và cài lại:
   ```bash
   rm -rf src/.cache/
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
   ```

</details>

<details>
<summary><b>❌ Kết Nối Cơ Sở Dữ Liệu Thất Bại</b></summary>

**Vấn Đề:** Không thể kết nối đến cơ sở dữ liệu MySQL

**Giải Pháp:**
1. Kiểm tra container cơ sở dữ liệu đang chạy:
   ```bash
   docker ps
   ```
2. Khởi động cơ sở dữ liệu nếu chưa chạy:
   ```bash
   cd src
   docker-compose up -d db
   ```
3. Xác minh connection string trong `.env`:
   ```
   DATABASE_URL=mysql+pymysql://nutrigain:password@localhost:3307/food_recommender
   ```

</details>

<details>
<summary><b>❌ Lỗi CORS Ở Frontend</b></summary>

**Vấn Đề:** Frontend không thể kết nối đến backend API

**Giải Pháp:**
1. Kiểm tra `VITE_API_BASE_URL` trong `src/frontend/.env`
2. Xác minh backend đang chạy trên đúng port
3. Kiểm tra cấu hình CORS của FastAPI trong `src/backend/app/main.py`

</details>

<details>
<summary><b>❌ Docker Build Thất Bại</b></summary>

**Vấn Đề:** Docker build thất bại với lỗi memory hoặc timeout

**Giải Pháp:**
1. Tăng giới hạn memory của Docker (Settings > Resources)
2. Sử dụng multi-stage builds (đã cấu hình sẵn)
3. Build services riêng lẻ:
   ```bash
   docker-compose build backend
   docker-compose build frontend
   ```

</details>

---


## 🚧 Cải Tiến Trong Tương Lai

- [ ] **Ứng Dụng Mobile** - Phiên bản React Native cho iOS và Android
- [ ] **Collaborative Filtering** - Hệ thống gợi ý kết hợp content-based và collaborative filtering
- [ ] **Lịch Lập Kế Hoạch Bữa Ăn** - Tạo kế hoạch bữa ăn hàng tuần với danh sách mua sắm
- [ ] **Tính Năng Xã Hội** - Chia sẻ tiến trình, công thức và thành tích với bạn bè
- [ ] **Chatbot Dinh Dưỡng** - Trợ lý AI cho các câu hỏi dinh dưỡng sử dụng LLM
- [ ] **Hỗ Trợ Đa Ngôn Ngữ** - Tiếng Anh, Tiếng Việt và nhiều hơn nữa
- [ ] **Quét Mã Vạch** - Quét sản phẩm thực phẩm để có thông tin dinh dưỡng ngay lập tức
- [ ] **Tích Hợp Thiết Bị Theo Dõi Sức Khỏe** - Đồng bộ với Apple Health, Google Fit
- [ ] **Tạo Công Thức** - Gợi ý công thức bằng AI dựa trên nguyên liệu có sẵn
- [ ] **Hướng Dẫn Chuẩn Bị Bữa Ăn** - Hướng dẫn nấu ăn từng bước với bộ đếm thời gian
- [ ] **Hỗ Trợ Chuyên Gia Dinh Dưỡng** - Kết nối người dùng với chuyên gia dinh dưỡng được chứng nhận
- [ ] **Phân Tích Nâng Cao** - Mô hình dự đoán tăng cân sử dụng ML

---

## 📚 Tài Liệu

| Tài Liệu | Mô Tả | Link |
|----------|-------------|------|
| **Báo Cáo Đồ Án (Tiếng Việt)** | Báo cáo đồ án tốt nghiệp hoàn chỉnh | [docs/BAOCAOĐATN.pdf](docs/BAOCAOĐATN.pdf) |
| **Poster Đồ Án** | Tóm tắt dự án trực quan | [docs/POSTERTN.pdf](docs/POSTERTN.pdf) |
| **Báo Cáo Đánh Giá CLIP** | Phân tích hiệu suất chi tiết mô hình AI | [src/backend/CLIP_EVALUATION_REPORT_76.26.md](src/backend/CLIP_EVALUATION_REPORT_76.26.md) |
| **Cấu Trúc Dự Án** | Giải thích cấu trúc thư mục chi tiết | [src/STRUCTURE.md](src/STRUCTURE.md) |
| **Tài Liệu API** | Swagger UI tương tác | http://localhost:8000/docs |

---


## 👥 Tác Giả

<div align="center">

### Trần Thị Yến Nhi

**Mã Sinh Viên:** 110122133  
**Lớp:** DA22TTB  
**Ngành:** Công Nghệ Thông Tin  
**Trường:** Đại Học Trà Vinh

[![Email](https://img.shields.io/badge/Email-110122133@st.tvu.edu.vn-D14836?style=for-the-badge&logo=gmail&logoColor=white)](mailto:110122133@st.tvu.edu.vn)
[![GitHub](https://img.shields.io/badge/GitHub-tranyennhi02-181717?style=for-the-badge&logo=github)](https://github.com/tranyennhi02)

</div>

---

## 🙏 Lời Cảm Ơn

Đồ án tốt nghiệp này không thể hoàn thành nếu không có sự hỗ trợ và hướng dẫn từ:

- **Đại Học Trà Vinh** - Khoa Kỹ Thuật và Công Nghệ, Bộ Môn Công Nghệ Thông Tin
- **Giảng Viên Hướng Dẫn** - Cho những hướng dẫn và chỉ bảo quý giá trong suốt dự án
- **OpenAI** - Cho mô hình CLIP và nghiên cứu vision-language
- **HuggingFace** - Cho thư viện Transformers và hosting mô hình
- **Cộng Đồng FastAPI** - Cho tài liệu và hỗ trợ tuyệt vời
- **Cộng Đồng React** - Cho các công cụ phát triển frontend hiện đại
- **Những Người Đóng Góp Mã Nguồn Mở** - Cho những thư viện và frameworks tuyệt vời

### Công Nghệ Được Sử Dụng

- [FastAPI](https://fastapi.tiangolo.com/) - Framework web Python hiện đại
- [React](https://reactjs.org/) - Thư viện UI frontend
- [PyTorch](https://pytorch.org/) - Framework deep learning
- [CLIP](https://github.com/openai/CLIP) - Mô hình vision-language của OpenAI
- [TailwindCSS](https://tailwindcss.com/) - Framework CSS utility-first
- [Recharts](https://recharts.org/) - Thư viện biểu đồ cho React
- [SQLAlchemy](https://www.sqlalchemy.org/) - Python SQL toolkit
- [Vite](https://vitejs.dev/) - Công cụ frontend thế hệ mới

---


## 📄 Giấy Phép

Dự án này là đồ án tốt nghiệp được nộp cho Đại Học Trà Vinh.

**Bản Quyền © 2026 Trần Thị Yến Nhi**

Mọi quyền được bảo lưu. Dự án này và tài liệu của nó là tài sản trí tuệ của tác giả và Đại Học Trà Vinh.

---

## 📞 Liên Hệ & Hỗ Trợ

Đối với các câu hỏi, đề xuất hoặc cơ hội hợp tác:

- 📧 **Email:** 110122133@st.tvu.edu.vn
- 🐛 **Báo Lỗi:** [GitHub Issues](https://github.com/tranyennhi02/tn-da22ttb-110122133-tranthiyennhi-nutrigain/issues)
- 📖 **Tài Liệu:** [Project Wiki](https://github.com/tranyennhi02/tn-da22ttb-110122133-tranthiyennhi-nutrigain/wiki)

---

<div align="center">

### ⭐ Nếu bạn thấy dự án này hữu ích, hãy cho một ngôi sao nhé!

**Được Tạo Với ❤️ Bởi Yến Nhi Tại Đại Học Trà Vinh**

[![Trà Vinh University](https://img.shields.io/badge/Đại_Học_Trà_Vinh-0066CC?style=for-the-badge)](https://tvu.edu.vn/)
[![Đồ Án Tốt Nghiệp](https://img.shields.io/badge/Đồ_Án_Tốt_Nghiệp-2026-green?style=for-the-badge)](.)

---

**NutriGain** • *Tăng Cân Thông Minh, Được Hỗ Trợ Bởi AI*

</div>
