from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import func, inspect, select, text


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from app.core.database import SessionLocal, engine, wait_for_database  # noqa: E402
from app.models.entities import Food  # noqa: E402


DEFAULT_CSV_PATH = PROJECT_DIR / "data" / "food_dataset_ready_for_mysql.csv"


def text_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return None
    return text


def float_or_none(value: Any) -> float | None:
    text = text_or_none(value)
    if text is None:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def bool_value(value: Any) -> bool:
    text = text_or_none(value)
    if text is None:
        return False
    return text.lower() in {"1", "true", "yes", "y", "on"}


def first_text(row: dict[str, Any], *columns: str) -> str | None:
    for column in columns:
        value = text_or_none(row.get(column))
        if value is not None:
            return value
    return None


def first_float(row: dict[str, Any], *columns: str) -> float | None:
    for column in columns:
        value = float_or_none(row.get(column))
        if value is not None:
            return value
    return None


def food_db_columns() -> set[str]:
    inspector = inspect(engine)
    if "foods" not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns("foods")}


def add_if_supported(values: dict[str, Any], supported: set[str], key: str, value: Any) -> None:
    if key in supported:
        values[key] = value


def build_food_values(row: dict[str, Any], supported: set[str]) -> dict[str, Any] | None:
    food_id = first_text(row, "food_id")
    name = first_text(row, "dish_name_vi", "display_name", "name", "original_name")
    calories = first_float(row, "kcal_per_serving_clean", "calories")
    if not food_id or not name or calories is None or calories <= 0:
        return None

    protein = first_float(row, "protein_per_serving_clean", "protein")
    fat = first_float(row, "fat_per_serving_clean", "fat")
    carbs = first_float(row, "carbs_per_serving_clean", "carbs")
    clean_category = first_text(row, "clean_category")
    serving_g = first_float(row, "recommended_serving_g")

    values: dict[str, Any] = {"food_id": food_id}

    add_if_supported(values, supported, "name", name)
    add_if_supported(values, supported, "dish_name_vi", first_text(row, "dish_name_vi") or name)
    add_if_supported(values, supported, "display_name", first_text(row, "display_name") or name)
    add_if_supported(values, supported, "original_name", first_text(row, "original_name") or name)
    add_if_supported(values, supported, "name_vi", first_text(row, "dish_name_vi", "display_name") or name)

    add_if_supported(values, supported, "clean_category", clean_category)
    if "category" in supported and ("clean_category" not in supported or clean_category):
        values["category"] = clean_category
    add_if_supported(values, supported, "food_group_vi", first_text(row, "food_group_vi"))
    add_if_supported(values, supported, "meal_role", first_text(row, "meal_role"))
    add_if_supported(values, supported, "type", first_text(row, "meal_role"))

    add_if_supported(values, supported, "calories", calories)
    add_if_supported(values, supported, "protein", protein)
    add_if_supported(values, supported, "fat", fat)
    add_if_supported(values, supported, "carbs", carbs)
    add_if_supported(values, supported, "calories_raw", first_float(row, "calories"))
    add_if_supported(values, supported, "protein_raw", first_float(row, "protein"))
    add_if_supported(values, supported, "fat_raw", first_float(row, "fat"))
    add_if_supported(values, supported, "carbs_raw", first_float(row, "carbs"))

    add_if_supported(values, supported, "kcal_per_100g_clean", first_float(row, "kcal_per_100g_clean"))
    add_if_supported(values, supported, "protein_per_100g_clean", first_float(row, "protein_per_100g_clean"))
    add_if_supported(values, supported, "fat_per_100g_clean", first_float(row, "fat_per_100g_clean"))
    add_if_supported(values, supported, "carbs_per_100g_clean", first_float(row, "carbs_per_100g_clean"))
    add_if_supported(values, supported, "kcal_per_serving_clean", calories)
    add_if_supported(values, supported, "protein_per_serving_clean", protein)
    add_if_supported(values, supported, "fat_per_serving_clean", fat)
    add_if_supported(values, supported, "carbs_per_serving_clean", carbs)

    add_if_supported(values, supported, "recommended_serving_g", serving_g)
    add_if_supported(values, supported, "serving_grams", serving_g)
    add_if_supported(values, supported, "quantity_g", serving_g)
    add_if_supported(values, supported, "serving_display", first_text(row, "serving_display"))

    add_if_supported(values, supported, "menu_eligible", bool_value(row.get("menu_eligible")))
    add_if_supported(values, supported, "image_url", first_text(row, "image_url"))
    add_if_supported(values, supported, "image_alt_vi", first_text(row, "image_alt_vi"))
    add_if_supported(values, supported, "image_source_type", first_text(row, "image_source_type"))
    add_if_supported(values, supported, "image_verified", bool_value(row.get("image_verified")))
    add_if_supported(values, supported, "image_quality_note", first_text(row, "image_quality_note"))
    add_if_supported(values, supported, "quality_flags", first_text(row, "quality_flags"))
    add_if_supported(values, supported, "search_keywords", first_text(row, "search_keywords"))

    return values


def import_foods(csv_path: Path) -> dict[str, int]:
    wait_for_database()
    supported = set(Food.__table__.columns.keys()) & food_db_columns()
    if "food_id" not in supported:
        raise RuntimeError("Food model/database must contain foods.food_id")

    inserted = 0
    updated = 0
    skipped = 0

    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        with SessionLocal() as db:
            for row in reader:
                values = build_food_values(row, supported)
                if values is None:
                    skipped += 1
                    continue

                food_id = str(values["food_id"])
                food = db.get(Food, food_id)
                if food is None:
                    food = Food(food_id=food_id)
                    db.add(food)
                    inserted += 1
                else:
                    updated += 1

                for key, value in values.items():
                    if key != "food_id" and hasattr(food, key):
                        setattr(food, key, value)

            db.commit()
            if "id" in food_db_columns():
                db.execute(text("UPDATE foods SET id = food_id WHERE id IS NULL OR id = ''"))
                db.commit()
            total = int(db.scalar(select(func.count()).select_from(Food)) or 0)
            eligible = int(db.scalar(select(func.count()).select_from(Food).where(Food.menu_eligible.is_(True))) or 0)

    return {
        "inserted": inserted,
        "updated": updated,
        "skipped": skipped,
        "total_foods": total,
        "eligible_foods": eligible,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Upsert foods from food_dataset_ready_for_mysql.csv")
    parser.add_argument("--csv", default=str(DEFAULT_CSV_PATH), help="Path to food_dataset_ready_for_mysql.csv")
    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.is_absolute():
        csv_path = Path.cwd() / csv_path
    csv_path = csv_path.resolve()
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    result = import_foods(csv_path)
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
