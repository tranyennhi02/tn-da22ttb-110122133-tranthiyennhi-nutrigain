# Cấu Trúc Dự Án NutriGain

> **Lưu ý quan trọng**: Cấu trúc này tuân thủ yêu cầu của nhà trường - TẤT CẢ source code và cache PHẢI nằm trong thư mục `src/`

## 📁 Cấu Trúc Thư Mục

```
NutriGain/
├── docs/                          # Tài liệu dự án (theo yêu cầu nhà trường)
│   ├── *.docx                    # File quyền đồ án
│   ├── *.pdf                     # File quyền đồ án PDF
│   ├── *.pptx                    # Slide báo vệ
│   ├── poster.pdf                # Poster A1
│   └── demo-guide.md             # Hướng dẫn demo
│
├── src/                           # SOURCE CODE (theo yêu cầu nhà trường)
│   ├── backend/                  # Backend FastAPI + Python
│   │   ├── app/                  # Application code
│   │   ├── scripts/              # Utility scripts
│   │   ├── results/              # CLIP evaluation results
│   │   ├── .venv/                # Python virtual environment
│   │   ├── requirements.txt      # Python dependencies
│   │   ├── run-local.bat         # Script chạy local
│   │   ├── Dockerfile            # Docker image cho backend
│   │   └── ...
│   │
│   ├── frontend/                 # Frontend React + Vite
│   │   ├── src/                  # React source code
│   │   ├── public/               # Static assets
│   │   ├── package.json          # Node dependencies
│   │   ├── Dockerfile            # Docker image cho frontend
│   │   └── ...
│   │
│   ├── .cache/                   # CACHE DIRECTORIES (inside src/)
│   │   ├── huggingface/          # HuggingFace models cache
│   │   │   ├── transformers/     # CLIP model files (~600MB)
│   │   │   └── hub/              # Model hub cache
│   │   └── torch/                # PyTorch cache
│   │
│   ├── docker-compose.yml        # Docker orchestration
│   ├── .env.example              # Environment variables template
│   └── .gitignore                # Git ignore rules
│
└── README.md                      # Project overview & setup guide
```

## 🎯 Yêu Cầu Nhà Trường

### 1. Repository GitHub
- **Tên repository**: `<tn-malop-mssv-hotensv-shortname>`
  - Ví dụ: `tn-da22tta-nguyenvana-dudoankght-ai`
- **Shortname**: Tên rút gọn của đồ án

### 2. Thư Mục `docs/`
Chứa các tài liệu văn bản:
- File quyền đồ án (`.docx`)
- File quyền đồ án PDF (`.pdf`)
- Slide báo vệ (`.pptx`)
- Poster A1 (`.pdf`, 594x841mm)
- Hướng dẫn demo

### 3. Thư Mục `src/`
Chứa **TẤT CẢ** source code:
- Backend code
- Frontend code
- Database scripts
- Docker files
- Hình ảnh, âm thanh, video
- **Cache directories** (`.cache/`)
- Tất cả file liên quan đến code

### 4. File `README.md`
Giới thiệu về đồ án với:
- Mục tiêu
- Kiến trúc
- Các phần mềm cần thiết
- Cách thức chạy ứng dụng (local hoặc Docker)

## ⚙️ Cache Configuration

### Vì Sao Cache Phải Trong `src/`?

Theo yêu cầu nhà trường, **TẤT CẢ** file liên quan đến dự án phải nằm trong `src/`. Do đó:

1. **Trước đây** (SAI):
   ```
   NutriGain/
   ├── .cache/          ❌ Ngoài src/
   ├── hf-cache/        ❌ Ngoài src/
   ├── torch-cache/     ❌ Ngoài src/
   └── src/
       └── backend/
   ```

2. **Bây giờ** (ĐÚNG):
   ```
   NutriGain/
   └── src/
       ├── .cache/      ✅ Trong src/
       │   ├── huggingface/
       │   └── torch/
       └── backend/
   ```

### Cách Cấu Hình Cache

#### Option 1: Dùng `run-local.bat` (Khuyến nghị)

File `src/backend/run-local.bat` đã được cấu hình tự động:

```batch
REM Set cache paths (inside src/ structure)
set HF_HOME=%CD%\..\.cache\huggingface
set TORCH_HOME=%CD%\..\.cache\torch
set TRANSFORMERS_CACHE=%CD%\..\.cache\huggingface\transformers
```

