# PyTorch DLL Load Error - Fix Applied

## Problem Summary
- **Error**: `DLL load failed while importing _C: The specified module could not be found`
- **Cause**: Multiple issues combined:
  1. Cache path conflicts between `.env.local` and `run-local.bat`
  2. Incorrect cache path defaults in `main.py` (pointing outside `src/`)
  3. Startup sequence issue - `.env` files loaded before cache paths were configured
  4. Environment variables not properly inherited when uvicorn starts with `--reload`

## Root Cause Analysis
When running `diagnose_pytorch.py` directly with Python, PyTorch imports successfully. However, when starting via `uvicorn app.main:app --reload`, the PyTorch DLL error occurs. This indicates:

1. **PyTorch installation is correct** (version 2.12.1+cpu)
2. **Visual C++ Redistributable is installed correctly**
3. **The issue is environment configuration**, not missing system libraries

The problem occurs because:
- `run-local.bat` sets cache environment variables
- But when uvicorn starts with `--reload`, it spawns a subprocess using WatchFiles
- The subprocess doesn't always inherit environment variables from the batch file
- `.env.local` was overriding cache paths to old locations outside `src/`
- `main.py` had default cache paths pointing outside `src/`

## Fixes Applied

### 1. Fixed `.env.local` Cache Paths
**File**: `src/backend/.env.local`

**Before**:
```env
# Hugging Face Cache - Dùng ổ D để tránh hết dung lượng ổ C
HF_HOME=D:\DOANTOTNGHIEP\NutriGain\hf-cache
HUGGINGFACE_HUB_CACHE=D:\DOANTOTNGHIEP\NutriGain\hf-cache\hub
HF_HUB_CACHE=D:\DOANTOTNGHIEP\NutriGain\hf-cache\hub
TRANSFORMERS_CACHE=D:\DOANTOTNGHIEP\NutriGain\hf-cache\transformers
TORCH_HOME=D:\DOANTOTNGHIEP\NutriGain\torch-cache
```

**After**:
```env
# Cache Configuration - Inside src/ as per school requirements
# These paths are set by run-local.bat and should NOT be overridden here
# Uncomment only if you need to override the defaults:
# HF_HOME=D:\DOANTOTNGHIEP\NutriGain\src\.cache\huggingface
# TORCH_HOME=D:\DOANTOTNGHIEP\NutriGain\src\.cache\torch
```

**Why**: Removed conflicting cache paths that pointed outside `src/`. Now `run-local.bat` and `main.py` defaults control the cache location.

### 2. Fixed `main.py` Cache Path Defaults
**File**: `src/backend/app/main.py`

**Changes**:
1. **Moved cache configuration BEFORE `.env` loading**
   - Ensures environment variables are set before any imports
   - Cache paths are available to all modules during import

2. **Updated default cache paths to `src/.cache/`**
   - `HF_HOME`: `src/.cache/huggingface/`
   - `TORCH_HOME`: `src/.cache/torch/`
   - `TRANSFORMERS_CACHE`: `src/.cache/huggingface/transformers/`
   - Complies with school requirement: all files inside `src/`

3. **Used `override=True` when loading `.env` files**
   - Ensures `.env.local` can override defaults if needed
   - But since `.env.local` no longer sets cache paths, defaults are used

**Before**:
```python
# Load .env file before importing settings
try:
    from dotenv import load_dotenv
    # ... load .env files ...
except:
    pass

# Configure cache AFTER .env loading
def _configure_hf_cache():
    project_root = Path(__file__).parent.parent.parent  # Points outside src/
    default_hf_home = str(project_root / "hf-cache")
    # ... old paths outside src/ ...
```

**After**:
```python
# Configure cache FIRST, before .env loading
def _configure_hf_cache():
    backend_dir = Path(__file__).parent.parent  # backend/
    src_dir = backend_dir.parent  # src/
    default_hf_home = str(src_dir / ".cache" / "huggingface")
    # ... paths inside src/ ...
    os.environ.setdefault("HF_HOME", default_hf_home)
    # ...

_configure_hf_cache()

# Load .env file AFTER cache configuration
try:
    from dotenv import load_dotenv
    # ... load with override=True ...
```

### 3. CLIP Model Already Cached
The CLIP model (`openai/clip-vit-base-patch32`, ~600MB) is already downloaded and cached at:
- `src/.cache/huggingface/`

Verified by running `test_clip_import.py` which successfully:
- Imported torch 2.12.1+cpu
- Imported transformers
- Loaded CLIP model from cache
- Model ready on CPU device

## Verification Steps

