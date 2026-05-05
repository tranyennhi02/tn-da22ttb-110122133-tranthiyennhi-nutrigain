import pandas as pd
import mysql.connector
from pathlib import Path

CSV_PATH = Path("data/food_dataset_ready_for_mysql.csv")

DB_CONFIG = {
    "host": "localhost",
    "port": 3307,
    "user": "nutrigain",
    "password": "yennhi2602",
    "database": "food_recommender",
    "charset": "utf8mb4",
}

COLUMNS = [
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


def clean_value(value):
    if pd.isna(value):
        return None

    if isinstance(value, str):
        value = value.strip()
        if value == "":
            return None

    return value


def main():
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"Không tìm thấy file CSV: {CSV_PATH.resolve()}")

    print(f"Reading CSV: {CSV_PATH.resolve()}")

    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")

    missing_csv_columns = [col for col in COLUMNS if col not in df.columns]
    if missing_csv_columns:
        raise ValueError(f"CSV thiếu cột: {missing_csv_columns}")

    df = df[COLUMNS].copy()

    df["menu_eligible"] = df["menu_eligible"].fillna(0).astype(int)
    df["image_verified"] = df["image_verified"].fillna(0).astype(int)

    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()

    try:
        # Debug kết nối
        cursor.execute("SELECT DATABASE()")
        print("Connected database:", cursor.fetchone()[0])

        cursor.execute("SHOW COLUMNS FROM foods")
        db_columns = [row[0] for row in cursor.fetchall()]
        print("Foods table columns:", db_columns)

        missing_db_columns = [col for col in COLUMNS if col not in db_columns]
        if missing_db_columns:
            raise ValueError(
                "Bảng foods đang thiếu cột: "
                f"{missing_db_columns}. Hãy sửa schema bảng foods trước khi import."
            )

        # Xóa dữ liệu cũ trong foods rồi import lại
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        cursor.execute("TRUNCATE TABLE foods")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")

        placeholders = ", ".join(["%s"] * len(COLUMNS))
        column_names = ", ".join(COLUMNS)

        sql = f"""
            INSERT INTO foods ({column_names})
            VALUES ({placeholders})
        """

        rows = [
            tuple(clean_value(value) for value in row)
            for row in df.itertuples(index=False, name=None)
        ]

        print(f"Importing rows: {len(rows)}")

        cursor.executemany(sql, rows)
        conn.commit()

        cursor.execute("SELECT COUNT(*) FROM foods")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM foods WHERE menu_eligible = 1")
        eligible = cursor.fetchone()[0]

        print(f"Imported foods: {total}")
        print(f"Menu eligible foods: {eligible}")

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()