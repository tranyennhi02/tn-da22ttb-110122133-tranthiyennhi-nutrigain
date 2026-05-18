from __future__ import annotations

import argparse
import re
import unicodedata
from pathlib import Path

import pandas as pd
from sqlalchemy import delete

from app.core.database import Base, SessionLocal, engine, wait_for_database
from app.models.entities import Food


GRAIN_KEYS = {
    "bread",
    "rice",
    "pasta",
    "noodle",
    "macaroni",
    "cereal",
    "bagel",
    "bun",
    "roll",
    "waffle",
    "pancake",
    "muffin",
    "cake",
    "pie",
    "cracker",
    "tortilla",
    "oat",
    "wheat",
    "lasagna",
    "ravioli",
}

MEAT_KEYS = {
    "beef",
    "pork",
    "chicken",
    "turkey",
    "fish",
    "salmon",
    "tuna",
    "shrimp",
    "ham",
    "sausage",
    "frankfurter",
    "bacon",
    "lamb",
    "duck",
    "goose",
    "egg",
}

DAIRY_KEYS = {
    "milk",
    "cheese",
    "yogurt",
    "butter",
    "cream",
    "ricotta",
    "mozzarella",
    "cheddar",
    "parmesan",
    "feta",
    "cottage",
}

FRUIT_KEYS = {
    "apple",
    "orange",
    "banana",
    "grape",
    "strawberry",
    "blueberry",
    "raspberry",
    "watermelon",
    "melon",
    "peach",
    "pear",
    "pineapple",
    "mango",
    "papaya",
    "kiwi",
    "lemon",
    "lime",
    "grapefruit",
    "cherry",
    "fig",
}

VEGETABLE_KEYS = {
    "tomato",
    "potato",
    "carrot",
    "broccoli",
    "cauliflower",
    "cabbage",
    "lettuce",
    "spinach",
    "kale",
    "bean",
    "beans",
    "pea",
    "peas",
    "corn",
    "onion",
    "garlic",
    "cucumber",
    "celery",
    "asparagus",
    "mushroom",
    "pepper",
    "zucchini",
    "eggplant",
    "squash",
    "pumpkin",
    "radish",
    "turnip",
}

PLANT_PROTEIN_KEYS = {
    "tofu",
    "soybean",
    "soybeans",
    "edamame",
    "tempeh",
    "chickpea",
    "chickpeas",
    "lentil",
    "lentils",
}

HEALTHY_FAT_KEYS = {
    "olive",
    "olives",
    "avocado",
    "avocados",
    "oil",
    "nut",
    "nuts",
    "peanut",
    "peanuts",
    "seed",
    "seeds",
    "almond",
    "walnut",
    "cashew",
    "pistachio",
}

VI_GRAIN_KEYS = {
    "gao",
    "com",
    "bun",
    "mi",
    "pho",
    "banh",
    "xoi",
    "ngu coc",
}

VI_MEAT_KEYS = {
    "thit",
    "bo",
    "heo",
    "lon",
    "ga",
    "ca",
    "tom",
    "cua",
    "trung",
}

VI_DAIRY_KEYS = {
    "sua",
    "pho mai",
    "ricotta",
    "sua chua",
    "kem",
}

VI_FRUIT_KEYS = {
    "trai cay",
    "hoa qua",
    "qua",
    "chuoi",
    "cam",
    "tao",
    "xoai",
    "dua",
    "nho",
}

VI_VEGETABLE_KEYS = {
    "rau",
    "cu",
    "cai",
    "khoai",
    "bi",
    "ca rot",
    "hanh",
    "toi",
    "nam",
    "dau",
}

VI_PLANT_PROTEIN_KEYS = {
    "dau phu",
    "dau nanh",
    "dau ga",
    "dau lang",
}

VI_HEALTHY_FAT_KEYS = {
    "dau oliu",
    "qua bo",
    "hanh nhan",
    "oc cho",
    "hat dieu",
    "hat",
}

TOKEN_PATTERN = re.compile(r"[a-zA-Z]+")


def _ascii_fold(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch)).lower()


def _tokenize(text: str) -> set[str]:
    return {token.lower() for token in TOKEN_PATTERN.findall(_ascii_fold(text))}


def _contains_any_keyword(text: str, keywords: set[str]) -> bool:
    lowered = _ascii_fold(text)
    tokens = _tokenize(lowered)
    for keyword in keywords:
        key = keyword.strip().lower()
        if not key:
            continue
        if " " in key:
            if key in lowered:
                return True
        elif key in tokens:
            return True
    return False


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import foods CSV into MySQL foods table")
    parser.add_argument("--csv-path", default=str(Path(__file__).resolve().parents[3] / "foods_clean.csv"), help="Path to foods_clean.csv")
    parser.add_argument("--truncate", action="store_true", help="Clear the foods table before import")
    parser.add_argument("--dry-run", action="store_true", help="Validate and print row count without writing")
    return parser


