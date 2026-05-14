"""Healthy weight-gain food recommender.

This module uses the scaled dataset for similarity computation and the raw
dataset for human-readable output.
"""

from __future__ import annotations

import argparse
import sys
import unicodedata
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence
import joblib

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity


FEATURE_COLUMNS = ["calories", "protein", "fat", "carbs"]
USER_HISTORY_COLUMNS = [
    "timestamp",
    "weight_kg",
    "height_cm",
    "activity_level",
    "age",
    "sex",
    "goal",
    "surplus_kcal",
    "preferred_categories",
    "excluded_categories",
]


def _console_safe(value: object) -> str:
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    return str(value).encode(encoding, errors="replace").decode(encoding, errors="replace")


def is_non_vegetarian_food(row: pd.Series | dict) -> bool:
    import unicodedata

    def strip_accents(s):
        return "".join(c for c in unicodedata.normalize("NFD", str(s or "")) if unicodedata.category(c) != "Mn").replace("đ", "d").replace("Đ", "D")

    cat_lower = str(row.get("category", "")).lower()
    clean_cat_lower = str(row.get("clean_category", "")).lower()
    group_lower = str(row.get("food_group", "")).lower()

    if any(c in {"protein_meat", "protein_seafood", "meat", "seafood", "đạm · hải sản", "đạm · thịt", "egg", "trứng"} for c in [cat_lower, clean_cat_lower, group_lower]):
        return True

    parts = [
        str(row.get("name", "")),
        str(row.get("name_en", "")),
        str(row.get("display_name_en", "")),
        str(row.get("name_vi", "")),
        str(row.get("category", "")),
        str(row.get("clean_category", "")),
        str(row.get("food_group", "")),
        str(row.get("tags", "")),
        str(row.get("ingredients", "")),
    ]
    raw_text = " ".join(parts).lower()
    norm_text = strip_accents(raw_text).lower()

    plant_milks = [
        "sữa đậu", "sữa hạnh nhân", "sữa dừa", "sữa bắp", "sữa hạt", "sữa gạo", "sữa yến mạch", "sữa thực vật", "sữa chua đậu",
        "sua dau", "sua hanh nhan", "sua dua", "sua bap", "sua hat", "sua gao", "sua yen mach", "sua thuc vat", "sua chua dau",
        "soy milk", "almond milk", "coconut milk", "oat milk", "rice milk", "nut milk", "plant milk", "soy yogurt", "tofu yogurt",
    ]
    is_plant_milk = any(pm in raw_text or pm in norm_text for pm in plant_milks)

    if any(c in {"dairy", "sữa"} for c in [cat_lower, clean_cat_lower, group_lower]) and not is_plant_milk:
        return True

    padded_raw = f" {raw_text} "
    padded_norm = f" {norm_text} "

    standalone_terms = [
        "heo", "lon", "ga", "vit", "ca", "tom", "cua", "muc", "ngheu", "so", "oc", "luon", "suon", "gio", "pate", "thit",
        "beef", "pork", "chicken", "duck", "fish", "shrimp", "crab", "squid", "meat", "steak", "sausage", "ham", "bacon", "tuna", "salmon",
        "cá", "bò", "gà", "vịt", "heo", "lợn", "tôm", "cua", "mực", "ốc", "sò", "nghêu", "lươn", "sườn", "giò",
        "trứng", "egg", "yolk", "mozzarella",
    ]
    for term in standalone_terms:
        if f" {term} " in padded_norm or f" {term} " in padded_raw:
            return True

    multi_terms = [
        "thit bo", "thit heo", "thit lon", "thit ga", "thit vit", "hai san", "bit tet", "mortadella", "xuc xich", "cha lua", "seafood",
        "thịt bò", "thịt heo", "thịt lợn", "thịt gà", "thịt vịt", "hải sản", "bít tết", "xúc xích", "chả lụa",
        "long do trung", "long trang trung", "lòng đỏ trứng", "lòng trắng trứng",
    ]
    for term in multi_terms:
        if term in norm_text or term in raw_text:
            return True

    if not is_plant_milk:
        dairy_terms = ["sữa", "sua", "milk", "cheese", "yogurt", "pho mai", "phô mai", "sữa chua", "sua chua", "dairy", "cream", "mozzarella"]
        for term in dairy_terms:
            if f" {term} " in padded_norm or f" {term} " in padded_raw or term in norm_text or term in raw_text:
                return True

    return False


DEFAULT_ACTIVITY_FACTORS = {
    "default": 1.3,
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "very_active": 1.9,
}
DEFAULT_MEAL_STRUCTURE = {
    "breakfast": 4,
    "lunch": 4,
    "dinner": 4,
}
MEAL_STRUCTURE_PRESETS = {
    "simple": {"breakfast": 3, "lunch": 3, "dinner": 3},
    "balanced": {"breakfast": 4, "lunch": 4, "dinner": 4},
    "full": {"breakfast": 5, "lunch": 5, "dinner": 5},
}
DEFAULT_MEAL_CALORIE_RATIOS = {
    "breakfast": 0.30,
    "lunch": 0.35,
    "dinner": 0.35,
}
BLOCKED_NAME_TERMS = (
    "olive garden",
    "carrabba",
    "mcdonald",
    "burger king",
    "kfc",
    "subway",
    "taco bell",
    "wendy's",
    "chick-fil-a",
    "pizza hut",
    "domino's",
    "egg white",
    "lean only",
    # exotic / wild meats not suitable for everyday nutrition
    "bear",
    "gau",
    "thit gau",
    "thịt gấu",
    "wild boar",
    "venison",
    "bison",
    "alligator",
    "crocodile",
    "ostrich",
    "kangaroo",
    "snake",
    "frog legs",
    "ech",
    "rắn",
    "ran",
    "thu rung",
    "thú rừng",
)
GENERIC_MENU_NAMES = {
    "ca",
    "banh",
    "rau",
    "do an nhanh",
    "do uong",
    "mon trang mieng",
    "nuoc sot",
    "thuc pham",
}
DIRTY_BULK_NAME_TERMS = (
    "ice cream",
    "ice creams",
    "pudding",
    "puddings",
    "pie",
    "pies",
    "pastry",
    "pastries",
    "muffin",
    "muffins",
    "doughnut",
    "doughnuts",
    "donut",
    "donuts",
    "sweet roll",
    "snack bar",
    "formulated bar",
    "chocolate",
    "bakery",
    "cream puff",
    "cream filled",
    "frosting",
    "frostings",
    "candy",
    "candies",
    "syrup",
    "syrups",
    "marshmallow",
    "cookie",
    "cookies",
    "cake",
    "cakes",
    "jelly",
    "jellies",
    "caramel",
    "butterscotch",
    "fruit butter",
    "fruit butters",
    "bo trai cay",
    "chocolate coated",
    "chocolate covered",
    "fruit-flavored drink",
    "beverage",
    "beverages",
    "drink",
    "drinks",
    "coffee substitute",
    "sauce",
    "sauces",
    "dry mix",
    "restaurant",
    "soft drink",
    "soda",
    "sweetener",
    "sweeteners",
    "dessert",
    "desserts",
    "custard",
    "eggnog",
    "sundae",
    "jam",
    "jelly",
    "mứt",
    "mut",
)
SEASONING_NAME_TERMS = (
    "lemon peel",
    "orange peel",
    "citrus peel",
    "zest",
    "lemon grass",
    "lemongrass",
    "citronella",
    "pepeao",
    "spice",
    "spices",
    "seasoning",
    "baking powder",
    "leavening",
    "salt, table",
    "salt substitute",
    "black pepper",
    "white pepper",
    "hot chili",
    "chili pepper",
    "cinnamon",
    "onion powder",
    "garlic powder",
    "vinegar",
    "dressing",
    "condiment",
    "extract",
    "juice from concentrate",
    "lemon juice",
    "lime juice",
    "fish sauce",
    "soy sauce",
    "mustard",
    "pickle",
    "pickles",
    # Vietnamese condiments / sauces that should never be meal-plan items
    "nuoc tuong",
    "nước tương",
    "xi dau",
    "xì dầu",
    "nuoc mam",
    "nước mắm",
    "tuong ot",
    "tương ớt",
    "tuong",
    "nuoc cham",
    "nước chấm",
    "muoi",
    "gia vi",
    "gia vị",
    "hoisin",
    "oyster sauce",
    "nuoc sot",
    "nước sốt",
    "hot sauce",
    "ketchup",
    "mayonnaise",
    "mayo",
)
UNFAMILIAR_NAME_TERMS = (
    "lasagna",
    "ravioli",
    "tamale",
    "tamales",
    "potsticker",
    "wonton",
    "pupusas",
    "empanadas",
    "alaska native",
    "giant kelp",
    "mouse nuts",
    "fast food",
    "fast foods",
    "burger",
    "burgers",
    "sandwich",
    "subway",
    "horned melon",
    "strawberry guava",
    "winged bean",
    "bean fruit",
    "breadfruit",
    "navajo",
    "imitation",
    "surimi",
    "frozen mixture",
    "ổi dâu",
    "quả đậu",
    "dưa sừng",
    "đồ ăn nhanh",
    "do an nhanh",
)
CLEAN_CARB_NAME_TERMS = (
    "rice",
    "oats",
    "oatmeal",
    "buckwheat",
    "wheat",
    "bread",
    "noodles",
    "pasta",
    "potato",
    "sweet potato",
    "corn",
    "beans",
    "lentils",
    "chickpeas",
    "banana",
    "plantain",
    "cereal",
    "grits",
    "cream of wheat",
    "kem lua mi",
    "kem lúa mì",
)
LEAN_PROTEIN_NAME_TERMS = (
    "chicken",
    "beef",
    "pork",
    "fish",
    "salmon",
    "tuna",
    "egg",
    "eggs",
    "tofu",
    "soybean",
    "beans",
    "yogurt",
    "milk",
)
GOOD_FAT_NAME_TERMS = (
    "avocado",
    "peanut",
    "peanuts",
    "almond",
    "walnut",
    "nuts",
    "olive",
    "salmon",
    "fish",
    "egg",
    "eggs",
    "whole milk",
    "yogurt",
    "bơ",
    "bo dau phong",
    "bơ đậu phộng",
    "hat",
    "hạt",
    "pho mai",
    "phô mai",
)
HEALTHY_ENERGY_EXTRA_TERMS = (
    "sua nguyen kem",
    "sữa nguyên kem",
    "full fat milk",
    "whole milk",
    "milk",
    "yogurt",
    "sua tuoi",
    "sua chua",
    "sữa chua",
    "sinh to chuoi sua",
    "sinh tố chuối sữa",
    "banana milk smoothie",
    "banana smoothie",
    "avocado",
    "qua bo",
    "quả bơ",
    "peanut butter",
    "bo dau phong",
    "bơ đậu phộng",
    "peanut",
    "peanuts",
    "almond",
    "hanh nhan",
    "hạnh nhân",
    "cashew",
    "hat dieu",
    "hạt điều",
    "walnut",
    "nuts",
    "yen mach",
    "yến mạch",
    "oat",
    "oats",
    "oatmeal",
    "sweet potato",
    "potato",
    "khoai",
    "cheese",
    "pho mai",
)
LOW_PRIORITY_EXTRA_TERMS = (
    "nuoc cam",
    "nuoc ep",
    "nuoc dua",
    "nuoc trai cay",
    "orange juice",
    "apple juice",
    "grape juice",
    "juice",
    "coconut water",
    "jam",
    "jelly",
    "mứt",
    "mut",
    "xuc xich",
    "xúc xích",
    "sausage",
    "smoked",
    "hun khoi",
    "hun khói",
    "processed",
    "do an nhanh",
    "đồ ăn nhanh",
    "fast food",
    "fried",
    "chien ran nhieu dau",
    "chiên rán nhiều dầu",
    "soft drink",
    "soda",
    "nuoc ngot",
    "nước ngọt",
    "candy",
    "banh keo ngot",
    "bánh kẹo ngọt",
    "mon ngot nhieu duong",
    "món ngọt nhiều đường",
    # condiments / sauces explicitly listed as low-priority
    "nuoc tuong",
    "nước tương",
    "xi dau",
    "nuoc mam",
    "nước mắm",
    "nuoc cham",
    "gia vi",
    "gia vị",
)
# Terms that clearly indicate a drink / juice — these items should NEVER fill
# staple / protein / vegetable / fruit meal slots.
DRINK_BEVERAGE_TERMS = (
    "juice",
    "nuoc ep",
    "nước ép",
    "nuoc cam",
    "nước cam",
    "nuoc tao",
    "nước táo",
    "nuoc dua",
    "nước dừa",
    "nuoc trai cay",
    "nước trái cây",
    "orange juice",
    "apple juice",
    "grape juice",
    "beverage",
    "do uong",
    "đồ uống",
    "tang cuong",
    "tăng cường",
    "fortified",
    "energy drink",
    "sport drink",
    "soft drink",
    "nuoc ngot",
    "nước ngọt",
    "coconut water",
    "smoothie",
    "sinh to",
    "sinh tố",
)
# Fresh whole fruit terms — these are actively preferred over juices.
FRESH_FRUIT_TERMS = (
    "chuoi",
    "chuối",
    "banana",
    "tao",
    "táo",
    "apple",
    "qua bo",
    "quả bơ",
    "avocado",
    "cam tuoi",
    "cam tươi",
    "orange",
    "xoai",
    "xoài",
    "mango",
    "du du",
    "đu đủ",
    "papaya",
    "berry",
    "berries",
    "dau tay",
    "dâu tây",
    "strawberry",
    "viet quat",
    "việt quất",
    "blueberry",
    "nho",
    "grape",
    "kiwi",
    "dua hau",
    "dưa hấu",
    "watermelon",
)
VEGETABLE_FRUIT_NAME_TERMS = (
    "broccoli",
    "spinach",
    "tomato",
    "carrot",
    "pepper",
    "banana",
    "apple",
    "orange",
    "mango",
    "berries",
    "beans",
)
FAMILIAR_NAME_TERMS = (
    # English familiar terms
    "rice",
    "egg",
    "chicken",
    "beef",
    "pork",
    "milk",
    "banana",
    "bread",
    "tofu",
    "fish",
    "sweet potato",
    "yogurt",
    "bean",
    "oat",
    "oatmeal",
    "salmon",
    "tuna",
    "avocado",
    "broccoli",
    "spinach",
    "carrot",
    # Vietnamese familiar terms
    "com",
    "cơm",
    "trứng",
    "thịt gà",
    "thịt heo",
    "thịt bò",
    "thịt",
    "sữa chua",
    "sữa",
    "chuối",
    "khoai lang",
    "khoai tây",
    "khoai",
    "đậu hũ",
    "đậu phụ",
    "đậu",
    "cá hồi",
    "cá ngừ",
    "cá",
    "yến mạch",
    "ngũ cốc",
    "rau cải",
    "rau bina",
    "rau",
    "bơ",
    "đu đủ",
    "cam",
    "xoài",
)
BREAKFAST_AVOID_TERMS = ("condensed", "evaporated", "cô đặc")
MEAL_CATEGORY_PRIORITIES = {
    "breakfast": ["grain", "dairy", "fruit", "meat", "plant_protein", "healthy_fat", "vegetable"],
    "lunch": ["grain", "meat", "vegetable", "plant_protein", "healthy_fat", "dairy", "fruit"],
    "snack": ["fruit", "dairy", "healthy_fat", "grain", "plant_protein"],
    "dinner": ["grain", "meat", "vegetable", "plant_protein", "healthy_fat", "dairy", "fruit"],
}
MEAL_MACRO_WEIGHTS = {
    "breakfast": {"calories": 0.20, "protein": 0.30, "fat": 0.15, "carbs": 0.35},
    "lunch": {"calories": 0.20, "protein": 0.25, "fat": 0.15, "carbs": 0.40},
    "snack": {"calories": 0.30, "protein": 0.20, "fat": 0.20, "carbs": 0.30},
    "dinner": {"calories": 0.20, "protein": 0.25, "fat": 0.15, "carbs": 0.40},
}
MEAL_REQUIRED_CATEGORIES = {
    "breakfast": ["grain"],
    "lunch": ["grain", "meat"],
    "snack": [],
    "dinner": ["grain", "meat"],
}
MEAL_CATEGORY_REPEAT_LIMITS = {
    "starch_grain": 2,
    "starch_tuber": 1,
    "vegetable": 2,
    "fruit": 1,
    "dairy": 1,
    "protein_meat": 2,
    "protein_seafood": 1,
    "plant_protein": 2,
    "egg": 1,
    "healthy_fat_nuts": 1,
    "drink_natural": 1,
    "other": 1,
}
MAX_DAILY_CATEGORY_REPEAT = {
    "dairy": 2,
    "starch_grain": 6,
    "starch_tuber": 2,
    "protein_meat": 6,
    "protein_seafood": 2,
    "vegetable": 6,
    "fruit": 3,
    "plant_protein": 2,
    "egg": 2,
    "healthy_fat_nuts": 3,
    "drink_natural": 1,
    "other": 2,
}
# Mỗi slot có vai trò cố định. Thứ tự quan trọng:
#   Grain → Protein → Vegetable → Fat/Extra
# Điều này đảm bảo bữa ăn luôn đủ 4 nhóm dinh dưỡng.
MEAL_SLOT_ROLES: dict[str, list[list[str]]] = {
    "breakfast": [
        ["grain"],                           # slot 0: tinh bột (cơm/bánh mì/yến mạch)
        ["meat", "plant_protein", "dairy"],  # slot 1: đạm (trứng/thịt/sữa chua)
        ["healthy_fat", "dairy", "fruit"],   # slot 2: chất béo tốt + bổ sung (bơ/sữa/trái cây)
    ],
    "lunch": [
        ["grain"],                           # slot 0: cơm/tinh bột
        ["meat", "plant_protein"],           # slot 1: đạm chính (thịt/cá/đậu phụ)
        ["vegetable"],                       # slot 2: rau củ
        ["healthy_fat", "dairy", "meat"],    # slot 3: chất béo/canh có đạm (dầu ô liu/phô mai)
    ],
    "snack": [
        ["fruit", "dairy"],                  # slot 0: trái cây hoặc sữa
        ["healthy_fat", "dairy", "grain"],   # slot 1: chất béo + carb bổ sung
    ],
    "dinner": [
        ["grain"],                           # slot 0: cơm/tinh bột
        ["meat", "plant_protein"],           # slot 1: đạm chính
        ["vegetable"],                       # slot 2: rau củ
        ["healthy_fat", "dairy", "meat"],    # slot 3: chất béo/canh
    ],
}
STARCH_CATEGORIES = ["starch_grain", "starch_tuber"]
PROTEIN_CATEGORIES = ["protein_meat", "protein_seafood", "plant_protein", "protein_plant", "egg"]
VEG_FRUIT_CATEGORIES = ["vegetable", "fruit"]
EXTRA_CATEGORIES = ["dairy", "healthy_fat_nuts", "plant_protein", "protein_plant", "fruit", "egg"]
DRINK_CATEGORIES = ["drink_natural"]

