from __future__ import annotations

import os
from pathlib import Path

# Load .env file before importing settings
try:
    from dotenv import load_dotenv
    # Try to load .env.local first (for local development), then fallback to .env
    backend_dir = Path(__file__).parent.parent
    env_local_file = backend_dir / ".env.local"
    env_file = backend_dir / ".env"
    
    if env_local_file.exists():
        load_dotenv(env_local_file)
        print(f"[DOTENV] Loaded {env_local_file}")
    elif env_file.exists():
        load_dotenv(env_file)
        print(f"[DOTENV] Loaded {env_file}")
    else:
        print(f"[DOTENV] No .env or .env.local file found in {backend_dir}")
except ImportError:
    print("[DOTENV] python-dotenv not installed, skipping .env load")
except Exception as e:
    print(f"[DOTENV] Error loading .env: {e}")

# Configure Hugging Face cache BEFORE importing any HF/transformers modules
def _configure_hf_cache():
    """Configure Hugging Face cache paths to use D drive instead of C drive"""
    project_root = Path(__file__).parent.parent.parent
    default_hf_home = str(project_root / "hf-cache")
    default_hub_cache = str(project_root / "hf-cache" / "hub")
    default_transformers_cache = str(project_root / "hf-cache" / "transformers")
    default_torch_home = str(project_root / "torch-cache")
    
    # Set environment variables with defaults
    os.environ.setdefault("HF_HOME", os.getenv("HF_HOME") or default_hf_home)
    os.environ.setdefault("HUGGINGFACE_HUB_CACHE", os.getenv("HUGGINGFACE_HUB_CACHE") or default_hub_cache)
    os.environ.setdefault("HF_HUB_CACHE", os.getenv("HF_HUB_CACHE") or default_hub_cache)
    os.environ.setdefault("TRANSFORMERS_CACHE", os.getenv("TRANSFORMERS_CACHE") or default_transformers_cache)
    os.environ.setdefault("TORCH_HOME", os.getenv("TORCH_HOME") or default_torch_home)
    
    # Create directories if they don't exist
    for env_var in ["HF_HOME", "HUGGINGFACE_HUB_CACHE", "HF_HUB_CACHE", "TRANSFORMERS_CACHE", "TORCH_HOME"]:
        cache_path = os.environ.get(env_var)
        if cache_path:
            try:
                Path(cache_path).mkdir(parents=True, exist_ok=True)
            except Exception as e:
                print(f"[HF CACHE] Warning: Failed to create {env_var} directory {cache_path}: {e}")
    
    # Log cache configuration
    print("[CLIP CACHE CONFIG] Hugging Face cache paths:")
    print(f"  HF_HOME: {os.environ.get('HF_HOME')}")
    print(f"  HUGGINGFACE_HUB_CACHE: {os.environ.get('HUGGINGFACE_HUB_CACHE')}")
    print(f"  HF_HUB_CACHE: {os.environ.get('HF_HUB_CACHE')}")
    print(f"  TRANSFORMERS_CACHE: {os.environ.get('TRANSFORMERS_CACHE')}")
    print(f"  TORCH_HOME: {os.environ.get('TORCH_HOME')}")
    
    # Check if cache is still pointing to C drive (Windows only)
    hf_home = os.environ.get("HF_HOME", "")
    if hf_home.upper().startswith("C:") or hf_home.upper().startswith("C\\"):
        print(f"[CLIP CACHE WARNING] Hugging Face cache is still on C drive: {hf_home}")

_configure_hf_cache()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import settings
from app.core.database import Base, engine, wait_for_database
from app.core.migrations import ensure_database_schema
from app.models import entities  # noqa: F401
from app.services.meal_reminder_service import start_meal_reminder_scheduler, stop_meal_reminder_scheduler


app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def run_db_repairs() -> None:
    from app.core.database import SessionLocal
    from app.models.entities import User, UserProfileEntity, WeightLog
    from datetime import date, datetime
    from zoneinfo import ZoneInfo
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "nhi96942@gmail.com").first()
        if not user:
            print("[REPAIR] User nhi96942@gmail.com not found")
            return
        
        # Find weight_log with weight_kg=38, source="profile_update" newest
        logs = db.query(WeightLog).filter(
            WeightLog.user_id == user.id,
            WeightLog.weight_kg == 38.0,
            WeightLog.source == "profile_update"
        ).order_by(WeightLog.id.desc()).all()

        VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
        target_date = date(2026, 5, 11)

        if logs:
            log = logs[0]
            print(f"[REPAIR] Found log to repair: ID={log.id}, log_date={log.log_date}, created_at={log.created_at}")
        else:
            profile = db.query(UserProfileEntity).filter(UserProfileEntity.user_id == user.id).first()
            if not profile or float(profile.weight_kg or 0) != 38.0:
                print("[REPAIR] No weight log of 38kg with source 'profile_update' found, and profile is not 38kg")
                return

            log = db.query(WeightLog).filter(
                WeightLog.user_id == user.id,
                WeightLog.log_date == target_date,
            ).order_by(WeightLog.id.desc()).first()
            if log:
                print(f"[REPAIR] Found existing log on target date to repair: ID={log.id}, weight={log.weight_kg}, source={log.source}")
            else:
                log = WeightLog(
                    user_id=user.id,
                    weight_kg=38.0,
                    log_date=target_date,
                    source="profile_update",
                    is_chart_milestone=False,
                )
                db.add(log)
                print("[REPAIR] No 38kg profile_update log found; creating missing 2026-05-11 profile_update log")
        
        # Set log_date to 2026-05-11
        log.weight_kg = 38.0
        log.log_date = target_date
        log.source = "profile_update"
        
        # Store weight log timestamps as Vietnam local time.
        dt_vn = datetime(2026, 5, 11, 12, 0, 0, tzinfo=VN_TZ)
        
        log.created_at = dt_vn
        log.updated_at = dt_vn
        
        db.commit()
        print(f"[REPAIR] Repair successful! ID={log.id}, log_date={log.log_date}, created_at={log.created_at}")
    except Exception as e:
        db.rollback()
        print(f"[REPAIR] Error during repair: {e}")
    finally:
        db.close()


@app.on_event("startup")
def startup() -> None:
    wait_for_database()
    Base.metadata.create_all(bind=engine)
    ensure_database_schema(engine)
    run_db_repairs()
    start_meal_reminder_scheduler()
    
    # Warm up CLIP model in background to avoid timeout on first image recognition
    import threading
    def warmup_clip():
        try:
            from app.services.clip_ingredient_service import warmup_clip_model
            warmup_clip_model()
        except Exception as e:
            print(f"[CLIP WARMUP] Error: {e}")
    
    threading.Thread(target=warmup_clip, daemon=True).start()


app.include_router(router)


@app.on_event("shutdown")
def shutdown() -> None:
    stop_meal_reminder_scheduler()
