from __future__ import annotations

import argparse
import os
import sys
import unicodedata
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import text


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


QUALITY_COLUMNS = [
    "is_common_food",
    "is_budget_friendly",
    "is_premium",
    "is_processed",
    "is_natural_food",
    "budget_tier",
    "natural_priority_score",
]

TEXT_COLUMNS = [
    "display_name",
    "dish_name_vi",
    "original_name",
    "clean_category",
    "food_group_vi",
    "meal_role",
    "search_keywords",
    "quality_flags",
]

COMMON_TERMS = (
    "com", "rice", "gao", "gao lut", "brown rice", "yen mach", "oat",
    "khoai", "khoai lang", "khoai tay", "khoai mon", "potato", "sweet potato",
    "trung", "egg", "sua tuoi", "sua nguyen chat", "whole milk", "soy milk", "sua dau nanh",
    "dau", "dau nanh", "dau phu", "dau hu", "tofu", "bean", "lentil",
    "rau", "rau cai", "ca rot", "ca chua", "bi", "bap cai", "cabbage", "carrot", "tomato",
    "chuoi", "banana", "tao", "apple", "cam", "orange", "du du", "papaya",
    "thit ga", "uc ga", "ga luoc", "ga nuong", "chicken", "chicken breast",
    "thit bo nac", "bo nac", "lean beef",
    "ca ro", "ca basa", "ca loc", "ca thu", "fish",
)

BUDGET_TERMS = (
    "com", "rice", "gao", "gao lut", "yen mach", "oat", "khoai", "potato",
    "trung", "egg", "dau", "bean", "tofu", "dau phu", "dau hu", "dau nanh",
    "rau", "chuoi", "banana", "sua tuoi", "milk", "sua dau nanh",
    "thit ga", "uc ga", "chicken", "ca ro", "ca basa", "ca loc", "fish",
)

PREMIUM_TERMS = (
    "mam xoi", "red raspberry", "raspberry", "nam viet quat", "cranberry",
    "viet quat", "blueberry", "berries", "berry", "dau tay", "strawberry",
    "sua chua hy lap", "greek yogurt", "ca hoi", "salmon",
    "bo than", "than lung", "tenderloin", "ribeye", "sirloin", "wagyu",
    "almond", "hanh nhan", "walnut", "oc cho", "macadamia", "pistachio", "hazelnut", "cashew",
    "imported", "nhap khau", "premium", "fancy", "cao cap",
    "caviar", "brie", "camembert", "emmental", "gruyere", "raclette",
    # Uncommon/less-common for Vietnamese budget meals → treated as premium
    # so they rank lower when budget = Tiết kiệm (soft penalty only, menu_eligible unchanged).
    "cha la", "date",
    "man hoang da", "wild plum",          # mận hoang dã
    "qua mo", "apricot",                  # quả mơ
    "sung say", "dried fig", "fig",        # sung sấy / quả sung
    "dried fruit", "trai cay kho",
    "tofu yogurt", "soy yogurt", "sua chua dau phu",
    "burrito", "taquito", "taco",          # Western fast/fusion food
    "ga tay", "turkey",                    # gà tây – less common in VN
    "ca bo", "avocado fish",               # cá bơ – obscure
    "phô mai xanh", "pho mai xanh", "blue cheese",  # fancy cheese
    "smoked salmon", "ca hoi xong khoi",  # smoked salmon
    "sot cream", "cream sauce", "bechamel",  # western sauces
)

PROCESSED_TERMS = (
    "snack", "mix", "mixed", "nuoc mix", "nuoc ep mix", "juice mix", "nuoc ep dong chai",
    "processed", "che bien san", "thit che bien", "sausage", "xuc xich",
    "mortadella", "salami", "ham", "bacon", "sup kem", "cream soup", "cream of mushroom",
    "sot pho mai", "cheese sauce", "candy", "sweets", "keo", "dessert", "cake", "cookie",
    "pastry", "donut", "ice cream", "dong hop", "canned",
)