MEAL_SLOT_ROLES = {
    # 5 items (full)
    "breakfast": [
        STARCH_CATEGORIES,
        PROTEIN_CATEGORIES,
        ["vegetable"],
        ["fruit"] + EXTRA_CATEGORIES,
        EXTRA_CATEGORIES,
    ],
    # 4 items (balanced)
    "lunch": [
        STARCH_CATEGORIES,
        PROTEIN_CATEGORIES,
        VEG_FRUIT_CATEGORIES,
        EXTRA_CATEGORIES,
    ],
    # 4 items
    "dinner": [
        STARCH_CATEGORIES,
        PROTEIN_CATEGORIES,
        VEG_FRUIT_CATEGORIES,
        EXTRA_CATEGORIES,
    ],
    # 2 items
    "snack": [
        VEG_FRUIT_CATEGORIES + ["dairy"],
        EXTRA_CATEGORIES,
    ],
}

# Override for simple (3 items) if requested by complexity mapping
MEAL_SLOT_ROLES_SIMPLE = {
    "breakfast": [
        STARCH_CATEGORIES,
        PROTEIN_CATEGORIES,
        VEG_FRUIT_CATEGORIES,
    ],
    "lunch": [
        STARCH_CATEGORIES,
        PROTEIN_CATEGORIES,
        VEG_FRUIT_CATEGORIES,
    ],
    "dinner": [
        STARCH_CATEGORIES,
        PROTEIN_CATEGORIES,
        VEG_FRUIT_CATEGORIES,
    ],
    "snack": [
        VEG_FRUIT_CATEGORIES + ["dairy"],
        EXTRA_CATEGORIES,
    ],
}

MEAL_SLOT_CALORIE_WEIGHTS = {
    "breakfast": [0.32, 0.18, 0.22, 0.20, 0.08],
    "lunch": [0.30, 0.25, 0.25, 0.20],
    "dinner": [0.30, 0.25, 0.25, 0.20],
    "snack": [0.55, 0.45],
}
MEAL_SLOT_CULINARY_ROLES = {
    "breakfast": ["staple", "protein", "vegetable", "fruit_or_extra", "extra"],
    "lunch": ["staple", "protein", "vegetable_or_fruit", "extra"],
    "dinner": ["staple", "protein", "vegetable_or_fruit", "extra"],
    "snack": ["fruit", "extra"],
}

_CATEGORY_TAXONOMY_CACHE: dict[str, str] = {}


def clear_taxonomy_cache() -> None:
    """Clear the global category taxonomy cache.
    Call this after reloading data or changing category rules."""
    _CATEGORY_TAXONOMY_CACHE.clear()


@dataclass(frozen=True)
class UserProfile:
    weight_kg: float
    height_cm: float
    activity_level: str = "moderate"
    age: int | None = None
    sex: str | None = None
    goal: str = "gain"
    surplus_kcal: float | None = None
    weight_gain_speed: str | None = None
    disliked_foods: tuple[str, ...] = ()
    disliked_food_groups: tuple[str, ...] = ()
    diet_type: str | None = None
    items_per_meal: int | None = None
    user_id: int | None = None