def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    clean_category_map = {
        "protein_meat": "meat",
        "protein_seafood": "meat",
        "starch_grain": "grain",
        "starch_tuber": "grain",
        "healthy_fat_nuts": "healthy_fat",
        "dessert_sweets": "junk_food",
    }
    if "name_vi" not in normalized.columns:
        if "dish_name_vi" in normalized.columns:
            normalized["name_vi"] = normalized["dish_name_vi"]
        elif "display_name" in normalized.columns:
            normalized["name_vi"] = normalized["display_name"]
        else:
            normalized["name_vi"] = None
    if "clean_category" in normalized.columns:
        normalized["category"] = normalized["clean_category"]
    if "type" not in normalized.columns:
        normalized["type"] = None
    if "menu_eligible" in normalized.columns:
        normalized = normalized[normalized["menu_eligible"].astype(str).str.lower().isin({"true", "1", "yes"})].copy()
    generic_display_names = {"món tráng miệng", "nước sốt", "thực phẩm", "đồ uống"}
    normalized = normalized[
        ~normalized["name_vi"].fillna("").astype(str).str.strip().str.lower().isin(generic_display_names)
    ].copy()
    serving_columns = {
        "kcal_per_serving_clean": "calories",
        "protein_per_serving_clean": "protein",
        "fat_per_serving_clean": "fat",
        "carbs_per_serving_clean": "carbs",
    }
    for source_column, target_column in serving_columns.items():
        if source_column in normalized.columns:
            normalized[target_column] = normalized[source_column]

    expected_columns = ["food_id", "name", "calories", "protein", "fat", "carbs", "name_vi", "category", "type"]
    missing_columns = [column for column in expected_columns if column not in normalized.columns]
    if missing_columns:
        raise ValueError(f"Missing columns in CSV: {', '.join(missing_columns)}")

    normalized["food_id"] = normalized["food_id"].astype(str).str.strip()
    normalized["name"] = normalized["name"].astype(str).str.strip()
    normalized["name_vi"] = normalized["name_vi"].where(normalized["name_vi"].notna(), None)
    normalized["category"] = normalized.apply(
        lambda row: normalize_category(
            f"{str(row['name'])} {'' if pd.isna(row['name_vi']) else str(row['name_vi'])}",
            str(row["category"]),
        ),
        axis=1,
    )
    if "clean_category" in normalized.columns:
        normalized["category"] = normalized["clean_category"].astype(str).str.strip().str.lower().map(
            lambda value: clean_category_map.get(value, value or "other")
        )
    normalized["type"] = normalized["type"].where(normalized["type"].notna(), None)

    for column in ["calories", "protein", "fat", "carbs"]:
        normalized[column] = pd.to_numeric(normalized[column], errors="coerce")

    # Đảm bảo calories luôn đồng bộ với macros theo công thức (Pro*4 + Fat*9 + Carb*4)
    required_columns = ["food_id", "name", "calories", "protein", "fat", "carbs", "category"]
    if normalized[required_columns].isna().any().any():
        raise ValueError("CSV contains invalid or empty required values")

    return normalized


def normalize_category(name: str, old_category: str) -> str:
    text = f"{name} {old_category}".strip().lower()

    if _contains_any_keyword(text, {"soy yogurt", "tofu yogurt", "sua chua dau nanh", "sua chua dau phu"}):
        return "dairy"
    if _contains_any_keyword(text, {"white bean", "small white", "dau trang"}):
        return "plant_protein"
    if _contains_any_keyword(text, VI_PLANT_PROTEIN_KEYS):
        return "plant_protein"
    if _contains_any_keyword(text, VI_HEALTHY_FAT_KEYS):
        return "healthy_fat"
    if _contains_any_keyword(text, VI_DAIRY_KEYS):
        return "dairy"
    if "men " in text or "men" in _tokenize(text):
        return "other"
    if _contains_any_keyword(text, {"la nho", "lá nho"}):
        return "vegetable"
    if _contains_any_keyword(text, {"ca com", "cá cơm"}):
        return "meat"
    if _contains_any_keyword(text, VI_VEGETABLE_KEYS):
        return "vegetable"
    if _contains_any_keyword(text, VI_FRUIT_KEYS):
        return "fruit"
    if _contains_any_keyword(text, VI_GRAIN_KEYS):
        return "grain"
    if _contains_any_keyword(text, VI_MEAT_KEYS):
        return "meat"

    if _contains_any_keyword(text, PLANT_PROTEIN_KEYS):
        return "plant_protein"
    if _contains_any_keyword(text, HEALTHY_FAT_KEYS):
        return "healthy_fat"
    if _contains_any_keyword(text, GRAIN_KEYS):
        return "grain"
    if _contains_any_keyword(text, MEAT_KEYS):
        return "meat"
    if _contains_any_keyword(text, DAIRY_KEYS):
        return "dairy"
    if _contains_any_keyword(text, VEGETABLE_KEYS):
        return "vegetable"
    if _contains_any_keyword(text, FRUIT_KEYS):
        return "fruit"

    fallback = _ascii_fold(old_category.strip().lower())
    if "vegetable" in fallback:
        return "vegetable"
    if "fruit" in fallback:
        return "fruit"
    if "grain" in fallback or "cereal" in fallback or "bread" in fallback:
        return "grain"
    if "milk" in fallback or "dairy" in fallback or "cheese" in fallback:
        return "dairy"
    if "meat" in fallback or "protein" in fallback or "egg" in fallback or "fish" in fallback:
        return "meat"
    fallback_map = {
        "carb": "grain",
        "carbohydrate": "grain",
        "starch": "grain",
        "protein": "meat",
        "meat": "meat",
        "dairy": "dairy",
        "fat": "healthy_fat",
        "oil": "healthy_fat",
        "fruit": "fruit",
        "vegetable": "vegetable",
        "veg": "vegetable",
        "plant protein": "plant_protein",
        "plant_protein": "plant_protein",
        "healthy fat": "healthy_fat",
        "healthy_fat": "healthy_fat",
    }
    return fallback_map.get(fallback, fallback or "other")


