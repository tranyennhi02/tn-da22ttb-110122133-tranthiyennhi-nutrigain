from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from backend.app.services.recommender_service import (
    MEAL_SLOT_ROLES,
    SLOT_CATEGORY_RULES,
    RecommenderService,
    _expand_food_terms,
    _row_matches_terms,
)
from backend.app.views.schemas import RecommendationInput


def _build_ranked_sample() -> pd.DataFrame:
    rows = [
        {"food_id": "1", "name": "Com trang", "clean_category": "starch_grain", "category": "starch_grain", "score": 0.95, "calories_raw": 210, "protein_raw": 4, "fat_raw": 1, "carbs_raw": 45},
        {"food_id": "2", "name": "Khoai lang", "clean_category": "starch_tuber", "category": "starch_tuber", "score": 0.90, "calories_raw": 180, "protein_raw": 3, "fat_raw": 0.3, "carbs_raw": 40},
        {"food_id": "3", "name": "Uc ga", "clean_category": "protein_meat", "category": "protein_meat", "score": 0.92, "calories_raw": 190, "protein_raw": 30, "fat_raw": 5, "carbs_raw": 0},
        {"food_id": "4", "name": "Ca hoi", "clean_category": "protein_seafood", "category": "protein_seafood", "score": 0.89, "calories_raw": 220, "protein_raw": 26, "fat_raw": 12, "carbs_raw": 0},
        {"food_id": "5", "name": "Dau hu", "clean_category": "plant_protein", "category": "plant_protein", "score": 0.85, "calories_raw": 140, "protein_raw": 14, "fat_raw": 7, "carbs_raw": 4},
        {"food_id": "6", "name": "Trung ga", "clean_category": "egg", "category": "egg", "score": 0.87, "calories_raw": 160, "protein_raw": 13, "fat_raw": 11, "carbs_raw": 1},
        {"food_id": "7", "name": "Rau luoc", "clean_category": "vegetable", "category": "vegetable", "score": 0.84, "calories_raw": 60, "protein_raw": 2, "fat_raw": 0.5, "carbs_raw": 10},
        {"food_id": "8", "name": "Tao", "clean_category": "fruit", "category": "fruit", "score": 0.83, "calories_raw": 95, "protein_raw": 0.3, "fat_raw": 0.2, "carbs_raw": 25},
        {"food_id": "9", "name": "Sua tuoi", "clean_category": "dairy", "category": "dairy", "score": 0.82, "calories_raw": 120, "protein_raw": 6, "fat_raw": 6, "carbs_raw": 9},
        {"food_id": "10", "name": "Hat hanh nhan", "clean_category": "healthy_fat_nuts", "category": "healthy_fat_nuts", "score": 0.81, "calories_raw": 170, "protein_raw": 6, "fat_raw": 15, "carbs_raw": 5},
        {"food_id": "11", "name": "Nuoc ep tao", "clean_category": "drink_natural", "category": "drink_natural", "score": 1.10, "calories_raw": 130, "protein_raw": 0.2, "fat_raw": 0.1, "carbs_raw": 30},
        {"food_id": "12", "name": "Banh ngot", "clean_category": "dessert_sweets", "category": "dessert_sweets", "score": 1.05, "calories_raw": 240, "protein_raw": 3, "fat_raw": 9, "carbs_raw": 36},
    ]
    return pd.DataFrame(rows)


def main() -> None:
    bmi_15_payload = RecommendationInput(weight=42, height=167, activity="moderate", age=22, sex="female", goal_type="gain")
    bmi_20_payload = RecommendationInput(weight=56, height=167, activity="moderate", age=22, sex="female", goal_type="gain")

    eligibility_15 = RecommenderService._build_eligibility_check(bmi_15_payload)
    eligibility_20 = RecommenderService._build_eligibility_check(bmi_20_payload)

    assert eligibility_15["eligible"] is True, f"BMI 15 should be eligible, got: {eligibility_15}"
    assert eligibility_20["eligible"] is False, f"BMI 20 should be blocked, got: {eligibility_20}"

    assert len(MEAL_SLOT_ROLES["breakfast"]) == 4
    assert len(MEAL_SLOT_ROLES["lunch"]) == 4
    assert len(MEAL_SLOT_ROLES["dinner"]) == 4
    assert "fruit_or_dairy" in MEAL_SLOT_ROLES["breakfast"]
    assert "vegetable" not in MEAL_SLOT_ROLES["breakfast"]

    forbidden = {"drink_natural", "dessert_sweets"}
    for meal_name, role_names in MEAL_SLOT_ROLES.items():
        for role_name in role_names:
            assert SLOT_CATEGORY_RULES[role_name].isdisjoint(forbidden), (
                f"Forbidden categories leaked into {meal_name}/{role_name}: {SLOT_CATEGORY_RULES[role_name]}"
            )

    disliked_terms = _expand_food_terms(["gà"])
    assert {"ga", "chicken", "turkey"}.issubset(set(disliked_terms)), disliked_terms
    assert _row_matches_terms({"name": "Uc ga ap chao", "clean_category": "protein_meat"}, disliked_terms)
    assert _row_matches_terms({"name": "Turkey breast", "clean_category": "protein_meat"}, disliked_terms)

    ranked = _build_ranked_sample()
    plan = RecommenderService.pickBalancedMeal(
        ranked=ranked,
        meal_structure={"breakfast": 4, "lunch": 4, "dinner": 4},
        target={"calories": 2100, "bmi": 15.0, "goal": "gain", "weight_gain_speed": "moderate", "disliked_foods": ["gà"]},
    )

    for meal_name in ("breakfast", "lunch", "dinner"):
        meal_df = plan[meal_name]
        assert len(meal_df) == 4, f"{meal_name} should have 4 items, got {len(meal_df)}"
        clean_categories = {str(row.get("clean_category", "")).strip().lower() for _, row in meal_df.iterrows()}
        assert "drink_natural" not in clean_categories, f"{meal_name} contains drink_natural"
        assert "dessert_sweets" not in clean_categories, f"{meal_name} contains dessert_sweets"

    print("PASS: recommender refactor smoke checks")


if __name__ == "__main__":
    main()