**Cách dùng**:
```bash
cd src/backend
run-local.bat
```

#### Option 2: Cấu hình thủ công

Nếu chạy trực tiếp Python:

**Windows PowerShell**:
```powershell
$env:HF_HOME="D:\DOANTOTNGHIEP\NutriGain\src\.cache\huggingface"
$env:TORCH_HOME="D:\DOANTOTNGHIEP\NutriGain\src\.cache\torch"
cd src/backend
python -m uvicorn app.main:app --reload
```

**Windows CMD**:
```cmd
set HF_HOME=D:\DOANTOTNGHIEP\NutriGain\src\.cache\huggingface
set TORCH_HOME=D:\DOANTOTNGHIEP\NutriGain\src\.cache\torch
cd src\backend
python -m uvicorn app.main:app --reload
```

**Linux/Mac**:
```bash
export HF_HOME="$PWD/src/.cache/huggingface"
export TORCH_HOME="$PWD/src/.cache/torch"
cd src/backend
python -m uvicorn app.main:app --reload
```

## 🚀 Chạy Ứng Dụng

### Local Development

1. **Backend**:
   ```bash
   cd src/backend
   run-local.bat        # Windows
   # hoặc
   ./run-local.sh       # Linux/Mac
   ```

2. **Frontend**:
   ```bash
   cd src/frontend
   npm install
   npm run dev
   ```

### Docker

```bash
cd src
docker-compose up -d
```

## 📝 Lưu Ý Quan Trọng

### ✅ ĐÚNG - Files trong `src/`

- ✅ `src/backend/` - Backend code
- ✅ `src/frontend/` - Frontend code
- ✅ `src/.cache/` - Cache directories
- ✅ `src/docker-compose.yml` - Docker config
- ✅ `src/.env` - Environment variables

### ❌ SAI - Files ngoài `src/`

- ❌ `backend/` - Phải là `src/backend/`
- ❌ `.cache/` - Phải là `src/.cache/`
- ❌ `hf-cache/` - Phải là `src/.cache/huggingface/`
- ❌ `torch-cache/` - Phải là `src/.cache/torch/`

### Git Ignore

File `src/.gitignore` đã được cấu hình đúng:

```gitignore
# Cache directories (inside src/)
.cache/
pip-cache/
pip-temp/
```

## 🔧 Troubleshooting

### CLIP không hoạt động?

**Vấn đề**: CLIP model không tải được hoặc báo lỗi cache

**Giải pháp**:
1. Kiểm tra cache path trong `run-local.bat`
2. Đảm bảo folder `src/.cache/huggingface/` tồn tại
3. Chạy lại `run-local.bat` (đã có auto-create cache dirs)

### Models bị tải xuống sai vị trí?

**Vấn đề**: Models vẫn tải về `C:\Users\...\.cache\`

**Giải pháp**:
- Luôn dùng `run-local.bat` (đã set `HF_HOME`)
- Hoặc set environment variables trước khi chạy Python

### Không tìm thấy models?

**Vấn đề**: Báo lỗi "Model not found"

**Giải pháp**:
1. Download models lần đầu (cần internet):
   ```bash
   cd src/backend
   run-local.bat
   ```
2. Models sẽ được cache tại `src/.cache/huggingface/`
3. Lần sau không cần download lại

## 📊 CLIP Model Cache

### Model Size
- **CLIP ViT-B/32**: ~600MB
- **Location**: `src/.cache/huggingface/hub/models--openai--clip-vit-base-patch32/`

### First Run
Lần chạy đầu tiên sẽ tải model từ HuggingFace:
```
Downloading: 100%|████████| 605MB/605MB [05:23<00:00, 1.87MB/s]
```

### Subsequent Runs
Các lần sau sẽ load từ cache (nhanh hơn):
```
Loading model from cache: src/.cache/huggingface/...
```

## 📧 Liên Hệ

Nếu có vấn đề về cấu trúc dự án theo yêu cầu nhà trường, vui lòng liên hệ.

---

**Ngày cập nhật**: 28/06/2026  
**Tuân thủ**: Yêu cầu cấu trúc đồ án tốt nghiệp - Nhà trường
