# NutriGain - Hệ Thống Gợi Ý Thực Đơn Tăng Cân Thông Minh

> **Đồ án tốt nghiệp** - Ứng dụng AI hỗ trợ người gầy tăng cân an toàn và khoa học

## 🎯 Mục Tiêu Đồ Án

### Mục Tiêu Tổng Quát
Xây dựng hệ thống recommendation AI giúp người dùng gầy (BMI < 23) tăng cân một cách khoa học, an toàn và bền vững thông qua việc gợi ý thực đơn cá nhân hóa và theo dõi tiến trình.

### Mục Tiêu Cụ Thể

1. **Personalized Meal Recommendation**
   - Gợi ý thực đơn dựa trên sở thích người dùng
   - Tính toán dinh dưỡng phù hợp với mục tiêu tăng cân
   - Content-based filtering với nutrition similarity

2. **AI-Powered Ingredient Recognition**
   - Nhận diện nguyên liệu từ ảnh sử dụng CLIP model
   - Hỗ trợ 26 loại nguyên liệu phổ biến
   - Độ chính xác 76.26% (167/219 ảnh test)

3. **Gamification & Motivation**
   - Hệ thống streak, achievements, challenges
   - Động lực hóa người dùng duy trì chế độ dinh dưỡng
   - Visual progress tracking

4. **Health Tracking**
   - Theo dõi cân nặng, BMI
   - Nutrition intake tracking
   - Visual analytics và báo cáo tiến trình

### Đối Tượng Sử Dụng
- Người dùng có BMI < 23 (gầy) muốn tăng cân khoa học
- Cần hướng dẫn dinh dưỡng và động lực duy trì
- Có nhu cầu theo dõi tiến trình tăng cân

## 🏗️ Kiến Trúc Hệ Thống

### Tech Stack

**Backend (FastAPI)**:
- **Framework**: FastAPI (Python 3.13)
- **Database**: MySQL 8.0
- **ORM**: SQLAlchemy
- **Authentication**: JWT tokens
- **AI/ML**: 
  - CLIP ViT-B/32 (PyTorch 2.6.0+cpu)
  - HuggingFace Transformers
- **Recommendation**: Content-based filtering

**Frontend (React)**:
- **Framework**: React 18.3.1
- **Build Tool**: Vite 5.4
- **Styling**: TailwindCSS 3.4
- **Icons**: Lucide React
- **HTTP Client**: Axios

**Infrastructure**:
- **Containerization**: Docker & Docker Compose
- **Web Server**: Nginx (production)
- **Reverse Proxy**: Nginx (API gateway)

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        Client Layer                         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │        React Frontend (Port 3000/5173)               │  │
│  │  - User Interface                                     │  │
│  │  - State Management                                   │  │
│  │  - Image Upload                                       │  │
│  └───────────────────┬──────────────────────────────────┘  │
└────────────────────────┼───────────────────────────────────┘
                         │
                         │ HTTP/REST API
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      Application Layer                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │       FastAPI Backend (Port 8000)                    │  │
│  │  ┌──────────────┐  ┌──────────────┐                 │  │
│  │  │   Auth API   │  │  Meals API   │                 │  │
│  │  └──────────────┘  └──────────────┘                 │  │
│  │  ┌──────────────┐  ┌──────────────┐                 │  │
│  │  │  Image API   │  │ Tracking API │                 │  │
│  │  └──────────────┘  └──────────────┘                 │  │
│  └───────────┬──────────────┬───────────────┬──────────┘  │
└──────────────┼──────────────┼───────────────┼─────────────┘
               │              │               │
               │              │               ▼
               │              │    ┌───────────────────────┐
               │              │    │   CLIP Model Layer    │
               │              │    │  ┌─────────────────┐  │
               │              │    │  │ CLIP ViT-B/32   │  │
               │              │    │  │ (PyTorch)       │  │
               │              │    │  │ 26 ingredients  │  │
               │              │    │  │ 76.26% accuracy │  │
               │              │    │  └─────────────────┘  │
               │              │    └───────────────────────┘
               │              │
               │              ▼
               │    ┌───────────────────────┐
               │    │ Recommendation Engine │
               │    │  ┌─────────────────┐  │
               │    │  │ Content-based   │  │
               │    │  │ Filtering       │  │
               │    │  │ (Nutrition      │  │
               │    │  │  Similarity)    │  │
               │    │  └─────────────────┘  │
               │    └───────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│                        Data Layer                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         MySQL Database (Port 3307)                   │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐          │  │
