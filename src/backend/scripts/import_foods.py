import argparse
from pathlib import Path

import mysql.connector
import pandas as pd


CSV_PATH = Path("data/food_dataset_ready_for_mysql.csv")

DB_CONFIG = {
    "host": "localhost",
    "port": 3307,
    "user": "nutrigain",
    "password": "yennhi2602",
    "database": "food_recommender",
    "charset": "utf8mb4",
}

REQUIRED_COLUMNS = [
    "food_id",
    "original_name",
    "display_name",
    "dish_name_vi",
    "clean_category",
    "food_group_vi",
    "meal_role",
    "recommended_serving_g",
    "serving_display",
    "kcal_per_100g_clean",
    "protein_per_100g_clean",
    "fat_per_100g_clean",
    "carbs_per_100g_clean",
    "kcal_per_serving_clean",
    "protein_per_serving_clean",
    "fat_per_serving_clean",
    "carbs_per_serving_clean",
    "menu_eligible",
    "quality_flags",
    "image_url",
    "image_alt_vi",
    "image_source_type",
    "image_verified",
    "image_quality_note",
    "search_keywords",
]

OPTIONAL_DEFAULTS = {
    "is_common_food": 0,
    "is_budget_friendly": 0,
    "is_premium": 0,
    "is_processed": 0,
    "is_natural_food": 0,
    "budget_tier": "standard",
    "natural_priority_score": 0.5,
}

BOOLEAN_COLUMNS = [
    "menu_eligible",
    "image_verified",
    "is_common_food",
    "is_budget_friendly",
    "is_premium",
    "is_processed",
    "is_natural_food",
]


def clean_value(value):
    if pd.isna(value):
        return None
    if isinstance(value, str):
        value = value.strip()
        if value == "":
            return None
    return value


def main():
    parser = argparse.ArgumentParser(description="Import food dataset into MySQL.")
    parser.add_argument("--replace", action="store_true", help="Truncate foods before import. Destructive.")
    args = parser.parse_args()

    if not CSV_PATH.exists():
        raise FileNotFoundError(f"Cannot find file: {CSV_PATH.resolve()}")

    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")

    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"CSV is missing columns: {missing}")

    for column, default in OPTIONAL_DEFAULTS.items():
        if column not in df.columns:
            df[column] = default

    import_columns = [*REQUIRED_COLUMNS, *OPTIONAL_DEFAULTS.keys()]
    df = df[import_columns]

    for column in BOOLEAN_COLUMNS:
        df[column] = df[column].fillna(0).astype(int)

    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()

    if args.replace:
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        cursor.execute("TRUNCATE TABLE foods")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")

    placeholders = ", ".join(["%s"] * len(import_columns))
    column_names = ", ".join(import_columns)
    updates = ", ".join(f"{column}=VALUES({column})" for column in import_columns if column != "food_id")

    sql = f"""
        INSERT INTO foods ({column_names})
        VALUES ({placeholders})
        ON DUPLICATE KEY UPDATE {updates}
    """

    rows = [
        tuple(clean_value(value) for value in row)
        for row in df.itertuples(index=False, name=None)
    ]

    cursor.executemany(sql, rows)
    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM foods")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM foods WHERE menu_eligible = 1")
    eligible = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    print(f"Imported/upserted foods: {len(rows)}")
    print(f"Foods in table: {total}")
    print(f"Menu eligible foods: {eligible}")
    if not args.replace:
        print("Mode: upsert only; existing rows were not truncated.")


if __name__ == "__main__":
    main()
