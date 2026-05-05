from __future__ import annotations

import logging
import traceback
from datetime import datetime, timedelta, timezone
from functools import lru_cache

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
        gain_speed = profile.get("weight_gain_speed", profile.get("gain_speed"))
        profile = UserProfile(
            weight_kg=float(profile.get("weight_kg", profile.get("weight"))),
            height_cm=float(profile.get("height_cm", profile.get("height"))),
            activity_level=str(profile.get("activity_level", profile.get("activity", "moderate"))),
            age=profile.get("age"),
            sex=profile.get("sex"),
            goal=str(profile.get("goal", "gain")),
            surplus_kcal=profile.get("surplus_kcal"),
            weight_gain_speed=None if gain_speed is None else str(gain_speed),
            disliked_foods=_coerce_profile_terms(profile.get("disliked_foods")),
            disliked_food_groups=_coerce_profile_terms(profile.get("disliked_food_groups")),
        )
    return HealthyWeightGainRecommender("", "")._estimate_target_nutrition(profile)


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


from app.core.config import settings
from app.models.entities import Food, FoodRating, MealPlanItem, RecommendationRequest, User, UserFavoriteFood
from app.repositories.interaction_repository import InteractionRepository
from app.repositories.recommendation_repository import RecommendationRepository
from app.repositories.user_repository import UserRepository
from app.views.schemas import RecommendationInput


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
        if bmi >= 18.5:
            return {
                "bmi": round(bmi, 2),
                "weight_status": weight_status,
                "eligible": False,
                "reason": "Hệ thống NutriGain hiện chỉ sinh thực đơn cho người thiếu cân (BMI < 18.5).",
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
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
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
                },
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
            "slow": 300.0,
            "nhe": 300.0,
            "medium": 400.0,
            "moderate": 400.0,
            "vua": 400.0,
            "fast": 500.0,
            "strong": 500.0,
            "nhanh": 500.0,
        }
        gain_surplus = payload.surplus_kcal
        if gain_surplus is None and speed in speed_surplus:
            gain_surplus = speed_surplus[speed]
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
        category = next_df["category"].astype(str).str.lower()
        names = next_df["name"].astype(str).str.lower()

        if diet_style in {"vegetarian", "chay"}:
            next_df = next_df[category != "meat"].copy()
            category = next_df["category"].astype(str).str.lower()
            names = next_df["name"].astype(str).str.lower()
        elif diet_style in {"vegan", "thuần chay", "thuan chay"}:
            next_df = next_df[~category.isin({"meat", "egg", "dairy"})].copy()
            category = next_df["category"].astype(str).str.lower()
            names = next_df["name"].astype(str).str.lower()

        if next_df.empty:
            return next_df

        if diet_style in {"low_carb", "low-carb", "keto"}:
            low_carb_boost = category.isin({"meat", "egg", "dairy", "healthy_fat", "plant_protein"}).astype(float)
            carb_penalty = category.isin({"grain", "fruit"}).astype(float)
            next_df["score"] = next_df["score"] + 0.08 * low_carb_boost - 0.12 * carb_penalty
        elif any(term in normalized_diet_style for term in EAT_CLEAN_DIET_TERMS):
            clean_boost = next_df.apply(HealthyWeightGainRecommender._food_quality_score, axis=1)
            next_df["score"] = next_df["score"] + 0.04 * clean_boost

        if budget_level in {"low", "saving", "cheap", "tiết kiệm", "tiet kiem"}:
            affordable_terms = ("rice", "oat", "egg", "tofu", "bean", "lentil", "banana", "potato", "milk")
            premium_terms = ("salmon", "tuna", "shrimp", "almond", "walnut", "cheese", "avocado")
            affordable_boost = names.apply(lambda text: 1.0 if any(term in text for term in affordable_terms) else 0.0)
            premium_penalty = names.apply(lambda text: 1.0 if any(term in text for term in premium_terms) else 0.0)
            next_df["score"] = next_df["score"] + 0.08 * affordable_boost - 0.08 * premium_penalty
        elif budget_level in {"high", "premium"}:
            premium_terms = ("salmon", "tuna", "avocado", "almond", "walnut", "yogurt")
            premium_boost = names.apply(lambda text: 1.0 if any(term in text for term in premium_terms) else 0.0)
            next_df["score"] = next_df["score"] + 0.04 * premium_boost

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
        return HealthyWeightGainRecommender.build_daily_meal_plan(
            ranked,
            meal_structure=meal_structure,
            target_calories=float(target["calories"]),
            target_nutrition=target,
        )

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
        grams = row.get("serving_grams")
        grams_value = None if pd.isna(grams) else float(grams)
        rounded_grams = int(round(grams_value)) if grams_value else 0
        lower = f"{display_name} {row.get('name', '')}".lower()
        category = str(row.get("category", "")).strip().lower()

        if rounded_grams <= 0:
            return "Không đủ dữ liệu khẩu phần"
        if any(term in lower for term in ("peanut butter", "bơ đậu phộng")):
            spoons = max(1, round(rounded_grams / 16))
            return f"{spoons} muỗng canh (~{rounded_grams}g)"
        if any(term in lower for term in ("peanut", "almond", "walnut", "đậu phộng")):
            return f"1 nắm nhỏ (~{rounded_grams}g)"
        if category == "dairy" or any(term in lower for term in ("milk", "yogurt", "sữa")):
            return f"1 ly/hộp (~{rounded_grams}g)"
        if category == "grain" or any(term in lower for term in ("rice", "oat", "potato", "bread", "cơm", "khoai")):
            return f"1 chén/bát hoặc 1 phần nhỏ (~{rounded_grams}g)"
        if category in {"meat", "egg", "plant_protein"}:
            return f"1 phần đạm (~{rounded_grams}g)"
        if category in {"vegetable", "fruit"}:
            return f"1 phần (~{rounded_grams}g)"
        return f"~{rounded_grams}g"

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
            "image_badge": None if uses_real_photo else "Ảnh minh họa",
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
        except Exception as exc:
            logger.error("Recommendation engine crashed: %s", exc)
            logger.error(traceback.format_exc())
            # Compute fallback target nutrition inline (same formula as _estimate_target_nutrition)
            _w = payload.weight
            _h = payload.height
            _age = payload.age or 25
            _sex = (payload.sex or "male").strip().lower()
            _act = {"sedentary": 1.2, "light": 1.375, "moderate": 1.55, "active": 1.725, "very_active": 1.9}
            _af = _act.get(payload.activity, 1.55)
            if _sex == "male":
                _bmr = 10 * _w + 6.25 * _h - 5 * _age + 5
            else:
                _bmr = 10 * _w + 6.25 * _h - 5 * _age - 161
            _maint = _bmr * _af
            _goal, _surplus_value = self._profile_goal_and_surplus(payload)
            if _goal == "lose":
                _surplus = -abs(_surplus_value or 350.0)
            elif _goal == "maintain":
                _surplus = 0.0
            else:
                _surplus = _surplus_value if _surplus_value is not None else 300.0
            _tcal = _maint + _surplus
            if _goal != "gain" and _age >= 18:
                _tcal = max(_tcal, 1200.0)
            if _goal == "gain":
                _tcal = max(_tcal, _maint)
            _bmi = _w / ((_h / 100.0) ** 2)
            _protein_per_kg = 1.8 if _bmi < 17.5 else 1.7
            _tpro = min(max(1.6 * _w, _protein_per_kg * _w), 2.2 * _w)
            _tfat = max(0.9 * _w, 0.30 * _tcal / 9.0)
            _tcarb = max((_tcal - _tpro * 4 - _tfat * 9) / 4, 0.0)
            if _bmi < 16:
                _bmi_status = "Suy dinh dưỡng độ 3"
                _medical_warning = "BMI đang rất thấp. Nên tham khảo bác sĩ/chuyên gia dinh dưỡng trước khi tăng cân."
            elif _bmi < 17:
                _bmi_status = "Suy dinh dưỡng độ 2"
                _medical_warning = "BMI đang thấp. Nên theo dõi sức khỏe và tham khảo chuyên gia nếu có triệu chứng bất thường."
            elif _bmi < 18.5:
                _bmi_status = "Gầy"
                _medical_warning = None
            else:
                _bmi_status = "Bình thường"
                _medical_warning = None
            fallback_target = {
                "calories": _tcal, "protein": _tpro, "fat": _tfat, "carbs": _tcarb,
                "bmi": _bmi, "bmr": _bmr, "tdee": _maint, "maintenance_kcal": _maint,
                "bmi_status": _bmi_status, "medical_warning": _medical_warning,
            }
            profile_goal, profile_surplus = self._profile_goal_and_surplus(payload)
            fallback_target = calculateNutritionTargets(
                UserProfile(
                    weight_kg=payload.weight,
                    height_cm=payload.height,
                    activity_level=payload.activity,
                    age=payload.age,
                    sex=payload.sex,
                    goal=profile_goal,
                    surplus_kcal=profile_surplus,
                    weight_gain_speed=payload.weight_gain_speed or payload.gain_speed,
                )
            )
            fallback_plan = HealthyWeightGainRecommender._build_fallback_meal_plan(fallback_target)
            fallback_payload: dict[str, list[dict]] = {}
            for meal_type, meal_df in fallback_plan.items():
                meal_list = []
                for _, row in meal_df.iterrows():
                    meal_list.append(self._to_food_item_payload(row))
                fallback_payload[meal_type] = meal_list
            audit_payload = self._audit_generated_menu(fallback_payload, eligibility_check)
            return {
                **audit_payload,
                "target": fallback_target,
                "top_recommendations": [],
                "meal_plan": fallback_payload,
                "evaluation": {
                    "target_calories": float(fallback_target.get("calories", 2000)),
                    "recommended_calories": 0.0,
                    "signed_error": 0.0,
                    "absolute_error": 0.0,
                    "relative_error_pct": 0.0,
                    "within_10pct": False,
                    "macro_mae_relative_pct": 0.0,
                    "macros_within_20pct_ratio": 0.0,
                    "preference_precision_pct": None,
                    "meal_calorie_ratio_targets": dict(DEFAULT_MEAL_CALORIE_RATIOS),
                    "meal_macro_distribution": {},
                    "validation": {
                        "is_valid": False,
                        "no_empty_meals": False,
                        "calorie_within_15pct": False,
                        "calorie_error_pct": 100.0,
                        "protein_within_25pct": False,
                        "protein_error_pct": 100.0,
                        "fat_within_25pct": False,
                        "fat_error_pct": 100.0,
                        "carbs_within_25pct": False,
                        "carbs_error_pct": 100.0,
                    },
                },
            }

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
        saved_profile = getattr(user, "profile", None)
        disliked_foods = self._merge_profile_lists(
            getattr(saved_profile, "disliked_foods", None),
            payload.disliked_foods,
        )
        disliked_food_groups = self._merge_profile_lists(
            getattr(saved_profile, "disliked_food_groups", None),
            payload.disliked_food_groups,
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

        meal_structure = HealthyWeightGainRecommender.meal_structure_for_complexity(payload.meal_complexity)
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
        if payload.favorites:
            fav_terms = [f.strip().lower() for f in payload.favorites if f.strip()]
            if fav_terms:
                fav_boost = ranked.apply(
                    lambda row: 0.12 if _row_matches_terms(row, fav_terms) else 0.0,
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

        target = recommender._estimate_target_nutrition(profile)
        meal_plan = self.pickBalancedMeal(ranked, meal_structure=meal_structure, target=target)

        meal_plan_totals = {
            nutrient: sum(float(df[nutrient].sum()) for df in meal_plan.values())
            for nutrient in ("calories_raw", "protein_raw", "fat_raw", "carbs_raw")
        }
        recommended_calories = float(meal_plan_totals["calories_raw"])
        absolute_error = abs(recommended_calories - float(target["calories"]))
        relative_error_pct = (absolute_error / float(target["calories"])) * 100.0 if target["calories"] else 0.0
        min_calories = float(target["calories"]) * 0.85
        meal_calories = {
            meal: float(df["calories_raw"].sum()) if not df.empty else 0.0
            for meal, df in meal_plan.items()
        }
        low_main_meals = [
            meal for meal in ("breakfast", "lunch", "dinner")
            if meal in meal_calories and meal_calories[meal] < 450.0
        ]
        protein_target = float(target["protein"])
        protein_error_pct = (
            abs(float(meal_plan_totals["protein_raw"]) - protein_target) / protein_target * 100.0
            if protein_target > 0
            else 0.0
        )
        fat_target = float(target["fat"])
        carbs_target = float(target["carbs"])
        actual_fat = float(meal_plan_totals["fat_raw"])
        actual_carbs = float(meal_plan_totals["carbs_raw"])
        fat_error_pct = abs(actual_fat - fat_target) / fat_target * 100.0 if fat_target > 0 else 0.0
        carbs_error_pct = abs(actual_carbs - carbs_target) / carbs_target * 100.0 if carbs_target > 0 else 0.0
        validation = {
            "is_valid": bool(meal_plan) and all(not df.empty for df in meal_plan.values()),
            "no_empty_meals": all(not df.empty for df in meal_plan.values()),
            "calorie_within_15pct": relative_error_pct <= 15.0 and recommended_calories >= min_calories,
            "calorie_error_pct": float(relative_error_pct),
            "protein_within_25pct": float(meal_plan_totals["protein_raw"]) >= protein_target * 0.8,
            "protein_error_pct": float(protein_error_pct),
            "fat_within_25pct": actual_fat >= fat_target * 0.8,
            "fat_error_pct": float(fat_error_pct),
            "carbs_within_25pct": actual_carbs <= carbs_target * 1.25 if carbs_target > 0 else True,
            "carbs_error_pct": float(carbs_error_pct),
            "min_calories": min_calories,
            "low_main_meals": low_main_meals,
        }
        validation["is_valid"] = bool(
            validation["is_valid"]
            and validation["calorie_within_15pct"]
            and validation["protein_within_25pct"]
            and validation["fat_within_25pct"]
            and validation["carbs_within_25pct"]
            and not low_main_meals
        )

        evaluation = recommender.evaluate_calorie_alignment(meal_plan, target["calories"])
        macro_metrics = recommender.evaluate_macro_alignment(meal_plan, target)
        meal_distribution = recommender.evaluate_meal_distribution(
            meal_plan=meal_plan,
            target_nutrition=target,
            meal_ratios=DEFAULT_MEAL_CALORIE_RATIOS,
        )
        preference_precision = recommender.evaluate_preference_precision(
            ranked,
            payload.preferred_categories,
            k=payload.top_n,
        )

        top_recommendations = [
            self._to_food_item_payload(row)
            for _, row in ranked.head(payload.top_n).iterrows()
        ]

        meal_plan_payload: dict[str, list[dict]] = {}
        meal_items_for_db: list[dict] = []
        for meal_type, meal_df in meal_plan.items():
            meal_list = []
            for _, row in meal_df.iterrows():
                item = self._to_food_item_payload(row)
                meal_list.append(item)
                meal_items_for_db.append(
                    {
                        "meal_type": meal_type,
                        "food_id": item["food_id"],
                        "name": item["name"],
                        "category": item["category"],
                        "serving_grams": item.get("serving_grams"),
                        "calories": item["calories"],
                        "protein": item["protein"],
                        "fat": item["fat"],
                        "carbs": item["carbs"],
                        "score": item["score"],
                    }
                )
            meal_plan_payload[meal_type] = meal_list

        preference_precision_pct = None
        if preference_precision is not None:
            preference_precision_pct = float(preference_precision * 100.0)

        audit_payload = self._audit_generated_menu(meal_plan_payload, eligibility_check)
        response_payload = {
            **audit_payload,
            "target": {
                "bmi": float(target["bmi"]),
                "bmr": float(target["bmr"]),
                "tdee": float(target["tdee"]),
                "maintenance_kcal": float(target["maintenance_kcal"]),
                "calories": float(target["calories"]),
                "protein": float(target["protein"]),
                "fat": float(target["fat"]),
                "carbs": float(target["carbs"]),
                "bmi_status": target.get("bmi_status"),
                "medical_warning": target.get("medical_warning"),
            },
            "top_recommendations": top_recommendations,
            "meal_plan": meal_plan_payload,
            "evaluation": {
                "target_calories": float(evaluation["target_calories"]),
                "recommended_calories": float(evaluation["recommended_calories"]),
                "signed_error": float(evaluation["signed_error"]),
                "absolute_error": float(evaluation["absolute_error"]),
                "relative_error_pct": float(evaluation["relative_error_pct"]),
                "within_10pct": bool(evaluation["within_10pct"]),
                "macro_mae_relative_pct": float(macro_metrics["macro_mae_relative_pct"]),
                "macros_within_20pct_ratio": float(macro_metrics["macros_within_20pct_ratio"]),
                "preference_precision_pct": preference_precision_pct,
                "meal_calorie_ratio_targets": {
                    key: float(value) for key, value in DEFAULT_MEAL_CALORIE_RATIOS.items()
                },
                "meal_macro_distribution": meal_distribution,
                "validation": {
                    "is_valid": bool(validation.get("is_valid", False)),
                    "no_empty_meals": bool(validation.get("no_empty_meals", False)),
                    "calorie_within_15pct": bool(validation.get("calorie_within_15pct", False)),
                    "calorie_error_pct": float(validation.get("calorie_error_pct", 0.0)),
                    "protein_within_25pct": bool(validation.get("protein_within_25pct", False)),
                    "protein_error_pct": float(validation.get("protein_error_pct", 0.0)),
                    "fat_within_25pct": bool(validation.get("fat_within_25pct", False)),
                    "fat_error_pct": float(validation.get("fat_error_pct", 0.0)),
                    "carbs_within_25pct": bool(validation.get("carbs_within_25pct", False)),
                    "carbs_error_pct": float(validation.get("carbs_error_pct", 0.0)),
                    "min_calories": float(validation.get("min_calories", 0.0)),
                    "low_main_meals": list(validation.get("low_main_meals", [])),
                },
            },
        }

        repository = RecommendationRepository(db)
        repository.create_request_with_items(
            request_payload={
                "weight_kg": payload.weight,
                "height_cm": payload.height,
                "user_id": user.id,
                "activity_level": payload.activity,
                "age": payload.age,
                "sex": payload.sex,
                "surplus_kcal": payload.surplus_kcal,
                "preferred_categories": ";".join(payload.preferred_categories + payload.favorites),
                "excluded_categories": ";".join(payload.excluded_categories + payload.allergens),
                "target_calories": response_payload["evaluation"]["target_calories"],
                "bmr": response_payload["target"]["bmr"],
                "tdee": response_payload["target"]["tdee"],
                "recommended_calories": response_payload["evaluation"]["recommended_calories"],
                "absolute_error": response_payload["evaluation"]["absolute_error"],
                "relative_error_pct": response_payload["evaluation"]["relative_error_pct"],
                "precision_pct": preference_precision_pct,
            },
            meal_items=meal_items_for_db,
        )

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
