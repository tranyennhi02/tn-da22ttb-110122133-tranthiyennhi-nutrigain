from __future__ import annotations

import copy
import logging
import os
import random
import traceback
from datetime import datetime, timedelta, timezone
from functools import lru_cache

import numpy as np
import pandas as pd
from fastapi import HTTPException, status
from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session

import sys as _sys
from pathlib import Path as _Path

# nutrigain_recommender.py lives at the project root (3 levels above this file:
#   backend/app/services/recommender_service.py  →  root = parents[3])
_PROJECT_ROOT = str(_Path(__file__).resolve().parents[3])
if _PROJECT_ROOT not in _sys.path:
    _sys.path.insert(0, _PROJECT_ROOT)

from nutrigain_recommender import (
    DEFAULT_MEAL_CALORIE_RATIOS,
    DEFAULT_MEAL_STRUCTURE,
    FEATURE_COLUMNS,
    HealthyWeightGainRecommender,
    UserProfile,
    clear_taxonomy_cache,
    is_non_vegetarian_food,
)
from app.services.nutrition_calculation_service import (
    NutritionCalculationService,
    asian_bmi_label,
    classify_asian_bmi,
)
from app.services.ml_food_eligibility_service import ml_food_eligibility_service

logger = logging.getLogger(__name__)

def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


DEFAULT_FOOD_PLACEHOLDER = "/images/placeholders/food-default.svg"
ML_SCORE_WEIGHT = 0.2
ENABLE_INGREDIENT_PREFERENCE = os.getenv("ENABLE_INGREDIENT_PREFERENCE", "true").lower() == "true"
ENABLE_HARD_INGREDIENT_COVERAGE = os.getenv("ENABLE_HARD_INGREDIENT_COVERAGE", "true").lower() == "true"
INGREDIENT_PREFERENCE_BONUS = _float_env("INGREDIENT_PREFERENCE_BONUS", 0.18)
RECOMMENDER_DIVERSITY_JITTER = _float_env("RECOMMENDER_DIVERSITY_JITTER", 0.18)
CATEGORY_PLACEHOLDERS = {
    "starch_grain": "/images/placeholders/starch-grain.svg",
    "starch_tuber": "/images/placeholders/starch-tuber.svg",
    "protein_meat": "/images/placeholders/protein-meat.svg",
    "protein_seafood": "/images/placeholders/protein-seafood.svg",
    "plant_protein": "/images/placeholders/protein-plant.svg",
    "protein_plant": "/images/placeholders/protein-plant.svg",
    "egg": "/images/placeholders/protein-meat.svg",
    "vegetable": "/images/placeholders/vegetable.svg",
    "vegetable_herb": "/images/placeholders/vegetable.svg",
    "fruit": "/images/placeholders/fruit.svg",
    "dairy": "/images/placeholders/dairy.svg",
    "drink_natural": "/images/placeholders/drink.svg",
    "fats_good": "/images/placeholders/healthy-fat.svg",
    "healthy_fat": "/images/placeholders/healthy-fat.svg",
    "healthy_fat_nuts": "/images/placeholders/healthy-fat.svg",
    "dessert_sweets": "/images/placeholders/dessert.svg",
    "other": "/images/placeholders/food-default.svg",
}

CANONICAL_FOOD_CATEGORIES = {
    "starch_grain",
    "starch_tuber",
    "protein_meat",
    "protein_seafood",
    "plant_protein",
    "egg",
    "vegetable",
    "fruit",
    "dairy",
    "healthy_fat_nuts",
    "drink_natural",
    "dessert_sweets",
    "other",
}

CATEGORY_ALIASES = {
    "grain": "starch_grain",
    "carb": "starch_grain",
    "pasta": "starch_grain",
    "mixed_dish": "starch_grain",
    "meat": "protein_meat",
    "protein": "protein_meat",
    "protein_plant": "plant_protein",
    "healthy_fat": "healthy_fat_nuts",
    "fats_good": "healthy_fat_nuts",
    "fat": "healthy_fat_nuts",
    "sweet_spread": "dessert_sweets",
    "vegetable_herb": "vegetable",
    "drink": "drink_natural",
    "beverage": "drink_natural",
    "juice": "drink_natural",
}

SLOT_CATEGORY_RULES = {
    "starch": {"starch_grain", "starch_tuber"},
    "protein": {"protein_meat", "protein_seafood", "plant_protein", "egg"},
    "vegetable": {"vegetable"},
    "vegetable_or_fruit": {"vegetable", "fruit"},
    "fruit_or_dairy": {"fruit", "dairy"},
    "extra": {"dairy", "healthy_fat_nuts", "plant_protein", "egg"},
    "fruit_or_extra": {"fruit", "dairy", "healthy_fat_nuts", "plant_protein", "egg"},
}

# Single source for 4-item meal roles.
MEAL_SLOT_ROLES = {
    "breakfast": ("starch", "protein", "fruit_or_dairy", "extra"),
    "lunch": ("starch", "protein", "vegetable_or_fruit", "extra"),
    "dinner": ("starch", "protein", "vegetable_or_fruit", "extra"),
}

EAT_CLEAN_DIET_TERMS = ("eat clean", "eat_clean", "clean", "balanced", "can bang", "cân bằng")
EAT_CLEAN_BLOCKED_TERMS = [
    "xúc xích",
    "xuc xich",
    "sausage",
    "hun khói",
    "hun khoi",
    "smoked",
    "đồ ăn nhanh",
    "do an nhanh",
    "fast food",
    "processed",
    "chiên rán nhiều dầu",
    "chien ran nhieu dau",
    "fried",
    "mứt",
    "mut",
    "jam",
    "jelly",
    "nước ngọt",
    "nuoc ngot",
    "soft drink",
    "soda",
    "bánh kẹo ngọt",
    "banh keo ngot",
    "món ngọt nhiều đường",
    "mon ngot nhieu duong",
    "sugary",
    "candy",
    "bánh sừng bò",
    "banh sung bo",
    "croissant",
    "pastry",
    "bánh ngọt",
    "banh ngot",
    "dessert",
    "ice cream",
    "kem trái cây",
    "kem trai cay",
    "chiên",
    "chien",
    "burrito",
    "taquito",
    "taco",
    "cá hồi lên men",
    "ca hoi len men",
    "fermented salmon",
    "cải ngựa",
    "cai ngua",
    "horseradish",
    "giăm bông",
    "giam bong",
    "ham",
    "processed_meat_limit_for_eat_clean",
    "bơ thực vật",
    "bo thuc vat",
    "margarine",
    "bánh cuộn",
    "banh cuon",
    "bánh mì quế",
    "banh mi que",
    "cinnamon",
    "sweet bread",
    "sweet roll",
    "trứng cá",
    "trung ca",
    "roe",
    "vụn thịt",
    "vun thit",
    "pizza",
    "tilefish",
    "dưa chua",
    "dua chua",
    "pickle",
    "súp",
    "sup",
    "soup",
    "thịt cừu",
    "thit cuu",
    "lamb",
    "sốt",
    "sot",
    "sauce",
    "nước thịt",
    "nuoc thit",
    "gravy",
    "kem hạt",
    "kem hat",
    "hazelnut",
    "cuộn bơ",
    "cuon bo",
    "peanut butter roll",
    "bologna",
    "sausage",
    "hot dog",
    "corn dog",
    "luncheon meat",
    "deli meat",
    "cold cut",
    "cold cuts",
    "salami",
    "pepperoni",
    "ham",
    "bacon",
    "processed meat",
    "thit nguoi",
    "thit che bien",
    "xuc xich",
]

LOW_FAT_DAIRY_TERMS = (
    "nonfat",
    "non fat",
    "non-fat",
    "fat free",
    "fat-free",
    "skim",
    "skimmed",
    "low fat",
    "low-fat",
    "reduced fat",
    "reduced-fat",
    "part skim",
    "1% milk",
    "2% milk",
    "khong beo",
    "it beo",
    "giam beo",
    "tach beo",
)
FULL_FAT_DAIRY_TERMS = (
    "whole milk",
    "full fat",
    "full-fat",
    "nguyen kem",
    "sua nguyen kem",
    "sua chua nguyen kem",
    "greek yogurt",
    "sua chua hy lap",
)
DAIRY_TERMS = ("milk", "sua", "yogurt", "sua chua", "cheese", "pho mai")
DAIRY_EXCLUSION_TERMS = (
    "sua",
    "milk",
    "dairy",
    "sua bo",
    "sua tuoi",
    "sua chua",
    "yogurt",
    "yoghurt",
    "cheese",
    "pho mai",
    "cream",
    "kem",
)
SOY_MILK_TERMS = ("soy milk", "soymilk", "sua dau nanh", "dau nanh beverage")
ANIMAL_MAIN_PROTEIN_WARNING = "Một số bữa có nhiều hơn một món đạm chính. Có thể thay bớt bằng đậu, ngũ cốc hoặc rau củ."
BAD_MENU_FAT_SPREAD_TERMS = (
    "margarine",
    "bo thuc vat",
    "vegetable oil spread",
    "buttery spread",
)
VEGETARIAN_SAFE_FILL_CATEGORIES = {
    "fruit",
    "vegetable",
    "starch_grain",
    "starch_tuber",
    "healthy_fat_nuts",
    "dairy",
    "plant_protein",
}
PROTEIN_EXCESS_WARNING_TEMPLATE = (
    "Protein đang vượt mục tiêu {excess_g}g. "
    "Nên giảm bớt món đạm và tăng năng lượng "
    "bằng tinh bột, trái cây hoặc chất béo tốt."
)
PROTEIN_EXCESS_WARNING = (
    "Protein đang vượt mục tiêu. Nên giảm bớt món đạm và tăng năng lượng bằng tinh bột hoặc chất béo tốt."
)
FISH_TERMS = ("ca", "fish", "salmon", "tuna", "mackerel", "sardine", "ca hoi", "ca thu", "ca ngu")
SHELLFISH_TERMS = ("tom", "shrimp", "prawn", "crab", "cua", "shellfish")
EGG_TERMS = ("trung", "egg")
MEAT_TERMS = (
    "thit",
    "meat",
    "chicken",
    "turkey",
    "beef",
    "pork",
    "lamb",
    "duck",
    "ga",
    "heo",
    "lon",
    "thit bo",
    "thit heo",
    "thit ga",
)
VEGETARIAN_BLOCKED_TERMS = MEAT_TERMS + tuple(term for term in FISH_TERMS if term != "ca") + SHELLFISH_TERMS + ("seafood", "hai san")
PROCESSED_MEAT_TERMS = (
    "biawurst",
    "bologna",
    "sausage",
    "hot dog",
    "corn dog",
    "luncheon",
    "deli meat",
    "cold cut",
    "cold cuts",
    "salami",
    "pepperoni",
    "ham",
    "bacon",
    "smoked meat",
    "processed meat",
    "processed",
    "thit nguoi",
    "thit che bien",
    "xuc xich",
    "giam bong",
    "mortadella",
)
DESSERT_SWEET_TERMS = (
    "dessert",
    "ice cream",
    "frozen dessert",
    "kem trai cay",
    "cake",
    "cookie",
    "pastry",
    "croissant",
    "donut",
    "doughnut",
    "sweet roll",
    "muffin",
    "candy",
    "sweets",
    "keo",
    "banh ngot",
    "banh sung bo",
)
REAL_BEEF_FAVORITE_TERMS = (
    "thit bo",
    "bo nac",
    "bo nuong",
    "bo xao",
    "bo luoc",
    "lean beef",
    "beef lean",
    "grilled beef",
    "stir fried beef",
    "boiled beef",
)
PROCESSED_FAVORITE_PENALTY_TERMS = (
    "biawurst",
    "xuc xich",
    "sausage",
    "processed",
    "processed meat",
    "thit che bien",
    "mortadella",
    "salami",
    "ham",
    "bacon",
)
SWEET_LOW_PRIORITY_TERMS = (
    "keo",
    "candy",
    "sweets",
)
NATURAL_FRUIT_TERMS = (
    "dau",
    "strawberry",
    "chuoi",
    "banana",
    "tao",
    "apple",
    "cam",
    "orange",
    "viet quat",
    "blueberry",
    "mam xoi",
    "raspberry",
)
SEMANTIC_FOOD_GROUP_TERMS = (
    ("egg", ("trung", "egg", "yolk", "long do trung")),
    ("milk_dairy", ("sua", "milk", "dairy", "cream", "kem", "cheese", "pho mai")),
    ("yogurt", ("sua chua", "yogurt", "yoghurt")),
    ("beef", ("thit bo", "bo nac", "bo xay", "beef", "lean beef")),
    ("chicken", ("thit ga", "uc ga", "ga nac", "chicken", "turkey")),
    ("fish_salmon", ("ca hoi", "salmon")),
    ("sweet_potato", ("khoai lang", "sweet potato")),
    ("rice", ("com", "gao", "gao lut", "rice")),
    ("potato", ("khoai tay", "potato")),
    ("tofu", ("dau hu", "dau phu", "tofu")),
    ("soy", ("dau nanh", "soy", "soybean")),
    ("fruit_berry", ("dau tay", "strawberry", "viet quat", "blueberry", "mam xoi", "raspberry", "berry")),
)
LEAN_CHICKEN_PROTEIN_TERMS = (
    "thit ga nac",
    "uc ga",
    "ga nuong",
    "ga luoc",
    "lean chicken",
    "chicken breast",
    "grilled chicken",
    "boiled chicken",
)
HEALTHY_HIGH_PROTEIN_TERMS = (
    "fish",
    "ca",
    "salmon",
    "tuna",
    "mackerel",
    "sardine",
    "egg",
    "trung",
    "milk",
    "sua",
    "yogurt",
    "sua chua",
    "bean",
    "dau",
    "tofu",
    "dau hu",
    "dau phu",
    "tempeh",
)
HEALTHY_GAIN_ENERGY_TERMS = (
    "avocado",
    "bo",
    "nuts",
    "hat",
    "almond",
    "walnut",
    "cashew",
    "peanut",
    "peanut butter",
    "olive",
    "olive oil",
    "dau olive",
    "egg",
    "trung",
    "salmon",
    "mackerel",
    "sardine",
    "tuna",
    "fatty fish",
    "ca hoi",
    "ca thu",
    "tofu",
    "dau hu",
    "dau phu",
    "whole milk",
    "sua nguyen kem",
    "full fat",
    "greek yogurt",
    "sua chua hy lap",
)

# ── Starch/calorie-dense foods to boost when kcal deficit but protein near target ──
ENERGY_STARCH_BOOST_TERMS = (
    "com", "gao", "gao lut", "rice", "brown rice",
    "yen mach", "oat", "oatmeal",
    "khoai lang", "khoai tay", "khoai", "sweet potato", "potato",
    "chuoi", "banana",
    "sua tuoi", "sua nguyen chat", "whole milk", "sua bo", "fresh milk",
    "bo dau phong", "peanut butter",
    "dau", "bean", "dau nanh", "soybean",
    "dau olive", "olive oil",
)

# ── Berry terms that should be reduced when already appearing in the day ──
COMMON_BERRY_TERMS = (
    "viet quat", "blueberry",
    "mam xoi", "raspberry",
    "dau tay", "strawberry",
    "berry", "berries",
)

# ── Common familiar Vietnamese foods – boost for all users ──
FAMILIAR_VN_FOOD_TERMS = (
    "com", "gao lut", "yen mach",
    "khoai lang", "khoai tay",
    "trung", "trung ga",
    "sua tuoi", "sua chua",
    "chuoi", "cam", "tao", "du du",
    "dau phu", "dau hu", "dau nanh",
    "rau cai", "ca rot", "bi do", "ca chua", "bong cai",
    "thit ga", "uc ga", "ga luoc", "ga nuong",
    "ca ro", "ca basa", "ca loc", "ca ngu", "ca thu",
)

# ── Less-familiar / unusual names for VN general users (soft penalty only) ──
LESS_FAMILIAR_VN_TERMS = (
    "ca mang",          # cá măng – uncommon to most users
    "sup ngheu",        # súp nghêu – clam soup
    "ngheu",            # nghêu – clams
    "sop ngheu",
)

BMI_NOT_UNDERWEIGHT = "BMI_NOT_UNDERWEIGHT"
BMI_OVERWEIGHT_NOT_SUPPORTED = "BMI_OVERWEIGHT_NOT_SUPPORTED"
BMI_OBESE_NOT_SUPPORTED = "BMI_OBESE_NOT_SUPPORTED"
BMI_SCOPE_MESSAGE = (
    "NutriGain hiện chỉ hỗ trợ tạo thực đơn tăng cân cho người thiếu cân có BMI dưới 18.5."
)
BMI_NOT_UNDERWEIGHT_MESSAGE = (
    BMI_SCOPE_MESSAGE
)
BMI_OVERWEIGHT_MESSAGE = BMI_SCOPE_MESSAGE
BMI_OBESE_MESSAGE = BMI_SCOPE_MESSAGE
BMI_SEVERE_UNDERWEIGHT_WARNING = (
    "BMI của bạn đang rất thấp. Thực đơn chỉ mang tính hỗ trợ, nên theo dõi cân nặng định kỳ "
    "và tham khảo chuyên gia dinh dưỡng khi cần."
)
BMI_REASON_BY_CATEGORY = {
    "normal": BMI_NOT_UNDERWEIGHT,
    "overweight": BMI_OVERWEIGHT_NOT_SUPPORTED,
    "obese": BMI_OBESE_NOT_SUPPORTED,
}
BMI_MESSAGE_BY_CATEGORY = {
    "normal": BMI_NOT_UNDERWEIGHT_MESSAGE,
    "overweight": BMI_OVERWEIGHT_MESSAGE,
    "obese": BMI_OBESE_MESSAGE,
}
WEIGHT_GAIN_GOAL_TERMS = {
    "gain",
    "weight_gain",
    "weight gain",
    "gain_weight",
    "muscle",
    "muscle_gain",
    "gain_muscle",
    "bulk",
    "healthy_gain",
    "tang can",
    "tăng cân",
}
MAINTAIN_TERMS = {"maintain", "maintenance", "keep", "stable", "giu can", "giữ cân"}
WEIGHT_LOSS_GOAL_TERMS = {"lose", "loss", "cut", "weight_loss", "weight loss", "giam can", "giảm cân"}


def _normalized_token(value: object) -> str:
    return " ".join(_normalize_search_text(value).replace("-", " ").replace("_", " ").split())


def _is_weight_gain_goal_value(value: object) -> bool:
    normalized = _normalized_token(value)
    return normalized in WEIGHT_GAIN_GOAL_TERMS or any(term in normalized for term in ("tang can", "weight gain"))


def _is_weight_loss_goal_value(value: object) -> bool:
    normalized = _normalized_token(value)
    return normalized in WEIGHT_LOSS_GOAL_TERMS or any(term in normalized for term in ("giam can", "weight loss"))


def _is_maintain_value(value: object) -> bool:
    normalized = _normalized_token(value)
    return not normalized or normalized in MAINTAIN_TERMS


def _has_weight_gain_intent(*, bmi: float | None, goal: object, weight_gain_speed: object) -> bool:
    if bmi is not None and bmi < 18.5:
        return True
    if _is_weight_loss_goal_value(goal):
        return False
    if _is_weight_gain_goal_value(goal):
        return True
    return not _is_maintain_value(weight_gain_speed)


def getCategoryPlaceholder(category: object) -> str:
    normalized = str(category or "").strip().lower()
    return CATEGORY_PLACEHOLDERS.get(normalized, DEFAULT_FOOD_PLACEHOLDER)


def _truthy(value: object) -> bool:
    return str(value or "").strip().lower() in {"true", "1", "yes", "y"}


def _valid_food_image_url(value: object) -> str:
    url = str(value or "").strip()
    lower = url.lower()
    if not url or lower in {"nan", "none", "null"}:
        return ""
    if lower.startswith(("http://", "https://", "/images/foods/")):
        return url
    return ""


def _uses_verified_real_photo(food: pd.Series | dict) -> bool:
    image_url = _valid_food_image_url(food.get("image_url", ""))
    source_type = str(food.get("image_source_type", "") or "").strip().lower()
    return bool(
        image_url
        and _truthy(food.get("image_verified", False))
        and source_type == "real"
    )


def getFoodImageUrl(food: pd.Series | dict) -> str:
    if _uses_verified_real_photo(food):
        return _valid_food_image_url(food.get("image_url", ""))
    category = food.get("clean_category", "")
    if category is None or (not isinstance(category, str) and pd.isna(category)):
        category = food.get("category", "")
    return getCategoryPlaceholder(category)


def calculateBMI(weight_kg: float | None, height_cm: float | None) -> float | None:
    if weight_kg is None or height_cm is None:
        return None
    height_m = float(height_cm) / 100.0
    if height_m <= 0:
        return None
    return round(float(weight_kg) / (height_m * height_m), 1)


def validateUserProfile(payload: RecommendationInput) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    weight = payload.weight
    height = payload.height
    age = payload.age
    target_weight = getattr(payload, "target_weight", None)

    if weight is None or height is None:
        errors.append("Cần bổ sung chiều cao và cân nặng để tính BMI.")
    if weight is not None and not (20 <= float(weight) <= 250):
        errors.append("Cân nặng nằm ngoài ngưỡng hợp lý 20-250kg.")
    if height is not None and not (100 <= float(height) <= 230):
        errors.append("Chiều cao nằm ngoài ngưỡng hợp lý 100-230cm.")
    if age is not None and not (1 <= int(age) <= 120):
        errors.append("Tuổi nằm ngoài ngưỡng hợp lý 1-120.")

    if weight is not None and not (25 <= float(weight) <= 250):
        warnings.append("Cân nặng hiện tại nằm ngoài khoảng phổ biến (25-250kg).")
    if height is not None and not (120 <= float(height) <= 220):
        warnings.append("Chiều cao hiện tại nằm ngoài khoảng phổ biến (120-220cm).")
    if age is not None and not (13 <= int(age) <= 100):
        warnings.append("Tuổi hiện tại nằm ngoài khoảng phổ biến (13-100).")
    if target_weight is not None and not (25 <= float(target_weight) <= 250):
        warnings.append("Mục tiêu cân nặng nằm ngoài khoảng phổ biến (25-250kg).")

    bmi = calculateBMI(weight, height)
    if bmi is None:
        errors.append("Không thể tính BMI từ hồ sơ hiện tại.")
    else:
        if bmi < 14:
            warnings.append("Cân nặng hiện tại rất thấp so với chiều cao. Bạn nên tham khảo ý kiến chuyên gia dinh dưỡng hoặc bác sĩ trước khi áp dụng thực đơn tăng cân.")
        elif 14 <= bmi < 16:
            warnings.append("BMI của bạn đang ở mức thiếu cân nặng. Hãy tăng cân từ từ và theo dõi sức khỏe định kỳ.")
            
    if target_weight is not None and weight is not None:
        diff = float(target_weight) - float(weight)
        goal_type = str(getattr(payload, "goal_type", "gain") or "gain").strip().lower()
        if diff > 30:
            warnings.append("Mục tiêu tăng cân khá lớn. Hệ thống sẽ hỗ trợ theo từng giai đoạn, bạn nên đặt mục tiêu ngắn hạn hơn.")
        if diff <= 0 and goal_type in {"gain", "muscle", "muscle_gain"}:
            warnings.append("Mục tiêu cân nặng không lớn hơn cân nặng hiện tại nhưng chế độ là tăng cân. Hãy kiểm tra lại.")

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "bmi": bmi,
    }


def calculateNutritionTargets(profile: UserProfile | dict) -> dict:
    if isinstance(profile, dict):
        weight_kg = float(profile.get("weight_kg", profile.get("weight", 0)))
        height_cm = float(profile.get("height_cm", profile.get("height", 0)))
        age = int(profile.get("age", 25))
        sex = str(profile.get("sex") or profile.get("gender") or "male")
        activity_level = str(profile.get("activity_level", profile.get("activity", "moderate")))
        gain_speed = str(profile.get("weight_gain_speed", profile.get("gain_speed", "moderate")))
        goal = profile.get("goal", profile.get("goal_type", "gain"))
        target_weight = profile.get("target_weight", profile.get("target_weight_kg", None))
    else:
        weight_kg = profile.weight_kg
        height_cm = profile.height_cm
        age = profile.age if profile.age is not None else 25
        sex = profile.sex or "male"
        activity_level = profile.activity_level
        gain_speed = profile.weight_gain_speed or "moderate"
        goal = profile.goal or "gain"
        target_weight = getattr(profile, "target_weight", None)

    result = NutritionCalculationService.calculate_targets(
        weight_kg=weight_kg,
        height_cm=height_cm,
        age=age,
        gender=sex,
        activity_level=activity_level,
        gain_speed=gain_speed,
        target_weight=target_weight,
    )
    bmi = float(result["profile_summary"].get("bmi") or calculateBMI(weight_kg, height_cm) or 0.0)
    gain_intent = _has_weight_gain_intent(bmi=bmi, goal=goal, weight_gain_speed=gain_speed)
    if not gain_intent:
        nutrition_target = result["nutrition_target"]
        calorie_target = round(float(nutrition_target.get("tdee") or 0.0))
        reference_weight = max(float(weight_kg or 0.0), 1.0)
        protein_g = round(1.6 * reference_weight)
        fat_g = round((0.30 * calorie_target) / 9) if calorie_target > 0 else 0
        remaining_kcal = calorie_target - (protein_g * 4) - (fat_g * 9)
        nutrition_target.update(
            {
                "surplus": 0,
                "ramp_up_week": None,
                "calorie_target": calorie_target,
                "protein_g": protein_g,
                "fat_g": fat_g,
                "carbs_g": max(0, round(remaining_kcal / 4)),
            }
        )
    return result


def normalizeFoodCategory(category: str, name: str = "") -> str:
    return HealthyWeightGainRecommender.normalize_food_category(category, name)


def _normalize_search_text(value: object) -> str:
    return HealthyWeightGainRecommender._strip_accents(value).lower()


def normalize_text_vi(value: object) -> str:
    return HealthyWeightGainRecommender._strip_accents(str(value or "").strip().lower()).replace("đ", "d")


# ── Ingredient alias map for safe ingredient preference matching ──────────────
# Maps normalized input terms → list of aliases to check against food haystack
INGREDIENT_ALIASES: dict[str, list[str]] = {
    "thit heo": ["thit heo", "heo", "thit lon", "lon", "pork", "ba chi", "suon", "nac vai", "gio"],
    "heo":      ["thit heo", "heo", "thit lon", "lon", "pork", "ba chi", "suon", "nac vai", "gio"],
    "lon":      ["thit heo", "heo", "thit lon", "lon", "pork", "suon"],
    "pork":     ["thit heo", "heo", "thit lon", "lon", "pork", "ba chi", "suon"],
    "ca rot":   ["ca rot", "carrot"],
    "carrot":   ["ca rot", "carrot"],
    "trung":    ["trung", "egg", "trung ga", "trung vit"],
    "egg":      ["trung", "egg", "trung ga", "trung vit"],
    "trung ga": ["trung", "egg", "trung ga"],
    "thit ga":  ["thit ga", "ga", "chicken", "uc ga", "ga nuong", "ga luoc"],
    "ga":       ["thit ga", "ga", "chicken", "uc ga"],
    "chicken":  ["thit ga", "ga", "chicken", "uc ga"],
    "thit bo":  ["thit bo", "bo", "beef", "bo nac", "bo xao", "bo nuong"],
    "bo":       ["thit bo", "bo", "beef", "bo nac"],
    "beef":     ["thit bo", "bo", "beef", "bo nac"],
    "dau hu":   ["dau hu", "dau phu", "tofu"],
    "dau phu":  ["dau hu", "dau phu", "tofu"],
    "tofu":     ["dau hu", "dau phu", "tofu"],
    "rau cai":  ["rau cai", "cai xanh", "bok choy", "rau"],
    "nam":      ["nam", "mushroom", "nam huong", "nam rom"],
    "mushroom": ["nam", "mushroom", "nam huong"],
    "ca chua":  ["ca chua", "tomato"],
    "tomato":   ["ca chua", "tomato"],
    "ca hoi":   ["ca hoi", "salmon"],
    "salmon":   ["ca hoi", "salmon"],
    "tom":      ["tom", "shrimp", "prawn"],
    "shrimp":   ["tom", "shrimp", "prawn"],
    "khoai lang":["khoai lang", "sweet potato", "khoai"],
    "khoai tay":["khoai tay", "potato", "khoai"],
    "bong cai": ["bong cai", "broccoli", "bong cai xanh"],
    "broccoli": ["bong cai", "broccoli"],
    "chuoi":    ["chuoi", "banana"],
    "banana":   ["chuoi", "banana"],
    "sua":      ["sua", "milk", "sua tuoi", "sua bo"],
    "milk":     ["sua", "milk", "sua tuoi", "sua bo"],
    "sua chua": ["sua chua", "yogurt", "yoghurt"],
    "yogurt":   ["sua chua", "yogurt", "yoghurt"],
}


def _get_ingredient_aliases(normalized_key: str) -> list[str]:
    """Return expanded alias list for an ingredient normalized key."""
    return INGREDIENT_ALIASES.get(normalized_key, [normalized_key])


def normalize_ingredient_list(values: object) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in values or []:
        raw = str(item or "").strip()
        key = normalize_text_vi(raw)
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(raw)
    return result


def ingredient_match_list(food: object, available_ingredients: object) -> list[str]:
    """Return list of available_ingredients that match this food (with alias expansion)."""
    if not available_ingredients:
        return []

    def get_value(obj: object, key: str, default: object = "") -> object:
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    haystack_parts = [
        get_value(food, "name", ""),
        get_value(food, "original_name", ""),
        get_value(food, "category", ""),
        get_value(food, "clean_category", ""),
        get_value(food, "food_group", ""),
        get_value(food, "description", ""),
        get_value(food, "search_keywords", ""),
    ]

    ingredients = get_value(food, "ingredients", []) or []
    tags = get_value(food, "tags", []) or []

    if isinstance(ingredients, str):
        haystack_parts.append(ingredients)
    else:
        haystack_parts.append(" ".join(map(str, ingredients)))

    if isinstance(tags, str):
        haystack_parts.append(tags)
    else:
        haystack_parts.append(" ".join(map(str, tags)))

    haystack = normalize_text_vi(" ".join(str(x) for x in haystack_parts if x))
    padded_haystack = f" {haystack} "

    matched: list[str] = []
    for ing in available_ingredients or []:
        norm_key = normalize_text_vi(ing)
        if not norm_key:
            continue
        # Try direct match first
        aliases = _get_ingredient_aliases(norm_key)
        found = False
        for alias in aliases:
            alias_norm = normalize_text_vi(alias)
            if not alias_norm:
                continue
            # Use word-boundary-aware matching for short tokens
            if len(alias_norm) <= 3:
                if f" {alias_norm} " in padded_haystack:
                    found = True
                    break
            elif alias_norm in haystack:
                found = True
                break
        if found:
            matched.append(ing)
    return matched


def ingredient_match_count(food: object, available_ingredients: object) -> int:
    """Return count of available_ingredients matching this food (alias-expanded)."""
    return len(ingredient_match_list(food, available_ingredients))


def _safe_text(value: object) -> str:
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value or "")


def _protein_excess_warning(total_protein: float, target_protein: float) -> str:
    excess_g = max(int(round(float(total_protein or 0.0) - float(target_protein or 0.0))), 0)
    return PROTEIN_EXCESS_WARNING_TEMPLATE.format(excess_g=excess_g)


def _append_unique_message(messages: list[str], message: str | None) -> None:
    if message and message not in messages:
        messages.append(message)


def _append_unique_explanation(
    explanations: list[dict],
    explanation_type: str,
    food: str,
    reason: str,
) -> None:
    for entry in explanations:
        if entry.get("type") == explanation_type and entry.get("reason") == reason:
            foods = entry.setdefault("foods", [])
            if food not in foods:
                foods.append(food)
            if not entry.get("food"):
                entry["food"] = food
            return
    entry = {"type": explanation_type, "food": food, "foods": [food], "reason": reason}
    if entry not in explanations:
        explanations.append(entry)


def _format_food_terms_for_message(foods: list[str]) -> str:
    return ", ".join(str(food).strip() for food in foods if str(food).strip())


@lru_cache(maxsize=512)
def _normalized_match_terms_cached(terms_key: tuple[str, ...]) -> tuple[str, ...]:
    normalized_terms: list[str] = []
    for term in terms_key:
        normalized_term = " ".join(_normalize_search_text(term).strip().split())
        normalized_term = "".join(char if char.isalnum() or char.isspace() else " " for char in normalized_term)
        normalized_term = " ".join(normalized_term.split())
        if normalized_term:
            normalized_terms.append(normalized_term)
    return tuple(normalized_terms)