NATURAL_CATEGORY_TERMS = (
    "starch_grain", "starch_tuber", "egg", "plant_protein", "vegetable", "fruit",
    "protein_meat", "protein_seafood", "dairy",
)


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def configure_database_url() -> None:
    load_dotenv(ROOT_DIR / ".env")
    database_url = os.getenv("DATABASE_URL", "")
    running_outside_docker = not Path("/.dockerenv").exists()
    if running_outside_docker and "@db:3306" in database_url:
        host_port = os.getenv("DB_PORT", "3307")
        os.environ["DATABASE_URL"] = database_url.replace("@db:3306", f"@127.0.0.1:{host_port}")


def normalize_text(value: object) -> str:
    text_value = str(value or "").lower()
    text_value = unicodedata.normalize("NFD", text_value)
    text_value = "".join(ch for ch in text_value if unicodedata.category(ch) != "Mn")
    return " ".join(text_value.split())


def text_has_any(text_value: str, terms: tuple[str, ...]) -> bool:
    return any(term in text_value for term in terms)


def coerce_bool(value: object) -> int:
    if isinstance(value, str):
        return 1 if value.strip().lower() in {"1", "true", "yes", "y"} else 0
    return 1 if bool(value) else 0


def row_text(row: pd.Series | dict[str, Any]) -> str:
    return normalize_text(" ".join(str(row.get(column, "") or "") for column in TEXT_COLUMNS))


def classify_row(row: pd.Series | dict[str, Any]) -> dict[str, Any]:
    text_value = row_text(row)
    category = normalize_text(row.get("clean_category", ""))
    common = text_has_any(text_value, COMMON_TERMS)
    budget = text_has_any(text_value, BUDGET_TERMS)
    premium = text_has_any(text_value, PREMIUM_TERMS)
    processed = text_has_any(text_value, PROCESSED_TERMS)
    natural_category = category in NATURAL_CATEGORY_TERMS
    natural = (natural_category or common or budget or premium) and not processed

    if processed:
        natural_score = 0.25
    elif common and budget:
        natural_score = 0.88
    elif common:
        natural_score = 0.80
    elif premium and natural:
        natural_score = 0.52
    elif natural:
        natural_score = 0.65
    else:
        natural_score = 0.45

    if processed:
        budget_tier = "standard" if budget else "flexible"
    elif premium:
        budget_tier = "premium"
    elif budget:
        budget_tier = "low"
    elif common:
        budget_tier = "standard"
    else:
        budget_tier = "standard"

    return {
        "is_common_food": int(common and not processed),
        "is_budget_friendly": int(budget and not premium),
        "is_premium": int(premium),
        "is_processed": int(processed),
        "is_natural_food": int(natural),
        "budget_tier": budget_tier,
        "natural_priority_score": round(float(max(0.0, min(1.0, natural_score))), 2),
    }


def apply_tags(df: pd.DataFrame) -> pd.DataFrame:
    tagged = df.copy()
    for column in QUALITY_COLUMNS:
        if column not in tagged.columns:
            tagged[column] = 0 if column != "budget_tier" else "standard"
    for index, row in tagged.iterrows():
        labels = classify_row(row)
        for column, value in labels.items():
            tagged.at[index, column] = value
    for column in QUALITY_COLUMNS:
        if column != "budget_tier":
            tagged[column] = pd.to_numeric(tagged[column], errors="coerce").fillna(0)
    return tagged