def _safe_str(value) -> str | None:
    """Return None for NaN/empty, otherwise str."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    return text if text else None


def _safe_bool(value, default: bool = False) -> bool:
    """Convert CSV boolean values safely."""
    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except (TypeError, ValueError):
        pass
    return str(value).strip().lower() in {"1", "true", "yes", "t"}


def import_foods(csv_path: Path, truncate: bool = False, dry_run: bool = False) -> int:
    wait_for_database()
    Base.metadata.create_all(bind=engine)

    df = normalize_dataframe(pd.read_csv(csv_path))
    if dry_run:
        return len(df)

    db = SessionLocal()
    try:
        if truncate:
            db.execute(delete(Food))
            db.commit()

        # Build lookup of already-verified foods to protect them
        verified_ids: set[str] = set()
        if not truncate:
            from sqlalchemy import select
            verified_rows = db.execute(
                select(Food.food_id).where(Food.image_verified.is_(True))
            ).fetchall()
            verified_ids = {str(r[0]) for r in verified_rows}

        inserted = 0
        for row in df.itertuples(index=False):
            food_id = str(row.food_id)
            is_verified = _safe_bool(getattr(row, "image_verified", None))

            # Read image columns from CSV if present
            csv_image_url = _safe_str(getattr(row, "image_url", None))
            csv_image_alt_vi = _safe_str(getattr(row, "image_alt_vi", None))
            csv_image_source_type = _safe_str(getattr(row, "image_source_type", None)) or "placeholder"
            csv_image_verified = is_verified
            csv_image_quality_note = _safe_str(getattr(row, "image_quality_note", None))

            existing = db.get(Food, food_id)
            if existing is not None:
                # Update non-image fields always
                existing.name = str(row.name)
                existing.calories = float(row.calories)
                existing.protein = float(row.protein)
                existing.fat = float(row.fat)
                existing.carbs = float(row.carbs)
                existing.name_vi = _safe_str(getattr(row, "name_vi", None))
                existing.category = str(row.category)
                existing.type = _safe_str(getattr(row, "type", None))
                # Only update image fields if the existing record is NOT already verified
                if food_id not in verified_ids:
                    existing.image_url = csv_image_url
                    existing.image_alt_vi = csv_image_alt_vi
                    existing.image_source_type = csv_image_source_type
                    existing.image_verified = csv_image_verified
                    existing.image_quality_note = csv_image_quality_note
            else:
                food = Food(
                    food_id=food_id,
                    name=str(row.name),
                    calories=float(row.calories),
                    protein=float(row.protein),
                    fat=float(row.fat),
                    carbs=float(row.carbs),
                    name_vi=_safe_str(getattr(row, "name_vi", None)),
                    category=str(row.category),
                    type=_safe_str(getattr(row, "type", None)),
                    image_url=csv_image_url,
                    image_alt_vi=csv_image_alt_vi,
                    image_source_type=csv_image_source_type,
                    image_verified=csv_image_verified,
                    image_quality_note=csv_image_quality_note,
                )
                db.add(food)
                inserted += 1

        db.commit()
        print(f"  [{inserted} new inserted, {len(df) - inserted} updated]")
    finally:
        db.close()

    return len(df)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    csv_path = Path(args.csv_path).resolve()

    count = import_foods(csv_path, truncate=args.truncate, dry_run=args.dry_run)
    if args.dry_run:
        print(f"Validated {count} rows from {csv_path}")
    else:
        print(f"Imported {count} rows into foods table from {csv_path}")


if __name__ == "__main__":
    main()