class HealthyWeightGainRecommender:
    def __init__(
        self,
        raw_path: str | Path,
        scaled_path: str | Path,
        preference_model_path: str | Path | None = None,
    ) -> None:
        self.raw_path = Path(raw_path)
        self.scaled_path = Path(scaled_path)
        self.preference_model_path = Path(preference_model_path) if preference_model_path else None
        self.raw_df: pd.DataFrame | None = None
        self.scaled_df: pd.DataFrame | None = None
        self.merged_df: pd.DataFrame | None = None
        self.feature_matrix: np.ndarray | None = None
        self.feature_min: pd.Series | None = None
        self.feature_max: pd.Series | None = None
        self.preference_model = None
        self.preference_categories: list[str] = []

    def load_data(self) -> "HealthyWeightGainRecommender":
        raw_df = pd.read_csv(self.raw_path)
        scaled_df = pd.read_csv(self.scaled_path)

        if {"dish_name_vi", "clean_category", "menu_eligible", "kcal_per_serving_clean"}.issubset(raw_df.columns):
            fixed_df = raw_df.copy()
            fixed_df = fixed_df[fixed_df["menu_eligible"].astype(str).str.lower().isin({"true", "1", "yes"})].copy()
            for boolean_column in ("is_raw_ingredient", "is_generic_name", "is_brand_or_restaurant"):
                if boolean_column in fixed_df.columns:
                    fixed_df = fixed_df[~fixed_df[boolean_column].astype(str).str.lower().isin({"true", "1", "yes"})].copy()
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
            if "quality_flags" in fixed_df.columns:
                fixed_df = fixed_df[
                    ~fixed_df["quality_flags"].fillna("").astype(str).str.lower().apply(
                        lambda flags: any(flag in flags for flag in severe_flags)
                    )
                ].copy()
            generic_mask = fixed_df["dish_name_vi"].apply(self._is_generic_menu_name)
            non_generic_df = fixed_df[~generic_mask].copy()
            if not non_generic_df.empty:
                fixed_df = non_generic_df

            serving_factor = pd.to_numeric(fixed_df["recommended_serving_g"], errors="coerce") / 100.0
            for serving_column, per100_column in (
                ("protein_per_serving_clean", "protein_per_100g_clean"),
                ("fat_per_serving_clean", "fat_per_100g_clean"),
                ("carbs_per_serving_clean", "carbs_per_100g_clean"),
            ):
                if per100_column not in fixed_df.columns:
                    fixed_df[per100_column] = pd.to_numeric(fixed_df[serving_column], errors="coerce") / serving_factor.replace(0, pd.NA)

            normalized_clean_category = fixed_df.apply(
                lambda row: self.normalize_food_category(
                    row.get("clean_category", ""),
                    row.get("dish_name_vi", ""),
                ),
                axis=1,
            )
            image_url_series = (
                fixed_df["image_url"]
                if "image_url" in fixed_df.columns
                else pd.Series("", index=fixed_df.index)
            )
            image_source_type_series = (
                fixed_df["image_source_type"]
                if "image_source_type" in fixed_df.columns
                else pd.Series("placeholder", index=fixed_df.index)
            )
            image_verified_series = (
                fixed_df["image_verified"]
                if "image_verified" in fixed_df.columns
                else pd.Series(False, index=fixed_df.index)
            )
            image_alt_series = (
                fixed_df["image_alt_vi"]
                if "image_alt_vi" in fixed_df.columns
                else pd.Series("", index=fixed_df.index)
            )
            image_quality_note_series = (
                fixed_df["image_quality_note"]
                if "image_quality_note" in fixed_df.columns
                else pd.Series("", index=fixed_df.index)
            )
            image_query_series = (
                fixed_df["image_search_query_vi"]
                if "image_search_query_vi" in fixed_df.columns
                else pd.Series("", index=fixed_df.index)
            )
            image_requirement_series = (
                fixed_df["image_requirement"]
                if "image_requirement" in fixed_df.columns
                else pd.Series("", index=fixed_df.index)
            )
            quality_flags_series = (
                fixed_df["quality_flags"]
                if "quality_flags" in fixed_df.columns
                else pd.Series("", index=fixed_df.index)
            )
            name_en_series = (
                fixed_df["name"]
                if "name" in fixed_df.columns
                else fixed_df["dish_name_vi"]
            )
            raw_df = pd.DataFrame(
                {
                    "food_id": fixed_df["food_id"].astype(str).str.strip(),
                    "name": fixed_df["dish_name_vi"].astype(str).str.strip(),
                    "name_en": name_en_series.astype(str).str.strip(),
                    "calories": pd.to_numeric(fixed_df["kcal_per_serving_clean"], errors="coerce"),
                    "protein": pd.to_numeric(fixed_df["protein_per_serving_clean"], errors="coerce"),
                    "fat": pd.to_numeric(fixed_df["fat_per_serving_clean"], errors="coerce"),
                    "carbs": pd.to_numeric(fixed_df["carbs_per_serving_clean"], errors="coerce"),
                    "category": normalized_clean_category.map(self.category_for_recommender),
                    "clean_category": normalized_clean_category,
                    "food_group": normalized_clean_category.map(self.category_label_vi),
                    "quantity_g": pd.to_numeric(fixed_df["recommended_serving_g"], errors="coerce"),
                    "serving_grams": pd.to_numeric(fixed_df["recommended_serving_g"], errors="coerce"),
                    "base_serving_grams": pd.to_numeric(fixed_df["recommended_serving_g"], errors="coerce"),
                    "serving_display": fixed_df.get("serving_display", "").astype(str),
                    "kcal_per_100g_clean": pd.to_numeric(fixed_df["kcal_per_100g_clean"], errors="coerce"),
                    "protein_per_100g_clean": pd.to_numeric(fixed_df["protein_per_100g_clean"], errors="coerce"),
                    "fat_per_100g_clean": pd.to_numeric(fixed_df["fat_per_100g_clean"], errors="coerce"),
                    "carbs_per_100g_clean": pd.to_numeric(fixed_df["carbs_per_100g_clean"], errors="coerce"),
                    "image_query": image_query_series.where(image_query_series.notna(), "").astype(str),
                    "image_requirement": image_requirement_series.where(image_requirement_series.notna(), "").astype(str),
                    "image_url": image_url_series.where(image_url_series.notna(), "").astype(str).str.strip(),
                    "image_alt_vi": image_alt_series.where(image_alt_series.notna(), "").astype(str).str.strip(),
                    "image_source_type": image_source_type_series.where(image_source_type_series.notna(), "placeholder").astype(str).str.strip(),
                    "image_verified": image_verified_series.where(image_verified_series.notna(), False),
                    "image_quality_note": image_quality_note_series.where(image_quality_note_series.notna(), "").astype(str).str.strip(),
                    "quality_flags": quality_flags_series.where(quality_flags_series.notna(), "").astype(str),
                }
            ).dropna(subset=["food_id", "name", *FEATURE_COLUMNS, "category"])
            raw_df = raw_df[raw_df["category"].astype(str).str.lower() != "junk_food"].copy()
            scaled_df = raw_df[["food_id", *FEATURE_COLUMNS, "category"]].copy()

        required_raw_columns = {"food_id", "name", *FEATURE_COLUMNS, "category"}
        required_scaled_columns = {"food_id", *FEATURE_COLUMNS, "category"}
        missing_raw = required_raw_columns - set(raw_df.columns)
        missing_scaled = required_scaled_columns - set(scaled_df.columns)
        if missing_raw:
            raise ValueError(f"Raw dataset is missing columns: {sorted(missing_raw)}")
        if missing_scaled:
            raise ValueError(f"Scaled dataset is missing columns: {sorted(missing_scaled)}")

        raw_df = raw_df.copy()
        scaled_df = scaled_df.copy()

        raw_df["food_id"] = raw_df["food_id"].astype(str)
        scaled_df["food_id"] = scaled_df["food_id"].astype(str)
        raw_df["display_name_en"] = raw_df["name"].map(self.clean_food_name)
        raw_df["category"] = raw_df.apply(
            lambda row: self._semantic_category(
                row.get("category", ""),
                f"{row.get('name', '')} {row.get('name_vi', '')}",
            ),
            axis=1,
        )

        merged_df = raw_df.merge(
            scaled_df[["food_id", *FEATURE_COLUMNS]],
            on="food_id",
            how="inner",
            suffixes=("_raw", "_scaled"),
            validate="one_to_one",
        )

        self.raw_df = raw_df
        self.scaled_df = scaled_df
        self.merged_df = merged_df
        self.feature_matrix = merged_df[[f"{col}_scaled" for col in FEATURE_COLUMNS]].to_numpy(dtype=float)
        self.feature_min = raw_df[FEATURE_COLUMNS].min()
        self.feature_max = raw_df[FEATURE_COLUMNS].max()
        self._load_preference_model()
        return self

    @staticmethod
    def clean_food_name(name: object) -> str:
        text = str(name or "").strip()
        if not text:
            return ""

        if "," in text:
            parts = [part.strip() for part in text.split(",") if part.strip()]
            if len(parts) > 1:
                head = parts[0]
                # Treat all-uppercase leading part as brand prefix.
                if head == head.upper() and any(ch.isalpha() for ch in head):
                    text = ", ".join(parts[1:])

        text = " ".join(text.split())
        return text

    @staticmethod
    def _row_name(row: pd.Series | dict) -> str:
        value = row.get("display_name_en") or row.get("name_en") or row.get("name") or ""
        return str(value).strip().lower()

    @staticmethod
    def _contains_any(text: str, terms: Sequence[str]) -> bool:
        return any(term in text for term in terms)

    @staticmethod
    def _strip_accents(value: object) -> str:
        text = str(value or "")
        text = unicodedata.normalize("NFD", text)
        return "".join(char for char in text if unicodedata.category(char) != "Mn").replace("đ", "d").replace("Đ", "D")

    @classmethod
    def _normalized_search_text(cls, value: object) -> str:
        text = cls._strip_accents(value).lower()
        text = "".join(char if char.isalnum() or char.isspace() else " " for char in text)
        return " ".join(text.split())

    @classmethod
    def _row_search_text(cls, row: pd.Series | dict) -> str:
        return cls._normalized_search_text(
            " ".join(
                str(row.get(column, "") or "")
                for column in ("food_id", "name", "name_en", "display_name_en", "clean_category", "food_group", "category")
            )
        )

    @classmethod
    def _row_matches_preference_terms(cls, row: pd.Series | dict, terms: Sequence[str]) -> bool:
        text = cls._row_search_text(row)
        if not text:
            return False
        padded_text = f" {text} "
        for term in terms:
            normalized_term = cls._normalized_search_text(term)
            if not normalized_term:
                continue
            if " " not in normalized_term and len(normalized_term) <= 3:
                if f" {normalized_term} " in padded_text:
                    return True
            elif normalized_term in text:
                return True
        return False

    @classmethod
    def _is_generic_menu_name(cls, name: object) -> bool:
        normalized = " ".join(cls._strip_accents(name).lower().strip().split())
        return normalized in GENERIC_MENU_NAMES

    @classmethod
    def normalize_food_category(cls, category: object, name: object = "") -> str:
        """Normalize food_dataset_fixed.csv clean_category after reading the CSV."""
        current = str(category or "").strip().lower() or "other"
        original = str(name or "").lower()
        text = cls._strip_accents(name).lower()

        if "mứt" in original or text.startswith("mut") or " mut " in f" {text} ":
            return "dessert_sweets"
        if cls._contains_any(
            text,
            ("nuoc cam", "nuoc dua", "nuoc ep", "nuoc trai cay", "orange juice", "juice"),
        ):
            return "drink_natural"
        if cls._contains_any(text, ("kem lua mi", "cream of wheat")):
            return "starch_grain"
        if cls._contains_any(text, ("do an nhanh", "fast food")):
            return "other"
        if "bac ha" in text:
            return "vegetable_herb"
        if "khoai tay" in text:
            return "starch_tuber"
        if "ngu coc" in text:
            return "starch_grain"
        if "banh" in text:
            if "banh mi" in text or current in {"starch_grain", "grain"}:
                return "starch_grain"
            return "dessert_sweets"
        return current

    @staticmethod
    def category_for_recommender(clean_category: object) -> str:
        normalized = str(clean_category or "").strip().lower()
        if normalized == "protein_plant":
            return "plant_protein"
        return normalized

    @staticmethod
    def category_label_vi(clean_category: object) -> str:
        normalized = str(clean_category or "").strip().lower()
        return {
            "starch_grain": "Tinh bột · Ngũ cốc",
            "starch_tuber": "Tinh bột · Củ",
            "protein_seafood": "Đạm · Hải sản",
            "protein_meat": "Đạm · Thịt",
            "protein_plant": "Đạm thực vật",
            "plant_protein": "Đạm thực vật",
            "vegetable": "Rau củ",
            "vegetable_herb": "Rau củ · Rau gia vị",
            "fruit": "Trái cây",
            "dairy": "Sữa",
            "drink_natural": "Đồ uống tự nhiên",
            "dessert_sweets": "Bánh/ngọt",
            "sweet_spread": "Bánh/ngọt",
            "fats_good": "Chất béo tốt",
            "healthy_fat": "Chất béo tốt",
            "healthy_fat_nuts": "Chất béo tốt",
            "egg": "Đạm · Trứng",
            "grain": "Tinh bột · Ngũ cốc",
            "meat": "Đạm · Thịt",
        }.get(normalized, "Khác")

    @staticmethod
    def _has_valid_image_url(row: pd.Series | dict) -> bool:
        value = str(row.get("image_url", "") or "").strip().lower()
        if not value or value in {"nan", "none", "null"}:
            return False
        if not (
            value.startswith("http://")
            or value.startswith("https://")
            or value.startswith("/images/foods/")
        ):
            return False
        source_type = str(row.get("image_source_type", "") or "").strip().lower()
        verified = str(row.get("image_verified", "") or "").strip().lower() in {"true", "1", "yes", "y"}
        return source_type == "real_food_photo" and verified

    @classmethod
    def _semantic_category(cls, category: object, name: object = "") -> str:
        text = f"{name} {category}".strip().lower()
        text_no_accent = cls._strip_accents(text).lower()
        old_category = str(category or "").strip().lower()

        if cls._contains_any(text_no_accent, ("mut ", " jam", "jelly")) or "mứt" in text:
            return "junk_food"
        if cls._contains_any(text_no_accent, ("nuoc cam", "nuoc dua", "nuoc ep", "nuoc trai cay", "orange juice", "juice")):
            return "drink_natural"
        if cls._contains_any(text_no_accent, ("kem lua mi", "cream of wheat")):
            return "grain"
        if cls._contains_any(text_no_accent, ("do an nhanh", "fast food")):
            return "other"
        if cls._contains_any(text, ("pie", "cake", "cookie", "pastry", "doughnut", "donut", "muffin", "sweet roll")):
            return "junk_food"
        if cls._contains_any(text, ("fast food", "mcdonald", "burger king", "kfc", "subway", "pizza hut", "taco bell")):
            return "other"
        if cls._contains_any(text, ("peanut butter", "peanut", "peanuts", "almond", "walnut", "nuts", "avocado", "olive", "olives", "olive oil")):
            return "healthy_fat"
        if cls._contains_any(text, ("crab", "cua", "crustacean", "shrimp", "prawn", "lobster", "mollusk", "oyster", "clam", "scallop")):
            return "meat"
        if cls._contains_any(text, ("taro", "khoai môn", "khoai mon")) and not cls._contains_any(text, ("taro leaves", "leaf", "leaves")):
            return "grain"
        if cls._contains_any(text, ("grape leaves", "leaf", "leaves", "greens")):
            return "vegetable"
        if cls._contains_any(text, ("yogurt", "cheese", "sua chua")):
            return "dairy"
        if cls._contains_any(text, ("pasta", "spaghetti", "macaroni", "noodle", "noodles")):
            return "grain"
        if cls._contains_any(text, ("rice", "oat", "oats", "oatmeal", "bread", "cereal", "potato", "corn")):
            return "grain"
        if cls._contains_any(text, ("bean", "beans", "lentil", "lentils", "chickpea", "chickpeas", "soybean", "soybeans", "tofu", "dau trang", "dau nanh", "dau phu", "đậu nành", "đậu phụ")):
            return "plant_protein"
        if cls._contains_any(text, ("milk", "sua ")):
            return "dairy"
        if cls._contains_any(text, ("chicken", "beef", "pork", "fish", "salmon", "tuna", "turkey", "shrimp", "ham", "bacon")):
            return "meat"
        if cls._contains_any(text, ("egg", "eggs", "trung")):
            return "egg"
        if cls._contains_any(text, ("broccoli", "spinach", "carrot", "tomato", "lettuce", "cabbage", "greens")):
            return "vegetable"
        if cls._contains_any(text, ("banana", "apple", "orange", "mango", "berries", "grape", "strawberry", "blueberry")):
            return "fruit"
        if old_category in {"carb", "starch"}:
            return "grain"
        if old_category == "protein":
            return "meat"
        if old_category == "fat":
            return "healthy_fat"
        return old_category or "other"

    @classmethod
    def _is_dirty_bulk_name(cls, name: object) -> bool:
        text = str(name or "").strip().lower()
        text_no_accent = cls._strip_accents(text).lower()
        return cls._contains_any(text, DIRTY_BULK_NAME_TERMS) or cls._contains_any(text_no_accent, DIRTY_BULK_NAME_TERMS)

    @classmethod
    def _is_seasoning_row(cls, row: pd.Series | dict) -> bool:
        text = cls._row_name(row)
        return cls._contains_any(text, SEASONING_NAME_TERMS)

    @classmethod
    def _culinary_role(cls, row: pd.Series | dict) -> str:
        text = cls._row_name(row)
        text_no_accent = cls._strip_accents(text).lower()
        category = cls._semantic_category(row.get("category", ""), text)
        if cls._is_dirty_bulk_name(text):
            return "dirty"
        if cls._is_seasoning_row(row):
            return "seasoning"
        if category == "drink_natural":
            return "drink_or_extra"
        row_fat = float(row.get("fat_raw", row.get("fat", 0.0)) or 0.0)
        if category == "healthy_fat" or (
            category == "dairy"
            and row_fat >= 4.0
            and cls._is_good_fat_row(row)
        ) or cls._contains_any(
            text_no_accent,
            ("avocado", "peanut butter", "peanut", "almond", "walnut", "nuts", "cheese", "pho mai"),
        ):
            return "fat"
        if cls._contains_any(text, ("yogurt", "milk", "sữa chua", "sá»¯a chua", "sữa", "sá»¯a")):
            return "protein"
        if cls._contains_any(text, ("bean", "beans", "lentil", "chickpea", "soybean", "tofu", "đậu", "Ä‘áº­u")):
            return "protein"
        if category in {"meat", "egg", "plant_protein"} or cls._contains_any(text, LEAN_PROTEIN_NAME_TERMS):
            return "protein"
        if category == "grain" or cls._contains_any(text, CLEAN_CARB_NAME_TERMS):
            return "staple"
        if category == "vegetable" or cls._contains_any(text, ("broccoli", "spinach", "carrot", "tomato", "greens", "lettuce")):
            return "vegetable"
        if category == "fruit" or cls._contains_any(text, ("banana", "apple", "orange", "mango", "berries", "grape")):
            return "fruit"
        if category == "drink_natural":
            return "drink_or_extra"
        if category == "junk_food":
            return "dessert"
        if category == "healthy_fat" or cls._is_good_fat_row(row):
            return "fat"
        return "side"

    @classmethod
    def _carb_family(cls, row: pd.Series | dict) -> str:
        text = cls._row_name(row)
        families = {
            "rice": ("rice", "arroz"),
            "noodle": ("noodle", "noodles", "pasta", "spaghetti", "macaroni", "soba", "somen"),
            "potato": ("potato", "sweet potato"),
            "corn": ("corn", "grits"),
            "bread": ("bread", "bagel", "roll", "biscuit"),
            "oat": ("oat", "oats", "oatmeal"),
            "bean": ("bean", "beans", "lentil", "chickpea", "soybean", "tofu"),
            "fruit": ("banana", "apple", "orange", "mango", "berries", "grape"),
            "cereal": ("cereal", "wheat", "buckwheat"),
        }
        for family, terms in families.items():
            if any(term in text for term in terms):
                return family
        return ""

    @classmethod
    def _food_family(cls, row: pd.Series | dict) -> str:
        """Coarse culinary family used to prevent redundant meal picks.

        This is intentionally broader than category. For example, Greek yogurt,
        soy yogurt and frozen yogurt should not appear together in one meal even
        when their category/role scores differ.
        """
        text = cls._row_name(row)
        families = {
            "yogurt": ("yogurt", "sữa chua", "sá»¯a chua"),
            "milk": ("milk", "sữa", "sá»¯a"),
            "cheese": ("cheese", "phô mai", "pho mai"),
            "bean": ("bean", "beans", "lentil", "chickpea", "soybean", "tofu", "đậu", "Ä‘áº­u"),
            "pasta": ("pasta", "spaghetti", "macaroni", "noodle", "noodles", "mì ống", "mÃ¬ á»‘ng"),
            "rice": ("rice", "cơm", "cÆ¡m"),
            "oat": ("oat", "oats", "oatmeal", "yến mạch", "yáº¿n máº¡ch"),
            "egg": ("egg", "eggs", "trứng", "trá»©ng"),
            "chicken": ("chicken", "gà", "gÃ "),
            "pork": ("pork", "heo", "lợn", "lá»£n"),
            "beef": ("beef", "bò", "bÃ²"),
            "fish": ("fish", "salmon", "tuna", "cá", "cÃ¡"),
        }
        for family, terms in families.items():
            if any(term in text for term in terms):
                return family
        return str(row.get("category", "")).strip().lower() or "other"

    @classmethod
    def _is_sweet_or_cold_side(cls, row: pd.Series | dict) -> bool:
        text = cls._row_name(row)
        category = cls._semantic_category(row.get("category", ""), text)
        return (
            category in {"fruit", "dairy"}
            or cls._contains_any(text, ("yogurt", "smoothie", "parfait", "fruit", "banana", "apple", "berries"))
        )

    @classmethod
    def _is_savory_staple(cls, row: pd.Series | dict) -> bool:
        return cls._carb_family(row) in {"noodle", "rice", "potato", "corn"}

    @classmethod
    def _is_clean_carb_row(cls, row: pd.Series | dict) -> bool:
        text = cls._row_name(row)
        category = cls._semantic_category(row.get("category", ""), text)
        if cls._is_dirty_bulk_name(text) or cls._is_seasoning_row(row):
            return False
        return category in {"grain", "fruit", "vegetable"} or cls._contains_any(text, CLEAN_CARB_NAME_TERMS)

    @classmethod
    def _is_lean_protein_row(cls, row: pd.Series | dict) -> bool:
        text = cls._row_name(row)
        category = cls._semantic_category(row.get("category", ""), text)
        if cls._is_dirty_bulk_name(text) or cls._is_seasoning_row(row):
            return False
        return category in {"meat", "egg", "plant_protein"} or cls._contains_any(text, LEAN_PROTEIN_NAME_TERMS)

    @classmethod
    def _is_good_fat_row(cls, row: pd.Series | dict) -> bool:
        text = cls._row_name(row)
        text_no_accent = cls._strip_accents(text).lower()
        category = cls._semantic_category(row.get("category", ""), text)
        if cls._is_dirty_bulk_name(text) or cls._is_seasoning_row(row):
            return False
        fat = float(row.get("fat_raw", row.get("fat", 0.0)) or 0.0)
        if category == "drink_natural" or cls._contains_any(text_no_accent, LOW_PRIORITY_EXTRA_TERMS):
            return False
        if cls._contains_any(text_no_accent, ("nonfat", "fat free", "skim", "khong beo")) and fat < 4.0:
            return False
        if cls._contains_any(text_no_accent, ("peanut", "almond", "walnut", "cashew", "nuts", "avocado", "olive", "cheese", "pho mai", "hat dieu", "hanh nhan", "qua bo")):
            return fat >= 3.0 or category == "healthy_fat"
        if cls._contains_any(text_no_accent, ("whole milk", "full fat milk", "yogurt", "milk", "sua tuoi", "sua chua", "sua nguyen kem")):
            return fat >= 4.0
        return category == "healthy_fat" and fat >= 3.0

    @classmethod
    def _healthy_energy_extra_score(cls, row: pd.Series | dict) -> float:
        text = cls._row_name(row)
        text_no_accent = cls._strip_accents(text).lower()
        category = cls._semantic_category(row.get("category", ""), text)
        if cls._is_dirty_bulk_name(text) or cls._is_seasoning_row(row):
            return -5.0
        if category in {"junk_food", "drink_natural"} or cls._contains_any(text_no_accent, LOW_PRIORITY_EXTRA_TERMS):
            return -4.0

        fat = float(row.get("fat_raw", row.get("fat", 0.0)) or 0.0)
        calories = float(row.get("calories_raw", row.get("calories", 0.0)) or 0.0)
        score = 0.0
        if cls._contains_any(text_no_accent, HEALTHY_ENERGY_EXTRA_TERMS):
            score += 1.0
        if cls._is_good_fat_row(row):
            score += 1.2
        if category in {"dairy", "healthy_fat", "grain"}:
            score += 0.3
        score += min(fat / 12.0, 1.0)
        score += min(calories / 250.0, 0.6)
        return score

    @classmethod
    def _food_quality_score(cls, row: pd.Series | dict) -> float:
        text = cls._row_name(row)
        category = cls._semantic_category(row.get("category", ""), text)
        score = 0.0
        if cls._is_dirty_bulk_name(text) or cls._is_seasoning_row(row) or category == "junk_food":
            score -= 3.0
        
        # Penalize weird foods
        if cls._contains_any(text, ("kem lua mi", "dau nanh to tam", "buttermilk", "pho mai kho")):
            score -= 2.0
            
        # Boost natural common foods
        if cls._contains_any(text, ("com", "khoai lang", "yen mach", "trung", "dau hu", "sua tuoi", "sua chua", "chuoi", "bo", "tao")):
            score += 1.2

        if cls._is_clean_carb_row(row):
            score += 1.0
        if cls._is_lean_protein_row(row):
            score += 0.8
        if cls._is_good_fat_row(row):
            score += 0.5
        if category in {"vegetable", "fruit"} or (
            category not in {"junk_food", "drink_natural"}
            and cls._contains_any(text, VEGETABLE_FRUIT_NAME_TERMS)
        ):
            score += 0.7
        return score

    def _load_preference_model(self) -> None:
        self.preference_model = None
        self.preference_categories = []
        if self.preference_model_path is None or not self.preference_model_path.exists():
            return
        try:
            artifact = joblib.load(self.preference_model_path)
        except Exception:
            return

        model = artifact.get("model") if isinstance(artifact, dict) else None
        categories = artifact.get("categories") if isinstance(artifact, dict) else None
        if model is None or not isinstance(categories, list):
            return

        self.preference_model = model
        self.preference_categories = [str(category).strip().lower() for category in categories]

    @staticmethod
    def _activity_level_for_model(activity_level: str) -> str:
        normalized = str(activity_level).strip().lower()
        if normalized in DEFAULT_ACTIVITY_FACTORS:
            return normalized
        return "moderate"

    def _predict_category_preferences(self, profile: UserProfile) -> dict[str, float]:
        if self.preference_model is None or not self.preference_categories:
            return {}

        age_value = float(profile.age) if profile.age is not None else -1.0
        sex_value = (profile.sex or "unknown").strip().lower()
        activity_value = self._activity_level_for_model(profile.activity_level)

        feature_df = pd.DataFrame(
            {
                "weight_kg": [float(profile.weight_kg)] * len(self.preference_categories),
                "height_cm": [float(profile.height_cm)] * len(self.preference_categories),
                "age": [age_value] * len(self.preference_categories),
                "activity_level": [activity_value] * len(self.preference_categories),
                "sex": [sex_value] * len(self.preference_categories),
                "category": self.preference_categories,
            }
        )

        try:
            probabilities = self.preference_model.predict_proba(feature_df)[:, 1]
        except Exception:
            return {}

        return {
            category: float(probability * 2.0 - 1.0)
            for category, probability in zip(self.preference_categories, probabilities)
        }

    def _ensure_fitted(self) -> None:
        if self.merged_df is None or self.feature_matrix is None:
            raise RuntimeError("Call load_data() before requesting recommendations.")

    @staticmethod
    def _serialize_categories(categories: Sequence[str] | None) -> str:
        if not categories:
            return ""
        cleaned = [category.strip().lower() for category in categories if category and category.strip()]
        return ";".join(cleaned)

    @staticmethod
    def _parse_categories(value: object) -> list[str]:
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return []
        text = str(value).strip()
        if not text:
            return []
        return [part.strip().lower() for part in text.split(";") if part.strip()]

    @staticmethod
    def _normalize_category_preferences(preferences: dict[str, float]) -> dict[str, float]:
        if not preferences:
            return {}
        max_abs = max(abs(value) for value in preferences.values()) or 1.0
        return {category: value / max_abs for category, value in preferences.items()}

    def _load_preference_model(self) -> None:
        self.preference_model = None
        self.preference_categories = []
        if self.preference_model_path is None or not self.preference_model_path.exists():
            return
        try:
            artifact = joblib.load(self.preference_model_path)
        except Exception:
            return

        model = artifact.get("model") if isinstance(artifact, dict) else None
        categories = artifact.get("categories") if isinstance(artifact, dict) else None
        if model is None or not isinstance(categories, list):
            return

        self.preference_model = model
        self.preference_categories = [str(category).strip().lower() for category in categories]

    @staticmethod
    def _activity_level_for_model(activity_level: str) -> str:
        normalized = str(activity_level).strip().lower()
        if normalized in DEFAULT_ACTIVITY_FACTORS:
            return normalized
        return "moderate"

    def _predict_category_preferences(self, profile: UserProfile) -> dict[str, float]:
        if self.preference_model is None or not self.preference_categories:
            return {}

        age_value = float(profile.age) if profile.age is not None else -1.0
        sex_value = (profile.sex or "unknown").strip().lower()
        activity_value = self._activity_level_for_model(profile.activity_level)

        feature_df = pd.DataFrame(
            {
                "weight_kg": [float(profile.weight_kg)] * len(self.preference_categories),
                "height_cm": [float(profile.height_cm)] * len(self.preference_categories),
                "age": [age_value] * len(self.preference_categories),
                "activity_level": [activity_value] * len(self.preference_categories),
                "sex": [sex_value] * len(self.preference_categories),
                "category": self.preference_categories,
            }
        )

        try:
            probabilities = self.preference_model.predict_proba(feature_df)[:, 1]
        except Exception:
            return {}

        return {
            category: float(probability * 2.0 - 1.0)
            for category, probability in zip(self.preference_categories, probabilities)
        }

    def _ensure_fitted(self) -> None:
        if self.merged_df is None or self.feature_matrix is None:
            raise RuntimeError("Call load_data() before requesting recommendations.")

    @staticmethod
    def _serialize_categories(categories: Sequence[str] | None) -> str:
        if not categories:
            return ""
        cleaned = [category.strip().lower() for category in categories if category and category.strip()]
        return ";".join(cleaned)

    @staticmethod
    def _parse_categories(value: object) -> list[str]:
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return []
        text = str(value).strip()
        if not text:
            return []
        return [part.strip().lower() for part in text.split(";") if part.strip()]

    @staticmethod
    def _normalize_category_preferences(preferences: dict[str, float]) -> dict[str, float]:
        if not preferences:
            return {}
        max_abs = max(abs(value) for value in preferences.values()) or 1.0
        return {category: value / max_abs for category, value in preferences.items()}

    def save_user_profile(
        self,
        profile: UserProfile,
        preferred_categories: Sequence[str] | None = None,
        excluded_categories: Sequence[str] | None = None,
        history_path: str | Path = "user_history.csv",
    ) -> Path:
        history_file = Path(history_path)
        history_file.parent.mkdir(parents=True, exist_ok=True)

        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "weight_kg": profile.weight_kg,
            "height_cm": profile.height_cm,
            "activity_level": profile.activity_level,
            "age": profile.age,
            "sex": profile.sex,
            "goal": profile.goal,
            "surplus_kcal": profile.surplus_kcal,
            "preferred_categories": self._serialize_categories(preferred_categories),
            "excluded_categories": self._serialize_categories(excluded_categories),
        }

        record_df = pd.DataFrame([record], columns=USER_HISTORY_COLUMNS)
        record_df.to_csv(history_file, mode="a", header=not history_file.exists(), index=False)
        return history_file

    def train_category_preferences(self, history_path: str | Path) -> dict[str, float]:
        history_file = Path(history_path)
        if not history_file.exists():
            return {}

        history_df = pd.read_csv(history_file)
        if history_df.empty:
            return {}

        category_preferences: dict[str, float] = {}
        for _, row in history_df.iterrows():
            for category in self._parse_categories(row.get("preferred_categories")):
                category_preferences[category] = category_preferences.get(category, 0.0) + 1.0
            for category in self._parse_categories(row.get("excluded_categories")):
                category_preferences[category] = category_preferences.get(category, 0.0) - 1.0

        return self._normalize_category_preferences(category_preferences)

    @staticmethod
    def _activity_factor(activity_level: str) -> float:
        normalized = str(activity_level or "default").strip().lower()
        if normalized in DEFAULT_ACTIVITY_FACTORS:
            return DEFAULT_ACTIVITY_FACTORS[normalized]
        
        vietnamese_mapping = {
            "sedentary": ["ít", "it", "ngồi nhiều", "ngoi nhieu"],
            "light": ["nhẹ", "nhe", "thỉnh thoảng", "thinh thoang"],
            "moderate": ["vừa", "vua", "trung bình", "trung binh"],
            "active": ["nhiều", "nhieu", "năng động", "nang dong"],
            "very_active": ["rất nhiều", "rat nhieu", "vận động viên"],
        }
        for eng_key, vi_terms in vietnamese_mapping.items():
            if any(term in normalized for term in vi_terms):
                return DEFAULT_ACTIVITY_FACTORS[eng_key]

        try:
            return float(normalized)
        except ValueError:
            return DEFAULT_ACTIVITY_FACTORS["default"]

    @staticmethod
    def _estimate_surplus(bmi: float, weight_gain_speed: str | None = None) -> float:
        """Compute caloric surplus for weight-gain goal.

        Fast gain speed yields 500–550 kcal to ensure severely underweight
        users (BMI < 16) can reach a nutritionally meaningful target.
        Vietnamese speed terms ("mạnh hơn", "nhanh hơn") are also mapped.
        """
        speed = str(weight_gain_speed or "").strip().lower()
        # Normalise common Vietnamese/mixed speed labels
        speed_surplus = {
            # Slow / nhẹ
            "slow": 250.0,
            "nhe": 250.0,
            "nhẹ": 250.0,
            "nhe on dinh": 250.0,
            "nhẹ, ổn định": 250.0,
            "nhe on": 250.0,
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
            "mạnh": 650.0,
            # "Mạnh hơn" / "Nhanh hơn" (stronger/faster) → higher surplus
            "manh hon": 750.0,
            "mạnh hơn": 750.0,
            "nhanh hon": 750.0,
            "nhanh hơn": 750.0,
            "faster": 750.0,
            "stronger": 750.0,
            "aggressive": 750.0,
        }
        if speed in speed_surplus:
            return speed_surplus[speed]
        # Partial match for Vietnamese compound phrases
        for key, value in speed_surplus.items():
            if key and key in speed:
                return value
        # BMI-based fallback
        if bmi < 16:
            return 500.0  # severely underweight → minimum meaningful surplus
        if bmi < 17.5:
            return 400.0
        if bmi < 18.5:
            return 250.0
        return 250.0

    @staticmethod
    def _normalize_sex(sex: str | None) -> str | None:
        if sex is None:
            return None
        normalized = sex.strip().lower()
        if normalized in {"m", "male", "nam"}:
            return "male"
        if normalized in {"f", "female", "nu"}:
            return "female"
        raise ValueError("sex must be male/female (or M/F).")

    def _estimate_target_nutrition(self, profile: UserProfile) -> dict[str, float]:
        activity_factor = self._activity_factor(profile.activity_level)
        height_m = profile.height_cm / 100.0
        bmi = profile.weight_kg / (height_m * height_m)

        # Mifflin-St Jeor BMR (same formula already in use, verified)
        if profile.age is not None and profile.sex is not None:
            sex = self._normalize_sex(profile.sex)
            if sex == "male":
                bmr = 10 * profile.weight_kg + 6.25 * profile.height_cm - 5 * profile.age + 5
            else:
                bmr = 10 * profile.weight_kg + 6.25 * profile.height_cm - 5 * profile.age - 161
        else:
            bmr = 24 * profile.weight_kg

        maintenance_kcal = bmr * activity_factor
        goal = str(profile.goal or "gain").strip().lower()
        surplus_kcal = profile.surplus_kcal
        if surplus_kcal is None:
            if goal == "lose":
                surplus_kcal = -350.0
            elif goal == "gain":
                surplus_kcal = self._estimate_surplus(bmi, profile.weight_gain_speed)
            else:
                surplus_kcal = 0.0
        else:
            surplus_kcal = float(surplus_kcal)
            if goal == "lose":
                surplus_kcal = -abs(surplus_kcal)
            elif goal in {"maintain", "maintenance"}:
                surplus_kcal = 0.0
            elif goal == "gain":
                surplus_kcal = abs(surplus_kcal)

        target_calories = maintenance_kcal + surplus_kcal
        if goal == "gain":
            target_calories = max(target_calories, maintenance_kcal)
        if goal != "gain" and profile.age is not None and profile.age >= 18:
            target_calories = max(target_calories, 1200.0)

        # ── Hard floors for severely underweight users ────────────────────────
        # A user with BMI < 16 pursuing fast/moderate gain MUST receive at least
        # TDEE + 350 kcal.
        if goal == "gain" and bmi < 16:
            is_slow = any(t in str(profile.weight_gain_speed or "").lower() for t in ("slow", "nhe", "nhẹ"))
            if not is_slow:
                min_fast_target = maintenance_kcal + 350.0
                target_calories = max(target_calories, min_fast_target)
        elif goal == "gain" and bmi < 17.5:
            min_target = maintenance_kcal + 300.0
            target_calories = max(target_calories, min_target)


        # Protein: keep recommendations near 1.6 g/kg, capped at 2.0 g/kg,
        # so calorie surplus is not accidentally filled by too many protein foods.
        protein_per_kg = 1.6
        protein_floor = 1.4 * profile.weight_kg
        protein_ceiling = 2.0 * profile.weight_kg
        target_protein = min(max(protein_floor, protein_per_kg * profile.weight_kg), protein_ceiling)

        target_fat = max(1.0 * profile.weight_kg, 0.30 * target_calories / 9.0)
        remaining_calories = target_calories - (target_protein * 4) - (target_fat * 9)
        target_carbs = max(remaining_calories / 4, 0.0)

        # Asian BMI status and medical warning
        display_bmi = round(bmi, 1)
        if display_bmi < 16:
            bmi_category = "underweight"
            bmi_status = "Gầy / thiếu cân"
            medical_warning = "BMI của bạn đang rất thấp. Thực đơn chỉ mang tính hỗ trợ, nên theo dõi cân nặng định kỳ và tham khảo chuyên gia dinh dưỡng khi cần."
        elif display_bmi < 18.5:
            bmi_category = "underweight"
            bmi_status = "Gầy / thiếu cân"
            medical_warning = None
        elif display_bmi < 23:
            bmi_category = "normal"
            bmi_status = "Bình thường"
            medical_warning = None
        elif display_bmi < 25:
            bmi_category = "overweight"
            bmi_status = "Thừa cân"
            medical_warning = None
        else:
            bmi_category = "obese"
            bmi_status = "Béo phì"
            medical_warning = None

        return {
            "calories": round(target_calories, 1),
            "protein": round(target_protein, 1),
            "fat": round(target_fat, 1),
            "carbs": round(target_carbs, 1),
            "bmi": round(bmi, 2),
            "bmr": round(bmr, 1),
            "tdee": round(maintenance_kcal, 1),
            "maintenance_kcal": round(maintenance_kcal, 1),
            "surplus_kcal": round(surplus_kcal, 1),
            "eligible": display_bmi < 18.5,
            "bmi_category": bmi_category,
            "bmi_label": bmi_status,
            "bmi_status": bmi_status,
            "medical_warning": medical_warning,
        }

    def _scale_profile_vector(self, target_nutrition: dict[str, float]) -> np.ndarray:
        assert self.feature_min is not None and self.feature_max is not None

        values = []
        for column in FEATURE_COLUMNS:
            min_value = float(self.feature_min[column])
            max_value = float(self.feature_max[column])
            target_value = float(target_nutrition[column])
            if max_value == min_value:
                values.append(0.0)
                continue
            scaled_value = (target_value - min_value) / (max_value - min_value)
            values.append(float(np.clip(scaled_value, 0.0, 1.0)))
        return np.array(values, dtype=float).reshape(1, -1)

    @staticmethod
    def _food_key_series(df: pd.DataFrame) -> pd.Series:
        name_col = "display_name_en" if "display_name_en" in df.columns else "name"
        return (
            df[name_col].astype(str).str.strip().str.lower()
            + "|"
            + df["category"].astype(str).str.strip().str.lower()
        )

    @staticmethod
    def meal_structure_for_complexity(complexity: str | None) -> dict[str, int]:
        normalized = str(complexity or "balanced").strip().lower()
        return dict(MEAL_STRUCTURE_PRESETS.get(normalized, DEFAULT_MEAL_STRUCTURE))

    @staticmethod
    def _daily_family_limit(family: str) -> int:
        if family in {"bean", "tofu", "soy"}:
            return 1
        if family in {"rice", "oat", "bread", "potato", "corn", "noodle", "pasta"}:
            return 2
        if family in {"milk", "yogurt", "cheese"}:
            return 1
        if family in {"vegetable", "fruit"}:
            return 3
        return 2

    @staticmethod
    def _macro_kcal(row: pd.Series | dict) -> float:
        protein = float(row.get("protein_raw", 0.0) or 0.0)
        fat = float(row.get("fat_raw", 0.0) or 0.0)
        carbs = float(row.get("carbs_raw", 0.0) or 0.0)
        return protein * 4.0 + carbs * 4.0 + fat * 9.0

    @staticmethod
    def _nutrient_value(row: pd.Series | dict, nutrient: str) -> float:
        return float(row.get(f"{nutrient}_raw", row.get(nutrient, 0.0)) or 0.0)

    @classmethod
    def _has_abnormal_macro_profile(cls, row: pd.Series | dict) -> bool:
        text = cls._row_name(row)
        category = cls._semantic_category(row.get("category", ""), text)
        calories = cls._nutrient_value(row, "calories")
        protein = cls._nutrient_value(row, "protein")
        fat = cls._nutrient_value(row, "fat")
        carbs = cls._nutrient_value(row, "carbs")
        macro_kcal = protein * 4.0 + carbs * 4.0 + fat * 9.0

        if calories <= 0 or macro_kcal <= 0:
            return True
        if category in {"meat", "egg"} and carbs > max(8.0, protein * 0.35):
            return True
        if "raw" in text and category in {"meat", "egg", "plant_protein"}:
            return True
        if "taro leaves" in text and "raw" in text:
            return True
        if category in {"meat", "egg", "plant_protein"} and protein > 45.0:
            return True
        if category == "healthy_fat" and cls._contains_any(text, ("peanut", "almond", "walnut", "nut", "butter")) and fat < 10.0:
            return True
        if cls._contains_any(text, ("peanut butter", "peanuts", "almond", "walnut")) and fat < 10.0:
            return True
        if category == "fruit" and fat > max(8.0, carbs * 0.5):
            return True
        return False

    @classmethod
    def _max_serving_grams(cls, row: pd.Series | dict) -> float:
        text = cls._row_name(row)
        text_no_accent = cls._strip_accents(text).lower()
        category = cls._semantic_category(row.get("category", ""), text)

        if cls._contains_any(text_no_accent, ("peanut butter", "peanuts", "almond", "walnut", "nuts", "olive", "olives")):
            return 35.0
        if cls._contains_any(text_no_accent, ("cheese", "pho mai")):
            return 80.0
        if cls._contains_any(text_no_accent, ("avocado",)):
            return 120.0
        if category == "healthy_fat":
            return 45.0
        if cls._contains_any(text, ("soybean", "soybeans", "Ä‘áº­u nÃ nh", "dau nanh")):
            return 160.0
        if category in {"meat", "egg", "plant_protein"}:
            return 180.0
        if category == "grain":
            return 220.0
        if category == "dairy":
            return 250.0
        if category == "fruit":
            return 180.0
        if category == "vegetable":
            return 250.0
        return 220.0

    @classmethod
    def _cap_row_serving(cls, row: pd.Series) -> pd.Series:
        serving_grams = float(row.get("serving_grams", 100.0) or 100.0)
        max_grams = cls._max_serving_grams(row)
        if serving_grams <= max_grams or serving_grams <= 0:
            return row

        scale = max_grams / serving_grams
        for nutrient_col in ("calories_raw", "protein_raw", "fat_raw", "carbs_raw"):
            if nutrient_col in row:
                row[nutrient_col] = float(row[nutrient_col]) * scale
        row["serving_grams"] = max_grams
        if "serving_multiplier" in row:
            row["serving_multiplier"] = float(row.get("serving_multiplier", 1.0) or 1.0) * scale
        return row

    @classmethod
    def _apply_serving_caps_to_plan(cls, plan: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
        capped: dict[str, pd.DataFrame] = {}
        for meal, meal_df in plan.items():
            if meal_df.empty:
                capped[meal] = meal_df
                continue
            capped[meal] = meal_df.copy().apply(cls._cap_row_serving, axis=1)
        return capped

    @staticmethod
    def _normalize_macro_calories(row: pd.Series, tolerance: float = 0.05) -> pd.Series:
        macro_kcal = HealthyWeightGainRecommender._macro_kcal(row)
        calories = float(row.get("calories_raw", 0.0) or 0.0)
        if macro_kcal > 0 and calories > 0:
            relative_gap = abs(calories - macro_kcal) / calories
            if relative_gap > tolerance:
                row["calories_raw"] = macro_kcal
        elif macro_kcal > 0:
            row["calories_raw"] = macro_kcal
        return row

    @staticmethod
    def _normalize_plan_macro_calories(plan: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
        normalized: dict[str, pd.DataFrame] = {}
        for meal, meal_df in plan.items():
            if meal_df.empty:
                normalized[meal] = meal_df
                continue
            next_df = meal_df.copy()
            next_df = next_df.apply(HealthyWeightGainRecommender._normalize_macro_calories, axis=1)
            normalized[meal] = next_df
        return normalized

    @staticmethod
    def _scale_plan_energy_if_needed(
        plan: dict[str, pd.DataFrame],
        target_calories: float,
        min_ratio: float = 0.95,
        max_ratio: float = 1.05,
    ) -> dict[str, pd.DataFrame]:
        current_calories = sum(
            float(meal_df["calories_raw"].sum())
            for meal_df in plan.values()
            if "calories_raw" in meal_df.columns and not meal_df.empty
        )
        min_calories = float(target_calories) * min_ratio
        max_calories = float(target_calories) * max_ratio
        if current_calories <= 0 or min_calories <= current_calories <= max_calories:
            return plan

        scale = min(max(float(target_calories) / current_calories, 0.8), 1.2)
        scaled: dict[str, pd.DataFrame] = {}
        for meal, meal_df in plan.items():
            if meal_df.empty:
                scaled[meal] = meal_df
                continue

            next_df = meal_df.copy()
            for row_idx, row in next_df.iterrows():
                serving_grams = float(row.get("serving_grams", 100.0) or 100.0)
                max_grams = HealthyWeightGainRecommender._max_serving_grams(row)
                row_scale = scale
                if serving_grams > 0 and row_scale >= 1.0:
                    row_scale = min(row_scale, max_grams / serving_grams)
                row_scale = max(row_scale, 1.0) if scale >= 1.0 else min(row_scale, 1.0)
                row_scale = max(row_scale, 0.8)
                for nutrient_col in ("calories_raw", "protein_raw", "fat_raw", "carbs_raw"):
                    if nutrient_col in next_df.columns:
                        next_df.at[row_idx, nutrient_col] = float(row[nutrient_col]) * row_scale
                if "serving_multiplier" in next_df.columns:
                    next_df.at[row_idx, "serving_multiplier"] = float(row.get("serving_multiplier", 1.0) or 1.0) * row_scale
                if "serving_grams" in next_df.columns:
                    next_df.at[row_idx, "serving_grams"] = min(serving_grams * row_scale, max_grams) if row_scale >= 1.0 else serving_grams * row_scale
            scaled[meal] = next_df
        capped = HealthyWeightGainRecommender._apply_serving_caps_to_plan(scaled)
        return HealthyWeightGainRecommender._normalize_plan_macro_calories(capped)

    @staticmethod
    def _rebalance_plan_macros_for_weight_gain(
        plan: dict[str, pd.DataFrame],
        target_nutrition: dict[str, float],
    ) -> dict[str, pd.DataFrame]:
        next_plan = {meal: meal_df.copy() for meal, meal_df in plan.items()}

        def totals(column: str) -> float:
            return sum(
                float(meal_df[column].sum())
                for meal_df in next_plan.values()
                if column in meal_df.columns and not meal_df.empty
            )

        protein_cap = float(target_nutrition.get("protein", 0.0)) * 1.25
        current_protein = totals("protein_raw")
        if protein_cap > 0 and current_protein > protein_cap:
            excess = current_protein - protein_cap
            protein_rows: list[tuple[str, object, pd.Series]] = []
            for meal, meal_df in next_plan.items():
                for idx, row in meal_df.iterrows():
                    if HealthyWeightGainRecommender._culinary_role(row) == "protein":
                        protein_rows.append((meal, idx, row))
            protein_rows.sort(key=lambda item: float(item[2].get("protein_raw", 0.0) or 0.0), reverse=True)
            for meal, idx, row in protein_rows:
                if excess <= 0:
                    break
                protein = float(row.get("protein_raw", 0.0) or 0.0)
                if protein <= 0:
                    continue
                max_reduction = protein * 0.25
                reduction = min(excess, max_reduction)
                scale = max((protein - reduction) / protein, 0.75)
                for nutrient_col in ("calories_raw", "protein_raw", "fat_raw", "carbs_raw"):
                    if nutrient_col in next_plan[meal].columns:
                        next_plan[meal].at[idx, nutrient_col] = float(row[nutrient_col]) * scale
                if "serving_multiplier" in next_plan[meal].columns:
                    next_plan[meal].at[idx, "serving_multiplier"] = float(row.get("serving_multiplier", 1.0) or 1.0) * scale
                if "serving_grams" in next_plan[meal].columns:
                    next_plan[meal].at[idx, "serving_grams"] = float(row.get("serving_grams", 100.0) or 100.0) * scale
                excess -= reduction

        fat_floor = float(target_nutrition.get("fat", 0.0)) * 0.85
        current_fat = totals("fat_raw")
        if fat_floor > 0 and current_fat < fat_floor:
            fat_rows: list[tuple[str, object, pd.Series]] = []
            for meal, meal_df in next_plan.items():
                for idx, row in meal_df.iterrows():
                    if HealthyWeightGainRecommender._culinary_role(row) == "fat":
                        fat_rows.append((meal, idx, row))
            needed_fat = fat_floor - current_fat
            fat_rows.sort(key=lambda item: float(item[2].get("fat_raw", 0.0) or 0.0), reverse=True)
            for meal, idx, row in fat_rows:
                if needed_fat <= 0:
                    break
                fat = float(row.get("fat_raw", 0.0) or 0.0)
                serving_grams = float(row.get("serving_grams", 100.0) or 100.0)
                if fat <= 0 or serving_grams <= 0:
                    continue
                max_scale = min(1.8, HealthyWeightGainRecommender._max_serving_grams(row) / serving_grams)
                if max_scale <= 1.0:
                    continue
                added_fat_at_max = fat * (max_scale - 1.0)
                scale = 1.0 + min(needed_fat, added_fat_at_max) / fat
                for nutrient_col in ("calories_raw", "protein_raw", "fat_raw", "carbs_raw"):
                    if nutrient_col in next_plan[meal].columns:
                        next_plan[meal].at[idx, nutrient_col] = float(row[nutrient_col]) * scale
                if "serving_multiplier" in next_plan[meal].columns:
                    next_plan[meal].at[idx, "serving_multiplier"] = float(row.get("serving_multiplier", 1.0) or 1.0) * scale
                if "serving_grams" in next_plan[meal].columns:
                    next_plan[meal].at[idx, "serving_grams"] = serving_grams * scale
                needed_fat -= fat * (scale - 1.0)

        capped = HealthyWeightGainRecommender._apply_serving_caps_to_plan(next_plan)
        return HealthyWeightGainRecommender._normalize_plan_macro_calories(capped)

    @staticmethod
    def _plan_macro_total(plan: dict[str, pd.DataFrame], column: str) -> float:
        return sum(
            float(meal_df[column].sum())
            for meal_df in plan.values()
            if column in meal_df.columns and not meal_df.empty
        )

    @classmethod
    def _portion_row_for_slot(cls, row: pd.Series, target_kcal: float, max_multiplier: float = 2.0) -> pd.Series:
        next_row = row.copy()
        base_calories = max(cls._macro_kcal(next_row) or float(next_row.get("calories_raw", 0.0) or 0.0), 1.0)
        max_serving_multiplier = max(cls._max_serving_grams(next_row) / 100.0, 0.15)
        serving_multiplier = float(np.clip(target_kcal / base_calories, 0.15, min(max_multiplier, max_serving_multiplier)))
        for nutrient_col in ("calories_raw", "protein_raw", "fat_raw", "carbs_raw"):
            if nutrient_col in next_row:
                next_row[nutrient_col] = float(next_row[nutrient_col]) * serving_multiplier
        next_row = cls._normalize_macro_calories(next_row)
        next_row["serving_multiplier"] = serving_multiplier
        base_serving_grams = float(next_row.get("base_serving_grams", next_row.get("quantity_g", 100.0)) or 100.0)
        next_row["serving_grams"] = round(serving_multiplier * base_serving_grams, 0)
        next_row = cls._cap_row_serving(next_row)
        next_row["culinary_role"] = cls._culinary_role(next_row)
        return next_row

    @classmethod
    def _replace_low_fat_extras(
        cls,
        plan: dict[str, pd.DataFrame],
        candidates_df: pd.DataFrame,
        target_nutrition: dict[str, float],
    ) -> dict[str, pd.DataFrame]:
        fat_floor = float(target_nutrition.get("fat", 0.0) or 0.0) * 0.85
        if fat_floor <= 0 or cls._plan_macro_total(plan, "fat_raw") >= fat_floor:
            return plan
        if candidates_df.empty:
            return plan

        next_plan = {meal: meal_df.copy() for meal, meal_df in plan.items()}
        used_food_ids = {
            str(row.get("food_id", ""))
            for meal_df in next_plan.values()
            for _, row in meal_df.iterrows()
        }
        used_family_counts: dict[str, int] = {}
        for meal_df in next_plan.values():
            for _, row in meal_df.iterrows():
                family = cls._food_family(row)
                if family:
                    used_family_counts[family] = used_family_counts.get(family, 0) + 1
        candidate_pool = candidates_df.copy()
        if "food_id" in candidate_pool.columns:
            candidate_pool = candidate_pool[~candidate_pool["food_id"].astype(str).isin(used_food_ids)]
        candidate_pool = candidate_pool[
            candidate_pool["category"].astype(str).str.lower().ne("drink_natural")
            & candidate_pool["category"].astype(str).str.lower().ne("junk_food")
        ].copy()
        if candidate_pool.empty:
            return next_plan

        candidate_pool["_extra_score"] = candidate_pool.apply(cls._healthy_energy_extra_score, axis=1)
        candidate_pool = candidate_pool[candidate_pool["_extra_score"] > 0.0].copy()
        if candidate_pool.empty:
            return next_plan
        max_fat = float(candidate_pool["fat_raw"].astype(float).max() or 1.0)
        candidate_pool["_fat_fix_score"] = (
            candidate_pool["_extra_score"]
            + candidate_pool["fat_raw"].astype(float) / max_fat
            + candidate_pool.apply(cls._is_good_fat_row, axis=1).astype(float) * 0.75
        )
        candidate_pool = candidate_pool.sort_values("_fat_fix_score", ascending=False)

        for meal, meal_df in list(next_plan.items()):
            if meal_df.empty or cls._plan_macro_total(next_plan, "fat_raw") >= fat_floor:
                continue

            replace_idx = None
            for idx in reversed(list(meal_df.index)):
                role = cls._culinary_role(meal_df.loc[idx])
                if role in {"fat", "side", "drink", "drink_or_extra"}:
                    replace_idx = idx
                    break
            if replace_idx is None and len(meal_df.index) >= 4:
                replace_idx = meal_df.index[-1]
            if replace_idx is None:
                continue

            current_row = meal_df.loc[replace_idx]
            current_fat = float(current_row.get("fat_raw", 0.0) or 0.0)
            current_kcal = float(current_row.get("calories_raw", 0.0) or 0.0)
            replacement = None
            for enforce_family_limit in (False,):
                for _, candidate in candidate_pool.iterrows():
                    candidate_id = str(candidate.get("food_id", ""))
                    if candidate_id in used_food_ids:
                        continue
                    candidate_family = cls._food_family(candidate)
                    if enforce_family_limit and candidate_family and used_family_counts.get(candidate_family, 0) >= 2:
                        continue
                    portioned = cls._portion_row_for_slot(candidate, max(current_kcal, 150.0), max_multiplier=1.8)
                    if float(portioned.get("fat_raw", 0.0) or 0.0) > current_fat + 1.0:
                        replacement = portioned
                        used_food_ids.add(candidate_id)
                        if candidate_family:
                            used_family_counts[candidate_family] = used_family_counts.get(candidate_family, 0) + 1
                        break
                if replacement is not None:
                    break
            if replacement is None:
                continue

            replacement = replacement.drop(labels=["_food_key", "_slot_score", "_extra_score", "_fat_fix_score"], errors="ignore")
            for column in replacement.index:
                if column not in next_plan[meal].columns:
                    next_plan[meal][column] = np.nan
            for column in next_plan[meal].columns:
                next_plan[meal].at[replace_idx, column] = replacement.get(column, np.nan)

        cleaned: dict[str, pd.DataFrame] = {}
        for meal, meal_df in next_plan.items():
            cleaned[meal] = meal_df.drop(
                columns=["_food_key", "_slot_score", "_extra_score", "_fat_fix_score"],
                errors="ignore",
            )
        return cls._normalize_plan_macro_calories(cleaned)

    def recommend(
        self,
        profile: UserProfile,
        top_n: int = 10,
        preferred_categories: Sequence[str] | None = None,
        excluded_categories: Sequence[str] | None = None,
        category_preferences: dict[str, float] | None = None,
    ) -> pd.DataFrame:
        self._ensure_fitted()
        assert self.merged_df is not None and self.feature_matrix is not None

        target_nutrition = self._estimate_target_nutrition(profile)
        if not target_nutrition.get("eligible", True):
            raise ValueError("NutriGain chỉ hỗ trợ tạo thực đơn tăng cân cho người thiếu cân có BMI dưới 18.5.")
        user_vector = self._scale_profile_vector(target_nutrition)
        all_scores = cosine_similarity(user_vector, self.feature_matrix).ravel()

        diet_type_str = getattr(profile, "diet_type", None)
        print("[VEGETARIAN FILTER INPUT]", {
            "user_id": getattr(profile, "user_id", None),
            "diet_type": diet_type_str,
            "items_per_meal": getattr(profile, "items_per_meal", None),
        })

        all_foods = self.merged_df.copy()
        score_by_food_id = {str(row.get("food_id")): score for (_, row), score in zip(all_foods.iterrows(), all_scores)}

        after_eligible = all_foods.copy()

        if str(diet_type_str).strip().lower() in {"vegetarian", "vegan", "ăn chay", "an chay", "vegetarianism"}:
            veg_mask = after_eligible.apply(is_non_vegetarian_food, axis=1)
            after_vegetarian = after_eligible[~veg_mask].copy()
            if after_vegetarian.empty:
                after_vegetarian = after_eligible.copy()
        else:
            after_vegetarian = after_eligible.copy()

        after_disliked = after_vegetarian.copy()
        result_df = after_disliked.copy()

        print("[RECOMMENDER CANDIDATE FILTER COUNTS]", {
            "all_foods": len(all_foods),
            "after_eligible": len(after_eligible),
            "after_vegetarian": len(after_vegetarian),
            "after_disliked": len(after_disliked),
            "final_candidates": len(result_df),
        })

        candidate_scores = np.array([score_by_food_id.get(str(row.get("food_id")), 0.0) for _, row in result_df.iterrows()])

        target_calories = float(target_nutrition["calories"])
        meal_slots = max(1, sum(DEFAULT_MEAL_STRUCTURE.values()))
        per_item_target = max(target_calories / meal_slots, 1.0)

        calories_raw = result_df["calories_raw"].astype(float).values
        calorie_gap = np.abs(calories_raw - per_item_target) / per_item_target
        calorie_alignment = 1.0 - np.clip(calorie_gap, 0.0, 1.0)

        macro_targets_per_item = {
            "protein": max(float(target_nutrition["protein"]) / meal_slots, 1.0),
            "fat": max(float(target_nutrition["fat"]) / meal_slots, 1.0),
            "carbs": max(float(target_nutrition["carbs"]) / meal_slots, 1.0),
        }
        protein_gap = np.abs(result_df["protein_raw"].astype(float).values - macro_targets_per_item["protein"]) / macro_targets_per_item["protein"]
        fat_gap = np.abs(result_df["fat_raw"].astype(float).values - macro_targets_per_item["fat"]) / macro_targets_per_item["fat"]
        carbs_gap = np.abs(result_df["carbs_raw"].astype(float).values - macro_targets_per_item["carbs"]) / macro_targets_per_item["carbs"]
        macro_alignment = 1.0 - np.clip(
            # Balanced macros for weight gain: protein = fat = carbs in importance
            0.35 * protein_gap + 0.30 * fat_gap + 0.35 * carbs_gap,
            0.0,
            1.0,
        )

        preference_scores = candidate_scores
        nutrition_scores = 0.15 * calorie_alignment + 0.45 * macro_alignment
        diversity_scores = np.zeros(len(result_df))
        budget_scores = np.zeros(len(result_df))

        print("[RECOMMENDER SCORE SHAPES]", {
            "candidate_foods": len(result_df),
            "nutrition_scores": len(nutrition_scores),
            "preference_scores": len(preference_scores),
            "diversity_scores": len(diversity_scores),
            "budget_scores": len(budget_scores),
        })

        def assert_same_length(label, expected_len, **arrays):
            bad = {name: len(value) for name, value in arrays.items() if value is not None and len(value) != expected_len}
            if bad:
                print("[RECOMMENDER SHAPE MISMATCH]", {
                    "label": label,
                    "expected_len": expected_len,
                    "bad": bad,
                })
                raise ValueError(f"Score arrays length mismatch at {label}: expected {expected_len}, got {bad}")

        assert_same_length(
            "final score combine",
            len(result_df),
            nutrition_scores=nutrition_scores,
            preference_scores=preference_scores,
            diversity_scores=diversity_scores,
            budget_scores=budget_scores,
        )

        result_df["score"] = (
            0.40 * preference_scores
            + nutrition_scores
            + diversity_scores
            + budget_scores
        )

        quality_score = result_df.apply(self._food_quality_score, axis=1)
        result_df["score"] = result_df["score"] + 0.08 * quality_score
        verified_image_boost = result_df.apply(self._has_valid_image_url, axis=1).astype(float)
        result_df["score"] = result_df["score"] + 0.04 * verified_image_boost
        
        category_scores: dict[str, float] = {}
        if category_preferences:
            category_scores.update(category_preferences)

        model_category_scores = self._predict_category_preferences(profile)
        for category, value in model_category_scores.items():
            category_scores[category] = category_scores.get(category, 0.0) + 0.5 * value

        if category_scores:
            category_boost = result_df["category"].str.lower().map(
                lambda category: category_scores.get(category, 0.0)
            )
            result_df["score"] = result_df["score"] + 0.07 * category_boost.fillna(0.0)

        generic_name_boost = result_df["name"].astype(str).str.lower().apply(
            lambda text: 1.0 if any(term in text for term in ("stew", "reduced fat")) else 0.0
        )
        result_df["score"] = result_df["score"] + 0.03 * generic_name_boost

        result_df["target_calories"] = target_nutrition["calories"]
        result_df["target_protein"] = target_nutrition["protein"]
        result_df["target_fat"] = target_nutrition["fat"]
        result_df["target_carbs"] = target_nutrition["carbs"]
        result_df["bmi"] = target_nutrition["bmi"]
        result_df["maintenance_kcal"] = target_nutrition["maintenance_kcal"]

        if excluded_categories:
            excluded_set = {category.lower() for category in excluded_categories}
            result_df = result_df[~result_df["category"].str.lower().isin(excluded_set)]

        disliked_terms = tuple(str(term).strip() for term in (profile.disliked_foods or ()) if str(term).strip())
        if disliked_terms:
            disliked_mask = result_df.apply(
                lambda row: self._row_matches_preference_terms(row, disliked_terms),
                axis=1,
            )
            result_df = result_df[~disliked_mask].copy()

        disliked_groups = tuple(
            self._normalized_search_text(term)
            for term in (profile.disliked_food_groups or ())
            if self._normalized_search_text(term)
        )
        if disliked_groups:
            group_mask = result_df.apply(
                lambda row: any(
                    group in self._normalized_search_text(
                        f"{row.get('category', '')} {row.get('clean_category', '')} {row.get('food_group', '')}"
                    )
                    for group in disliked_groups
                ),
                axis=1,
            )
            result_df = result_df[~group_mask].copy()

        blocked_mask = result_df["name"].astype(str).str.lower().apply(
            lambda text: any(term in text for term in BLOCKED_NAME_TERMS)
        )
        result_df = result_df[~blocked_mask]

        dirty_bulk_mask = result_df["name"].astype(str).str.lower().apply(self._is_dirty_bulk_name)
        result_df = result_df[~dirty_bulk_mask]
        seasoning_mask = result_df.apply(self._is_seasoning_row, axis=1)
        result_df = result_df[~seasoning_mask]
        abnormal_macro_mask = result_df.apply(self._has_abnormal_macro_profile, axis=1)
        result_df = result_df[~abnormal_macro_mask]
        if "category" in result_df.columns:
            result_df = result_df[result_df["category"].astype(str).str.lower() != "junk_food"]

        unfamiliar_mask = result_df["name"].astype(str).str.lower().apply(
            lambda text: any(term in text for term in UNFAMILIAR_NAME_TERMS)
        )
        result_df = result_df[~unfamiliar_mask]

        # ── Hard filter: drinks / juices can NEVER fill non-drink slots ────────
        # Remove all drink/beverage items from the main candidate pool so they
        # cannot accidentally score their way into grain / protein / vegetable
        # / fruit slots during meal plan assembly.
        drink_mask = result_df["name"].astype(str).str.lower().apply(
            lambda n: any(t in n for t in DRINK_BEVERAGE_TERMS)
        ) | result_df["category"].astype(str).str.lower().isin({"drink_natural"})
        result_df = result_df[~drink_mask].copy()

        # ── Fresh fruit boost ────────────────────────────────────────────────
        # Whole fruit gets a significant scoring advantage over juices/drinks.
        fresh_fruit_boost = result_df["name"].astype(str).str.lower().apply(
            lambda n: 0.18 if any(t in n for t in FRESH_FRUIT_TERMS) else 0.0
        ) * result_df["category"].astype(str).str.lower().isin({"fruit"}).astype(float)
        result_df["score"] = result_df["score"] + fresh_fruit_boost

        # ── Familiar Vietnamese food boost ───────────────────────────────────
        familiar_boost = result_df["name"].astype(str).str.lower().apply(
            lambda text: 1.0 if any(term in text for term in FAMILIAR_NAME_TERMS) else 0.0
        )
        result_df["score"] = result_df["score"] + 0.08 * familiar_boost

        # ── Exotic / hard-to-find food penalty ──────────────────────────────
        # Items that are rare or culturally unfamiliar to Vietnamese everyday
        # eating are penalised so accessible alternatives rank higher.
        _exotic_name_terms = (
            "fermented salmon", "ca hoi len men",
            "herring roe", "trung ca trich",
            "caviar", "surstromming", "gravlax",
            "dandelion", "rau bo cong anh",
            "chicory", "endive", "radicchio",
            "tilsit", "emmental", "raclette", "gruyere",
            "camembert", "brie", "dry cheese", "pho mai kho",
            "cottage cheese", "ricotta",
            "offal", "organ meat", "sweetbread", "foie gras",
            "noi tang",
        )
        exotic_penalty_vec = result_df["name"].astype(str).str.lower().apply(
            lambda n: 1.0 if any(t in n for t in _exotic_name_terms) else 0.0
        )
        result_df["score"] = result_df["score"] - 0.35 * exotic_penalty_vec

        carb_density = result_df["carbs_raw"].astype(float) / np.maximum(result_df["calories_raw"].astype(float), 1.0)
        carb_support_mask = result_df["category"].astype(str).str.lower().isin({"grain", "fruit", "vegetable", "dairy", "plant_protein"})
        clean_carb_boost = result_df.apply(lambda row: 1.0 if self._is_clean_carb_row(row) else 0.0, axis=1)
        result_df["score"] = (
            result_df["score"]
            + 0.04 * np.clip(carb_density, 0.0, 0.40) * carb_support_mask.astype(float)
            + 0.05 * clean_carb_boost
        )

        # Smart rule: boost protein-dense foods for weight gain
        # g protein per 100 kcal — higher is better for muscle building
        prot_density = result_df["protein_raw"].astype(float) / np.maximum(result_df["calories_raw"].astype(float), 1.0) * 100.0
        protein_cat_mask = result_df["category"].astype(str).str.lower().isin({"meat", "egg", "plant_protein", "dairy", "other"})
        clean_protein_boost = result_df.apply(lambda row: 1.0 if self._is_lean_protein_row(row) else 0.0, axis=1)
        good_fat_boost = result_df.apply(lambda row: 1.0 if self._is_good_fat_row(row) else 0.0, axis=1)
        result_df["score"] = (
            result_df["score"]
            + 0.10 * np.clip(prot_density / 30.0, 0.0, 1.0) * protein_cat_mask.astype(float)
            + 0.07 * clean_protein_boost
            + 0.12 * good_fat_boost
        )

        lower_item_bound = max(per_item_target * 0.25, 80.0)
        upper_item_bound = max(per_item_target * 2.2, 500.0)
        effective_calories = result_df.apply(
            lambda row: min(
                float(row.get("calories_raw", 0.0) or 0.0),
                float(row.get("calories_raw", 0.0) or 0.0)
                * (HealthyWeightGainRecommender._max_serving_grams(row) / 100.0),
            ),
            axis=1,
        )
        result_df = result_df[
            (effective_calories >= lower_item_bound)
            & (effective_calories <= upper_item_bound)
        ]

        result_df = result_df.copy()
        result_df["_food_key"] = self._food_key_series(result_df)
        result_df = result_df.drop_duplicates(subset=["_food_key"], keep="first")
        result_df = result_df.drop(columns=["_food_key"])

        return result_df.sort_values("score", ascending=False).head(top_n)

    @staticmethod
    def build_daily_meal_plan(
        ranked_df: pd.DataFrame,
        meal_structure: dict[str, int] | None = None,
        target_calories: float | None = None,
        target_nutrition: dict[str, float] | None = None,
    ) -> dict[str, pd.DataFrame]:
        """Role-based meal planner.

        Each meal slot has a defined role (grain / protein / vegetable / extra).
        Items are selected to fill roles in order, ensuring every meal is
        structurally coherent (rice + meat + vegetable) before calorie matching
        applies as a secondary criterion.
        """
        structure = meal_structure or DEFAULT_MEAL_STRUCTURE
        if ranked_df.empty:
            return {meal: ranked_df.iloc[0:0].copy() for meal in structure}

        working_df = ranked_df.copy()
        working_df["_food_key"] = HealthyWeightGainRecommender._food_key_series(working_df)
        dirty_mask = working_df["name"].astype(str).str.lower().apply(
            HealthyWeightGainRecommender._is_dirty_bulk_name
        )
        seasoning_mask = working_df.apply(HealthyWeightGainRecommender._is_seasoning_row, axis=1)
        abnormal_macro_mask = working_df.apply(HealthyWeightGainRecommender._has_abnormal_macro_profile, axis=1)
        working_df = working_df[~dirty_mask & ~seasoning_mask & ~abnormal_macro_mask].copy()
        working_df = working_df[
            working_df["category"].astype(str).str.lower() != "junk_food"
        ].copy()
        # ── Hard exclude drinks / juices / beverages from all meal slots ──────
        # drink_natural items and anything named as a juice/beverage must not
        # appear in grain / protein / vegetable / fruit slots.
        drink_name_mask = working_df["name"].astype(str).str.lower().apply(
            lambda n: any(t in n for t in DRINK_BEVERAGE_TERMS)
        )
        drink_cat_mask = working_df["category"].astype(str).str.lower().isin({"drink_natural"})
        working_df = working_df[~drink_name_mask & ~drink_cat_mask].copy()
        # ─────────────────────────────────────────────────────────────────────
        if "clean_category" in working_df.columns:
            working_df = working_df[
                working_df["clean_category"].astype(str).str.lower() != "vegetable_herb"
            ].copy()
        working_df = working_df.sort_values("score", ascending=False).reset_index(drop=True)
        if working_df.empty:
            return {meal: ranked_df.iloc[0:0].copy() for meal in structure}

        if target_calories is None:
            target_calories = float(working_df["calories_raw"].head(10).sum())
        if target_nutrition is None:
            target_nutrition = {
                "calories": float(target_calories),
                "protein": max(float(target_calories) * 0.15 / 4.0, 1.0),
                "fat": max(float(target_calories) * 0.25 / 9.0, 1.0),
                "carbs": max(float(target_calories) * 0.60 / 4.0, 1.0),
            }

        ratio_sum = sum(DEFAULT_MEAL_CALORIE_RATIOS.get(m, 0.0) for m in structure) or float(len(structure))
        seen_food_keys: set[str] = set()   # dedup by English food key
        seen_display_names: set[str] = set()  # dedup by Vietnamese display name
        daily_family_counts: dict[str, int] = {}
        daily_category_counts: dict[str, int] = {}
        plan: dict[str, pd.DataFrame] = {}

        for meal in structure:
            full_slot_roles = MEAL_SLOT_ROLES.get(meal, [[]])
            requested_slots = max(1, int(structure.get(meal, len(full_slot_roles))))
            slot_roles = full_slot_roles[: min(requested_slots, len(full_slot_roles))]
            raw_slot_weights = MEAL_SLOT_CALORIE_WEIGHTS.get(meal, [])[: len(slot_roles)]
            weight_sum = sum(raw_slot_weights) or 1.0
            slot_weights = [float(weight) / weight_sum for weight in raw_slot_weights]
            meal_ratio = DEFAULT_MEAL_CALORIE_RATIOS.get(meal, 1.0 / len(structure)) / ratio_sum
            meal_target = float(target_calories) * meal_ratio
            n_slots = len(slot_roles)
            selected_rows: list[pd.Series] = []
            selected_carb_families: set[str] = set()
            selected_food_families: set[str] = set()
            savory_staple_selected = False
            remaining_kcal = meal_target

            for slot_idx in range(n_slots):
                allowed_cats = set(slot_roles[slot_idx]) if slot_idx < len(slot_roles) else set()
                required_role = MEAL_SLOT_CULINARY_ROLES.get(meal, [])[slot_idx] if slot_idx < len(MEAL_SLOT_CULINARY_ROLES.get(meal, [])) else ""
                slot_weight = slot_weights[slot_idx] if slot_idx < len(slot_weights) else 1.0 / n_slots
                slot_target_kcal = meal_target * slot_weight

                # --- Build candidate pool (role-filtered, no duplicates) ---
                # Filter by food_key AND by display name to prevent same Vietnamese
                # name appearing twice (e.g. two "Sữa đậu nành" entries with
                # different English names but same translated display name).
                avail = working_df[
                    ~working_df["_food_key"].isin(seen_food_keys)
                    & ~working_df["name"].astype(str).str.strip().str.lower().isin(seen_display_names)
                ].copy()
                variety_avail = avail[
                    ~avail.apply(
                        lambda row: (
                            daily_family_counts.get(HealthyWeightGainRecommender._food_family(row), 0)
                            >= HealthyWeightGainRecommender._daily_family_limit(
                                HealthyWeightGainRecommender._food_family(row)
                            )
                        )
                        or (
                            daily_category_counts.get(str(row.get("category", "")).strip().lower(), 0)
                            >= MAX_DAILY_CATEGORY_REPEAT.get(
                                str(row.get("category", "")).strip().lower(),
                                MAX_DAILY_CATEGORY_REPEAT["other"],
                            )
                        ),
                        axis=1,
                    )
                ]
                if not variety_avail.empty:
                    avail = variety_avail
                pool = avail[avail["category"].str.lower().isin(allowed_cats)] if allowed_cats else avail
                if pool.empty:
                    pool = avail  # fallback: relax category constraint

                if required_role:
                    role_pool = pool[pool.apply(
                        lambda row: HealthyWeightGainRecommender._culinary_role(row) == required_role,
                        axis=1,
                    )]
                    if not role_pool.empty:
                        pool = role_pool
                    else:
                        wider_role_pool = avail[avail.apply(
                            lambda row: HealthyWeightGainRecommender._culinary_role(row) == required_role,
                            axis=1,
                        )]
                        if not wider_role_pool.empty:
                            pool = wider_role_pool
                        elif required_role in {"fruit", "vegetable"}:
                            continue

                if required_role in {"fruit", "vegetable"}:
                    main_produce_pool = pool[
                        pool["category"].astype(str).str.lower().isin({"fruit", "vegetable"})
                        & (pool.get("clean_category", "").astype(str).str.lower() != "vegetable_herb")
                        # Explicitly exclude drinks/juices from produce slots
                        & ~pool["category"].astype(str).str.lower().isin({"drink_natural"})
                        & ~pool["name"].astype(str).str.lower().apply(
                            lambda n: any(t in n for t in ("juice", "nuoc ep", "nước ép", "nuoc cam", "nước cam", "nuoc tao", "apple juice"))
                        )
                    ]
                    if not main_produce_pool.empty:
                        pool = main_produce_pool

                if selected_food_families:
                    family_pool = pool[
                        ~pool.apply(
                            lambda row: HealthyWeightGainRecommender._food_family(row) in selected_food_families,
                            axis=1,
                        )
                    ]
                    if not family_pool.empty:
                        pool = family_pool
                    else:
                        wider_family_pool = avail[
                            ~avail.apply(
                                lambda row: HealthyWeightGainRecommender._food_family(row) in selected_food_families,
                                axis=1,
                            )
                        ]
                        if not wider_family_pool.empty:
                            pool = wider_family_pool
                        else:
                            continue

                # Culinary coherence: if the meal starts with a savory staple
                # such as pasta/noodles/rice, do not pair it with yogurt/parfait
                # as the protein/fat side in the same meal.
                if savory_staple_selected and required_role in {"protein", "fat"}:
                    savory_pool = pool[
                        ~pool.apply(HealthyWeightGainRecommender._is_sweet_or_cold_side, axis=1)
                    ]
                    if not savory_pool.empty:
                        pool = savory_pool

                if meal == "breakfast":
                    breakfast_pool = pool[
                        ~pool.apply(
                            lambda row: HealthyWeightGainRecommender._contains_any(
                                HealthyWeightGainRecommender._row_name(row),
                                ("soup", "stew", "ham", "cured", "mollusk", "oyster", "crustacean", "ready-to-serve"),
                            ),
                            axis=1,
                        )
                    ]
                    if not breakfast_pool.empty:
                        pool = breakfast_pool

                if pool.empty:
                    break

                # --- Role-aware slot scoring ---
                # Protein slot: reward protein density (g protein / kcal)
                is_carb_slot = bool(allowed_cats & {"grain", "fruit"}) and not bool(allowed_cats & {"meat", "egg"})
                is_protein_slot = bool(allowed_cats & {"meat", "egg", "plant_protein"}) and "grain" not in allowed_cats and "healthy_fat" not in allowed_cats
                # Fat slot: reward fat density — healthy_fat is primary, dairy secondary
                is_fat_slot = "healthy_fat" in allowed_cats and "grain" not in allowed_cats and not (allowed_cats == {"vegetable"})
                # Grain slot: reward carb density + calorie fit
                is_grain_slot = allowed_cats == {"grain"}
                # Vegetable slot: lighter calorie constraint, prioritise variety
                is_light_slot = allowed_cats == {"vegetable"} or allowed_cats == {"fruit"}

                if is_carb_slot:
                    clean_pool = pool[pool.apply(HealthyWeightGainRecommender._is_clean_carb_row, axis=1)]
                    if meal == "breakfast":
                        breakfast_pool = clean_pool[
                            ~clean_pool.apply(
                                lambda row: HealthyWeightGainRecommender._carb_family(row) == "noodle"
                                or HealthyWeightGainRecommender._contains_any(
                                    HealthyWeightGainRecommender._row_name(row),
                                    ("pasta", "spaghetti", "macaroni", "noodle", "noodles"),
                                ),
                                axis=1,
                            )
                        ]
                        if breakfast_pool.empty:
                            continue
                        clean_pool = breakfast_pool
                    if selected_carb_families:
                        family_pool = clean_pool[
                            ~clean_pool.apply(
                                lambda row: HealthyWeightGainRecommender._carb_family(row) in selected_carb_families,
                                axis=1,
                            )
                        ]
                        if not family_pool.empty:
                            clean_pool = family_pool
                    if not clean_pool.empty:
                        pool = clean_pool
                elif is_protein_slot:
                    protein_pool = pool[pool.apply(HealthyWeightGainRecommender._is_lean_protein_row, axis=1)]
                    if not protein_pool.empty:
                        pool = protein_pool
                elif is_fat_slot:
                    fat_pool = pool[pool.apply(HealthyWeightGainRecommender._is_good_fat_row, axis=1)]
                    if not fat_pool.empty:
                        pool = fat_pool
                    else:
                        extra_pool = pool[
                            pool.apply(HealthyWeightGainRecommender._healthy_energy_extra_score, axis=1) > 0.0
                        ]
                        if not extra_pool.empty:
                            pool = extra_pool

                # Always compute calorie gap for use in scoring formulas
                cal_gap = (pool["calories_raw"].astype(float) - slot_target_kcal).abs() / max(slot_target_kcal, 1.0)
                daily_protein_target = float(target_nutrition.get("protein", 0.0))
                if is_protein_slot:
                    slot_protein_target = max(
                        daily_protein_target * meal_ratio * 0.75,
                        daily_protein_target / max(len(structure), 1) * 0.65,
                        1.0,
                    )
                else:
                    slot_protein_target = max(daily_protein_target * meal_ratio * slot_weight, 1.0)
                protein_overshoot_penalty = (
                    (pool["protein_raw"].astype(float) - slot_protein_target * 1.25).clip(lower=0.0)
                    / slot_protein_target
                ).clip(0.0, 2.0)

                pool = pool.copy()
                clean_carb = pool.apply(HealthyWeightGainRecommender._is_clean_carb_row, axis=1).astype(float)
                clean_protein = pool.apply(HealthyWeightGainRecommender._is_lean_protein_row, axis=1).astype(float)
                good_fat = pool.apply(HealthyWeightGainRecommender._is_good_fat_row, axis=1).astype(float)
                energy_extra = pool.apply(HealthyWeightGainRecommender._healthy_energy_extra_score, axis=1)
                quality = pool.apply(HealthyWeightGainRecommender._food_quality_score, axis=1)
                image_bonus = pool.apply(HealthyWeightGainRecommender._has_valid_image_url, axis=1).astype(float) * 0.06
                family_repeat_penalty = pool.apply(
                    lambda row: 0.18 * daily_family_counts.get(
                        HealthyWeightGainRecommender._food_family(row),
                        0,
                    ),
                    axis=1,
                )
                new_protein_family_bonus = pool.apply(
                    lambda row: (
                        0.16
                        if is_protein_slot
                        and daily_family_counts.get(HealthyWeightGainRecommender._food_family(row), 0) == 0
                        else 0.0
                    ),
                    axis=1,
                )
                if is_fat_slot:
                    # Reward g-fat per 100 kcal — higher = better for this slot
                    max_fat = pool["fat_raw"].astype(float).max() or 1.0
                    fat_norm = pool["fat_raw"].astype(float) / max_fat
                    pool["_slot_score"] = (
                        pool["score"] * 0.30
                        + fat_norm * 0.34
                        + good_fat * 0.22
                        + energy_extra.clip(-1.0, 2.5) * 0.12
                        + (1.0 - cal_gap.clip(0.0, 1.0)) * 0.10
                        + image_bonus
                        - family_repeat_penalty
                    )
                elif is_protein_slot:
                    max_prot = pool["protein_raw"].astype(float).max() or 1.0
                    prot_norm = pool["protein_raw"].astype(float) / max_prot
                    pool["_slot_score"] = (
                        pool["score"] * 0.30
                        + prot_norm * 0.35
                        + clean_protein * 0.20
                        + (1.0 - cal_gap.clip(0.0, 1.0)) * 0.15
                        + new_protein_family_bonus
                        + image_bonus
                        - family_repeat_penalty
                        - protein_overshoot_penalty * 0.18
                    )
                elif is_carb_slot:
                    max_carbs = pool["carbs_raw"].astype(float).max() or 1.0
                    carb_norm = pool["carbs_raw"].astype(float) / max_carbs
                    pool["_slot_score"] = (
                        pool["score"] * 0.25
                        + carb_norm * 0.35
                        + clean_carb * 0.25
                        + (1.0 - cal_gap.clip(0.0, 1.0)) * 0.15
                        + image_bonus
                        - family_repeat_penalty
                    )
                elif is_light_slot:
                    pool["_slot_score"] = (
                        pool["score"] * 0.45
                        + quality * 0.25
                        + (1.0 - cal_gap.clip(0.0, 1.0)) * 0.30
                        + image_bonus
                        - family_repeat_penalty
                    )
                else:
                    pool["_slot_score"] = (
                        pool["score"] * 0.45
                        + quality * 0.20
                        + (1.0 - cal_gap.clip(0.0, 1.0)) * 0.35
                        + image_bonus
                        - family_repeat_penalty
                    )

                # Hard cap: don't overshoot remaining meal budget by more than 25%
                remaining_slots_left = n_slots - slot_idx
                max_kcal = max(remaining_kcal * (1.15 if remaining_slots_left == 1 else 1.35), 80.0)
                slot_max_kcal = max(slot_target_kcal * (4.0 if is_carb_slot else 2.5), 220.0)
                max_kcal = min(max_kcal, slot_max_kcal)
                capped = pool[pool["calories_raw"].astype(float) <= max_kcal]
                if capped.empty:
                    capped = pool  # relax cap if no candidates fit

                best_row = capped.sort_values("_slot_score", ascending=False).iloc[0].copy()
                macro_base_calories = HealthyWeightGainRecommender._macro_kcal(best_row)
                base_calories = max(macro_base_calories or float(best_row["calories_raw"]), 1.0)
                max_serving_multiplier = max(
                    HealthyWeightGainRecommender._max_serving_grams(best_row) / 100.0,
                    0.15,
                )
                serving_multiplier = float(
                    np.clip(slot_target_kcal / base_calories, 0.15, min(3.5, max_serving_multiplier))
                )
                if is_protein_slot:
                    base_protein = max(float(best_row.get("protein_raw", 0.0) or 0.0), 0.0)
                    if base_protein > 0:
                        protein_cap_multiplier = (slot_protein_target * 1.05) / base_protein
                        serving_multiplier = min(serving_multiplier, max(0.45, protein_cap_multiplier))
                for nutrient_col in ("calories_raw", "protein_raw", "fat_raw", "carbs_raw"):
                    best_row[nutrient_col] = float(best_row[nutrient_col]) * serving_multiplier
                best_row = HealthyWeightGainRecommender._normalize_macro_calories(best_row)
                best_row["serving_multiplier"] = serving_multiplier
                base_serving_grams = float(best_row.get("base_serving_grams", best_row.get("quantity_g", 100.0)) or 100.0)
                best_row["serving_grams"] = round(serving_multiplier * base_serving_grams, 0)
                best_row = HealthyWeightGainRecommender._cap_row_serving(best_row)
                best_row["culinary_role"] = HealthyWeightGainRecommender._culinary_role(best_row)
                selected_rows.append(best_row)
                seen_food_keys.add(str(best_row["_food_key"]))
                food_family = HealthyWeightGainRecommender._food_family(best_row)
                if food_family:
                    selected_food_families.add(food_family)
                    daily_family_counts[food_family] = daily_family_counts.get(food_family, 0) + 1
                category_key = str(best_row.get("category", "")).strip().lower() or "other"
                daily_category_counts[category_key] = daily_category_counts.get(category_key, 0) + 1
                if slot_idx == 0 and HealthyWeightGainRecommender._is_savory_staple(best_row):
                    savory_staple_selected = True
                carb_family = HealthyWeightGainRecommender._carb_family(best_row)
                if is_carb_slot and carb_family:
                    selected_carb_families.add(carb_family)
                # Also track Vietnamese display name to block same-name duplicates
                seen_display_names.add(str(best_row["name"]).strip().lower())
                remaining_kcal -= float(best_row["calories_raw"])

            while len(selected_rows) < requested_slots:
                fallback_slot_idx = len(selected_rows)
                fallback_allowed = set(slot_roles[fallback_slot_idx]) if fallback_slot_idx < len(slot_roles) else set()
                fallback_role = MEAL_SLOT_CULINARY_ROLES.get(meal, [])[fallback_slot_idx] if fallback_slot_idx < len(MEAL_SLOT_CULINARY_ROLES.get(meal, [])) else ""
                fallback_pool = working_df[
                    ~working_df["_food_key"].isin(seen_food_keys)
                    & ~working_df["name"].astype(str).str.strip().str.lower().isin(seen_display_names)
                ].copy()
                if fallback_allowed:
                    constrained = fallback_pool[fallback_pool["category"].astype(str).str.lower().isin(fallback_allowed)]
                    if not constrained.empty:
                        fallback_pool = constrained
                if fallback_role in {"fat", "side"}:
                    side_pool = fallback_pool[
                        fallback_pool["category"].astype(str).str.lower().isin({"healthy_fat", "dairy", "fruit"})
                    ]
                    if not side_pool.empty:
                        fallback_pool = side_pool
                    extra_pool = fallback_pool[
                        fallback_pool.apply(HealthyWeightGainRecommender._healthy_energy_extra_score, axis=1) > 0.0
                    ]
                    if not extra_pool.empty:
                        fallback_pool = extra_pool
                if fallback_role == "vegetable":
                    vegetable_pool = fallback_pool[fallback_pool["category"].astype(str).str.lower() == "vegetable"]
                    if not vegetable_pool.empty:
                        fallback_pool = vegetable_pool
                if fallback_role == "fruit":
                    produce_pool = fallback_pool[
                        fallback_pool["category"].astype(str).str.lower().isin({"fruit", "vegetable"})
                        & (fallback_pool.get("clean_category", "").astype(str).str.lower() != "vegetable_herb")
                    ]
                    if not produce_pool.empty:
                        fallback_pool = produce_pool
                if fallback_pool.empty:
                    break

                best_row = fallback_pool.sort_values("score", ascending=False).iloc[0].copy()
                fallback_target_kcal = max(meal_target / max(n_slots, 1) * 0.65, 80.0)
                base_calories = max(HealthyWeightGainRecommender._macro_kcal(best_row) or float(best_row["calories_raw"]), 1.0)
                max_serving_multiplier = max(
                    HealthyWeightGainRecommender._max_serving_grams(best_row) / 100.0,
                    0.15,
                )
                serving_multiplier = float(np.clip(fallback_target_kcal / base_calories, 0.15, min(2.0, max_serving_multiplier)))
                for nutrient_col in ("calories_raw", "protein_raw", "fat_raw", "carbs_raw"):
                    best_row[nutrient_col] = float(best_row[nutrient_col]) * serving_multiplier
                best_row = HealthyWeightGainRecommender._normalize_macro_calories(best_row)
                best_row["serving_multiplier"] = serving_multiplier
                base_serving_grams = float(best_row.get("base_serving_grams", best_row.get("quantity_g", 100.0)) or 100.0)
                best_row["serving_grams"] = round(serving_multiplier * base_serving_grams, 0)
                best_row = HealthyWeightGainRecommender._cap_row_serving(best_row)
                best_row["culinary_role"] = HealthyWeightGainRecommender._culinary_role(best_row)
                selected_rows.append(best_row)
                seen_food_keys.add(str(best_row["_food_key"]))
                seen_display_names.add(str(best_row["name"]).strip().lower())
                food_family = HealthyWeightGainRecommender._food_family(best_row)
                if food_family:
                    selected_food_families.add(food_family)
                    daily_family_counts[food_family] = daily_family_counts.get(food_family, 0) + 1
                category_key = str(best_row.get("category", "")).strip().lower() or "other"
                daily_category_counts[category_key] = daily_category_counts.get(category_key, 0) + 1

            if selected_rows:
                drop_cols = [c for c in ["_food_key", "_slot_score"] if c in selected_rows[0].index]
                meal_df = pd.DataFrame(selected_rows).drop(columns=drop_cols, errors="ignore").reset_index(drop=True)
            else:
                meal_df = working_df.iloc[0:0].drop(columns=["_food_key"], errors="ignore")
            plan[meal] = meal_df

        capped_plan = HealthyWeightGainRecommender._apply_serving_caps_to_plan(plan)
        normalized_plan = HealthyWeightGainRecommender._normalize_plan_macro_calories(capped_plan)
        fat_guarded_plan = HealthyWeightGainRecommender._replace_low_fat_extras(
            normalized_plan,
            working_df,
            target_nutrition,
        )
        balanced_plan = HealthyWeightGainRecommender._rebalance_plan_macros_for_weight_gain(
            fat_guarded_plan,
            target_nutrition,
        )
        return HealthyWeightGainRecommender._scale_plan_energy_if_needed(
            balanced_plan,
            float(target_nutrition.get("calories", target_calories)),
        )

    @staticmethod
    def _calibrate_meal_macros(
        plan: dict[str, pd.DataFrame],
        target_nutrition: dict[str, float],
        meal_ratios: dict[str, float],
    ) -> dict[str, pd.DataFrame]:
        """Normalize macro grams to the selected calorie portions.

        The source CSV mixes calories and macro grams on slightly different
        serving bases. After portioning calories per slot, this calibration keeps
        the selected foods and calories unchanged, then aligns displayed macro
        grams with the daily macro targets per meal.
        """
        ratio_sum = sum(meal_ratios.get(meal, 0.0) for meal in plan) or 1.0
        calibrated: dict[str, pd.DataFrame] = {}
        for meal, meal_df in plan.items():
            if meal_df.empty:
                calibrated[meal] = meal_df
                continue

            meal_ratio = meal_ratios.get(meal, 1.0 / max(len(plan), 1)) / ratio_sum
            next_df = meal_df.copy()
            for macro in ("protein", "fat", "carbs"):
                col = f"{macro}_raw"
                current_total = float(next_df[col].sum())
                target_total = float(target_nutrition[macro]) * meal_ratio
                if current_total > 0:
                    next_df[col] = next_df[col].astype(float) * (target_total / current_total)
            calibrated[meal] = next_df
        return calibrated

    @staticmethod
    def _build_fallback_meal_plan(
        target_nutrition: dict[str, float],
    ) -> dict[str, pd.DataFrame]:
        """Return an empty-DataFrame meal plan when the engine crashes entirely.
        This prevents the fallback handler in the service layer from raising
        AttributeError and crashing the HTTP response."""
        empty = pd.DataFrame(
            columns=[
                "food_id", "name", "display_name_en", "name_en",
                "category", "calories_raw", "protein_raw", "fat_raw",
                "carbs_raw", "score",
            ]
        )
        return {meal: empty.copy() for meal in DEFAULT_MEAL_STRUCTURE}

    @staticmethod
    def evaluate_meal_distribution(
        meal_plan: dict[str, pd.DataFrame],
        target_nutrition: dict[str, float],
        meal_ratios: dict[str, float] | None = None,
    ) -> dict[str, dict[str, float]]:
        ratios = meal_ratios or DEFAULT_MEAL_CALORIE_RATIOS
        ratio_sum = sum(ratios.values()) or 1.0

        payload: dict[str, dict[str, float]] = {}
        for meal, df in meal_plan.items():
            normalized_ratio = float(ratios.get(meal, 0.0)) / ratio_sum
            target_cal = float(target_nutrition["calories"]) * normalized_ratio
            target_protein = float(target_nutrition["protein"]) * normalized_ratio
            target_fat = float(target_nutrition["fat"]) * normalized_ratio
            target_carbs = float(target_nutrition["carbs"]) * normalized_ratio

            actual_cal = float(df["calories_raw"].sum()) if not df.empty else 0.0
            actual_protein = float(df["protein_raw"].sum()) if not df.empty else 0.0
            actual_fat = float(df["fat_raw"].sum()) if not df.empty else 0.0
            actual_carbs = float(df["carbs_raw"].sum()) if not df.empty else 0.0

            payload[meal] = {
                "ratio_pct": normalized_ratio * 100.0,
                "target_calories": target_cal,
                "actual_calories": actual_cal,
                "target_protein": target_protein,
                "actual_protein": actual_protein,
                "target_fat": target_fat,
                "actual_fat": actual_fat,
                "target_carbs": target_carbs,
                "actual_carbs": actual_carbs,
                # Aliases for frontend compatibility
                "calories": actual_cal,
                "protein": actual_protein,
                "fat": actual_fat,
                "carbs": actual_carbs,
            }

        return payload

    @staticmethod
    def evaluate_calorie_alignment(
        meal_plan: dict[str, pd.DataFrame],
        target_calories: float,
    ) -> dict[str, float]:
        recommended_calories = 0.0
        for meal_df in meal_plan.values():
            if "calories_raw" in meal_df.columns and not meal_df.empty:
                recommended_calories += float(meal_df["calories_raw"].sum())

        absolute_error = abs(recommended_calories - target_calories)
        relative_error_pct = (absolute_error / target_calories * 100.0) if target_calories > 0 else 0.0
        return {
            "target_calories": float(target_calories),
            "recommended_calories": recommended_calories,
            "signed_error": recommended_calories - float(target_calories),
            "absolute_error": absolute_error,
            "relative_error_pct": relative_error_pct,
            "within_10pct": relative_error_pct <= 10.0,
        }

    @staticmethod
    def evaluate_macro_alignment(
        meal_plan: dict[str, pd.DataFrame],
        target_nutrition: dict[str, float],
    ) -> dict[str, float]:
        totals = {
            "protein": 0.0,
            "fat": 0.0,
            "carbs": 0.0,
        }
        for meal_df in meal_plan.values():
            if meal_df.empty:
                continue
            if "protein_raw" in meal_df.columns:
                totals["protein"] += float(meal_df["protein_raw"].sum())
            if "fat_raw" in meal_df.columns:
                totals["fat"] += float(meal_df["fat_raw"].sum())
            if "carbs_raw" in meal_df.columns:
                totals["carbs"] += float(meal_df["carbs_raw"].sum())

        metrics: dict[str, float] = {}
        relative_errors: list[float] = []
        for macro in ("protein", "fat", "carbs"):
            target_value = max(float(target_nutrition.get(macro, 0.0)), 1e-6)
            recommended_value = totals[macro]
            absolute_error = abs(recommended_value - target_value)
            relative_error_pct = absolute_error / target_value * 100.0
            metrics[f"target_{macro}"] = target_value
            metrics[f"recommended_{macro}"] = recommended_value
            metrics[f"{macro}_absolute_error"] = absolute_error
            metrics[f"{macro}_relative_error_pct"] = relative_error_pct
            relative_errors.append(relative_error_pct)

        metrics["macro_mae_relative_pct"] = float(np.mean(relative_errors)) if relative_errors else 0.0
        metrics["macros_within_20pct_ratio"] = float(
            np.mean([err <= 20.0 for err in relative_errors]) if relative_errors else 0.0
        )
        return metrics

    @staticmethod
    def evaluate_preference_precision(
        ranked_df: pd.DataFrame,
        preferred_categories: Sequence[str] | None,
        k: int = 10,
    ) -> float | None:
        if not preferred_categories:
            return None

        preferred = {category.strip().lower() for category in preferred_categories if category and category.strip()}
        if not preferred:
            return None

        if ranked_df.empty or "category" not in ranked_df.columns:
            return None

        top_df = ranked_df.head(max(k, 1))
        categories = top_df["category"].astype(str).str.lower()
        total = len(categories)
        if total == 0:
            return None
        matched = int(categories.isin(preferred).sum())
        return matched / total


def build_profile_from_args(args: argparse.Namespace) -> UserProfile:
    return UserProfile(
        weight_kg=args.weight,
        height_cm=args.height,
        activity_level=args.activity,
        age=args.age,
        sex=args.sex,
        goal=args.goal,
        surplus_kcal=args.surplus_kcal,
    )


def collect_profile_interactively() -> tuple[UserProfile, list[str], list[str]]:
    def ask_text(prompt: str, default: str | None = None) -> str:
        suffix = f" [{default}]" if default is not None else ""
        value = input(f"{prompt}{suffix}: ").strip()
        return value if value else (default or "")

    def ask_float(prompt: str, default: float) -> float:
        value = ask_text(prompt, str(default))
        return float(value)

    def ask_int(prompt: str, default: int | None = None) -> int | None:
        value = ask_text(prompt, "" if default is None else str(default))
        return int(value) if value else default

    def ask_categories(prompt: str) -> list[str]:
        value = ask_text(prompt, "")
        if not value:
            return []
        return [item.strip().lower() for item in value.split(",") if item.strip()]

    weight = ask_float("Nhap can nang (kg)", 50.0)
    height = ask_float("Nhap chieu cao (cm)", 165.0)
    activity = ask_text("Nhap muc do hoat dong (sedentary/light/moderate/active/very_active)", "moderate")
    age = ask_int("Nhap tuoi", None)
    sex = ask_text("Nhap gioi tinh (male/female)", "") or None
    surplus_input = ask_text("Nhap calorie surplus neu muon override, bo trong neu khong", "")
    surplus_kcal = float(surplus_input) if surplus_input else None
    preferred_categories = ask_categories("Nhap category uu tien, cach nhau bang dau phay")
    excluded_categories = ask_categories("Nhap category can tranh, cach nhau bang dau phay")

    profile = UserProfile(
        weight_kg=weight,
        height_cm=height,
        activity_level=activity,
        age=age,
        sex=sex,
        goal="gain",
        surplus_kcal=surplus_kcal,
    )
    return profile, preferred_categories, excluded_categories


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Healthy weight-gain food recommender")
    parser.add_argument("--raw-path", default="data/food_dataset_fixed.csv", help="Path to food_dataset_fixed.csv")
    parser.add_argument("--scaled-path", default="data/food_dataset_fixed.csv", help="Path to food_dataset_fixed.csv")
    parser.add_argument(
        "--preference-model-path",
        default="preference_model.joblib",
        help="Path to trained preference model artifact (optional)",
    )
    parser.add_argument("--user-history-path", default="user_history.csv", help="Path to saved user history CSV")
    parser.add_argument("--interactive", action="store_true", help="Prompt for user input interactively")
    parser.add_argument("--weight", type=float, default=50.0, help="Body weight in kg")
    parser.add_argument("--height", type=float, default=165.0, help="Height in cm")
    parser.add_argument("--activity", default="moderate", help="Activity level or numeric multiplier")
    parser.add_argument("--age", type=int, default=None, help="Age in years")
    parser.add_argument("--sex", default=None, help="Sex: male/female")
    parser.add_argument("--goal", default="gain", choices=["gain"], help="Current goal")
    parser.add_argument("--surplus-kcal", type=float, default=None, help="Optional calorie surplus override")
    parser.add_argument("--top-n", type=int, default=10, help="Number of results to return")
    parser.add_argument("--save-user-data", action="store_true", help="Append user input to history CSV")
    parser.add_argument(
        "--preferred-categories",
        nargs="*",
        default=None,
        help="Optional categories to prioritize",
    )
    parser.add_argument(
        "--excluded-categories",
        nargs="*",
        default=None,
        help="Optional categories to exclude",
    )
    return parser.parse_args()


def format_recommendations(df: pd.DataFrame) -> str:
    columns = [
        "food_id",
        "name",
        "category",
        "calories_raw",
        "protein_raw",
        "fat_raw",
        "carbs_raw",
        "score",
    ]
    available = [column for column in columns if column in df.columns]
    display_df = df[available].copy()
    display_df.columns = [
        "food_id",
        "name",
        "category",
        "calories",
        "protein",
        "fat",
        "carbs",
        "score",
    ][: len(available)]
    return display_df.to_string(index=False)


def format_meal_plan(meal_plan: dict[str, pd.DataFrame]) -> str:
    lines: list[str] = []
    labels = {
        "breakfast": "Sang",
        "lunch": "Trua",
        "dinner": "Toi",
    }
    for meal_key in ["breakfast", "lunch", "dinner"]:
        meal_df = meal_plan.get(meal_key)
        if meal_df is None:
            continue
        label = labels.get(meal_key, meal_key)
        lines.append(f"{label}:")
        if meal_df.empty:
            lines.append("  - Khong du du lieu de goi y")
            continue
        for _, row in meal_df.iterrows():
            portion = ""
            if "serving_grams" in row and not pd.isna(row["serving_grams"]):
                portion = f" ~{float(row['serving_grams']):.0f}g"
            lines.append(
                f"  - {row['name']}{portion} ({row['category']}): {row['calories_raw']:.1f} kcal | "
                f"P {row['protein_raw']:.1f}g - F {row['fat_raw']:.1f}g - C {row['carbs_raw']:.1f}g"
            )
    return "\n".join(lines)


def format_evaluation(
    calorie_metrics: dict[str, float],
    macro_metrics: dict[str, float],
    preference_precision: float | None,
) -> str:
    lines = [
        "Danh gia he thong:",
        (
            f"  - Target calories: {calorie_metrics['target_calories']:.1f} kcal | "
            f"Goi y calories: {calorie_metrics['recommended_calories']:.1f} kcal"
        ),
        (
            f"  - Sai so tuyet doi: {calorie_metrics['absolute_error']:.1f} kcal "
            f"({calorie_metrics['relative_error_pct']:.2f}%)"
        ),
        (
            f"  - Sai so macro trung binh: {macro_metrics['macro_mae_relative_pct']:.2f}% | "
            f"Ty le macro dat nguong 20%: {macro_metrics['macros_within_20pct_ratio'] * 100:.2f}%"
        ),
    ]
    if preference_precision is not None:
        lines.append(f"  - Precision theo preferred_categories: {preference_precision * 100:.2f}%")
    else:
        lines.append("  - Precision theo preferred_categories: chua tinh (khong co preferred_categories)")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    recommender = HealthyWeightGainRecommender(
        args.raw_path,
        args.scaled_path,
        preference_model_path=args.preference_model_path,
    ).load_data()
    if args.interactive:
        profile, preferred_categories, excluded_categories = collect_profile_interactively()
    else:
        profile = build_profile_from_args(args)
        preferred_categories = args.preferred_categories or []
        excluded_categories = args.excluded_categories or []

    history_preferences = recommender.train_category_preferences(args.user_history_path)
    current_preferences: dict[str, float] = dict(history_preferences)
    for category in preferred_categories:
        normalized = category.strip().lower()
        if normalized:
            current_preferences[normalized] = current_preferences.get(normalized, 0.0) + 1.0
    for category in excluded_categories:
        normalized = category.strip().lower()
        if normalized:
            current_preferences[normalized] = current_preferences.get(normalized, 0.0) - 1.0

    if args.save_user_data or args.interactive:
        recommender.save_user_profile(
            profile=profile,
            preferred_categories=preferred_categories,
            excluded_categories=excluded_categories,
            history_path=args.user_history_path,
        )

    meal_slots = sum(DEFAULT_MEAL_STRUCTURE.values())
    candidate_top_n = max(args.top_n * 12, meal_slots * 30, 1600)
    recommendations = recommender.recommend(
        profile=profile,
        top_n=candidate_top_n,
        preferred_categories=preferred_categories,
        excluded_categories=excluded_categories,
        category_preferences=current_preferences,
    )

    target_info = recommender._estimate_target_nutrition(profile)
    meal_plan = recommender.build_daily_meal_plan(
        recommendations, 
        meal_structure=DEFAULT_MEAL_STRUCTURE,
        target_calories=target_info["calories"],
        target_nutrition=target_info,
    )
    calorie_metrics = recommender.evaluate_calorie_alignment(meal_plan, target_info["calories"])
    macro_metrics = recommender.evaluate_macro_alignment(meal_plan, target_info)
    preference_precision = recommender.evaluate_preference_precision(
        recommendations,
        preferred_categories,
        k=args.top_n,
    )
    top_recommendations = recommendations.head(args.top_n)

    print("Target nutrition")
    print(
        f"  BMI: {target_info['bmi']:.2f} | BMR: {target_info['bmr']:.1f} kcal | "
        f"TDEE: {target_info['tdee']:.1f} kcal | "
        f"Target calories: {target_info['calories']:.1f} kcal"
    )
    if target_info.get("bmi_status"):
        print(f"  BMI status: {_console_safe(target_info['bmi_status'])}")
    if target_info.get("medical_warning"):
        print(f"  Medical note: {_console_safe(target_info['medical_warning'])}")
    print(
        f"  Protein: {target_info['protein']:.1f} g | Fat: {target_info['fat']:.1f} g | Carbs: {target_info['carbs']:.1f} g"
    )
    print()
    print("Top recommendations")
    print(_console_safe(format_recommendations(top_recommendations)))
    print()
    print("Thuc don 1 ngay (3 bua chinh: Sang - Trua - Toi)")
    print(_console_safe(format_meal_plan(meal_plan)))
    print()
    print(format_evaluation(calorie_metrics, macro_metrics, preference_precision))
    if args.save_user_data or args.interactive:
        print()
        print(f"Saved user profile to {args.user_history_path}")
        print("Next runs will reuse saved category preferences when history exists.")


if __name__ == "__main__":
    main()