def print_stats(df: pd.DataFrame) -> None:
    total = len(df)
    print(f"Total foods: {total}")
    print(f"Common foods: {int(pd.to_numeric(df['is_common_food'], errors='coerce').fillna(0).sum())}")
    print(f"Budget-friendly foods: {int(pd.to_numeric(df['is_budget_friendly'], errors='coerce').fillna(0).sum())}")
    print(f"Premium foods: {int(pd.to_numeric(df['is_premium'], errors='coerce').fillna(0).sum())}")
    print(f"Processed foods: {int(pd.to_numeric(df['is_processed'], errors='coerce').fillna(0).sum())}")
    print(f"Natural foods: {int(pd.to_numeric(df['is_natural_food'], errors='coerce').fillna(0).sum())}")
    print("Budget tiers:")
    for tier, count in df["budget_tier"].fillna("standard").value_counts().sort_index().items():
        print(f"  {tier}: {int(count)}")

    def item_name(row: pd.Series) -> str:
        return str(row.get("dish_name_vi") or row.get("display_name") or row.get("original_name") or row.get("food_id"))

    eligible = pd.to_numeric(df.get("menu_eligible", pd.Series(1, index=df.index)), errors="coerce").fillna(0).astype(int) == 1
    for label, mask in (
        ("Top premium still menu_eligible=1", eligible & (pd.to_numeric(df["is_premium"], errors="coerce").fillna(0) == 1)),
        ("Top processed still menu_eligible=1", eligible & (pd.to_numeric(df["is_processed"], errors="coerce").fillna(0) == 1)),
        ("Top budget-friendly", pd.to_numeric(df["is_budget_friendly"], errors="coerce").fillna(0) == 1),
    ):
        print(label + ":")
        sample = df.loc[mask].head(30)
        for _, row in sample.iterrows():
            print(f"  - {row.get('food_id')}: {item_name(row)}")


def read_db_dataframe() -> pd.DataFrame:
    configure_database_url()
    from app.core.database import engine
    from app.core.migrations import ensure_database_schema

    ensure_database_schema(engine)
    query = text(
        """
        SELECT food_id, original_name, display_name, dish_name_vi, clean_category,
               food_group_vi, meal_role, search_keywords, quality_flags, menu_eligible,
               is_common_food, is_budget_friendly, is_premium, is_processed,
               is_natural_food, budget_tier, natural_priority_score
        FROM foods
        """
    )
    return pd.read_sql(query, engine)


def update_database(df: pd.DataFrame) -> None:
    configure_database_url()
    from app.core.database import engine
    from app.core.migrations import ensure_database_schema

    ensure_database_schema(engine)
    update_sql = text(
        """
        UPDATE foods
        SET is_common_food = :is_common_food,
            is_budget_friendly = :is_budget_friendly,
            is_premium = :is_premium,
            is_processed = :is_processed,
            is_natural_food = :is_natural_food,
            budget_tier = :budget_tier,
            natural_priority_score = :natural_priority_score
        WHERE food_id = :food_id
        """
    )
    records = [
        {
            "food_id": str(row["food_id"]),
            "is_common_food": coerce_bool(row["is_common_food"]),
            "is_budget_friendly": coerce_bool(row["is_budget_friendly"]),
            "is_premium": coerce_bool(row["is_premium"]),
            "is_processed": coerce_bool(row["is_processed"]),
            "is_natural_food": coerce_bool(row["is_natural_food"]),
            "budget_tier": str(row["budget_tier"] or "standard"),
            "natural_priority_score": float(row["natural_priority_score"] or 0.5),
        }
        for _, row in df.iterrows()
    ]
    with engine.begin() as connection:
        connection.execute(update_sql, records)
    print(f"Updated DB rows: {len(records)}")
    print("menu_eligible was not changed.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Tag food quality fields for recommender soft scoring.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Print stats only.")
    mode.add_argument("--apply", action="store_true", help="Update DB quality columns.")
    parser.add_argument("--csv", type=Path, help="Read tags from CSV instead of DB.")
    parser.add_argument("--output", type=Path, help="Write tagged CSV.")
    args = parser.parse_args()

    if args.csv:
        df = pd.read_csv(args.csv, encoding="utf-8-sig")
    else:
        df = read_db_dataframe()

    tagged = apply_tags(df)
    print_stats(tagged)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        tagged.to_csv(args.output, index=False, encoding="utf-8-sig")
        print(f"Wrote tagged CSV: {args.output}")

    if args.apply:
        if args.csv:
            raise SystemExit("--apply updates the database; omit --csv to apply DB tags.")
        update_database(tagged)
    else:
        print("Dry run only; no database rows were updated.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