def _normalized_match_terms(terms: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    return _normalized_match_terms_cached(tuple(str(term or "") for term in terms))


def _row_match_text(row: pd.Series | dict) -> str:
    cached = row.get("_search_text_cache", "")
    try:
        has_cached_text = cached is not None and not pd.isna(cached) and bool(str(cached).strip())
    except (TypeError, ValueError):
        has_cached_text = bool(cached)
    if has_cached_text:
        return str(cached)
    raw_text = _normalize_search_text(
        " ".join(
            _safe_text(row.get(column, ""))
            for column in (
                "food_id",
                "name",
                "name_en",
                "display_name_en",
                "original_name",
                "search_keywords",
                "image_query",
                "quality_flags",
                "clean_category",
                "food_group",
                "category",
            )
        )
    )
    text = "".join(char if char.isalnum() or char.isspace() else " " for char in raw_text)
    return " ".join(text.split())


def _attach_row_search_cache(ranked: pd.DataFrame) -> pd.DataFrame:
    if ranked.empty or "_search_text_cache" in ranked.columns:
        return ranked
    next_ranked = ranked.copy()
    next_ranked["_search_text_cache"] = next_ranked.apply(_row_match_text, axis=1)
    return next_ranked


def _limit_ranked_candidate_pool(ranked: pd.DataFrame, meal_slots: int, top_n: int | None = None) -> pd.DataFrame:
    if ranked.empty:
        return ranked
    pool_limit = max(600, min(1200, max(int(meal_slots or 0) * 80, int(top_n or 0) * 12)))
    if len(ranked) <= pool_limit:
        return ranked
    reserve = min(300, max(120, pool_limit // 4))
    top_rows = ranked.head(max(pool_limit - reserve, pool_limit // 2))
    category_column = "clean_category" if "clean_category" in ranked.columns else "category" if "category" in ranked.columns else None
    if category_column:
        category_count = max(int(ranked[category_column].nunique(dropna=True) or 1), 1)
        per_category = max(12, min(60, reserve // category_count + 1))
        category_rows = ranked.groupby(category_column, group_keys=False).head(per_category)
        candidate_pool = pd.concat([top_rows, category_rows], ignore_index=False)
    else:
        candidate_pool = top_rows
    subset = ["food_id"] if "food_id" in candidate_pool.columns else None
    candidate_pool = candidate_pool.drop_duplicates(subset=subset, keep="first").head(pool_limit)
    return candidate_pool.sort_values("score", ascending=False)


def _row_matches_terms(row: pd.Series | dict, terms: list[str]) -> bool:
    text = _row_match_text(row)
    padded_text = f" {text} "
    is_soy_milk = _text_has_any(text, SOY_MILK_TERMS)
    for normalized_term in _normalized_match_terms(terms):
        if is_soy_milk and normalized_term in DAIRY_EXCLUSION_TERMS:
            continue
        if " " not in normalized_term and len(normalized_term) <= 3:
            if f" {normalized_term} " in padded_text:
                return True
        elif normalized_term in text:
            return True
    return False


def _row_search_text(row: pd.Series | dict) -> str:
    return _normalize_search_text(
        " ".join(
            _safe_text(row.get(column, ""))
            for column in (
                "food_id",
                "name",
                "name_en",
                "display_name_en",
                "original_name",
                "search_keywords",
                "image_query",
                "quality_flags",
                "clean_category",
                "food_group",
                "category",
            )
        )
    )


def _text_has_term(text: str, term: str) -> bool:
    normalized_term = " ".join(_normalize_search_text(term).strip().split())
    if not normalized_term:
        return False
    if " " not in normalized_term and len(normalized_term) <= 3:
        return f" {normalized_term} " in f" {text} "
    return normalized_term in text


def _text_has_any(text: str, terms: tuple[str, ...] | list[str]) -> bool:
    return any(_text_has_term(text, term) for term in terms)


def _row_category(row: pd.Series | dict) -> str:
    return str(row.get("clean_category", row.get("category", "")) or "").strip().lower()


def _is_animal_protein_category(category: object) -> bool:
    normalized = _canonical_food_category(category)
    return normalized in {"protein_meat", "protein_seafood"}


def _animal_main_protein_source(row: pd.Series | dict) -> str:
    category = _canonical_food_category(
        row.get("clean_category", row.get("category", "")),
        row.get("name", ""),
    )
    text = _row_search_text(row)
    if category == "egg" or _text_has_any(text, EGG_TERMS):
        return "egg"
    if category == "protein_seafood" or _text_has_any(text, FISH_TERMS + SHELLFISH_TERMS + ("seafood", "hai san")):
        return "seafood"
    if category == "protein_meat" or _text_has_any(text, MEAT_TERMS):
        if _text_has_any(text, ("beef", "thit bo")):
            return "beef"
        if _text_has_any(text, ("chicken", "turkey", "thit ga", "ga")):
            return "chicken"
        return "meat"
    return ""


def _is_animal_meat_or_seafood_row(row: pd.Series | dict) -> bool:
    category = _canonical_food_category(row.get("clean_category", row.get("category", "")), row.get("name", ""))
    return category in {"protein_meat", "protein_seafood"} or _row_matches_terms(row, list(VEGETARIAN_BLOCKED_TERMS)) or is_non_vegetarian_food(row)


def _is_vegetarian_diet(value: object) -> bool:
    normalized = _normalize_search_text(value or "")
    return normalized in {"vegetarian", "chay"} or "vegetarian" in normalized or "an chay" in normalized


def _is_vegan_diet(value: object) -> bool:
    normalized = _normalize_search_text(value or "")
    return normalized in {"vegan", "thuan chay"} or "vegan" in normalized or "thuan chay" in normalized


def _favorite_term_conflicts_with_vegetarian(term: object) -> bool:
    raw = str(term or "").strip().lower()
    normalized = " ".join(_normalize_search_text(raw).split())
    if not normalized:
        return False

    animal_phrases = (
        "thit ga",
        "thit bo",
        "thit heo",
        "thit lon",
        "beef",
        "chicken",
        "turkey",
        "pork",
        "lamb",
        "duck",
        "fish",
        "salmon",
        "tuna",
        "mackerel",
        "sardine",
        "shrimp",
        "prawn",
        "crab",
        "seafood",
        "meat",
        "egg",
        "trung",
    )
    if any(phrase in normalized for phrase in animal_phrases):
        return True

    accented_animal_terms = ("gà", "bò", "heo", "lợn", "cá", "tôm", "mực", "cua", "hải sản", "thịt", "trứng")
    if any(term_text in raw for term_text in accented_animal_terms):
        return True

    # Keep "bo" ambiguous: users may mean "bơ" (avocado/butter). Exact "bò" is caught above.
    return normalized in {"ga", "heo", "lon", "tom", "muc", "cua", "hai san", "trung", "egg"}


def _favorite_term_is_protein_limited(term: object) -> bool:
    raw = str(term or "").strip().lower()
    normalized = " ".join(_normalize_search_text(raw).split())
    if not normalized:
        return False
    protein_terms = (
        "thit",
        "meat",
        "beef",
        "chicken",
        "turkey",
        "pork",
        "fish",
        "salmon",
        "tuna",
        "shrimp",
        "prawn",
        "crab",
        "seafood",
        "egg",
        "trung",
        "milk",
        "yogurt",
        "dairy",
        "tofu",
        "dau hu",
        "dau phu",
        "soy",
        "bean",
    )
    accented_terms = ("gà", "bò", "heo", "lợn", "cá", "tôm", "mực", "cua", "hải sản", "thịt", "trứng", "sữa", "đậu hũ", "đậu phụ")
    return (
        any(term_text in raw for term_text in accented_terms)
        or any(term_text in normalized for term_text in protein_terms)
        or normalized in {"ga", "heo", "lon", "tom", "muc", "cua", "hai san"}
    )


def _split_favorite_foods_by_diet(favorite_foods: list[str], diet_type: object) -> tuple[list[str], list[str]]:
    if not _is_vegetarian_diet(diet_type):
        return favorite_foods, []

    allowed: list[str] = []
    blocked: list[str] = []
    for favorite in favorite_foods:
        if _favorite_term_conflicts_with_vegetarian(favorite):
            blocked.append(favorite)
        else:
            allowed.append(favorite)
    return allowed, blocked


def _row_nutrient(row: pd.Series | dict, *keys: str) -> float:
    for key in keys:
        value = row.get(key, None)
        if value is None:
            continue
        try:
            if pd.isna(value):
                continue
        except TypeError:
            pass
        try:
            return float(value or 0.0)
        except (TypeError, ValueError):
            continue
    return 0.0


def _is_dairy_row(row: pd.Series | dict) -> bool:
    category = _row_category(row)
    text = _row_search_text(row)
    return category == "dairy" or _text_has_any(text, DAIRY_TERMS)


def _is_low_fat_dairy_row(row: pd.Series | dict) -> bool:
    if not _is_dairy_row(row):
        return False
    text = _row_search_text(row)
    if _text_has_any(text, LOW_FAT_DAIRY_TERMS):
        return True
    if _text_has_any(text, FULL_FAT_DAIRY_TERMS):
        return False
    fat = _row_nutrient(row, "fat_raw", "fat_per_serving_clean", "fat")
    calories = _row_nutrient(row, "calories_raw", "kcal_per_serving_clean", "calories")
    return fat <= 2.5 and calories <= 160.0


def _is_full_fat_dairy_row(row: pd.Series | dict) -> bool:
    if not _is_dairy_row(row) or _is_low_fat_dairy_row(row):
        return False
    text = _row_search_text(row)
    fat = _row_nutrient(row, "fat_raw", "fat_per_serving_clean", "fat")
    calories = _row_nutrient(row, "calories_raw", "kcal_per_serving_clean", "calories")
    return _text_has_any(text, FULL_FAT_DAIRY_TERMS) or (fat >= 4.0 and calories >= 110.0)


def _is_abnormal_fat_spread_row(row: pd.Series | dict) -> bool:
    text = _row_search_text(row)
    if not _text_has_any(text, BAD_MENU_FAT_SPREAD_TERMS):
        return False

    raw_category = _row_category(row)
    clean_category = _canonical_food_category(row.get("clean_category", row.get("category", "")), row.get("name", ""))
    calories = _row_nutrient(row, "kcal_per_serving_clean", "calories_raw", "calories", "kcal")
    serving_grams = _row_nutrient(row, "serving_grams", "quantity_g")
    standalone_spread = (
        raw_category in {"vegetable", "added_fat", "fat_spread", "margarine", "butter", "healthy_fat", "healthy_fat_nuts"}
        or clean_category in {"vegetable", "healthy_fat_nuts"}
    )
    if not standalone_spread:
        return False

    if raw_category in {"vegetable", "fat_spread", "margarine"} or clean_category == "vegetable":
        return True
    if calories > 0 and calories < 25.0:
        return True
    if serving_grams >= 80.0 and 0 < calories < 120.0:
        return True
    return False


def _is_processed_meat_row(row: pd.Series | dict) -> bool:
    category = _row_category(row)
    text = _row_search_text(row)
    return (
        category in {"processed_meat", "meat_processed"}
        or _text_has_any(text, PROCESSED_MEAT_TERMS)
    )


def _is_dessert_or_sweet_row(row: pd.Series | dict) -> bool:
    category = _row_category(row)
    text = _row_search_text(row)
    return category in {"dessert_sweets", "sweet_spread"} or _text_has_any(text, DESSERT_SWEET_TERMS + SWEET_LOW_PRIORITY_TERMS)


def _favorite_foods_include_beef(favorite_foods: object) -> bool:
    normalized = " ".join(_normalize_search_text(term) for term in _coerce_profile_terms(favorite_foods))
    return _text_has_any(normalized, ("bo", "beef", "thit bo"))


def _is_real_beef_preference_row(row: pd.Series | dict) -> bool:
    category = _canonical_food_category(row.get("clean_category", row.get("category", "")), row.get("name", ""))
    if category != "protein_meat" or _is_processed_meat_row(row):
        return False
    return _text_has_any(_row_search_text(row), REAL_BEEF_FAVORITE_TERMS)


def _is_processed_favorite_penalty_row(row: pd.Series | dict) -> bool:
    return _is_processed_meat_row(row) or _text_has_any(_row_search_text(row), PROCESSED_FAVORITE_PENALTY_TERMS)


def _is_natural_fruit_row(row: pd.Series | dict) -> bool:
    category = _canonical_food_category(row.get("clean_category", row.get("category", "")), row.get("name", ""))
    return category == "fruit" and _text_has_any(_row_search_text(row), NATURAL_FRUIT_TERMS)


def normalize_food_similarity_key(food: pd.Series | dict) -> str:
    text = _row_search_text(food)
    for key, terms in SEMANTIC_FOOD_GROUP_TERMS:
        if _text_has_any(text, terms):
            return key

    category = _canonical_food_category(food.get("clean_category", food.get("category", "")), food.get("name", ""))
    if category in {"protein_meat", "protein_seafood", "egg", "dairy", "plant_protein"}:
        name_key = " ".join(_normalize_search_text(food.get("name", "")).split())
        return f"{category}:{name_key}" if name_key else category
    return ""


def _is_lean_chicken_preference_row(row: pd.Series | dict) -> bool:
    category = _canonical_food_category(row.get("clean_category", row.get("category", "")), row.get("name", ""))
    if category != "protein_meat" or _is_processed_meat_row(row):
        return False
    return _text_has_any(_row_search_text(row), LEAN_CHICKEN_PROTEIN_TERMS)


def _is_high_protein_preferred_row(row: pd.Series | dict) -> bool:
    if _is_processed_meat_row(row):
        return False
    category = _canonical_food_category(row.get("clean_category", row.get("category", "")), row.get("name", ""))
    if category in {"protein_seafood", "egg", "dairy", "plant_protein"}:
        return True
    if category == "protein_meat":
        return _is_real_beef_preference_row(row) or _is_lean_chicken_preference_row(row)
    text = _row_search_text(row)
    return _text_has_any(text, HEALTHY_HIGH_PROTEIN_TERMS)


def _healthy_favorite_score_adjustment(row: pd.Series | dict, favorite_foods: object) -> float:
    adjustment = 0.0
    if _favorite_foods_include_beef(favorite_foods):
        if _is_real_beef_preference_row(row):
            adjustment += 0.55
        elif _is_processed_favorite_penalty_row(row):
            adjustment -= 0.55

    if _is_processed_favorite_penalty_row(row):
        adjustment -= 0.20
    if _is_dessert_or_sweet_row(row) or _text_has_any(_row_search_text(row), SWEET_LOW_PRIORITY_TERMS):
        adjustment -= 0.24
    if _is_natural_fruit_row(row):
        adjustment += 0.14
    return adjustment


def _is_healthy_gain_energy_row(row: pd.Series | dict) -> bool:
    if _is_dessert_or_sweet_row(row) or _is_processed_meat_row(row) or _is_low_fat_dairy_row(row):
        return False
    category = _row_category(row)
    text = _row_search_text(row)
    protein = _row_nutrient(row, "protein_raw", "protein_per_serving_clean", "protein")
    fat = _row_nutrient(row, "fat_raw", "fat_per_serving_clean", "fat")
    if category in {"healthy_fat", "healthy_fat_nuts", "fats_good"}:
        return True
    if _is_full_fat_dairy_row(row):
        return True
    if category in {"egg", "protein_seafood"} and (fat >= 3.0 or protein >= 8.0):
        return True
    if category in {"protein_meat", "plant_protein", "protein_plant"} and protein >= 8.0:
        return True
    return _text_has_any(text, HEALTHY_GAIN_ENERGY_TERMS)


def _coerce_profile_terms(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, (list, tuple, set)):
        return tuple(str(item).strip() for item in value if str(item).strip())
    text = str(value).strip()
    if not text:
        return ()
    return tuple(part.strip() for part in text.replace(",", ";").split(";") if part.strip())


def _expand_food_terms(terms: list[str]) -> list[str]:
    synonym_map = {
        "ga": ["ga", "thit ga", "chicken", "turkey"],
        "gà": ["ga", "thit ga", "chicken", "turkey"],
        "chicken": ["ga", "thit ga", "chicken", "turkey"],
        "turkey": ["ga", "thit ga", "chicken", "turkey"],
        "ca": list(FISH_TERMS),
        "cá": list(FISH_TERMS),
        "fish": list(FISH_TERMS),
        "tom": list(SHELLFISH_TERMS),
        "tôm": list(SHELLFISH_TERMS),
        "shrimp": list(SHELLFISH_TERMS),
        "sua": ["sua", "sua bo", "sua tuoi", "sua chua", "milk", "cow milk", "fresh milk", "yogurt", "yoghurt", "dairy", "cheese", "pho mai", "cream", "kem"],
        "sữa": ["sua", "sua bo", "sua tuoi", "sua chua", "milk", "cow milk", "fresh milk", "yogurt", "yoghurt", "dairy", "cheese", "pho mai", "cream", "kem"],
        "sua dong vat": ["sua", "sua bo", "sua tuoi", "sua chua", "milk", "cow milk", "fresh milk", "yogurt", "yoghurt", "dairy", "cheese", "pho mai", "cream", "kem"],
        "milk": ["sua", "sua bo", "sua tuoi", "sua chua", "milk", "cow milk", "fresh milk", "yogurt", "yoghurt", "dairy", "cheese", "pho mai", "cream", "kem"],
        "trung": list(EGG_TERMS),
        "trứng": list(EGG_TERMS),
        "egg": list(EGG_TERMS),
    }
    expanded: list[str] = []
    seen: set[str] = set()
    for term in terms:
        if not term:
            continue
        raw_lower = str(term).strip().lower()
        normalized = " ".join(_normalize_search_text(term).split())
        if not normalized:
            continue

        if "bò" in raw_lower or normalized in {"beef", "thit bo"}:
            candidates = ["bo", "thit bo", "beef"]
        elif normalized in {"heo", "lon", "pork", "thit heo", "thit lon"} or "lợn" in raw_lower:
            candidates = ["heo", "lon", "thit heo", "thit lon", "pork"]
        elif normalized in {"meat", "thit"} or "thịt" in raw_lower:
            candidates = list(MEAT_TERMS)
        elif normalized in {"seafood", "hai san"} or "hải sản" in raw_lower:
            candidates = list(FISH_TERMS) + list(SHELLFISH_TERMS) + ["seafood", "hai san"]
        elif "mực" in raw_lower or normalized == "muc":
            candidates = ["muc", "squid", "seafood", "hai san"]
        elif normalized in {"sua", "sua dong vat", "milk", "dairy"}:
            candidates = ["sua", "sua bo", "sua tuoi", "sua chua", "milk", "cow milk", "fresh milk", "yogurt", "yoghurt", "dairy", "cheese", "pho mai", "cream", "kem"]
        else:
            candidates = synonym_map.get(normalized, [normalized])
        for candidate in candidates:
            key = " ".join(_normalize_search_text(candidate).split())
            if key and key not in seen:
                seen.add(key)
                expanded.append(candidate)
    return expanded


def _canonical_food_category(category: object, name: object = "") -> str:
    raw = _normalize_search_text(str(category or "")).strip()
    mapped = CATEGORY_ALIASES.get(raw, raw)
    if mapped in CANONICAL_FOOD_CATEGORIES:
        return mapped

    name_text = _normalize_search_text(str(name or ""))
    text = f"{mapped} {name_text}".strip()

    if any(term in text for term in ("rice", "com", "oat", "bread", "grain", "cereal", "noodle", "pasta")):
        return "starch_grain"
    if any(term in text for term in ("potato", "khoai", "tuber")):
        return "starch_tuber"
    if any(term in text for term in ("egg", "trung")):
        return "egg"
    if any(term in text for term in ("fish", "ca ", "seafood", "shrimp", "tom")):
        return "protein_seafood"
    if any(term in text for term in ("tofu", "dau hu", "dau phu", "bean", "soy")):
        return "plant_protein"
    if any(term in text for term in ("chicken", "turkey", "beef", "pork", "thit", "meat")):
        return "protein_meat"
    if any(term in text for term in ("vegetable", "rau")):
        return "vegetable"
    if any(term in text for term in ("fruit", "trai cay", "apple", "banana", "orange", "tao", "chuoi")):
        return "fruit"
    if any(term in text for term in ("milk", "yogurt", "cheese", "sua", "dairy")):
        return "dairy"
    if any(term in text for term in ("nut", "hat", "avocado", "olive", "oil", "bo dau phong", "peanut butter")):
        return "healthy_fat_nuts"
    if any(term in text for term in ("juice", "nuoc ep", "drink", "beverage", "nuoc trai cay")):
        return "drink_natural"
    if any(term in text for term in ("dessert", "cake", "cookie", "candy", "banh", "keo", "sweet")):
        return "dessert_sweets"
    return "other"


def macro_group(category: object) -> str:
    canonical = _canonical_food_category(category)
    if canonical in {"protein_meat", "protein_seafood", "plant_protein", "egg"}:
        return "protein"
    if canonical in {"vegetable"}:
        return "vegetable"
    if canonical in {"starch_grain", "starch_tuber"}:
        return "starch"
    if canonical in {"dairy"}:
        return "dairy"
    if canonical in {"fruit"}:
        return "fruit"
    return "extra"


def _serving_limits(category: object, name: object = "") -> tuple[float | None, float | None]:
    text = _normalize_search_text(f"{category} {name}")
    if "oil" in text or "olive" in text or "spread" in text or "butter" in text or "margarine" in text or "bo thuc vat" in text or "dau olive" in text:
        return 5.0, 20.0
    if "vegetable" in text or "rau" in text:
        return 80.0, 250.0
    if "dessert_sweets" in text or "sweet_spread" in text or "dessert" in text or "banh ngot" in text or "kem " in f"{text} ":
        return 50.0, 120.0
    if "fruit" in text or "trai cay" in text or "chuoi" in text or "banana" in text or "apple" in text or "tao" in text:
        return 80.0, 200.0
    if "yogurt" in text or "sua chua" in text:
        return 100.0, 200.0
    if "milk" in text or "sua" in text or "dairy" in text:
        return 180.0, 300.0
    if "plant_protein" in text or "protein_plant" in text or "tofu" in text or "dau hu" in text or "dau phu" in text:
        return 80.0, 220.0
    if "starch_grain" in text or "grain" in text or "rice" in text or "com" in text or "oat" in text:
        return 100.0, 250.0
    if "starch_tuber" in text or "potato" in text or "khoai" in text:
        return 100.0, 300.0
    if "protein_meat" in text or "meat" in text or "chicken" in text or "thit" in text:
        return 70.0, 160.0
    if "protein_seafood" in text or "seafood" in text or "fish" in text or " ca " in f" {text} ":
        return 70.0, 160.0
    if "egg" in text or "trung" in text:
        return 50.0, 120.0
    if "healthy_fat_nuts" in text or "fats_good" in text or "healthy_fat" in text or "nuts" in text or "hat" in text:
        return 10.0, 40.0
    return None, None


from app.core.config import settings
from app.models.entities import Food, FoodRating, MealPlanItem, RecommendationRequest, User, UserFavoriteFood, UserProfileEntity
from app.repositories.interaction_repository import InteractionRepository
from app.repositories.recommendation_repository import RecommendationRepository
from app.repositories.user_repository import UserRepository
from app.views.schemas import MealPlanRegenerateInput, RecommendationInput


class RecommenderService:
    @staticmethod
    def _weight_status_from_bmi(bmi: float | None) -> str:
        if bmi is None:
            return "unknown"
        return classify_asian_bmi(float(bmi))

    @staticmethod
    def _build_eligibility_check(payload: RecommendationInput) -> dict:
        profile_validation = validateUserProfile(payload)
        if not profile_validation["valid"]:
            return {
                "bmi": None if profile_validation["bmi"] is None else round(float(profile_validation["bmi"]), 2),
                "weight_status": "unknown",
                "bmi_category": "unknown",
                "bmi_label": "Đang theo dõi",
                "eligible": False,
                "reason": " ".join(profile_validation["errors"]),
                "warnings": profile_validation.get("warnings", []),
            }

        bmi = float(profile_validation["bmi"])
        weight_status = RecommenderService._weight_status_from_bmi(bmi)
        bmi_label = asian_bmi_label(weight_status)
        if bmi >= 18.5:
            reason = BMI_REASON_BY_CATEGORY.get(weight_status, BMI_NOT_UNDERWEIGHT)
            message = BMI_MESSAGE_BY_CATEGORY.get(weight_status, BMI_NOT_UNDERWEIGHT_MESSAGE)
            return {
                "bmi": round(bmi, 2),
                "weight_status": weight_status,
                "bmi_category": weight_status,
                "bmi_label": bmi_label,
                "eligible": False,
                "reason": reason,
                "message": message,
                "warnings": profile_validation.get("warnings", []),
            }

        return {
            "bmi": round(bmi, 2),
            "weight_status": weight_status,
            "bmi_category": weight_status,
            "bmi_label": bmi_label,
            "eligible": True,
            "reason": "Người dùng thiếu cân có BMI dưới 18.5 và đủ điều kiện tạo thực đơn tăng cân.",
            "message": BMI_SEVERE_UNDERWEIGHT_WARNING if bmi < 16 else None,
            "warnings": profile_validation.get("warnings", []),
        }

    @staticmethod
    def _raise_if_not_eligible(payload: RecommendationInput) -> dict:
        eligibility = RecommenderService._build_eligibility_check(payload)
        if not eligibility["eligible"]:
            if eligibility.get("reason") in {
                BMI_NOT_UNDERWEIGHT,
                BMI_OVERWEIGHT_NOT_SUPPORTED,
                BMI_OBESE_NOT_SUPPORTED,
            }:
                return eligibility
            detail = {
                "eligibility_check": eligibility,
                "overall_assessment": {
                    "score": 0,
                    "summary": "Không sinh thực đơn vì hồ sơ không đạt điều kiện sử dụng.",
                    "main_problems": [eligibility["reason"]],
                },
                "detected_issues": [
                    {
                        "meal": "profile",
                        "item_name": "",
                        "issue_type": "eligibility_error",
                        "severity": "high",
                        "evidence": eligibility["reason"],
                        "reason": "Không thể xác thực hồ sơ để tạo thực đơn phù hợp.",
                        "suggested_fix": "Bổ sung chiều cao, cân nặng và các thông tin hồ sơ bắt buộc.",
                    }
                ],
                "fixed_menu": [],
                "validation_rules_to_add": [
                    "Chặn request tạo thực đơn nếu thiếu chiều cao hoặc cân nặng.",
                    "Chặn request tạo thực đơn tăng cân nếu BMI >= 18.5.",
                ],
            }
            logger.error("Recommendation failed: %s", detail)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=detail,
            )
        return eligibility

    @staticmethod
    def _ineligible_scope_response(eligibility: dict) -> dict:
        bmi = eligibility.get("bmi")
        category = eligibility.get("bmi_category") or eligibility.get("weight_status") or "normal"
        label = eligibility.get("bmi_label") or asian_bmi_label(category)
        reason = eligibility.get("reason") or BMI_REASON_BY_CATEGORY.get(category, BMI_NOT_UNDERWEIGHT)
        message = eligibility.get("message") or BMI_MESSAGE_BY_CATEGORY.get(category, BMI_NOT_UNDERWEIGHT_MESSAGE)
        return {
            "eligible": False,
            "reason": reason,
            "bmi": bmi,
            "bmi_category": category,
            "bmi_label": label,
            "message": message,
            "meal_plan": None,
            "validation": None,
            "eligibility_check": {
                "bmi": bmi,
                "weight_status": category,
                "bmi_category": category,
                "bmi_label": label,
                "eligible": False,
                "reason": reason,
                "message": message,
            },
            "overall_assessment": {
                "score": 0,
                "summary": message,
                "main_problems": [message],
            },
            "detected_issues": [],
            "fixed_menu": [],
            "validation_rules_to_add": [
                "Tính BMI từ chiều cao/cân nặng và không tạo thực đơn tăng cân nếu BMI >= 18.5.",
            ],
        }

    @staticmethod
    def _normalize_food_category(category: str, name: str = "") -> str:
        normalized = HealthyWeightGainRecommender._semantic_category(category, name)
        return _canonical_food_category(normalized, name)

    @staticmethod
    def _build_recommender_from_sql(db: Session) -> HealthyWeightGainRecommender:
        inspector = inspect(db.bind)
        food_columns = {column["name"] for column in inspector.get_columns("foods")}
        id_column = "food_id" if "food_id" in food_columns else "id" if "id" in food_columns else None
        required_columns = {
            "dish_name_vi",
            "clean_category",
            "food_group_vi",
            "recommended_serving_g",
            "serving_display",
            "kcal_per_serving_clean",
            "protein_per_serving_clean",
            "fat_per_serving_clean",
            "carbs_per_serving_clean",
            "image_url",
            "image_source_type",
            "image_verified",
            "menu_eligible",
        }
        missing_columns = sorted(required_columns - food_columns)
        if id_column is None:
            missing_columns.insert(0, "id or food_id")
        if missing_columns:
            raise ValueError(f"foods table is missing required runtime columns: {missing_columns}")

        optional_columns = [
            "original_name",
            "display_name",
            "meal_role",
            "kcal_per_100g_clean",
            "protein_per_100g_clean",
            "fat_per_100g_clean",
            "carbs_per_100g_clean",
            "quality_flags",
            "image_alt_vi",
            "image_quality_note",
            "search_keywords",
            "is_common_food",
            "is_budget_friendly",
            "is_premium",
            "is_processed",
            "is_natural_food",
            "budget_tier",
            "natural_priority_score",
            "original_name",
        ]
        select_parts = [f"CAST({id_column} AS CHAR) AS food_id"]
        for column in [
            "dish_name_vi",
            "clean_category",
            "food_group_vi",
            "recommended_serving_g",
            "serving_display",
            "kcal_per_serving_clean",
            "protein_per_serving_clean",
            "fat_per_serving_clean",
            "carbs_per_serving_clean",
            "image_url",
            "image_source_type",
            "image_verified",
            *optional_columns,
        ]:
            if column in food_columns:
                select_parts.append(column)
            else:
                select_parts.append(f"NULL AS {column}")

        rows = db.execute(
            text(
                f"""
                SELECT {", ".join(select_parts)}
                FROM foods
                WHERE menu_eligible = 1
                """
            )
        ).mappings().all()
        clean_df = pd.DataFrame(rows)
        if clean_df.empty:
            raise ValueError("MySQL foods table has no rows with menu_eligible = 1.")

        severe_flags = {
            "raw_ingredient",
            "generic_name",
            "brand_or_restaurant",
            "abnormal_macro",
            "nutrition_outlier",
            "invalid_name",
            "wrong_category",
            "dessert_or_junk",
        }
        clean_df = clean_df[
            ~clean_df["quality_flags"].fillna("").astype(str).str.lower().apply(
                lambda flags: any(flag in flags for flag in severe_flags)
            )
        ].copy()
        if clean_df.empty:
            raise ValueError("MySQL foods table has no usable menu rows after quality filtering.")

        generic_mask = clean_df["dish_name_vi"].apply(HealthyWeightGainRecommender._is_generic_menu_name)
        non_generic_df = clean_df[~generic_mask].copy()
        if not non_generic_df.empty:
            clean_df = non_generic_df

        numeric_columns = [
            "recommended_serving_g",
            "kcal_per_100g_clean",
            "kcal_per_serving_clean",
            "protein_per_serving_clean",
            "fat_per_serving_clean",
            "carbs_per_serving_clean",
        ]
        for column in numeric_columns:
            clean_df[column] = pd.to_numeric(clean_df[column], errors="coerce")

        per_100_columns = {
            "protein_per_100g_clean": "protein_per_serving_clean",
            "fat_per_100g_clean": "fat_per_serving_clean",
            "carbs_per_100g_clean": "carbs_per_serving_clean",
        }
        serving_factor = clean_df["recommended_serving_g"] / 100.0
        for per_100_column, serving_column in per_100_columns.items():
            if per_100_column in clean_df.columns:
                clean_df[per_100_column] = pd.to_numeric(clean_df[per_100_column], errors="coerce")
            else:
                clean_df[per_100_column] = clean_df[serving_column] / serving_factor.replace(0, pd.NA)

        clean_df = clean_df.dropna(
            subset=[
                "food_id",
                "dish_name_vi",
                "clean_category",
                "recommended_serving_g",
                "kcal_per_serving_clean",
                "protein_per_serving_clean",
                "fat_per_serving_clean",
                "carbs_per_serving_clean",
            ]
        )
        if clean_df.empty:
            raise ValueError("MySQL foods table has no eligible menu rows after required nutrition filtering.")

        normalized_clean_category = clean_df.apply(
            lambda row: HealthyWeightGainRecommender.normalize_food_category(
                row.get("clean_category", ""),
                row.get("dish_name_vi", ""),
            ),
            axis=1,
        )
        image_url_series = (
            clean_df["image_url"]
            if "image_url" in clean_df.columns
            else pd.Series("", index=clean_df.index)
        )
        image_source_type_series = (
            clean_df["image_source_type"]
            if "image_source_type" in clean_df.columns
            else pd.Series("placeholder", index=clean_df.index)
        )
        image_verified_series = (
            clean_df["image_verified"]
            if "image_verified" in clean_df.columns
            else pd.Series(False, index=clean_df.index)
        )
        image_alt_series = (
            clean_df["image_alt_vi"]
            if "image_alt_vi" in clean_df.columns
            else pd.Series("", index=clean_df.index)
        )
        image_quality_note_series = (
            clean_df["image_quality_note"]
            if "image_quality_note" in clean_df.columns
            else pd.Series("", index=clean_df.index)
        )
        image_query_series = (
            clean_df["search_keywords"]
            if "search_keywords" in clean_df.columns
            else pd.Series("", index=clean_df.index)
        )
        image_requirement_series = (
            clean_df["image_requirement"]
            if "image_requirement" in clean_df.columns
            else pd.Series("", index=clean_df.index)
        )
        name_en_series = (
            clean_df["display_name"]
            if "display_name" in clean_df.columns
            else clean_df["dish_name_vi"]
        )
        original_name_series = (
            clean_df["original_name"]
            if "original_name" in clean_df.columns
            else name_en_series
        )
        bool_quality_series = {
            column: (
                clean_df[column]
                if column in clean_df.columns
                else pd.Series(False, index=clean_df.index)
            )
            for column in (
                "is_common_food",
                "is_budget_friendly",
                "is_premium",
                "is_processed",
                "is_natural_food",
            )
        }
        budget_tier_series = (
            clean_df["budget_tier"]
            if "budget_tier" in clean_df.columns
            else pd.Series("standard", index=clean_df.index)
        )
        natural_priority_series = (
            clean_df["natural_priority_score"]
            if "natural_priority_score" in clean_df.columns
            else pd.Series(0.5, index=clean_df.index)
        )
        bad_image_debug = clean_df.loc[
            image_url_series.fillna("").astype(str).str.strip().eq(""),
            ["food_id", "dish_name_vi", "clean_category"],
        ].head(5)
        if not bad_image_debug.empty:
            logger.info(
                "foods rows with missing image_url (first 5): %s",
                bad_image_debug.to_dict(orient="records"),
            )

        raw_df = pd.DataFrame(
            {
                "food_id": clean_df["food_id"].astype(str).str.strip(),
                "name": clean_df["dish_name_vi"].astype(str).str.strip(),
                "name_en": original_name_series.astype(str).str.strip(),
                "original_name": original_name_series.astype(str).str.strip(),
                "display_name_en": name_en_series.map(HealthyWeightGainRecommender.clean_food_name),
                "calories": clean_df["kcal_per_serving_clean"].astype(float),
                "protein": clean_df["protein_per_serving_clean"].astype(float),
                "fat": clean_df["fat_per_serving_clean"].astype(float),
                "carbs": clean_df["carbs_per_serving_clean"].astype(float),
                "category": normalized_clean_category.map(HealthyWeightGainRecommender.category_for_recommender),
                "clean_category": normalized_clean_category,
                "food_group": normalized_clean_category.map(HealthyWeightGainRecommender.category_label_vi),
                "quantity_g": clean_df["recommended_serving_g"].astype(float),
                "serving_grams": clean_df["recommended_serving_g"].astype(float),
                "base_serving_grams": clean_df["recommended_serving_g"].astype(float),
                "serving_display": clean_df["serving_display"].where(clean_df["serving_display"].notna(), "").astype(str),
                "kcal_per_100g_clean": clean_df["kcal_per_100g_clean"].astype(float),
                "protein_per_100g_clean": clean_df["protein_per_100g_clean"].astype(float),
                "fat_per_100g_clean": clean_df["fat_per_100g_clean"].astype(float),
                "carbs_per_100g_clean": clean_df["carbs_per_100g_clean"].astype(float),
                "image_query": image_query_series.where(image_query_series.notna(), "").astype(str),
                "image_requirement": image_requirement_series.where(image_requirement_series.notna(), "").astype(str),
                "image_url": image_url_series.where(image_url_series.notna(), "").astype(str).str.strip(),
                "image_alt_vi": image_alt_series.where(image_alt_series.notna(), "").astype(str).str.strip(),
                "image_source_type": image_source_type_series.where(image_source_type_series.notna(), "placeholder").astype(str).str.strip(),
                "image_verified": image_verified_series.where(image_verified_series.notna(), False),
                "image_quality_note": image_quality_note_series.where(image_quality_note_series.notna(), "").astype(str).str.strip(),
                "quality_flags": clean_df["quality_flags"].where(clean_df["quality_flags"].notna(), "").astype(str),
                "is_common_food": bool_quality_series["is_common_food"].fillna(False).astype(bool),
                "is_budget_friendly": bool_quality_series["is_budget_friendly"].fillna(False).astype(bool),
                "is_premium": bool_quality_series["is_premium"].fillna(False).astype(bool),
                "is_processed": bool_quality_series["is_processed"].fillna(False).astype(bool),
                "is_natural_food": bool_quality_series["is_natural_food"].fillna(False).astype(bool),
                "budget_tier": budget_tier_series.where(budget_tier_series.notna(), "standard").astype(str).str.strip(),
                "natural_priority_score": pd.to_numeric(natural_priority_series, errors="coerce").fillna(0.5).clip(lower=0.0, upper=1.0),
                "source": "mysql:foods",
            }
        )
        raw_df = raw_df[raw_df["category"].astype(str).str.lower() != "junk_food"].copy()

        scaled_df = raw_df[["food_id", "name", *FEATURE_COLUMNS, "category"]].copy()
        for column in FEATURE_COLUMNS:
            min_value = float(raw_df[column].min())
            max_value = float(raw_df[column].max())
            if max_value == min_value:
                scaled_df[column] = 0.0
            else:
                scaled_df[column] = (raw_df[column].astype(float) - min_value) / (max_value - min_value)

        merged_df = raw_df.merge(
            scaled_df[["food_id", *FEATURE_COLUMNS]],
            on="food_id",
            how="inner",
            suffixes=("_raw", "_scaled"),
            validate="one_to_one",
        )

        recommender = HealthyWeightGainRecommender(
            "mysql:foods",
            "mysql:foods",
            preference_model_path=settings.preference_model_path,
        )
        recommender.raw_df = raw_df
        recommender.scaled_df = scaled_df
        recommender.merged_df = merged_df
        recommender.feature_matrix = merged_df[[f"{col}_scaled" for col in FEATURE_COLUMNS]].to_numpy(dtype=float)
        recommender.feature_min = raw_df[FEATURE_COLUMNS].min()
        recommender.feature_max = raw_df[FEATURE_COLUMNS].max()
        recommender._load_preference_model()
        return recommender

    @staticmethod
    def _train_category_preferences_from_sql(db: Session, user_id: int | None = None) -> dict[str, float]:
        request_query = select(
            RecommendationRequest.preferred_categories,
            RecommendationRequest.excluded_categories,
        )
        if user_id is not None:
            request_query = request_query.where(RecommendationRequest.user_id == user_id)
        rows = db.execute(request_query).all()

        category_preferences: dict[str, float] = {}
        for preferred, excluded in rows:
            for category in RecommenderService._parse_categories(preferred):
                category_preferences[category] = category_preferences.get(category, 0.0) + 1.0
            for category in RecommenderService._parse_categories(excluded):
                category_preferences[category] = category_preferences.get(category, 0.0) - 1.0

        if user_id is not None:
            favorite_categories = db.execute(
                text(
                    """
                    SELECT f.clean_category
                    FROM foods f
                    JOIN user_favorite_foods uff ON uff.food_id = f.food_id
                    WHERE uff.user_id = :user_id
                    """
                ),
                {"user_id": user_id},
            ).scalars()
            for category in favorite_categories:
                normalized = RecommenderService._normalize_food_category(str(category))
                category_preferences[normalized] = category_preferences.get(normalized, 0.0) + 1.5

            rating_rows = db.execute(
                text(
                    """
                    SELECT f.clean_category, fr.rating
                    FROM foods f
                    JOIN food_ratings fr ON fr.food_id = f.food_id
                    WHERE fr.user_id = :user_id
                    """
                ),
                {"user_id": user_id},
            ).all()
            for category, rating in rating_rows:
                normalized = RecommenderService._normalize_food_category(str(category))
                category_preferences[normalized] = category_preferences.get(normalized, 0.0) + (
                    (int(rating) - 3) / 2.0
                )

        if not category_preferences:
            return {}

        max_abs = max(abs(value) for value in category_preferences.values()) or 1.0
        return {category: value / max_abs for category, value in category_preferences.items()}

    @staticmethod
    def _parse_categories(value: str | None) -> list[str]:
        if value is None:
            return []
        text = str(value).strip()
        if not text:
            return []
        return [part.strip().lower() for part in text.split(";") if part.strip()]

    @staticmethod
    def _parse_profile_list(value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, (list, tuple, set)):
            return [str(item).strip() for item in value if str(item).strip()]
        text = str(value).strip()
        if not text:
            return []
        return [part.strip() for part in text.replace(",", ";").split(";") if part.strip()]

    @staticmethod
    def _merge_profile_lists(*values: object) -> list[str]:
        merged: list[str] = []
        seen: set[str] = set()
        for value in values:
            for item in RecommenderService._parse_profile_list(value):
                key = _normalize_search_text(item)
                if key and key not in seen:
                    seen.add(key)
                    merged.append(item)
        return merged

    @staticmethod
    def _serialize_profile_list(value: object) -> str | None:
        items = RecommenderService._parse_profile_list(value)
        return ";".join(items) if items else None

    @staticmethod
    def _hydrate_payload_from_saved_profile(payload: RecommendationInput, saved_profile: object | None) -> None:
        if saved_profile is None:
            return

        fields_set = set(getattr(payload, "model_fields_set", set()))

        def field_missing(field_name: str) -> bool:
            value = getattr(payload, field_name, None)
            return field_name not in fields_set or value is None or value == ""

        def set_if_missing(field_name: str, value: object) -> None:
            if field_missing(field_name) and value is not None and value != "":
                setattr(payload, field_name, value)

        set_if_missing("age", getattr(saved_profile, "age", None))
        set_if_missing("sex", getattr(saved_profile, "sex", None) or getattr(saved_profile, "gender", None))
        set_if_missing("activity", getattr(saved_profile, "activity_level", None))
        set_if_missing("weight_gain_speed", getattr(saved_profile, "weight_gain_speed", None))
        set_if_missing("gain_speed", getattr(payload, "weight_gain_speed", None))
        set_if_missing("surplus_kcal", getattr(saved_profile, "surplus_kcal", None))
        set_if_missing("target_weight", getattr(saved_profile, "target_weight_kg", None))
        set_if_missing("diet_type", getattr(saved_profile, "diet_type", None))
        set_if_missing("diet_style", getattr(payload, "diet_type", None))
        if getattr(payload, "diet_style", None) and not getattr(payload, "diet_type", None):
            payload.diet_type = payload.diet_style
        elif getattr(payload, "diet_type", None) and not getattr(payload, "diet_style", None):
            payload.diet_style = payload.diet_type
        set_if_missing("budget_level", getattr(saved_profile, "budget_level", None))
        set_if_missing("items_per_meal", getattr(saved_profile, "items_per_meal", None))

    @staticmethod
    def _profile_goal_and_surplus(payload: RecommendationInput) -> tuple[str, float | None]:
        speed = _normalized_token(payload.weight_gain_speed or payload.gain_speed or "")
        speed_surplus = {
            # Slow / nhẹ
            "slow": 250.0,
            "nhe": 250.0,
            "nhẹ": 300.0,
            "nhe on dinh": 250.0,
            "nhẹ, ổn định": 300.0,
            # Medium / vừa
            "medium": 400.0,
            "moderate": 400.0,
            "vua": 400.0,
            "vừa": 400.0,
            # Fast / mạnh
            "fast": 650.0,
            "strong": 650.0,
            "nhanh": 650.0,
            "manh": 650.0,
            "mạnh": 500.0,
            # Stronger / mạnh hơn
            "manh hon": 750.0,
            "mạnh hơn": 550.0,
            "nhanh hon": 750.0,
            "nhanh hơn": 550.0,
            "faster": 750.0,
            "stronger": 750.0,
            "aggressive": 750.0,
        }
        gain_surplus = payload.surplus_kcal
        goal_type = str(payload.goal_type or "gain").strip().lower()
        if _is_weight_loss_goal_value(goal_type):
            return "maintain", 0.0
        if gain_surplus is None:
            if speed in speed_surplus:
                gain_surplus = speed_surplus[speed]
            else:
                # Partial match
                for key, val in speed_surplus.items():
                    if key and key in speed:
                        gain_surplus = val
                        break
        if _is_maintain_value(goal_type) and _is_maintain_value(speed):
            return "maintain", 0.0
        if goal_type in {"muscle", "muscle_gain", "gain_muscle"}:
            return "gain", gain_surplus or 300.0
        return "gain", gain_surplus

    @staticmethod
    def _normalize_budget_level(value: object) -> str:
        normalized = _normalize_search_text(str(value or "standard")).strip()
        if normalized in {"low", "saving", "savings", "cheap", "budget", "economy", "tiet kiem"}:
            return "low"
        if normalized in {"high", "premium", "flexible", "linh hoat", "linh hoat hon"}:
            return "high"
        return "standard"

    @staticmethod
    def _budget_score_adjustment(row: pd.Series | dict, budget_level: object) -> float:
        budget = RecommenderService._normalize_budget_level(budget_level)
        if budget not in {"low", "standard", "high"}:
            return 0.0

        text = _normalize_search_text(
            " ".join(
                str(row.get(column, "") or "")
                for column in (
                    "name",
                    "name_en",
                    "display_name",
                    "display_name_en",
                    "original_name",
                    "search_keywords",
                    "category",
                    "clean_category",
                    "food_group",
                    "quality_flags",
                )
            )
        )
        category = _canonical_food_category(row.get("clean_category", row.get("category", "")), row.get("name", ""))
        is_common_field = _truthy(row.get("is_common_food", False))
        is_budget_field = _truthy(row.get("is_budget_friendly", False))
        is_premium_field = _truthy(row.get("is_premium", False))
        is_processed_field = _truthy(row.get("is_processed", False))
        is_natural_field = _truthy(row.get("is_natural_food", False))
        budget_tier = _normalize_search_text(str(row.get("budget_tier", "") or "standard")).strip()
        try:
            natural_priority = float(row.get("natural_priority_score", 0.5) or 0.5)
        except (TypeError, ValueError):
            natural_priority = 0.5
        natural_priority = float(np.clip(natural_priority, 0.0, 1.0))

        affordable_terms = (
            "rice", "com", "gao", "gao lut", "brown rice",
            "oat", "oatmeal", "yen mach",
            "potato", "khoai", "khoai lang", "khoai tay", "khoai mon", "sweet potato",
            "egg", "trung",
            "bean", "dau", "soy", "soybean", "dau nanh", "tofu", "dau hu", "dau phu", "lentil",
            "vegetable", "rau", "cabbage", "cai", "carrot", "ca rot", "tomato", "ca chua",
            "banana", "chuoi",
            "milk", "sua", "soy milk", "sua dau nanh",
            "chicken", "ga luoc", "ga nuong", "uc ga", "thit ga",
            "fish", "ca ro", "ca basa", "ca loc", "ca thu", "ca ngu",
        )
        basic_dairy_terms = ("milk", "sua tuoi", "soy milk", "sua dau nanh")
        premium_terms = (
            "salmon", "ca hoi", "shrimp", "tom",
            "tenderloin", "sirloin", "ribeye", "wagyu", "beef loin", "bo than", "than lung",
            "premium", "fancy", "imported", "nhap khau", "cao cap",
            "greek yogurt", "sua chua hy lap",
            "raspberry", "mam xoi", "red raspberry", "cranberry", "nam viet quat", "blueberry", "viet quat",
            "strawberry", "dau tay",
            "blackberry", "berry", "berries",
            "almond", "walnut", "macadamia", "pistachio", "hazelnut", "cashew",
            "caviar", "brie", "camembert", "emmental", "gruyere", "raclette",
            "mix", "mixed juice", "juice mix", "nuoc ep mix", "nuoc buoi do mix", "grapefruit mix",
        )
        mix_or_drink_terms = (
            "mix", "mixed", "juice mix", "nuoc ep mix", "nuoc buoi do mix", "grapefruit mix",
            "smoothie mix", "beverage mix",
        )
        lean_regular_beef_terms = (
            "lean beef", "beef lean", "thit bo nac", "bo nac", "bo xao", "bo luoc", "bo nuong",
        )
        common_chicken_or_fish_terms = (
            "chicken", "thit ga", "ga luoc", "ga nuong", "uc ga",
            "fish", "ca ro", "ca basa", "ca loc", "ca thu",
        )

        # ── Less-common-for-VN-budget terms (soft penalty, not a hard filter) ─
        less_common_vn_budget_terms = (
            "turkey", "ga tay",                        # gà tây
            "burrito", "taquito", "taco",              # western fusion
            "wild plum", "man hoang da",               # mận hoang dã
            "apricot", "qua mo",                       # quả mơ
            "dried fig", "sung say",                   # sung sấy
            "ca bo", "avocado fish",                   # cá bơ
            "fig",                                     # quả sung tươi
            "blue cheese", "pho mai xanh",
            "smoked salmon", "ca hoi xong khoi",
            "bechamel", "cream sauce",
        )

        # ── Common affordable Vietnamese everyday foods (extra boost for low budget) ─
        extra_affordable_vn_terms = (
            "com", "gao", "gao lut", "khoai lang", "khoai tay",
            "trung", "dau phu", "dau hu", "dau nanh",
            "rau", "ca rot", "bi", "chuoi", "cam", "du du",
            "thit ga", "uc ga", "ga luoc", "ga nuong",
            "ca ro", "ca basa", "ca loc",
            "sua tuoi", "sua dau nanh",
        )

        is_affordable = (
            category in {"starch_grain", "starch_tuber", "egg", "plant_protein", "vegetable"}
            or any(term in text for term in affordable_terms)
        )
        is_basic_dairy = category == "dairy" and any(term in text for term in basic_dairy_terms) and "greek" not in text
        is_premium = any(term in text for term in premium_terms)
        is_mix_or_drink = any(term in text for term in mix_or_drink_terms)
        is_regular_beef = category == "protein_meat" and any(term in text for term in lean_regular_beef_terms)
        is_beef = category == "protein_meat" and any(term in text for term in ("beef", "thit bo", " bo "))
        is_fish_or_seafood = category == "protein_seafood"
        is_common_chicken_or_fish = any(term in text for term in common_chicken_or_fish_terms) and not is_premium
        is_expensive_nut_category = category == "healthy_fat_nuts" and not any(term in text for term in ("peanut", "dau phong"))

        if is_basic_dairy:
            is_affordable = True
        if is_expensive_nut_category:
            is_premium = True

        if budget == "low":
            adjustment = 0.0
            adjustment += 0.28 * float(is_budget_field)
            adjustment += 0.16 * float(is_common_field)
            adjustment += 0.12 * float(is_natural_field)
            adjustment += 0.18 if budget_tier == "low" else 0.0
            adjustment += (natural_priority - 0.5) * 0.26
            if is_affordable:
                adjustment += 0.46
            if is_basic_dairy:
                adjustment += 0.14
            if is_common_chicken_or_fish:
                adjustment += 0.16
            if is_regular_beef:
                adjustment -= 0.05
            elif is_beef or is_fish_or_seafood:
                adjustment -= 0.24
            if is_premium:
                adjustment -= 0.95
            if is_mix_or_drink:
                adjustment -= 0.45
            adjustment -= 0.58 * float(is_premium_field)
            adjustment -= 0.42 * float(is_processed_field)
            if budget_tier == "premium":
                adjustment -= 0.48
            elif budget_tier == "flexible":
                adjustment -= 0.18
            if natural_priority < 0.35:
                adjustment -= 0.22
            # Extra boost: common everyday Vietnamese foods
            if any(term in text for term in extra_affordable_vn_terms):
                adjustment += 0.22
            # Soft penalty: less-common / Western foods unfamiliar in VN budget cooking
            if any(term in text for term in less_common_vn_budget_terms):
                adjustment -= 0.38
            return adjustment

        if budget == "standard":
            adjustment = 0.0
            adjustment += 0.08 * float(is_budget_field)
            adjustment += 0.08 * float(is_common_field)
            adjustment += 0.06 * float(is_natural_field)
            adjustment += (natural_priority - 0.5) * 0.12
            if is_affordable:
                adjustment += 0.10
            if is_regular_beef or (is_fish_or_seafood and not is_premium):
                adjustment += 0.04
            if is_premium:
                adjustment -= 0.26
            if is_mix_or_drink:
                adjustment -= 0.18
            adjustment -= 0.12 * float(is_premium_field)
            adjustment -= 0.20 * float(is_processed_field)
            return adjustment

        adjustment = 0.0
        adjustment += 0.04 * float(is_common_field)
        adjustment += 0.05 * float(is_natural_field)
        adjustment += 0.12 * float(is_premium_field)
        adjustment += (natural_priority - 0.5) * 0.08
        if is_premium:
            adjustment += 0.16
        if is_regular_beef or is_fish_or_seafood:
            adjustment += 0.08
        if is_affordable:
            adjustment += 0.04
        adjustment -= 0.16 * float(is_processed_field)
        return adjustment

    @staticmethod
    def _natural_food_score_adjustment(row: pd.Series | dict) -> float:
        text = _normalize_search_text(
            " ".join(
                str(row.get(column, "") or "")
                for column in (
                    "name",
                    "name_en",
                    "display_name",
                    "display_name_en",
                    "original_name",
                    "search_keywords",
                    "category",
                    "clean_category",
                    "food_group",
                    "quality_flags",
                )
            )
        )
        category = _canonical_food_category(row.get("clean_category", row.get("category", "")), row.get("name", ""))
        is_common_field = _truthy(row.get("is_common_food", False))
        is_processed_field = _truthy(row.get("is_processed", False))
        is_natural_field = _truthy(row.get("is_natural_food", False))
        try:
            natural_priority = float(row.get("natural_priority_score", 0.5) or 0.5)
        except (TypeError, ValueError):
            natural_priority = 0.5
        natural_priority = float(np.clip(natural_priority, 0.0, 1.0))
        everyday_terms = (
            "rice", "com", "gao", "gao lut", "brown rice",
            "oat", "oatmeal", "yen mach",
            "potato", "khoai", "khoai lang", "khoai tay", "khoai mon", "sweet potato",
            "egg", "trung",
            "milk", "sua tuoi", "sua nguyen chat", "whole milk", "soy milk", "sua dau nanh",
            "soy", "soybean", "dau nanh", "tofu", "dau hu", "dau phu", "bean", "lentil",
            "vegetable", "rau", "cabbage", "cai", "carrot", "ca rot", "tomato", "ca chua", "pumpkin", "bi do",
            "banana", "chuoi", "apple", "tao", "orange", "cam", "papaya", "du du",
            "lean chicken", "chicken breast", "uc ga", "ga luoc", "ga nuong", "thit ga",
            "lean beef", "thit bo nac", "bo nac",
            "fish", "ca ro", "ca basa", "ca loc", "ca thu",
            "peanut butter", "bo dau phong",
        )
        low_natural_terms = (
            "mix", "mixed", "juice mix", "nuoc ep mix", "nuoc buoi do mix", "grapefruit mix",
            "snack", "fancy", "premium", "imported", "nhap khau", "cao cap",
            "processed", "che bien san", "canned", "dong hop", "sausage", "xuc xich", "bacon", "ham",
            "cream soup", "cream of mushroom", "soup cream", "sup kem", "sup kem nam",
            "dessert", "sweet", "cake", "cookie", "candy", "keo", "pastry", "donut", "ice cream",
            "blue cornmeal", "bot ngo xanh", "prickly pear", "qua le gai", "surstromming", "caviar",
        )
        adjustment = 0.0
        adjustment += 0.18 * float(is_natural_field)
        adjustment += 0.12 * float(is_common_field)
        adjustment += (natural_priority - 0.5) * 0.38
        if category in {"starch_grain", "starch_tuber", "egg", "plant_protein", "vegetable"}:
            adjustment += 0.16
        if any(term in text for term in everyday_terms):
            adjustment += 0.22
        if category in {"fruit", "dairy"} and any(term in text for term in ("banana", "chuoi", "apple", "tao", "orange", "cam", "papaya", "du du", "milk", "sua tuoi", "soy milk", "sua dau nanh")):
            adjustment += 0.10
        if any(term in text for term in low_natural_terms):
            adjustment -= 0.42
        if is_processed_field:
            adjustment -= 0.46
        if _is_processed_meat_row(row) or _is_dessert_or_sweet_row(row):
            adjustment -= 0.30
        return adjustment

    @staticmethod
    def _apply_budget_score_adjustments(
        ranked: pd.DataFrame,
        budget_level: object,
        *,
        strength: float = 1.0,
    ) -> pd.DataFrame:
        if ranked.empty:
            return ranked
        adjusted = ranked.copy()
        budget = RecommenderService._normalize_budget_level(budget_level)
        if budget not in {"low", "standard", "high"}:
            return adjusted
        budget_adjustment = adjusted.apply(
            lambda row: RecommenderService._budget_score_adjustment(row, budget) * float(strength),
            axis=1,
        )
        adjusted["score"] = adjusted["score"].astype(float) + budget_adjustment.astype(float)
        return adjusted.sort_values("score", ascending=False)

    @staticmethod
    def _apply_natural_food_score_adjustments(
        ranked: pd.DataFrame,
        *,
        strength: float = 1.0,
    ) -> pd.DataFrame:
        if ranked.empty:
            return ranked
        adjusted = ranked.copy()
        natural_adjustment = adjusted.apply(
            lambda row: RecommenderService._natural_food_score_adjustment(row) * float(strength),
            axis=1,
        )
        adjusted["score"] = adjusted["score"].astype(float) + natural_adjustment.astype(float)
        return adjusted.sort_values("score", ascending=False)

    @staticmethod
    def _apply_diet_and_budget_preferences(
        ranked: pd.DataFrame,
        payload: RecommendationInput,
        target: dict | None = None,
    ) -> pd.DataFrame:
        if ranked.empty:
            return ranked

        next_df = ranked.copy()
        diet_style = str(payload.diet_type or payload.diet_style or "balanced").strip().lower()
        normalized_diet_style = _normalize_search_text(diet_style)
        budget_level = str(payload.budget_level or "standard").strip().lower()
        target = target or {}
        bmi_for_scoring = (
            float(payload.weight / ((payload.height / 100) ** 2))
            if payload.weight and payload.height
            else float(target.get("bmi") or 99.0)
        )
        goal_type = str(payload.goal_type or target.get("goal") or "gain").strip().lower()
        gain_speed = payload.weight_gain_speed or payload.gain_speed or target.get("weight_gain_speed")
        gain_energy_mode = _has_weight_gain_intent(
            bmi=bmi_for_scoring,
            goal=goal_type,
            weight_gain_speed=gain_speed,
        )
        target_kcal = float(target.get("calories") or target.get("calorie_target") or payload.target_calories or 0.0)
        target_protein = float(target.get("protein") or target.get("protein_g") or payload.protein_target or 0.0)
        target_fat = float(target.get("fat") or target.get("fat_g") or payload.fat_target or 0.0)
        fat_priority = target_kcal > 0 and target_fat > 0 and ((target_fat * 9.0) / target_kcal) >= 0.28
        protein_priority = target_kcal > 0 and target_protein > 0 and ((target_protein * 4.0) / target_kcal) >= 0.16

        # ── Pre-build clean string Series (always bool-safe) ──────────────────
        # Use str.contains for masks so the result is always bool dtype.
        names = next_df["name"].fillna("").astype(str).str.lower()
        category = next_df["category"].fillna("").astype(str).str.lower()

        # ── Diet-type hard filters (remove rows) ──────────────────────────────
        if _is_vegetarian_diet(diet_style):
            blocked_mask = next_df.apply(_is_animal_meat_or_seafood_row, axis=1)
            next_df = next_df[~blocked_mask].copy()
            category = next_df["category"].fillna("").astype(str).str.lower()
            names = next_df["name"].fillna("").astype(str).str.lower()
        elif _is_vegan_diet(diet_style):
            blocked_mask = next_df.apply(
                lambda row: _is_animal_meat_or_seafood_row(row)
                or _canonical_food_category(row.get("clean_category", row.get("category", "")), row.get("name", "")) in {"egg", "dairy"},
                axis=1,
            )
            next_df = next_df[~blocked_mask].copy()
            category = next_df["category"].fillna("").astype(str).str.lower()
            names = next_df["name"].fillna("").astype(str).str.lower()

        if next_df.empty:
            return next_df

        # ── Helper: build a boolean mask from a list of keyword strings ────────
        name_parts = []
        for column in ("name", "name_en", "display_name_en", "original_name", "search_keywords"):
            if column in next_df.columns:
                name_parts.append(next_df[column].fillna("").astype(str))
        names = (name_parts[0] if name_parts else pd.Series("", index=next_df.index)).copy()
        for part in name_parts[1:]:
            names = names + " " + part
        names = names.str.lower()
        normalized_names = names.apply(_normalize_search_text)
        category = next_df["category"].fillna("").astype(str).str.lower()

        def _name_contains_any(terms: tuple | list) -> "pd.Series[bool]":
            """Return bool Series: True where name contains any of the terms."""
            import re
            raw_terms = [str(t) for t in terms if str(t).strip()]
            normalized_terms = [_normalize_search_text(t) for t in raw_terms if _normalize_search_text(t)]
            raw_pattern = "|".join(re.escape(t) for t in raw_terms)
            normalized_pattern = "|".join(re.escape(t) for t in normalized_terms)
            raw_mask = names.str.contains(raw_pattern, case=False, na=False, regex=True) if raw_pattern else pd.Series(False, index=next_df.index)
            normalized_mask = normalized_names.str.contains(normalized_pattern, case=False, na=False, regex=True) if normalized_pattern else pd.Series(False, index=next_df.index)
            return (raw_mask | normalized_mask).fillna(False)

        def _cat_is_any(cats: set) -> "pd.Series[bool]":
            """Return bool Series: True where category is in cats."""
            return category.isin(cats)

        is_high_protein_diet = (
            normalized_diet_style in {"high_protein", "high protein", "giau protein"}
            or "high protein" in normalized_diet_style
            or "giau protein" in normalized_diet_style
        )

        # ── Low-carb / keto ───────────────────────────────────────────────────
        if diet_style in {"low_carb", "low-carb", "keto", "high_protein", "high-protein"} or is_high_protein_diet:
            bmi_val = (
                float(payload.weight / ((payload.height / 100) ** 2))
                if payload.weight and payload.height
                else 99.0
            )
            goal_type = str(payload.goal_type or "gain").strip().lower()
            is_severely_underweight_gain = bmi_val < 17.0 and goal_type in {"gain", "muscle", "muscle_gain"}

            if is_severely_underweight_gain:
                # Smart low-carb: only penalise refined/processed carbs
                _refined_carb_terms = (
                    "candy", "kẹo", "soda", "nước ngọt", "soft drink",
                    "sugar", "đường trắng", "white bread", "cake", "bánh ngọt",
                    "cookie", "mứt", "jam", "jelly",
                )
                _complex_carb_terms = (
                    "khoai lang", "sweet potato", "yến mạch", "oat",
                    "cơm", "rice", "đậu", "bean", "chuối", "banana",
                    "sữa", "milk",
                )
                refined_mask: pd.Series = _name_contains_any(_refined_carb_terms)  # bool
                complex_mask: pd.Series = _name_contains_any(_complex_carb_terms)   # bool
                next_df["score"] = (
                    next_df["score"]
                    - 0.15 * refined_mask.astype(float)
                    + 0.10 * complex_mask.astype(float)
                )
            else:
                low_carb_boost_mask: pd.Series = _cat_is_any({"meat", "egg", "dairy", "healthy_fat", "plant_protein"})  # bool
                carb_penalty_mask: pd.Series = _cat_is_any({"grain", "fruit"})  # bool
                next_df["score"] = (
                    next_df["score"]
                    + 0.08 * low_carb_boost_mask.astype(float)
                    - 0.12 * carb_penalty_mask.astype(float)
                )

            if is_high_protein_diet:
                high_protein_preferred_mask = next_df.apply(_is_high_protein_preferred_row, axis=1).astype(bool)
                processed_meat_mask = next_df.apply(_is_processed_favorite_penalty_row, axis=1).astype(bool)
                real_beef_mask = next_df.apply(_is_real_beef_preference_row, axis=1).astype(bool)
                favorite_beef_bonus = 0.18 if _favorite_foods_include_beef(getattr(payload, "favorite_foods", [])) else 0.0
                next_df["score"] = (
                    next_df["score"]
                    + 0.55 * high_protein_preferred_mask.astype(float)
                    + favorite_beef_bonus * real_beef_mask.astype(float)
                    - 1.45 * processed_meat_mask.astype(float)
                )

        # ── Eat-clean / balanced-eat-clean ────────────────────────────────────
        elif any(term in normalized_diet_style for term in EAT_CLEAN_DIET_TERMS):
            clean_boost = next_df.apply(HealthyWeightGainRecommender._food_quality_score, axis=1)
            next_df["score"] = next_df["score"] + 0.06 * clean_boost.astype(float)

            # Penalty for drinks/juices/fortified beverages (bool mask, never float | float)
            _drink_terms = (
                "juice", "nuoc ep", "nước ép", "nuoc cam", "nuoc tao",
                "beverage", "do uong", "đồ uống",
                "tang cuong", "tăng cường", "fortified",
                "energy drink", "soft drink", "nuoc ngot", "nước ngọt",
                "soda", "smoothie", "sinh to", "sinh tố",
            )
            drink_name_mask: pd.Series = _name_contains_any(_drink_terms)       # bool
            drink_cat_mask: pd.Series = _cat_is_any({"drink_natural"})           # bool
            drink_penalty_mask: pd.Series = (drink_name_mask | drink_cat_mask).fillna(False)  # bool
            next_df["score"] = next_df["score"] - 0.40 * drink_penalty_mask.astype(float)

            # Penalty for unfamiliar cheeses and processed items
            _unfamiliar_for_clean = (
                "tilsit", "gouda", "emmental", "brie", "camembert",
                "cottage cheese", "ricotta", "processed cheese",
                "bơ thực vật", "margarine",
                "mix", "mì ống phô mai mix", "macaroni and cheese",
            )
            unfamiliar_mask: pd.Series = _name_contains_any(_unfamiliar_for_clean)  # bool
            next_df["score"] = next_df["score"] - 0.20 * unfamiliar_mask.astype(float)

            # ── Eat Clean specific penalties ──
            _ec_fried = ("chiên", "chien", "fried", "fries", "deep fried")
            _ec_sweets = ("snack", "bánh quế", "banh que", "waffle", "candy", "sweets", "kẹo", "keo")
            _ec_unnatural = ("que cá", "fish stick", "mix", "bột ngô xanh", "blue cornmeal", "quả lê gai", "prickly pear", "nước bưởi")
            fried_mask = _name_contains_any(_ec_fried)
            sweets_mask = _name_contains_any(_ec_sweets)
            unnatural_mask = _name_contains_any(_ec_unnatural)
            processed_meat_mask_ec = next_df.apply(_is_processed_favorite_penalty_row, axis=1).astype(bool)

            next_df["score"] = (
                next_df["score"]
                - 1.50 * processed_meat_mask_ec.astype(float)
                - 1.30 * fried_mask.astype(float)
                - 1.30 * sweets_mask.astype(float)
                - 1.00 * unnatural_mask.astype(float)
            )

            # ── Eat Clean specific boosts ──
            _ec_simple_cook = ("luộc", "luoc", "hấp", "hap", "nướng", "nuong", "áp chảo ít dầu", "ap chao it dau")
            _ec_good_carbs = ("cơm", "com", "gạo lứt", "gao lut", "yến mạch", "yen mach", "oat", "khoai lang hấp", "khoai lang luộc", "khoai lang hap", "khoai lang luoc")
            _ec_good_proteins = ("thịt bò nạc", "thit bo nac", "ức gà", "uc ga", "cá", "ca ", "trứng", "trung", "đậu phụ", "dau phu", "đậu hũ", "dau hu", "đậu nành", "dau nanh", "tempeh")
            _ec_good_extras = ("rau", "trái cây", "trai cay", "fruit", "hạt", "hat", "nut")

            simple_cook_mask = _name_contains_any(_ec_simple_cook)
            good_carbs_mask = _name_contains_any(_ec_good_carbs)
            good_proteins_mask = _name_contains_any(_ec_good_proteins)
            good_extras_mask = _name_contains_any(_ec_good_extras)

            next_df["score"] = (
                next_df["score"]
                + 0.40 * simple_cook_mask.astype(float)
                + 0.45 * good_carbs_mask.astype(float)
                + 0.45 * good_proteins_mask.astype(float)
                + 0.35 * good_extras_mask.astype(float)
            )

            # ── Eat Clean favorite specific logic ──
            fav_list = getattr(payload, "favorite_foods", [])
            fav_text = " ".join(_normalize_search_text(t) for t in _coerce_profile_terms(fav_list))
            
            if "bo " in fav_text or "beef" in fav_text or "thit bo" in fav_text:
                real_beef_mask = next_df.apply(_is_real_beef_preference_row, axis=1).astype(bool)
                next_df["score"] = next_df["score"] + 0.35 * real_beef_mask.astype(float)
                
            if "ga " in fav_text or "chicken" in fav_text or "thit ga" in fav_text:
                lean_chicken_mask = next_df.apply(_is_lean_chicken_preference_row, axis=1).astype(bool)
                next_df["score"] = next_df["score"] + 0.35 * lean_chicken_mask.astype(float)
                
            if "trung" in fav_text or "egg" in fav_text:
                good_egg_mask = _name_contains_any(("trứng luộc", "trung luoc", "trứng chín", "trung chin", "boiled egg"))
                next_df["score"] = next_df["score"] + 0.35 * good_egg_mask.astype(float)

        # ── Budget level scoring ───────────────────────────────────────────────
        if budget_level in {"low", "saving", "cheap", "tiết kiệm", "tiet kiem"}:
            # Common budget-friendly Vietnamese foods
            affordable_terms = (
                "rice", "com", "gao", "gao lut",
                "oat", "oatmeal", "yen mach",
                "egg", "trung",
                "tofu", "bean", "dau phu", "dau hu", "dau nanh", "lentil",
                "banana", "chuoi", "cam", "orange", "du du", "papaya", "tao", "apple",
                "potato", "khoai", "khoai lang", "khoai tay",
                "milk", "sua tuoi", "sua dau nanh",
                "chicken", "thit ga", "uc ga", "ga luoc", "ga nuong",
                "ca ro", "ca basa", "ca loc",
                "rau", "ca rot", "bi", "vegetable",
            )
            # Less-common / Western foods that rarely appear in VN budget meals
            less_common_budget_terms = (
                "turkey", "ga tay",
                "burrito", "taquito", "taco",
                "wild plum", "man hoang da",
                "apricot", "qua mo",
                "dried fig", "sung say", "fig",
                "ca bo", "avocado fish",
                "blue cheese", "pho mai xanh",
                "smoked salmon", "ca hoi xong khoi",
                "bechamel", "cream sauce",
            )
            affordable_mask: pd.Series = _name_contains_any(affordable_terms)          # bool
            less_common_mask: pd.Series = _name_contains_any(less_common_budget_terms) # bool
            premium_terms_base = ("salmon", "tuna", "shrimp", "almond", "walnut", "cheese", "avocado")
            premium_mask: pd.Series = _name_contains_any(premium_terms_base)           # bool
            next_df["score"] = (
                next_df["score"]
                + 0.12 * affordable_mask.astype(float)
                - 0.10 * premium_mask.astype(float)
                - 0.28 * less_common_mask.astype(float)
            )
        elif budget_level in {"high", "premium"}:
            premium_terms = ("salmon", "tuna", "avocado", "almond", "walnut", "yogurt")
            premium_boost_mask: pd.Series = _name_contains_any(premium_terms)    # bool
            next_df["score"] = next_df["score"] + 0.04 * premium_boost_mask.astype(float)
        next_df = RecommenderService._apply_budget_score_adjustments(next_df, budget_level, strength=1.0)
        next_df = RecommenderService._apply_natural_food_score_adjustments(next_df, strength=1.0)

        # ── Universal exotic / hard-to-find food penalty ──────────────────────
        _exotic_terms = (
            "fermented salmon", "ca hoi len men",
            "herring roe", "trung ca trich", "trứng cá trích",
            "caviar", "surstromming", "gravlax",
            "dandelion", "rau bo cong anh", "rau bồ công anh",
            "radish greens", "turnip greens", "rau cải củ",
            "boysenberry", "buttermilk", "cream of wheat", "kem lua mi", "kem lúa mì",
            "tofu yogurt", "soy yogurt", "sữa chua đậu phụ",
            "silken soybean", "dau nanh to tam", "đậu nành tơ tằm",
            "soybean mocha", "dau nanh mocha", "đậu nành mocha", "mocha",
            "chicory", "endive", "radicchio",
            "tilsit", "emmental", "raclette", "gruyere",
            "camembert", "brie", "dry cheese", "pho mai kho", "phô mai khô", "tilsit cheese", "phô mai tilsit",
            "cheese tomato sauce", "pho mai sot ca chua", "phô mai sốt cà chua",
            "cottage cheese", "ricotta",
            "offal", "organ meat", "sweetbread", "foie gras",
            "noi tang",
        )
        exotic_mask: pd.Series = _name_contains_any(_exotic_terms)               # bool
        next_df["score"] = next_df["score"] - 1.35 * exotic_mask.astype(float)

        # Keep sweet/processed foods as rare fallback items, not daily calorie fillers.
        _sweet_processed_terms = (
            "croissant", "banh sung bo", "bánh sừng bò",
            "ice cream", "kem trai cay", "kem trái cây", "frozen dessert",
            "dessert", "cake", "cookie", "pastry", "donut", "doughnut",
            "sweet roll", "muffin", "banh ngot", "bánh ngọt",
            "burrito", "taquito", "taco", "corn dog", "hot dog",
            "hazelnut", "kem hat", "kem hạt", "peanut butter roll", "cuon bo", "cuộn bơ",
        )
        sweet_processed_mask = (
            next_df.get("clean_category", pd.Series("", index=next_df.index)).astype(str).str.lower().isin({"dessert_sweets", "sweet_spread"})
            | _name_contains_any(_sweet_processed_terms)
        )
        next_df["score"] = next_df["score"] - 0.50 * sweet_processed_mask.astype(float)

        # ── Global familiar items boost & unfamiliar penalty ──────────────────
        _familiar_boost_terms = (
            "cơm", "com", "gạo lứt", "gao lut", "yến mạch", "yen mach", "bánh mì nguyên hạt", "banh mi nguyen hat",
            "khoai lang luộc", "khoai lang luoc", "khoai lang hấp", "khoai lang hap", "khoai lang nướng", "khoai lang nuong",
            "trứng", "trung", "thịt gà", "thit ga", "ức gà", "uc ga", "thịt bò nạc", "thit bo nac", "cá", "ca",
            "đậu phụ", "dau phu", "đậu nành", "dau nanh", "tempeh",
            "rau cải", "rau cai", "cà rốt", "ca rot", "bí", "bi", "cà chua", "ca chua",
            "chuối", "chuoi", "cam", "dâu", "dau", "việt quất", "viet quat"
        )
        _unfamiliar_penalty_terms = ("snack", "mix", "que cá", "que ca", "quả lê gai", "qua le gai", "bột ngô xanh", "bot ngo xanh")
        
        familiar_mask = _name_contains_any(_familiar_boost_terms)
        unfamiliar_mask2 = _name_contains_any(_unfamiliar_penalty_terms)
        
        next_df["score"] = (
            next_df["score"]
            + 0.15 * familiar_mask.astype(float)
            - 0.25 * unfamiliar_mask2.astype(float)
        )

        is_clean_like = any(term in normalized_diet_style for term in EAT_CLEAN_DIET_TERMS)
        low_fat_dairy_mask = next_df.apply(_is_low_fat_dairy_row, axis=1).astype(bool)
        full_fat_dairy_mask = next_df.apply(_is_full_fat_dairy_row, axis=1).astype(bool)
        processed_meat_mask = next_df.apply(_is_processed_meat_row, axis=1).astype(bool)
        dessert_sweet_mask = next_df.apply(_is_dessert_or_sweet_row, axis=1).astype(bool)
        healthy_gain_energy_mask = next_df.apply(_is_healthy_gain_energy_row, axis=1).astype(bool)
        if gain_energy_mode:
            low_fat_penalty = 0.75 if bmi_for_scoring < 18.5 else 0.45
            processed_penalty = 1.30 if is_clean_like else 0.75
            dessert_penalty = 1.15 if is_clean_like else 0.70
            next_df["score"] = (
                next_df["score"]
                - low_fat_penalty * low_fat_dairy_mask.astype(float)
                - processed_penalty * processed_meat_mask.astype(float)
                - dessert_penalty * dessert_sweet_mask.astype(float)
                + 0.34 * full_fat_dairy_mask.astype(float)
                + (0.30 + (0.18 if bmi_for_scoring < 16.0 else 0.0)) * healthy_gain_energy_mask.astype(float)
            )
        else:
            next_df["score"] = (
                next_df["score"]
                - 0.15 * processed_meat_mask.astype(float)
                - 0.12 * dessert_sweet_mask.astype(float)
                - (0.18 if fat_priority else 0.04) * low_fat_dairy_mask.astype(float)
                + (0.10 if fat_priority else 0.0) * full_fat_dairy_mask.astype(float)
            )

        # ── Universal boost for popular / easy-to-find foods ──────────────
        _popular_terms = (
            "com", "khoai", "yen mach", "sua tuoi", "sua chua", "sua",
            "chuoi", "tao", "trung", "thit ga", "uc ga", "ca", "rau cu", "hat", "nuts",
            "cơm", "rice", "khoai lang", "sweet potato",
            "yến mạch", "oat", "oatmeal",
            "trứng gà", "trứng", "egg",
            "sữa tươi", "sữa", "milk",
            "sữa chua", "yogurt",
            "đậu hũ", "đậu phụ", "tofu",
            "đậu nành", "soybean",
            "thịt gà", "ức gà", "chicken",
            "thịt nạc", "lean meat", "pork loin", "beef lean",
            "cá hồi", "cá ngừ", "cá rô", "cá basa", "fish",
            "rau củ", "rau củ hỗn hợp", "mixed vegetables", "rau xào", "rau luộc",
            "chuối", "banana", "bơ", "avocado", "táo", "apple",
            "hạt", "đậu phộng", "peanut", "almond", "walnut",
        )
        popular_mask: pd.Series = _name_contains_any(_popular_terms)              # bool
        next_df["score"] = next_df["score"] + 0.18 * popular_mask.astype(float)

        # ── Global Whole Food Boost & Processed Food Penalty ──────────────
        _whole_food_terms = (
            "tươi", "nguyên cám", "whole", "fresh", "thịt tươi", "cá tươi", "rau tươi", "nguyên hạt", "trái cây tươi",
        )
        _processed_food_terms = (
            "canned", "đóng hộp", "xúc xích", "sausage", "thịt xông khói", "bacon", 
            "chế biến sẵn", "đóng gói", "bơ thực vật", "margarine", "đồ hộp", "thịt nguội", "dăm bông", "ham",
            "mì gói", "instant noodle", "snack",
        )
        whole_food_mask: pd.Series = _name_contains_any(_whole_food_terms)
        processed_food_mask: pd.Series = _name_contains_any(_processed_food_terms)
        next_df["score"] = (
            next_df["score"]
            + 0.15 * whole_food_mask.astype(float)
            - 0.35 * processed_food_mask.astype(float)
        )

        _good_fat_terms = (
            "avocado", "bo", "bơ", "nuts", "hat", "hạt", "almond", "walnut",
            "peanut butter", "bo dau phong", "bơ đậu phộng", "olive", "dau olive", "dầu olive",
            "salmon", "ca hoi", "cá hồi",
        )
        _natural_protein_terms = (
            "egg", "trung", "trứng", "fish", "ca ", "cá ", "salmon", "tuna",
            "lean meat", "thit nac", "thịt nạc", "tofu", "dau hu", "đậu hũ", "greek yogurt",
        )
        category_series = next_df.get("clean_category", pd.Series("", index=next_df.index)).astype(str).str.lower()
        good_fat_mask = category_series.isin({"healthy_fat", "healthy_fat_nuts", "fats_good"}) | _name_contains_any(_good_fat_terms)
        natural_protein_mask = category_series.isin({"protein_meat", "protein_seafood", "egg", "plant_protein", "protein_plant"}) | _name_contains_any(_natural_protein_terms)
        if gain_energy_mode:
            next_df["score"] = (
                next_df["score"]
                + 0.16 * good_fat_mask.astype(float)
                + 0.10 * natural_protein_mask.astype(float)
            )
        else:
            next_df["score"] = (
                next_df["score"]
                + (0.08 if fat_priority else 0.0) * good_fat_mask.astype(float)
                + (0.07 if protein_priority else 0.02) * natural_protein_mask.astype(float)
            )

        # ── BMI < 16: boost easy-to-eat energy-dense familiar foods ───────────
        bmi_check = (
            float(payload.weight / ((payload.height / 100) ** 2))
            if payload.weight and payload.height
            else 99.0
        )
        if bmi_check < 16.0:
            _bmi16_priority_terms = (
                "cơm", "rice", "khoai lang", "sweet potato", "khoai tây", "potato",
                "yến mạch", "oat", "oatmeal", "bánh mì", "bread",
                "trứng", "egg", "thịt gà", "chicken", "cá", "fish",
                "đậu hũ", "đậu phụ", "tofu", "đậu nành", "soybean",
                "sữa chua", "yogurt", "sữa", "milk",
                "chuối", "banana", "bơ", "avocado",
                "xoài", "mango", "đu đủ", "papaya",
            )
            bmi16_mask: pd.Series = _name_contains_any(_bmi16_priority_terms)    # bool
            next_df["score"] = next_df["score"] + 0.18 * bmi16_mask.astype(float)

            # Penalty for highly processed / hard-to-eat foods
            _bmi16_penalty_terms = (
                "bơ thực vật", "margarine",
                "mix", "mixed", "mì ống phô mai mix", "macaroni and cheese",
                "canned", "đóng hộp", "xúc xích", "sausage",
            )
            bmi16_penalty_mask: pd.Series = _name_contains_any(_bmi16_penalty_terms)
            next_df["score"] = next_df["score"] - 0.25 * bmi16_penalty_mask.astype(float)

        # ── PHẦN 1: Boost tinh bột/sữa/chuối khi kcal còn thiếu nhưng protein gần đủ ──
        # Khi protein đã đạt >= 85% target nhưng kcal vẫn còn thiếu nhiều,
        # ưu tiên thêm năng lượng từ tinh bột, sữa, trái cây thay vì thêm đạm.
        _plan_kcal = float(target.get("calories") or target_kcal or 0.0)
        _plan_protein_target = float(target.get("protein") or target.get("protein_g") or target_protein or 0.0)
        if _plan_kcal > 0 and _plan_protein_target > 0:
            _protein_ratio = (target.get("current_protein") or 0.0)
            # Use payload-level signals if available; otherwise fall back to heuristic
            _protein_near_target = bool(target.get("protein_near_target", False))
            if not _protein_near_target:
                # Heuristic: high-protein diet with gain mode => assume protein likely near target
                _hp_diet = "high protein" in _normalize_search_text(target.get("diet_type", "") or "")
                _protein_near_target = _hp_diet and gain_energy_mode
            if _protein_near_target or gain_energy_mode:
                energy_starch_mask: pd.Series = _name_contains_any(ENERGY_STARCH_BOOST_TERMS)
                next_df["score"] = next_df["score"] + 0.20 * energy_starch_mask.astype(float)

        # ── PHẦN 2 & 3: Boost món Việt quen, giảm nhẹ tên lạ và quả mọng thừa ──
        familiar_vn_mask: pd.Series = _name_contains_any(FAMILIAR_VN_FOOD_TERMS)
        less_familiar_mask: pd.Series = _name_contains_any(LESS_FAMILIAR_VN_TERMS)
        berry_mask: pd.Series = _name_contains_any(COMMON_BERRY_TERMS)
        next_df["score"] = (
            next_df["score"]
            + 0.12 * familiar_vn_mask.astype(float)
            - 0.30 * less_familiar_mask.astype(float)
            - 0.18 * berry_mask.astype(float)  # reduce but don't hard-block berries
        )

        return next_df.sort_values("score", ascending=False)

    @staticmethod
    def filterFoodsByDietType(ranked: pd.DataFrame, diet_type: str, min_items: int = 0) -> pd.DataFrame:
        normalized_diet = _normalize_search_text(diet_type or "balanced")
        if ranked.empty:
            return ranked
        if _is_vegetarian_diet(normalized_diet):
            return ranked[~ranked.apply(_is_animal_meat_or_seafood_row, axis=1)].copy()
        if _is_vegan_diet(normalized_diet):
            blocked_mask = ranked.apply(
                lambda row: _is_animal_meat_or_seafood_row(row)
                or _canonical_food_category(row.get("clean_category", row.get("category", "")), row.get("name", "")) in {"egg", "dairy"},
                axis=1,
            )
            return ranked[~blocked_mask].copy()
        if not any(term in normalized_diet for term in EAT_CLEAN_DIET_TERMS):
            return ranked

        blocked_mask = ranked.apply(
            lambda row: (
                HealthyWeightGainRecommender._is_dirty_bulk_name(
                    f"{row.get('name', '')} {row.get('name_en', '')}"
                )
                or HealthyWeightGainRecommender._is_generic_menu_name(row.get("name", ""))
                or _row_matches_terms(row, EAT_CLEAN_BLOCKED_TERMS)
                or _is_processed_meat_row(row)
                or _is_dessert_or_sweet_row(row)
            ),
            axis=1,
        )
        preferred = ranked[~blocked_mask].copy()
        fallback = ranked[blocked_mask].copy()
        if len(preferred) >= max(0, int(min_items)) or fallback.empty:
            return preferred.sort_values("score", ascending=False)

        preferred["diet_fallback"] = False
        fallback["diet_fallback"] = True
        fallback["score"] = (fallback["score"].astype(float) - 1.0).clip(lower=0.0)
        return pd.concat([preferred, fallback], ignore_index=True).sort_values("score", ascending=False)

    @staticmethod
    def _filter_eat_clean_ineligible(ranked: pd.DataFrame, diet_style: str) -> pd.DataFrame:
        return RecommenderService.filterFoodsByDietType(ranked, diet_style)

    @staticmethod
    def pickBalancedMeal(
        ranked: pd.DataFrame,
        meal_structure: dict[str, int],
        target: dict,
    ) -> dict[str, pd.DataFrame]:
        STARCH_CATEGORIES = {"starch_grain", "starch_tuber"}
        PROTEIN_CATEGORIES = {"protein_meat", "protein_seafood", "plant_protein", "egg"}
        VEG_FRUIT_CATEGORIES = {"vegetable", "fruit"}
        EXTRA_CATEGORIES = {"dairy", "healthy_fat_nuts", "plant_protein", "egg"}
        DESSERT_CATEGORIES = {"dessert_sweets", "sweet_spread"}

        logger.info(f"Picking meals. Total ranked rows: {len(ranked)}")
        cat_counts = ranked["clean_category"].value_counts().to_dict()
        logger.info(f"Category counts before picking: {cat_counts}")

        plan: dict[str, pd.DataFrame] = {}
        target_calories = float(target.get("calories", 2000))
        target_bmi = None
        try:
            target_bmi = float(target.get("bmi")) if target.get("bmi") is not None else None
        except (TypeError, ValueError):
            target_bmi = None
        gain_energy_mode = bool(target.get("gain_energy_mode")) or _has_weight_gain_intent(
            bmi=target_bmi,
            goal=target.get("goal", "gain"),
            weight_gain_speed=target.get("weight_gain_speed"),
        )
        target_fat = float(target.get("fat") or target.get("fat_g") or 0.0)
        target_protein = float(target.get("protein") or target.get("protein_g") or 0.0)
        fat_priority = target_calories > 0 and target_fat > 0 and ((target_fat * 9.0) / target_calories) >= 0.28
        protein_priority = target_calories > 0 and target_protein > 0 and ((target_protein * 4.0) / target_calories) >= 0.16
        ratio_sum = sum(DEFAULT_MEAL_CALORIE_RATIOS.get(m, 0) for m in meal_structure) or float(len(meal_structure))
        
        seen_food_ids = set()
        seen_food_names: set[str] = set()
        starch_group_counts: dict[str, int] = {}
        family_counts: dict[str, int] = {}
        dairy_count = 0
        bean_count = 0
        dairy_soy_count = 0
        dessert_count = 0
        animal_protein_count = 0
        current_day_protein = 0.0
        is_eat_clean = any(term in _normalize_search_text(target.get("diet_type", "") or "balanced") for term in EAT_CLEAN_DIET_TERMS)
        vegetarian_mode = _is_vegetarian_diet(target.get("diet_type", ""))
        budget_level = RecommenderService._normalize_budget_level(target.get("budget_level", "standard"))
        max_animal_protein_count = 0 if vegetarian_mode else (2 if target_protein <= 95 else 3)

        def _row_clean_category(row: pd.Series | dict) -> str:
            return _canonical_food_category(
                row.get("clean_category", row.get("category", "")),
                row.get("name", ""),
            )

        def _row_name_text(row: pd.Series | dict) -> str:
            return _normalize_search_text(
                f"{row.get('name', '')} {row.get('name_en', '')} {row.get('display_name_en', '')}"
            )

        def _row_name_key(row: pd.Series | dict) -> str:
            return _normalize_search_text(row.get("name", "")).strip()

        def _row_semantic_key(row: pd.Series | dict) -> str:
            return normalize_food_similarity_key(row)

        def _row_is_animal_protein(row: pd.Series | dict) -> bool:
            return _row_clean_category(row) in {"protein_meat", "protein_seafood"} or _is_animal_meat_or_seafood_row(row)

        def _row_is_heavy_breakfast_protein(row: pd.Series | dict) -> bool:
            if not _row_is_animal_protein(row):
                return False
            name_text = _row_name_text(row)
            return _row_clean_category(row) == "protein_meat" or any(
                term in name_text
                for term in ("beef", "pork", "lamb", "rib", "steak", "thit bo", "thit heo", "suon", "bo ")
            )

        def _row_is_dessert(row: pd.Series | dict) -> bool:
            category = _row_clean_category(row)
            name_text = _row_name_text(row)
            return (
                _is_dessert_or_sweet_row(row)
                or category in DESSERT_CATEGORIES
                or HealthyWeightGainRecommender._is_dirty_bulk_name(name_text)
                or any(term in name_text for term in ("croissant", "pastry", "cake", "cookie", "ice cream", "kem trai cay", "banh ngot"))
            )

        def _row_is_primary_starch(row: pd.Series | dict) -> bool:
            category = _row_clean_category(row)
            carb_family = HealthyWeightGainRecommender._carb_family(row)
            name_text = _row_name_text(row)
            return (
                category in STARCH_CATEGORIES
                or carb_family in {"rice", "noodle", "pasta", "potato", "corn", "bread", "oat", "cereal"}
                or any(term in name_text for term in ("rice", "com", "noodle", "pasta", "spaghetti", "bread", "banh mi", "oat", "yen mach", "potato", "khoai"))
            )

        def _row_is_dairy_or_soy(row: pd.Series | dict) -> bool:
            category = _row_clean_category(row)
            family = HealthyWeightGainRecommender._food_family(row)
            name_text = _row_name_text(row)
            return (
                category in {"dairy", "plant_protein"}
                or family in {"milk", "yogurt", "cheese", "bean", "tofu", "soy"}
                or any(term in name_text for term in ("milk", "sua", "yogurt", "sua chua", "soy", "dau nanh", "tofu", "dau hu", "dau phu"))
            )

        def _row_is_good_gain_extra(row: pd.Series | dict) -> bool:
            category = _row_clean_category(row)
            return (
                _is_healthy_gain_energy_row(row)
                or category in {"healthy_fat_nuts", "egg"}
            )

        def _row_slot_adjustment(
            row: pd.Series | dict,
            slot_name: str,
            meal_has_starch: bool,
            meal_dairy_soy_count: int,
            meal_animal_main_sources: set[str] | None = None,
            current_protein: float = 0.0,
        ) -> float:
            category = _row_clean_category(row)
            name_text = _row_name_text(row)
            calories = max(float(row.get("calories_raw", row.get("kcal_per_serving_clean", 0.0)) or 0.0), 1.0)
            protein = float(row.get("protein_raw", row.get("protein_per_serving_clean", 0.0)) or 0.0)
            fat = float(row.get("fat_raw", row.get("fat_per_serving_clean", 0.0)) or 0.0)
            carbs = float(row.get("carbs_raw", row.get("carbs_per_serving_clean", 0.0)) or 0.0)
            carb_density = carbs * 4.0 / calories
            score_delta = 0.0

            if is_eat_clean and target_protein > 0 and current_protein > target_protein * 1.05:
                if category in PROTEIN_CATEGORIES or protein >= 8.0:
                    score_delta -= 1.50
                # Bù kcal bằng carb/fat tự nhiên
                if category in STARCH_CATEGORIES and not _row_is_dessert(row):
                    score_delta += 0.80
                if category == "healthy_fat_nuts":
                    score_delta += 0.50
                if category == "fruit" and any(term in name_text for term in ("chuoi", "cam", "dau", "viet quat")):
                    score_delta += 0.50

            if _row_is_dessert(row):
                score_delta -= 1.75 if dessert_count else 1.15
            if _is_processed_meat_row(row):
                score_delta -= 1.35
            if _is_low_fat_dairy_row(row):
                score_delta -= 0.85 if gain_energy_mode or fat_priority else 0.05
            if meal_has_starch and slot_name != "starch" and _row_is_primary_starch(row):
                score_delta -= 2.0
            if _row_is_dairy_or_soy(row) and dairy_soy_count >= 2:
                score_delta -= 0.45
            if _row_is_dairy_or_soy(row) and meal_dairy_soy_count >= 1 and slot_name != "protein":
                score_delta -= 0.55
            candidate_animal_source = _animal_main_protein_source(row)
            if candidate_animal_source and meal_animal_main_sources:
                score_delta -= 1.25
                if candidate_animal_source == "egg" or "egg" in meal_animal_main_sources:
                    score_delta -= 0.35

            if slot_name == "extra":
                if gain_energy_mode and _row_is_good_gain_extra(row):
                    score_delta += 0.60
                if (gain_energy_mode or fat_priority) and (
                    category == "healthy_fat_nuts"
                    or any(term in name_text for term in ("avocado", "bo", "nuts", "hat", "peanut butter", "olive", "oil", "dau olive"))
                ):
                    score_delta += 0.35
                if (gain_energy_mode or protein_priority) and (category == "egg" or any(term in name_text for term in ("egg", "trung"))):
                    score_delta += 0.16
                if (gain_energy_mode or fat_priority) and (_is_full_fat_dairy_row(row) or (category in {"dairy"} and fat >= 4.0)):
                    score_delta += 0.34
                if _is_low_fat_dairy_row(row):
                    score_delta -= 0.80 if gain_energy_mode or fat_priority else 0.05
                if category == "fruit" and (carbs >= 25.0 or carb_density >= 0.55):
                    score_delta -= 0.22
                if carbs >= 25.0 or carb_density >= 0.55:
                    score_delta -= 0.38
            elif slot_name == "protein":
                if category in PROTEIN_CATEGORIES:
                    score_delta += 0.18
                if _is_processed_meat_row(row):
                    score_delta -= 1.00
                if _row_is_primary_starch(row):
                    score_delta -= 0.35
            elif slot_name in {"vegetable_or_fruit", "vegetable"}:
                if category == "vegetable":
                    score_delta += 0.14
                elif category == "fruit" and carbs >= 24.0:
                    score_delta -= 0.10
            elif slot_name == "fruit_or_dairy":
                if category in {"fruit", "dairy"}:
                    score_delta += 0.12
            elif slot_name == "starch":
                if category in STARCH_CATEGORIES and not _row_is_dessert(row):
                    score_delta += 0.15

            score_delta += RecommenderService._budget_score_adjustment(row, budget_level) * 0.85
            score_delta += RecommenderService._natural_food_score_adjustment(row) * 0.75
            return score_delta

        for meal, requested_slots in meal_structure.items():
            meal_ratio = DEFAULT_MEAL_CALORIE_RATIOS.get(meal, 1.0 / len(meal_structure)) / ratio_sum
            meal_target_kcal = target_calories * meal_ratio
            
            if requested_slots <= 3:
                slots = [
                    {"name": "starch", "cats": STARCH_CATEGORIES, "required": True},
                    {"name": "protein", "cats": PROTEIN_CATEGORIES, "required": True},
                    {"name": "vegetable_or_fruit", "cats": VEG_FRUIT_CATEGORIES, "required": True},
                ]
            elif requested_slots == 4:
                slot_names = MEAL_SLOT_ROLES.get(meal, MEAL_SLOT_ROLES["lunch"])
                slots = [
                    {
                        "name": slot_name,
                        "cats": SLOT_CATEGORY_RULES.get(slot_name, {"other"}),
                        "required": slot_name != "extra",
                    }
                    for slot_name in slot_names
                ]
            else:
                slots = [
                    {"name": "starch", "cats": STARCH_CATEGORIES, "required": True},
                    {"name": "protein", "cats": PROTEIN_CATEGORIES, "required": True},
                    {"name": "vegetable", "cats": {"vegetable"}, "required": True},
                    {"name": "fruit_or_extra", "cats": {"fruit"}.union(EXTRA_CATEGORIES), "required": False},
                    {"name": "extra", "cats": EXTRA_CATEGORIES, "required": False},
                ]
            
            selected_rows = []
            selected_semantic_keys: set[str] = set()

            def _prefer_semantic_distinct(pool: pd.DataFrame) -> pd.DataFrame:
                if pool.empty or not selected_semantic_keys:
                    return pool
                distinct_pool = pool[
                    ~pool.apply(lambda row: bool(_row_semantic_key(row)) and _row_semantic_key(row) in selected_semantic_keys, axis=1)
                ].copy()
                return distinct_pool if not distinct_pool.empty else pool

            for slot_idx, slot in enumerate(slots):
                slot_name = slot["name"]
                allowed_cats = slot["cats"]
                
                pool = ranked[
                    ~ranked["food_id"].isin(seen_food_ids)
                    & ~ranked.apply(lambda row: _row_name_key(row) in seen_food_names, axis=1)
                ].copy()
                pool = _prefer_semantic_distinct(pool)
                if family_counts:
                    family_pool = pool[
                        ~pool.apply(
                            lambda row: family_counts.get(HealthyWeightGainRecommender._food_family(row), 0)
                            >= HealthyWeightGainRecommender._daily_family_limit(
                                HealthyWeightGainRecommender._food_family(row)
                            ),
                            axis=1,
                        )
                    ]
                    if not family_pool.empty:
                        pool = family_pool
                # Ensure drink_natural only used in extra slots
                if slot_name != "extra":
                    pool = pool[pool["clean_category"] != "drink_natural"]
                if dessert_count >= 1:
                    dessert_limited_pool = pool[~pool.apply(_row_is_dessert, axis=1)]
                    if not dessert_limited_pool.empty:
                        pool = dessert_limited_pool
                if slot_name == "starch" and starch_group_counts:
                    pool = pool[
                        pool.apply(
                            lambda row: starch_group_counts.get(str(row.get("clean_category", "")), 0) < 2,
                            axis=1,
                        )
                    ]
                if dairy_count >= 2:
                    pool = pool[pool["clean_category"] != "dairy"]
                if bean_count >= 2:
                    pool = pool[
                        ~pool.apply(lambda row: _row_clean_category(row) in {"plant_protein"}, axis=1)
                    ]
                if dairy_soy_count >= 3:
                    limited_pool = pool[
                        ~pool.apply(lambda row: _row_clean_category(row) in {"dairy", "plant_protein"}, axis=1)
                    ]
                    if not limited_pool.empty:
                        pool = limited_pool

                meal_has_starch = any(_row_is_primary_starch(row) for row in selected_rows)
                meal_dairy_soy_count = sum(1 for row in selected_rows if _row_is_dairy_or_soy(row))
                meal_animal_protein_count = sum(1 for row in selected_rows if _row_is_animal_protein(row))
                meal_animal_main_sources = {
                    source
                    for source in (_animal_main_protein_source(row) for row in selected_rows)
                    if source
                }
                if meal_has_starch and slot_name != "starch":
                    non_starch_pool = pool[~pool.apply(_row_is_primary_starch, axis=1)]
                    if not non_starch_pool.empty:
                        pool = non_starch_pool
                    
                constrained_pool = pool[pool.apply(lambda row: _row_clean_category(row) in allowed_cats, axis=1)]
                if slot_name == "protein" and not constrained_pool.empty:
                    natural_protein_pool = constrained_pool[
                        ~constrained_pool.apply(_is_processed_meat_row, axis=1)
                        & ~constrained_pool.apply(_row_is_dessert, axis=1)
                    ]
                    if not natural_protein_pool.empty:
                        constrained_pool = natural_protein_pool
                    if animal_protein_count >= max_animal_protein_count or meal_animal_protein_count >= 1:
                        non_animal_pool = constrained_pool[~constrained_pool.apply(_row_is_animal_protein, axis=1)]
                        if not non_animal_pool.empty:
                            constrained_pool = non_animal_pool
                    if meal == "breakfast":
                        lighter_breakfast_pool = constrained_pool[~constrained_pool.apply(_row_is_heavy_breakfast_protein, axis=1)]
                        if not lighter_breakfast_pool.empty:
                            constrained_pool = lighter_breakfast_pool
                if slot_name == "starch" and not constrained_pool.empty:
                    clean_starch_pool = constrained_pool[~constrained_pool.apply(_row_is_dessert, axis=1)]
                    if not clean_starch_pool.empty:
                        constrained_pool = clean_starch_pool
                if slot_name == "extra" and not constrained_pool.empty:
                    cleaner_extra_pool = constrained_pool[~constrained_pool.apply(_row_is_dessert, axis=1)]
                    if not cleaner_extra_pool.empty:
                        constrained_pool = cleaner_extra_pool
                    if gain_energy_mode or fat_priority:
                        healthy_extra_pool = constrained_pool[constrained_pool.apply(_row_is_good_gain_extra, axis=1)]
                        if not healthy_extra_pool.empty:
                            constrained_pool = healthy_extra_pool
                
                if constrained_pool.empty:
                    available = pool.apply(_row_clean_category, axis=1).value_counts().to_dict()
                    logger.warning(f"Slot {slot_name} fail to find strict match in {meal}. Available categories: {available}")
                    fallback_cats = allowed_cats.copy()
                    if "protein_meat" in allowed_cats:
                        fallback_cats.update({"protein_seafood", "plant_protein", "egg", "dairy"})
                    if "dairy" in allowed_cats or "healthy_fat_nuts" in allowed_cats:
                        fallback_cats.update({"dairy", "healthy_fat_nuts", "plant_protein", "fruit", "egg"})
                    if slot_name in {"vegetable_or_fruit", "fruit_or_dairy"}:
                        fallback_cats.update({"vegetable", "fruit"})

                    constrained_pool = pool[pool.apply(lambda row: _row_clean_category(row) in fallback_cats, axis=1)]

                    # Fallback of last resort: if we still can't find anything because daily limits are depleted,
                    # relax the daily limits and try finding items from the entire ranked pool.
                    if constrained_pool.empty:
                        relaxed_pool = ranked[
                            ~ranked["food_id"].isin(seen_food_ids)
                            & ~ranked.apply(lambda row: _row_name_key(row) in seen_food_names, axis=1)
                        ].copy()
                        relaxed_pool = _prefer_semantic_distinct(relaxed_pool)
                        if slot_name != "extra":
                            relaxed_pool = relaxed_pool[~relaxed_pool.apply(lambda row: _row_clean_category(row) == "drink_natural", axis=1)]
                        constrained_pool = relaxed_pool[relaxed_pool.apply(lambda row: _row_clean_category(row) in fallback_cats, axis=1)]

                    # Ultimate fallback: fallback to standard categories if slot matching fails
                    if constrained_pool.empty:
                        logger.warning(f"Slot {slot_name} in {meal} still empty. Applying standard category fallback.")
                        ultimate_cats = set()
                        if slot_name == "starch":
                            ultimate_cats.update(STARCH_CATEGORIES)
                        elif slot_name == "protein":
                            ultimate_cats.update(PROTEIN_CATEGORIES)
                        elif "veg" in slot_name or "fruit" in slot_name:
                            ultimate_cats.update(VEG_FRUIT_CATEGORIES)
                        else:
                            ultimate_cats.update(EXTRA_CATEGORIES)

                        # Try pool first, then ranked
                        constrained_pool = pool[pool.apply(lambda row: _row_clean_category(row) in ultimate_cats, axis=1)]
                        if constrained_pool.empty:
                            relaxed_pool = ranked[
                                ~ranked["food_id"].isin(seen_food_ids)
                                & ~ranked.apply(lambda row: _row_name_key(row) in seen_food_names, axis=1)
                            ].copy()
                            relaxed_pool = _prefer_semantic_distinct(relaxed_pool)
                            if slot_name != "extra":
                                relaxed_pool = relaxed_pool[~relaxed_pool.apply(lambda row: _row_clean_category(row) == "drink_natural", axis=1)]
                            constrained_pool = relaxed_pool[relaxed_pool.apply(lambda row: _row_clean_category(row) in ultimate_cats, axis=1)]

                    # Last resort: just use any available item from the entire pool
                    if constrained_pool.empty:
                        logger.warning(f"Slot {slot_name} in {meal} still empty after category fallback. Using any available item.")
                        relaxed_pool = ranked[
                            ~ranked["food_id"].isin(seen_food_ids)
                            & ~ranked.apply(lambda row: _row_name_key(row) in seen_food_names, axis=1)
                        ].copy()
                        relaxed_pool = _prefer_semantic_distinct(relaxed_pool)
                        if slot_name != "extra":
                            relaxed_pool = relaxed_pool[~relaxed_pool.apply(lambda row: _row_clean_category(row) == "drink_natural", axis=1)]
                        constrained_pool = relaxed_pool

                if constrained_pool.empty:
                    if slot["required"]:
                        logger.error(f"Required slot {slot_name} failed completely in meal {meal}")
                    continue
                
                scored_pool = constrained_pool.copy()
                scored_pool["_slot_score"] = scored_pool.apply(
                    lambda row: float(row.get("score", 0.0) or 0.0) + _row_slot_adjustment(
                        row,
                        slot_name,
                        meal_has_starch,
                        meal_dairy_soy_count,
                        meal_animal_main_sources,
                        current_day_protein,
                    ),
                    axis=1,
                )
                best_row = scored_pool.sort_values("_slot_score", ascending=False).iloc[0].copy()
                best_row = best_row.drop(labels=["_slot_score"], errors="ignore")
                
                slot_target_kcal = meal_target_kcal / len(slots)
                base_calories = max(float(best_row.get("calories_raw", 1.0) or 1.0), 1.0)
                serving_multiplier = float(np.clip(slot_target_kcal / base_calories, 0.15, 3.5))
                for nutrient_col in ("calories_raw", "protein_raw", "fat_raw", "carbs_raw"):
                    if nutrient_col in best_row:
                        best_row[nutrient_col] = float(best_row.get(nutrient_col, 0) or 0) * serving_multiplier
                
                base_serving_grams = float(best_row.get("base_serving_grams", best_row.get("quantity_g", 100.0)) or 100.0)
                proposed_grams = serving_multiplier * base_serving_grams
                min_g, max_g = _serving_limits(best_row.get("clean_category", best_row.get("category", "")), best_row.get("name", ""))
                if min_g is not None and max_g is not None:
                    proposed_grams = float(np.clip(proposed_grams, min_g, max_g))
                    serving_multiplier = proposed_grams / base_serving_grams if base_serving_grams > 0 else serving_multiplier
                    for nutrient_col in ("calories_raw", "protein_raw", "fat_raw", "carbs_raw"):
                        per_100_col = {
                            "calories_raw": "kcal_per_100g_clean",
                            "protein_raw": "protein_per_100g_clean",
                            "fat_raw": "fat_per_100g_clean",
                            "carbs_raw": "carbs_per_100g_clean",
                        }[nutrient_col]
                        if per_100_col in best_row and not pd.isna(best_row.get(per_100_col, None)):
                            best_row[nutrient_col] = float(best_row.get(per_100_col, 0.0) or 0.0) * proposed_grams / 100.0
                best_row["serving_grams"] = round(proposed_grams, 0)
                best_row["serving_multiplier"] = serving_multiplier
                best_row["culinary_role"] = slot_name
                
                selected_rows.append(best_row)
                current_day_protein += float(best_row.get("protein_raw", 0.0) or 0.0)
                seen_food_ids.add(best_row["food_id"])
                seen_food_names.add(_row_name_key(best_row))
                semantic_key = _row_semantic_key(best_row)
                if semantic_key:
                    selected_semantic_keys.add(semantic_key)
                family = HealthyWeightGainRecommender._food_family(best_row)
                if family:
                    family_counts[family] = family_counts.get(family, 0) + 1
                clean_category = str(best_row.get("clean_category", ""))
                canonical_clean_category = _canonical_food_category(clean_category, best_row.get("name", ""))
                if canonical_clean_category in STARCH_CATEGORIES:
                    starch_group_counts[canonical_clean_category] = starch_group_counts.get(canonical_clean_category, 0) + 1
                if canonical_clean_category == "dairy":
                    dairy_count += 1
                if canonical_clean_category == "plant_protein":
                    bean_count += 1
                if canonical_clean_category in {"dairy", "plant_protein"} or family in {"milk", "yogurt", "cheese", "bean", "tofu", "soy"}:
                    dairy_soy_count += 1
                if _row_is_animal_protein(best_row):
                    animal_protein_count += 1
                if _row_is_dessert(best_row):
                    dessert_count += 1
            
            # --- Fallback & Energy/Healthy Fat Filler for exact slot counts ---
            disliked_foods = _expand_food_terms(target.get("disliked_foods", []))
            
            # Helper to check if a row has energy/fat features
            def _is_fat_or_healthy_gain_food(r) -> bool:
                r_name = _normalize_search_text(str(r.get("name", ""))).lower()
                r_cat = _row_clean_category(r)
                r_group = _normalize_search_text(str(r.get("food_group", ""))).lower()
                r_text = f" {r_cat} {r_group} {r_name} "
                
                # Check categories
                if r_cat in {
                    "dairy", "healthy_fat_nuts", "egg", "plant_protein"
                }:
                    return True
                
                # Check keywords
                keywords = [
                    "bo", "butter", "peanut", "dau phong", "avocado", "nuts", "hat",
                    "hanh nhan", "almond", "cashew", "hat dieu", "oc cho", "walnut",
                    "milk", "sua", "yogurt", "sua chua", "cheese", "pho mai",
                    "tofu", "dau hu", "dau phu", "trung", "egg", "dua", "coconut"
                ]
                for kw in keywords:
                    if kw in r_text:
                        # Exclude beef/meat containing "bo"
                        if kw == "bo" and ("thit bo" in r_text or "beef" in r_text or "t-bone" in r_text):
                            continue
                        return True
                return False
                
            meal_has_energy = any(_is_fat_or_healthy_gain_food(row) for row in selected_rows)
            def _blocked_by_animal_policy(row: pd.Series | dict) -> bool:
                return _row_is_animal_protein(row) and (
                    animal_protein_count >= max_animal_protein_count
                    or any(_row_is_animal_protein(selected) for selected in selected_rows)
                    or (meal == "breakfast" and _row_is_heavy_breakfast_protein(row))
                )
            
            # Build list of fallback candidate items
            fallback_candidates = []
            fallback_groups = [
                # Group 1: Trứng (egg)
                ["trung", "egg"],
                # Group 2: Sữa nguyên kem (whole milk), Sữa chua nguyên kem (whole yogurt)
                ["sua nguyen kem", "whole milk", "sua tuoi nguyen kem", "sua chua nguyen kem", "whole yogurt"],
                # Group 3: Bơ (butter / avocado)
                ["bo ", "bo_", "butter", "bo dau phong", "peanut butter", "avocado", "qua bo"],
                # Group 4: Hạt (nuts)
                ["hat", "nuts", "hanh nhan", "almond", "cashew", "hat dieu", "peanut", "dau phong", "oc cho", "walnut"],
                # Group 5: Đậu hũ (tofu)
                ["dau hu", "dau phu", "tofu"],
                # Group 6: Cá béo (fatty fish)
                ["ca beo", "fatty fish", "salmon", "ca hoi", "ca thu", "tuna", "ca ngu", "ca trich", "mackerel"]
            ]
            
            for _, r_row in ranked.iterrows():
                row_name = _normalize_search_text(str(r_row.get("name", ""))).lower()
                row_cat = _row_clean_category(r_row)
                row_text = f" {row_name} {row_cat} "

                if row_cat in {"dessert_sweets", "drink_natural"} or _row_is_dessert(r_row):
                    continue
                if _blocked_by_animal_policy(r_row):
                    continue
                
                # Filter out disliked / chicken
                if disliked_foods:
                    if _row_matches_terms(r_row, disliked_foods):
                        continue
                        
                matched_g_idx = -1
                for g_idx, keywords in enumerate(fallback_groups):
                    if any(kw in row_text for kw in keywords):
                        matched_g_idx = g_idx
                        break
                if matched_g_idx != -1:
                    fallback_candidates.append((matched_g_idx, r_row))
                    
            fallback_candidates.sort(key=lambda x: (x[0], -float(x[1].get("score", 0.0))))
            fallback_rows = [item[1] for item in fallback_candidates]
            
            # If the meal has exactly requested_slots items but requested_slots >= 4 and has NO energy items,
            # we replace the 4th item (index 3) with a fallback energy food
            if requested_slots >= 4 and len(selected_rows) == requested_slots and not meal_has_energy:
                replaced = False
                for f_row in fallback_rows:
                    if _is_fat_or_healthy_gain_food(f_row):
                        selected_ids = {r.get("food_id") for r in selected_rows}
                        if f_row.get("food_id") not in selected_ids:
                            # Scale the fallback row to match slot target
                            scaled_row = f_row.copy()
                            slot_target_kcal = meal_target_kcal / requested_slots
                            base_calories = max(float(scaled_row.get("calories_raw", scaled_row.get("calories", 1.0)) or 1.0), 1.0)
                            serving_multiplier = float(np.clip(slot_target_kcal / base_calories, 0.15, 3.5))
                            
                            for col in ("calories_raw", "protein_raw", "fat_raw", "carbs_raw", "calories", "protein", "fat", "carbs"):
                                if col in scaled_row:
                                    scaled_row[col] = float(scaled_row.get(col, 0) or 0) * serving_multiplier
                                    
                            base_sg = float(scaled_row.get("base_serving_grams", scaled_row.get("quantity_g", scaled_row.get("serving_grams", 100.0))) or 100.0)
                            prop_g = serving_multiplier * base_sg
                            min_g, max_g = _serving_limits(scaled_row.get("clean_category", scaled_row.get("category", "")), scaled_row.get("name", ""))
                            if min_g is not None and max_g is not None:
                                prop_g = float(np.clip(prop_g, min_g, max_g))
                                serving_multiplier = prop_g / base_sg if base_sg > 0 else serving_multiplier
                                for col in ("calories_raw", "protein_raw", "fat_raw", "carbs_raw", "calories", "protein", "fat", "carbs"):
                                    p100 = {
                                        "calories_raw": "kcal_per_100g_clean", "calories": "kcal_per_100g_clean",
                                        "protein_raw": "protein_per_100g_clean", "protein": "protein_per_100g_clean",
                                        "fat_raw": "fat_per_100g_clean", "fat": "fat_per_100g_clean",
                                        "carbs_raw": "carbs_per_100g_clean", "carbs": "carbs_per_100g_clean",
                                    }.get(col)
                                    if p100 in scaled_row and not pd.isna(scaled_row.get(p100, None)):
                                        scaled_row[col] = float(scaled_row.get(p100, 0.0) or 0.0) * prop_g / 100.0
                            scaled_row["serving_grams"] = round(prop_g, 0)
                            scaled_row["serving_multiplier"] = serving_multiplier
                            scaled_row["culinary_role"] = "extra"
                            
                            # Replace the 4th item (index 3)
                            old_row = selected_rows[3]
                            old_was_animal = _row_is_animal_protein(old_row)
                            new_is_animal = _row_is_animal_protein(scaled_row)
                            seen_food_ids.discard(old_row.get("food_id"))
                            seen_food_names.discard(_row_name_key(old_row))
                            old_semantic_key = _row_semantic_key(old_row)
                            if old_semantic_key:
                                selected_semantic_keys.discard(old_semantic_key)
                            
                            selected_rows[3] = scaled_row
                            seen_food_ids.add(scaled_row["food_id"])
                            seen_food_names.add(_row_name_key(scaled_row))
                            new_semantic_key = _row_semantic_key(scaled_row)
                            if new_semantic_key:
                                selected_semantic_keys.add(new_semantic_key)
                            if old_was_animal:
                                animal_protein_count = max(0, animal_protein_count - 1)
                            if new_is_animal:
                                animal_protein_count += 1
                            replaced = True
                            meal_has_energy = True
                            break
                if not replaced:
                    for _, r_row in ranked.iterrows():
                        if _is_fat_or_healthy_gain_food(r_row):
                            selected_ids = {r.get("food_id") for r in selected_rows}
                            if r_row.get("food_id") not in selected_ids and _row_name_key(r_row) not in seen_food_names:
                                if disliked_foods and _row_matches_terms(r_row, disliked_foods):
                                    continue
                                if _row_clean_category(r_row) in {"dessert_sweets", "drink_natural"} or _row_is_dessert(r_row):
                                    continue
                                if _blocked_by_animal_policy(r_row):
                                    continue
                                # Scale the row
                                scaled_row = r_row.copy()
                                slot_target_kcal = meal_target_kcal / requested_slots
                                base_calories = max(float(scaled_row.get("calories_raw", scaled_row.get("calories", 1.0)) or 1.0), 1.0)
                                serving_multiplier = float(np.clip(slot_target_kcal / base_calories, 0.15, 3.5))
                                
                                for col in ("calories_raw", "protein_raw", "fat_raw", "carbs_raw", "calories", "protein", "fat", "carbs"):
                                    if col in scaled_row:
                                        scaled_row[col] = float(scaled_row.get(col, 0) or 0) * serving_multiplier
                                        
                                base_sg = float(scaled_row.get("base_serving_grams", scaled_row.get("quantity_g", scaled_row.get("serving_grams", 100.0))) or 100.0)
                                prop_g = serving_multiplier * base_sg
                                min_g, max_g = _serving_limits(scaled_row.get("clean_category", scaled_row.get("category", "")), scaled_row.get("name", ""))
                                if min_g is not None and max_g is not None:
                                    prop_g = float(np.clip(prop_g, min_g, max_g))
                                    serving_multiplier = prop_g / base_sg if base_sg > 0 else serving_multiplier
                                    for col in ("calories_raw", "protein_raw", "fat_raw", "carbs_raw", "calories", "protein", "fat", "carbs"):
                                        p100 = {
                                            "calories_raw": "kcal_per_100g_clean", "calories": "kcal_per_100g_clean",
                                            "protein_raw": "protein_per_100g_clean", "protein": "protein_per_100g_clean",
                                            "fat_raw": "fat_per_100g_clean", "fat": "fat_per_100g_clean",
                                            "carbs_raw": "carbs_per_100g_clean", "carbs": "carbs_per_100g_clean",
                                        }.get(col)
                                        if p100 in scaled_row and not pd.isna(scaled_row.get(p100, None)):
                                            scaled_row[col] = float(scaled_row.get(p100, 0.0) or 0.0) * prop_g / 100.0
                                scaled_row["serving_grams"] = round(prop_g, 0)
                                scaled_row["serving_multiplier"] = serving_multiplier
                                scaled_row["culinary_role"] = "extra"
                                
                                # Replace the 4th item (index 3)
                                old_row = selected_rows[3]
                                old_was_animal = _row_is_animal_protein(old_row)
                                new_is_animal = _row_is_animal_protein(scaled_row)
                                seen_food_ids.discard(old_row.get("food_id"))
                                seen_food_names.discard(_row_name_key(old_row))
                                old_semantic_key = _row_semantic_key(old_row)
                                if old_semantic_key:
                                    selected_semantic_keys.discard(old_semantic_key)
                                
                                selected_rows[3] = scaled_row
                                seen_food_ids.add(scaled_row["food_id"])
                                seen_food_names.add(_row_name_key(scaled_row))
                                new_semantic_key = _row_semantic_key(scaled_row)
                                if new_semantic_key:
                                    selected_semantic_keys.add(new_semantic_key)
                                if old_was_animal:
                                    animal_protein_count = max(0, animal_protein_count - 1)
                                if new_is_animal:
                                    animal_protein_count += 1
                                replaced = True
                                meal_has_energy = True
                                break
                            
            # Fill missing items until we reach requested_slots
            attempts_fill = 0
            while len(selected_rows) < requested_slots and attempts_fill < 10:
                attempts_fill += 1
                selected_ids = {r.get("food_id") for r in selected_rows}
                selected_names = {_row_name_key(r) for r in selected_rows}
                selected_semantic_keys_current = {
                    key
                    for key in (_row_semantic_key(r) for r in selected_rows)
                    if key
                }

                def _would_duplicate_semantic(row: pd.Series | dict) -> bool:
                    semantic_key = _row_semantic_key(row)
                    return bool(semantic_key and semantic_key in selected_semantic_keys_current)
                
                found_fb = None
                # First try fallback rows prioritizing energy foods if requested_slots >= 4 and not meal_has_energy
                for f_row in fallback_rows:
                    if f_row.get("food_id") not in selected_ids and _row_name_key(f_row) not in selected_names:
                        if _would_duplicate_semantic(f_row):
                            continue
                        if requested_slots >= 4 and not meal_has_energy:
                            if _is_fat_or_healthy_gain_food(f_row):
                                found_fb = f_row
                                break
                        else:
                            found_fb = f_row
                            break
                
                # If not found but we specifically need an energy food, look for one in fallback_rows regardless of target
                if found_fb is None and requested_slots >= 4 and not meal_has_energy:
                    for f_row in fallback_rows:
                        if f_row.get("food_id") not in selected_ids and _row_name_key(f_row) not in selected_names:
                            if _would_duplicate_semantic(f_row):
                                continue
                            found_fb = f_row
                            break
                            
                # If not found, try any other row in ranked prioritizing energy food if needed
                if found_fb is None:
                    for _, r_row in ranked.iterrows():
                        if r_row.get("food_id") not in selected_ids and _row_name_key(r_row) not in selected_names:
                            if _would_duplicate_semantic(r_row):
                                continue
                            if disliked_foods and _row_matches_terms(r_row, disliked_foods):
                                continue
                            if _row_clean_category(r_row) in {"dessert_sweets", "drink_natural"} or _row_is_dessert(r_row):
                                continue
                            if _blocked_by_animal_policy(r_row):
                                continue
                            if requested_slots >= 4 and not meal_has_energy:
                                if _is_fat_or_healthy_gain_food(r_row):
                                    found_fb = r_row
                                    break
                            else:
                                found_fb = r_row
                                break
                                
                # Fallback to any food in ranked if we couldn't find an energy one
                if found_fb is None and requested_slots >= 4 and not meal_has_energy:
                    for _, r_row in ranked.iterrows():
                        if r_row.get("food_id") not in selected_ids and _row_name_key(r_row) not in selected_names:
                            if disliked_foods and _row_matches_terms(r_row, disliked_foods):
                                continue
                            if _row_clean_category(r_row) in {"dessert_sweets", "drink_natural"} or _row_is_dessert(r_row):
                                continue
                            if _blocked_by_animal_policy(r_row):
                                continue
                            found_fb = r_row
                            break
                            
                if found_fb is not None:
                    scaled_row = found_fb.copy()
                    slot_target_kcal = meal_target_kcal / requested_slots
                    base_calories = max(float(scaled_row.get("calories_raw", scaled_row.get("calories", 1.0)) or 1.0), 1.0)
                    serving_multiplier = float(np.clip(slot_target_kcal / base_calories, 0.15, 3.5))
                    
                    for col in ("calories_raw", "protein_raw", "fat_raw", "carbs_raw", "calories", "protein", "fat", "carbs"):
                        if col in scaled_row:
                            scaled_row[col] = float(scaled_row.get(col, 0) or 0) * serving_multiplier
                            
                    base_sg = float(scaled_row.get("base_serving_grams", scaled_row.get("quantity_g", scaled_row.get("serving_grams", 100.0))) or 100.0)
                    prop_g = serving_multiplier * base_sg
                    min_g, max_g = _serving_limits(scaled_row.get("clean_category", scaled_row.get("category", "")), scaled_row.get("name", ""))
                    if min_g is not None and max_g is not None:
                        prop_g = float(np.clip(prop_g, min_g, max_g))
                        serving_multiplier = prop_g / base_sg if base_sg > 0 else serving_multiplier
                        for col in ("calories_raw", "protein_raw", "fat_raw", "carbs_raw", "calories", "protein", "fat", "carbs"):
                            p100 = {
                                "calories_raw": "kcal_per_100g_clean", "calories": "kcal_per_100g_clean",
                                "protein_raw": "protein_per_100g_clean", "protein": "protein_per_100g_clean",
                                "fat_raw": "fat_per_100g_clean", "fat": "fat_per_100g_clean",
                                "carbs_raw": "carbs_per_100g_clean", "carbs": "carbs_per_100g_clean",
                            }.get(col)
                            if p100 in scaled_row and not pd.isna(scaled_row.get(p100, None)):
                                scaled_row[col] = float(scaled_row.get(p100, 0.0) or 0.0) * prop_g / 100.0
                    scaled_row["serving_grams"] = round(prop_g, 0)
                    scaled_row["serving_multiplier"] = serving_multiplier
                    scaled_row["culinary_role"] = "extra"
                    
                    selected_rows.append(scaled_row)
                    seen_food_ids.add(scaled_row["food_id"])
                    seen_food_names.add(_row_name_key(scaled_row))
                    semantic_key = _row_semantic_key(scaled_row)
                    if semantic_key:
                        selected_semantic_keys.add(semantic_key)
                    if _row_is_animal_protein(scaled_row):
                        animal_protein_count += 1
                    if _is_fat_or_healthy_gain_food(scaled_row):
                        meal_has_energy = True
                else:
                    break
            
            # Strictly validate length
            if len(selected_rows) < requested_slots:
                logger.warning(
                    "[MEAL ITEM COUNT CHECK] user_id=%s meal_type=%s expected_items=%s actual_items=%s missing_count=%s reason=%s available_candidates_after_hard_filter=%s",
                    target.get("user_id"),
                    meal,
                    requested_slots,
                    len(selected_rows),
                    requested_slots - len(selected_rows),
                    "initial_slot_selection_incomplete",
                    len(ranked),
                )
            # ------------------------------------------------------------------

            if selected_rows:
                plan[meal] = pd.DataFrame(selected_rows)
            else:
                plan[meal] = ranked.iloc[0:0].copy()
                
        return plan

    @staticmethod
    @lru_cache(maxsize=4096)
    def _translate_food_name_vi(name: str) -> str:
        text = str(name).strip()
        normalized = _normalize_search_text(text)
        compact = normalized.replace(",", "").replace("(", "").replace(")", "")
        compact = " ".join(compact.split())
        if compact == "bo trai cay":
            return "Quả bơ"
        if compact == "mi trung chin":
            return "Mì trứng chín"
        return text

    @staticmethod
    def _complete_food_name_vi(name: str, category: str = "") -> str:
        text = HealthyWeightGainRecommender.clean_food_name(name)
        lower = text.lower()
        category_key = str(category or "").strip().lower()

        if lower in {"cá", "ca"}:
            return "Cá hấp gừng"
        if lower in {"khoai tây", "khoai tay"}:
            return "Khoai tây nghiền"
        if lower in {"đậu nành", "dau nanh"}:
            return "Đậu nành luộc"
        if lower in {"đậu phộng", "dau phong"}:
            return "Đậu phộng rang"
        if lower in {"cám gạo thô", "cam gao tho"}:
            return "Cháo yến mạch cám gạo"
        if "rice bran" in lower or "bran, rice" in lower:
            return "Cháo yến mạch cám gạo"
        if "peanut butter" in lower:
            return "Bơ đậu phộng phết bánh mì"
        if "peanut" in lower:
            return "Đậu phộng rang"
        if "soybean" in lower or "soybeans" in lower:
            return "Đậu nành luộc"
        if "tofu" in lower:
            return "Đậu phụ sốt cà chua"
        if "potato" in lower:
            return "Khoai tây nghiền"
        if "sweet potato" in lower:
            return "Khoai lang nướng"
        if "salmon" in lower:
            return "Cá hồi áp chảo"
        if "tuna" in lower:
            return "Cá ngừ áp chảo"
        if "fish" in lower:
            return "Cá hấp gừng"
        if "chicken" in lower:
            return "Ức gà áp chảo"
        if "beef" in lower:
            return "Bò xào rau củ"
        if "pork" in lower:
            return "Thịt heo nạc áp chảo"
        if "egg" in lower:
            return "Trứng luộc"
        if "oat" in lower:
            return "Cháo yến mạch"
        if "rice" in lower:
            return "Cơm trắng"
        if "bread" in lower:
            return "Bánh mì nguyên cám"
        if "banana" in lower:
            return "Chuối chín"
        if "apple" in lower and "pie" not in lower:
            return "Táo cắt lát"
        if "yogurt" in lower:
            return "Sữa chua"
        if "milk" in lower:
            return "Sữa tươi"
        if category_key == "vegetable":
            return f"{text} luộc" if text else "Rau củ luộc"

        return text

    @staticmethod
    def _portion_display(row, display_name: str) -> str:
        """Return a human-friendly Vietnamese serving description."""
        grams = row.get("serving_grams")
        grams_value = None if pd.isna(grams) else float(grams)
        rounded_grams = int(round(grams_value)) if grams_value else 0
        lower = f"{display_name} {row.get('name', '')}".lower()
        clean_cat = str(row.get("clean_category", "") or "").strip().lower()
        category = str(row.get("category", "")).strip().lower()

        if rounded_grams <= 0:
            return "Không đủ dữ liệu khẩu phần"

        # ── Condiment / Sauce ───────────────────────────────────────────────
        if clean_cat in {"condiment", "sauce"} or category == "seasoning":
            return "Không dùng làm món chính"

        # ── Grain/Cereal/Oats MUST be matched FIRST before any protein check ─
        # This prevents oats/ngũ cốc from falling into protein_meat fallback.
        if any(t in lower for t in ("oat", "yến mạch", "ngũ cốc", "cereal", "porridge", "cháo", "granola")):
            return f"1 chén/bát vừa (~{rounded_grams}g)"

        # ── Special overrides (Margarine / Pasta) ─────────────────────────
        if any(t in lower for t in ("margarine", "bơ thực vật", "butter", "bơ lạt")):
            return f"1 muỗng/phần nhỏ (~{rounded_grams}g)"
        if any(t in lower for t in ("mì ống", "pasta", "macaroni", "spaghetti", "noodle", "mì", "mi ong", "mi mix")):
            return f"1 phần vừa (~{rounded_grams}g)"
        if any(t in lower for t in ("peanut butter", "bơ đậu phộng")):
            spoons = max(1, round(rounded_grams / 16))
            return f"{spoons} muỗng canh (~{rounded_grams}g)"
        if any(t in lower for t in ("peanut", "almond", "walnut", "hạnh nhân", "đậu phộng", "hạt điều")):
            return f"1 phần nhỏ (~{rounded_grams}g)"

        # ── clean_category — precise mapping ───────────────────────────────
        if clean_cat == "starch_grain":
            return f"1 phần ngũ cốc/chén vừa (~{rounded_grams}g)"
        if clean_cat == "starch_tuber":
            return f"1 củ/phần vừa (~{rounded_grams}g)"
        if clean_cat == "protein_meat":
            return f"1 phần thịt vừa (~{rounded_grams}g)"
        if clean_cat == "protein_seafood":
            return f"1 miếng cá/tôm vừa (~{rounded_grams}g)"
        if clean_cat == "protein_plant":
            return f"1 phần đạm thực vật (~{rounded_grams}g)"
        if clean_cat == "egg":
            pieces = max(1, round(rounded_grams / 60))
            return f"{pieces} quả trứng (~{rounded_grams}g)"
        if clean_cat == "dairy":
            return f"1 ly/hộp (~{rounded_grams}g)"
        if clean_cat in {"vegetable", "vegetable_herb"}:
            return f"1 bát rau (~{rounded_grams}g)"
        if clean_cat == "fruit":
            return f"1 phần trái cây (~{rounded_grams}g)"
        if clean_cat in {"healthy_fat", "healthy_fat_nuts", "fats_good"}:
            return f"1 phần nhỏ (~{rounded_grams}g)"
        if clean_cat in {"fat_spread", "butter", "margarine"}:
            return f"1 muỗng/phần nhỏ (~{rounded_grams}g)"
        if clean_cat in {"mixed_dish", "pasta"}:
            return f"1 phần vừa (~{rounded_grams}g)"
        if clean_cat in {"drink_natural", "drink", "beverage", "juice"}:
            return f"1 ly (~{rounded_grams}ml)"

        # ── Fallback by recommender category ─────────────────────────────
        if category == "grain" or any(t in lower for t in ("rice", "potato", "bread", "cơm", "khoai")):
            return f"1 chén/bát vừa (~{rounded_grams}g)"
        if category in {"meat", "plant_protein"} or any(t in lower for t in ("chicken", "beef", "pork", "fish", "tofu", "gà", "heo", "bò", "cá", "đậu phụ")):
            return f"1 phần đạm (~{rounded_grams}g)"
        if category == "egg" or any(t in lower for t in ("egg", "trứng")):
            pieces = max(1, round(rounded_grams / 60))
            return f"{pieces} quả trứng (~{rounded_grams}g)"
        if category == "dairy" or any(t in lower for t in ("milk", "yogurt", "sữa")):
            return f"1 ly/hộp (~{rounded_grams}g)"
        if category == "vegetable":
            return f"1 bát rau (~{rounded_grams}g)"
        if category == "fruit":
            return f"1 phần trái cây (~{rounded_grams}g)"
        if category == "healthy_fat":
            return f"1 phần nhỏ (~{rounded_grams}g)"
        if category == "drink_natural":
            return f"1 ly (~{rounded_grams}ml)"

        return f"1 phần vừa (~{rounded_grams}g)"

    @staticmethod
    def _image_requirement(display_name: str, category: str) -> str:
        text = display_name.lower()
        if any(term in text for term in ("cá", "gà", "bò", "heo", "trứng", "đậu phụ")):
            return "Ảnh món đã chế biến, thấy rõ thực phẩm chính, không dùng ảnh sống hoặc bao bì."
        if any(term in text for term in ("khoai", "cơm", "cháo", "bánh mì")):
            return "Ảnh món tinh bột đã chế biến trong bát/đĩa, không dùng ảnh nguyên liệu thô."
        if any(term in text for term in ("bơ đậu phộng", "đậu phộng")):
            return "Ảnh khẩu phần nhỏ, đúng bơ/đậu phộng ăn kèm, không dùng ảnh bao bì sản phẩm."
        if category == "dairy":
            return "Ảnh sữa hoặc sữa chua trong ly/hộp ăn, không dùng ảnh bao bì thương mại."
        return "Ảnh món ăn đúng tên món và đúng thực phẩm chính."

    @staticmethod
    def _translate_category_vi(category: str) -> str:
        mapping = {
            "dairy": "Sữa",
            "protein_meat": "Đạm thịt",
            "protein_seafood": "Đạm hải sản",
            "plant_protein": "Đạm thực vật",
            "egg": "Trứng",
            "starch_grain": "Tinh bột ngũ cốc",
            "starch_tuber": "Tinh bột củ",
            "fruit": "Trái cây",
            "vegetable": "Rau củ",
            "healthy_fat_nuts": "Chất béo tốt",
            "drink_natural": "Đồ uống tự nhiên",
            "dessert_sweets": "Món ngọt",
            "other": "Khác",
        }
        normalized = _canonical_food_category(category)
        return mapping.get(normalized, normalized.capitalize() if normalized else "Khác")

    @staticmethod
    def _build_food_image_url(english_name: str, food_id: str | None = None) -> str | None:
        # Do not call external image providers. Images must come from the foods table.
        return None

    @staticmethod
    def classifyMealRole(row: pd.Series | dict) -> str:
        role = str(row.get("culinary_role", "") or "").strip().lower()
        if role:
            return role
        category = _canonical_food_category(row.get("clean_category", row.get("category", "")), row.get("name", ""))
        name = str(row.get("name", "") or "")
        name_text = _normalize_search_text(name)
        if any(term in name_text for term in ("nuoc cam", "nuoc ep", "nuoc dua", "nuoc trai cay", "orange juice", "juice")):
            return "drink_or_extra"
        if category in {"starch_grain", "starch_tuber"}:
            return "staple"
        if category in {"protein_meat", "protein_seafood", "plant_protein", "egg"}:
            return "protein"
        if category == "vegetable":
            return "vegetable"
        if category == "fruit":
            return "fruit"
        if category == "drink_natural":
            return "drink_or_extra"
        if category in {"dessert_sweets", "sweet_spread"} or HealthyWeightGainRecommender._is_dirty_bulk_name(name):
            return "dessert"
        if category == "healthy_fat_nuts":
            return "fat"
        return "side"

    @staticmethod
    def _meal_role_reason(meal_role: str, category: str) -> str:
        role = str(meal_role or "").strip().lower()
        clean_category = str(category or "").strip().lower()
        if role == "staple":
            return "Cung cấp năng lượng chính, hỗ trợ tăng cân đều trong ngày."
        if role == "protein":
            return "Bổ sung protein giúp tăng cân có chất lượng và duy trì khối cơ."
        if role in {"vegetable", "fruit"} and clean_category not in {"dessert_sweets", "sweet_spread"}:
            return "Bổ sung chất xơ, vitamin và khoáng chất."
        if role in {"drink", "drink_or_extra"}:
            return "Bổ sung năng lượng/nước, không thay thế hoàn toàn trái cây tươi."
        if role == "dessert" or clean_category in {"dessert_sweets", "sweet_spread"}:
            return "Bổ sung năng lượng nhanh, nên dùng lượng vừa phải."
        return "Tăng năng lượng lành mạnh, hỗ trợ đạt mục tiêu kcal."

    @classmethod
    def _to_food_item_payload(cls, row) -> dict:
        original_name = str(row.get("name", ""))
        display_name = original_name or cls._complete_food_name_vi(original_name, str(row.get("category", "")))
        display_name = cls._translate_food_name_vi(display_name)
        image_query = str(row.get("image_query", "") or display_name).strip()
        category = str(row.get("clean_category", row["category"]))
        image_url = getFoodImageUrl(row)
        uses_real_photo = _uses_verified_real_photo(row)
        image_alt = str(row.get("image_alt_vi", "") or "").strip() or f"Ảnh món {display_name}"
        quantity_g = None if pd.isna(row.get("serving_grams", None)) else float(row.get("serving_grams"))
        if quantity_g is None:
            quantity_g = None if pd.isna(row.get("quantity_g", None)) else float(row.get("quantity_g"))

        if quantity_g and all(not pd.isna(row.get(column, None)) for column in (
            "kcal_per_100g_clean",
            "protein_per_100g_clean",
            "fat_per_100g_clean",
            "carbs_per_100g_clean",
        )):
            calories = float(row["kcal_per_100g_clean"]) * quantity_g / 100.0
            protein = float(row["protein_per_100g_clean"]) * quantity_g / 100.0
            fat = float(row["fat_per_100g_clean"]) * quantity_g / 100.0
            carbs = float(row["carbs_per_100g_clean"]) * quantity_g / 100.0
        else:
            calories = float(row["calories_raw"])
            protein = float(row["protein_raw"])
            fat = float(row["fat_raw"])
            carbs = float(row["carbs_raw"])

        serving_display = str(row.get("serving_display", "") or "").strip()
        image_requirement = str(row.get("image_requirement", "") or "").strip() or cls._image_requirement(display_name, category)
        meal_role = cls.classifyMealRole(row)
        return {
            "food_id": str(row["food_id"]),
            "original_name": original_name,
            "name": display_name,
            "food_group": HealthyWeightGainRecommender.category_label_vi(category),
            "meal_role": meal_role,
            "image_url": image_url,
            "image_alt": image_alt,
            "image_source_type": "real" if uses_real_photo else "placeholder",
            "image_verified": bool(uses_real_photo),
            "image_badge": None,
            "image_query": image_query,
            "image_requirement": image_requirement,
            "category": category,
            "normalized_category": str(row["category"]),
            "culinary_role": None if pd.isna(row.get("culinary_role", None)) else row.get("culinary_role"),
            "quantity_g": quantity_g,
            "serving_grams": quantity_g,
            "serving_display": serving_display,
            "portion_display": serving_display or cls._portion_display(row, display_name),
            "serving_multiplier": None if pd.isna(row.get("serving_multiplier", None)) else float(row.get("serving_multiplier")),
            "kcal": calories,
            "calories": calories,
            "protein": protein,
            "fat": fat,
            "carbs": carbs,
            "reason": cls._meal_role_reason(meal_role, category),
            "status": "suggested",
            "quality_flags": str(row.get("quality_flags", "") or "") or None,
            "score": float(row["score"]),
        }

    @staticmethod
    def _kcal_validation_message(total_kcal: float, target_kcal: float) -> str:
        kcal_diff = float(total_kcal) - float(target_kcal)
        kcal_diff_abs = abs(kcal_diff)
        kcal_diff_pct = (kcal_diff_abs / float(target_kcal)) * 100 if target_kcal > 0 else 100.0
        direction = "cao hơn" if kcal_diff > 0 else "thấp hơn"
        return (
            f"Thực đơn hiện tại đạt {round(total_kcal)} kcal, {direction} mục tiêu "
            f"{round(target_kcal)} kcal khoảng {round(kcal_diff_abs)} kcal, "
            f"tương đương {kcal_diff_pct:.2f}%. Vui lòng tạo lại để có thực đơn phù hợp hơn."
        )

    @staticmethod
    def validateMealPlan(meal_plan: dict, target: dict) -> dict:
        target_kcal = float(target.get("target_kcal") or target.get("calorie_target") or target.get("calories") or 0.0)
        total_kcal = float(meal_plan.get("total_kcal") or meal_plan.get("totalKcal") or 0.0)
        min_kcal = target_kcal * 0.95
        max_kcal = target_kcal * 1.05
        kcal_diff = total_kcal - target_kcal
        kcal_diff_abs = abs(kcal_diff)
        kcal_diff_pct = (kcal_diff_abs / target_kcal) * 100 if target_kcal > 0 else 100.0
        is_kcal_valid = target_kcal > 0 and min_kcal <= total_kcal <= max_kcal
        reason = None if is_kcal_valid else (
            f"Tổng kcal ({round(total_kcal)}) lệch {kcal_diff_pct:.2f}% so với target ({round(target_kcal)})"
        )
        return {
            "isValid": is_kcal_valid,
            "is_valid": is_kcal_valid,
            "reason": reason,
            "targetKcal": target_kcal,
            "totalKcal": total_kcal,
            "kcalDiff": kcal_diff,
            "kcalDiffPct": kcal_diff_pct,
            "target_kcal": target_kcal,
            "total_kcal": total_kcal,
            "kcal_diff": kcal_diff,
            "kcal_diff_pct": kcal_diff_pct,
        }

    @classmethod
    def _validate_generated_plan(
        cls,
        *,
        total_kcal: float,
        total_protein: float,
        total_fat: float,
        total_carbs: float,
        target: dict,
        errors: list[str] | None = None,
        warnings: list[str] | None = None,
        infos: list[str] | None = None,
    ) -> dict:
        target_kcal = float(target.get("calorie_target") or target.get("calories") or 0.0)
        kcal_diff = total_kcal - target_kcal
        kcal_diff_pct = (abs(kcal_diff) / target_kcal) * 100 if target_kcal > 0 else 100.0
        
        target_protein = float(target.get("protein_g") or target.get("protein") or 0.0)
        protein_pct = (total_protein / target_protein) * 100 if target_protein > 0 else 100.0
        
        target_fat = float(target.get("fat_g") or target.get("fat") or 0.0)
        fat_pct = (total_fat / target_fat) * 100 if target_fat > 0 else 100.0
        
        target_carbs = float(target.get("carbs_g") or target.get("carbs") or 0.0)
        carbs_pct = (total_carbs / target_carbs) * 100 if target_carbs > 0 else 100.0

        next_errors = list(errors or [])
        next_warnings = list(warnings or [])
        next_infos = list(infos or [])

        protein_over_major = target_protein > 0 and total_protein > target_protein * 1.15
        protein_over_minor = target_protein > 0 and total_protein > target_protein * 1.10

        status = "valid"
        if total_kcal <= 0:
            status = "invalid"
            next_errors.append("Không có dữ liệu thực đơn.")
        elif kcal_diff_pct > 10 or protein_over_major or fat_pct < 70 or carbs_pct > 130 or fat_pct > 150 or carbs_pct < 70:
            status = "major_adjustment"
        elif kcal_diff_pct > 5 or protein_over_minor or protein_pct < 90 or fat_pct < 80 or fat_pct > 135 or carbs_pct < 80 or carbs_pct > 115:
            status = "minor_adjustment"
        if next_errors and status == "valid":
            status = "major_adjustment"

        if protein_over_major:
            _append_unique_message(next_warnings, _protein_excess_warning(total_protein, target_protein))

        if status in ("minor_adjustment", "major_adjustment"):
            if protein_pct > 115:
                _append_unique_message(next_warnings, _protein_excess_warning(total_protein, target_protein))
            elif protein_pct > 110:
                next_warnings.append(f"Protein đang cao hơn mục tiêu {round(total_protein - target_protein)}g. Bạn có thể giảm bớt món đạm hoặc đổi sang món giàu tinh bột/chất béo tốt.")
            elif protein_pct < 90:
                next_warnings.append("Bữa này còn thiếu đạm. Có thể thêm trứng, cá, thịt nạc, đậu hũ hoặc sữa chua Hy Lạp.")
            if fat_pct < 80:
                next_warnings.append("Bữa này còn thiếu chất béo tốt. Có thể thêm bơ, hạt, trứng, cá béo hoặc sữa nguyên kem.")
            elif fat_pct > 135:
                next_warnings.append(f"Fat cao hơn mục tiêu {round(total_fat - target_fat)}g.")
            if carbs_pct < 80:
                next_warnings.append(f"Carbs thấp hơn mục tiêu {round(target_carbs - total_carbs)}g.")
            elif carbs_pct > 115:
                next_warnings.append("Bữa này hơi nhiều tinh bột. Có thể giảm một phần tinh bột hoặc đổi sang bơ, hạt, trứng hay sữa nguyên kem.")
            if kcal_diff_pct > 5:
                next_warnings.append(f"Tổng kcal lệch {kcal_diff_pct:.1f}% so với mục tiêu.")

        if status == "major_adjustment" and not next_errors:
            next_errors = next_warnings.copy()

        is_valid = status == "valid"
        
        return {
            "status": status,
            "is_valid": is_valid,
            "isValid": is_valid,
            "reason": next_errors[0] if next_errors else (next_warnings[0] if next_warnings else None),
            "warnings": next_warnings,
            "infos": next_infos,
            "errors": next_errors,
            "targetKcal": target_kcal,
            "totalKcal": total_kcal,
            "kcalDiff": kcal_diff,
            "kcalDiffPct": kcal_diff_pct,
            "target_kcal": target_kcal,
            "total_kcal": total_kcal,
            "kcal_diff": kcal_diff,
            "kcal_diff_pct": kcal_diff_pct,
        }

    @classmethod
    def _plan_totals_from_frames(cls, plan: dict[str, pd.DataFrame]) -> dict[str, float]:
        totals = {"kcal": 0.0, "protein": 0.0, "fat": 0.0, "carbs": 0.0}
        for meal_df in plan.values():
            for _, row in meal_df.iterrows():
                item = cls._to_food_item_payload(row)
                totals["kcal"] += float(item.get("calories", 0.0) or 0.0)
                totals["protein"] += float(item.get("protein", 0.0) or 0.0)
                totals["fat"] += float(item.get("fat", 0.0) or 0.0)
                totals["carbs"] += float(item.get("carbs", 0.0) or 0.0)
        return totals

    @staticmethod
    def _category_role_vi(category: str) -> str:
        normalized = _canonical_food_category(category)
        if normalized in {"starch_grain", "starch_tuber"}:
            return "grain"
        if normalized in {"protein_meat", "protein_seafood", "plant_protein", "egg"}:
            return "protein"
        if normalized == "healthy_fat_nuts":
            return "fat"
        if normalized == "vegetable":
            return "vegetable"
        if normalized == "drink_natural":
            return "side"
        if normalized == "fruit":
            return "fruit"
        if normalized in {"dairy", "drink_natural"}:
            return "side"
        return "side"

    @classmethod
    def _audit_generated_menu(cls, meal_plan_payload: dict[str, list[dict]], eligibility_check: dict) -> dict:
        issues: list[dict] = []
        fixed_menu: list[dict] = []
        total_calories = 0.0
        meal_calories: dict[str, float] = {}

        for meal, items in meal_plan_payload.items():
            roles = {cls._category_role_vi(item.get("category")) for item in items}
            meal_total = sum(float(item.get("calories") or 0.0) for item in items)
            meal_calories[meal] = meal_total
            total_calories += meal_total

            if items and "grain" not in roles:
                issues.append({
                    "meal": meal,
                    "item_name": "",
                    "issue_type": "poor_meal_balance",
                    "severity": "medium",
                    "evidence": "Bữa ăn chưa có món tinh bột rõ ràng.",
                    "reason": "Người thiếu cân cần nguồn carb ổn định để tăng năng lượng lành mạnh.",
                    "suggested_fix": "Bổ sung cơm, cháo yến mạch, khoai hoặc bánh mì nguyên cám.",
                })
            if items and "protein" not in roles:
                issues.append({
                    "meal": meal,
                    "item_name": "",
                    "issue_type": "poor_meal_balance",
                    "severity": "medium",
                    "evidence": "Bữa ăn chưa có món đạm rõ ràng.",
                    "reason": "Thiếu đạm làm thực đơn tăng cân dễ lệch sang tăng mỡ thay vì tăng cân lành mạnh.",
                    "suggested_fix": "Bổ sung trứng, cá, thịt nạc, sữa chua hoặc đậu phụ.",
                })
            if meal in {"lunch", "dinner"} and items and "vegetable" not in roles:
                issues.append({
                    "meal": meal,
                    "item_name": "",
                    "issue_type": "poor_meal_balance",
                    "severity": "low",
                    "evidence": "Bữa chính chưa có rau/củ.",
                    "reason": "Thiếu rau làm bữa ăn kém cân bằng và giảm trải nghiệm ăn uống dài hạn.",
                    "suggested_fix": "Bổ sung rau luộc, rau xào ít dầu hoặc canh rau.",
                })

            fixed_menu.append({
                "meal": meal,
                "items": [
                    {
                        "old_item": item.get("original_name") if item.get("original_name") != item.get("name") else None,
                        "new_item": item.get("name"),
                        "category": item.get("category"),
                        "portion_display": item.get("portion_display") or "Không đủ dữ liệu",
                        "kcal": round(float(item.get("calories") or 0.0), 1),
                        "protein": round(float(item.get("protein") or 0.0), 1),
                        "fat": round(float(item.get("fat") or 0.0), 1),
                        "carb": round(float(item.get("carbs") or 0.0), 1),
                        "image_requirement": item.get("image_requirement") or "Ảnh món ăn đúng tên món.",
                        "reason": "Được giữ trong thực đơn sau khi kiểm tra nhóm món, dữ liệu dinh dưỡng và khẩu phần.",
                    }
                    for item in items
                ],
            })

            for item in items:
                original = str(item.get("original_name") or "")
                current = str(item.get("name") or "")
                if original and original.strip().lower() != current.strip().lower():
                    issues.append({
                        "meal": meal,
                        "item_name": current,
                        "issue_type": "invalid_name",
                        "severity": "low",
                        "evidence": f"Tên gốc trong dữ liệu: {original}",
                        "reason": "Tên gốc có thể là nguyên liệu hoặc mô tả CSDL, không đủ tự nhiên khi hiển thị thực đơn.",
                        "suggested_fix": f"Hiển thị tên món hoàn chỉnh: {current}.",
                    })

        if meal_calories:
            dinner = meal_calories.get("dinner", 0.0)
            lunch = meal_calories.get("lunch", 0.0)
            if dinner > 0 and lunch > 0 and dinner > lunch * 1.2:
                issues.append({
                    "meal": "dinner",
                    "item_name": "",
                    "issue_type": "poor_meal_balance",
                    "severity": "medium",
                    "evidence": f"Bữa tối {round(dinner)} kcal cao hơn bữa trưa {round(lunch)} kcal quá nhiều.",
                    "reason": "Tăng cân lành mạnh nên phân bổ năng lượng đều, tránh dồn quá nhiều vào bữa tối.",
                    "suggested_fix": "Chuyển một phần năng lượng sang bữa sáng hoặc bữa trưa.",
                })

        penalty = 0
        for issue in issues:
            penalty += {"low": 3, "medium": 8, "high": 18}.get(issue["severity"], 5)
        score = max(0, min(100, 100 - penalty))
        main_problems = [issue["reason"] for issue in issues[:5]]
        if not main_problems:
            main_problems = ["Không phát hiện lỗi nghiêm trọng sau khi chuẩn hóa tên món, khẩu phần và dữ liệu dinh dưỡng."]

        return {
            "eligibility_check": eligibility_check,
            "overall_assessment": {
                "score": score,
                "summary": (
                    "Thực đơn đủ điều kiện cho người thiếu cân có BMI dưới 18.5 theo mục tiêu và dữ liệu dinh dưỡng đã nhập."
                    if eligibility_check.get("eligible")
                    else "Không đủ điều kiện sinh thực đơn."
                ),
                "main_problems": main_problems,
            },
            "detected_issues": issues,
            "fixed_menu": fixed_menu,
            "validation_rules_to_add": [
                "Tính BMI từ chiều cao/cân nặng và chặn tạo thực đơn tăng cân khi BMI >= 18.5.",
                "Loại món có dữ liệu dinh dưỡng lệch nghiêm trọng so với kcal trước khi lập thực đơn.",
                "Giới hạn khẩu phần món nhiều năng lượng như bơ đậu phộng, hạt, đậu phộng.",
                "Chuẩn hóa tên nguyên liệu thành tên món ăn hoàn chỉnh trước khi hiển thị.",
                "Mỗi bữa chính phải có tinh bột, đạm và rau/củ hoặc trái cây phù hợp.",
                "Ảnh món ăn phải thể hiện món đã chế biến, không dùng ảnh sống hoặc bao bì sản phẩm.",
            ],
        }

    @staticmethod
    def _load_recent_food_ids(db: Session, days: int = 3, user_id: int | None = None) -> dict[str, float]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        cutoff_naive = cutoff.replace(tzinfo=None)
        now = datetime.now(timezone.utc)

        sql = text(
            """
            SELECT
                COALESCE(CAST(f.food_id AS CHAR), CAST(mpi.food_id AS CHAR)) AS food_key,
                mp.created_at AS created_at
            FROM meal_plan_items mpi
            INNER JOIN meals m
                ON mpi.meal_id = m.id
            INNER JOIN meal_plans mp
                ON m.meal_plan_id = mp.id
            LEFT JOIN foods f
                ON mpi.food_id = f.id
            WHERE mp.created_at >= :cutoff
              AND (:user_id IS NULL OR mp.user_id = :user_id)
            ORDER BY mp.created_at DESC
            """
        )

        rows = db.execute(
            sql,
            {
                "cutoff": cutoff_naive,
                "user_id": user_id,
            },
        ).all()

        penalties: dict[str, float] = {}

        for food_key, created_at in rows:
            if food_key is None or created_at is None:
                continue

            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)

            age_days = (now - created_at).total_seconds() / 86400.0

            if age_days < 1.0:
                penalty = 0.30
            elif age_days < 2.0:
                penalty = 0.15
            else:
                penalty = 0.08

            fid = str(food_key)

            if penalties.get(fid, 0.0) < penalty:
                penalties[fid] = penalty

        return penalties

    def generate_recommendations(
        self,
        payload: RecommendationInput,
        db: Session,
        user: User,
        eligibility_check: object = True,
        persist: bool = True,
    ) -> dict:
        if isinstance(eligibility_check, bool):
            if eligibility_check:
                elig_res = self._raise_if_not_eligible(payload)
            else:
                elig_res = {"eligible": True, "reason": "Bypassed eligibility check"}
        else:
            elig_res = eligibility_check

        if not elig_res.get("eligible", False):
            logger.info("Recommendation skipped for out-of-scope BMI: %s", elig_res)
            return self._ineligible_scope_response(elig_res)
        # 🟢 SAFE EXECUTION LAYER: wrap entire flow in try/except
        # so any unexpected crash returns a valid (fallback) response.
        try:
            return self._generate_recommendations_inner(
                payload,
                db,
                user,
                eligibility_check=elig_res,
                persist=persist,
            )
        except HTTPException:
            raise
        except ValueError as exc:
            logger.error("Recommendation engine failed: %s", exc)
            msg = str(exc)
            if any(term in msg.lower() for term in ("mismatch", "broadcast", "shape", "length", "array")):
                logger.error(traceback.format_exc())
                raise HTTPException(status_code=500, detail="Lỗi hệ thống khi tạo thực đơn (internal recommender error). Vui lòng thử lại sau.")
            # Build a structured detail payload for frontend consumption and logs
            detail: dict = {
                "message": msg,
                "user_id": getattr(user, "id", None),
                "plan_date": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "profile": {
                    "weight": getattr(payload, "weight", None),
                    "height": getattr(payload, "height", None),
                    "age": getattr(payload, "age", None),
                    "sex": getattr(payload, "sex", None),
                    "activity": getattr(payload, "activity", None),
                    "weight_gain_speed": getattr(payload, "weight_gain_speed", None),
                    "diet_type": getattr(payload, "diet_type", None),
                    "items_per_meal": getattr(payload, "items_per_meal", None) or getattr(payload, "meal_complexity", None),
                },
                "bmi": calculateBMI(getattr(payload, "weight", None), getattr(payload, "height", None)),
            }
            # Attempt to provide food counts for debugging; ignore if this fails
            try:
                recommender = self._build_recommender_from_sql(db)
                total_foods = len(recommender.raw_df) if hasattr(recommender, "raw_df") else None
                detail["food_counts"] = {"total": total_foods}
            except Exception as _:
                detail["food_counts_error"] = str(_)

            logger.error("Recommendation failure detail: %s", detail)
            raise HTTPException(status_code=422, detail=detail)
        except Exception as exc:
            logger.error("Recommendation engine crashed: %s", exc)
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail="Lỗi hệ thống khi tạo thực đơn. Vui lòng thử lại sau.")

    def regenerate_meal_plan(self, payload: MealPlanRegenerateInput, db: Session, user: User) -> dict:
        repository = RecommendationRepository(db)
        previous_id: int | None = None
        if payload.previousMealPlanId not in (None, ""):
            try:
                previous_id = int(payload.previousMealPlanId)
            except (TypeError, ValueError):
                previous_id = None

        db.expire_all()
        saved_user = UserRepository(db).get_by_id(user.id) or user
        saved_profile = (
            db.query(UserProfileEntity)
            .filter(UserProfileEntity.user_id == user.id)
            .populate_existing()
            .first()
        )
        print("[REGENERATE FRESH DB PROFILE]", {
            "current_user_id": user.id,
            "email": user.email,
            "profile_user_id": saved_profile.user_id if saved_profile else None,
            "weight_kg": saved_profile.weight_kg if saved_profile else None,
            "target_weight_kg": saved_profile.target_weight_kg if saved_profile else None,
            "height_cm": saved_profile.height_cm if saved_profile else None,
            "diet_type": saved_profile.diet_type if saved_profile else None,
            "items_per_meal": saved_profile.items_per_meal if saved_profile else None,
            "updated_at": str(saved_profile.updated_at) if saved_profile and saved_profile.updated_at else None,
        })

        def meal_complexity_from_items(items_per_meal: object) -> str | None:
            try:
                count = int(items_per_meal)
            except (TypeError, ValueError):
                return None
            if count <= 3:
                return "simple"
            if count >= 5:
                return "full"
            return "balanced"

        weight = getattr(saved_profile, "weight_kg", None) if saved_profile else payload.weight
        height = getattr(saved_profile, "height_cm", None) if saved_profile else payload.height
        age = getattr(saved_profile, "age", None) if saved_profile else payload.age
        sex = (
            (getattr(saved_profile, "sex", None) or getattr(saved_profile, "gender", None))
            if saved_profile
            else payload.sex
        )
        activity = (getattr(saved_profile, "activity_level", None) if saved_profile else payload.activity) or "moderate"
        surplus = getattr(saved_profile, "surplus_kcal", None) if saved_profile else payload.surplus_kcal
        gain_speed = (
            (getattr(saved_profile, "weight_gain_speed", None) if saved_profile else None)
            or payload.weight_gain_speed
            or payload.gain_speed
        )
        diet_type = (getattr(saved_profile, "diet_type", None) if saved_profile else None) or getattr(payload, "diet_type", None) or getattr(payload, "diet_style", None)
        diet_style = diet_type or getattr(payload, "diet_style", None) or getattr(payload, "diet_type", None) or "balanced"
        budget_level = (getattr(saved_profile, "budget_level", None) if saved_profile else None) or payload.budget_level or "standard"
        normalized_available_ingredients = normalize_ingredient_list(getattr(payload, "available_ingredients", []))
        print("[REGENERATE AVAILABLE INGREDIENTS NORMALIZED]", normalized_available_ingredients, flush=True)
        items_per_meal_val = (
            (getattr(saved_profile, "items_per_meal", None) if saved_profile else None)
            or getattr(payload, "items_per_meal", None)
            or (3 if getattr(payload, "meal_complexity", None) == "simple" else 5 if getattr(payload, "meal_complexity", None) == "full" else 4 if getattr(payload, "meal_complexity", None) == "balanced" else None)
        )
        meal_complexity = (
            payload.meal_complexity
            or meal_complexity_from_items(items_per_meal_val)
            or "balanced"
        )
        target_weight = (
            getattr(saved_profile, "target_weight_kg", None)
            if saved_profile and getattr(saved_profile, "target_weight_kg", None) is not None
            else payload.target_weight
        )
        if target_weight is not None and height is not None and float(height) > 0:
            target_bmi = float(target_weight) / ((float(height) / 100.0) ** 2)
            if target_bmi >= 23.0:
                min_normal_weight = round(18.5 * ((float(height) / 100.0) ** 2), 1)
                max_normal_weight = round(22.9 * ((float(height) / 100.0) ** 2), 1)
                raise ValueError(
                    f"Cân nặng mục tiêu vượt vùng BMI bình thường theo chuẩn Châu Á. "
                    f"Vui lòng chọn mục tiêu trong khoảng {min_normal_weight}kg–{max_normal_weight}kg."
                )

        # Determine disliked_foods, disliked_food_groups, and favorite_foods.
        # If explicitly passed in the request payload, we respect the request directly.
        # Otherwise, we pull from the saved profile.
        if saved_profile is not None:
            favorite_foods = self._parse_profile_list(getattr(saved_profile, "favorite_foods", None))
            disliked_foods = self._parse_profile_list(getattr(saved_profile, "disliked_foods", None))
            disliked_food_groups = self._parse_profile_list(getattr(saved_profile, "disliked_food_groups", None))
        else:
            favorite_foods = self._parse_profile_list(payload.favorite_foods)
            disliked_foods = self._parse_profile_list(payload.disliked_foods)
            disliked_food_groups = self._parse_profile_list(payload.disliked_food_groups)

        if weight is None or height is None:
            detail = {
                "message": "Vui lòng hoàn thiện hồ sơ trước khi tạo lại thực đơn.",
                "user_id": getattr(user, "id", None),
                "required_fields": ["weight_kg", "height_cm"],
                "provided": {
                    "weight": weight,
                    "height": height,
                    "age": age,
                    "sex": sex,
                },
            }
            logger.error("Recommendation failed (missing profile fields): %s", detail)
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)

        random_seed = payload.generation_seed or payload.random_seed or payload.randomSeed or int(datetime.now(timezone.utc).timestamp())
        request_payload = RecommendationInput(
            weight=float(weight),
            height=float(height),
            activity=activity,
            age=age,
            sex=sex,
            goal_type=payload.goal_type or "gain",
            weight_gain_speed=gain_speed,
            gain_speed=gain_speed,
            meal_complexity=meal_complexity,
            items_per_meal=items_per_meal_val,
            diet_style=diet_style,
            diet_type=diet_type,
            budget_level=budget_level,
            surplus_kcal=surplus,
            target_calories=payload.targetKcal,
            target_weight=target_weight,
            protein_target=payload.protein_target,
            fat_target=payload.fat_target,
            carb_target=payload.carb_target,
            top_n=payload.top_n,
            preferred_categories=payload.preferred_categories,
            excluded_categories=payload.excluded_categories,
            allergens=payload.allergens,
            favorite_foods=favorite_foods,
            disliked_foods=disliked_foods,
            disliked_food_groups=disliked_food_groups,
            available_ingredients=normalized_available_ingredients,
            random_seed=random_seed,
            generation_seed=random_seed,
            exclude_food_ids=[],
            exclude_meal_plan_id=previous_id,
            macro_backtracking_attempts=8,
            save_user_data=True,
        )
        eligibility_check = self._build_eligibility_check(request_payload)
        if not eligibility_check.get("eligible"):
            logger.info("Regeneration skipped for out-of-scope BMI: %s", eligibility_check)
            result = self._ineligible_scope_response(eligibility_check)
            result["profile_snapshot"] = {
                "user_id": user.id,
                "email": user.email,
                "weight_kg": weight,
                "target_weight_kg": target_weight,
                "height_cm": height,
                "diet_type": diet_type,
                "items_per_meal": items_per_meal_val,
                "available_ingredients": normalized_available_ingredients,
                "updated_at": str(saved_profile.updated_at) if saved_profile and saved_profile.updated_at else None,
            }
            return result

        exclude_food_ids: list[str] = []
        if previous_id is not None:
            repository.mark_meal_plan_status(user.id, previous_id, "needs_regeneration")
            if payload.excludePreviousItems:
                exclude_food_ids = repository.meal_plan_food_ids(user.id, previous_id)
        request_payload.exclude_food_ids = exclude_food_ids
        result = self.generate_recommendations(request_payload, db, saved_user or user)
        result["profile_snapshot"] = {
            "user_id": user.id,
            "email": user.email,
            "weight_kg": weight,
            "target_weight_kg": target_weight,
            "height_cm": height,
            "diet_type": diet_type,
            "items_per_meal": items_per_meal_val,
            "available_ingredients": normalized_available_ingredients,
            "updated_at": str(saved_profile.updated_at) if saved_profile and saved_profile.updated_at else None,
        }
        return result

    def _generate_recommendations_inner(
        self,
        payload: RecommendationInput,
        db: Session,
        user: User,
        eligibility_check: object = True,
        persist: bool = True,
    ) -> dict:
        if isinstance(eligibility_check, bool):
            if eligibility_check:
                eligibility_check = self._raise_if_not_eligible(payload)
            else:
                eligibility_check = {"eligible": True, "reason": "Bypassed eligibility check"}
        # Clear taxonomy cache to avoid stale data from previous requests
        clear_taxonomy_cache()
        recommender = self._build_recommender_from_sql(db)
        saved_profile = getattr(user, "profile", None)
        self._hydrate_payload_from_saved_profile(payload, saved_profile)
        profile_goal, profile_surplus = self._profile_goal_and_surplus(payload)
        available_ingredients = normalize_ingredient_list(getattr(payload, "available_ingredients", []))
        print("[INGREDIENT PREFERENCE ENABLED]", ENABLE_INGREDIENT_PREFERENCE, flush=True)

        # ── Debug: user profile summary ───────────────────────────────────────
        _dbmi = calculateBMI(payload.weight, payload.height)
        logger.debug(
            "[NutriGain] Profile | weight=%.1fkg height=%.1fcm age=%s sex=%s "
            "activity=%s gain_speed=%s | BMI=%.2f goal=%s surplus=%.0f | "
            "meal_complexity=%s",
            payload.weight or 0,
            payload.height or 0,
            payload.age,
            payload.sex,
            payload.activity,
            payload.weight_gain_speed or payload.gain_speed,
            _dbmi or 0,
            profile_goal,
            profile_surplus or 0,
            payload.meal_complexity,
        )
        # Determine disliked_foods, disliked_food_groups, and favorite_foods.
        # If explicitly passed in the request payload, we respect the request directly.
        # Otherwise, we pull from the saved profile.
        if "favorite_foods" in payload.model_fields_set:
            favorite_foods = self._parse_profile_list(payload.favorite_foods)
        else:
            favorite_foods = self._parse_profile_list(getattr(saved_profile, "favorite_foods", None))

        if "disliked_foods" in payload.model_fields_set:
            disliked_foods = self._parse_profile_list(payload.disliked_foods)
        else:
            disliked_foods = self._parse_profile_list(getattr(saved_profile, "disliked_foods", None))

        if "disliked_food_groups" in payload.model_fields_set:
            disliked_food_groups = self._parse_profile_list(payload.disliked_food_groups)
        else:
            disliked_food_groups = self._parse_profile_list(getattr(saved_profile, "disliked_food_groups", None))
        effective_gain_speed = payload.weight_gain_speed or payload.gain_speed
        if _is_weight_loss_goal_value(payload.goal_type):
            effective_gain_speed = "maintain"
        profile = UserProfile(
            weight_kg=payload.weight,
            height_cm=payload.height,
            activity_level=payload.activity,
            age=payload.age,
            sex=payload.sex,
            goal=profile_goal,
            surplus_kcal=profile_surplus,
            weight_gain_speed=effective_gain_speed,
            disliked_foods=tuple(disliked_foods),
            disliked_food_groups=tuple(disliked_food_groups),
            diet_type=getattr(payload, "diet_type", None) or getattr(payload, "diet_style", None) or getattr(saved_profile, "diet_type", None),
            items_per_meal=getattr(payload, "items_per_meal", None),
            user_id=getattr(user, "id", None),
        )
        print("[RECOMMENDER FINAL PROFILE USED]", {
            "user_id": user.id,
            "email": user.email,
            "weight_kg": profile.weight_kg,
            "target_weight_kg": getattr(payload, "target_weight", None),
            "height_cm": profile.height_cm,
            "age": profile.age,
            "sex": profile.sex,
            "activity_level": profile.activity_level,
            "weight_gain_speed": profile.weight_gain_speed,
            "diet_type": profile.diet_type,
            "items_per_meal": profile.items_per_meal,
            "available_ingredients": available_ingredients,
        })

        calculated_targets = calculateNutritionTargets(
            {
                "weight_kg": payload.weight,
                "height_cm": payload.height,
                "activity_level": payload.activity,
                "age": payload.age,
                "sex": payload.sex,
                "goal": profile_goal,
                "weight_gain_speed": effective_gain_speed,
                "target_weight": payload.target_weight,
            }
        )
        profile_summary = calculated_targets["profile_summary"]
        nutrition_target = calculated_targets["nutrition_target"]
        if payload.target_calories:
            nutrition_target["calorie_target"] = float(payload.target_calories)
            if payload.protein_target is not None:
                nutrition_target["protein_g"] = float(payload.protein_target)
            if payload.fat_target is not None:
                nutrition_target["fat_g"] = float(payload.fat_target)
            if payload.carb_target is not None:
                nutrition_target["carbs_g"] = float(payload.carb_target)

        gain_energy_mode = _has_weight_gain_intent(
            bmi=float(profile_summary.get("bmi") or _dbmi or 0.0),
            goal=payload.goal_type or profile_goal,
            weight_gain_speed=effective_gain_speed,
        )

        # Map to old target format for backwards compatibility with recommender (temporary)
        target = {
            "calories": nutrition_target["calorie_target"],
            "protein": nutrition_target["protein_g"],
            "fat": nutrition_target["fat_g"],
            "carbs": nutrition_target["carbs_g"],
            "bmi": profile_summary["bmi"],
            "bmi_category": profile_summary.get("bmi_category") or profile_summary.get("bmi_status"),
            "bmi_label": profile_summary.get("bmi_label") or asian_bmi_label(profile_summary.get("bmi_status")),
            "bmr": nutrition_target["bmr"],
            "tdee": nutrition_target["tdee"],
            "maintenance_kcal": nutrition_target["tdee"],
            "bmi_status": profile_summary["bmi_status"],
            "medical_warning": BMI_SEVERE_UNDERWEIGHT_WARNING if profile_summary.get("medical_warning") else None,
            "goal": payload.goal_type or profile_goal,
            "weight_gain_speed": effective_gain_speed,
            "diet_type": payload.diet_type or payload.diet_style,
            "budget_level": payload.budget_level,
            "items_per_meal": payload.items_per_meal,
            "gain_energy_mode": gain_energy_mode,
            "disliked_foods": disliked_foods,
            "available_ingredients": available_ingredients,
            "user_id": getattr(user, "id", None),
        }

        history_preferences = self._train_category_preferences_from_sql(db, user_id=user.id)
        current_preferences = dict(history_preferences)
        for category in payload.preferred_categories:
            normalized = _canonical_food_category(category)
            if normalized:
                current_preferences[normalized] = current_preferences.get(normalized, 0.0) + 1.0
        for category in payload.excluded_categories:
            normalized = _canonical_food_category(category)
            if normalized:
                current_preferences[normalized] = current_preferences.get(normalized, 0.0) - 1.0

        def _meal_structure_from_items_per_meal(items_per_meal: object) -> dict[str, int] | None:
            try:
                count = int(items_per_meal)
            except (TypeError, ValueError):
                return None
            if count <= 0:
                return None
            count = max(1, min(count, 5))
            return {"breakfast": count, "lunch": count, "dinner": count}

        meal_structure = (
            _meal_structure_from_items_per_meal(getattr(payload, "items_per_meal", None))
            or HealthyWeightGainRecommender.meal_structure_for_complexity(payload.meal_complexity)
        )
        include_snack = bool(getattr(payload, "include_snack", False))
        if not include_snack:
            meal_structure = {
                meal_type: slots
                for meal_type, slots in meal_structure.items()
                if meal_type in {"breakfast", "lunch", "dinner"}
            }
        for meal_type in ("breakfast", "lunch", "dinner"):
            meal_structure.setdefault(meal_type, 4)
        meal_slots = sum(meal_structure.values())
        # Pool must be large enough for 13 slots across 4 meals with enough diversity
        candidate_top_n = max(payload.top_n * 12, meal_slots * 30, 1600)
        print("[RECOMMENDER PROFILE SYNC CHECK]", {
            "user_id": user.id,
            "diet_type": getattr(payload, "diet_type", None) or getattr(payload, "diet_style", None),
            "items_per_meal": getattr(payload, "items_per_meal", None),
            "budget_level": getattr(payload, "budget_level", None),
        })
        ranked = recommender.recommend(
            profile=profile,
            top_n=candidate_top_n,
            preferred_categories=payload.preferred_categories,
            excluded_categories=payload.excluded_categories,
            category_preferences=current_preferences,
        )
        ranked = _attach_row_search_cache(ranked)
        ranked = self._apply_diet_and_budget_preferences(ranked, payload, target=target)
        ranked = self.filterFoodsByDietType(
            ranked,
            payload.diet_type or payload.diet_style,
            min_items=meal_slots * 3,
        )

        disliked_foods_expanded = _expand_food_terms(disliked_foods)
        if disliked_foods_expanded:
            disliked_mask = ranked.apply(
                lambda row: _row_matches_terms(row, disliked_foods_expanded),
                axis=1,
            )
            ranked = ranked[~disliked_mask].copy()

        if disliked_food_groups:
            group_terms = [_normalize_search_text(group) for group in disliked_food_groups if _normalize_search_text(group)]
            if group_terms:
                group_mask = ranked.apply(
                    lambda row: any(
                        group in _normalize_search_text(
                            f"{row.get('category', '')} {row.get('clean_category', '')} {row.get('food_group', '')}"
                        )
                        for group in group_terms
                    ),
                    axis=1,
                )
                ranked = ranked[~group_mask].copy()

        # Apply allergen name filter
        if payload.allergens:
            allergen_terms = [a.strip().lower() for a in payload.allergens if a.strip()]
            if allergen_terms:
                allergen_mask = ranked.apply(
                    lambda row: _row_matches_terms(row, allergen_terms),
                    axis=1,
                )
                ranked = ranked[~allergen_mask].copy()

        abnormal_fat_spread_mask = ranked.apply(_is_abnormal_fat_spread_row, axis=1).astype(bool)
        if abnormal_fat_spread_mask.any():
            sample_columns = [
                column
                for column in ("food_id", "name", "kcal_per_serving_clean")
                if column in ranked.columns
            ]
            logger.warning(
                "Filtered abnormal fat spread rows before meal picking: count=%s sample=%s",
                int(abnormal_fat_spread_mask.sum()),
                ranked.loc[abnormal_fat_spread_mask, sample_columns].head(5).to_dict(orient="records"),
            )
            ranked = ranked[~abnormal_fat_spread_mask].copy()

        scoring_favorite_foods, favorite_food_diet_conflicts = _split_favorite_foods_by_diet(
            favorite_foods,
            payload.diet_type or payload.diet_style,
        )
        hard_exclusion_terms_for_favorites = _expand_food_terms(disliked_foods) + _expand_food_terms(payload.allergens)
        if hard_exclusion_terms_for_favorites:
            scoring_favorite_foods = [
                favorite
                for favorite in scoring_favorite_foods
                if not _row_matches_terms(
                    {"name": favorite, "original_name": favorite, "search_keywords": favorite, "category": ""},
                    hard_exclusion_terms_for_favorites,
                )
            ]

        interaction_repository = InteractionRepository(db)
        favorite_food_ids = interaction_repository.favorite_food_ids(user.id)
        user_ratings = interaction_repository.ratings_by_user(user.id)

        # Boost favorites
        if scoring_favorite_foods:
            fav_terms = [f.strip().lower() for f in scoring_favorite_foods if f.strip()]
            if fav_terms:
                fav_boost = ranked.apply(
                    lambda row: 0.16 if _row_matches_terms(row, fav_terms) else 0.0,
                    axis=1,
                )
                ranked = ranked.copy()
                ranked["score"] = ranked["score"] + fav_boost

        healthy_favorite_adjustment = ranked.apply(
            lambda row: _healthy_favorite_score_adjustment(row, scoring_favorite_foods),
            axis=1,
        )
        if healthy_favorite_adjustment.any():
            ranked = ranked.copy()
            ranked["score"] = ranked["score"] + healthy_favorite_adjustment

        if favorite_food_ids:
            ranked = ranked.copy()
            ranked["score"] = ranked["score"] + ranked["food_id"].astype(str).map(
                lambda food_id: 0.10 if food_id in favorite_food_ids else 0.0
            )

        if user_ratings:
            ranked = ranked.copy()
            ranked["score"] = ranked["score"] + ranked["food_id"].astype(str).map(
                lambda food_id: ((user_ratings.get(food_id, 3) - 3) / 2.0) * 0.08
            )
            ranked = ranked[ranked["score"] > 0].copy()
            ranked = ranked.sort_values("score", ascending=False)

        # ── Variety penalty: reduce score for recently recommended foods ──────
        # Foods recommended yesterday lose 0.30 points; 2-3 days ago lose 0.08.
        # This ensures the engine naturally rotates the menu across days.
        recent_penalties = self._load_recent_food_ids(db, days=3, user_id=user.id)
        if recent_penalties:
            ranked = ranked.copy()
            penalty_series = ranked["food_id"].astype(str).map(
                lambda fid: recent_penalties.get(fid, 0.0)
            )
            ranked["score"] = (ranked["score"] - penalty_series).clip(lower=0.0)
            ranked = ranked.sort_values("score", ascending=False)
        # ─────────────────────────────────────────────────────────────────────

        logger.debug(
            "[NutriGain] Target | BMI=%.2f BMR=%.0f TDEE=%.0f kcal=%.0f "
            "protein=%.1fg fat=%.1fg carbs=%.1fg surplus=%.0f",
            target.get("bmi", 0),
            nutrition_target.get("bmr", 0),
            nutrition_target.get("tdee", 0),
            target.get("calories", 0),
            target.get("protein", 0),
            target.get("fat", 0),
            target.get("carbs", 0),
            nutrition_target.get("surplus", 0),
        )
        target_kcal = nutrition_target["calorie_target"]

        hard_excluded_food_ids = {str(food_id) for food_id in payload.exclude_food_ids if str(food_id).strip()}
        if hard_excluded_food_ids:
            ranked = ranked[~ranked["food_id"].astype(str).isin(hard_excluded_food_ids)].copy()

        # --- Pre-filter Outliers (Trứng Cá + Seafood Carbs > 2) ---
        outlier_mask = ranked.apply(
            lambda row: "trứng cá" in str(row.get("name", "")).lower() and str(row.get("clean_category", str(row.get("category", "")))).lower() in ["seafood", "protein_seafood", "hải sản"] and float(row.get("Carbs(g)", row.get("carbs", 0))) > 2,
            axis=1
        )
        ranked = ranked[~outlier_mask].copy()
        ranked = _limit_ranked_candidate_pool(ranked, meal_slots, payload.top_n)

        ml_metadata = ml_food_eligibility_service.get_metadata()
        ml_score_used = False
        if not ranked.empty:
            try:
                ml_scores = pd.Series(
                    [ml_food_eligibility_service.get_food_ml_score(row) for _, row in ranked.iterrows()],
                    index=ranked.index,
                )
                ml_score_mask = ml_scores.notna()
                if bool(ml_metadata.get("ml_enabled")) and ml_score_mask.any():
                    ranked = ranked.copy()
                    ranked["rule_score"] = ranked["score"].astype(float)
                    ranked["ml_score"] = ml_scores
                    ranked.loc[ml_score_mask, "score"] = (
                        ranked.loc[ml_score_mask, "rule_score"] * (1.0 - ML_SCORE_WEIGHT)
                        + ranked.loc[ml_score_mask, "ml_score"].astype(float) * ML_SCORE_WEIGHT
                    )
                    ranked = ranked.sort_values("score", ascending=False)
                    ml_score_used = True
            except Exception as exc:
                ml_metadata = ml_food_eligibility_service.get_metadata()
                ml_score_used = False
                logger.warning("Food eligibility ML scoring skipped; using rule-based ranking: %s", exc)
        ranked = self._apply_budget_score_adjustments(ranked, payload.budget_level, strength=0.45)
        ranked = self._apply_natural_food_score_adjustments(ranked, strength=0.35)

        if ENABLE_INGREDIENT_PREFERENCE and available_ingredients and not ranked.empty:
            try:
                ranked = ranked.copy()
                # Phase 4: compute match count capped at 2, apply bonus
                score_before_series = ranked["score"].astype(float).copy()
                match_counts = ranked.apply(
                    lambda row: min(ingredient_match_count(row, available_ingredients), 2),
                    axis=1,
                )
                ranked["ingredient_match_count"] = match_counts.astype(int)
                if match_counts.any():
                    ranked["score"] = ranked["score"].astype(float) + (
                        ranked["ingredient_match_count"].astype(float) * INGREDIENT_PREFERENCE_BONUS
                    )
                    ranked = ranked.sort_values("score", ascending=False)

                # Phase 2: candidate summary debug log (top 10 only, not entire DB)
                try:
                    matched_mask = ranked["ingredient_match_count"] > 0
                    matched_count = int(matched_mask.sum())
                    top_matched = []
                    for _, mrow in ranked[matched_mask].head(10).iterrows():
                        fid = str(mrow.get("food_id", ""))
                        fname = str(mrow.get("name", ""))
                        sb = round(float(score_before_series.loc[mrow.name]) if mrow.name in score_before_series.index else 0.0, 3)
                        sa = round(float(mrow.get("score", 0.0)), 3)
                        matches = ingredient_match_list(mrow, available_ingredients)
                        top_matched.append({"id": fid, "name": fname, "matches": matches, "score_before": sb, "score_after": sa})
                    print("[INGREDIENT PREFERENCE CANDIDATE SUMMARY]", {
                        "available_ingredients": list(available_ingredients),
                        "candidate_count": len(ranked),
                        "matched_candidate_count": matched_count,
                        "top_matched_candidates": top_matched,
                    }, flush=True)
                except Exception as log_exc:
                    print("[INGREDIENT PREFERENCE CANDIDATE SUMMARY FAILED]", repr(log_exc), flush=True)
            except Exception as exc:
                print("[INGREDIENT PREFERENCE FALLBACK]", repr(exc), flush=True)

        # Retry logic: try multiple seeded variants and keep the closest kcal plan.
        best_meal_plan = None
        best_delta = float("inf")
        best_totals: dict[str, float] | None = None
        max_attempts = max(1, min(int(payload.macro_backtracking_attempts or 8), 8))
        seed_base = payload.generation_seed or payload.random_seed or int(datetime.now(timezone.utc).timestamp())
        print("[RECOMMENDER GENERATION SEED]", seed_base, flush=True)

        for attempt in range(max_attempts):
            attempt_ranked = ranked.copy()
            try:
                rng = random.Random(seed_base + attempt)
                # Phase 6: wider top_pool for real diversity
                top_pool_size = min(len(attempt_ranked), max(meal_slots * 5, 12))
                if top_pool_size > 0:
                    top_index = attempt_ranked.head(top_pool_size).index
                    attempt_ranked.loc[top_index, "_seed_jitter"] = [
                        rng.uniform(-RECOMMENDER_DIVERSITY_JITTER, RECOMMENDER_DIVERSITY_JITTER)
                        for _ in range(top_pool_size)
                    ]
                    attempt_ranked["_seed_jitter"] = attempt_ranked["_seed_jitter"].fillna(0.0)
                    attempt_ranked["score"] = attempt_ranked["score"].astype(float) + attempt_ranked["_seed_jitter"]
                    attempt_ranked = attempt_ranked.sort_values("score", ascending=False).drop(columns=["_seed_jitter"])
            except Exception as exc:
                print("[RECOMMENDER DIVERSITY FALLBACK]", repr(exc), flush=True)
                attempt_ranked = ranked.copy()

            meal_plan = self.pickBalancedMeal(attempt_ranked, meal_structure=meal_structure, target=target)
            
            plan_totals = self._plan_totals_from_frames(meal_plan)
            temp_kcal = plan_totals["kcal"]
                    
            delta_pct = abs(temp_kcal - target_kcal) / target_kcal if target_kcal > 0 else 0
            target_protein_for_attempt = max(float(target.get("protein") or 0.0), 1.0)
            target_fat_for_attempt = max(float(target.get("fat") or 0.0), 1.0)
            target_carbs_for_attempt = max(float(target.get("carbs") or 0.0), 1.0)
            protein_short = max((target_protein_for_attempt * 0.90 - plan_totals["protein"]) / target_protein_for_attempt, 0.0)
            protein_excess = max((plan_totals["protein"] - target_protein_for_attempt * 1.10) / target_protein_for_attempt, 0.0)
            fat_short = max((target_fat_for_attempt * 0.80 - plan_totals["fat"]) / target_fat_for_attempt, 0.0)
            fat_excess = max((plan_totals["fat"] - target_fat_for_attempt * 1.35) / target_fat_for_attempt, 0.0)
            carb_excess = max((plan_totals["carbs"] - target_carbs_for_attempt * 1.15) / target_carbs_for_attempt, 0.0)
            plan_quality_delta = (
                delta_pct
                + (0.45 * protein_short)
                + (0.38 * protein_excess)
                + (0.40 * fat_short)
                + (0.12 * fat_excess)
                + (0.55 * carb_excess)
            )
            
            if plan_quality_delta < best_delta:
                best_delta = plan_quality_delta
                best_meal_plan = meal_plan
                best_totals = plan_totals
                
            if delta_pct <= 0.05 and protein_short <= 0 and protein_excess <= 0 and fat_short <= 0 and carb_excess <= 0:
                break

            # If failed, penalize selected items slightly to try different combinations
            selected_ids = []
            for _mt_p, _mdf_p in meal_plan.items():
                selected_ids.extend(_mdf_p["food_id"].tolist())
            _penalty_mask = ranked["food_id"].isin(selected_ids)
            ranked.loc[_penalty_mask, "score"] -= 0.15 + (attempt * 0.01)
            ranked = ranked.sort_values("score", ascending=False)

        meal_plan = best_meal_plan
        if meal_plan is None:
            _fail_detail = {
                "message": "Không tìm được món phù hợp để tạo thực đơn. Vui lòng kiểm tra dữ liệu foods hoặc nới lỏng điều kiện lọc.",
                "user_id": getattr(user, "id", None),
                "profile": {
                    "weight": payload.weight,
                    "height": payload.height,
                    "age": payload.age,
                    "sex": payload.sex,
                    "activity": payload.activity,
                    "diet_type": payload.diet_type,
                    "items_per_meal": payload.items_per_meal or payload.meal_complexity,
                },
                "bmi": calculateBMI(payload.weight, payload.height),
                "ranked_count": len(ranked),
                "category_counts": ranked["clean_category"].value_counts().to_dict(),
                "top_items": ranked[["name", "clean_category", "score"]].head(10).to_dict(orient="records") if not ranked.empty else [],
            }
            logger.error("Meal plan generation failed: %s", _fail_detail)
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=_fail_detail)

        # Phase 5: Forced one daily match when ingredient preference active but no item matched
        if ENABLE_INGREDIENT_PREFERENCE and available_ingredients and meal_plan is not None and not ranked.empty:
            try:
                _day_has_match = False
                for _mt5, _mdf5 in meal_plan.items():
                    if not isinstance(_mdf5, pd.DataFrame) or _mdf5.empty:
                        continue
                    for _, _r5 in _mdf5.iterrows():
                        if ingredient_match_count(_r5, available_ingredients) > 0:
                            _day_has_match = True
                            break
                    if _day_has_match:
                        break
                if not _day_has_match:
                    _has_mcol = "ingredient_match_count" in ranked.columns
                    _mpool = ranked[ranked["ingredient_match_count"] > 0] if _has_mcol else ranked[
                        ranked.apply(lambda _rr: ingredient_match_count(_rr, available_ingredients), axis=1) > 0
                    ]
                    if not _mpool.empty:
                        _bmr = _mpool.iloc[0]
                        _bm_kcal = float(_bmr.get("calories_raw", _bmr.get("kcal_per_serving_clean", 0)) or 0)
                        _replaced = False
                        for _mt5, _mdf5 in meal_plan.items():
                            if not isinstance(_mdf5, pd.DataFrame) or _mdf5.empty:
                                continue
                            _existing_ids = {str(_rx.get("food_id", "")) for _, _rx in _mdf5.iterrows()}
                            if str(_bmr.get("food_id", "")) in _existing_ids:
                                _replaced = True
                                break
                            for _idx5, _ritem in _mdf5.iterrows():
                                _rkcal = float(_ritem.get("calories_raw", _ritem.get("kcal_per_serving_clean", 0)) or 0)
                                if ingredient_match_count(_ritem, available_ingredients) == 0 and abs(_bm_kcal - _rkcal) <= 200:
                                    _new_df5 = _mdf5.copy()
                                    _ms5 = pd.DataFrame([_bmr], index=[_idx5])
                                    _new_df5 = pd.concat([_new_df5.drop(index=_idx5), _ms5]).reset_index(drop=True)
                                    meal_plan[_mt5] = _new_df5
                                    print("[INGREDIENT PREFERENCE FORCED ONE DAILY MATCH]", {
                                        "replaced_name": str(_ritem.get("name", "")),
                                        "replacement_name": str(_bmr.get("name", "")),
                                        "meal_type": _mt5,
                                        "kcal_delta": round(abs(_bm_kcal - _rkcal), 1),
                                        "matched_ingredients": ingredient_match_list(_bmr, available_ingredients),
                                    }, flush=True)
                                    _replaced = True
                                    break
                            if _replaced:
                                break
                        if not _replaced:
                            print("[INGREDIENT PREFERENCE FORCE SKIPPED]", {
                                "reason": "No item within calorie delta or item already present",
                                "best_match_name": str(_bmr.get("name", "")),
                            }, flush=True)
                    else:
                        print("[INGREDIENT PREFERENCE FORCE SKIPPED]", {
                            "reason": "No matched candidates in ranked pool",
                            "available_ingredients": list(available_ingredients),
                        }, flush=True)
            except Exception as _force_exc:
                print("[INGREDIENT PREFERENCE FORCE FALLBACK]", repr(_force_exc), flush=True)



        # Build meal plan payload and calculate true totals from items
        meal_plan_payload: list[dict] = []
        meal_items_for_db: list[dict] = []
        total_kcal = 0.0
        total_protein = 0.0
        total_fat = 0.0
        total_carbs = 0.0
        
        for meal_type, meal_df in meal_plan.items():
            meal_list = []
            meal_actual_kcal = 0.0
            for _, row in meal_df.iterrows():
                item = self._to_food_item_payload(row)
                meal_list.append(item)
                meal_actual_kcal += float(item.get("calories", 0))
                total_kcal += float(item.get("calories", 0))
                total_protein += float(item.get("protein", 0))
                total_fat += float(item.get("fat", 0))
                total_carbs += float(item.get("carbs", 0))
                
                meal_items_for_db.append(
                    {
                        "meal_type": meal_type,
                        "food_id": item["food_id"],
                        "name": item["name"],
                        "category": item["category"],
                            "serving_grams": item.get("serving_grams"),
                            "serving_display": item.get("serving_display") or item.get("portion_display"),
                            "calories": item["calories"],
                            "protein": item["protein"],
                            "fat": item["fat"],
                            "carbs": item["carbs"],
                            "reason": item.get("name"),
                            "image_url": item.get("image_url"),
                            "image_badge": item.get("image_badge"),
                            "score": item["score"],
                        }
                )
            
            meal_plan_payload.append({
                "meal_type": meal_type,
                "actual_kcal": round(meal_actual_kcal),
                "items": meal_list
            })

        if available_ingredients:
            try:
                selected_food_names = [
                    str(item.get("name") or "")
                    for meal in meal_plan_payload
                    for item in meal.get("items", [])
                    if item.get("name")
                ]
                matched_food_names = [
                    str(item.get("name") or "")
                    for meal in meal_plan_payload
                    for item in meal.get("items", [])
                    if item.get("name") and ingredient_match_count(item, available_ingredients) > 0
                ]
                print("[INGREDIENT PREFERENCE SELECTED SUMMARY]", {
                    "available_ingredients": available_ingredients,
                    "selected_food_names": selected_food_names,
                    "matched_food_names": matched_food_names,
                }, flush=True)
            except Exception as exc:
                print("[INGREDIENT PREFERENCE SUMMARY FAILED]", repr(exc), flush=True)

        target_kcal = float(nutrition_target["calorie_target"])
        min_kcal = target_kcal * 0.95 if target_kcal > 0 else 0.0
        max_kcal = target_kcal * 1.05 if target_kcal > 0 else 0.0
        preserved_item_count_note = False
        target_protein = float(nutrition_target.get("protein_g") or nutrition_target.get("protein_target") or nutrition_target.get("protein") or 0.0)
        target_fat = float(nutrition_target.get("fat_g") or nutrition_target.get("fat_target") or nutrition_target.get("fat") or 0.0)
        target_carbs = float(nutrition_target.get("carbs_g") or nutrition_target.get("carb_target") or nutrition_target.get("carbs") or 0.0)
        bmi_value_for_policy = float(target.get("bmi") or _dbmi or 0.0)
        gain_energy_mode = bool(target.get("gain_energy_mode")) or _has_weight_gain_intent(
            bmi=bmi_value_for_policy,
            goal=payload.goal_type or profile_goal,
            weight_gain_speed=effective_gain_speed,
        )

        def _expected_slots_for_meal(meal_type: str) -> int:
            return max(1, int(meal_structure.get(str(meal_type).lower(), 4)))

        def _refresh_item_serving_display(item: dict) -> None:
            item["portion_display"] = self._portion_display(item, str(item.get("name", "")))
            item["serving_display"] = item["portion_display"]

        def _enforce_meal_item_limits() -> None:
            nonlocal preserved_item_count_note
            for meal in meal_plan_payload:
                items = meal.get("items", [])
                limit = _expected_slots_for_meal(meal.get("meal_type", "meal"))
                if len(items) <= limit:
                    continue

                def removal_priority(item: dict) -> tuple[int, float]:
                    role = str(item.get("meal_role") or item.get("culinary_role") or "").lower()
                    category = _canonical_food_category(item.get("category"), item.get("name"))
                    optional = role in {"extra", "fat", "side", "drink", "drink_or_extra"} or category in {"dairy", "healthy_fat_nuts", "fruit"}
                    return (0 if optional else 1, float(item.get("calories") or item.get("kcal") or 0.0))

                while len(items) > limit:
                    remove_index = min(range(len(items)), key=lambda idx: removal_priority(items[idx]))
                    items.pop(remove_index)
                    preserved_item_count_note = True

        def _recompute_plan_totals() -> tuple[list[dict], float, float, float, float]:
            _enforce_meal_item_limits()
            rebuilt_items: list[dict] = []
            recomputed_kcal = 0.0
            recomputed_protein = 0.0
            recomputed_fat = 0.0
            recomputed_carbs = 0.0
            for meal in meal_plan_payload:
                meal_type = str(meal.get("meal_type", "meal"))
                meal_kcal = 0.0
                for item in meal.get("items", []):
                    calories = float(item.get("calories") or item.get("kcal") or 0.0)
                    protein = float(item.get("protein") or 0.0)
                    fat = float(item.get("fat") or 0.0)
                    carbs = float(item.get("carbs") or 0.0)
                    item["calories"] = calories
                    item["kcal"] = calories
                    item["protein"] = protein
                    item["fat"] = fat
                    item["carbs"] = carbs
                    _refresh_item_serving_display(item)
                    meal_kcal += calories
                    recomputed_kcal += calories
                    recomputed_protein += protein
                    recomputed_fat += fat
                    recomputed_carbs += carbs
                    rebuilt_items.append(
                        {
                            "meal_type": meal_type,
                            "food_id": item.get("food_id"),
                            "name": item.get("name"),
                            "category": item.get("category"),
                            "serving_grams": item.get("serving_grams") or item.get("quantity_g"),
                            "serving_display": item.get("serving_display") or item.get("portion_display"),
                            "calories": calories,
                            "protein": protein,
                            "fat": fat,
                            "carbs": carbs,
                            "reason": item.get("name"),
                            "image_url": item.get("image_url"),
                            "image_badge": item.get("image_badge"),
                            "score": float(item.get("score") or 0.0),
                        }
                    )
                meal["actual_kcal"] = round(meal_kcal)
            return rebuilt_items, recomputed_kcal, recomputed_protein, recomputed_fat, recomputed_carbs

        def _scale_payload_items(scale: float) -> None:
            for meal in meal_plan_payload:
                for item in meal.get("items", []):
                    item_scale = scale
                    quantity_g = item.get("quantity_g") or item.get("serving_grams")
                    if quantity_g is not None:
                        old_q = float(quantity_g)
                        new_q = old_q * scale
                        min_q, max_q = _serving_limits(item.get("category", ""), item.get("name", ""))
                        if min_q is not None and max_q is not None:
                            new_q = min(max(new_q, min_q), max_q)
                        item_scale = new_q / old_q if old_q > 0 else scale

                        item["quantity_g"] = new_q
                        item["serving_grams"] = new_q
                        _refresh_item_serving_display(item)
                    item["calories"] = float(item.get("calories") or 0.0) * item_scale
                    item["kcal"] = item["calories"]
                    item["protein"] = float(item.get("protein") or 0.0) * item_scale
                    item["fat"] = float(item.get("fat") or 0.0) * item_scale
                    item["carbs"] = float(item.get("carbs") or 0.0) * item_scale

        def _scale_preferred_energy_items(scale: float) -> None:
            energy_categories = {
                "starch_grain",
                "starch_tuber",
                "healthy_fat_nuts",
                "dairy",
                "fruit",
            }
            for meal in meal_plan_payload:
                for item in meal.get("items", []):
                    category = _canonical_food_category(item.get("category"), item.get("name"))
                    if category not in energy_categories:
                        continue
                    item_scale = scale
                    quantity_g = item.get("quantity_g") or item.get("serving_grams")
                    if quantity_g is not None:
                        old_q = float(quantity_g)
                        new_q = old_q * scale
                        min_q, max_q = _serving_limits(item.get("category", ""), item.get("name", ""))
                        if min_q is not None and max_q is not None:
                            new_q = min(max(new_q, min_q), max_q)
                        item_scale = new_q / old_q if old_q > 0 else scale
                        item["quantity_g"] = new_q
                        item["serving_grams"] = new_q
                        _refresh_item_serving_display(item)
                    item["calories"] = float(item.get("calories") or 0.0) * item_scale
                    item["kcal"] = item["calories"]
                    item["protein"] = float(item.get("protein") or 0.0) * item_scale
                    item["fat"] = float(item.get("fat") or 0.0) * item_scale
                    item["carbs"] = float(item.get("carbs") or 0.0) * item_scale

        def _scale_protein_items(scale: float) -> None:
            for meal in meal_plan_payload:
                for item in meal.get("items", []):
                    cat = _canonical_food_category(item.get("category"), item.get("name"))
                    if cat not in {"protein_meat", "protein_seafood", "plant_protein", "egg"}:
                        continue
                    q = float(item.get("quantity_g") or item.get("serving_grams") or 100)
                    next_q = q * scale
                    min_q, max_q = _serving_limits(item.get("category", ""), item.get("name", ""))
                    if min_q is not None and max_q is not None:
                        next_q = min(max(next_q, min_q), max_q)
                    item_scale = next_q / q if q > 0 else scale
                    item["quantity_g"] = next_q
                    item["serving_grams"] = next_q
                    _refresh_item_serving_display(item)
                    for key in ["calories", "kcal", "protein", "fat", "carbs"]:
                        item[key] = float(item.get(key) or 0.0) * item_scale

        def _is_dairy_or_soy_item(item: dict) -> bool:
            category = _canonical_food_category(item.get("category") or item.get("clean_category"), item.get("name", ""))
            name_text = _normalize_search_text(item.get("name", ""))
            return (
                category in {"dairy", "plant_protein"}
                or any(term in name_text for term in ("milk", "sua", "yogurt", "sua chua", "soy", "dau nanh", "tofu", "dau hu", "dau phu"))
            )

        def _current_dairy_soy_count() -> int:
            return sum(
                1
                for meal in meal_plan_payload
                for item in meal.get("items", [])
                if _is_dairy_or_soy_item(item)
            )

        def _current_family_count(family: str) -> int:
            if not family:
                return 0
            return sum(
                1
                for meal in meal_plan_payload
                for item in meal.get("items", [])
                if HealthyWeightGainRecommender._food_family(item) == family
            )

        def _item_category(item: dict) -> str:
            return _canonical_food_category(item.get("category") or item.get("clean_category"), item.get("name", ""))

        vegetarian_mode = _is_vegetarian_diet(payload.diet_type or payload.diet_style or "")
        max_animal_protein_items = 0 if vegetarian_mode else (2 if target_protein <= 95 else 3)
        budget_level = RecommenderService._normalize_budget_level(payload.budget_level)

        def _is_animal_protein_item(item: dict) -> bool:
            return _item_category(item) in {"protein_meat", "protein_seafood"} or _row_matches_terms(item, list(VEGETARIAN_BLOCKED_TERMS)) or is_non_vegetarian_food(item)

        def _is_animal_protein_row(row: pd.Series | dict) -> bool:
            return _canonical_food_category(row.get("clean_category", row.get("category", "")), row.get("name", "")) in {"protein_meat", "protein_seafood"} or _is_animal_meat_or_seafood_row(row)

        protein_limited_categories = {"protein_meat", "protein_seafood", "egg", "dairy", "plant_protein"}
        protein_limited_terms = (
            "fish",
            "ca",
            "salmon",
            "tuna",
            "meat",
            "thit",
            "beef",
            "pork",
            "chicken",
            "ga",
            "egg",
            "trung",
            "milk",
            "sua",
            "yogurt",
            "sua chua",
            "soy",
            "dau nanh",
            "tofu",
            "dau hu",
            "dau phu",
        )

        def _is_protein_limited_food(row: pd.Series | dict) -> bool:
            category = _canonical_food_category(row.get("clean_category", row.get("category", "")), row.get("name", ""))
            if category in protein_limited_categories:
                return True
            name_text = _normalize_search_text(row.get("name", ""))
            return _text_has_any(name_text, protein_limited_terms)

        def _budget_rank_delta(row: pd.Series | dict, strength: float = 1.0) -> float:
            return -RecommenderService._budget_score_adjustment(row, budget_level) * float(strength)

        def _natural_rank_delta(row: pd.Series | dict, strength: float = 1.0) -> float:
            return -RecommenderService._natural_food_score_adjustment(row) * float(strength)

        def _animal_protein_count() -> int:
            return sum(
                1
                for meal in meal_plan_payload
                for item in meal.get("items", [])
                if _is_animal_protein_item(item)
            )

        def _item_name_text(item: dict) -> str:
            return _normalize_search_text(item.get("name", ""))

        def _is_dessert_or_sweet_item(item: dict) -> bool:
            category = _item_category(item)
            name_text = _item_name_text(item)
            return (
                _is_dessert_or_sweet_row(item)
                or category == "dessert_sweets"
                or HealthyWeightGainRecommender._is_dirty_bulk_name(name_text)
                or any(term in name_text for term in ("croissant", "banh sung bo", "ice cream", "kem trai cay", "dessert", "cake", "cookie", "pastry", "donut", "banh ngot"))
            )

        def _is_primary_starch_item(item: dict) -> bool:
            category = _item_category(item)
            name_text = _item_name_text(item)
            return (
                category in {"starch_grain", "starch_tuber"}
                or any(term in name_text for term in ("rice", "com", "noodle", "pasta", "spaghetti", "bread", "banh mi", "oat", "yen mach", "potato", "khoai", "cereal"))
            )

        def _is_optional_item(item: dict) -> bool:
            role = str(item.get("meal_role") or item.get("culinary_role") or "").lower()
            category = _item_category(item)
            return (
                role in {"extra", "fat", "side", "fruit", "drink", "drink_or_extra"}
                or category in {"dairy", "healthy_fat_nuts", "fruit", "dessert_sweets"}
            )

        def _should_replace_low_fat_dairy() -> bool:
            return bmi_value_for_policy < 18.5 or (target_fat > 0 and total_fat < target_fat * 0.80)

        def _row_is_good_energy_or_protein(row: pd.Series | dict, *, avoid_carb_heavy: bool = True, allow_low_fat_dairy: bool = False) -> bool:
            category = _canonical_food_category(row.get("clean_category", row.get("category", "")), row.get("name", ""))
            name_text = _normalize_search_text(row.get("name", ""))
            if category in {"dessert_sweets", "drink_natural", "starch_grain", "starch_tuber"}:
                return False
            if any(term in name_text for term in ("rice", "com", "noodle", "pasta", "spaghetti", "bread", "banh mi", "oat", "yen mach", "potato", "khoai", "cereal")):
                return False
            if HealthyWeightGainRecommender._is_dirty_bulk_name(name_text):
                return False
            if _is_processed_meat_row(row) or _is_dessert_or_sweet_row(row):
                return False
            if _is_low_fat_dairy_row(row) and not allow_low_fat_dairy:
                return False
            calories = max(float(row.get("kcal_per_serving_clean") or row.get("calories_raw") or 0.0), 1.0)
            carbs = float(row.get("carbs_per_serving_clean") or row.get("carbs_raw") or 0.0)
            if avoid_carb_heavy and (category == "fruit" or carbs * 4.0 / calories > 0.50):
                return False
            return (
                _is_healthy_gain_energy_row(row)
                or category in {"healthy_fat_nuts", "dairy", "egg", "protein_seafood", "protein_meat", "plant_protein"}
                or any(term in name_text for term in ("avocado", "bo", "nuts", "hat", "peanut butter", "olive", "oil", "dau olive", "egg", "trung", "salmon", "ca hoi", "fish", "milk", "sua", "yogurt", "sua chua", "tofu", "dau hu", "dau phu", "lean meat", "thit nac"))
            )

        def _replace_or_fill_high_energy_items(target_add_kcal: float, max_changes: int = 3, prefer_fat: bool = False) -> int:
            nonlocal preserved_item_count_note
            existing_ids = {
                str(item.get("food_id"))
                for meal in meal_plan_payload
                for item in meal.get("items", [])
                if item.get("food_id") is not None
            }
            added = 0
            added_kcal = 0.0

            for _, row in ranked.iterrows():
                if added >= max_changes:
                    break
                candidate_id = str(row.get("food_id", ""))
                if not candidate_id or candidate_id in existing_ids:
                    continue
                candidate_family = HealthyWeightGainRecommender._food_family(row)
                if candidate_family and _current_family_count(candidate_family) >= HealthyWeightGainRecommender._daily_family_limit(candidate_family):
                    continue
                if not _row_is_good_energy_or_protein(row, avoid_carb_heavy=True):
                    continue
                if _is_animal_protein_row(row) and (
                    _animal_protein_count() >= max_animal_protein_items
                    or (target_protein > 0 and total_protein >= target_protein * 0.95)
                ):
                    continue
                if prefer_fat:
                    category = _canonical_food_category(row.get("clean_category", row.get("category", "")), row.get("name", ""))
                    name_text = _normalize_search_text(row.get("name", ""))
                    fat_value = float(row.get("fat_per_serving_clean") or row.get("fat_raw") or 0.0)
                    is_fat_forward = (
                        category in {"healthy_fat_nuts", "dairy", "egg"}
                        or fat_value >= 7.0
                        or any(term in name_text for term in ("avocado", "bo", "nuts", "hat", "peanut butter", "olive", "oil", "dau olive", "whole milk", "sua nguyen kem", "salmon", "ca hoi"))
                    )
                    if not is_fat_forward:
                        continue
                kcal_serving = float(row.get("kcal_per_serving_clean") or row.get("calories_raw") or 0.0)
                kcal_100g = float(row.get("kcal_per_100g_clean") or 0.0)
                if kcal_serving <= 150 and kcal_100g <= 150:
                    continue
                candidate_item = self._to_food_item_payload(row)
                if _is_dairy_or_soy_item(candidate_item) and _current_dairy_soy_count() >= 3:
                    continue

                target_meal = None
                replace_index = None
                best_gain = 0.0
                for meal in meal_plan_payload:
                    items = meal.get("items", [])
                    limit = _expected_slots_for_meal(meal.get("meal_type", "meal"))
                    if len(items) < limit:
                        target_meal = meal
                        replace_index = None
                        best_gain = float(candidate_item.get("calories") or 0.0)
                        break
                    for idx, current in enumerate(items):
                        if not _is_optional_item(current):
                            continue
                        gain = float(candidate_item.get("calories") or 0.0) - float(current.get("calories") or current.get("kcal") or 0.0)
                        if gain > best_gain:
                            best_gain = gain
                            target_meal = meal
                            replace_index = idx
                if target_meal is None or best_gain <= 25:
                    continue
                if _is_animal_protein_item(candidate_item) and any(
                    _is_animal_protein_item(item)
                    for idx, item in enumerate(target_meal.get("items", []))
                    if idx != replace_index
                ):
                    continue

                if replace_index is None:
                    target_meal["items"].append(candidate_item)
                else:
                    target_meal["items"][replace_index] = candidate_item
                    preserved_item_count_note = True

                existing_ids.add(candidate_id)
                added += 1
                added_kcal += max(best_gain, 0.0)
                if added_kcal >= target_add_kcal:
                    break
            return added

        def _replace_high_carb_items(max_changes: int = 2) -> int:
            nonlocal preserved_item_count_note
            existing_ids = {
                str(item.get("food_id"))
                for meal in meal_plan_payload
                for item in meal.get("items", [])
                if item.get("food_id") is not None
            }
            replacements = 0

            for meal in meal_plan_payload:
                if replacements >= max_changes:
                    break
                items = meal.get("items", [])
                starch_indexes = [idx for idx, item in enumerate(items) if _is_primary_starch_item(item)]
                target_candidates: list[tuple[int, float, int, dict]] = []
                for idx, item in enumerate(items):
                    carbs = float(item.get("carbs") or 0.0)
                    if _is_dessert_or_sweet_item(item):
                        target_candidates.append((0, carbs, idx, item))
                    elif idx in starch_indexes[1:]:
                        target_candidates.append((1, carbs, idx, item))
                    elif _is_optional_item(item) and carbs >= 22:
                        target_candidates.append((2, carbs, idx, item))
                    elif _item_category(item) in {"fruit", "dairy"} and carbs >= 25:
                        target_candidates.append((3, carbs, idx, item))

                if not target_candidates:
                    continue
                _, _, target_index, target_item = sorted(target_candidates, key=lambda item: (item[0], -item[1]))[0]

                target_carbs_item = float(target_item.get("carbs") or 0.0)
                target_kcal_item = float(target_item.get("calories") or target_item.get("kcal") or 0.0)
                replacement_item = None
                for _, row in ranked.iterrows():
                    candidate_id = str(row.get("food_id", ""))
                    if not candidate_id or candidate_id in existing_ids:
                        continue
                    candidate_family = HealthyWeightGainRecommender._food_family(row)
                    if candidate_family and _current_family_count(candidate_family) >= HealthyWeightGainRecommender._daily_family_limit(candidate_family):
                        continue
                    if not _row_is_good_energy_or_protein(row, avoid_carb_heavy=True):
                        continue
                    if _is_animal_protein_row(row) and (
                        _animal_protein_count() >= max_animal_protein_items
                        or (target_protein > 0 and total_protein >= target_protein * 0.95)
                    ):
                        continue
                    candidate_item = self._to_food_item_payload(row)
                    if _is_dairy_or_soy_item(candidate_item) and _current_dairy_soy_count() >= 3:
                        continue
                    meal_items_without_target = [
                        item
                        for item_idx, item in enumerate(items)
                        if item_idx != target_index
                    ]
                    if _row_has_meal_semantic_duplicate(candidate_item, meal_items_without_target):
                        continue
                    candidate_carbs = float(candidate_item.get("carbs") or 0.0)
                    candidate_kcal = float(candidate_item.get("calories") or candidate_item.get("kcal") or 0.0)
                    if candidate_carbs > max(22.0, target_carbs_item - 15.0):
                        continue
                    if target_kcal_item > 0 and candidate_kcal < target_kcal_item * 0.55:
                        continue
                    replacement_item = candidate_item
                    break

                if replacement_item is None:
                    continue
                if _is_animal_protein_item(replacement_item) and any(
                    _is_animal_protein_item(item)
                    for idx, item in enumerate(items)
                    if idx != target_index
                ):
                    continue

                items[target_index] = replacement_item
                existing_ids.add(str(replacement_item.get("food_id")))
                replacements += 1
                preserved_item_count_note = True

            return replacements

        def _replace_low_protein_items(target_add_protein: float, max_changes: int = 2) -> int:
            nonlocal preserved_item_count_note
            existing_ids = {
                str(item.get("food_id"))
                for meal in meal_plan_payload
                for item in meal.get("items", [])
                if item.get("food_id") is not None
            }
            replacements = 0
            added_protein = 0.0

            for meal in meal_plan_payload:
                if replacements >= max_changes or added_protein >= target_add_protein:
                    break
                items = meal.get("items", [])
                target_indexes = [
                    idx for idx, item in enumerate(items)
                    if _is_optional_item(item)
                    and not _is_primary_starch_item(item)
                    and float(item.get("protein") or 0.0) < 7.0
                ]
                if not target_indexes:
                    continue
                target_index = min(target_indexes, key=lambda idx: float(items[idx].get("protein") or 0.0))
                target_item = items[target_index]
                target_protein_item = float(target_item.get("protein") or 0.0)
                target_kcal_item = float(target_item.get("calories") or target_item.get("kcal") or 0.0)

                replacement_item = None
                for _, row in ranked.iterrows():
                    candidate_id = str(row.get("food_id", ""))
                    if not candidate_id or candidate_id in existing_ids:
                        continue
                    candidate_family = HealthyWeightGainRecommender._food_family(row)
                    if candidate_family and _current_family_count(candidate_family) >= HealthyWeightGainRecommender._daily_family_limit(candidate_family):
                        continue
                    category = _canonical_food_category(row.get("clean_category", row.get("category", "")), row.get("name", ""))
                    if category not in {"egg", "protein_seafood", "protein_meat", "plant_protein", "dairy"}:
                        continue
                    if category in {"protein_seafood", "protein_meat"} and _animal_protein_count() >= max_animal_protein_items:
                        continue
                    if not _row_is_good_energy_or_protein(row, avoid_carb_heavy=True, allow_low_fat_dairy=True):
                        continue
                    candidate_item = self._to_food_item_payload(row)
                    if _is_dairy_or_soy_item(candidate_item) and _current_dairy_soy_count() >= 3:
                        continue
                    meal_items_without_target = [
                        item
                        for item_idx, item in enumerate(items)
                        if item_idx != target_index
                    ]
                    if _row_has_meal_semantic_duplicate(candidate_item, meal_items_without_target):
                        continue
                    candidate_protein = float(candidate_item.get("protein") or 0.0)
                    candidate_kcal = float(candidate_item.get("calories") or candidate_item.get("kcal") or 0.0)
                    if candidate_protein < target_protein_item + 5.0:
                        continue
                    if target_kcal_item > 0 and candidate_kcal < target_kcal_item * 0.45:
                        continue
                    replacement_item = candidate_item
                    break

                if replacement_item is None:
                    continue
                if _is_animal_protein_item(replacement_item) and any(
                    _is_animal_protein_item(item)
                    for idx, item in enumerate(items)
                    if idx != target_index
                ):
                    continue

                items[target_index] = replacement_item
                existing_ids.add(str(replacement_item.get("food_id")))
                replacements += 1
                added_protein += max(float(replacement_item.get("protein") or 0.0) - target_protein_item, 0.0)
                preserved_item_count_note = True

            return replacements

        def _scale_item_payload_to_kcal(item: dict, desired_kcal: float) -> None:
            current_kcal = float(item.get("calories") or item.get("kcal") or 0.0)
            if desired_kcal <= 0 or current_kcal <= 0:
                return
            scale = float(np.clip(desired_kcal / current_kcal, 0.60, 1.80))
            item_scale = scale
            quantity_g = item.get("quantity_g") or item.get("serving_grams")
            if quantity_g is not None:
                old_q = float(quantity_g)
                next_q = old_q * scale
                min_q, max_q = _serving_limits(item.get("category", ""), item.get("name", ""))
                if min_q is not None and max_q is not None:
                    next_q = min(max(next_q, min_q), max_q)
                item_scale = next_q / old_q if old_q > 0 else scale
                item["quantity_g"] = next_q
                item["serving_grams"] = next_q
                _refresh_item_serving_display(item)
            for key in ("calories", "kcal", "protein", "fat", "carbs"):
                item[key] = float(item.get(key) or 0.0) * item_scale

        def _row_is_low_protein_energy_replacement(row: pd.Series | dict, meal: dict, *, allow_second_starch: bool = False) -> bool:
            category = _canonical_food_category(row.get("clean_category", row.get("category", "")), row.get("name", ""))
            if category not in {"starch_grain", "starch_tuber", "fruit", "healthy_fat_nuts", "vegetable"}:
                return False
            if _is_protein_limited_food(row):
                return False
            if category in {"starch_grain", "starch_tuber"} and _meal_has_primary_starch(meal) and not allow_second_starch:
                return False
            if _is_abnormal_fat_spread_row(row) or _is_dessert_or_sweet_row(row) or _is_processed_meat_row(row):
                return False
            return True

        def _replace_excess_protein_items(max_changes: int = 3) -> int:
            nonlocal preserved_item_count_note
            replacements = 0

            while replacements < max_changes and _protein_is_above_target(1.15):
                existing_ids = {
                    str(item.get("food_id"))
                    for meal in meal_plan_payload
                    for item in meal.get("items", [])
                    if item.get("food_id") is not None
                }
                target_candidates: list[tuple[int, float, dict, int, dict]] = []
                for meal in meal_plan_payload:
                    for idx, item in enumerate(meal.get("items", [])):
                        if not _is_protein_limited_food(item):
                            continue
                        protein_value = float(item.get("protein") or 0.0)
                        category = _item_category(item)
                        if _is_animal_protein_item(item):
                            priority = 0
                        elif category in {"egg", "dairy", "plant_protein"} or _is_dairy_or_soy_item(item):
                            priority = 1
                        else:
                            continue
                        target_candidates.append((priority, -protein_value, meal, idx, item))

                if not target_candidates:
                    break

                _, _, target_meal, target_index, target_item = sorted(target_candidates, key=lambda item: (item[0], item[1]))[0]
                target_item_id = str(target_item.get("food_id")) if target_item.get("food_id") is not None else ""
                target_protein_item = float(target_item.get("protein") or 0.0)
                target_kcal_item = float(target_item.get("calories") or target_item.get("kcal") or 0.0)
                replacement_choices: list[tuple[float, float, float, float, float, dict]] = []

                for allow_second_starch in (False, True):
                    for _, row in ranked.iterrows():
                        candidate_id = str(row.get("food_id", "")).strip()
                        if not candidate_id or candidate_id == target_item_id:
                            continue
                        ids_without_target = {food_id for food_id in existing_ids if food_id != target_item_id}
                        if not _row_passes_hard_constraints(row, target_meal.get("items", []), ids_without_target):
                            continue
                        if not _row_is_low_protein_energy_replacement(row, target_meal, allow_second_starch=allow_second_starch):
                            continue
                        candidate_family = HealthyWeightGainRecommender._food_family(row)
                        if candidate_family and _current_family_count(candidate_family) >= HealthyWeightGainRecommender._daily_family_limit(candidate_family):
                            continue
                        candidate_item = self._to_food_item_payload(row)
                        if _is_protein_limited_food(candidate_item):
                            continue
                        if target_kcal_item > 0:
                            _scale_item_payload_to_kcal(candidate_item, target_kcal_item)
                        candidate_protein = float(candidate_item.get("protein") or 0.0)
                        candidate_kcal = float(candidate_item.get("calories") or candidate_item.get("kcal") or 0.0)
                        current_total_protein = _current_payload_totals()[1]
                        projected_protein = current_total_protein - target_protein_item + candidate_protein
                        if target_protein > 0 and projected_protein < target_protein * 0.90:
                            continue
                        if candidate_protein >= max(target_protein_item - 3.0, target_protein_item * 0.70):
                            continue
                        if target_kcal_item > 0 and candidate_kcal < target_kcal_item * 0.45:
                            continue
                        category = _item_category(candidate_item)
                        meal_items_without_target = [
                            item
                            for item_idx, item in enumerate(target_meal.get("items", []))
                            if item_idx != target_index
                        ]
                        semantic_duplicate_penalty = 6.0 if _row_has_meal_semantic_duplicate(candidate_item, meal_items_without_target) else 0.0
                        category_rank = {
                            "starch_grain": 0.0,
                            "starch_tuber": 0.0,
                            "fruit": 1.0,
                            "healthy_fat_nuts": 2.0,
                            "vegetable": 3.0,
                        }.get(category, 5.0)
                        replacement_choices.append(
                            (
                                semantic_duplicate_penalty,
                                category_rank
                                + (4.0 if allow_second_starch else 0.0)
                                + _budget_rank_delta(row, strength=1.0)
                                + _natural_rank_delta(row, strength=0.8),
                                candidate_protein,
                                abs(candidate_kcal - target_kcal_item),
                                -float(candidate_item.get("score") or 0.0),
                                candidate_item,
                            )
                        )
                    if replacement_choices:
                        break

                if not replacement_choices:
                    break

                replacement_item = sorted(replacement_choices, key=lambda item: (item[0], item[1], item[2], item[3], item[4]))[0][5]
                target_meal["items"][target_index] = replacement_item
                preserved_item_count_note = True
                replacements += 1

            return replacements

        def _replace_low_quality_items(max_changes: int = 4) -> int:
            nonlocal preserved_item_count_note
            existing_ids = {
                str(item.get("food_id"))
                for meal in meal_plan_payload
                for item in meal.get("items", [])
                if item.get("food_id") is not None
            }
            replacements = 0

            for meal in meal_plan_payload:
                if replacements >= max_changes:
                    break
                items = meal.get("items", [])
                for idx, target_item in enumerate(list(items)):
                    if replacements >= max_changes:
                        break
                    target_is_processed = _is_processed_meat_row(target_item)
                    target_is_sweet = _is_dessert_or_sweet_item(target_item)
                    target_is_low_fat_dairy = _is_low_fat_dairy_row(target_item) and _should_replace_low_fat_dairy()
                    if not (target_is_processed or target_is_sweet or target_is_low_fat_dairy):
                        continue

                    target_category = _item_category(target_item)
                    target_kcal_item = float(target_item.get("calories") or target_item.get("kcal") or 0.0)
                    replacement_item = None

                    for _, row in ranked.iterrows():
                        candidate_id = str(row.get("food_id", ""))
                        if not candidate_id or candidate_id in existing_ids:
                            continue
                        candidate_category = _canonical_food_category(row.get("clean_category", row.get("category", "")), row.get("name", ""))
                        if candidate_category in {"protein_seafood", "protein_meat"} and (
                            _animal_protein_count() >= max_animal_protein_items
                            or (target_protein > 0 and total_protein >= target_protein * 0.95)
                        ):
                            continue
                        if target_is_processed and candidate_category not in {"egg", "protein_seafood", "protein_meat", "plant_protein", "dairy"}:
                            continue
                        if target_is_low_fat_dairy and candidate_category not in {"dairy", "egg", "healthy_fat_nuts", "protein_seafood", "plant_protein", "protein_meat"}:
                            continue
                        if target_is_sweet and candidate_category in {"dessert_sweets", "drink_natural", "starch_grain", "starch_tuber"}:
                            continue
                        if _is_processed_meat_row(row) or _is_dessert_or_sweet_row(row) or _is_low_fat_dairy_row(row):
                            continue
                        if not _row_is_good_energy_or_protein(row, avoid_carb_heavy=True):
                            continue
                        candidate_family = HealthyWeightGainRecommender._food_family(row)
                        if candidate_family and _current_family_count(candidate_family) >= HealthyWeightGainRecommender._daily_family_limit(candidate_family):
                            continue
                        candidate_item = self._to_food_item_payload(row)
                        if _is_dairy_or_soy_item(candidate_item) and _current_dairy_soy_count() >= 3:
                            continue
                        meal_items_without_target = [
                            item
                            for item_idx, item in enumerate(items)
                            if item_idx != idx
                        ]
                        if _row_has_meal_semantic_duplicate(candidate_item, meal_items_without_target):
                            continue
                        candidate_kcal = float(candidate_item.get("calories") or candidate_item.get("kcal") or 0.0)
                        if target_kcal_item > 0 and candidate_kcal < target_kcal_item * 0.45:
                            continue
                        replacement_item = candidate_item
                        break

                    if replacement_item is None:
                        continue
                    if _is_animal_protein_item(replacement_item) and any(
                        _is_animal_protein_item(item)
                        for item_idx, item in enumerate(items)
                        if item_idx != idx
                    ):
                        continue

                    items[idx] = replacement_item
                    existing_ids.add(str(replacement_item.get("food_id")))
                    replacements += 1
                    preserved_item_count_note = True

            return replacements

        def _meal_label_vi(meal_type: object) -> str:
            labels = {"breakfast": "bữa sáng", "lunch": "bữa trưa", "dinner": "bữa tối", "snack": "bữa phụ"}
            return labels.get(str(meal_type or "").lower(), "bữa ăn")

        def _row_number(row: pd.Series | dict, *keys: str) -> float:
            for key in keys:
                value = row.get(key, None)
                try:
                    if value is None or pd.isna(value):
                        continue
                except (TypeError, ValueError):
                    if value is None:
                        continue
                try:
                    return float(value)
                except (TypeError, ValueError):
                    continue
            return 0.0

        hard_block_terms = _expand_food_terms(disliked_foods) + _expand_food_terms(payload.allergens)
        meal_fill_debug: list[dict] = []
        semantic_duplicate_relaxed_note = False

        def _meal_semantic_keys(items: list[dict]) -> set[str]:
            return {
                key
                for key in (normalize_food_similarity_key(item) for item in items)
                if key
            }

        def _row_has_meal_semantic_duplicate(row: pd.Series | dict, meal_items: list[dict]) -> bool:
            semantic_key = normalize_food_similarity_key(row)
            return bool(semantic_key and semantic_key in _meal_semantic_keys(meal_items))

        def _menu_eligible(row: pd.Series | dict) -> bool:
            value = row.get("menu_eligible", True)
            if isinstance(value, str):
                return value.strip().lower() not in {"0", "false", "no", "n", "none", "null"}
            return bool(value)

        def _row_has_valid_macros(row: pd.Series | dict) -> bool:
            calories = _row_number(row, "kcal_per_serving_clean", "calories_raw", "calories", "kcal")
            protein = _row_number(row, "protein_per_serving_clean", "protein_raw", "protein")
            fat = _row_number(row, "fat_per_serving_clean", "fat_raw", "fat")
            carbs = _row_number(row, "carbs_per_serving_clean", "carbs_raw", "carbs", "carb")
            return calories > 0 and protein >= 0 and fat >= 0 and carbs >= 0

        def _row_passes_hard_constraints(row: pd.Series | dict, meal_items: list[dict], existing_ids: set[str]) -> bool:
            candidate_id = str(row.get("food_id", "")).strip()
            if not candidate_id or candidate_id in existing_ids:
                return False
            if candidate_id in hard_excluded_food_ids:
                return False
            if not _menu_eligible(row) or not _row_has_valid_macros(row):
                return False
            if _is_abnormal_fat_spread_row(row):
                return False
            meal_ids = {str(item.get("food_id")) for item in meal_items if item.get("food_id") is not None}
            if candidate_id in meal_ids:
                return False
            if hard_block_terms and _row_matches_terms(row, hard_block_terms):
                return False
            if vegetarian_mode and _is_animal_protein_row(row):
                return False
            return True

        def _current_payload_totals() -> tuple[float, float, float, float]:
            current_kcal = 0.0
            current_protein = 0.0
            current_fat = 0.0
            current_carbs = 0.0
            for meal in meal_plan_payload:
                for item in meal.get("items", []):
                    current_kcal += float(item.get("calories") or item.get("kcal") or 0.0)
                    current_protein += float(item.get("protein") or 0.0)
                    current_fat += float(item.get("fat") or 0.0)
                    current_carbs += float(item.get("carbs") or item.get("carb") or 0.0)
            return current_kcal, current_protein, current_fat, current_carbs

        def _protein_is_above_target(multiplier: float = 1.0) -> bool:
            _, current_protein, _, _ = _current_payload_totals()
            return target_protein > 0 and current_protein > target_protein * multiplier

        def _protein_is_near_or_above_target(multiplier: float = 0.95) -> bool:
            _, current_protein, _, _ = _current_payload_totals()
            return target_protein > 0 and current_protein >= target_protein * multiplier

        def _row_is_high_protein_fill(row: pd.Series | dict) -> bool:
            protein = _row_number(row, "protein_per_serving_clean", "protein_raw", "protein")
            if protein <= 0:
                return False
            calories = max(_row_number(row, "kcal_per_serving_clean", "calories_raw", "calories", "kcal"), 1.0)
            protein_kcal_ratio = (protein * 4.0) / calories
            category = _canonical_food_category(row.get("clean_category", row.get("category", "")), row.get("name", ""))
            if category in {"protein_meat", "protein_seafood"}:
                return protein >= 8.0
            if category in {"egg", "plant_protein"}:
                return protein >= 10.0 or protein_kcal_ratio >= 0.26
            if category == "dairy":
                return protein >= 12.0 or protein_kcal_ratio >= 0.30
            return protein >= 15.0 or protein_kcal_ratio >= 0.32

        normalized_favorite_text = " ".join(
            _normalize_search_text(favorite)
            for favorite in favorite_foods
            if str(favorite or "").strip()
        )
        user_prefers_milk_fill = any(
            _text_has_term(normalized_favorite_text, term)
            for term in ("sua", "milk", "yogurt", "sua chua", "soy milk", "sua dau nanh")
        )

        def _row_is_preferred_milk_fill(row: pd.Series | dict) -> bool:
            category = _canonical_food_category(row.get("clean_category", row.get("category", "")), row.get("name", ""))
            text = _row_search_text(row)
            is_milk_or_yogurt = category == "dairy" and any(
                _text_has_term(text, term)
                for term in ("milk", "sua", "yogurt", "sua chua")
            )
            is_soy_milk = any(
                term in text
                for term in ("soy milk", "soymilk", "soy beverage", "sua dau nanh", "dau nanh beverage")
            )
            return is_milk_or_yogurt or is_soy_milk

        def _candidate_fill_priority(row: pd.Series | dict) -> tuple[float, float, float]:
            current_kcal, current_protein, _, _ = _current_payload_totals()
            protein_near_or_above_target = target_protein > 0 and current_protein >= target_protein * 0.95
            protein_high = target_protein > 0 and current_protein > target_protein * 1.15
            kcal_gap = max(target_kcal - current_kcal, 0.0) if target_kcal > 0 else 0.0
            missing_kcal = kcal_gap > 0
            category = _canonical_food_category(row.get("clean_category", row.get("category", "")), row.get("name", ""))
            name_text = _normalize_search_text(row.get("name", ""))
            kcal = _row_number(row, "kcal_per_serving_clean", "calories_raw", "calories", "kcal")
            score = float(row.get("score", 0.0) or 0.0)

            if protein_near_or_above_target and _row_is_high_protein_fill(row):
                return (99.0, 0.0, 0.0)

            energy_terms = ("oat", "yen mach", "rice", "com", "gao lut", "khoai", "potato", "bread", "banh mi", "banana", "chuoi", "avocado", "qua bo", "nuts", "hat", "olive", "dau olive", "peanut", "dau phong")
            energy_bonus = -0.25 if any(term in name_text for term in energy_terms) else 0.0
            quality_penalty = 0.0
            if _is_processed_favorite_penalty_row(row):
                quality_penalty += 2.0
            if _is_dessert_or_sweet_row(row) or _text_has_any(name_text, SWEET_LOW_PRIORITY_TERMS):
                quality_penalty += 2.0
            natural_fruit_bonus = -0.35 if _is_natural_fruit_row(row) else 0.0
            real_beef_bonus = (
                -0.45
                if _favorite_foods_include_beef(favorite_foods) and _is_real_beef_preference_row(row)
                else 0.0
            )
            favorite_milk_bonus = (
                -2.4
                if user_prefers_milk_fill
                and _row_is_preferred_milk_fill(row)
                and not (protein_near_or_above_target and _row_is_high_protein_fill(row))
                else 0.0
            )

            if protein_high:
                category_order = {
                    "fruit": 0.0,
                    "vegetable": 1.0,
                    "starch_tuber": 2.0,
                    "starch_grain": 2.2,
                    "plant_protein": 3.0,
                    "healthy_fat_nuts": 4.0,
                }
            elif missing_kcal:
                category_order = {
                    "fruit": 0.0,
                    "vegetable": 1.0,
                    "starch_tuber": 2.0,
                    "starch_grain": 2.2,
                    "plant_protein": 3.0,
                    "healthy_fat_nuts": 4.0,
                    "dairy": 5.0,
                    "egg": 6.0,
                }
            else:
                category_order = {
                    "fruit": 0.0,
                    "vegetable": 1.0,
                    "starch_tuber": 2.0,
                    "starch_grain": 2.2,
                    "plant_protein": 3.0,
                    "healthy_fat_nuts": 4.0,
                    "dairy": 5.0,
                    "egg": 6.0,
                }

            rank = (
                category_order.get(category, 8.0)
                + energy_bonus
                + natural_fruit_bonus
                + real_beef_bonus
                + favorite_milk_bonus
                + quality_penalty
                + _budget_rank_delta(row, strength=1.35)
                + _natural_rank_delta(row, strength=1.0)
            )
            if missing_kcal:
                if 150.0 <= kcal_gap <= 250.0:
                    target_item_kcal = kcal_gap
                    moderate_kcal_bonus = -0.25 if 120.0 <= kcal <= 280.0 else 0.25
                    kcal_sort = abs(kcal - target_item_kcal) + moderate_kcal_bonus
                else:
                    target_item_kcal = min(max(kcal_gap, 120.0), 280.0)
                    kcal_sort = abs(kcal - target_item_kcal)
            else:
                kcal_sort = kcal
            return (rank, kcal_sort, -score)

        def _meal_has_primary_starch(meal: dict) -> bool:
            return any(_is_primary_starch_item(item) for item in meal.get("items", []))

        def _row_is_vegetarian_safe_fill_candidate(row: pd.Series | dict, meal: dict) -> bool:
            category = _canonical_food_category(row.get("clean_category", row.get("category", "")), row.get("name", ""))
            if category not in VEGETARIAN_SAFE_FILL_CATEGORIES:
                return False
            if category in {"starch_grain", "starch_tuber"} and _meal_has_primary_starch(meal):
                return False
            if _is_abnormal_fat_spread_row(row) or _is_dessert_or_sweet_row(row) or _is_processed_meat_row(row):
                return False
            return True

        def _row_is_soft_fill_candidate(row: pd.Series | dict, meal: dict) -> bool:
            category_rank = _candidate_fill_priority(row)[0]
            if category_rank >= 99.0:
                return False
            if vegetarian_mode and _expected_slots_for_meal(meal.get("meal_type", "meal")) >= 5:
                return _row_is_vegetarian_safe_fill_candidate(row, meal)
            return not _is_abnormal_fat_spread_row(row)

        def _candidate_rows_for_meal(meal: dict) -> tuple[list[pd.Series | dict], list[pd.Series | dict]]:
            meal_items = meal.get("items", [])
            existing_ids = {
                str(item.get("food_id"))
                for payload_meal in meal_plan_payload
                for item in payload_meal.get("items", [])
                if item.get("food_id") is not None
            }
            hard_candidates: list[pd.Series | dict] = []
            for _, row in ranked.iterrows():
                if not _row_passes_hard_constraints(row, meal_items, existing_ids):
                    continue
                hard_candidates.append(row)

            soft_candidates = [
                row
                for row in hard_candidates
                if _row_is_soft_fill_candidate(row, meal)
            ]

            def _semantic_sort(rows: list[pd.Series | dict]) -> list[pd.Series | dict]:
                distinct_rows = [row for row in rows if not _row_has_meal_semantic_duplicate(row, meal_items)]
                duplicate_rows = [row for row in rows if _row_has_meal_semantic_duplicate(row, meal_items)]
                meal_animal_sources = {
                    source
                    for source in (_animal_main_protein_source(item) for item in meal_items)
                    if source
                }

                def _fill_sort_key(row: pd.Series | dict) -> tuple[float, float, float, float]:
                    candidate_source = _animal_main_protein_source(row)
                    animal_penalty = 3.0 if candidate_source and meal_animal_sources else 0.0
                    if candidate_source == "egg" or "egg" in meal_animal_sources:
                        animal_penalty += 1.0
                    rank, kcal_sort, score_sort = _candidate_fill_priority(row)
                    return (animal_penalty, rank, kcal_sort, score_sort)

                return sorted(distinct_rows, key=_fill_sort_key) + sorted(duplicate_rows, key=_fill_sort_key)

            return (
                _semantic_sort(hard_candidates),
                _semantic_sort(soft_candidates),
            )

        def fill_missing_items_for_meal(meal: dict, missing_count: int, reason: str) -> list[str]:
            nonlocal semantic_duplicate_relaxed_note
            if missing_count <= 0:
                return []
            meal_type = str(meal.get("meal_type") or "meal").lower()
            expected = _expected_slots_for_meal(meal_type)
            before_count = len(meal.get("items", []))
            hard_candidates, soft_candidates = _candidate_rows_for_meal(meal)
            logger.warning(
                "[MEAL ITEM COUNT CHECK] user_id=%s meal_type=%s expected_items=%s actual_items=%s missing_count=%s reason=%s candidate_count_after_hard_filter=%s candidate_count_after_soft_filter=%s",
                user.id,
                meal_type,
                expected,
                before_count,
                missing_count,
                reason,
                len(hard_candidates),
                len(soft_candidates),
            )

            added_names: list[str] = []
            no_item_added_reason = "not_attempted"
            candidates_to_try = soft_candidates or hard_candidates
            if not candidates_to_try:
                no_item_added_reason = "no_candidate_after_hard_filter"

            for row in candidates_to_try:
                if len(added_names) >= missing_count:
                    break
                item = self._to_food_item_payload(row)
                if not _row_passes_hard_constraints(row, meal.get("items", []), {
                    str(existing.get("food_id"))
                    for payload_meal in meal_plan_payload
                    for existing in payload_meal.get("items", [])
                    if existing.get("food_id") is not None
                }):
                    no_item_added_reason = "candidate_rejected_after_payload_conversion"
                    continue
                if _row_has_meal_semantic_duplicate(row, meal.get("items", [])):
                    semantic_duplicate_relaxed_note = True
                meal.setdefault("items", []).append(item)
                added_names.append(str(item.get("name") or item.get("food_id") or "item"))
                no_item_added_reason = ""

            logger.warning(
                "[MEAL FILL RESULT] meal_type=%s added_items=%s final_count=%s",
                meal_type,
                added_names,
                len(meal.get("items", [])),
            )
            final_count = len(meal.get("items", []))
            if final_count < expected:
                if added_names and not no_item_added_reason:
                    no_item_added_reason = "not_enough_candidates_after_partial_fill"
                elif not added_names and not no_item_added_reason:
                    no_item_added_reason = "no_item_added"
                logger.warning(
                    "[MEAL FILL FAIL] meal_type=%s expected_items=%s actual_items=%s candidate_count_after_hard_filter=%s candidate_count_after_soft_filter=%s reason_no_item_added=%s",
                    meal_type,
                    expected,
                    final_count,
                    len(hard_candidates),
                    len(soft_candidates),
                    no_item_added_reason,
                )
            meal_fill_debug.append(
                {
                    "meal_type": meal_type,
                    "expected_items": expected,
                    "actual_items_before": before_count,
                    "actual_items": final_count,
                    "missing_requested": missing_count,
                    "added_count": len(added_names),
                    "added_items": added_names,
                    "candidate_count_after_hard_filter": len(hard_candidates),
                    "candidate_count_after_soft_filter": len(soft_candidates),
                    "reason_no_item_added": no_item_added_reason if final_count < expected else "",
                }
            )
            return added_names

        def _fill_missing_items_for_all_meals(reason: str) -> int:
            added_total = 0
            for meal in meal_plan_payload:
                meal_type = str(meal.get("meal_type") or "meal").lower()
                expected = _expected_slots_for_meal(meal_type)
                actual = len(meal.get("items", []))
                missing = max(expected - actual, 0)
                if missing <= 0:
                    continue
                added_total += len(fill_missing_items_for_meal(meal, missing, reason))
            return added_total

        def _build_item_count_summary() -> tuple[dict[str, dict[str, int]], list[str], int]:
            summary: dict[str, dict[str, int]] = {}
            warnings_for_counts: list[str] = []
            missing_total = 0
            for meal in meal_plan_payload:
                meal_type = str(meal.get("meal_type") or "meal").lower()
                expected = _expected_slots_for_meal(meal_type)
                actual = len(meal.get("items", []))
                meal["expected_items"] = expected
                meal["actual_items"] = actual
                summary[meal_type] = {"expected": expected, "actual": actual}
                if actual >= expected:
                    continue
                missing_total += expected - actual
                label = {
                    "breakfast": "Bữa sáng",
                    "lunch": "Bữa trưa",
                    "dinner": "Bữa tối",
                    "snack": "Bữa phụ",
                }.get(meal_type, "Bữa ăn")
                warnings_for_counts.append(
                    f"{label} chỉ tạo được {actual}/{expected} món phù hợp."
                )
            return summary, warnings_for_counts, missing_total

        meal_types_present = {str(meal.get("meal_type", "")).lower() for meal in meal_plan_payload}


        meal_items_for_db, total_kcal, total_protein, total_fat, total_carbs = _recompute_plan_totals()
        sample_total_kcal = total_kcal
        logger.warning(
            "DEBUG_SAMPLE_TOTAL_KCAL=%s target=%s min=%s max=%s item_count=%s",
            sample_total_kcal,
            target_kcal,
            min_kcal,
            max_kcal,
            len(meal_items_for_db),
        )

        low_quality_replacements = _replace_low_quality_items(max_changes=4)
        if low_quality_replacements:
            logger.warning("DEBUG_LOW_QUALITY_REPLACED items=%s", low_quality_replacements)
            meal_items_for_db, total_kcal, total_protein, total_fat, total_carbs = _recompute_plan_totals()

        if target_kcal > 0 and total_kcal < min_kcal and total_kcal > 0:
            scale_up = target_kcal / total_kcal
            if 0.75 <= scale_up <= 1.35:
                _scale_payload_items(scale_up)
                logger.warning("DEBUG_KCAL_SCALE_UP applied scale=%s", scale_up)
            elif scale_up > 1.35:
                _scale_payload_items(1.35)
                added_items = _replace_or_fill_high_energy_items(target_add_kcal=(min_kcal - total_kcal), max_changes=3)
                logger.warning("DEBUG_KCAL_LOW replaced_high_energy_items=%s scale_candidate=%s", added_items, scale_up)
                meal_items_for_db, total_kcal, total_protein, total_fat, total_carbs = _recompute_plan_totals()
                if total_kcal > 0:
                    next_scale = target_kcal / total_kcal
                    if 0.75 <= next_scale <= 1.35:
                        _scale_payload_items(next_scale)
                        logger.warning("DEBUG_KCAL_SCALE_UP_AFTER_ADD applied scale=%s", next_scale)

        meal_items_for_db, total_kcal, total_protein, total_fat, total_carbs = _recompute_plan_totals()

        if target_kcal > 0 and total_kcal > max_kcal and total_kcal > 0:
            scale_down = target_kcal / total_kcal
            if 0.75 <= scale_down <= 1.35:
                _scale_payload_items(scale_down)
                logger.warning("DEBUG_KCAL_SCALE_DOWN applied scale=%s", scale_down)
            elif scale_down < 0.75:
                removed = 0
                for meal in meal_plan_payload:
                    items = meal.get("items", [])
                    while total_kcal > max_kcal and len(items) > 1 and removed < 3:
                        optional_indexes = [
                            idx for idx, item in enumerate(items)
                            if str(item.get("meal_role") or item.get("culinary_role") or "").lower() in {"extra", "fat", "side", "drink", "drink_or_extra"}
                        ]
                        if not optional_indexes:
                            break
                        idx = max(optional_indexes, key=lambda i: float(items[i].get("calories") or 0.0))
                        items.pop(idx)
                        removed += 1
                        preserved_item_count_note = True
                        meal_items_for_db, total_kcal, total_protein, total_fat, total_carbs = _recompute_plan_totals()
                logger.warning("DEBUG_KCAL_HIGH removed_snack_items=%s scale_candidate=%s", removed, scale_down)
                if total_kcal > 0:
                    next_scale_down = target_kcal / total_kcal
                    if 0.75 <= next_scale_down <= 1.35:
                        _scale_payload_items(next_scale_down)
                        logger.warning("DEBUG_KCAL_SCALE_DOWN_AFTER_REMOVE applied scale=%s", next_scale_down)

        meal_items_for_db, total_kcal, total_protein, total_fat, total_carbs = _recompute_plan_totals()
        
        target_protein = float(nutrition_target.get("protein_g") or nutrition_target.get("protein_target") or nutrition_target.get("protein") or 0.0)
        if target_protein > 0 and total_protein < target_protein * 0.90:
            replacements = _replace_low_protein_items(
                target_add_protein=(target_protein * 0.90 - total_protein),
                max_changes=2,
            )
            if replacements:
                logger.warning("DEBUG_PROTEIN_LOW replaced_low_protein_items=%s", replacements)
                meal_items_for_db, total_kcal, total_protein, total_fat, total_carbs = _recompute_plan_totals()

        if target_protein > 0 and total_protein > target_protein * 1.10:
            scale_p = (target_protein * 1.05) / total_protein

        if ENABLE_HARD_INGREDIENT_COVERAGE and available_ingredients:
            requested_ingredients = list(available_ingredients)
            baseline_food_ids = {
                str(item.get("food_id"))
                for meal in meal_plan_payload
                for item in meal.get("items", [])
                if item.get("food_id") is not None
            }
            coverage_added_foods: list[str] = []

            def _current_covered_ingredients() -> set[str]:
                covered: set[str] = set()
                for meal in meal_plan_payload:
                    for item in meal.get("items", []):
                        covered.update(ingredient_match_list(item, requested_ingredients))
                return covered

            def _select_coverage_target(candidate_item: dict, candidate_group: str):
                best_choice: tuple[tuple[float, float, float, float], int, int | None] | None = None
                for meal_index, meal in enumerate(meal_plan_payload):
                    items = meal.get("items", [])
                    meal_type = str(meal.get("meal_type") or "meal").lower()
                    expected = _expected_slots_for_meal(meal_type)
                    same_group_present = any(
                        macro_group(existing.get("category") or existing.get("clean_category") or "") == candidate_group
                        for existing in items
                    )
                    if len(items) < expected:
                        append_score = (
                            0.0 if same_group_present else 1.0,
                            float(len(items)),
                            float(expected - len(items)),
                            -float(candidate_item.get("score") or 0.0),
                        )
                        choice = (append_score, meal_index, None)
                        if best_choice is None or choice[0] < best_choice[0]:
                            best_choice = choice

                    for item_index, current_item in enumerate(items):
                        if ingredient_match_count(current_item, requested_ingredients) > 0:
                            continue
                        current_group = macro_group(current_item.get("category") or current_item.get("clean_category") or "")
                        if candidate_group == "protein" and current_group not in {"protein", "extra"}:
                            continue
                        if candidate_group == "starch" and current_group not in {"starch", "extra"}:
                            continue
                        if candidate_group == "vegetable" and current_group not in {"vegetable", "extra"}:
                            continue
                        if candidate_group == "dairy" and current_group not in {"dairy", "extra"}:
                            continue
                        if candidate_group == "fruit" and current_group not in {"fruit", "extra"}:
                            continue
                        if candidate_group == "extra" and current_group not in {"extra", "fruit", "dairy"}:
                            continue
                        if current_group != candidate_group and not _is_optional_item(current_item):
                            continue

                        meal_without_target = [existing for idx, existing in enumerate(items) if idx != item_index]
                        if _row_has_meal_semantic_duplicate(candidate_item, meal_without_target):
                            continue

                        current_kcal = float(current_item.get("calories") or current_item.get("kcal") or 0.0)
                        candidate_kcal = float(candidate_item.get("calories") or candidate_item.get("kcal") or 0.0)
                        replace_score = (
                            0.0 if current_group == candidate_group else 1.0,
                            0.0 if _is_optional_item(current_item) else 1.0,
                            abs(candidate_kcal - current_kcal),
                            -float(current_item.get("score") or 0.0),
                        )
                        choice = (replace_score, meal_index, item_index)
                        if best_choice is None or choice[0] < best_choice[0]:
                            best_choice = choice

                return best_choice

            current_covered = _current_covered_ingredients()
            for ingredient in requested_ingredients:
                if ingredient in current_covered:
                    continue

                candidate_rows: list[tuple[tuple[float, float, float], dict, str]] = []
                for _, row in ranked.iterrows():
                    if ingredient_match_count(row, [ingredient]) <= 0:
                        continue
                    if not _row_passes_hard_constraints(row, [], baseline_food_ids):
                        continue
                    candidate_item = copy.deepcopy(self._to_food_item_payload(row))
                    candidate_group = macro_group(candidate_item.get("category") or row.get("clean_category") or row.get("category") or "")
                    candidate_priority = (
                        -float(row.get("score") or 0.0),
                        0.0 if candidate_group in {"starch", "protein", "dairy"} else 1.0,
                        float(candidate_item.get("calories") or 0.0),
                    )
                    candidate_rows.append((candidate_priority, candidate_item, candidate_group))

                candidate_rows.sort(key=lambda item: item[0])
                if not candidate_rows:
                    print("[HARD INGREDIENT COVERAGE SKIPPED]", {
                        "ingredient": ingredient,
                        "reason": "no_candidate",
                    }, flush=True)
                    continue

                accepted = False
                for _, candidate_item, candidate_group in candidate_rows:
                    before_snapshot = copy.deepcopy(meal_plan_payload)
                    before_totals = (total_kcal, total_protein, total_fat, total_carbs)
                    target_choice = _select_coverage_target(candidate_item, candidate_group)
                    if target_choice is None:
                        print("[HARD INGREDIENT COVERAGE SKIPPED]", {
                            "ingredient": ingredient,
                            "candidate": candidate_item.get("name"),
                            "reason": "no_safe_slot",
                        }, flush=True)
                        continue

                    _, meal_index, target_index = target_choice
                    target_meal = meal_plan_payload[meal_index]
                    if target_index is None:
                        target_meal.setdefault("items", []).append(candidate_item)
                        action = "append"
                        target_name = None
                    else:
                        target_name = str(target_meal.get("items", [])[target_index].get("name") or "")
                        target_meal["items"][target_index] = candidate_item
                        action = "replace"
                        preserved_item_count_note = True

                    meal_items_for_db, total_kcal, total_protein, total_fat, total_carbs = _recompute_plan_totals()
                    catchup_applied = False

                    if target_protein > 0 and total_protein < target_protein * 0.90:
                        protein_replacements = _replace_low_protein_items(
                            target_add_protein=(target_protein * 0.90 - total_protein),
                            max_changes=2,
                        )
                        if protein_replacements:
                            catchup_applied = True
                            meal_items_for_db, total_kcal, total_protein, total_fat, total_carbs = _recompute_plan_totals()

                    if target_kcal > 0 and total_kcal < min_kcal:
                        energy_replacements = _replace_or_fill_high_energy_items(
                            target_add_kcal=max(min_kcal - total_kcal, 0.0),
                            max_changes=2,
                            prefer_fat=candidate_group in {"dairy", "extra"},
                        )
                        if energy_replacements:
                            catchup_applied = True
                            meal_items_for_db, total_kcal, total_protein, total_fat, total_carbs = _recompute_plan_totals()
                        if total_kcal < min_kcal and total_kcal > 0:
                            final_scale = target_kcal / total_kcal
                            if 1.0 <= final_scale <= 1.25:
                                _scale_preferred_energy_items(final_scale)
                                catchup_applied = True
                                meal_items_for_db, total_kcal, total_protein, total_fat, total_carbs = _recompute_plan_totals()
                            elif 0.75 <= final_scale <= 1.35:
                                _scale_payload_items(final_scale)
                                catchup_applied = True
                                meal_items_for_db, total_kcal, total_protein, total_fat, total_carbs = _recompute_plan_totals()

                    if target_kcal > 0 and total_kcal < min_kcal:
                        meal_plan_payload[:] = before_snapshot
                        meal_items_for_db, total_kcal, total_protein, total_fat, total_carbs = _recompute_plan_totals()
                        print("[HARD INGREDIENT COVERAGE SKIPPED]", {
                            "ingredient": ingredient,
                            "candidate": candidate_item.get("name"),
                            "reason": "would_break_kcal_balance",
                        }, flush=True)
                        continue

                    if target_protein > 0 and total_protein < target_protein * 0.85:
                        meal_plan_payload[:] = before_snapshot
                        meal_items_for_db, total_kcal, total_protein, total_fat, total_carbs = _recompute_plan_totals()
                        print("[HARD INGREDIENT COVERAGE SKIPPED]", {
                            "ingredient": ingredient,
                            "candidate": candidate_item.get("name"),
                            "reason": "would_break_protein_balance",
                        }, flush=True)
                        continue

                    if target_kcal > 0 and total_kcal < before_totals[0] * 0.95 and not catchup_applied:
                        meal_plan_payload[:] = before_snapshot
                        meal_items_for_db, total_kcal, total_protein, total_fat, total_carbs = _recompute_plan_totals()
                        print("[HARD INGREDIENT COVERAGE SKIPPED]", {
                            "ingredient": ingredient,
                            "candidate": candidate_item.get("name"),
                            "reason": "would_make_kcal_worse",
                        }, flush=True)
                        continue

                    coverage_added_foods.append(str(candidate_item.get("name") or candidate_item.get("food_id") or "item"))
                    current_covered = _current_covered_ingredients()
                    accepted = True
                    if catchup_applied:
                        print("[HARD INGREDIENT COVERAGE_ACCEPTED_AFTER_CATCHUP]", {
                            "ingredient": ingredient,
                            "candidate": candidate_item.get("name"),
                            "action": action,
                            "target_meal": str(target_meal.get("meal_type") or "meal"),
                            "target_item": target_name,
                        }, flush=True)
                    else:
                        print("[HARD INGREDIENT COVERAGE ACCEPTED]", {
                            "ingredient": ingredient,
                            "candidate": candidate_item.get("name"),
                            "action": action,
                            "target_meal": str(target_meal.get("meal_type") or "meal"),
                            "target_item": target_name,
                        }, flush=True)
                    break

                if not accepted:
                    print("[HARD INGREDIENT COVERAGE SKIPPED]", {
                        "ingredient": ingredient,
                        "reason": "no_safe_candidate_after_balance",
                    }, flush=True)

            meal_items_for_db, total_kcal, total_protein, total_fat, total_carbs = _recompute_plan_totals()
            final_covered = _current_covered_ingredients()
            final_uncovered = [ingredient for ingredient in requested_ingredients if ingredient not in final_covered]
            added_balance_foods = [
                str(item.get("name") or item.get("food_id") or "item")
                for meal in meal_plan_payload
                for item in meal.get("items", [])
                if str(item.get("food_id")) not in baseline_food_ids
                and macro_group(item.get("category") or item.get("clean_category") or "") in {"starch", "protein", "dairy"}
            ]
            print("[HARD INGREDIENT COVERAGE FINAL]", {
                "requested_ingredients": requested_ingredients,
                "covered_ingredients": sorted(final_covered),
                "uncovered_ingredients": final_uncovered,
                "nutrition_after": {
                    "total_kcal": round(total_kcal, 2),
                    "target_kcal": round(target_kcal, 2),
                    "protein": round(total_protein, 2),
                },
                "added_balance_foods": added_balance_foods,
            }, flush=True)
            _scale_protein_items(scale_p)
            meal_items_for_db, total_kcal, total_protein, total_fat, total_carbs = _recompute_plan_totals()

        target_fat = float(nutrition_target.get("fat_g") or nutrition_target.get("fat_target") or nutrition_target.get("fat") or 0.0)
        if target_fat > 0 and total_fat < target_fat * 0.80:
            added_items = _replace_or_fill_high_energy_items(target_add_kcal=min(max(target_kcal * 0.08, 120.0), 320.0), max_changes=2, prefer_fat=True)
            logger.warning("DEBUG_FAT_LOW replaced_high_energy_items=%s", added_items)
            meal_items_for_db, total_kcal, total_protein, total_fat, total_carbs = _recompute_plan_totals()

        target_carbs = float(nutrition_target.get("carbs_g") or nutrition_target.get("carb_target") or nutrition_target.get("carbs") or 0.0)
        if target_carbs > 0 and total_carbs > target_carbs * 1.12:
            replacements = _replace_high_carb_items(max_changes=3)
            if replacements:
                logger.warning("DEBUG_CARBS_HIGH replaced_high_carb_items=%s", replacements)
                meal_items_for_db, total_kcal, total_protein, total_fat, total_carbs = _recompute_plan_totals()

        if target_kcal > 0 and total_kcal > 0:
            final_scale = target_kcal / total_kcal
            if total_kcal < min_kcal and 0.92 <= final_scale <= 1.35:
                if target_protein > 0 and total_protein >= target_protein * 1.05:
                    _scale_preferred_energy_items(final_scale)
                else:
                    _scale_payload_items(final_scale)
                logger.warning("DEBUG_FINAL_KCAL_SCALE_UP applied scale=%s", final_scale)
                meal_items_for_db, total_kcal, total_protein, total_fat, total_carbs = _recompute_plan_totals()
            elif total_kcal > max_kcal and 0.82 <= final_scale <= 1.0:
                _scale_payload_items(final_scale)
                logger.warning("DEBUG_FINAL_KCAL_SCALE_DOWN applied scale=%s", final_scale)
                meal_items_for_db, total_kcal, total_protein, total_fat, total_carbs = _recompute_plan_totals()

        if target_protein > 0 and total_protein > target_protein * 1.12:
            scale_p = (target_protein * 1.08) / total_protein
            _scale_protein_items(scale_p)
            logger.warning("DEBUG_FINAL_PROTEIN_SCALE_DOWN applied scale=%s", scale_p)
            meal_items_for_db, total_kcal, total_protein, total_fat, total_carbs = _recompute_plan_totals()
            if total_protein > target_protein * 1.15:
                protein_replacements = _replace_excess_protein_items(max_changes=3)
                if protein_replacements:
                    logger.warning("DEBUG_PROTEIN_HIGH_REPLACED items=%s", protein_replacements)
                    meal_items_for_db, total_kcal, total_protein, total_fat, total_carbs = _recompute_plan_totals()
            if target_kcal > 0 and total_kcal < min_kcal and total_kcal > 0:
                catchup_scale = target_kcal / total_kcal
                if 1.0 <= catchup_scale <= 1.25:
                    _scale_preferred_energy_items(catchup_scale)
                    logger.warning("DEBUG_FINAL_ENERGY_CATCHUP applied scale=%s", catchup_scale)
                    meal_items_for_db, total_kcal, total_protein, total_fat, total_carbs = _recompute_plan_totals()

        fill_added_count = _fill_missing_items_for_all_meals("post_macro_adjustment")
        if fill_added_count:
            meal_items_for_db, total_kcal, total_protein, total_fat, total_carbs = _recompute_plan_totals()
        if target_protein > 0 and total_protein > target_protein * 1.15:
            protein_replacements = _replace_excess_protein_items(max_changes=3)
            if protein_replacements:
                logger.warning("DEBUG_POST_FILL_PROTEIN_HIGH_REPLACED items=%s", protein_replacements)
                meal_items_for_db, total_kcal, total_protein, total_fat, total_carbs = _recompute_plan_totals()
                if target_kcal > 0 and total_kcal < min_kcal and total_kcal > 0:
                    catchup_scale = target_kcal / total_kcal
                    if 1.0 <= catchup_scale <= 1.25:
                        _scale_preferred_energy_items(catchup_scale)
                        logger.warning("DEBUG_POST_FILL_ENERGY_CATCHUP applied scale=%s", catchup_scale)
                        meal_items_for_db, total_kcal, total_protein, total_fat, total_carbs = _recompute_plan_totals()
        meal_item_count_summary, meal_item_count_warnings, missing_item_count_total = _build_item_count_summary()

        delta_pct = abs(total_kcal - target_kcal) / target_kcal if target_kcal > 0 else 0.0

        errors = []
        warnings = []
        infos = []
        recommendation_explanations: list[dict] = []
        warnings.extend(meal_item_count_warnings)
        semantic_duplicate_meals: list[str] = []
        for meal in meal_plan_payload:
            seen_semantic_keys: set[str] = set()
            duplicate_found = False
            for item in meal.get("items", []):
                semantic_key = normalize_food_similarity_key(item)
                if not semantic_key:
                    continue
                if semantic_key in seen_semantic_keys:
                    duplicate_found = True
                    break
                seen_semantic_keys.add(semantic_key)
            if duplicate_found:
                semantic_duplicate_meals.append(str(meal.get("meal_type") or "meal"))
        if semantic_duplicate_meals or semantic_duplicate_relaxed_note:
            _append_unique_message(
                infos,
                "Một số món tương tự nhau được dùng lại do không đủ lựa chọn phù hợp.",
            )
        is_vegetarian_plan = _is_vegetarian_diet(payload.diet_type or payload.diet_style or "")

        def _favorite_is_selected(favorite: str) -> bool:
            raw_favorite = str(favorite or "").strip().lower()
            normalized_favorite = " ".join(_normalize_search_text(raw_favorite).split())
            beef_favorite = raw_favorite == "bò" or normalized_favorite in {"beef", "thit bo"}
            favorite_terms = _expand_food_terms([favorite])
            for meal in meal_plan_payload:
                for item in meal.get("items", []):
                    if beef_favorite:
                        item_text = _normalize_search_text(
                            f"{item.get('name', '')} {item.get('original_name', '')} {item.get('category', '')} {item.get('normalized_category', '')}"
                        )
                        if _item_category(item) == "protein_meat" and (
                            "beef" in item_text or "thit bo" in item_text or _text_has_term(item_text, "bo")
                        ):
                            return True
                    elif favorite_terms and _row_matches_terms(item, favorite_terms):
                        return True
            return False

        disliked_terms_for_favorites = hard_exclusion_terms_for_favorites
        favorite_skip_groups = {
            "excluded": [],
            "vegetarian": [],
            "protein": [],
            "macro": [],
        }
        for favorite in favorite_foods:
            favorite_label = str(favorite or "").strip()
            if not favorite_label:
                continue
            if _favorite_is_selected(favorite_label):
                continue
            favorite_row = {"name": favorite_label, "original_name": favorite_label, "search_keywords": favorite_label, "category": ""}
            if disliked_terms_for_favorites and _row_matches_terms(favorite_row, disliked_terms_for_favorites):
                favorite_skip_groups["excluded"].append(favorite_label)
                _append_unique_explanation(
                    recommendation_explanations,
                    "favorite_skipped",
                    favorite_label,
                    "excluded_by_disliked_or_allergy",
                )
            elif is_vegetarian_plan and (
                favorite_label in favorite_food_diet_conflicts
                or _favorite_term_conflicts_with_vegetarian(favorite_label)
            ):
                favorite_skip_groups["vegetarian"].append(favorite_label)
                _append_unique_explanation(
                    recommendation_explanations,
                    "favorite_skipped",
                    favorite_label,
                    "conflicts_with_vegetarian",
                )
            elif (
                target_protein > 0
                and total_protein >= target_protein * 0.95
                and _favorite_term_is_protein_limited(favorite_label)
            ):
                favorite_skip_groups["protein"].append(favorite_label)
                _append_unique_explanation(
                    recommendation_explanations,
                    "favorite_skipped",
                    favorite_label,
                    "protein_near_or_above_target",
                )
            elif _favorite_foods_include_beef([favorite_label]):
                favorite_skip_groups["macro"].append(favorite_label)
                _append_unique_explanation(
                    recommendation_explanations,
                    "favorite_skipped",
                    favorite_label,
                    "macro_balance_preferred",
                )

        excluded_favorites = _format_food_terms_for_message(favorite_skip_groups["excluded"])
        if excluded_favorites:
            _append_unique_message(
                infos,
                f"Món yêu thích '{excluded_favorites}' nằm trong danh sách loại trừ nên không được ưu tiên.",
            )

        vegetarian_favorites = _format_food_terms_for_message(favorite_skip_groups["vegetarian"])
        if vegetarian_favorites:
            _append_unique_message(
                infos,
                f"Món yêu thích '{vegetarian_favorites}' không phù hợp với chế độ ăn chay nên không được ưu tiên.",
            )

        protein_limited_favorites = _format_food_terms_for_message(favorite_skip_groups["protein"])
        if protein_limited_favorites:
            _append_unique_message(
                infos,
                f"Món yêu thích '{protein_limited_favorites}' chưa được ưu tiên vì hệ thống chọn phương án cân bằng kcal/protein tốt hơn.",
            )

        macro_balanced_favorites = _format_food_terms_for_message(favorite_skip_groups["macro"])
        if macro_balanced_favorites:
            _append_unique_message(
                infos,
                f"Món yêu thích '{macro_balanced_favorites}' chưa được ưu tiên vì hệ thống chọn phương án cân bằng kcal/protein tốt hơn.",
            )

        normalized_diet_for_validation = _normalize_search_text(payload.diet_type or payload.diet_style or "")
        is_clean_diet = any(term in normalized_diet_for_validation for term in EAT_CLEAN_DIET_TERMS)
        is_vegetarian_plan = _is_vegetarian_diet(payload.diet_type or payload.diet_style or "")
        final_disliked_terms = _expand_food_terms(disliked_foods)
        seafood_count = 0
        animal_protein_count_final = 0
        dessert_count_final = 0
        processed_meat_count_final = 0
        low_fat_dairy_count_final = 0
        food_ids = set()
        for meal in meal_plan_payload:
            meal_starch_count = 0
            meal_animal_protein_count = 0
            meal_animal_main_protein_count = 0
            for item in meal["items"]:
                if item["food_id"] in food_ids:
                    errors.append(f"Trùng lặp món ăn trong ngày: {item['name']}")
                food_ids.add(item["food_id"])
                if final_disliked_terms and _row_matches_terms(item, final_disliked_terms):
                    errors.append(f"Món '{item['name']}' nằm trong danh sách không thích của người dùng.")
                if _is_animal_protein_item(item):
                    animal_protein_count_final += 1
                    meal_animal_protein_count += 1
                    if is_vegetarian_plan:
                        errors.append(f"Chế độ ăn chay không phù hợp với món '{item['name']}'.")
                if _animal_main_protein_source(item):
                    meal_animal_main_protein_count += 1
                if _is_primary_starch_item(item):
                    meal_starch_count += 1
                if _is_dessert_or_sweet_item(item):
                    dessert_count_final += 1
                if _is_processed_meat_row(item):
                    processed_meat_count_final += 1
                if _is_low_fat_dairy_row(item):
                    low_fat_dairy_count_final += 1
                cat_lower = item.get("category", "").lower()
                name_lower = item.get("name", "").lower()
                if cat_lower in ["seafood", "hải sản", "protein_seafood"]:
                    seafood_count += 1
                    if "trứng cá" in name_lower and float(item.get("carbs", 0)) > 2:
                        errors.append(f"Món '{item['name']}' có dữ liệu carbs bất thường với nhóm Hải sản.")
                    
            if meal_starch_count > 1:
                errors.append("Mỗi bữa chỉ nên có một nguồn tinh bột chính; hãy đổi món tinh bột thứ hai sang bơ, hạt, trứng, cá béo hoặc sữa nguyên kem.")
            if (
                meal_animal_main_protein_count > 1
                and (target_protein <= 0 or total_protein >= target_protein)
                and ANIMAL_MAIN_PROTEIN_WARNING not in warnings
            ):
                warnings.append(ANIMAL_MAIN_PROTEIN_WARNING)

        if seafood_count > 2:
            errors.append("Hải sản xuất hiện quá 2 lần/ngày. (Vượt ngưỡng an toàn)")
            
        if dessert_count_final > 1:
            errors.append("Món ngọt/dessert xuất hiện quá 1 lần trong ngày, chưa phù hợp kế hoạch tăng cân lành mạnh.")
        if is_clean_diet and processed_meat_count_final > 0:
            errors.append("Eat clean không nên có thịt chế biến như bologna, xúc xích hoặc thịt nguội.")
        elif processed_meat_count_final > 1:
            warnings.append("Thịt chế biến xuất hiện nhiều hơn 1 lần trong ngày; nên ưu tiên trứng, cá, thịt nạc hoặc đậu hũ.")
        if low_fat_dairy_count_final > 0 and _should_replace_low_fat_dairy():
            warnings.append("Sữa/sữa chua ít béo không phải món phụ tăng năng lượng chính; nếu có lựa chọn, nên ưu tiên sữa nguyên kem hoặc sữa chua nguyên kem.")

        if profile_summary.get("medical_warning"):
            warnings.append(BMI_SEVERE_UNDERWEIGHT_WARNING)
        if semantic_duplicate_relaxed_note:
            infos.append("Một số món tương tự nhau được dùng lại do không đủ lựa chọn phù hợp.")
        if preserved_item_count_note or (target_kcal > 0 and total_kcal < min_kcal):
            warnings.append("Có thể cần tăng khẩu phần trong giới hạn hợp lý hoặc thêm bữa phụ tùy chọn, nhưng thực đơn vẫn giữ đúng số món mỗi bữa bạn đã chọn.")

        validation_result = self._validate_generated_plan(
            total_kcal=total_kcal,
            total_protein=total_protein,
            total_fat=total_fat,
            total_carbs=total_carbs,
            target=nutrition_target,
            errors=errors,
            warnings=warnings,
            infos=infos,
        )
        validation_result["meal_item_count_summary"] = meal_item_count_summary
        validation_result["meal_fill_debug"] = meal_fill_debug
        validation_result["recommendation_explanations"] = recommendation_explanations
        validation_result["ml_enabled"] = bool(ml_metadata.get("ml_enabled"))
        validation_result["ml_score_used"] = bool(ml_score_used)
        validation_result["ml_score_weight"] = ML_SCORE_WEIGHT
        macro_only_major = (
            validation_result["status"] == "major_adjustment"
            and not errors
            and missing_item_count_total <= 1
        )
        kcal_major = target_kcal > 0 and abs(total_kcal - target_kcal) / target_kcal > 0.10
        protein_major = target_protein > 0 and total_protein > target_protein * 1.15
        if macro_only_major and not kcal_major and not protein_major:
            validation_result["status"] = "minor_adjustment"
            validation_result["is_valid"] = False
            validation_result["isValid"] = False
            validation_result["errors"] = []
            validation_result["reason"] = (
                validation_result["warnings"][0]
                if validation_result.get("warnings")
                else None
            )
        if missing_item_count_total > 0:
            if missing_item_count_total == 1 and validation_result["status"] == "valid":
                validation_result["status"] = "minor_adjustment"
            elif missing_item_count_total > 1 or validation_result["status"] == "valid":
                validation_result["status"] = "major_adjustment" if missing_item_count_total > 1 else "minor_adjustment"
            validation_result["is_valid"] = False
            validation_result["isValid"] = False
            if not validation_result.get("reason") and meal_item_count_warnings:
                validation_result["reason"] = meal_item_count_warnings[0]
        is_valid = validation_result["is_valid"]
        if is_vegetarian_plan and not is_valid and errors:
            validation_result["status"] = "major_adjustment"
            validation_result["message"] = "Chưa đủ món chay phù hợp để đạt tối ưu dinh dưỡng. Hệ thống đã tạo phương án gần nhất từ các món chay hiện có."
            if validation_result["message"] not in warnings:
                warnings.append(validation_result["message"])
            if validation_result["message"] not in validation_result["warnings"]:
                validation_result["warnings"].append(validation_result["message"])
        else:
            validation_result["message"] = (
                "Bữa ăn đã đủ nhóm chính và phù hợp với kế hoạch tăng cân hôm nay."
                if is_valid
                else "Thực đơn cần chỉnh thêm để phù hợp hơn với kế hoạch tăng cân hôm nay."
            )
        if not is_valid:
            kcal_diff = total_kcal - target_kcal
            kcal_diff_pct = (abs(kcal_diff) / target_kcal) * 100 if target_kcal > 0 else 100.0
            logger.error(
                "Kcal validation mismatch | target_kcal=%s total_kcal=%s min_kcal=%s max_kcal=%s kcal_diff=%s kcal_diff_pct=%s meals=%s items=%s item_total_kcal=%s",
                target_kcal,
                total_kcal,
                min_kcal,
                max_kcal,
                kcal_diff,
                kcal_diff_pct,
                len(meal_plan_payload),
                len(meal_items_for_db),
                sum(float(item.get("calories") or 0.0) for item in meal_items_for_db),
            )

        required_meals = {"breakfast", "lunch", "dinner"}
        present_meals = {str(meal.get("meal_type", "")).lower() for meal in meal_plan_payload}
        missing_meals = sorted(required_meals - present_meals)
        if missing_meals:
            logger.warning("Generated meal plan missing meals: %s", missing_meals)

        # --- Construct New Response Schema ---
        response_payload = {
            "eligible": True,
            "reason": "OK",
            "bmi": round(float(profile_summary.get("bmi") or 0.0), 2),
            "bmi_category": profile_summary.get("bmi_category") or profile_summary.get("bmi_status"),
            "bmi_label": profile_summary.get("bmi_label") or asian_bmi_label(profile_summary.get("bmi_status")),
            "message": eligibility_check.get("message"),
            "warning": BMI_SEVERE_UNDERWEIGHT_WARNING if profile_summary.get("medical_warning") else None,
            "eligibility_check": eligibility_check,
            "profile_summary": profile_summary,
            "nutrition_target": nutrition_target,
            "meal_plan": {
                "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "total_kcal": round(total_kcal),
                "total_protein_g": round(total_protein),
                "total_fat_g": round(total_fat),
                "total_carbs_g": round(total_carbs),
                "status": validation_result["status"],
                "meal_item_count_summary": meal_item_count_summary,
                "meals": meal_plan_payload
            },
            "validation": validation_result,
            "recommendation_explanations": recommendation_explanations,
            "meal_item_count_summary": meal_item_count_summary,
            "target": target
        }

        if persist and meal_items_for_db:
            repository = RecommendationRepository(db)
            logger.warning("Sample meal_items_for_db (first 10): %s", meal_items_for_db[:10])
            created_request = repository.create_request_with_items(
                request_payload={
                    "weight_kg": payload.weight,
                    "height_cm": payload.height,
                    "user_id": user.id,
                    "activity_level": payload.activity,
                    "age": payload.age,
                    "sex": payload.sex,
                    "surplus_kcal": payload.surplus_kcal,
                    "preferred_categories": ";".join(payload.preferred_categories + favorite_foods),
                    "excluded_categories": ";".join(payload.excluded_categories + payload.allergens),
                    "target_calories": nutrition_target["calorie_target"],
                    "target_protein": nutrition_target["protein_g"],
                    "target_fat": nutrition_target["fat_g"],
                    "target_carbs": nutrition_target["carbs_g"],
                    "recommended_calories": total_kcal,
                    "absolute_error": abs(total_kcal - target_kcal),
                    "relative_error_pct": delta_pct * 100,
                    "precision_pct": 0,
                },
                meal_items=meal_items_for_db,
                meal_plan_status=validation_result["status"],
            )
            if created_request.meal_plans:
                persisted_plan = created_request.meal_plans[0]
                response_payload["meal_plan"]["id"] = persisted_plan.id
                response_payload["meal_plan"]["total_kcal"] = round(float(persisted_plan.total_kcal or 0.0))
                response_payload["meal_plan"]["total_protein_g"] = round(float(persisted_plan.total_protein or 0.0))
                response_payload["meal_plan"]["total_fat_g"] = round(float(persisted_plan.total_fat or 0.0))
                response_payload["meal_plan"]["total_carbs_g"] = round(float(persisted_plan.total_carbs or 0.0))
                inserted_items = [item for meal in persisted_plan.meals for item in meal.items]
                inserted_total_kcal = sum(float(item.kcal or 0.0) for item in inserted_items)
                response_payload["validation"]["totalKcal"] = inserted_total_kcal
                response_payload["validation"]["total_kcal"] = inserted_total_kcal
                logger.warning("DEBUG_INSERTED_TOTAL_KCAL=%s inserted_count=%s", inserted_total_kcal, len(inserted_items))
        elif persist:
            logger.error("Skip persisting empty meal plan for user_id=%s to avoid 422.", user.id)

        if payload.save_user_data:
            # Log what recommender attempted to save but DO NOT persist favorite/disliked lists
            print("[PROFILE WRITE SOURCE] recommender_service.py: save_user_data attempted values=", {
                "weight_kg": payload.weight,
                "height_cm": payload.height,
                "favorite_foods": ", ".join(favorite_foods) if favorite_foods else "",
                "disliked_foods": self._serialize_profile_list(disliked_foods),
            })
            # Only persist core numeric/profile fields. Do NOT write favorite/disliked foods here.
            saved_profile = UserRepository(db).upsert_profile(
                user.id,
                {
                    "weight_kg": payload.weight,
                    "height_cm": payload.height,
                    "activity_level": payload.activity,
                    "age": payload.age,
                    "sex": payload.sex,
                    "surplus_kcal": payload.surplus_kcal,
                },
            )

        return response_payload

    def get_history(self, db: Session, user: User, limit: int = 10, period: str = "all") -> dict:
        repository = RecommendationRepository(db)
        rows = repository.list_recent_requests(limit=limit, user_id=user.id, period=period)
        return {"items": repository.to_history_payload(rows)}

    def get_history_detail(self, db: Session, user: User, request_id: int) -> dict:
        repository = RecommendationRepository(db)
        row = repository.get_request(request_id=request_id, user_id=user.id)
        if row is None:
            from fastapi import HTTPException, status

            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="History item not found")
        return repository.to_history_detail_payload(row)

    def get_today_meal_plan(self, db: Session, user: User) -> dict:
        return RecommendationRepository(db).today_meal_plan_payload(user.id)

    def check_in_meal_plan_item(
        self,
        db: Session,
        user: User,
        meal_plan_item_id: int,
        eaten: bool,
        serving_grams: float | None = None,
    ) -> dict:
        repository = RecommendationRepository(db)
        try:
            repository.set_meal_plan_item_eaten(
                user_id=user.id,
                meal_plan_item_id=meal_plan_item_id,
                eaten=eaten,
                serving_grams=serving_grams,
            )
        except ValueError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meal plan item not found") from None
        return repository.today_meal_plan_payload(user.id)
