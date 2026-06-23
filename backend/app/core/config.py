from __future__ import annotations

import os
from dotenv import load_dotenv


# Load environment variables from .env file
env_file_path = os.path.join(os.path.dirname(__file__), "../../.env")
load_dotenv(env_file_path)

# Debug: print to verify .env is loaded
print(f"[CONFIG DEBUG] Loading .env from: {os.path.abspath(env_file_path)}")
print(f"[CONFIG DEBUG] SMSGATE_URL = {os.getenv('SMSGATE_URL', 'NOT SET')}")
print(f"[CONFIG DEBUG] SMSGATE_USERNAME = {os.getenv('SMSGATE_USERNAME', 'NOT SET')}")
print(f"[CONFIG DEBUG] SMSGATE_PASSWORD = {os.getenv('SMSGATE_PASSWORD', 'NOT SET')}")


DEFAULT_FOOD_DATASET_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../data/food_dataset_fixed.csv")
)


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value in (None, ""):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value in (None, ""):
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    app_name: str = os.getenv("APP_NAME", "NutriGain API")
    app_env: str = os.getenv("APP_ENV", "development")
    app_host: str = os.getenv("APP_HOST", "0.0.0.0")
    app_port: int = _int_env("APP_PORT", 8000)
    app_timezone: str = os.getenv("APP_TIMEZONE", "Asia/Ho_Chi_Minh")

    database_url: str = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://nutrigain:nutrigain@db:3306/nutrigain",
    )

    food_dataset_path: str = os.getenv("FOOD_DATASET_PATH", DEFAULT_FOOD_DATASET_PATH)
    raw_data_path: str = os.getenv("RAW_DATA_PATH", food_dataset_path)
    scaled_data_path: str = os.getenv("SCALED_DATA_PATH", food_dataset_path)
    user_history_path: str = os.getenv("USER_HISTORY_PATH", "/app/user_history.csv")
    preference_model_path: str = os.getenv("PREFERENCE_MODEL_PATH", "/app/preference_model.joblib")

    frontend_origin: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
    frontend_url: str = os.getenv("FRONTEND_URL", frontend_origin)
    jwt_secret_key: str = os.getenv(
        "JWT_SECRET_KEY",
        "dev-only-change-this-secret-before-production",
    )
    access_token_expire_minutes: int = _int_env("ACCESS_TOKEN_EXPIRE_MINUTES", 1440)
    google_client_id: str | None = os.getenv("GOOGLE_CLIENT_ID", None)
    google_client_secret: str | None = os.getenv("GOOGLE_CLIENT_SECRET", None)
    google_redirect_uri: str = os.getenv(
        "GOOGLE_REDIRECT_URI",
        "http://localhost:8000/api/v1/auth/google/callback",
    )
    reset_password_token_expire_minutes: int = _int_env("RESET_PASSWORD_TOKEN_EXPIRE_MINUTES", 30)
    smtp_host: str = os.getenv("SMTP_HOST", "")
    smtp_port: int = _int_env("SMTP_PORT", 587)
    smtp_user: str = os.getenv("SMTP_USER", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    smtp_from: str = os.getenv("SMTP_FROM", "")
    smtp_use_tls: bool = _bool_env("SMTP_USE_TLS", True)
    # SMSGate SMS settings (Basic Auth + JWT token)
    smsgate_url: str = os.getenv("SMSGATE_URL", "")
    smsgate_username: str = os.getenv("SMSGATE_USERNAME", "")
    smsgate_password: str = os.getenv("SMSGATE_PASSWORD", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_vision_model: str = os.getenv("OPENAI_VISION_MODEL", "gpt-4o-mini")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    ai_provider: str = os.getenv("AI_PROVIDER", "gemini")
    enable_ingredient_image_recognition: bool = _bool_env("ENABLE_INGREDIENT_IMAGE_RECOGNITION", True)
    
    # Hugging Face cache paths - Dùng ổ D để tránh hết dung lượng ổ C
    hf_home: str | None = os.getenv("HF_HOME", None)
    huggingface_hub_cache: str | None = os.getenv("HUGGINGFACE_HUB_CACHE", None)
    hf_hub_cache: str | None = os.getenv("HF_HUB_CACHE", None)
    transformers_cache: str | None = os.getenv("TRANSFORMERS_CACHE", None)
    torch_home: str | None = os.getenv("TORCH_HOME", None)


settings = Settings()
