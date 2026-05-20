from __future__ import annotations

import os


DEFAULT_FOOD_DATASET_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../data/food_dataset_fixed.csv")
)


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value in (None, ""):
        return default
    try:
        return int(value)
    except ValueError:
        return default


class Settings:
    app_name: str = os.getenv("APP_NAME", "NutriGain API")
    app_env: str = os.getenv("APP_ENV", "development")
    app_host: str = os.getenv("APP_HOST", "0.0.0.0")
    app_port: int = _int_env("APP_PORT", 8000)

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
    reset_password_token_expire_minutes: int = _int_env("RESET_PASSWORD_TOKEN_EXPIRE_MINUTES", 30)
    smtp_host: str = os.getenv("SMTP_HOST", "")
    smtp_port: int = _int_env("SMTP_PORT", 0)
    smtp_user: str = os.getenv("SMTP_USER", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    smtp_from: str = os.getenv("SMTP_FROM", "")


settings = Settings()
