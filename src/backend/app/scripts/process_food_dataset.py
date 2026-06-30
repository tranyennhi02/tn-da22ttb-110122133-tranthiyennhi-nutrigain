from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from app.core.database import SessionLocal
from app.scripts.import_foods_csv import import_foods, normalize_dataframe
from app.services.recommender_service import RecommenderService
from app.views.schemas import RecommendationInput
from nutrigain_recommender import (
    DEFAULT_MEAL_CALORIE_RATIOS,
    DEFAULT_MEAL_STRUCTURE,
    MEAL_CATEGORY_PRIORITIES,
    MEAL_CATEGORY_REPEAT_LIMITS,
    MEAL_MACRO_WEIGHTS,
    MEAL_REQUIRED_CATEGORIES,
    MAX_DAILY_CATEGORY_REPEAT,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Process the foods dataset in 3 steps: normalize, build meal template, generate a user meal plan"
    )
    parser.add_argument(
        "--csv-path",
        default=str(Path(__file__).resolve().parents[3] / "foods_clean.csv"),
        help="Path to foods_clean.csv",
    )
    parser.add_argument(
        "--truncate",
        action="store_true",
        help="Clear the foods table before import",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate the CSV and build the meal template without writing to the database",
    )
    parser.add_argument(
        "--template-output",
        default=str(Path(__file__).resolve().parents[3] / "meal_template.json"),
        help="Where to write the generated meal template JSON",
    )
    parser.add_argument("--weight", type=float, help="User weight in kg")
    parser.add_argument("--height", type=float, help="User height in cm")
    parser.add_argument("--activity", default="moderate", help="Activity level")
    parser.add_argument("--age", type=int, default=None, help="User age")
    parser.add_argument("--sex", type=str, default=None, help="User sex")
    parser.add_argument("--surplus-kcal", type=float, default=None, help="Additional calories above maintenance")
    parser.add_argument("--top-n", type=int, default=10, help="Number of recommendations to return")
    parser.add_argument(
        "--preferred-categories",
        nargs="*",
        default=[],
        help="Preferred food categories",
    )
    parser.add_argument(
        "--excluded-categories",
        nargs="*",
        default=[],
        help="Excluded food categories",
    )
    return parser


def build_meal_template() -> dict[str, dict[str, object]]:
    template: dict[str, dict[str, object]] = {}
    for meal, slot_count in DEFAULT_MEAL_STRUCTURE.items():
        template[meal] = {
            "slots": int(slot_count),
            "target_calorie_ratio": float(DEFAULT_MEAL_CALORIE_RATIOS.get(meal, 0.0)),
            "required_categories": list(MEAL_REQUIRED_CATEGORIES.get(meal, [])),
            "priority_categories": list(MEAL_CATEGORY_PRIORITIES.get(meal, [])),
            "macro_weights": {
                key: float(value) for key, value in MEAL_MACRO_WEIGHTS.get(meal, {}).items()
            },
        }

    return {
        "meals": template,
        "daily_category_repeat_limits": {key: int(value) for key, value in MAX_DAILY_CATEGORY_REPEAT.items()},
        "meal_category_repeat_limits": {key: int(value) for key, value in MEAL_CATEGORY_REPEAT_LIMITS.items()},
    }


def write_template(template: dict[str, object], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(template, ensure_ascii=False, indent=2), encoding="utf-8")


def summarize_dataframe(df: pd.DataFrame) -> str:
    counts = df["category"].value_counts().to_dict()
    lines = [f"rows={len(df)}"]
    for category, count in sorted(counts.items()):
        lines.append(f"{category}={count}")
    return "\n".join(lines)


def generate_meal_plan(args: argparse.Namespace) -> dict:
    if args.weight is None or args.height is None:
        raise ValueError("--weight and --height are required to generate a meal plan")

    payload = RecommendationInput(
        weight=args.weight,
        height=args.height,
        activity=args.activity,
        age=args.age,
        sex=args.sex,
        surplus_kcal=args.surplus_kcal,
        top_n=args.top_n,
        preferred_categories=args.preferred_categories,
        excluded_categories=args.excluded_categories,
    )

    db = SessionLocal()
    try:
        service = RecommenderService()
        return service.generate_recommendations(payload, db)
    finally:
        db.close()


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    csv_path = Path(args.csv_path).resolve()
    template_output = Path(args.template_output).resolve()

    normalized_df = normalize_dataframe(pd.read_csv(csv_path))
    template = build_meal_template()
    write_template(template, template_output)

    print("[Step 1] Chuẩn hóa & phân loại thực phẩm")
    print(summarize_dataframe(normalized_df))
    print(f"template_written={template_output}")

    if args.dry_run:
        return

    imported_count = import_foods(csv_path, truncate=args.truncate, dry_run=False)
    print("[Step 1b] Imported foods into database")
    print(f"imported_rows={imported_count}")

    print("[Step 2] Xây dựng cấu trúc bữa ăn")
    print(json.dumps(template, ensure_ascii=False, indent=2))

    if args.weight is None or args.height is None:
        print("[Step 3] Bỏ qua sinh thực đơn vì chưa cung cấp --weight và --height")
        return

    print("[Step 3] Sinh thực đơn theo nhu cầu năng lượng người dùng")
    result = generate_meal_plan(args)
    print(json.dumps(result["target"], ensure_ascii=False, indent=2))
    print(json.dumps(result["meal_plan"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()