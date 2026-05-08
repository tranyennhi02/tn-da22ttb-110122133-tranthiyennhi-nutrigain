from __future__ import annotations

import logging
import random
import traceback
from datetime import datetime, timedelta, timezone
from functools import lru_cache

import numpy as np
import pandas as pd
from fastapi import HTTPException, status
from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session

from nutrigain_recommender import (
    DEFAULT_MEAL_CALORIE_RATIOS,
    DEFAULT_MEAL_STRUCTURE,
    FEATURE_COLUMNS,
    HealthyWeightGainRecommender,
    UserProfile,
    clear_taxonomy_cache,
)
from app.services.nutrition_calculation_service import NutritionCalculationService

logger = logging.getLogger(__name__)

DEFAULT_FOOD_PLACEHOLDER = "/images/placeholders/food-default.svg"
CATEGORY_PLACEHOLDERS = {
    "starch_grain": "/images/placeholders/starch-grain.svg",
    "starch_tuber": "/images/placeholders/starch-tuber.svg",
    "protein_meat": "/images/placeholders/protein-meat.svg",
    "protein_seafood": "/images/placeholders/protein-seafood.svg",
    "protein_plant": "/images/placeholders/protein-plant.svg",
    "vegetable": "/images/placeholders/vegetable.svg",
    "vegetable_herb": "/images/placeholders/vegetable.svg",
    "fruit": "/images/placeholders/fruit.svg",
    "dairy": "/images/placeholders/dairy.svg",
    "drink_natural": "/images/placeholders/drink.svg",
    "fats_good": "/images/placeholders/healthy-fat.svg",
    "healthy_fat": "/images/placeholders/healthy-fat.svg",
    "healthy_fat_nuts": "/images/placeholders/healthy-fat.svg",
    "dessert_sweets": "/images/placeholders/dessert.svg",
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
]


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
    return bool(
        image_url
        and _truthy(food.get("image_verified", False))
        and str(food.get("image_source_type", "") or "").strip().lower() == "real_food_photo"
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
    return float(weight_kg) / (height_m * height_m)


def validateUserProfile(payload: RecommendationInput) -> dict:
    errors: list[str] = []
    weight = payload.weight
    height = payload.height
    age = payload.age

    if weight is None or height is None:
        errors.append("Cần bổ sung chiều cao và cân nặng để tính BMI.")
    if weight is not None and not (20 <= float(weight) <= 250):
        errors.append("Cân nặng nằm ngoài ngưỡng hợp lý 20-250kg.")
    if height is not None and not (100 <= float(height) <= 230):
        errors.append("Chiều cao nằm ngoài ngưỡng hợp lý 100-230cm.")
    if age is not None and not (1 <= int(age) <= 120):
        errors.append("Tuổi nằm ngoài ngưỡng hợp lý 1-120.")

    bmi = calculateBMI(weight, height)
    if bmi is None:
        errors.append("Không thể tính BMI từ hồ sơ hiện tại.")

    return {
        "valid": not errors,
        "errors": errors,
        "bmi": bmi,
    }


def calculateNutritionTargets(profile: UserProfile | dict) -> dict:
    if isinstance(profile, dict):
        weight_kg = float(profile.get("weight_kg", profile.get("weight", 0)))
        height_cm = float(profile.get("height_cm", profile.get("height", 0)))
        age = int(profile.get("age", 25))
        sex = str(profile.get("sex", "male"))
        activity_level = str(profile.get("activity_level", profile.get("activity", "moderate")))
        gain_speed = str(profile.get("weight_gain_speed", profile.get("gain_speed", "moderate")))
    else:
        weight_kg = profile.weight_kg
        height_cm = profile.height_cm
        age = profile.age if profile.age is not None else 25
        sex = profile.sex or "male"
        activity_level = profile.activity_level
        gain_speed = profile.weight_gain_speed or "moderate"

    return NutritionCalculationService.calculate_targets(
        weight_kg=weight_kg,
        height_cm=height_cm,
        age=age,
        gender=sex,
        activity_level=activity_level,
        gain_speed=gain_speed
    )


def normalizeFoodCategory(category: str, name: str = "") -> str:
    return HealthyWeightGainRecommender.normalize_food_category(category, name)


def _normalize_search_text(value: object) -> str:
    return HealthyWeightGainRecommender._strip_accents(value).lower()


def _row_matches_terms(row: pd.Series | dict, terms: list[str]) -> bool:
    raw_text = _normalize_search_text(
        " ".join(
            str(row.get(column, "") or "")
            for column in ("food_id", "name", "name_en", "display_name_en", "clean_category", "food_group", "category")
        )
    )
    text = "".join(char if char.isalnum() or char.isspace() else " " for char in raw_text)
    text = " ".join(text.split())
    padded_text = f" {text} "
    for term in terms:
        normalized_term = " ".join(_normalize_search_text(term).strip().split())
        if not normalized_term:
            continue
        if " " not in normalized_term and len(normalized_term) <= 3:
            if f" {normalized_term} " in padded_text:
                return True
        elif normalized_term in text:
            return True
    return False


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
    expanded: list[str] = []
    synonym_map = {
        "ga": ["ga", "thit ga", "uc ga", "chicken", "chicken breast", "turkey", "ga tay"],
        "gà": ["gà", "thịt gà", "ức gà", "chicken", "chicken breast", "turkey", "gà tây"],
        "sua": ["sua", "milk"],
        "sữa": ["sữa", "milk"],
        "yen mach": ["yen mach", "oat", "oatmeal"],
        "yến mạch": ["yến mạch", "oat", "oatmeal"],
        "chuoi": ["chuoi", "banana"],
        "chuối": ["chuối", "banana"],
    }
    seen: set[str] = set()
    for term in terms:
        normalized = " ".join(_normalize_search_text(term).split())
        candidates = synonym_map.get(normalized, [term])
        for candidate in candidates:
            key = " ".join(_normalize_search_text(candidate).split())
            if key and key not in seen:
                seen.add(key)
                expanded.append(candidate)
    return expanded


def _serving_limits(category: object, name: object = "") -> tuple[float | None, float | None]:
    text = _normalize_search_text(f"{category} {name}")
    if "vegetable" in text or "rau" in text:
        return 80.0, 250.0
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
    if "oil" in text or "olive" in text or "spread" in text or "butter" in text or "dau olive" in text:
        return 5.0, 20.0
    return None, None


from app.core.config import settings
from app.models.entities import Food, FoodRating, MealPlanItem, RecommendationRequest, User, UserFavoriteFood
from app.repositories.interaction_repository import InteractionRepository
from app.repositories.recommendation_repository import RecommendationRepository
from app.repositories.user_repository import UserRepository
from app.views.schemas import MealPlanRegenerateInput, RecommendationInput


class RecommenderService:
    @staticmethod
    def _weight_status_from_bmi(bmi: float | None) -> str:
        if bmi is None:
            return "unknown"
        if bmi < 18.5:
            return "underweight"
        if bmi < 25:
            return "normal"
        if bmi < 30:
            return "overweight"
        return "obese"

    @staticmethod
    def _build_eligibility_check(payload: RecommendationInput) -> dict:
        profile_validation = validateUserProfile(payload)
        if not profile_validation["valid"]:
            return {
                "bmi": None if profile_validation["bmi"] is None else round(float(profile_validation["bmi"]), 2),
                "weight_status": "unknown",
                "eligible": False,
                "reason": " ".join(profile_validation["errors"]),
            }

        bmi = float(profile_validation["bmi"])
        weight_status = RecommenderService._weight_status_from_bmi(bmi)
        # Allow BMI up to 18.7 — measurements have margin of error and a
        # user computed as 18.49 should not be arbitrarily blocked.
        # The system is still strictly for underweight/near-underweight users.
        if bmi >= 18.7:
            return {
                "bmi": round(bmi, 2),
                "weight_status": weight_status,
                "eligible": False,
                "reason": "Hệ thống NutriGain hiện chỉ sinh thực đơn cho người thiếu cân hoặc gần ngưỡng thiếu cân (BMI < 18.7).",
            }

        goal_type = str(payload.goal_type or "gain").strip().lower()
        if goal_type in {"lose", "loss", "cut", "maintain", "maintenance", "keep"}:
            return {
                "bmi": round(bmi, 2),
                "weight_status": weight_status,
                "eligible": False,
                "reason": "Hệ thống này chỉ phục vụ mục tiêu tăng cân lành mạnh cho người thiếu cân.",
            }

        return {
            "bmi": round(bmi, 2),
            "weight_status": weight_status,
            "eligible": True,
            "reason": "Người dùng thuộc nhóm thiếu cân và đủ điều kiện tạo thực đơn tăng cân lành mạnh.",
        }

    @staticmethod
    def _raise_if_not_eligible(payload: RecommendationInput) -> dict:
        eligibility = RecommenderService._build_eligibility_check(payload)
        if not eligibility["eligible"]:
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
                        "reason": "Sinh thực đơn cho người không thuộc nhóm thiếu cân sẽ sai phạm vi hệ thống.",
                        "suggested_fix": "Chỉ tạo thực đơn khi BMI < 18.5 và mục tiêu là tăng cân lành mạnh.",
                    }
                ],
                "fixed_menu": [],
                "validation_rules_to_add": [
                    "Chặn request tạo thực đơn nếu thiếu chiều cao hoặc cân nặng.",
                    "Chặn request tạo thực đơn nếu BMI >= 18.5.",
                    "Chỉ cho phép mục tiêu tăng cân/tăng cơ trong hệ thống NutriGain.",
                ],
            }
            logger.error("Recommendation failed: %s", detail)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=detail,
            )
        return eligibility

    @staticmethod
    def _normalize_food_category(category: str, name: str = "") -> str:
        normalized = HealthyWeightGainRecommender._semantic_category(category, name)
        text = f"{name} {normalized}".strip().lower()
        if any(term in text for term in ("soy yogurt", "tofu yogurt", "sữa chua đậu nành", "sữa chua đậu phụ")):
            return "dairy"
        if any(term in text for term in ("white bean", "small white", "beans,", "lentil", "chickpea", "đậu trắng")):
            return "plant_protein"
        if any(term in text for term in ("tofu", "soybean", "tempeh", "đậu phụ", "đậu nành")):
            return "plant_protein"
        mapping = {
            "carb": "grain",
            "protein": "meat",
            "fat": "healthy_fat",
            "dairy": "dairy",
        }
        return mapping.get(normalized, normalized or "other")

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
                "name_en": name_en_series.astype(str).str.strip(),
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
    def _profile_goal_and_surplus(payload: RecommendationInput) -> tuple[str, float | None]:
        speed = str(payload.weight_gain_speed or payload.gain_speed or "").strip().lower()
        speed_surplus = {
            # Slow / nhẹ
            "slow": 300.0,
            "nhe": 300.0,
            "nhẹ": 300.0,
            "nhe on dinh": 300.0,
            "nhẹ, ổn định": 300.0,
            # Medium / vừa
            "medium": 400.0,
            "moderate": 400.0,
            "vua": 400.0,
            "vừa": 400.0,
            # Fast / mạnh
            "fast": 500.0,
            "strong": 500.0,
            "nhanh": 500.0,
            "manh": 500.0,
            "mạnh": 500.0,
            # Stronger / mạnh hơn
            "manh hon": 550.0,
            "mạnh hơn": 550.0,
            "nhanh hon": 550.0,
            "nhanh hơn": 550.0,
            "faster": 550.0,
            "stronger": 550.0,
            "aggressive": 550.0,
        }
        gain_surplus = payload.surplus_kcal
        if gain_surplus is None:
            if speed in speed_surplus:
                gain_surplus = speed_surplus[speed]
            else:
                # Partial match
                for key, val in speed_surplus.items():
                    if key and key in speed:
                        gain_surplus = val
                        break
        goal_type = str(payload.goal_type or "gain").strip().lower()
        if goal_type in {"maintain", "maintenance", "keep"}:
            return "maintain", 0.0
        if goal_type in {"lose", "loss", "cut"}:
            return "lose", payload.surplus_kcal or 350.0
        if goal_type in {"muscle", "muscle_gain", "gain_muscle"}:
            return "gain", gain_surplus or 300.0
        return "gain", gain_surplus

    @staticmethod
    def _apply_diet_and_budget_preferences(ranked: pd.DataFrame, payload: RecommendationInput) -> pd.DataFrame:
        if ranked.empty:
            return ranked

        next_df = ranked.copy()
        diet_style = str(payload.diet_type or payload.diet_style or "balanced").strip().lower()
        normalized_diet_style = _normalize_search_text(diet_style)
        budget_level = str(payload.budget_level or "standard").strip().lower()

        # ── Pre-build clean string Series (always bool-safe) ──────────────────
        # Use str.contains for masks so the result is always bool dtype.
        names = next_df["name"].fillna("").astype(str).str.lower()
        category = next_df["category"].fillna("").astype(str).str.lower()

        # ── Diet-type hard filters (remove rows) ──────────────────────────────
        if diet_style in {"vegetarian", "chay"}:
            next_df = next_df[~category.isin({"meat"})].copy()
            category = next_df["category"].fillna("").astype(str).str.lower()
            names = next_df["name"].fillna("").astype(str).str.lower()
        elif diet_style in {"vegan", "thuần chay", "thuan chay"}:
            next_df = next_df[~category.isin({"meat", "egg", "dairy"})].copy()
            category = next_df["category"].fillna("").astype(str).str.lower()
            names = next_df["name"].fillna("").astype(str).str.lower()

        if next_df.empty:
            return next_df

        # ── Helper: build a boolean mask from a list of keyword strings ────────
        def _name_contains_any(terms: tuple | list) -> "pd.Series[bool]":
            """Return bool Series: True where name contains any of the terms."""
            import re
            pattern = "|".join(re.escape(t) for t in terms if t)
            return names.str.contains(pattern, case=False, na=False, regex=True)

        def _cat_is_any(cats: set) -> "pd.Series[bool]":
            """Return bool Series: True where category is in cats."""
            return category.isin(cats)

        # ── Low-carb / keto ───────────────────────────────────────────────────
        if diet_style in {"low_carb", "low-carb", "keto"}:
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

        # ── Budget level scoring ───────────────────────────────────────────────
        if budget_level in {"low", "saving", "cheap", "tiết kiệm", "tiet kiem"}:
            affordable_terms = ("rice", "oat", "egg", "tofu", "bean", "lentil", "banana", "potato", "milk")
            premium_terms = ("salmon", "tuna", "shrimp", "almond", "walnut", "cheese", "avocado")
            affordable_mask: pd.Series = _name_contains_any(affordable_terms)   # bool
            premium_mask: pd.Series = _name_contains_any(premium_terms)          # bool
            next_df["score"] = (
                next_df["score"]
                + 0.08 * affordable_mask.astype(float)
                - 0.08 * premium_mask.astype(float)
            )
        elif budget_level in {"high", "premium"}:
            premium_terms = ("salmon", "tuna", "avocado", "almond", "walnut", "yogurt")
            premium_boost_mask: pd.Series = _name_contains_any(premium_terms)    # bool
            next_df["score"] = next_df["score"] + 0.04 * premium_boost_mask.astype(float)

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
            "cottage cheese", "ricotta",
            "offal", "organ meat", "sweetbread", "foie gras",
            "noi tang",
        )
        exotic_mask: pd.Series = _name_contains_any(_exotic_terms)               # bool
        next_df["score"] = next_df["score"] - 0.85 * exotic_mask.astype(float)

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
            "cá hồi", "cá ngừ", "cá rô", "cá basa", "fish",
            "rau củ", "rau xào", "rau luộc",
            "chuối", "banana", "bơ", "avocado", "táo", "apple",
            "hạt", "đậu phộng", "peanut", "almond", "walnut",
        )
        popular_mask: pd.Series = _name_contains_any(_popular_terms)              # bool
        next_df["score"] = next_df["score"] + 0.18 * popular_mask.astype(float)

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

        return next_df.sort_values("score", ascending=False)

    @staticmethod
    def filterFoodsByDietType(ranked: pd.DataFrame, diet_type: str, min_items: int = 0) -> pd.DataFrame:
        normalized_diet = _normalize_search_text(diet_type or "balanced")
        if not any(term in normalized_diet for term in EAT_CLEAN_DIET_TERMS):
            return ranked
        if ranked.empty:
            return ranked

        blocked_mask = ranked.apply(
            lambda row: (
                HealthyWeightGainRecommender._is_dirty_bulk_name(
                    f"{row.get('name', '')} {row.get('name_en', '')}"
                )
                or HealthyWeightGainRecommender._is_generic_menu_name(row.get("name", ""))
                or _row_matches_terms(row, EAT_CLEAN_BLOCKED_TERMS)
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
        PROTEIN_CATEGORIES = {"protein_meat", "protein_seafood", "plant_protein", "protein_plant", "egg"}
        VEG_FRUIT_CATEGORIES = {"vegetable", "fruit"}
        EXTRA_CATEGORIES = {"dairy", "healthy_fat_nuts", "plant_protein", "protein_plant", "fruit", "egg"}

        logger.info(f"Picking meals. Total ranked rows: {len(ranked)}")
        cat_counts = ranked["clean_category"].value_counts().to_dict()
        logger.info(f"Category counts before picking: {cat_counts}")

        plan: dict[str, pd.DataFrame] = {}
        target_calories = float(target.get("calories", 2000))
        ratio_sum = sum(DEFAULT_MEAL_CALORIE_RATIOS.get(m, 0) for m in meal_structure) or float(len(meal_structure))
        
        seen_food_ids = set()
        starch_group_counts: dict[str, int] = {}
        family_counts: dict[str, int] = {}
        dairy_count = 0
        bean_count = 0

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
                slots = [
                    {"name": "starch", "cats": STARCH_CATEGORIES, "required": True},
                    {"name": "protein", "cats": PROTEIN_CATEGORIES, "required": True},
                    {"name": "vegetable_or_fruit", "cats": VEG_FRUIT_CATEGORIES, "required": True},
                    {"name": "extra", "cats": EXTRA_CATEGORIES, "required": False},
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
            for slot_idx, slot in enumerate(slots):
                slot_name = slot["name"]
                allowed_cats = slot["cats"]
                
                pool = ranked[~ranked["food_id"].isin(seen_food_ids)].copy()
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
                        ~pool["clean_category"].isin({"plant_protein", "protein_plant"})
                    ]
                    
                constrained_pool = pool[pool["clean_category"].isin(allowed_cats)]
                
                if constrained_pool.empty:
                    available = pool["clean_category"].value_counts().to_dict()
                    logger.warning(f"Slot {slot_name} fail to find strict match in {meal}. Available categories: {available}")
                    fallback_cats = allowed_cats.copy()
                    if "protein_meat" in allowed_cats:
                        fallback_cats.update({"protein_seafood", "plant_protein", "egg", "dairy"})
                    if "dairy" in allowed_cats or "healthy_fat_nuts" in allowed_cats:
                        fallback_cats.update({"dairy", "healthy_fat_nuts", "plant_protein", "fruit", "egg", "drink_natural"})
                    if slot_name == "vegetable_or_fruit":
                        fallback_cats.update({"vegetable", "fruit"})

                    constrained_pool = pool[pool["clean_category"].isin(fallback_cats)]
                
                if constrained_pool.empty:
                    if slot["required"]:
                        logger.error(f"Required slot {slot_name} failed even after fallback in meal {meal}")
                    continue
                
                best_row = constrained_pool.sort_values("score", ascending=False).iloc[0].copy()
                
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
                seen_food_ids.add(best_row["food_id"])
                family = HealthyWeightGainRecommender._food_family(best_row)
                if family:
                    family_counts[family] = family_counts.get(family, 0) + 1
                clean_category = str(best_row.get("clean_category", ""))
                if clean_category in STARCH_CATEGORIES:
                    starch_group_counts[clean_category] = starch_group_counts.get(clean_category, 0) + 1
                if clean_category == "dairy":
                    dairy_count += 1
                if clean_category in {"plant_protein", "protein_plant"}:
                    bean_count += 1
            
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
            "meat": "Đạm",
            "egg": "Trứng",
            "grain": "Tinh bột",
            "fruit": "Trái cây",
            "vegetable": "Rau củ",
            "plant_protein": "Đạm thực vật",
            "healthy_fat": "Chất béo tốt",
            "other": "Khác",
        }
        normalized = str(category).strip().lower()
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
        category = str(row.get("clean_category", row.get("category", "")) or "").strip().lower()
        name = str(row.get("name", "") or "")
        name_text = _normalize_search_text(name)
        if any(term in name_text for term in ("nuoc cam", "nuoc ep", "nuoc dua", "nuoc trai cay", "orange juice", "juice")):
            return "drink_or_extra"
        if category in {"starch_grain", "starch_tuber", "grain"}:
            return "staple"
        if category in {"protein_meat", "protein_seafood", "protein_plant", "meat", "egg", "plant_protein"}:
            return "protein"
        if category in {"vegetable", "vegetable_herb"}:
            return "vegetable"
        if category == "fruit":
            return "fruit"
        if category == "drink_natural":
            return "drink_or_extra"
        if category in {"dessert_sweets", "sweet_spread"} or HealthyWeightGainRecommender._is_dirty_bulk_name(name):
            return "dessert"
        if category in {"fats_good", "healthy_fat", "healthy_fat_nuts"}:
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
            "image_source_type": "real_food_photo" if uses_real_photo else "placeholder",
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

        status = "valid"
        if total_kcal <= 0:
            status = "invalid"
            next_errors.append("Không có dữ liệu thực đơn.")
        elif kcal_diff_pct > 10 or protein_pct > 130 or fat_pct < 70 or carbs_pct > 130 or fat_pct > 130 or carbs_pct < 70:
            status = "major_adjustment"
        elif kcal_diff_pct > 5 or protein_pct > 110 or protein_pct < 90 or fat_pct < 80 or fat_pct > 120 or carbs_pct < 80 or carbs_pct > 120:
            status = "minor_adjustment"

        if status in ("minor_adjustment", "major_adjustment"):
            if protein_pct > 110:
                next_warnings.append(f"Protein đang cao hơn mục tiêu {round(total_protein - target_protein)}g. Bạn có thể giảm bớt món đạm hoặc đổi sang món giàu tinh bột/chất béo tốt.")
            elif protein_pct < 90:
                next_warnings.append("Bữa ăn trong ngày hơi thiếu đạm. Có thể ưu tiên thêm trứng, đậu hũ, cá hoặc thịt nạc ở lần tạo tiếp theo.")
            if fat_pct < 80:
                next_warnings.append("Thực đơn còn thiếu chất béo tốt. Có thể thêm bơ, hạt, trứng hoặc sữa nguyên kem.")
            elif fat_pct > 120:
                next_warnings.append(f"Fat cao hơn mục tiêu {round(total_fat - target_fat)}g.")
            if carbs_pct < 80:
                next_warnings.append(f"Carbs thấp hơn mục tiêu {round(target_carbs - total_carbs)}g.")
            elif carbs_pct > 120:
                next_warnings.append("Thực đơn hơi nhiều tinh bột. Có thể giảm khẩu phần tinh bột hoặc đổi sang món giàu chất béo tốt.")
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
        normalized = str(category or "").strip().lower()
        if normalized in {"starch_grain", "starch_tuber"}:
            return "grain"
        if normalized in {"protein_meat", "protein_seafood", "protein_plant"}:
            return "protein"
        if normalized == "healthy_fat_nuts":
            return "fat"
        if normalized == "vegetable_herb":
            return "vegetable"
        if normalized == "drink_natural":
            return "side"
        if normalized in {"tinh bá»™t", "tinh bột", "grain"}:
            return "grain"
        if normalized in {"Ä‘áº¡m", "đạm", "trá»©ng", "trứng", "Ä‘áº¡m thá»±c váº­t", "đạm thực vật", "meat", "egg", "plant_protein"}:
            return "protein"
        if normalized in {"rau cá»§", "rau củ", "vegetable"}:
            return "vegetable"
        if normalized in {"trÃ¡i cÃ¢y", "trái cây", "fruit"}:
            return "fruit"
        if normalized in {"cháº¥t bÃ©o tá»‘t", "chất béo tốt", "healthy_fat"}:
            return "fat"
        if normalized in {"sá»¯a", "sữa", "dairy"}:
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
                        "reason": "Được giữ trong thực đơn sau khi kiểm tra nhóm món, macro và khẩu phần.",
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
            main_problems = ["Không phát hiện lỗi nghiêm trọng sau khi chuẩn hóa tên món, khẩu phần và macro."]

        return {
            "eligibility_check": eligibility_check,
            "overall_assessment": {
                "score": score,
                "summary": (
                    "Thực đơn đủ điều kiện cho người thiếu cân cần tăng cân lành mạnh."
                    if eligibility_check.get("eligible")
                    else "Không đủ điều kiện sinh thực đơn."
                ),
                "main_problems": main_problems,
            },
            "detected_issues": issues,
            "fixed_menu": fixed_menu,
            "validation_rules_to_add": [
                "Tính BMI từ chiều cao/cân nặng và chặn BMI >= 18.5.",
                "Loại món có macro lệch nghiêm trọng so với kcal trước khi lập thực đơn.",
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

    def generate_recommendations(self, payload: RecommendationInput, db: Session, user: User) -> dict:
        eligibility_check = self._raise_if_not_eligible(payload)
        # 🟢 SAFE EXECUTION LAYER: wrap entire flow in try/except
        # so any unexpected crash returns a valid (fallback) response.
        try:
            return self._generate_recommendations_inner(payload, db, user, eligibility_check)
        except HTTPException:
            raise
        except ValueError as exc:
            logger.error("Recommendation engine failed: %s", exc)
            # Build a structured detail payload for frontend consumption and logs
            detail: dict = {
                "message": str(exc),
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

        exclude_food_ids: list[str] = []
        if previous_id is not None:
            repository.mark_meal_plan_status(user.id, previous_id, "needs_regeneration")
            if payload.excludePreviousItems:
                exclude_food_ids = repository.meal_plan_food_ids(user.id, previous_id)

        # Always re-fetch the user from DB to pick up the latest profile
        try:
            from app.repositories.user_repository import UserRepository
            saved_user = UserRepository(db).get_by_id(user.id)
        except Exception:
            saved_user = user
        saved_profile = getattr(saved_user, "profile", None)

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

        weight = payload.weight if payload.weight is not None else getattr(saved_profile, "weight_kg", None)
        height = payload.height if payload.height is not None else getattr(saved_profile, "height_cm", None)
        age = payload.age if payload.age is not None else getattr(saved_profile, "age", None)
        sex = payload.sex if payload.sex is not None else (
            getattr(saved_profile, "sex", None) or getattr(saved_profile, "gender", None)
        )
        activity = payload.activity or getattr(saved_profile, "activity_level", None) or "moderate"
        surplus = payload.surplus_kcal if payload.surplus_kcal is not None else getattr(saved_profile, "surplus_kcal", None)
        gain_speed = (
            payload.weight_gain_speed
            or payload.gain_speed
            or getattr(saved_profile, "weight_gain_speed", None)
        )
        diet_type = payload.diet_type or getattr(saved_profile, "diet_type", None)
        diet_style = payload.diet_style or diet_type or "balanced"
        budget_level = payload.budget_level or getattr(saved_profile, "budget_level", None) or "standard"
        meal_complexity = (
            payload.meal_complexity
            or meal_complexity_from_items(getattr(payload, "items_per_meal", None))
            or meal_complexity_from_items(getattr(saved_profile, "items_per_meal", None))
            or "balanced"
        )
        target_weight = (
            payload.target_weight
            if payload.target_weight is not None
            else getattr(saved_profile, "target_weight_kg", None)
        )
        favorite_foods = self._merge_profile_lists(
            getattr(saved_profile, "favorite_foods", None),
            payload.favorite_foods,
        )
        disliked_foods = self._merge_profile_lists(
            getattr(saved_profile, "disliked_foods", None),
            payload.disliked_foods,
        )
        disliked_food_groups = self._merge_profile_lists(
            getattr(saved_profile, "disliked_food_groups", None),
            payload.disliked_food_groups,
        )

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

        random_seed = payload.random_seed or payload.randomSeed or int(datetime.now(timezone.utc).timestamp())
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
            items_per_meal=getattr(payload, "items_per_meal", None) or getattr(saved_profile, "items_per_meal", None),
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
            random_seed=random_seed,
            exclude_food_ids=exclude_food_ids,
            exclude_meal_plan_id=previous_id,
            macro_backtracking_attempts=20,
            save_user_data=True,
        )
        return self.generate_recommendations(request_payload, db, saved_user or user)

    def _generate_recommendations_inner(
        self,
        payload: RecommendationInput,
        db: Session,
        user: User,
        eligibility_check: dict,
    ) -> dict:
        # Clear taxonomy cache to avoid stale data from previous requests
        clear_taxonomy_cache()
        recommender = self._build_recommender_from_sql(db)
        profile_goal, profile_surplus = self._profile_goal_and_surplus(payload)

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
        saved_profile = getattr(user, "profile", None)
        disliked_foods = self._merge_profile_lists(
            getattr(saved_profile, "disliked_foods", None),
            payload.disliked_foods,
        )
        disliked_foods = _expand_food_terms(disliked_foods)
        disliked_food_groups = self._merge_profile_lists(
            getattr(saved_profile, "disliked_food_groups", None),
            payload.disliked_food_groups,
        )
        favorite_foods = self._merge_profile_lists(
            getattr(saved_profile, "favorite_foods", None),
            payload.favorite_foods,
        )
        profile = UserProfile(
            weight_kg=payload.weight,
            height_cm=payload.height,
            activity_level=payload.activity,
            age=payload.age,
            sex=payload.sex,
            goal=profile_goal,
            surplus_kcal=profile_surplus,
            weight_gain_speed=payload.weight_gain_speed or payload.gain_speed,
            disliked_foods=tuple(disliked_foods),
            disliked_food_groups=tuple(disliked_food_groups),
        )

        history_preferences = self._train_category_preferences_from_sql(db, user_id=user.id)
        current_preferences = dict(history_preferences)
        for category in payload.preferred_categories:
            normalized = category.strip().lower()
            if normalized:
                current_preferences[normalized] = current_preferences.get(normalized, 0.0) + 1.0
        for category in payload.excluded_categories:
            normalized = category.strip().lower()
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
        ranked = recommender.recommend(
            profile=profile,
            top_n=candidate_top_n,
            preferred_categories=payload.preferred_categories,
            excluded_categories=payload.excluded_categories,
            category_preferences=current_preferences,
        )
        ranked = self._apply_diet_and_budget_preferences(ranked, payload)
        ranked = self.filterFoodsByDietType(
            ranked,
            payload.diet_type or payload.diet_style,
            min_items=meal_slots * 3,
        )

        if disliked_foods:
            disliked_mask = ranked.apply(
                lambda row: _row_matches_terms(row, disliked_foods),
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

        interaction_repository = InteractionRepository(db)
        favorite_food_ids = interaction_repository.favorite_food_ids(user.id)
        user_ratings = interaction_repository.ratings_by_user(user.id)

        # Boost favorites
        if favorite_foods:
            fav_terms = [f.strip().lower() for f in favorite_foods if f.strip()]
            if fav_terms:
                fav_boost = ranked.apply(
                    lambda row: 0.16 if _row_matches_terms(row, fav_terms) else 0.0,
                    axis=1,
                )
                ranked = ranked.copy()
                ranked["score"] = ranked["score"] + fav_boost

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

        # Calculate new target using NutritionCalculationService
        calculated_targets = calculateNutritionTargets(profile)
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
        
        # Map to old target format for backwards compatibility with recommender (temporary)
        target = {
            "calories": nutrition_target["calorie_target"],
            "protein": nutrition_target["protein_g"],
            "fat": nutrition_target["fat_g"],
            "carbs": nutrition_target["carbs_g"],
            "bmi": profile_summary["bmi"],
            "bmr": nutrition_target["bmr"],
            "tdee": nutrition_target["tdee"],
            "maintenance_kcal": nutrition_target["tdee"],
            "bmi_status": profile_summary["bmi_status"],
            "medical_warning": str(profile_summary["medical_warning"]) if profile_summary.get("medical_warning") else None
        }
        
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

        if payload.exclude_food_ids:
            excluded_ids = {str(food_id) for food_id in payload.exclude_food_ids if str(food_id).strip()}
            if excluded_ids:
                filtered_ranked = ranked[~ranked["food_id"].astype(str).isin(excluded_ids)].copy()
                if len(filtered_ranked) >= max(meal_slots * 3, 20):
                    ranked = filtered_ranked
                else:
                    ranked = ranked.copy()
                    ranked["score"] = ranked["score"] - ranked["food_id"].astype(str).isin(excluded_ids).astype(float) * 0.5

        # --- Pre-filter Outliers (Trứng Cá + Seafood Carbs > 2) ---
        outlier_mask = ranked.apply(
            lambda row: "trứng cá" in str(row.get("name", "")).lower() and str(row.get("clean_category", str(row.get("category", "")))).lower() in ["seafood", "protein_seafood", "hải sản"] and float(row.get("Carbs(g)", row.get("carbs", 0))) > 2,
            axis=1
        )
        ranked = ranked[~outlier_mask].copy()

        # Retry logic: try multiple seeded variants and keep the closest kcal plan.
        best_meal_plan = None
        best_delta = float("inf")
        best_totals: dict[str, float] | None = None
        max_attempts = max(1, min(int(payload.macro_backtracking_attempts or 20), 20))
        seed_base = payload.random_seed or int(datetime.now(timezone.utc).timestamp())
        
        for attempt in range(max_attempts):
            attempt_ranked = ranked.copy()
            if attempt > 0:
                rng = random.Random(seed_base + attempt)
                attempt_ranked["_seed_jitter"] = [rng.uniform(-0.035, 0.035) for _ in range(len(attempt_ranked))]
                attempt_ranked["score"] = attempt_ranked["score"].astype(float) + attempt_ranked["_seed_jitter"]
                attempt_ranked = attempt_ranked.sort_values("score", ascending=False).drop(columns=["_seed_jitter"])

            meal_plan = self.pickBalancedMeal(attempt_ranked, meal_structure=meal_structure, target=target)
            
            plan_totals = self._plan_totals_from_frames(meal_plan)
            temp_kcal = plan_totals["kcal"]
                    
            delta_pct = abs(temp_kcal - target_kcal) / target_kcal if target_kcal > 0 else 0
            
            if delta_pct < best_delta:
                best_delta = delta_pct
                best_meal_plan = meal_plan
                best_totals = plan_totals
                
            if delta_pct <= 0.05:
                break
                
            # If failed, penalize selected items slightly to try different combinations
            selected_ids = []
            for meal_type, meal_df in meal_plan.items():
                selected_ids.extend(meal_df["food_id"].tolist())
                
            penalty = ranked["food_id"].isin(selected_ids)
            ranked.loc[penalty, "score"] -= 0.15 + (attempt * 0.01)
            ranked = ranked.sort_values("score", ascending=False)
            
        meal_plan = best_meal_plan
        if meal_plan is None:
            detail = {
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
            logger.error("Meal plan generation failed: %s", detail)
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)

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

        target_kcal = float(nutrition_target["calorie_target"])
        min_kcal = target_kcal * 0.95 if target_kcal > 0 else 0.0
        max_kcal = target_kcal * 1.05 if target_kcal > 0 else 0.0
        preserved_item_count_note = False

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
                    category = str(item.get("category") or "").lower()
                    optional = role in {"extra", "fat", "side", "drink", "drink_or_extra"} or category in {"dairy", "healthy_fat_nuts", "fats_good", "healthy_fat", "fruit"}
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

        def _replace_or_fill_high_energy_items(target_add_kcal: float, max_changes: int = 3) -> int:
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
                category = str(row.get("clean_category", row.get("category", ""))).lower()
                name_text = _normalize_search_text(row.get("name", ""))
                energy_fat_terms = ("avocado", "bo", "nuts", "hat", "olive", "oil", "dau", "milk", "sua", "yogurt", "sua chua", "egg", "trung", "salmon", "ca hoi")
                is_good_energy = category in {"healthy_fat_nuts", "dairy", "egg", "protein_seafood", "starch_grain", "starch_tuber"} or any(term in name_text for term in energy_fat_terms)
                if not is_good_energy:
                    continue
                kcal_serving = float(row.get("kcal_per_serving_clean") or row.get("calories_raw") or 0.0)
                kcal_100g = float(row.get("kcal_per_100g_clean") or 0.0)
                if kcal_serving <= 150 and kcal_100g <= 150:
                    continue
                candidate_item = self._to_food_item_payload(row)

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
                        role = str(current.get("meal_role") or current.get("culinary_role") or "").lower()
                        category_current = str(current.get("category") or "").lower()
                        optional = role in {"extra", "fat", "side", "drink", "drink_or_extra"} or category_current in {"dairy", "healthy_fat_nuts", "fats_good", "healthy_fat", "fruit"}
                        if not optional:
                            continue
                        gain = float(candidate_item.get("calories") or 0.0) - float(current.get("calories") or current.get("kcal") or 0.0)
                        if gain > best_gain:
                            best_gain = gain
                            target_meal = meal
                            replace_index = idx
                if target_meal is None or best_gain <= 25:
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
        if target_protein > 0 and total_protein > target_protein * 1.10:
            scale_p = (target_protein * 1.05) / total_protein
            for meal in meal_plan_payload:
                for item in meal.get("items", []):
                    cat = str(item.get("category", "")).lower()
                    if "protein" in cat or "meat" in cat or "seafood" in cat or "egg" in cat:
                        q = float(item.get("quantity_g") or item.get("serving_grams") or 100)
                        next_q = q * scale_p
                        min_q, max_q = _serving_limits(item.get("category", ""), item.get("name", ""))
                        if min_q is not None and max_q is not None:
                            next_q = min(max(next_q, min_q), max_q)
                        item_scale = next_q / q if q > 0 else scale_p
                        item["quantity_g"] = next_q
                        item["serving_grams"] = next_q
                        _refresh_item_serving_display(item)
                        for k in ["calories", "kcal", "protein", "fat", "carbs"]:
                            item[k] = float(item.get(k) or 0.0) * item_scale
            meal_items_for_db, total_kcal, total_protein, total_fat, total_carbs = _recompute_plan_totals()

        target_fat = float(nutrition_target.get("fat_g") or nutrition_target.get("fat_target") or nutrition_target.get("fat") or 0.0)
        if target_fat > 0 and total_fat < target_fat * 0.80:
            added_items = _replace_or_fill_high_energy_items(target_add_kcal=min(max(target_kcal * 0.08, 120.0), 320.0), max_changes=2)
            logger.warning("DEBUG_FAT_LOW replaced_high_energy_items=%s", added_items)
            meal_items_for_db, total_kcal, total_protein, total_fat, total_carbs = _recompute_plan_totals()

        delta_pct = abs(total_kcal - target_kcal) / target_kcal if target_kcal > 0 else 0.0

        errors = []
        warnings = []
            
        seafood_count = 0
        food_ids = set()
        for meal in meal_plan_payload:
            for item in meal["items"]:
                if item["food_id"] in food_ids:
                    errors.append(f"Trùng lặp món ăn trong ngày: {item['name']}")
                food_ids.add(item["food_id"])
                cat_lower = item.get("category", "").lower()
                name_lower = item.get("name", "").lower()
                if cat_lower in ["seafood", "hải sản", "protein_seafood"]:
                    seafood_count += 1
                    if "trứng cá" in name_lower and float(item.get("carbs", 0)) > 2:
                        errors.append(f"Món '{item['name']}' có dữ liệu carbs bất thường với nhóm Hải sản.")
                    
        if seafood_count > 2:
            errors.append("Hải sản xuất hiện quá 2 lần/ngày. (Vượt ngưỡng an toàn)")
            
        if profile_summary.get("medical_warning"):
            warnings.append("BMI < 16: Thực đơn chỉ mang tính tham khảo.")
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
        )
        is_valid = validation_result["is_valid"]
        validation_result["message"] = (
            "Thực đơn đạt mục tiêu." if is_valid else "Thực đơn chưa đạt mục tiêu, vui lòng tạo lại."
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
            "profile_summary": profile_summary,
            "nutrition_target": nutrition_target,
            "meal_plan": {
                "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "total_kcal": round(total_kcal),
                "total_protein_g": round(total_protein),
                "total_fat_g": round(total_fat),
                "total_carbs_g": round(total_carbs),
                "status": validation_result["status"],
                "meals": meal_plan_payload
            },
            "validation": validation_result,
            "target": target
        }

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

        if payload.save_user_data:
            UserRepository(db).upsert_profile(
                user.id,
                {
                    "weight_kg": payload.weight,
                    "height_cm": payload.height,
                    "activity_level": payload.activity,
                    "age": payload.age,
                    "sex": payload.sex,
                    "surplus_kcal": payload.surplus_kcal,
                    "favorite_foods": ", ".join(favorite_foods) if favorite_foods else None,
                    "disliked_foods": self._serialize_profile_list(disliked_foods),
                    "disliked_food_groups": self._serialize_profile_list(disliked_food_groups),
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