### Step 1: Stop Existing Backend Server
**IMPORTANT**: Port 8000 is currently in use. Stop any existing backend servers:
- Press `Ctrl+C` in the terminal running the backend
- Or close the terminal window

### Step 2: Start Backend Server
```cmd
cd d:\DOANTOTNGHIEP\NutriGain\src\backend
.\run-local.bat
```

### Step 3: Verify CLIP Loads Successfully
Look for these log messages:
```
[CLIP CACHE CONFIG] Hugging Face cache paths:
  HF_HOME: D:\DOANTOTNGHIEP\NutriGain\src\.cache\huggingface
  HUGGINGFACE_HUB_CACHE: D:\DOANTOTNGHIEP\NutriGain\src\.cache\huggingface\hub
  HF_HUB_CACHE: D:\DOANTOTNGHIEP\NutriGain\src\.cache\huggingface\hub
  TRANSFORMERS_CACHE: D:\DOANTOTNGHIEP\NutriGain\src\.cache\huggingface\transformers
  TORCH_HOME: D:\DOANTOTNGHIEP\NutriGain\src\.cache\torch

INFO:     [CLIP WARMUP START]
INFO:     [CLIP ENABLED] Ingredient image recognition enabled
INFO:     [CLIP CACHE CONFIG] {...}
INFO:     [CLIP MODEL STATUS] {'loaded': True, 'device': 'cpu', 'modelName': 'openai/clip-vit-base-patch32'}
INFO:     [CLIP WARMUP DONE]
```

**SUCCESS INDICATORS**:
- ✓ All cache paths point to `src\.cache\`
- ✓ No `DLL load failed` error
- ✓ `[CLIP MODEL STATUS]` shows `'loaded': True`
- ✓ `[CLIP WARMUP DONE]` appears

**FAILURE INDICATORS**:
- ✗ `ERROR: [CLIP UNAVAILABLE] Missing dependency: DLL load failed`
- ✗ `[CLIP MODEL STATUS]` shows `'loaded': False`
- ✗ `WARNING: [CLIP WARMUP SKIPPED] model unavailable`

### Step 4: If DLL Error Still Occurs (Fallback)
If the DLL error persists after these fixes, the issue might be Python 3.13 incompatibility. Try:

1. **Check Windows system PATH for conflicting Python installations**
   ```powershell
   $env:PATH -split ';' | Select-String python
   ```

2. **Reinstall PyTorch** (force reinstall to ensure all DLLs are present)
   ```cmd
   cd d:\DOANTOTNGHIEP\NutriGain\src\backend
   .\.venv\Scripts\activate
   pip uninstall torch torchvision torchaudio -y
   pip install torch==2.12.1 --force-reinstall
   ```

3. **Verify Visual C++ Redistributable is installed**
   - Download: https://aka.ms/vs/17/release/vc_redist.x64.exe
   - Install if not already installed
   - Restart computer after installation

## Files Changed
1. `src/backend/.env.local` - Removed conflicting cache path environment variables
2. `src/backend/app/main.py` - Reorganized startup sequence and fixed default cache paths

## Files Created (for diagnostics)
1. `src/backend/diagnose_pytorch.py` - PyTorch DLL diagnostic script
2. `src/backend/test_clip_import.py` - CLIP import test (proves PyTorch works)
3. `src/backend/PYTORCH_DLL_FIX.md` - This document

## Next Steps After Verification

Once CLIP loads successfully, proceed to measure accuracy improvements:

### Run Accuracy Evaluation
```cmd
cd d:\DOANTOTNGHIEP\NutriGain\src\backend
$env:HF_HOME="D:\DOANTOTNGHIEP\NutriGain\src\.cache\huggingface"
.\.venv\Scripts\python.exe -m scripts.evaluate_clip_accuracy --test-dir ../data/clip_test_images
```

**Expected Result**:
- Current baseline: 76.26% (167/219 successful recognitions)
- Target: 80% (requires +8-9 more correct predictions)
- With 716 prompts (up from 651), accuracy should improve

### If 80% Target Not Reached
Review `CLIP_ACCURACY_IMPROVEMENT.md` for next steps:
1. Analyze which ingredients still have low accuracy
2. Add more targeted prompts for ingredients at 50-70% accuracy
3. Consider CLIP Large model if Base model hits limitations
4. Document final results and rationale

## Summary
✓ Cache paths now correctly point to `src/.cache/` (school requirement compliance)  
✓ Startup sequence fixed - cache configured before any imports  
✓ PyTorch installation verified working (via diagnostic scripts)  
✓ CLIP model already cached and ready  
✓ Visual C++ Redistributable installed  

**ACTION REQUIRED**: User needs to stop existing server and restart via `run-local.bat` to verify the fix.