│  │  │  Users   │  │  Meals   │  │  Foods   │          │  │
│  │  └──────────┘  └──────────┘  └──────────┘          │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐          │  │
│  │  │ Profiles │  │  Logs    │  │Favorites │          │  │
│  │  └──────────┘  └──────────┘  └──────────┘          │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                      Cache Layer                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │        src/.cache/ (Inside src/)                     │  │
│  │  - HuggingFace models (~600MB)                       │  │
│  │  - PyTorch cache                                      │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow Diagram

```
User uploads image
       │
       ▼
[Frontend] ──(HTTP POST /api/v1/ingredients/recognize)──▶ [Backend API]
                                                                 │
                                                                 ▼
                                                          [CLIP Service]
                                                                 │
                                                                 ├─▶ Load CLIP model
                                                                 ├─▶ Process image
                                                                 ├─▶ Match with 716 prompts
                                                                 └─▶ Return top ingredients
                                                                 │
       ┌─────────────────────────────────────────────────────────┘
       │
       ▼
[Backend API] ──(JSON response)──▶ [Frontend]
       │                                 │
       ▼                                 ▼
Save to database              Display results to user
```

## � Phần Mềm Cần Thiết Để Triển Khai

### Development Environment

| Phần Mềm | Version | Mục Đích | Download Link |
|----------|---------|----------|---------------|
| **Python** | 3.13.9 | Backend runtime | [python.org](https://python.org) |
| **Node.js** | 18+ | Frontend build tool | [nodejs.org](https://nodejs.org) |
| **Docker Desktop** | 20+ | Container runtime | [docker.com](https://docker.com) |
| **Git** | Latest | Version control | [git-scm.com](https://git-scm.com) |
| **Visual Studio Code** | Latest | Code editor (khuyến nghị) | [code.visualstudio.com](https://code.visualstudio.com) |

### System Requirements

**Minimum**:
- CPU: Dual-core 2.0 GHz
- RAM: 4GB (8GB khuyến nghị cho CLIP model)
- Disk: 5GB free space (2GB for models + 3GB for source code)
- OS: Windows 10/11, macOS 10.15+, Ubuntu 20.04+

**Recommended**:
- CPU: Quad-core 2.5 GHz+
- RAM: 8GB+
- Disk: 10GB+ SSD
- Network: Stable internet (lần đầu tải CLIP model ~600MB)

### Additional Dependencies

**Windows** (quan trọng cho PyTorch):
- Visual C++ Redistributable 2015-2022 (x64)
  - Download: https://aka.ms/vs/17/release/vc_redist.x64.exe
  - Cần thiết để PyTorch load DLL files

**Python Packages** (tự động cài qua pip):
- FastAPI, Uvicorn, SQLAlchemy
- PyTorch 2.6.0+cpu (stable build)
- Transformers, Pillow
- python-dotenv, PyJWT

**Node Packages** (tự động cài qua npm):
- React, Vite, TailwindCSS
- Axios, React Router
- Lucide React

## 🚀 Cách Thức Chạy Chương Trình

### 🐳 Option 1: Docker Compose (Khuyến Nghị - Production Ready)

**Đây là cách triển khai đơn giản nhất, phù hợp cho hosting, production, và demo đồ án.**

#### Ưu Điểm
- ✅ Tất cả services chạy trong containers (isolated)
- ✅ Dễ deploy lên cloud (AWS, GCP, Azure, DigitalOcean)
- ✅ Không cần cài đặt Python, Node.js trực tiếp
- ✅ Consistent across environments

#### Bước Thực Hiện

```bash
# 1. Clone repository
git clone <repository-url>
cd NutriGain/src

# 2. Copy environment files
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

# 3. Chỉnh sửa .env files nếu cần
# (Mặc định đã config sẵn cho Docker)

# 4. Build và start tất cả services
docker-compose up -d --build

# 5. Chờ services khởi động (30-60s)
docker-compose logs -f

# 6. Kiểm tra services đang chạy
docker-compose ps
```

#### Truy Cập Ứng Dụng

| Service | URL | Mô Tả |
|---------|-----|-------|
| **Frontend** | http://localhost:3000 | React app |
| **Backend API** | http://localhost:8000 | FastAPI server |
| **API Docs** | http://localhost:8000/docs | Swagger UI |
| **Database** | localhost:3307 | MySQL |

#### Quản Lý Services

```bash
# Xem logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Stop services
docker-compose down

# Restart service
docker-compose restart backend

# Rebuild service after code changes
docker-compose up -d --build backend
```

#### Deploy Lên Cloud Hosting

**Railway.app** (Miễn phí cho students):
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login và deploy
railway login
railway init
railway up
```

**Render.com**:
1. Connect GitHub repository
2. Chọn `docker-compose.yml`
3. Click "Deploy"

**DigitalOcean App Platform**:
1. Connect repository
2. Detect Dockerfile
3. Configure environment variables
4. Deploy

### 💻 Option 2: Local Development (Dev Mode)

**Phù hợp khi đang phát triển code và cần hot reload.**

#### Backend Setup

```bash
# 1. Vào thư mục backend
cd src/backend

# 2. Tạo virtual environment
python -m venv .venv

# 3. Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 4. Cài đặt dependencies
pip install -r requirements.txt

# 5. Copy và config .env
cp .env.example .env.local
# Chỉnh sửa .env.local nếu cần

# 6. Start MySQL database (Docker)
cd ..
docker-compose up -d db

# 7. Chờ database ready (5-10s)
# Kiểm tra: docker-compose logs db

# 8. Quay lại backend và start server
cd backend
run-local.bat      # Windows
./run-local.sh     # Linux/Mac
```

**Backend sẽ chạy tại**: http://localhost:8000

**⚠️ Lưu Ý Quan Trọng - CLIP Model**:
- Server chạy **KHÔNG có hot reload** (để CLIP model stable)
- Khi thay đổi code: nhấn `Ctrl+C` và chạy lại `run-local.bat`
- Lần đầu chạy sẽ tải CLIP model ~600MB (chờ 2-3 phút)
- Các lần sau load từ cache `src/.cache/` (nhanh hơn)

#### Frontend Setup

```bash
# 1. Mở terminal mới, vào thư mục frontend
cd src/frontend

# 2. Cài đặt dependencies
npm install

# 3. Copy và config .env
cp .env.example .env
# Mặc định đã config cho local backend

# 4. Start dev server
npm run dev
```

**Frontend sẽ chạy tại**: http://localhost:5173

### 🌐 Option 3: Deploy Lên VPS/Server (Production)

**Phù hợp cho demo đồ án trên server thật.**

#### Yêu Cầu VPS
- Ubuntu 20.04+ / CentOS 8+
- RAM: 2GB+ (4GB recommended)
- CPU: 2 cores+
- Disk: 10GB+

#### Setup Script

```bash
# 1. SSH vào VPS
ssh user@your-server-ip

# 2. Cài đặt Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# 3. Cài đặt Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 4. Clone repository
git clone <repository-url>
cd NutriGain/src

# 5. Config production environment
cp backend/.env.example backend/.env
# Edit với production values (database password, secret keys, etc.)

# 6. Build và start
docker-compose -f docker-compose.prod.yml up -d --build

# 7. Setup Nginx reverse proxy (optional)
sudo apt install nginx
sudo nano /etc/nginx/sites-available/nutrigain
```

**Nginx Config** (`/etc/nginx/sites-available/nutrigain`):
```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Frontend
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

```bash
# Enable site và restart Nginx
sudo ln -s /etc/nginx/sites-available/nutrigain /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### SSL Certificate (HTTPS)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal test
sudo certbot renew --dry-run
```

## 📁 Cấu Trúc Dự Án

> ⚠️ **Quan trọng**: Cấu trúc này tuân thủ yêu cầu nhà trường - TẤT CẢ source code và cache phải nằm trong `src/`

```
NutriGain/
├── docs/                          # Tài liệu đồ án
│   ├── BAOCAOĐATN.docx           # Báo cáo đồ án (Word)
│   ├── BAOCAOĐATN.pdf            # Báo cáo đồ án (PDF)
│   ├── slides.pptx                # Slide báo vệ
│   └── poster.pdf                 # Poster đồ án
│
├── src/                           # SOURCE CODE (TẤT CẢ trong đây)
│   ├── backend/                   # FastAPI Backend
│   │   ├── app/
│   │   │   ├── api/              # API endpoints
│   │   │   ├── core/             # Config, database, security
│   │   │   ├── models/           # SQLAlchemy models
│   │   │   ├── services/         # Business logic
│   │   │   │   └── clip_ingredient_service.py  # CLIP recognition
│   │   │   ├── repositories/     # Database queries
│   │   │   └── main.py           # FastAPI app
│   │   ├── scripts/              # Utility scripts
│   │   │   └── evaluate_clip_accuracy.py  # CLIP evaluation
│   │   ├── .env.local            # Local environment config
│   │   ├── requirements.txt      # Python dependencies
│   │   ├── run-local.bat         # Windows startup script
│   │   └── Dockerfile            # Docker image
│   │
│   ├── frontend/                  # React Frontend
│   │   ├── src/
│   │   │   ├── components/       # React components
│   │   │   ├── pages/            # Page components
│   │   │   ├── services/         # API calls
│   │   │   ├── utils/            # Utilities
│   │   │   └── App.jsx           # Main app
│   │   ├── public/               # Static assets
│   │   ├── .env                  # Frontend config
│   │   ├── package.json          # NPM dependencies
│   │   └── Dockerfile            # Docker image
│   │
│   ├── .cache/                    # Cache (tuân thủ yêu cầu)
│   │   ├── huggingface/          # CLIP model cache (~600MB)
│   │   └── torch/                # PyTorch cache
│   │
│   ├── data/                      # Test data
│   │   └── clip_test_images/     # 219 images for evaluation
│   │
│   ├── docker-compose.yml         # Dev environment
│   ├── docker-compose.prod.yml   # Production environment
│   ├── .gitignore                # Git ignore
│   └── STRUCTURE.md              # Cấu trúc chi tiết
│
└── README.md                      # File này (hướng dẫn chính)
```

### Giải Thích Cấu Trúc

**`docs/`**: Tài liệu đồ án (Word, PDF, PowerPoint, Poster)  
**`src/`**: Toàn bộ source code và cache (tuân thủ yêu cầu nhà trường)  
**`src/backend/`**: Python FastAPI backend với CLIP AI model  
**`src/frontend/`**: React frontend với TailwindCSS  
**`src/.cache/`**: Cache models (CLIP ~600MB, tuân thủ yêu cầu nằm trong src/)  

Chi tiết xem [src/STRUCTURE.md](src/STRUCTURE.md)

## 🔧 Configuration & Environment Variables

### Backend Configuration (`src/backend/.env.local`)

```env
# Database - MySQL trong Docker
DATABASE_URL=mysql+pymysql://nutrigain:yennhi2602@localhost:3307/food_recommender

# JWT Secret
SECRET_KEY=your-super-secret-key-change-in-production

# Feature Flags
ENABLE_INGREDIENT_IMAGE_RECOGNITION=true

# Cache Configuration (tự động set bởi run-local.bat)
# HF_HOME sẽ được set vào src/.cache/huggingface/
# TORCH_HOME sẽ được set vào src/.cache/torch/
```

**Frontend** (`src/frontend/.env`):
```env
VITE_API_BASE_URL=http://localhost:8000
```

## ⚙️ CLIP Model - Đã Khắc Phục Lỗi DLL

### ✅ Trạng Thái: Hoạt Động Bình Thường

CLIP model đã được fix hoàn toàn và sẵn sàng sử dụng!

**PyTorch Version**: 2.6.0+cpu (stable)  
**CLIP Model**: openai/clip-vit-base-patch32  
**Accuracy**: 76.26% (167/219 images)  
**Cache Location**: `src/.cache/huggingface/` (~600MB)

### Kiểm Tra CLIP Đã Load

Sau khi start backend, tìm dòng log:
```
INFO: [CLIP MODEL STATUS] {'loaded': True, 'device': 'cpu', ...}
INFO: [CLIP MODEL LOADED] Model cached for subsequent requests
```

Xem hướng dẫn chi tiết: [src/backend/HUONG_DAN_CLIP.md](src/backend/HUONG_DAN_CLIP.md)

## 📊 Features - Chức Năng Chính

### 1. Meal Recommendation
- Content-based filtering dựa trên nutrition similarity
- Personalization theo user preferences
- BMI gate: chỉ gợi ý cho người BMI < 23
- Diversity trong recommendations

### 2. AI Image Recognition (CLIP)
- **Model**: CLIP ViT-B/32 (OpenAI)
- **Prompts**: 716 prompts cho 26 nguyên liệu
- **Accuracy**: 76.26% (167/219 test images)
- **Supported**: Cam, Cà chua, Trứng, Thịt, Cá, Rau, v.v.

### 3. Gamification
- **Streak**: Chuỗi ngày hoàn thành liên tục
- **Achievements**: 8 loại huy hiệu
- **Challenges**: Thử thách hằng ngày
- **Levels**: Hệ thống cấp độ 1-20

### 4. Progress Tracking
- Weight log với BMI tự động
- Nutrition tracking
- Visual charts & analytics

## 📈 CLIP Performance

### Accuracy Breakdown

| Nhóm | Nguyên Liệu | Accuracy |
|------|-------------|----------|
| 🟢 Hoàn hảo (100%) | Cam, Cà chua, Cà rốt, Khoai lang, Khoai tây, Trứng | 6/26 |
| 🟡 Rất tốt (80-99%) | Cá hồi, Sữa, Táo, Chuối, Cua, Thịt bò | 6/26 |
| 🟠 Trung bình (60-79%) | Yến mạch, Tôm, Cá, Đậu nành, Rau cải, Thịt gà | 7/26 |
| 🔴 Yếu (<60%) | Cơm, Nấm, Đậu hũ, Thịt lợn, Bí đỏ, Hàu, Sò | 7/26 |

**Overall**: 76.26% (167/219 successful recognitions)

Chi tiết: [src/backend/CLIP_EVALUATION_REPORT_76.26.md](src/backend/CLIP_EVALUATION_REPORT_76.26.md)

## 🧪 Testing

### Backend Tests

```bash
cd src/backend
pytest
```

### CLIP Evaluation

```bash
cd src/backend

# Quick test
python -m scripts.quick_test_clip

# Full evaluation
python -m scripts.evaluate_clip_accuracy --test-dir ../data/clip_test_images
```

## 📝 API Documentation

API documentation có sẵn tại:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

```
POST   /api/v1/auth/register           # Đăng ký
POST   /api/v1/auth/login              # Đăng nhập
GET    /api/v1/meals/recommend         # Gợi ý thực đơn
POST   /api/v1/ingredients/recognize   # Nhận diện nguyên liệu
GET    /api/v1/gamification/summary    # Thống kê gamification
POST   /api/v1/weight-logs             # Ghi nhận cân nặng
```

## 🎓 Tài Liệu

- **Quyền đồ án**: `docs/*.docx`, `docs/*.pdf`
- **Slide báo vệ**: `docs/*.pptx`
- **Poster**: `docs/poster.pdf`
- **Hướng dẫn demo**: `docs/demo-guide.md`
- **Cấu trúc chi tiết**: [src/STRUCTURE.md](src/STRUCTURE.md)
- **CLIP Evaluation**: [src/backend/CLIP_EVALUATION_REPORT_76.26.md](src/backend/CLIP_EVALUATION_REPORT_76.26.md)

## 🐛 Troubleshooting

### CLIP không hoạt động?

**Vấn đề**: CLIP model không tải được

**Giải pháp**: Đảm bảo đang dùng `run-local.bat` hoặc set cache paths:
```bash
set HF_HOME=D:\path\to\NutriGain\src\.cache\huggingface
set TORCH_HOME=D:\path\to\NutriGain\src\.cache\torch
```

### Database connection failed?

**Vấn đề**: Không kết nối được PostgreSQL

**Giải pháp**:
```bash
# Check database is running
docker ps

# Start database if not running
cd src
docker-compose up -d db
```

### Frontend không gọi được API?

**Vấn đề**: CORS error

**Giải pháp**: Kiểm tra `VITE_API_BASE_URL` trong `src/frontend/.env`

## 📧 Liên Hệ

- **Sinh viên**: Trần Thị Yến Nhi
- **MSSV**: 110122133
- **Email**: 110122133@st.tvu.edu.vn
- **Lớp**: DA22TTB
- **Khoa**: Công Nghệ Thông Tin

## 📄 License

Đồ án tốt nghiệp 

---