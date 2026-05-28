from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def _table_columns(engine: Engine, table_name: str) -> set[str]:
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def _add_column_if_missing(engine: Engine, table_name: str, column_name: str, ddl: str) -> None:
    if column_name in _table_columns(engine, table_name):
        return
    with engine.begin() as connection:
        connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {ddl}"))


def ensure_database_schema(engine: Engine) -> None:
    """Small compatibility migration for existing local MySQL volumes.

    The project does not use Alembic yet; create_all creates new tables but will
    not add new columns to old tables. These ALTERs keep older demo databases
    usable after adding auth/user-specific history.
    """
    _add_column_if_missing(engine, "users", "auth_provider", "auth_provider VARCHAR(50) NULL DEFAULT 'email'")
    _add_column_if_missing(engine, "users", "google_sub", "google_sub VARCHAR(255) NULL")
    _add_column_if_missing(engine, "users", "email_verified", "email_verified BOOLEAN NOT NULL DEFAULT 0")
    _add_column_if_missing(engine, "users", "role", "role VARCHAR(30) NOT NULL DEFAULT 'USER'")
    _add_column_if_missing(engine, "users", "status", "status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE'")
    _add_column_if_missing(engine, "foods", "name", "name TEXT NULL")
    _add_column_if_missing(engine, "foods", "calories", "calories FLOAT NULL")
    _add_column_if_missing(engine, "foods", "protein", "protein FLOAT NULL")
    _add_column_if_missing(engine, "foods", "fat", "fat FLOAT NULL")
    _add_column_if_missing(engine, "foods", "carbs", "carbs FLOAT NULL")
    _add_column_if_missing(engine, "foods", "name_vi", "name_vi TEXT NULL")
    _add_column_if_missing(engine, "foods", "category", "category VARCHAR(100) NULL")
    _add_column_if_missing(engine, "foods", "type", "type VARCHAR(50) NULL")
    _add_column_if_missing(engine, "foods", "image_url", "image_url TEXT NULL")
    _add_column_if_missing(engine, "foods", "source", "source VARCHAR(100) NULL")
    _add_column_if_missing(engine, "foods", "original_name", "original_name TEXT NULL")
    _add_column_if_missing(engine, "foods", "display_name", "display_name TEXT NULL")
    _add_column_if_missing(engine, "foods", "dish_name_vi", "dish_name_vi TEXT NULL")
    _add_column_if_missing(engine, "foods", "clean_category", "clean_category VARCHAR(100) NULL")
    _add_column_if_missing(engine, "foods", "food_group_vi", "food_group_vi VARCHAR(255) NULL")
    _add_column_if_missing(engine, "foods", "meal_role", "meal_role VARCHAR(100) NULL")
    _add_column_if_missing(engine, "foods", "recommended_serving_g", "recommended_serving_g FLOAT NULL")
    _add_column_if_missing(engine, "foods", "serving_display", "serving_display VARCHAR(255) NULL")
    _add_column_if_missing(engine, "foods", "kcal_per_100g_clean", "kcal_per_100g_clean FLOAT NULL")
    _add_column_if_missing(engine, "foods", "protein_per_100g_clean", "protein_per_100g_clean FLOAT NULL")
    _add_column_if_missing(engine, "foods", "fat_per_100g_clean", "fat_per_100g_clean FLOAT NULL")
    _add_column_if_missing(engine, "foods", "carbs_per_100g_clean", "carbs_per_100g_clean FLOAT NULL")
    _add_column_if_missing(engine, "foods", "kcal_per_serving_clean", "kcal_per_serving_clean FLOAT NULL")
    _add_column_if_missing(engine, "foods", "protein_per_serving_clean", "protein_per_serving_clean FLOAT NULL")
    _add_column_if_missing(engine, "foods", "fat_per_serving_clean", "fat_per_serving_clean FLOAT NULL")
    _add_column_if_missing(engine, "foods", "carbs_per_serving_clean", "carbs_per_serving_clean FLOAT NULL")
    _add_column_if_missing(engine, "foods", "menu_eligible", "menu_eligible BOOLEAN NOT NULL DEFAULT 0")
    _add_column_if_missing(engine, "foods", "quality_flags", "quality_flags TEXT NULL")
    _add_column_if_missing(engine, "foods", "image_alt_vi", "image_alt_vi TEXT NULL")
    _add_column_if_missing(engine, "foods", "image_source_type", "image_source_type VARCHAR(100) NULL")
    _add_column_if_missing(engine, "foods", "image_verified", "image_verified BOOLEAN NOT NULL DEFAULT 0")
    _add_column_if_missing(engine, "foods", "image_quality_note", "image_quality_note TEXT NULL")
    _add_column_if_missing(engine, "foods", "search_keywords", "search_keywords TEXT NULL")
    _add_column_if_missing(engine, "foods", "excluded_from_recommendation", "excluded_from_recommendation BOOLEAN NOT NULL DEFAULT 0")
    _add_column_if_missing(engine, "foods", "admin_rejected", "admin_rejected BOOLEAN NOT NULL DEFAULT 0")
    _add_column_if_missing(engine, "foods", "exclusion_reason", "exclusion_reason TEXT NULL")
    _add_column_if_missing(engine, "foods", "is_common_food", "is_common_food BOOLEAN NOT NULL DEFAULT 0")
    _add_column_if_missing(engine, "foods", "is_budget_friendly", "is_budget_friendly BOOLEAN NOT NULL DEFAULT 0")
    _add_column_if_missing(engine, "foods", "is_premium", "is_premium BOOLEAN NOT NULL DEFAULT 0")
    _add_column_if_missing(engine, "foods", "is_processed", "is_processed BOOLEAN NOT NULL DEFAULT 0")
    _add_column_if_missing(engine, "foods", "is_natural_food", "is_natural_food BOOLEAN NOT NULL DEFAULT 0")
    _add_column_if_missing(engine, "foods", "budget_tier", "budget_tier VARCHAR(20) NOT NULL DEFAULT 'standard'")
    _add_column_if_missing(engine, "foods", "natural_priority_score", "natural_priority_score FLOAT NOT NULL DEFAULT 0.5")

    _add_column_if_missing(engine, "recommendation_requests", "user_id", "user_id INTEGER NULL")
    _add_column_if_missing(engine, "recommendation_requests", "bmr", "bmr FLOAT NULL")
    _add_column_if_missing(engine, "recommendation_requests", "tdee", "tdee FLOAT NULL")
    _add_column_if_missing(engine, "meal_plan_items", "meal_id", "meal_id INTEGER NULL")
    _add_column_if_missing(engine, "meal_plan_items", "serving_grams", "serving_grams FLOAT NULL")
    _add_column_if_missing(engine, "food_log_items", "meal_plan_item_id", "meal_plan_item_id INTEGER NULL")
    _add_column_if_missing(engine, "user_profiles", "favorite_foods", "favorite_foods TEXT NULL")
    _add_column_if_missing(engine, "user_profiles", "disliked_foods", "disliked_foods TEXT NULL")
    _add_column_if_missing(engine, "user_profiles", "disliked_food_groups", "disliked_food_groups TEXT NULL")
    _add_column_if_missing(engine, "user_profiles", "target_weight_kg", "target_weight_kg FLOAT NULL")
    _add_column_if_missing(engine, "user_profiles", "target_duration_value", "target_duration_value INTEGER NULL")
    _add_column_if_missing(engine, "user_profiles", "target_duration_unit", "target_duration_unit VARCHAR(20) NULL")
    _add_column_if_missing(engine, "user_profiles", "target_duration_months", "target_duration_months FLOAT NULL")
    _add_column_if_missing(engine, "user_profiles", "target_gain_rate_kg_per_month", "target_gain_rate_kg_per_month FLOAT NULL")
    _add_column_if_missing(engine, "user_profiles", "weight_gain_speed", "weight_gain_speed VARCHAR(50) NULL")
    _add_column_if_missing(engine, "user_profiles", "diet_type", "diet_type VARCHAR(50) NULL")
    _add_column_if_missing(engine, "user_profiles", "budget_level", "budget_level VARCHAR(50) NULL")
    _add_column_if_missing(engine, "user_profiles", "items_per_meal", "items_per_meal INTEGER NULL")
    _add_column_if_missing(engine, "user_profiles", "breakfast_time", "breakfast_time VARCHAR(5) NULL")
    _add_column_if_missing(engine, "user_profiles", "lunch_time", "lunch_time VARCHAR(5) NULL")
    _add_column_if_missing(engine, "user_profiles", "dinner_time", "dinner_time VARCHAR(5) NULL")
    _add_column_if_missing(engine, "user_profiles", "meal_reminder_enabled", "meal_reminder_enabled BOOLEAN NOT NULL DEFAULT 0")
    _add_column_if_missing(engine, "user_profiles", "reminder_email", "reminder_email VARCHAR(255) NULL")
    _add_column_if_missing(engine, "user_profiles", "gender", "gender VARCHAR(20) NULL")
    _add_column_if_missing(engine, "weight_logs", "source", "source VARCHAR(50) NULL")
    _add_column_if_missing(engine, "weight_logs", "is_chart_milestone", "is_chart_milestone BOOLEAN NOT NULL DEFAULT 0")
    _add_column_if_missing(engine, "weight_logs", "updated_at", "updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")

    inspector = inspect(engine)
    if "meal_consumption_logs" not in inspector.get_table_names():
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    CREATE TABLE meal_consumption_logs (
                        id INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        meal_plan_id VARCHAR(255) NOT NULL,
                        food_id VARCHAR(255) NOT NULL,
                        meal_type VARCHAR(50) NULL,
                        status VARCHAR(50) NOT NULL DEFAULT 'eaten',
                        consumed_at DATETIME NULL,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        kcal FLOAT NULL,
                        protein FLOAT NULL,
                        INDEX idx_meal_consumption_logs_user_id (user_id),
                        INDEX idx_meal_consumption_logs_meal_plan_id (meal_plan_id)
                    )
                    """
                )
            )
    else:
        _add_column_if_missing(engine, "meal_consumption_logs", "meal_type", "meal_type VARCHAR(50) NULL")
        _add_column_if_missing(engine, "meal_consumption_logs", "status", "status VARCHAR(50) NOT NULL DEFAULT 'eaten'")
        _add_column_if_missing(engine, "meal_consumption_logs", "consumed_at", "consumed_at DATETIME NULL")
        _add_column_if_missing(engine, "meal_consumption_logs", "created_at", "created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP")
        _add_column_if_missing(engine, "meal_consumption_logs", "kcal", "kcal FLOAT NULL")
        _add_column_if_missing(engine, "meal_consumption_logs", "protein", "protein FLOAT NULL")

    inspector = inspect(engine)
    if "error_logs" not in inspector.get_table_names():
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    CREATE TABLE error_logs (
                        id INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY,
                        user_id INTEGER NULL,
                        endpoint VARCHAR(255) NULL,
                        error_type VARCHAR(100) NOT NULL,
                        message TEXT NULL,
                        stack_trace TEXT NULL,
                        status VARCHAR(30) NOT NULL DEFAULT 'OPEN',
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
            )

    if "password_reset_tokens" not in inspector.get_table_names():
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    CREATE TABLE password_reset_tokens (
                        id INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        token_hash VARCHAR(64) NOT NULL UNIQUE,
                        expires_at DATETIME NOT NULL,
                        used_at DATETIME NULL,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_password_reset_tokens_user_id (user_id),
                        INDEX idx_password_reset_tokens_token_hash (token_hash)
                    )
                    """
                )
            )

    if "email_verification_tokens" not in inspector.get_table_names():
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    CREATE TABLE email_verification_tokens (
                        id INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY,
                        user_id INTEGER NOT NULL UNIQUE,
                        code_hash VARCHAR(64) NOT NULL,
                        expires_at DATETIME NOT NULL,
                        attempts INTEGER NOT NULL DEFAULT 0,
                        last_sent_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        consumed_at DATETIME NULL,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        INDEX idx_email_verification_tokens_user_id (user_id)
                    )
                    """
                )
            )

    if "meal_reminder_logs" not in inspector.get_table_names():
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    CREATE TABLE meal_reminder_logs (
                        id INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        meal_type VARCHAR(20) NOT NULL,
                        scheduled_time VARCHAR(5) NULL,
                        reminder_date DATE NOT NULL,
                        sent_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        status VARCHAR(20) NOT NULL DEFAULT 'sent',
                        error_message VARCHAR(255) NULL,
                        UNIQUE KEY uq_meal_reminder_user_meal_date (user_id, meal_type, reminder_date),
                        INDEX idx_meal_reminder_logs_user_id (user_id),
                        INDEX idx_meal_reminder_logs_reminder_date (reminder_date)
                    )
                    """
                )
            )
    else:
        _add_column_if_missing(engine, "meal_reminder_logs", "scheduled_time", "scheduled_time VARCHAR(5) NULL")

    with engine.begin() as connection:
        connection.execute(text("UPDATE users SET role = UPPER(role) WHERE role IS NOT NULL"))
        connection.execute(text("UPDATE users SET role = 'USER' WHERE role IS NULL OR role = ''"))
        connection.execute(text("UPDATE users SET status = 'LOCKED' WHERE is_active = 0"))
        connection.execute(text("UPDATE users SET status = 'ACTIVE' WHERE status IS NULL OR status = ''"))
        connection.execute(text("UPDATE users SET email_verified = 1 WHERE email_verified IS NULL OR email_verified = 0"))
        connection.execute(
            text(
                """
                UPDATE foods
                SET
                    name = COALESCE(name, display_name, original_name, dish_name_vi),
                    name_vi = COALESCE(name_vi, dish_name_vi),
                    category = COALESCE(category, clean_category, 'other'),
                    calories = COALESCE(calories, kcal_per_serving_clean, 0),
                    protein = COALESCE(protein, protein_per_serving_clean, 0),
                    fat = COALESCE(fat, fat_per_serving_clean, 0),
                    carbs = COALESCE(carbs, carbs_per_serving_clean, 0)
                """
            )
        )
        connection.execute(
            text(
                """
                UPDATE foods
                SET category = 'plant_protein'
                WHERE LOWER(CONCAT(COALESCE(name, ''), ' ', COALESCE(name_vi, ''))) LIKE '%white bean%'
                   OR LOWER(CONCAT(COALESCE(name, ''), ' ', COALESCE(name_vi, ''))) LIKE '%small white%'
                   OR LOWER(CONCAT(COALESCE(name, ''), ' ', COALESCE(name_vi, ''))) LIKE '%đậu trắng%'
                """
            )
        )
        connection.execute(
            text(
                """
                UPDATE foods
                SET category = 'plant_protein'
                WHERE LOWER(CONCAT(COALESCE(name, ''), ' ', COALESCE(name_vi, ''))) LIKE '%bean%'
                   OR LOWER(CONCAT(COALESCE(name, ''), ' ', COALESCE(name_vi, ''))) LIKE '%lentil%'
                   OR LOWER(CONCAT(COALESCE(name, ''), ' ', COALESCE(name_vi, ''))) LIKE '%chickpea%'
                   OR LOWER(CONCAT(COALESCE(name, ''), ' ', COALESCE(name_vi, ''))) LIKE '%soybean%'
                   OR LOWER(CONCAT(COALESCE(name, ''), ' ', COALESCE(name_vi, ''))) LIKE '%tofu%'
                """
            )
        )
        connection.execute(
            text(
                """
                UPDATE foods
                SET category = 'dairy'
                WHERE LOWER(CONCAT(COALESCE(name, ''), ' ', COALESCE(name_vi, ''))) LIKE '%soy yogurt%'
                   OR LOWER(CONCAT(COALESCE(name, ''), ' ', COALESCE(name_vi, ''))) LIKE '%tofu yogurt%'
                   OR LOWER(CONCAT(COALESCE(name, ''), ' ', COALESCE(name_vi, ''))) LIKE '%sữa chua đậu nành%'
                   OR LOWER(CONCAT(COALESCE(name, ''), ' ', COALESCE(name_vi, ''))) LIKE '%sữa chua đậu phụ%'
                """
            )
        )
        connection.execute(
            text(
                """
                UPDATE foods
                SET category = 'grain'
                WHERE LOWER(CONCAT(COALESCE(name, ''), ' ', COALESCE(name_vi, ''))) LIKE '%pasta%'
                   OR LOWER(CONCAT(COALESCE(name, ''), ' ', COALESCE(name_vi, ''))) LIKE '%spaghetti%'
                   OR LOWER(CONCAT(COALESCE(name, ''), ' ', COALESCE(name_vi, ''))) LIKE '%macaroni%'
                   OR LOWER(CONCAT(COALESCE(name, ''), ' ', COALESCE(name_vi, ''))) LIKE '%noodle%'
                   OR LOWER(CONCAT(COALESCE(name, ''), ' ', COALESCE(name_vi, ''))) LIKE '%potato%'
                   OR LOWER(CONCAT(COALESCE(name, ''), ' ', COALESCE(name_vi, ''))) LIKE '%corn%'
                """
            )
        )
        connection.execute(
            text(
                """
                UPDATE foods
                SET category = 'vegetable'
                WHERE LOWER(CONCAT(COALESCE(name, ''), ' ', COALESCE(name_vi, ''))) LIKE '%grape leaves%'
                   OR LOWER(CONCAT(COALESCE(name, ''), ' ', COALESCE(name_vi, ''))) LIKE '%leaf%'
                   OR LOWER(CONCAT(COALESCE(name, ''), ' ', COALESCE(name_vi, ''))) LIKE '%greens%'
                """
            )
        )
