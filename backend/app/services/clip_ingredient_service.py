from __future__ import annotations

import io
import logging
import os
import re
import statistics
import threading
import unicodedata
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen


logger = logging.getLogger("uvicorn.error")

_model_lock = threading.Lock()

# FIX: Final safety gate now respects prompt majority decisions
# When ingredients are accepted via prompt majority (e.g., fish_prompt_majority),
# the acceptance reason and majority info are preserved and passed to the final
# safety gate. The gate uses majority-specific validation rules instead of
# hardcoded thresholds, allowing properly validated majority decisions to pass.

def _is_ingredient_recognition_enabled() -> bool:
    """Check if ingredient image recognition is enabled via environment variable."""
    enabled = os.getenv("ENABLE_INGREDIENT_IMAGE_RECOGNITION", "true").lower()
    return enabled in ("true", "1", "yes", "on")

FAIL_MESSAGE = "Chưa nhận diện chắc nguyên liệu trong ảnh này"
LOW_CONFIDENCE_MESSAGE = "Chưa nhận diện rõ nguyên liệu trong ảnh này. Bạn có thể nhập thủ công."
HIGH_CONFIDENCE_THRESHOLD = 0.25
MEDIUM_CONFIDENCE_THRESHOLD = 0.18
LOW_CONFIDENCE_THRESHOLD = 0.12
MAX_IMAGE_DOWNLOAD_BYTES = 8 * 1024 * 1024

# PHẦN 1: Meat/Seafood force thresholds
MEAT_FORCE_NAMES = {"Thịt lợn", "Thịt bò", "Thịt gà", "Xúc xích"}
SEAFOOD_FORCE_NAMES = {"Cá", "Tôm", "Cua", "Sò", "Hàu", "Hải sản"}
MEAT_FORCE_MIN_SCORE = 0.36
SEAFOOD_FORCE_MIN_SCORE = 0.34
FORCE_MIN_MARGIN = 0.035

# Safety thresholds for special accept branches
MEAT_NAMES = {"Thịt lợn", "Thịt bò", "Thịt gà"}
SAUSAGE_NAMES = {"Xúc xích"}
SEAFOOD_NAMES = {"Cá", "Tôm", "Cua", "Sò", "Hàu", "Hải sản"}


def get_prompt_majority(top_prompts: list[dict[str, Any]], ingredient_name: str, top_n: int = 10) -> dict[str, Any]:
    """
    Analyze prompt majority for a specific ingredient.
    Returns counts and ratio of prompts matching the ingredient.
    """
    prompts = top_prompts[:top_n] if top_prompts else []
    count = sum(1 for p in prompts if p.get("ingredient") == ingredient_name)
    top3_count = sum(1 for p in prompts[:3] if p.get("ingredient") == ingredient_name)
    top5_count = sum(1 for p in prompts[:5] if p.get("ingredient") == ingredient_name)
    
    return {
        "count": count,
        "top3Count": top3_count,
        "top5Count": top5_count,
        "ratio": count / max(len(prompts), 1),
    }


def has_strong_veg_fruit_tuber_blocker(
    grouped_candidates: list[dict[str, Any]],
    top_prompts: list[dict[str, Any]],
    best_score: float
) -> bool:
    """
    Check if there's a strong vegetable/fruit/tuber blocker that should prevent accepting meat/seafood.
    This prevents misidentifying vegetables as meat/seafood.
    Only block when blocker is really strong - in top 3 and score is very close to best.
    """
    VEG_FRUIT_TUBER_NAMES = {
        "Khoai tây", "Khoai lang", "Cà rốt", "Cà chua", "Cam",
        "Táo", "Bí đỏ", "Bí", "Củ cải", "Rau cải", "Rau bina",
        "Đậu nành", "Đậu phụ"
    }
    
    # Find best blocker candidate
    best_blocker = None
    best_blocker_score = 0.0
    best_blocker_rank = 999
    
    for idx, c in enumerate(grouped_candidates):
        name = c.get("name")
        if name in VEG_FRUIT_TUBER_NAMES:
            score = float(c.get("score", 0) or 0)
            if score > best_blocker_score:
                best_blocker = c
                best_blocker_score = score
                best_blocker_rank = idx
    
    # Count veg/fruit/tuber prompts in top 10
    blocker_prompt_count = sum(
        1 for p in top_prompts[:10]
        if p.get("ingredient") in VEG_FRUIT_TUBER_NAMES
    )
    
    # PHẦN 6: Block only if best blocker is in top 3 AND score is very close to best_score
    # Changed from 0.04 to 0.03 to be more restrictive
    if best_blocker and best_blocker_rank <= 2 and best_blocker_score >= best_score - 0.03:
        return True
    
    # PHẦN 6: Block if there are many veg/fruit/tuber prompts in top 10 (4+, not just candidate presence)
    if blocker_prompt_count >= 4:
        return True
    
    return False


def can_accept_candidate(
    candidate: dict[str, Any] | None,
    grouped_candidates: list[dict[str, Any]],
    reason: str,
    allow_majority_override: bool = False,
    majority_info: dict[str, Any] | None = None
) -> tuple[bool, str]:
    """
    Check if a candidate can be safely accepted based on strict thresholds for meat/seafood/sausage.
    Returns (can_accept, reject_reason).
    
    If allow_majority_override is True and reason is a majority reason, use relaxed thresholds
    based on prompt majority consensus instead of hardcoded thresholds.
    """
    if not candidate:
        return False, "missing_candidate"
    
    name = str(candidate.get("name", ""))
    score = float(candidate.get("score", 0) or 0)
    
    # Find rank (1-indexed)
    try:
        rank = grouped_candidates.index(candidate) + 1
    except ValueError:
        return False, "candidate_not_in_list"
    
    # Majority reasons that can bypass strict checks with proper validation
    majority_reasons = {
        "pork_prompt_majority",
        "shrimp_prompt_majority",
        "crab_prompt_majority",
        "fish_prompt_majority",
        "sausage_prompt_majority",
        "beef_prompt_majority",
        "chicken_prompt_majority",
    }
    
    # PHẦN 5: Majority override with specific validation per ingredient
    if allow_majority_override and reason in majority_reasons and majority_info:
        # Validate majority info is strong enough
        count = majority_info.get("count", 0)
        top3_count = majority_info.get("top3Count", 0)
        ratio = majority_info.get("ratio", 0)
        
        # Beef majority override
        if reason == "beef_prompt_majority" and name == "Thịt bò":
            if rank == 1 and score >= 0.31 and count >= 6 and top3_count >= 3 and ratio >= 0.6:
                return True, "beef_majority_override_ok"
            return False, f"beef_majority_not_strong_enough (score={score:.4f}, count={count}, top3={top3_count}, ratio={ratio:.2f})"
        
        # Chicken majority override
        if reason == "chicken_prompt_majority" and name == "Thịt gà":
            if rank == 1 and score >= 0.32 and count >= 6 and top3_count >= 3 and ratio >= 0.6:
                return True, "chicken_majority_override_ok"
            return False, f"chicken_majority_not_strong_enough (score={score:.4f}, count={count}, top3={top3_count}, ratio={ratio:.2f})"
        
        # Fish majority override
        if reason == "fish_prompt_majority" and name == "Cá":
            if rank == 1 and score >= 0.28 and count >= 6 and top3_count >= 3 and ratio >= 0.6:
                return True, "fish_majority_override_ok"
            return False, f"fish_majority_not_strong_enough (score={score:.4f}, count={count}, top3={top3_count}, ratio={ratio:.2f})"
        
        # Shrimp majority override
        if reason == "shrimp_prompt_majority" and name == "Tôm":
            if rank == 1 and score >= 0.27 and count >= 6 and top3_count >= 3 and ratio >= 0.6:
                return True, "shrimp_majority_override_ok"
            return False, f"shrimp_majority_not_strong_enough (score={score:.4f}, count={count}, top3={top3_count}, ratio={ratio:.2f})"
        
        # Crab majority override
        if reason == "crab_prompt_majority" and name == "Cua":
            if rank == 1 and score >= 0.30 and count >= 6 and top3_count >= 2 and ratio >= 0.6:
                return True, "crab_majority_override_ok"
            return False, f"crab_majority_not_strong_enough (score={score:.4f}, count={count}, top3={top3_count}, ratio={ratio:.2f})"
        
        # Pork majority override
        if reason == "pork_prompt_majority" and name == "Thịt lợn":
            if rank == 1 and score >= 0.30 and count >= 6 and top3_count >= 3 and ratio >= 0.6:
                return True, "pork_majority_override_ok"
            return False, f"pork_majority_not_strong_enough (score={score:.4f}, count={count}, top3={top3_count}, ratio={ratio:.2f})"
        
        # Sausage majority override
        if reason == "sausage_prompt_majority" and name == "Xúc xích":
            if rank == 1 and score >= 0.30 and count >= 6 and top3_count >= 3 and ratio >= 0.6:
                return True, "sausage_majority_override_ok"
            return False, f"sausage_majority_not_strong_enough (score={score:.4f}, count={count}, top3={top3_count}, ratio={ratio:.2f})"
    
    # Get top and second scores for margin calculation
    top_score = float(grouped_candidates[0].get("score", 0) or 0) if grouped_candidates else 0
    second_score = float(grouped_candidates[1].get("score", 0) or 0) if len(grouped_candidates) > 1 else 0
    
    # Calculate margin
    if rank == 1:
        margin_over_second = score - second_score
    else:
        margin_over_second = score - top_score
    
    # Standard strict checks when not using majority override
    # Meat checks
    if name in MEAT_NAMES:
        if score < 0.36:
            return False, f"meat_score_below_0_36 (score={score:.4f})"
        if rank != 1:
            return False, f"meat_not_top1 (rank={rank})"
        if len(grouped_candidates) > 1 and score - second_score < 0.035:
            return False, f"meat_margin_too_small (margin={score - second_score:.4f})"
    
    # Sausage checks
    if name in SAUSAGE_NAMES:
        if score < 0.34:
            return False, f"sausage_score_below_0_34 (score={score:.4f})"
        if rank > 2:
            return False, f"sausage_rank_too_low (rank={rank})"
        if rank != 1 and score < top_score - 0.02:
            return False, f"sausage_too_far_from_top (delta={top_score - score:.4f})"
    
    # Seafood checks
    if name in SEAFOOD_NAMES:
        if score < 0.34:
            return False, f"seafood_score_below_0_34 (score={score:.4f})"
        if rank != 1:
            return False, f"seafood_not_top1 (rank={rank})"
        if len(grouped_candidates) > 1 and score - second_score < 0.035:
            return False, f"seafood_margin_too_small (margin={score - second_score:.4f})"
    
    return True, "ok"


VALID_INGREDIENTS = [
    "Cơm",
    "Khoai lang",
    "Khoai tây",
    "Trứng",
    "Thịt lợn",
    "Thịt bò",
    "Thịt gà",
    "Xúc xích",
    "Cua",
    "Cá",
    "Hàu",
    "Sò",
    "Tôm",
    "Hải sản",
    "Đậu hũ",
    "Đậu nành",
    "Sữa",
    "Yến mạch",
    "Rau cải",
    "Cà rốt",
    "Bí đỏ",
    "Chuối",
    "Táo",
    "Cam",
    "Cà chua",
    "Nấm",
]

INGREDIENT_PROMPT_GROUPS = {
    "Thịt bò": [
        "raw beef",
        "raw beef steak",
        "beef meat",
        "beef steak",
        "marbled beef",
        "red meat beef",
        "thit bo song",
        "thịt bò sống",
        "miếng thịt bò",
        "thịt bò",
    ],
    "Thịt lợn": [
        "pork",
        "raw pork",
        "fresh pork",
        "raw pork meat",
        "fresh pork meat",
        "pork slices",
        "raw pork slices",
        "pork loin",
        "pork tenderloin",
        "pork chop",
        "boneless pork",
        "lean pork",
        "pork meat",
        "raw pork loin",
        "a photo of raw pork",
        "a photo of raw pork slices",
        "a photo of fresh pork meat",
        "thịt lợn",
        "thit lon",
        "thịt lợn sống",
        "thit lon song",
        "miếng thịt lợn",
        "mieng thit lon",
        "thịt heo",
        "thit heo",
        "thịt heo sống",
        "thit heo song",
        "miếng thịt heo",
        "mieng thit heo",
    ],
    "Thịt gà": [
        "raw chicken",
        "chicken breast",
        "chicken meat",
        "raw poultry",
        "whole chicken",
        "chicken",
        "hen",
        "rooster",
        "poultry",
        "chicken drumstick",
        "chicken thigh",
        "chicken wing",
        "fresh chicken",
        "a photo of a raw whole chicken",
        "a photo of raw chicken on a cutting board",
        "a photo of a whole raw chicken",
        "a photo of uncooked chicken meat",
        "a photo of fresh raw chicken",
        "a photo of chicken poultry meat",
        "raw whole chicken on white background",
        "uncooked whole chicken",
        "whole chicken on cutting board",
        "raw whole chicken",
        "whole uncooked chicken",
        "gà nguyên con sống",
        "thịt gà sống nguyên con",
        "thit ga song",
        "ức gà",
        "thịt gà",
        "gà nguyên con",
        "ga nguyen con",
        "con gà",
        "con ga",
        "gà",
        "ga",
    ],
    "Xúc xích": [
        "sausage",
        "sausages",
        "hot dog",
        "hotdog",
        "frankfurter",
        "wiener sausage",
        "grilled sausage",
        "cooked sausage",
        "sausage skewers",
        "sausages on skewers",
        "processed sausage",
        "red sausage",
        "a photo of sausages",
        "a photo of sausage skewers",
        "a close-up photo of sausages",
        "a photo of grilled sausages",
        "a photo of hot dogs",
        "sausage on a stick",
        "skewered sausages",
        "xúc xích",
        "xuc xich",
        "xúc xích xiên",
        "xuc xich xien",
        "xúc xích nướng",
        "xuc xich nuong",
        "xúc xích đỏ",
        "xuc xich do",
    ],
    "Cua": [
        "crab",
        "live crab",
        "fresh crab",
        "raw crab",
        "con cua",
        "cua biển",
        "thịt cua",
        "cua tươi",
    ],
    "Hàu": [
        "oyster",
        "oysters",
        "fresh oysters",
        "raw oysters",
        "oyster shell",
        "oyster on half shell",
        "oyster meat",
        "shucked oyster",
        "pacific oyster",
        "rock oyster",
        "hàu sống",
        "hàu tươi",
        "hàu biển",
        "con hàu",
        "hàu",
        "hau song",
        "hau tuoi",
    ],
    "Sò": [
        "clam",
        "clams",
        "fresh clams",
        "shellfish clam",
        "manila clam",
        "littleneck clam",
        "sò",
        "nghêu",
        "so tuoi",
        "ngheu bien",
    ],
    "Tôm": [
        "shrimp",
        "prawns",
        "fresh shrimp",
        "raw shrimp",
        "tôm sú",
        "tôm",
    ],
    "Hải sản": [
        "seafood",
        "shellfish",
        "mixed seafood",
        "seafood platter",
        "hải sản",
    ],
    "Trứng": [
        "egg",
        "chicken egg",
        "eggs",
        "raw egg",
        "quả trứng",
        "trứng gà",
        "trứng",
    ],
    "Cà chua": [
        "tomato",
        "tomatoes",
        "fresh tomato",
        "fresh tomatoes",
        "red tomato",
        "cherry tomatoes",
        "sliced tomato",
        "tomato with green stem",
        "cà chua",
        "ca chua",
        "quả cà chua",
        "qua ca chua",
        "cà chua đỏ",
        "cà chua bi",
    ],
    "Nấm": [
        "mushroom",
        "mushrooms",
        "fresh mushrooms",
        "nấm",
    ],
    "Đậu hũ": [
        "tofu",
        "tofu blocks",
        "bean curd",
        "đậu hũ",
        "đậu phụ",
    ],
    "Rau cải": [
        "bok choy",
        "pak choi",
        "mustard greens",
        "leafy greens",
        "rau cải",
        "cải xanh",
        "cải thìa",
    ],
    "Cơm": [
        "rice",
        "cooked white rice",
        "a bowl of rice",
        "steamed rice",
        "white rice",
        "cơm trắng",
        "cơm",
    ],
    "Khoai lang": [
        "sweet potato",
        "sweet potatoes",
        "raw sweet potato",
        "raw sweet potatoes",
        "purple sweet potato",
        "red skin sweet potato",
        "orange sweet potato",
        "yellow flesh sweet potato",
        "orange flesh sweet potato",
        "roasted sweet potato",
        "cut sweet potato",
        "sliced sweet potato",
        "sweet potato tubers",
        "long sweet potato tubers",
        "Japanese sweet potato",
        "củ khoai lang",
        "khoai lang",
        "khoai lang tím",
        "khoai lang đỏ",
        "khoai lang cam",
        "khoai lang ruột vàng",
        "khoai lang ruột cam",
        "khoai lang nướng",
        "khoai lang nguyên củ",
        "khoai lang cắt đôi",
    ],
    "Khoai tây": [
        "potato",
        "potatoes",
        "raw potato",
        "raw potatoes",
        "fresh potato",
        "fresh potatoes",
        "yellow potato",
        "yellow potatoes",
        "white potato",
        "white potatoes",
        "brown potato",
        "brown potatoes",
        "small round potatoes",
        "round potatoes",
        "oval potatoes",
        "pile of potatoes",
        "unpeeled potatoes",
        "potato tubers",
        "củ khoai tây",
        "khoai tây",
        "khoai tây sống",
        "khoai tây vàng",
        "khoai tây trắng",
        "khoai tây nguyên củ",
        "nhiều củ khoai tây",
        "củ khoai tây tròn",
        "củ khoai tây vàng",
    ],
    "Cà rốt": [
        "carrot",
        "carrots",
        "fresh carrot",
        "fresh carrots",
        "raw carrot",
        "raw carrots",
        "sliced carrot",
        "sliced carrots",
        "carrot sticks",
        "cà rốt",
        "ca rot",
        "củ cà rốt",
        "cu ca rot",
    ],
    "Chuối": [
        "banana",
        "bananas",
        "ripe banana",
        "yellow banana",
        "chuối",
    ],
    "Táo": [
        "apple",
        "red apple",
        "green apple",
        "apples",
        "táo",
    ],
    "Cam": [
        "orange fruit",
        "oranges",
        "fresh orange",
        "orange slices",
        "peeled orange",
        "quả cam",
        "qua cam",
        "cam tươi",
        "cam tuoi",
    ],
    "Cá": [
        "fish",
        "fresh fish",
        "fish fillet",
        "cooked fish",
        "raw fish",
        "whole fish",
        "con cá",
        "thịt cá",
        "cá tươi",
        "cá sống",
        "phi lê cá",
    ],
    "Đậu nành": [
        "soybeans",
        "soy beans",
        "edamame",
        "soy bean ingredient",
        "đậu nành",
    ],
    "Sữa": [
        "milk",
        "fresh milk",
        "cow milk",
        "a glass of milk",
        "milk in a glass",
        "pouring milk into a glass",
        "white milk in a cup",
        "bottle of milk",
        "milk carton",
        "white milk",
        "glass of milk",
        "cup of milk",
        "pouring milk",
        "ly sữa",
        "sữa tươi",
        "sữa bò",
        "cốc sữa",
        "rót sữa vào ly",
        "sữa",
    ],
    "Yến mạch": [
        "oats",
        "oatmeal",
        "rolled oats",
        "oat flakes",
        "yến mạch",
    ],
    "Bí đỏ": [
        "pumpkin",
        "pumpkin pieces",
        "squash",
        "pumpkin slices",
        "bí đỏ",
    ],
}

FILENAME_INGREDIENT_PATTERNS = [
    ("Cà rốt", ["ca rot", "carrot"]),  # Check vegetables first
    ("Cà chua", ["ca chua", "tomato"]),
    ("Cam", ["qua cam", "orange fruit"]),
    ("Khoai lang", ["khoai lang", "sweet potato"]),  # MUST check before potato!
    ("Khoai tây", ["khoai tay", "potato"]),  # Check after sweet potato
    ("Thịt gà", ["thit ga", "chicken", "ga nguyen con", "whole chicken", "hen", "rooster", "poultry"]),
    ("Xúc xích", ["xuc xich", "sausage", "hot dog", "hotdog", "frankfurter", "wiener"]),
    ("Hàu", ["hau", "oyster", "oysters", "hau song", "hau tuoi"]),
    ("Sò", ["so", "ngheu", "clam", "clams", "so tuoi"]),
    ("Tôm", ["tom", "shrimp", "prawn", "tom su"]),
    ("Cua", ["con cua", "crab", "thit cua", "cua bien", "cua dong"]),
    ("Hải sản", ["hai san", "seafood", "shellfish"]),
    ("Cá", ["con ca", "thit ca", "fish"]),  # Removed dangerous "ca" alias
    ("Thịt lợn", ["thit lon", "thit heo", "heo", "lon", "pork"]),
    ("Thịt bò", ["thit bo", "beef", "bo"]),
    ("Trứng", ["trung", "egg"]),
    ("Nấm", ["nam", "mushroom"]),
    ("Đậu hũ", ["dau hu", "dau phu", "tofu"]),
    ("Rau cải", ["rau cai", "greens", "bok choy"]),
    ("Sữa", ["sua", "milk"]),
    ("Chuối", ["chuoi", "banana"]),
    ("Đậu nành", ["dau nanh", "soybean", "soy bean"]),
    ("Bí đỏ", ["bi do", "pumpkin"]),
    ("Yến mạch", ["yen mach", "oat", "oatmeal"]),
    ("Cơm", ["com", "rice"]),
    ("Táo", ["tao", "apple"]),
]

PROMPT_FEATURE_VERSION = "ingredient-prompts-v6-veg-fruit-guard"

_model = None
_processor = None
_model_name = None
_model_device = None
_text_features = None
_prompt_meta: list[tuple[str, str]] | None = None
_text_features_version = None


def _clip_model_name() -> str:
    return os.getenv("CLIP_MODEL_NAME", "openai/clip-vit-base-patch32")


def _log_clip_model_status(
    loaded: bool,
    device: str | None = None,
    model_name: str | None = None,
    error: str | None = None,
) -> None:
    logger.info(
        "[CLIP MODEL STATUS] %s",
        {
            "loaded": bool(loaded),
            "device": device or "",
            "modelName": model_name or _clip_model_name(),
            "error": error,
        },
    )


def _clip_feature_tensor(output: Any, feature_name: str):
    if hasattr(output, "norm"):
        return output
    pooler_output = getattr(output, "pooler_output", None)
    if pooler_output is not None and hasattr(pooler_output, "norm"):
        return pooler_output
    if isinstance(output, (tuple, list)):
        for item in output:
            if hasattr(item, "norm"):
                return item
    raise TypeError(f"CLIP {feature_name} features are not a tensor: {type(output).__name__}")


def recognize_ingredients_with_clip(
    image_bytes: bytes | None,
    filename: str | None = None,
    image_url: str | None = None,
) -> dict[str, Any]:
    # Check if feature is enabled
    if not _is_ingredient_recognition_enabled():
        logger.info("[CLIP INGREDIENT RECOGNITION] Feature disabled via ENABLE_INGREDIENT_IMAGE_RECOGNITION=false")
        return _ingredient_response(
            success=False,
            ingredients=[],
            candidates=[],
            message="Tính năng nhận diện nguyên liệu từ ảnh hiện đang tắt. Vui lòng nhập thủ công.",
            used_filename_fallback=False,
        )
    
    # Check if torch is available
    try:
        import torch
    except ImportError:
        logger.warning("[CLIP INGREDIENT RECOGNITION] torch not installed")
        return _ingredient_response(
            success=False,
            ingredients=[],
            candidates=[],
            message="Thiếu thư viện torch nên chưa thể nhận diện ảnh. Vui lòng cài dependency hoặc nhập thủ công.",
            used_filename_fallback=False,
        )
    
    try:
        return _recognize_ingredients_with_clip(image_bytes=image_bytes, filename=filename, image_url=image_url)
    except Exception as exc:
        logger.exception("[CLIP INGREDIENT ERROR] %s", exc)
        return _ingredient_response(
            success=False,
            ingredients=[],
            candidates=[],
            message=FAIL_MESSAGE,
            used_filename_fallback=False,
        )


def normalize_ingredient_output_name(name: str) -> str:
    """Normalize ingredient output names to standard format"""
    normalized = normalize_filename(name)
    if normalized in ["thit heo", "heo", "pork", "raw pork", "fresh pork", "pork slices"]:
        return "Thịt lợn"
    if normalized in ["thit lon", "lon"]:
        return "Thịt lợn"
    return name


def _recognize_ingredients_with_clip(
    image_bytes: bytes | None,
    filename: str | None,
    image_url: str | None,
) -> dict[str, Any]:
    import time
    start_time = time.time()
    
    # Log deduplication tracking for this request
    logged_rejections: set[str] = set()
    
    def log_rejection_once(key: str, message: str, payload: dict[str, Any]) -> None:
        """Log rejection messages only once per unique key to avoid duplicate logs."""
        if key in logged_rejections:
            return
        logged_rejections.add(key)
        logger.info(message, payload)
    
    logger.info("[INGREDIENT RECOGNITION CODE VERSION] clip-v6-veg-fruit-guard")
    
    try:
        import torch
    except Exception as exc:
        _log_clip_model_status(
            loaded=False,
            error=f"torch unavailable: {type(exc).__name__}: {exc}",
        )
        return _filename_fallback_response(filename, fallback_reason="torch unavailable", original_error=exc)

    try:
        from PIL import Image
    except Exception as exc:
        _log_clip_model_status(
            loaded=False,
            error=f"pillow unavailable: {type(exc).__name__}: {exc}",
        )
        return _filename_fallback_response(filename, fallback_reason="pillow unavailable", original_error=exc)

    model, processor = get_clip_model()
    loaded = model is not None and processor is not None
    if not loaded:
        return _filename_fallback_response(filename, fallback_reason="clip unavailable")

    resolved_bytes, source_type, image_mode, image_size = _load_image_bytes(image_bytes, image_url, Image)
    logger.info(
        "[CLIP IMAGE INPUT DEBUG] %s",
        {
            "fileName": filename or "",
            "hasImageBytes": bool(resolved_bytes),
            "imageMode": image_mode,
            "imageSize": image_size,
            "sourceType": source_type,
        },
    )

    image = Image.open(io.BytesIO(resolved_bytes))
    image.load()
    if image.mode != "RGB":
        image = image.convert("RGB")
    
    # Resize ảnh nếu quá lớn để tăng tốc (max 1024px)
    max_size = 1024
    original_size = image.size
    if max(image.size) > max_size:
        ratio = max_size / max(image.size)
        new_size = (int(image.size[0] * ratio), int(image.size[1] * ratio))
        image = image.resize(new_size, Image.Resampling.LANCZOS)
        logger.info("[CLIP IMAGE RESIZED] %s -> %s", original_size, new_size)

    try:
        grouped_candidates, top_prompts = _score_image_against_prompt_groups(image, model, processor)
    except Exception as exc:
        logger.exception("[CLIP IMAGE ENCODE ERROR] %s", exc)
        # Khi lỗi encode, không trả candidates đoán bừa
        return _ingredient_response(
            success=False,
            ingredients=[],
            candidates=[],
            message="Chưa nhận diện rõ nguyên liệu trong ảnh này. Bạn có thể nhập thủ công.",
            used_filename_fallback=False,
        )
    accepted_ingredients: list[str] = []
    used_filename_fallback = False

    # Log raw scores để debug
    if grouped_candidates:
        logger.info(
            "[IMAGE RECOGNITION RAW LABELS] %s",
            {
                "top5": [
                    {"name": c["name"], "score": c["score"]}
                    for c in grouped_candidates[:5]
                ]
            }
        )

    # Kiểm tra force accept từ top prompts trước
    forced = _force_accept_from_top_prompts(top_prompts, grouped_candidates, log_rejection_once)
    
    # PHẦN 1: Track acceptance reason for final safety gate
    # Initialize BEFORE checking forced, not after
    accepted_reason = None
    accepted_majority_info = None
    
    if forced:
        accepted_ingredients = [forced]
        # For sausage force accept, store the reason as majority type
        if forced == "Xúc xích":
            # Check if it meets majority criteria
            majority = get_prompt_majority(top_prompts, "Xúc xích")
            if majority["count"] >= 6 and majority["top3Count"] >= 3:
                accepted_reason = "sausage_prompt_majority"
                accepted_majority_info = majority
        logger.info("[INGREDIENT FORCE ACCEPTED FROM TOP PROMPT] %s", forced)
    
    # PROMPT MAJORITY ACCEPT: Check strong prompt consensus before threshold checks
    # This allows accepting clear ingredients even with lower scores if prompts strongly agree
    if not accepted_ingredients and grouped_candidates and top_prompts:
        best = grouped_candidates[0]
        best_name = best.get("name")
        best_score = float(best.get("score", 0) or 0)
        second_score = float(grouped_candidates[1].get("score", 0) or 0) if len(grouped_candidates) > 1 else 0
        second_name = grouped_candidates[1].get("name") if len(grouped_candidates) > 1 else None
        margin = best_score - second_score
        
        majority = get_prompt_majority(top_prompts, best_name)
        
        logger.info("[STRONG_PROMPT_MAJORITY_CHECK] %s", {
            "ingredient": best_name,
            "score": best_score,
            "secondName": second_name,
            "secondScore": second_score,
            "margin": margin,
            "promptMajority": majority,
        })
        
        # Check for vegetable/fruit/tuber blocker
        has_blocker = has_strong_veg_fruit_tuber_blocker(grouped_candidates, top_prompts, best_score)
        
        if has_blocker:
            logger.info("[STRONG_PROMPT_MAJORITY_BLOCKED] %s", {
                "ingredient": best_name,
                "blocker": "veg_fruit_tuber",
                "reason": "strong_veg_fruit_tuber_signal_prevents_meat_seafood_accept",
            })
        
        # PHẦN 1: Rule cho Thịt bò - majority accept
        if not accepted_ingredients and best_name == "Thịt bò" and not has_blocker:
            if (
                best_score >= 0.31
                and majority["count"] >= 6
                and majority["top3Count"] >= 3
                and majority["ratio"] >= 0.6
                and margin >= 0.02
            ):
                accepted_ingredients = ["Thịt bò"]
                accepted_reason = "beef_prompt_majority"
                accepted_majority_info = majority
                logger.info("[MEAT_PROMPT_MAJORITY_ACCEPT] ingredient=Thịt bò score=%.3f margin=%.3f majority=%s decision=accepted reason=beef_prompt_majority", 
                           best_score, margin, majority)
        
        # Rule cho Thịt lợn
        if not accepted_ingredients and best_name == "Thịt lợn" and not has_blocker:
            if (
                best_score >= 0.30
                and majority["count"] >= 6
                and majority["top3Count"] >= 3
                and margin >= 0.01
            ):
                accepted_ingredients = ["Thịt lợn"]
                accepted_reason = "pork_prompt_majority"
                accepted_majority_info = majority
                logger.info("[INGREDIENT ACCEPTED] pork_prompt_majority score=%.3f margin=%.3f majority=%s", 
                           best_score, margin, majority)
        
        # PHẦN 3: Rule cho Thịt gà - không bị block bởi meat/seafood competitors
        if not accepted_ingredients and best_name == "Thịt gà" and not has_blocker:
            if (
                best_score >= 0.32
                and majority["count"] >= 6
                and majority["top3Count"] >= 3
                and majority["ratio"] >= 0.6
                and margin >= 0.03
            ):
                accepted_ingredients = ["Thịt gà"]
                accepted_reason = "chicken_prompt_majority"
                accepted_majority_info = majority
                logger.info("[MEAT_PROMPT_MAJORITY_ACCEPT] ingredient=Thịt gà score=%.3f margin=%.3f majority=%s decision=accepted reason=chicken_prompt_majority", 
                           best_score, margin, majority)
        
        # Rule cho Tôm (không cần margin cao vì second thường là Hải sản)
        if not accepted_ingredients and best_name == "Tôm" and not has_blocker:
            if (
                best_score >= 0.27
                and majority["count"] >= 6
                and majority["top3Count"] >= 3
            ):
                accepted_ingredients = ["Tôm"]
                accepted_reason = "shrimp_prompt_majority"
                accepted_majority_info = majority
                logger.info("[INGREDIENT ACCEPTED] shrimp_prompt_majority score=%.3f majority=%s", 
                           best_score, majority)
        
        # Rule cho Cua (second có thể là Hải sản, không phải competitor)
        if not accepted_ingredients and best_name == "Cua" and not has_blocker:
            if (
                best_score >= 0.30
                and majority["count"] >= 6
                and majority["top3Count"] >= 2
            ):
                accepted_ingredients = ["Cua"]
                accepted_reason = "crab_prompt_majority"
                accepted_majority_info = majority
                logger.info("[INGREDIENT ACCEPTED] crab_prompt_majority score=%.3f majority=%s", 
                           best_score, majority)
        
        # Rule cho Cá
        if not accepted_ingredients and best_name == "Cá" and not has_blocker:
            if (
                best_score >= 0.28
                and majority["count"] >= 6
                and majority["top3Count"] >= 3
            ):
                accepted_ingredients = ["Cá"]
                accepted_reason = "fish_prompt_majority"
                accepted_majority_info = majority
                logger.info("[INGREDIENT ACCEPTED] fish_prompt_majority score=%.3f majority=%s", 
                           best_score, majority)
        
        # PHẦN 4: Rule cho Xúc xích - majority accept
        if not accepted_ingredients and best_name == "Xúc xích" and not has_blocker:
            sausage_rank = grouped_candidates.index(best)
            if (
                best_score >= 0.30
                and majority["count"] >= 6
                and majority["top3Count"] >= 3
                and majority["ratio"] >= 0.6
                and sausage_rank == 0
            ):
                accepted_ingredients = ["Xúc xích"]
                accepted_reason = "sausage_prompt_majority"
                accepted_majority_info = majority
                logger.info("[MEAT_PROMPT_MAJORITY_ACCEPT] ingredient=Xúc xích score=%.3f margin=%.3f majority=%s decision=accepted reason=sausage_prompt_majority", 
                           best_score, margin, majority)
            else:
                # Log why sausage majority was not accepted
                logger.info("[SAUSAGE_MAJORITY_REJECTED] %s", {
                    "ingredient": "Xúc xích",
                    "score": best_score,
                    "rank": sausage_rank,
                    "majority": majority,
                    "checks": {
                        "score_gte_0_30": best_score >= 0.30,
                        "count_gte_6": majority["count"] >= 6,
                        "top3Count_gte_3": majority["top3Count"] >= 3,
                        "ratio_gte_0_6": majority["ratio"] >= 0.6,
                        "rank_eq_0": sausage_rank == 0,
                    }
                })
        elif not accepted_ingredients and best_name == "Xúc xích" and has_blocker:
            # Log blocker details
            logger.info("[SAUSAGE_BLOCKED_BY_VEG] %s", {
                "ingredient": "Xúc xích",
                "score": best_score,
                "hasBlocker": has_blocker,
                "reason": "veg_fruit_tuber_blocker",
            })
    
    # PHẦN 4: Fix forced Khoai tây nếu có tín hiệu Khoai lang rõ
    if accepted_ingredients and accepted_ingredients[0] == "Khoai tây":
        sweet_potato_candidate_check = next(
            (c for c in grouped_candidates if c.get("name") == "Khoai lang"),
            None,
        )
        strong_sweet_signal_check = has_strong_sweet_potato_signal(top_prompts, grouped_candidates)
        strong_potato_signal_check = has_strong_potato_signal(top_prompts, grouped_candidates)
        
        # Cancel forced potato nếu có sweet signal rõ VÀ KHÔNG có potato signal rõ
        if strong_sweet_signal_check and not strong_potato_signal_check and sweet_potato_candidate_check:
            sweet_potato_score_check = float(sweet_potato_candidate_check.get("score", 0) or 0)
            sweet_potato_rank_check = grouped_candidates.index(sweet_potato_candidate_check)
            potato_score_check = float(next((c.get("score", 0) for c in grouped_candidates if c.get("name") == "Khoai tây"), 0) or 0)
            
            if sweet_potato_rank_check <= 3 and sweet_potato_score_check >= potato_score_check - 0.06:
                # Cancel forced Khoai tây
                accepted_ingredients = ["Khoai lang"]
                logger.info("[POTATO_GUARD] cancel forced potato due to sweet potato signal", {
                    "forcedIngredient": "Khoai tây",
                    "overrideTo": "Khoai lang",
                    "sweetPotatoScore": sweet_potato_score_check,
                    "potatoScore": potato_score_check,
                    "strongSweetSignal": strong_sweet_signal_check,
                    "strongPotatoSignal": strong_potato_signal_check,
                })


    # Rule ưu tiên cho Sữa - kiểm tra trước Thịt gà
    milk_candidate = next(
        (c for c in grouped_candidates if c.get("name") == "Sữa"),
        None,
    )
    
    if not accepted_ingredients and milk_candidate:
        milk_score = float(milk_candidate.get("score", 0) or 0)
        milk_rank = grouped_candidates.index(milk_candidate)
        
        logger.info("[MILK DEBUG] %s", {
            "rank": milk_rank,
            "score": milk_score,
            "candidate": milk_candidate,
        })
        
        # Accept Sữa nếu trong top 3 với score >= 0.14 (milk has no special restrictions)
        if milk_rank <= 3 and milk_score >= 0.14:
            accepted_ingredients = ["Sữa"]
            logger.info("[INGREDIENT ACCEPTED] Milk top3: %.3f", milk_score)

    # Rule ưu tiên cho Xúc xích - kiểm tra trước Thịt gà
    sausage_candidate = next(
        (c for c in grouped_candidates if c.get("name") == "Xúc xích"),
        None,
    )
    
    if not accepted_ingredients and sausage_candidate:
        sausage_score = float(sausage_candidate.get("score", 0) or 0)
        sausage_rank = grouped_candidates.index(sausage_candidate)
        
        logger.info("[SAUSAGE DEBUG] %s", {
            "rank": sausage_rank,
            "score": sausage_score,
            "candidate": sausage_candidate,
        })
        
        # PHẦN 1 & 2: If sausage is accepted via majority, skip this rule
        # This priority rule is for non-majority cases only
        # Majority cases are already handled earlier in the prompt majority section
        
        # Check safety before accepting (non-majority case)
        can_accept, reject_reason = can_accept_candidate(sausage_candidate, grouped_candidates, "sausage_top3", allow_majority_override=False)
        
        if can_accept and sausage_rank <= 3 and sausage_score >= 0.12:
            accepted_ingredients = ["Xúc xích"]
            logger.info("[INGREDIENT ACCEPTED] Sausage top3: %.3f", sausage_score)
        elif not can_accept:
            log_rejection_once(
                f"special_reject:sausage_top3:{reject_reason}",
                "[SPECIAL_ACCEPT_REJECTED] %s",
                {
                    "rule": "sausage_top3",
                    "candidate": {"name": "Xúc xích", "score": sausage_score, "rank": sausage_rank + 1},
                    "reason": reject_reason,
                    "groupedTop5": [{"name": c.get("name"), "score": c.get("score")} for c in grouped_candidates[:5]],
                }
            )

    # PHẦN 4: High-confidence accept cho Cà rốt/Cà chua/Cam - ưu tiên trước seafood
    carrot_candidate = next(
        (c for c in grouped_candidates if c.get("name") == "Cà rốt"),
        None,
    )
    tomato_candidate = next(
        (c for c in grouped_candidates if c.get("name") == "Cà chua"),
        None,
    )
    orange_candidate = next(
        (c for c in grouped_candidates if c.get("name") == "Cam"),
        None,
    )
    sweet_potato_candidate = next(
        (c for c in grouped_candidates if c.get("name") == "Khoai lang"),
        None,
    )
    potato_candidate = next(
        (c for c in grouped_candidates if c.get("name") == "Khoai tây"),
        None,
    )
    pumpkin_candidate = next(
        (c for c in grouped_candidates if c.get("name") == "Bí đỏ"),
        None,
    )

    # GUARD: Khoai tây vs Khoai lang - cải thiện logic với cả 2 tín hiệu
    strong_sweet_signal = has_strong_sweet_potato_signal(top_prompts, grouped_candidates)
    strong_potato_signal = has_strong_potato_signal(top_prompts, grouped_candidates)
    
    # PHẦN 5: High confidence Khoai tây với strong potato signal - chạy TRƯỚC sweet potato nếu có tín hiệu rõ
    if not accepted_ingredients and strong_potato_signal and potato_candidate:
        potato_score = float(potato_candidate.get("score", 0) or 0)
        potato_rank = grouped_candidates.index(potato_candidate)
        
        # PHẦN 3: Chỉ accept Khoai tây nếu rank <= 5
        if potato_rank <= 3 and potato_score >= 0.24:
            # Nếu có tín hiệu potato rõ và không có tín hiệu sweet potato rõ, ưu tiên Khoai tây
            if not strong_sweet_signal:
                if not sweet_potato_candidate or potato_score >= sweet_potato_candidate.get("score", 0) - 0.08:
                    accepted_ingredients = ["Khoai tây"]
                    logger.info("[POTATO_HIGH_CONFIDENCE] accepted due to strong potato signal", {
                        "potatoScore": potato_score,
                        "potatoRank": potato_rank + 1,
                        "sweetPotatoScore": sweet_potato_candidate.get("score", 0) if sweet_potato_candidate else None,
                        "strongPotatoSignal": strong_potato_signal,
                        "strongSweetSignal": strong_sweet_signal,
                    })
    
    # PHẦN 3: High confidence Khoai lang phải chạy TRƯỚC high confidence Khoai tây nếu có tín hiệu
    if not accepted_ingredients and strong_sweet_signal and sweet_potato_candidate:
        sweet_potato_score = float(sweet_potato_candidate.get("score", 0) or 0)
        sweet_potato_rank = grouped_candidates.index(sweet_potato_candidate)
        
        # Đếm sweet prompts
        sweet_top_prompt_count_check = sum(1 for p in top_prompts[:10] if str(p.get("ingredient", "")) == "Khoai lang")
        
        # PHẦN 3: Chỉ accept Khoai lang nếu rank <= 5
        if sweet_potato_rank <= 3 and sweet_potato_score >= 0.24 and sweet_top_prompt_count_check >= 2:
            # Nếu có tín hiệu khoai lang rõ, accept ngay khi điểm không thua quá xa potato
            if not potato_candidate or sweet_potato_score >= potato_candidate.get("score", 0) - 0.015:
                accepted_ingredients = ["Khoai lang"]
                logger.info("[SWEET_POTATO_HIGH_CONFIDENCE] accepted before potato due to strong signal", {
                    "sweetPotatoScore": sweet_potato_score,
                    "sweetPotatoRank": sweet_potato_rank + 1,
                    "potatoScore": potato_candidate.get("score", 0) if potato_candidate else None,
                    "strongSweetSignal": strong_sweet_signal,
                    "strongPotatoSignal": strong_potato_signal,
                    "sweetTopPromptCount": sweet_top_prompt_count_check,
                })

    # PHẦN 1 & 2 & 4: Guard Khoai tây vs Khoai lang với cả 2 tín hiệu
    if not accepted_ingredients and potato_candidate and sweet_potato_candidate:
        potato_score = float(potato_candidate.get("score", 0) or 0)
        sweet_potato_score = float(sweet_potato_candidate.get("score", 0) or 0)
        potato_rank = grouped_candidates.index(potato_candidate)
        sweet_potato_rank = grouped_candidates.index(sweet_potato_candidate)
        
        delta_potato_minus_sweet = potato_score - sweet_potato_score
        
        # Count potato vs sweet potato prompts in top 10
        potato_top_prompt_count = 0
        sweet_top_prompt_count = 0
        potato_prompt_score_sum = 0.0
        sweet_prompt_score_sum = 0.0
        
        for p in top_prompts[:10]:
            ingredient = str(p.get("ingredient", ""))
            score = float(p.get("score", 0) or 0)
            if ingredient == "Khoai tây":
                potato_top_prompt_count += 1
                potato_prompt_score_sum += score
            elif ingredient == "Khoai lang":
                sweet_top_prompt_count += 1
                sweet_prompt_score_sum += score
        
        logger.info("[POTATO_SIGNAL_DEBUG] %s", {
            "potatoPromptCount": potato_top_prompt_count,
            "sweetPromptCount": sweet_top_prompt_count,
            "potatoPromptScoreSum": potato_prompt_score_sum,
            "sweetPromptScoreSum": sweet_prompt_score_sum,
            "potatoCandidateScore": potato_score,
            "sweetCandidateScore": sweet_potato_score,
            "strongPotatoSignal": strong_potato_signal,
            "strongSweetSignal": strong_sweet_signal,
        })
        
        logger.info("[POTATO_GUARD] analyzing", {
            "potato": {"rank": potato_rank + 1, "score": potato_score},
            "sweetPotato": {"rank": sweet_potato_rank + 1, "score": sweet_potato_score},
            "strongPotatoSignal": strong_potato_signal,
            "strongSweetSignal": strong_sweet_signal,
            "deltaPotatoMinusSweet": delta_potato_minus_sweet,
            "potatoTopPromptCount": potato_top_prompt_count,
            "sweetTopPromptCount": sweet_top_prompt_count,
            "topPrompts": [str(p.get("prompt") or p.get("text") or p) for p in top_prompts[:10]],
        })
        
        # PHẦN 3: Guard chặn Khoai tây khi rank quá thấp
        if potato_rank > 5 and potato_top_prompt_count < 2:
            log_rejection_once(
                "potato_guard_skip:rank_too_low_no_prompt",
                "[POTATO_GUARD_SKIPPED] %s",
                {
                    "reason": "potato_rank_too_low_no_prompt_evidence",
                    "potatoRank": potato_rank + 1,
                    "potatoScore": potato_score,
                    "sweetRank": sweet_potato_rank + 1,
                    "sweetScore": sweet_potato_score,
                    "potatoTopPromptCount": potato_top_prompt_count,
                    "sweetTopPromptCount": sweet_top_prompt_count,
                    "currentTopCandidate": grouped_candidates[0].get("name") if grouped_candidates else None,
                }
            )
            # Không cho phép potato guard quyết định
            # Skip toàn bộ potato guard logic
        else:
            # DECISION LOGIC:
            # 0. PRIORITY: Khoai tây top1 với majority prompts và không có sweet prompts
            if potato_rank == 0 and potato_score >= sweet_potato_score + 0.015 and potato_top_prompt_count >= 3 and sweet_top_prompt_count == 0:
                accepted_ingredients = ["Khoai tây"]
                logger.info("[POTATO_GUARD] decision", {
                    "decision": "Khoai tây",
                    "reason": "potato_top1_majority_prompts_no_sweet_prompts",
                    "potatoScore": potato_score,
                    "sweetPotatoScore": sweet_potato_score,
                    "delta": delta_potato_minus_sweet,
                    "potatoTopPromptCount": potato_top_prompt_count,
                    "sweetTopPromptCount": sweet_top_prompt_count,
                })
            
            # 1. Nếu Khoai tây top1 và score cao hơn ít nhất 0.015
            if not accepted_ingredients and potato_rank < sweet_potato_rank and delta_potato_minus_sweet >= 0.015:
                if not strong_sweet_signal:
                    accepted_ingredients = ["Khoai tây"]
                    logger.info("[POTATO_GUARD] decision", {
                        "decision": "Khoai tây",
                        "reason": "potato_top1_and_score_higher",
                        "potatoScore": potato_score,
                        "sweetPotatoScore": sweet_potato_score,
                        "delta": delta_potato_minus_sweet,
                    })
            
            # 2. Nếu top prompts phần lớn là Khoai tây (>= 3 prompts) và potato score >= sweet score
            if not accepted_ingredients and potato_top_prompt_count >= 3 and potato_score >= sweet_potato_score:
                accepted_ingredients = ["Khoai tây"]
                logger.info("[POTATO_GUARD] decision", {
                    "decision": "Khoai tây",
                    "reason": "top_prompts_majority_potato",
                    "potatoTopPromptCount": potato_top_prompt_count,
                    "sweetTopPromptCount": sweet_top_prompt_count,
                    "potatoScore": potato_score,
                    "sweetPotatoScore": sweet_potato_score,
                })
            
            # 3. Nếu có tín hiệu khoai tây rõ và không có tín hiệu khoai lang rõ
            if not accepted_ingredients and strong_potato_signal and not strong_sweet_signal:
                if potato_score >= sweet_potato_score - 0.08:
                    accepted_ingredients = ["Khoai tây"]
                    logger.info("[POTATO_GUARD] decision", {
                        "decision": "Khoai tây",
                        "reason": "strong_potato_signal_no_sweet",
                        "potatoScore": potato_score,
                        "sweetPotatoScore": sweet_potato_score,
                    })
            
            # 4. Nếu có tín hiệu khoai lang rõ, ưu tiên Khoai lang khi điểm không thua quá nhiều
            # CHỈ khi sweet_top_prompt_count >= 2
            if not accepted_ingredients and strong_sweet_signal and not strong_potato_signal and sweet_top_prompt_count >= 2:
                if sweet_potato_score >= potato_score - 0.015:
                    accepted_ingredients = ["Khoai lang"]
                    logger.info("[POTATO_GUARD] decision", {
                        "decision": "Khoai lang",
                        "reason": "strong_sweet_signal_with_prompts",
                        "potatoScore": potato_score,
                        "sweetPotatoScore": sweet_potato_score,
                        "sweetTopPromptCount": sweet_top_prompt_count,
                    })
            
            # 5. Nếu không có tín hiệu khoai lang rõ và điểm gần nhau, chọn Khoai tây
            if not accepted_ingredients and not strong_sweet_signal and abs(delta_potato_minus_sweet) < 0.08:
                accepted_ingredients = ["Khoai tây"]
                logger.info("[POTATO_GUARD] decision", {
                    "decision": "Khoai tây",
                    "reason": "no_sweet_signal_close_scores",
                    "potatoScore": potato_score,
                    "sweetPotatoScore": sweet_potato_score,
                    "delta": delta_potato_minus_sweet,
                })
            
            # 6. Chỉ chọn Khoai lang nếu vượt rõ
            if not accepted_ingredients and sweet_potato_score >= potato_score + 0.08:
                accepted_ingredients = ["Khoai lang"]
                logger.info("[POTATO_GUARD] decision", {
                    "decision": "Khoai lang",
                    "reason": "sweet_score_clearly_higher",
                    "potatoScore": potato_score,
                    "sweetPotatoScore": sweet_potato_score,
                    "delta": delta_potato_minus_sweet,
                })

    # High confidence Khoai tây (chỉ chạy khi chưa có decision và không có strong sweet signal)
    if not accepted_ingredients and potato_candidate and not strong_sweet_signal:
        potato_score = float(potato_candidate.get("score", 0) or 0)
        potato_rank = grouped_candidates.index(potato_candidate)
        
        # PHẦN 3: Đếm potato top prompt count để guard
        potato_top_prompt_count_check = sum(1 for p in top_prompts[:10] if str(p.get("ingredient", "")) == "Khoai tây")
        
        # PHẦN 3: Chỉ accept nếu rank <= 5 hoặc có prompt evidence
        if potato_rank > 5 and potato_top_prompt_count_check < 2:
            log_rejection_once(
                "potato_guard_skip:high_confidence_rank_low",
                "[POTATO_GUARD_SKIPPED] %s",
                {
                    "reason": "potato_high_confidence_blocked_rank_too_low",
                    "potatoRank": potato_rank + 1,
                    "potatoScore": potato_score,
                    "potatoTopPromptCount": potato_top_prompt_count_check,
                }
            )
        elif potato_rank <= 3 and potato_score >= 0.26:
            # Chỉ accept nếu không có sweet potato vượt rõ rệt VÀ không có strong sweet signal
            if not sweet_potato_candidate:
                accepted_ingredients = ["Khoai tây"]
                logger.info("[POTATO_HIGH_CONFIDENCE] accepted potato (no sweet potato competition): %.3f", potato_score)
            else:
                sweet_potato_score = float(sweet_potato_candidate.get("score", 0) or 0)
                # Accept potato khi không có strong sweet signal và điểm không thua xa
                if sweet_potato_score <= potato_score + 0.04:
                    accepted_ingredients = ["Khoai tây"]
                    logger.info("[POTATO_HIGH_CONFIDENCE] accepted before sweet potato", {
                        "potatoScore": potato_score,
                        "sweetPotatoScore": sweet_potato_score,
                        "strongSweetSignal": strong_sweet_signal,
                        "strongPotatoSignal": strong_potato_signal,
                    })

    # GUARD: Khoai lang vs Cà chua - ưu tiên Khoai lang nếu điểm gần nhau
    if not accepted_ingredients and sweet_potato_candidate and tomato_candidate:
        sweet_potato_score = float(sweet_potato_candidate.get("score", 0) or 0)
        tomato_score = float(tomato_candidate.get("score", 0) or 0)
        sweet_potato_rank = grouped_candidates.index(sweet_potato_candidate)
        tomato_rank = grouped_candidates.index(tomato_candidate)
        
        delta = tomato_score - sweet_potato_score
        
        # Nếu điểm gần nhau (delta < 0.07), ưu tiên Khoai lang vì vỏ đỏ/tím dễ bị tomato ăn nhầm
        if sweet_potato_rank <= 3 and sweet_potato_score >= 0.25:
            if delta < 0.07:
                accepted_ingredients = ["Khoai lang"]
                logger.info("[SWEET_POTATO_TOMATO_GUARD] prefer sweet potato over tomato because scores are close", {
                    "sweetPotatoScore": sweet_potato_score,
                    "tomatoScore": tomato_score,
                    "delta": delta,
                })

    # High confidence Khoai lang phải chạy trước relaxed Tomato
    if not accepted_ingredients and sweet_potato_candidate:
        sweet_potato_score = float(sweet_potato_candidate.get("score", 0) or 0)
        sweet_potato_rank = grouped_candidates.index(sweet_potato_candidate)
        
        # PHẦN 3: Đếm sweet potato top prompt count để guard
        sweet_top_prompt_count_check2 = sum(1 for p in top_prompts[:10] if str(p.get("ingredient", "")) == "Khoai lang")
        
        # PHẦN 3: Chỉ accept nếu rank <= 5 hoặc có prompt evidence
        if sweet_potato_rank > 5 and sweet_top_prompt_count_check2 < 2:
            log_rejection_once(
                "potato_guard_skip:sweet_high_confidence_rank_low",
                "[POTATO_GUARD_SKIPPED] %s",
                {
                    "reason": "sweet_potato_high_confidence_blocked_rank_too_low",
                    "sweetPotatoRank": sweet_potato_rank + 1,
                    "sweetPotatoScore": sweet_potato_score,
                    "sweetTopPromptCount": sweet_top_prompt_count_check2,
                }
            )
        elif sweet_potato_rank <= 3 and sweet_potato_score >= 0.25:
            # Chỉ accept nếu không có tomato vượt rõ rệt
            if not tomato_candidate:
                accepted_ingredients = ["Khoai lang"]
                logger.info("[SWEET_POTATO_HIGH_CONFIDENCE] accepted sweet potato (no tomato competition): %.3f", sweet_potato_score)
            else:
                tomato_score = float(tomato_candidate.get("score", 0) or 0)
                if tomato_score <= sweet_potato_score + 0.07:
                    accepted_ingredients = ["Khoai lang"]
                    logger.info("[SWEET_POTATO_HIGH_CONFIDENCE] accepted before tomato", {
                        "sweetPotatoScore": sweet_potato_score,
                        "tomatoScore": tomato_score,
                    })

    # Accept Cà rốt nếu trong top 3 với score >= 0.28
    # PHẦN 2: Không accept nếu top1 là meat/seafood/sausage với prompt majority rõ
    if not accepted_ingredients and carrot_candidate:
        carrot_score = float(carrot_candidate.get("score", 0) or 0)
        carrot_rank = grouped_candidates.index(carrot_candidate)
        
        # Check if top candidate is meat/seafood with strong majority
        top_candidate = grouped_candidates[0] if grouped_candidates else None
        skip_carrot_for_meat = False
        
        if top_candidate:
            top_name = top_candidate.get("name")
            top_score = float(top_candidate.get("score", 0) or 0)
            top_majority = get_prompt_majority(top_prompts, top_name)
            
            if top_name in (MEAT_NAMES | SEAFOOD_NAMES | SAUSAGE_NAMES):
                if top_score >= 0.30 and top_majority["count"] >= 6 and top_majority["top3Count"] >= 3:
                    skip_carrot_for_meat = True
                    logger.info("[CARROT_HIGH_CONFIDENCE_SKIPPED] %s", {
                        "carrotCandidate": {"rank": carrot_rank + 1, "score": carrot_score},
                        "topCandidate": {"name": top_name, "score": top_score},
                        "topMajority": top_majority,
                        "reason": "top_meat_or_seafood_prompt_majority_stronger",
                    })
        
        if not skip_carrot_for_meat and carrot_rank <= 3 and carrot_score >= 0.28:
            accepted_ingredients = ["Cà rốt"]
            logger.info("[INGREDIENT ACCEPTED] Carrot high confidence: %.3f", carrot_score)

    # Accept Cà chua nếu trong top 3 với score >= 0.27 (và đã qua guard với Khoai lang)
    # PHẦN 7: Không accept nếu top1 là meat/seafood/sausage với prompt majority rõ
    if not accepted_ingredients and tomato_candidate:
        tomato_score = float(tomato_candidate.get("score", 0) or 0)
        tomato_rank = grouped_candidates.index(tomato_candidate)
        
        # Check if top candidate is meat/seafood with strong majority
        top_candidate = grouped_candidates[0] if grouped_candidates else None
        skip_tomato_for_meat = False
        
        if top_candidate:
            top_name = top_candidate.get("name")
            top_score = float(top_candidate.get("score", 0) or 0)
            top_majority = get_prompt_majority(top_prompts, top_name)
            
            if top_name in (MEAT_NAMES | SEAFOOD_NAMES | SAUSAGE_NAMES):
                if top_score >= 0.30 and top_majority["count"] >= 6 and top_majority["top3Count"] >= 3:
                    skip_tomato_for_meat = True
                    logger.info("[VEG_HIGH_CONFIDENCE_SKIPPED] %s", {
                        "vegCandidate": {"name": "Cà chua", "rank": tomato_rank + 1, "score": tomato_score},
                        "topCandidate": {"name": top_name, "score": top_score},
                        "topMajority": top_majority,
                        "reason": "top_meat_or_seafood_prompt_majority_stronger",
                    })
        
        if not skip_tomato_for_meat and tomato_rank <= 3 and tomato_score >= 0.27:
            # Kiểm tra lại sweet potato không vượt quá gần
            if sweet_potato_candidate:
                sweet_potato_score = float(sweet_potato_candidate.get("score", 0) or 0)
                if sweet_potato_score >= tomato_score - 0.08:
                    # Sweet potato quá gần, không accept tomato
                    logger.info("[TOMATO BLOCKED] Sweet potato too close: %.3f vs %.3f", sweet_potato_score, tomato_score)
                else:
                    accepted_ingredients = ["Cà chua"]
                    logger.info("[INGREDIENT ACCEPTED] Tomato high confidence: %.3f", tomato_score)
            else:
                accepted_ingredients = ["Cà chua"]
                logger.info("[INGREDIENT ACCEPTED] Tomato high confidence: %.3f", tomato_score)

    # Accept Cam nếu trong top 3 với score >= 0.27
    # PHẦN 7: Không accept nếu top1 là meat/seafood/sausage với prompt majority rõ
    if not accepted_ingredients and orange_candidate:
        orange_score = float(orange_candidate.get("score", 0) or 0)
        orange_rank = grouped_candidates.index(orange_candidate)
        
        # Check if top candidate is meat/seafood with strong majority
        top_candidate = grouped_candidates[0] if grouped_candidates else None
        skip_orange_for_meat = False
        
        if top_candidate:
            top_name = top_candidate.get("name")
            top_score = float(top_candidate.get("score", 0) or 0)
            top_majority = get_prompt_majority(top_prompts, top_name)
            
            if top_name in (MEAT_NAMES | SEAFOOD_NAMES | SAUSAGE_NAMES):
                if top_score >= 0.30 and top_majority["count"] >= 6 and top_majority["top3Count"] >= 3:
                    skip_orange_for_meat = True
                    logger.info("[VEG_HIGH_CONFIDENCE_SKIPPED] %s", {
                        "vegCandidate": {"name": "Cam", "rank": orange_rank + 1, "score": orange_score},
                        "topCandidate": {"name": top_name, "score": top_score},
                        "topMajority": top_majority,
                        "reason": "top_meat_or_seafood_prompt_majority_stronger",
                    })
        
        if not skip_orange_for_meat and orange_rank <= 3 and orange_score >= 0.27:
            accepted_ingredients = ["Cam"]
            logger.info("[INGREDIENT ACCEPTED] Orange high confidence: %.3f", orange_score)

    # PHẦN 2: Guard rau củ/quả trước cá/hải sản
    fish_candidate = next(
        (c for c in grouped_candidates if c.get("name") == "Cá"),
        None,
    )
    crab_candidate = next(
        (c for c in grouped_candidates if c.get("name") == "Cua"),
        None,
    )
    seafood_candidate = next(
        (c for c in grouped_candidates if c.get("name") == "Hải sản"),
        None,
    )
    shrimp_candidate = next(
        (c for c in grouped_candidates if c.get("name") == "Tôm"),
        None,
    )
    clam_candidate = next(
        (c for c in grouped_candidates if c.get("name") == "Sò"),
        None,
    )
    oyster_candidate = next(
        (c for c in grouped_candidates if c.get("name") == "Hàu"),
        None,
    )

    # Tìm best vegetable/fruit candidate
    vegetable_or_fruit_candidates = [
        carrot_candidate,
        tomato_candidate,
        orange_candidate,
        sweet_potato_candidate,
        pumpkin_candidate,
    ]
    vegetable_or_fruit_candidates = [c for c in vegetable_or_fruit_candidates if c is not None]
    
    best_veg_fruit = None
    if vegetable_or_fruit_candidates:
        best_veg_fruit = max(vegetable_or_fruit_candidates, key=lambda c: float(c.get("score", 0) or 0))
    
    # Guard: Nếu có rau củ/quả trong top 3 với score >= 0.28, ưu tiên nó trước seafood
    if not accepted_ingredients and best_veg_fruit:
        best_veg_fruit_score = float(best_veg_fruit.get("score", 0) or 0)
        best_veg_fruit_rank = grouped_candidates.index(best_veg_fruit)
        best_veg_fruit_name = best_veg_fruit.get("name")
        
        # PHẦN 3 & 4: Guard cho Khoai tây - không accept nếu rank quá thấp
        if best_veg_fruit_name == "Khoai tây":
            potato_top_prompt_count_guard = sum(1 for p in top_prompts[:10] if str(p.get("ingredient", "")) == "Khoai tây")
            if best_veg_fruit_rank > 5 and potato_top_prompt_count_guard < 2:
                log_rejection_once(
                    "potato_guard_skip:best_veg_fruit_rank_low",
                    "[POTATO_GUARD_SKIPPED] %s",
                    {
                        "reason": "potato_in_best_veg_fruit_blocked_rank_too_low",
                        "potatoRank": best_veg_fruit_rank + 1,
                        "potatoScore": best_veg_fruit_score,
                        "potatoTopPromptCount": potato_top_prompt_count_guard,
                        "currentTopCandidate": grouped_candidates[0].get("name") if grouped_candidates else None,
                    }
                )
                # Không accept, skip logic này
                best_veg_fruit = None
                best_veg_fruit_score = 0.0
        
        # Tìm best seafood candidate
        if best_veg_fruit:
            seafood_candidates = [fish_candidate, crab_candidate, seafood_candidate, shrimp_candidate, clam_candidate, oyster_candidate]
            seafood_candidates = [c for c in seafood_candidates if c is not None]
            best_seafood = None
            if seafood_candidates:
                best_seafood = max(seafood_candidates, key=lambda c: float(c.get("score", 0) or 0))
            
            if best_veg_fruit_rank <= 3 and best_veg_fruit_score >= 0.28:
                # Nếu seafood không hơn rõ rệt (>= 0.04), ưu tiên rau củ/quả
                if best_seafood:
                    best_seafood_score = float(best_seafood.get("score", 0) or 0)
                    if best_seafood_score <= best_veg_fruit_score + 0.04:
                        accepted_ingredients = [best_veg_fruit_name]
                        logger.info("[INGREDIENT ACCEPTED] Vegetable/Fruit guard over seafood", {
                            "vegFruit": best_veg_fruit_name,
                            "vegFruitScore": best_veg_fruit_score,
                            "seafoodScore": best_seafood_score,
                        })
                else:
                    # Không có seafood candidate, accept rau củ/quả
                    accepted_ingredients = [best_veg_fruit_name]
                    logger.info("[INGREDIENT ACCEPTED] Vegetable/Fruit no seafood competition: %.3f", best_veg_fruit_score)

    # PHẦN 5: Siết rule Cá/Cua/Hải sản - không accept nếu có rau củ/quả trong top 3
    top3_names = [c.get("name") for c in grouped_candidates[:3]]
    blocking_veg_fruit = ["Cà rốt", "Cà chua", "Cam", "Khoai lang", "Bí đỏ", "Khoai tây"]
    has_blocking_veg_fruit_in_top3 = any(name in top3_names for name in blocking_veg_fruit)

    # Log debug info cho vegetable/fruit guard
    logger.info("[VEG_FRUIT_OVER_SEAFOOD_GUARD] %s", {
        "bestVegFruit": best_veg_fruit,
        "fishCandidate": fish_candidate,
        "crabCandidate": crab_candidate,
        "seafoodCandidate": seafood_candidate,
        "hasBlockingVegFruitInTop3": has_blocking_veg_fruit_in_top3,
        "top3Names": top3_names,
        "decision": accepted_ingredients,
    })

    # Get pork, chicken, beef candidates for guard logic
    pork_candidate = next(
        (c for c in grouped_candidates if c.get("name") in ["Thịt lợn", "Thịt heo"]),
        None,
    )
    chicken_candidate = next(
        (c for c in grouped_candidates if c.get("name") == "Thịt gà"),
        None,
    )
    beef_candidate = next(
        (c for c in grouped_candidates if c.get("name") == "Thịt bò"),
        None,
    )

    # Guard: Pork over chicken if both present and pork score is close
    if not accepted_ingredients and pork_candidate and chicken_candidate:
        pork_score = float(pork_candidate.get("score", 0) or 0)
        chicken_score = float(chicken_candidate.get("score", 0) or 0)
        pork_rank = grouped_candidates.index(pork_candidate)
        
        # Check safety before accepting
        can_accept, reject_reason = can_accept_candidate(pork_candidate, grouped_candidates, "pork_over_chicken", allow_majority_override=False)
        
        if can_accept and pork_rank <= 5 and pork_score >= chicken_score - 0.03:
            accepted_ingredients = ["Thịt lợn"]
            logger.info("[INGREDIENT ACCEPTED] Pork over chicken guard", {
                "pork_score": pork_score,
                "chicken_score": chicken_score,
                "pork_rank": pork_rank,
            })
        elif not can_accept:
            log_rejection_once(
                f"special_reject:pork_over_chicken:{reject_reason}",
                "[SPECIAL_ACCEPT_REJECTED] %s",
                {
                    "rule": "pork_over_chicken",
                    "candidate": {"name": "Thịt lợn", "score": pork_score, "rank": pork_rank + 1},
                    "reason": reject_reason,
                    "groupedTop5": [{"name": c.get("name"), "score": c.get("score")} for c in grouped_candidates[:5]],
                }
            )

    # Relaxed rule for pork - accept if in top 3 with score >= 0.12
    if not accepted_ingredients and pork_candidate:
        pork_score = float(pork_candidate.get("score", 0) or 0)
        pork_rank = grouped_candidates.index(pork_candidate)
        
        # Check safety before accepting
        can_accept, reject_reason = can_accept_candidate(pork_candidate, grouped_candidates, "pork_top3", allow_majority_override=False)
        
        if can_accept and pork_rank <= 3 and pork_score >= 0.12:
            accepted_ingredients = ["Thịt lợn"]
            logger.info("[INGREDIENT ACCEPTED] Pork top3", {
                "score": pork_score,
                "rank": pork_rank,
            })
        elif not can_accept:
            log_rejection_once(
                f"special_reject:pork_top3:{reject_reason}",
                "[SPECIAL_ACCEPT_REJECTED] %s",
                {
                    "rule": "pork_top3",
                    "candidate": {"name": "Thịt lợn", "score": pork_score, "rank": pork_rank + 1},
                    "reason": reject_reason,
                    "groupedTop5": [{"name": c.get("name"), "score": c.get("score")} for c in grouped_candidates[:5]],
                }
            )

    if not accepted_ingredients and chicken_candidate:
        chicken_score = float(chicken_candidate.get("score", 0) or 0)
        chicken_rank = grouped_candidates.index(chicken_candidate)
        
        # Kiểm tra xem có candidate khác tốt hơn không
        best_candidate = grouped_candidates[0] if grouped_candidates else None
        best_name = best_candidate.get("name") if best_candidate else None
        best_score = float(best_candidate.get("score", 0) or 0) if best_candidate else 0
        
        # PHẦN 3: Chicken chỉ bị block bởi veg/fruit/tuber mạnh, KHÔNG bị block bởi meat/seafood khác
        top_names = [str(c.get("name") or "") for c in grouped_candidates[:5]]
        
        # Veg/fruit/tuber blockers that can actually block chicken
        veg_fruit_tuber_blockers = ["Cà rốt", "Cà chua", "Cam", "Khoai tây", "Khoai lang", "Bí đỏ", "Táo"]
        has_veg_blocker = any(name in top_names for name in veg_fruit_tuber_blockers)
        
        # Check if there's a strong veg/fruit/tuber blocker
        veg_blocker_candidate = None
        for name in veg_fruit_tuber_blockers:
            candidate = next((c for c in grouped_candidates if c.get("name") == name), None)
            if candidate:
                veg_blocker_candidate = candidate
                break
        
        veg_blocker_strong = False
        if veg_blocker_candidate:
            veg_blocker_score = float(veg_blocker_candidate.get("score", 0) or 0)
            veg_blocker_rank = grouped_candidates.index(veg_blocker_candidate)
            # Blocker is strong if in top 3 and score is close to chicken
            if veg_blocker_rank <= 2 and veg_blocker_score >= chicken_score - 0.05:
                veg_blocker_strong = True
        
        logger.info("[CHICKEN_BLOCKER_CHECK] %s", {
            "chickenCandidate": {"rank": chicken_rank + 1, "score": chicken_score},
            "blockerCandidate": veg_blocker_candidate,
            "blockerType": "veg_fruit_tuber" if veg_blocker_strong else "none",
            "decision": "blocked" if veg_blocker_strong else "not_blocked",
            "reason": "veg_fruit_tuber_blocker_strong" if veg_blocker_strong else "no_strong_blocker",
        })

        logger.info("[CHICKEN DEBUG] %s", {
            "rank": chicken_rank,
            "score": chicken_score,
            "candidate": chicken_candidate,
            "bestName": best_name,
            "bestScore": best_score,
            "hasVegBlocker": has_veg_blocker,
            "vegBlockerStrong": veg_blocker_strong,
            "topPrompts": top_prompts[:10],
            "groupedTop10": grouped_candidates[:10],
        })

        # Thắt chặt rule cho gà: chỉ accept nếu rank <= 2 và score >= 0.16
        # KHÔNG accept nếu:
        # - Có veg/fruit/tuber blocker mạnh
        # - Có candidate khác rõ hơn (score cao hơn >= 0.03)
        should_accept_chicken = False
        if chicken_rank <= 2 and chicken_score >= 0.16:
            # Block nếu có veg/fruit/tuber blocker mạnh
            if veg_blocker_strong:
                logger.info("[CHICKEN BLOCKED] Strong veg/fruit/tuber blocker in top 3: %s", veg_blocker_candidate.get("name"))
            elif best_name == "Thịt gà":
                should_accept_chicken = True
            elif best_score < chicken_score + 0.03:
                # Candidate khác không rõ hơn gà nhiều
                should_accept_chicken = True
        
        if should_accept_chicken:
            # Apply final safety check for chicken
            can_accept, reject_reason = can_accept_candidate(chicken_candidate, grouped_candidates, "chicken_guard", allow_majority_override=False)
            if can_accept:
                accepted_ingredients = ["Thịt gà"]
                logger.info("[INGREDIENT ACCEPTED] Chicken strict: %.3f", chicken_score)
            else:
                log_rejection_once(
                    f"special_reject:chicken_guard:{reject_reason}",
                    "[SPECIAL_ACCEPT_REJECTED] %s",
                    {
                        "rule": "chicken_guard",
                        "candidate": {"name": "Thịt gà", "score": chicken_score, "rank": chicken_rank + 1},
                        "reason": reject_reason,
                        "groupedTop5": [{"name": c.get("name"), "score": c.get("score")} for c in grouped_candidates[:5]],
                    }
                )
    
    # Nếu chưa có accepted_ingredients, chạy logic threshold cũ
    if not accepted_ingredients and grouped_candidates:
        best_candidate = grouped_candidates[0]
        best_score = float(best_candidate["score"])
        best_name = str(best_candidate["name"])
        
        # GUARD: Block Cá/Cua/Hải sản nếu có rau củ/quả trong top 3
        if best_name in ["Cá", "Cua", "Hải sản", "Tôm", "Sò", "Hàu"]:
            if has_blocking_veg_fruit_in_top3:
                logger.info("[INGREDIENT BLOCKED] Seafood blocked by vegetable/fruit in top3: %s", best_name)
                # Không accept, để fallback hoặc return empty
                best_candidate = None
                best_score = 0
                best_name = ""
        
        # Danh sách nguyên liệu phổ biến cần nhận diện tốt
        common_ingredients = {
            "Thịt gà", "Thịt bò", "Thịt lợn", "Trứng", "Cá", 
            "Tôm", "Cua", "Hàu", "Sò", "Hải sản",
            "Đậu hũ", "Rau cải", "Cà chua", "Nấm", "Cơm"
        }
        
        # PHẦN 2: Siết chặt meat/seafood accept trong fallback logic
        if best_name and best_score >= HIGH_CONFIDENCE_THRESHOLD:
            # Kiểm tra meat/seafood với threshold cao hơn
            if best_name in MEAT_FORCE_NAMES:
                # Tính margin
                second_score = float(grouped_candidates[1]["score"]) if len(grouped_candidates) > 1 else 0
                margin = best_score - second_score
                if best_score < MEAT_FORCE_MIN_SCORE or margin < FORCE_MIN_MARGIN:
                    log_rejection_once(
                        f"uncertain_result:meat_fallback:{best_name}",
                        "[UNCERTAIN_RESULT] %s",
                        {
                            "topCandidate": best_name,
                            "topScore": best_score,
                            "margin": margin,
                            "reason": f"meat score {best_score} < {MEAT_FORCE_MIN_SCORE} or margin {margin} < {FORCE_MIN_MARGIN}",
                        }
                    )
                    # Không accept, skip
                else:
                    accepted_ingredients = [best_name]
                    logger.info("[INGREDIENT ACCEPTED] High confidence meat: %s (%.3f, margin=%.3f)", best_name, best_score, margin)
            elif best_name in SEAFOOD_FORCE_NAMES:
                # Tính margin
                second_score = float(grouped_candidates[1]["score"]) if len(grouped_candidates) > 1 else 0
                margin = best_score - second_score
                if best_score < SEAFOOD_FORCE_MIN_SCORE or margin < FORCE_MIN_MARGIN:
                    log_rejection_once(
                        f"uncertain_result:seafood_fallback:{best_name}",
                        "[UNCERTAIN_RESULT] %s",
                        {
                            "topCandidate": best_name,
                            "topScore": best_score,
                            "margin": margin,
                            "reason": f"seafood score {best_score} < {SEAFOOD_FORCE_MIN_SCORE} or margin {margin} < {FORCE_MIN_MARGIN}",
                        }
                    )
                    # Không accept, skip
                else:
                    accepted_ingredients = [best_name]
                    logger.info("[INGREDIENT ACCEPTED] High confidence seafood: %s (%.3f, margin=%.3f)", best_name, best_score, margin)
            else:
                # Không phải meat/seafood, accept với threshold cũ
                accepted_ingredients = [best_name]
                logger.info("[INGREDIENT ACCEPTED] High confidence: %s (%.3f)", best_name, best_score)
        
        # Nhánh riêng cho gà với threshold thấp hơn
        elif best_name == "Thịt gà" and best_score >= 0.15:
            # Apply safety check for chicken relaxed threshold
            best_candidate_for_check = grouped_candidates[0]
            can_accept, reject_reason = can_accept_candidate(best_candidate_for_check, grouped_candidates, "chicken_relaxed_threshold")
            if can_accept:
                accepted_ingredients = [best_name]
                logger.info("[INGREDIENT ACCEPTED] Chicken relaxed threshold: %s (%.3f)", best_name, best_score)
            else:
                log_rejection_once(
                    f"special_reject:chicken_relaxed_threshold:{reject_reason}",
                    "[SPECIAL_ACCEPT_REJECTED] %s",
                    {
                        "rule": "chicken_relaxed_threshold",
                        "candidate": {"name": best_name, "score": best_score, "rank": 1},
                        "reason": reject_reason,
                        "groupedTop5": [{"name": c.get("name"), "score": c.get("score")} for c in grouped_candidates[:5]],
                    }
                )
        
        # Nếu score trung bình (0.17-0.25) và là nguyên liệu phổ biến
        elif best_name and best_score >= 0.17 and best_name in common_ingredients:
            accepted_ingredients = [best_name]
            logger.info("[INGREDIENT ACCEPTED] Medium confidence common: %s (%.3f)", best_name, best_score)
        
        # Nếu score trung bình và là hải sản, kiểm tra kỹ hơn
        elif best_name and best_score >= MEDIUM_CONFIDENCE_THRESHOLD:
            # Ưu tiên loại cụ thể hơn "Hải sản"
            if best_name == "Hải sản":
                # Kiểm tra xem có loại cụ thể nào trong top 5 không
                specific_seafood = {"Hàu", "Sò", "Cua", "Tôm", "Cá"}
                specific_candidates = [c for c in grouped_candidates[:5] if c["name"] in specific_seafood]
                if specific_candidates and specific_candidates[0]["score"] >= 0.15:
                    # Ưu tiên loại cụ thể
                    accepted_ingredients = [specific_candidates[0]["name"]]
                    logger.info("[INGREDIENT ACCEPTED] Specific seafood over generic: %s (%.3f)", 
                               specific_candidates[0]["name"], specific_candidates[0]["score"])
                else:
                    accepted_ingredients = [best_name]
                    logger.info("[INGREDIENT ACCEPTED] Generic seafood: %s (%.3f)", best_name, best_score)
            elif best_name in {"Hàu", "Sò", "Cua", "Tôm", "Cá"}:
                seafood_count = sum(1 for c in grouped_candidates[:3] if c["name"] in {"Hàu", "Sò", "Cua", "Tôm", "Hải sản", "Cá"})
                if seafood_count >= 2:
                    accepted_ingredients = [best_name]
                    logger.info("[INGREDIENT ACCEPTED] Seafood group: %s (%.3f)", best_name, best_score)
        
        # Nếu score thấp, thử fallback từ filename
        elif best_score < LOW_CONFIDENCE_THRESHOLD:
            fallback_ingredients = recognize_ingredient_from_filename(filename)
            if fallback_ingredients:
                accepted_ingredients = fallback_ingredients
                used_filename_fallback = True
                logger.info("[INGREDIENT ACCEPTED] Filename fallback: %s", fallback_ingredients)

    # Normalize output names
    normalized_accepted_ingredients = [normalize_ingredient_output_name(x) for x in accepted_ingredients]
    
    # PHẦN 6: Preserve accepted_reason after normalization
    # If normalization changed the name, the reason is still valid
    if normalized_accepted_ingredients != accepted_ingredients:
        logger.info("[INGREDIENT_NORMALIZED] %s -> %s, reason preserved: %s", 
                   accepted_ingredients, normalized_accepted_ingredients, accepted_reason)
    
    elapsed_time = time.time() - start_time
    logger.info("[INGREDIENT IMAGE RECOGNITION TIME] %.3f seconds", elapsed_time)

    # Log debug info chi tiết
    logger.info("[INGREDIENT IMAGE PORK CHICKEN DEBUG] %s", {
        "topPrompts": top_prompts[:10] if top_prompts else [],
        "groupedTop10": grouped_candidates[:10] if grouped_candidates else [],
        "milkCandidate": milk_candidate,
        "sausageCandidate": sausage_candidate,
        "porkCandidate": pork_candidate,
        "chickenCandidate": chicken_candidate,
        "beefCandidate": beef_candidate,
        "acceptedBeforeNormalize": accepted_ingredients,
        "acceptedAfterNormalize": normalized_accepted_ingredients,
        "forced": forced,
    })
    
    # Log potato/sweet potato/tomato guard debug info with detailed data
    if potato_candidate or sweet_potato_candidate:
        potato_top_prompt_count_log = sum(1 for p in top_prompts[:10] if str(p.get("ingredient", "")) == "Khoai tây")
        sweet_top_prompt_count_log = sum(1 for p in top_prompts[:10] if str(p.get("ingredient", "")) == "Khoai lang")
        
        logger.info("[POTATO_GUARD] Final decision %s", {
            "potato": {
                "rank": grouped_candidates.index(potato_candidate) + 1 if potato_candidate else None,
                "score": float(potato_candidate.get("score", 0) or 0) if potato_candidate else None,
            },
            "sweetPotato": {
                "rank": grouped_candidates.index(sweet_potato_candidate) + 1 if sweet_potato_candidate else None,
                "score": float(sweet_potato_candidate.get("score", 0) or 0) if sweet_potato_candidate else None,
            },
            "potatoScore": float(potato_candidate.get("score", 0) or 0) if potato_candidate else None,
            "sweetScore": float(sweet_potato_candidate.get("score", 0) or 0) if sweet_potato_candidate else None,
            "deltaPotatoMinusSweet": (
                float(potato_candidate.get("score", 0) or 0) - float(sweet_potato_candidate.get("score", 0) or 0)
                if potato_candidate and sweet_potato_candidate else None
            ),
            "potatoTopPromptCount": potato_top_prompt_count_log,
            "sweetTopPromptCount": sweet_top_prompt_count_log,
            "strongPotatoSignal": strong_potato_signal if 'strong_potato_signal' in locals() else None,
            "strongSweetSignal": strong_sweet_signal if 'strong_sweet_signal' in locals() else None,
            "decision": normalized_accepted_ingredients,
            "reason": "see guard analysis logs above for decision reason",
        })
    
    # Use normalized ingredients
    accepted_ingredients = normalized_accepted_ingredients

    # FINAL SAFETY GATE: Validate meat/seafood/sausage one last time before response
    # BUT respect majority override reasons
    if accepted_ingredients:
        accepted_name = accepted_ingredients[0]
        if accepted_name in (MEAT_NAMES | SEAFOOD_NAMES | SAUSAGE_NAMES):
            accepted_candidate = next((c for c in grouped_candidates if c.get("name") == accepted_name), None)
            if accepted_candidate:
                # Use the stored reason and majority info
                is_majority_accept = accepted_reason in {
                    "pork_prompt_majority",
                    "shrimp_prompt_majority",
                    "crab_prompt_majority",
                    "fish_prompt_majority",
                    "sausage_prompt_majority",
                    "beef_prompt_majority",
                    "chicken_prompt_majority",
                }
                
                # Use stored reason or fallback to generic gate
                safety_reason = accepted_reason if accepted_reason else "final_safety_gate"
                
                can_accept, reject_reason = can_accept_candidate(
                    accepted_candidate,
                    grouped_candidates,
                    safety_reason,
                    allow_majority_override=is_majority_accept,
                    majority_info=accepted_majority_info
                )
                
                # PHẦN 5: Log when majority accept is passed through final gate
                if can_accept and is_majority_accept:
                    accepted_score = float(accepted_candidate.get("score", 0) or 0)
                    logger.info("[FINAL_MAJORITY_ACCEPT_PASSED] %s", {
                        "accepted": accepted_name,
                        "acceptedReason": accepted_reason,
                        "acceptedScore": accepted_score,
                        "majority": accepted_majority_info,
                    })
                
                if not can_accept:
                    accepted_score = float(accepted_candidate.get("score", 0) or 0)
                    accepted_rank = grouped_candidates.index(accepted_candidate) + 1
                    log_rejection_once(
                        f"final_reject:{accepted_name}:{reject_reason}",
                        "[FINAL_ACCEPT_REJECTED] %s",
                        {
                            "accepted": accepted_name,
                            "candidate": {"name": accepted_name, "score": accepted_score, "rank": accepted_rank},
                            "reason": reject_reason,
                            "acceptedReason": accepted_reason,
                            "isMajorityAccept": is_majority_accept,
                            "majorityInfo": accepted_majority_info,
                            "groupedTop5": [{"name": c.get("name"), "score": c.get("score")} for c in grouped_candidates[:5]],
                        }
                    )
                    # Clear accepted_ingredients and return uncertain
                    accepted_ingredients = []
                    log_rejection_once(
                        f"uncertain_result:final_gate:{accepted_name}",
                        "[UNCERTAIN_RESULT] %s",
                        {
                            "reason": reject_reason,
                            "topCandidate": accepted_name,
                            "topScore": accepted_score,
                        }
                    )

    # Log debug info
    logger.info("[CLIP FORCE MATCH DEBUG] %s", {
        "topPrompts": top_prompts[:8] if top_prompts else [],
        "forced": forced,
        "groupedTop5": grouped_candidates[:5] if grouped_candidates else [],
    })

    if not accepted_ingredients:
        # Không nhận diện được - KHÔNG trả candidates để tránh gợi ý sai
        response = _ingredient_response(
            success=False,
            ingredients=[],
            candidates=[],
            message="Chưa nhận diện rõ nguyên liệu trong ảnh này. Bạn có thể nhập thủ công.",
            used_filename_fallback=used_filename_fallback,
        )
        _log_clip_debug(top_prompts, grouped_candidates, accepted_ingredients, used_filename_fallback)
        return response

    # Đã nhận diện được - truyền score thật vào candidates
    # PHẦN 5: Tìm score thật của accepted ingredient
    response_candidates = []
    for ingredient_name in accepted_ingredients:
        candidate = next((c for c in grouped_candidates if c.get("name") == ingredient_name), None)
        if candidate:
            response_candidates.append({
                "name": ingredient_name,
                "score": round(float(candidate.get("score", 0) or 0), 4)
            })

    response = _ingredient_response(
        success=True,
        ingredients=accepted_ingredients,
        candidates=response_candidates,
        message=f"Đã nhận diện nguyên liệu: {', '.join(accepted_ingredients)}",
        used_filename_fallback=used_filename_fallback,
    )
    _log_clip_debug(top_prompts, grouped_candidates, accepted_ingredients, used_filename_fallback)
    return response


def _load_image_bytes(
    image_bytes: bytes | None,
    image_url: str | None,
    pil_image_module,
) -> tuple[bytes, str, str | None, tuple[int, int] | None]:
    if image_bytes:
        resolved_bytes = bytes(image_bytes)
        image = pil_image_module.open(io.BytesIO(resolved_bytes))
        image.load()
        return resolved_bytes, "upload", image.mode, image.size

    if image_url:
        resolved_bytes = _download_image_bytes(image_url)
        image = pil_image_module.open(io.BytesIO(resolved_bytes))
        image.load()
        return resolved_bytes, "url", image.mode, image.size

    raise ValueError("Không có dữ liệu ảnh hợp lệ")


def _download_image_bytes(image_url: str) -> bytes:
    parsed = urlparse(str(image_url or ""))
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("URL ảnh không hợp lệ")

    request = Request(image_url, headers={"User-Agent": "NutriGain-CLIP/1.0"})
    with urlopen(request, timeout=15) as response:
        payload = response.read(MAX_IMAGE_DOWNLOAD_BYTES + 1)

    if len(payload) > MAX_IMAGE_DOWNLOAD_BYTES:
        raise ValueError("Ảnh tải về vượt quá giới hạn cho phép")
    return payload


def get_clip_model():
    global _model, _processor, _model_name, _model_device
    
    # Check if feature is enabled before loading model
    if not _is_ingredient_recognition_enabled():
        logger.info("[CLIP MODEL] Skipping model load - feature disabled via ENABLE_INGREDIENT_IMAGE_RECOGNITION=false")
        return None, None
    
    # Return cached model if already loaded
    if _model is not None and _processor is not None:
        logger.debug("[CLIP MODEL] Using cached model (device=%s, name=%s)", _model_device, _model_name)
        return _model, _processor

    with _model_lock:
        # Double-check after acquiring lock
        if _model is not None and _processor is not None:
            logger.debug("[CLIP MODEL] Using cached model after lock (device=%s, name=%s)", _model_device, _model_name)
            return _model, _processor

        logger.info("[CLIP ENABLED] Ingredient image recognition enabled")
        
        # Log cache configuration
        logger.info("[CLIP CACHE CONFIG] %s", {
            "HF_HOME": os.environ.get("HF_HOME"),
            "HUGGINGFACE_HUB_CACHE": os.environ.get("HUGGINGFACE_HUB_CACHE"),
            "HF_HUB_CACHE": os.environ.get("HF_HUB_CACHE"),
            "TRANSFORMERS_CACHE": os.environ.get("TRANSFORMERS_CACHE"),
            "TORCH_HOME": os.environ.get("TORCH_HOME"),
        })
        
        # Check if cache is still pointing to C drive (warning)
        hf_home = os.environ.get("HF_HOME", "")
        if hf_home.upper().startswith("C:") or hf_home.upper().startswith("C\\"):
            logger.warning("[CLIP CACHE WARNING] Hugging Face cache is still on C drive: %s", hf_home)
        
        model_name = _clip_model_name()
        try:
            import torch
            from transformers import CLIPModel, CLIPProcessor
        except ImportError as exc:
            error_msg = str(exc)
            if "torch" in error_msg.lower():
                logger.error(
                    "[CLIP UNAVAILABLE] PyTorch not installed. "
                    "Install with: pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu"
                )
            else:
                logger.error("[CLIP UNAVAILABLE] Missing dependency: %s", error_msg)
            _log_clip_model_status(
                loaded=False,
                model_name=model_name,
                error=f"dependency unavailable: {type(exc).__name__}: {exc}",
            )
            return None, None
        except Exception as exc:
            logger.warning("[CLIP UNAVAILABLE] %s", exc)
            _log_clip_model_status(
                loaded=False,
                model_name=model_name,
                error=f"import failed: {type(exc).__name__}: {exc}",
            )
            return None, None

        try:
            # Determine cache directory from environment variables
            cache_dir = os.environ.get("HUGGINGFACE_HUB_CACHE") or os.environ.get("HF_HOME")
            
            logger.info("[CLIP MODEL LOADING] model=%s cache_dir=%s (first time only)", model_name, cache_dir)
            
            # Load model and processor with explicit cache_dir
            _model = CLIPModel.from_pretrained(model_name, cache_dir=cache_dir)
            _processor = CLIPProcessor.from_pretrained(model_name, cache_dir=cache_dir)
            _model_device = "cuda" if torch.cuda.is_available() else "cpu"
            _model_name = model_name
            _model.to(_model_device)
        except Exception as exc:
            logger.warning("[CLIP MODEL LOAD ERROR] model=%s error=%s", model_name, exc)
            _log_clip_model_status(
                loaded=False,
                model_name=model_name,
                error=f"model load failed: {type(exc).__name__}: {exc}",
            )
            _model = None
            _processor = None
            _model_name = None
            _model_device = None
            return None, None
        _model.eval()
        _log_clip_model_status(loaded=True, device=_model_device, model_name=_model_name)
        logger.info("[CLIP MODEL LOADED] Model cached for subsequent requests")
        return _model, _processor


def _score_image_against_prompt_groups(image, model, processor) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    import torch

    device = next(model.parameters()).device
    image_inputs = processor(images=image, return_tensors="pt").to(device)
    text_features, prompt_meta = get_text_features(model, processor)

    with torch.no_grad():
        image_features = _clip_feature_tensor(model.get_image_features(**image_inputs), "image")
        image_features = image_features / image_features.norm(dim=-1, keepdim=True)
        scores = (image_features @ text_features.T)[0]

    grouped: dict[str, list[dict[str, Any]]] = {}
    top_prompts: list[dict[str, Any]] = []
    for idx, score in enumerate(scores):
        ingredient, prompt = prompt_meta[int(idx)]
        value = float(score.item())
        grouped.setdefault(ingredient, []).append({"prompt": prompt, "score": value})
        top_prompts.append({"ingredient": ingredient, "prompt": prompt, "score": round(value, 4)})

    grouped_candidates: list[dict[str, Any]] = []
    for ingredient, prompt_scores in grouped.items():
        prompt_scores.sort(key=lambda item: item["score"], reverse=True)
        # Kết hợp max score và mean top 3 để không bị kéo tụt bởi các prompt yếu
        best_score = prompt_scores[0]["score"]
        mean_top3 = statistics.mean(item["score"] for item in prompt_scores[:3])
        final_score = (best_score * 0.85) + (mean_top3 * 0.15)
        grouped_candidates.append(
            {
                "name": ingredient,
                "score": round(float(final_score), 4),
                "topPrompts": prompt_scores[:3],
            }
        )

    grouped_candidates.sort(key=lambda item: item["score"], reverse=True)
    top_prompts.sort(key=lambda item: item["score"], reverse=True)
    return grouped_candidates, top_prompts[:10]


def get_text_features(model, processor):
    global _text_features, _prompt_meta, _text_features_version
    if (
        _text_features is not None
        and _prompt_meta is not None
        and _text_features_version == PROMPT_FEATURE_VERSION
    ):
        return _text_features, _prompt_meta

    import torch

    prompts: list[str] = []
    prompt_meta: list[tuple[str, str]] = []
    templates = [
        "{}",
        "a photo of {}",
        "a close-up photo of {}",
        "a food ingredient photo of {}",
        "a raw ingredient photo of {}",
    ]
    for ingredient, ingredient_prompts in INGREDIENT_PROMPT_GROUPS.items():
        for prompt in ingredient_prompts:
            for template in templates:
                text = template.format(prompt)
                prompts.append(text)
                prompt_meta.append((ingredient, text))

    device = next(model.parameters()).device
    inputs = processor(text=prompts, return_tensors="pt", padding=True, truncation=True).to(device)
    with torch.no_grad():
        text_features = _clip_feature_tensor(model.get_text_features(**inputs), "text")
        text_features = text_features / text_features.norm(dim=-1, keepdim=True)

    _text_features = text_features
    _prompt_meta = prompt_meta
    _text_features_version = PROMPT_FEATURE_VERSION
    
    logger.info("[CLIP TEXT PROMPTS BUILT] %s", {
        "version": PROMPT_FEATURE_VERSION,
        "promptCount": len(prompts),
        "hasChickenPhotoPrompt": any("raw whole chicken" in prompt.lower() for prompt in prompts),
    })
    
    return _text_features, _prompt_meta


def recognize_ingredient_from_filename(filename: str | None) -> list[str]:
    normalized = normalize_filename(filename)
    if not normalized:
        return []

    found: list[str] = []
    for ingredient, patterns in FILENAME_INGREDIENT_PATTERNS:
        if any(phrase_in_text(pattern, normalized) for pattern in patterns):
            if ingredient not in found:
                found.append(ingredient)
    return _unique_ingredients(found)


def _filename_fallback_response(
    filename: str | None,
    fallback_reason: str,
    original_error: Exception | None = None,
) -> dict[str, Any]:
    fallback_ingredients = recognize_ingredient_from_filename(filename)
    logger.info(
        "[CLIP FILENAME FALLBACK] %s",
        {
            "acceptedIngredients": fallback_ingredients,
            "usedFilenameFallback": bool(fallback_ingredients),
            "fallbackReason": fallback_reason,
            "fallbackError": type(original_error).__name__ if original_error else None,
        },
    )
    if fallback_ingredients:
        return _ingredient_response(
            success=True,
            ingredients=fallback_ingredients,
            candidates=[{"name": item, "score": LOW_CONFIDENCE_THRESHOLD} for item in fallback_ingredients],
            message=f"Đã nhận diện tạm theo tên file: {', '.join(fallback_ingredients)}",
            used_filename_fallback=True,
        )
    return _ingredient_response(
        success=False,
        ingredients=[],
        candidates=[],
        message=FAIL_MESSAGE,
        used_filename_fallback=False,
    )


def normalize_filename(value: str | None) -> str:
    text = os.path.basename(str(value or ""))
    text = re.sub(r"\.[a-z0-9]+$", " ", text, flags=re.IGNORECASE)
    text = strip_accents(text).lower()
    text = re.sub(r"[_\-.]+", " ", text)
    text = re.sub(r"[^a-z0-9\s]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def phrase_in_text(phrase: str, text: str) -> bool:
    normalized_phrase = normalize_filename(phrase)
    if not normalized_phrase:
        return False
    return re.search(rf"(^|\s){re.escape(normalized_phrase)}($|\s)", text) is not None


def strip_accents(value: object) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    return "".join(char for char in text if unicodedata.category(char) != "Mn").replace("đ", "d").replace("Đ", "D")


def _unique_ingredients(values: list[str]) -> list[str]:
    ingredients: list[str] = []
    seen: set[str] = set()

    for value in values:
        cleaned = str(value or "").strip()
        if not cleaned:
            continue
        key = normalize_filename(cleaned)
        if not key or key in seen:
            continue
        seen.add(key)
        ingredients.append(cleaned)

    return ingredients


def _dedupe_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for candidate in candidates:
        name = str(candidate.get("name", "")).strip()
        if not name:
            continue
        key = normalize_filename(name)
        if key in seen:
            continue
        seen.add(key)
        deduped.append({"name": name, "score": round(float(candidate.get("score", 0.0)), 4)})
    return deduped


def _log_clip_debug(top_prompts, grouped_candidates, accepted_ingredients, used_filename_fallback) -> None:
    logger.info(
        "[CLIP INGREDIENT SCORES DEBUG] %s",
        {
            "topPrompts": top_prompts,
            "groupedCandidates": grouped_candidates[:5],
            "acceptedIngredients": accepted_ingredients,
            "usedFilenameFallback": bool(used_filename_fallback),
        },
    )


def _ingredient_response(
    success: bool,
    ingredients: list[str],
    candidates: list[dict[str, Any]],
    message: str,
    used_filename_fallback: bool,
) -> dict[str, Any]:
    safe_ingredients = [item for item in _unique_ingredients(ingredients) if item in VALID_INGREDIENTS]
    safe_candidates = _dedupe_candidates(candidates)[:5]
    
    # PHẦN 5: Confidence phải là score thật, không phải 1.0
    confidence_value = 0.0
    if safe_candidates:
        confidence_value = round(float(safe_candidates[0]["score"]), 4)
    elif success and safe_ingredients:
        # Nếu có ingredients nhưng không có candidates, vẫn không set 1.0
        # Tìm score thật từ grouped_candidates nếu có
        confidence_value = 0.0
    
    response = {
        "success": bool(success and safe_ingredients),
        "ingredients": safe_ingredients,
        "candidates": safe_candidates,
        "confidence": confidence_value,
        "method": "clip",
        "usedFilenameFallback": bool(used_filename_fallback),
        "message": message if (success and safe_ingredients) else (message or FAIL_MESSAGE),
    }
    logger.info("[INGREDIENT RECOGNITION RESULT] %s", response)
    return response


def clip_threshold() -> float:
    return LOW_CONFIDENCE_THRESHOLD


def _get_smart_fallback_candidates(grouped_candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Trả về candidates thông minh dựa trên top scores"""
    if not grouped_candidates:
        # Không trả mặc định seafood nữa - trả rỗng
        return []
    
    return grouped_candidates[:5]


def has_strong_potato_signal(top_prompts: list[dict[str, Any]], grouped_candidates: list[dict[str, Any]] | None = None) -> bool:
    """Phát hiện tín hiệu khoai tây rõ ràng từ top prompts hoặc candidates"""
    # Kiểm tra top prompts có chứa từ khoá khoai tây mạnh
    text_parts = []
    for item in (top_prompts or [])[:20]:
        prompt = str(item.get("text") or item.get("prompt") or item.get("label") or item or "")
        text_parts.append(prompt)
    
    combined_text = strip_accents(" ".join(text_parts)).lower()
    
    # Các từ khoá potato không có "sweet"
    potato_terms = [
        "potato",
        "potatoes",
        "raw potato",
        "raw potatoes",
        "fresh potato",
        "fresh potatoes",
        "yellow potato",
        "yellow potatoes",
        "white potato",
        "white potatoes",
        "brown potato",
        "brown potatoes",
        "round potatoes",
        "oval potatoes",
        "small round potatoes",
        "pile of potatoes",
        "unpeeled potatoes",
        "potato tubers",
        "khoai tay",
        "cu khoai tay",
        "khoai tay vang",
        "khoai tay trang",
        "khoai tay song",
        "nhieu cu khoai tay",
    ]
    
    # Các từ khoá sweet potato
    sweet_terms = [
        "sweet potato",
        "sweet potatoes",
        "khoai lang",
        "purple sweet potato",
        "red skin sweet potato",
        "orange sweet potato",
        "yellow flesh sweet potato",
        "orange flesh sweet potato",
        "long sweet potato",
    ]
    
    # Đếm số lượng prompts cho mỗi loại trong top 10
    potato_count = 0
    sweet_count = 0
    potato_score_sum = 0.0
    sweet_score_sum = 0.0
    
    for idx, item in enumerate(top_prompts[:10] if top_prompts else []):
        prompt = strip_accents(str(item.get("prompt", ""))).lower()
        score = float(item.get("score", 0) or 0)
        
        is_sweet = any(strip_accents(term).lower() in prompt for term in sweet_terms)
        is_potato = any(strip_accents(term).lower() in prompt for term in potato_terms)
        
        if is_sweet:
            sweet_count += 1
            sweet_score_sum += score
        elif is_potato:  # Only count as potato if NOT sweet
            potato_count += 1
            potato_score_sum += score
    
    # Nếu có nhiều sweet potato prompts hơn và điểm tổng cũng cao hơn, không tính là potato signal
    if sweet_count >= potato_count and sweet_score_sum >= potato_score_sum:
        return False
    
    # Nếu có potato prompts và không bị sweet potato vượt, tính là có potato signal
    if potato_count >= 3 and potato_score_sum >= 0.7:
        return True
    
    # Kiểm tra Khoai tây candidate mạnh
    if grouped_candidates:
        potato_candidate = None
        sweet_potato_candidate = None
        
        for c in grouped_candidates:
            if c.get("name") == "Khoai tây":
                potato_candidate = c
            elif c.get("name") == "Khoai lang":
                sweet_potato_candidate = c
        
        if potato_candidate:
            potato_score = float(potato_candidate.get("score", 0) or 0)
            potato_rank = grouped_candidates.index(potato_candidate) + 1
            
            if potato_rank <= 3 and potato_score >= 0.25:
                # Chỉ return True nếu không có sweet potato vượt rõ
                if not sweet_potato_candidate:
                    return True
                sweet_potato_score = float(sweet_potato_candidate.get("score", 0) or 0)
                if potato_score >= sweet_potato_score - 0.02:
                    return True
    
    return False


def has_strong_sweet_potato_signal(top_prompts: list[dict[str, Any]], grouped_candidates: list[dict[str, Any]] | None = None) -> bool:
    """Phát hiện tín hiệu khoai lang rõ ràng từ top prompts hoặc candidates"""
    # 1. Đếm top prompt theo ingredient label
    sweet_prompt_count = 0
    potato_prompt_count = 0
    sweet_prompt_score_sum = 0.0
    potato_prompt_score_sum = 0.0
    
    for p in (top_prompts or [])[:10]:
        ingredient = str(p.get("ingredient", ""))
        score = float(p.get("score", 0) or 0)
        
        if ingredient == "Khoai lang":
            sweet_prompt_count += 1
            sweet_prompt_score_sum += score
        elif ingredient == "Khoai tây":
            potato_prompt_count += 1
            potato_prompt_score_sum += score
    
    # Nếu top prompts đa số là Khoai tây và không có prompt Khoai lang, chắc chắn không có strong sweet signal
    if potato_prompt_count >= 3 and sweet_prompt_count == 0:
        return False
    
    # Nếu Khoai tây prompt áp đảo Khoai lang, không strong sweet
    if potato_prompt_count > sweet_prompt_count and potato_prompt_score_sum >= sweet_prompt_score_sum:
        return False
    
    # 2. Text strong terms chỉ tính trên prompt có ingredient == Khoai lang
    sweet_text_parts = []
    for item in (top_prompts or [])[:20]:
        ingredient = str(item.get("ingredient", ""))
        if ingredient == "Khoai lang":
            prompt = str(item.get("text") or item.get("prompt") or item.get("label") or item or "")
            sweet_text_parts.append(prompt)
    
    sweet_combined_text = strip_accents(" ".join(sweet_text_parts)).lower()
    
    strong_terms = [
        "sweet potato",
        "sweet potatoes", 
        "raw sweet potato",
        "purple sweet potato",
        "red skin sweet potato",
        "orange sweet potato",
        "yellow flesh sweet potato",
        "orange flesh sweet potato",
        "japanese sweet potato",
        "long sweet potato",
        "sweet potato tubers",
        "khoai lang",
        "khoai lang tim",
        "khoai lang do",
        "khoai lang ruot vang",
        "khoai lang ruot cam",
        "khoai lang cat doi",
    ]
    
    has_strong_text = False
    for term in strong_terms:
        normalized_term = strip_accents(term).lower()
        if normalized_term in sweet_combined_text:
            has_strong_text = True
            break
    
    if has_strong_text and sweet_prompt_count >= 2:
        return True
    
    # 3. Candidate rank/score chỉ được dùng khi không bị Khoai tây áp đảo
    if grouped_candidates:
        sweet_potato_candidate = None
        potato_candidate = None
        
        for c in grouped_candidates:
            if c.get("name") == "Khoai lang":
                sweet_potato_candidate = c
            elif c.get("name") == "Khoai tây":
                potato_candidate = c
        
        if sweet_potato_candidate:
            sp_score = float(sweet_potato_candidate.get("score", 0) or 0)
            sp_rank = grouped_candidates.index(sweet_potato_candidate)
            p_score = float(potato_candidate.get("score", 0) or 0) if potato_candidate else 0
            
            # Khoai lang chỉ strong nếu:
            # - rank <= 2
            # - score >= 0.30
            # - và không thua Khoai tây quá 0.015
            if sp_rank <= 2 and sp_score >= 0.30:
                if not potato_candidate or sp_score >= p_score - 0.015:
                    return True
    
    return False


def _force_accept_from_top_prompts(
    top_prompts: list[dict[str, Any]], 
    grouped_candidates: list[dict[str, Any]],
    log_rejection_once_fn: Any = None
) -> str | None:
    """Kiểm tra xem có match mạnh từ top prompts không"""
    
    # Default no-op logger if not provided
    if log_rejection_once_fn is None:
        def log_rejection_once_fn(key: str, message: str, payload: dict[str, Any]) -> None:
            logger.info(message, payload)
    
    # PHẦN 5: Đảm bảo thứ tự kiểm tra sweet potato trước potato
    force_rules = {
        "Sữa": ["milk", "fresh milk", "cow milk", "glass of milk", "milk in a glass", "pouring milk", "white milk", "bottle of milk", "cup of milk"],
        "Xúc xích": ["sausage", "sausages", "hot dog", "hotdog", "frankfurter", "wiener", "sausage skewers", "processed sausage", "red sausage"],
        "Khoai lang": ["sweet potato", "sweet potatoes", "raw sweet potato", "purple sweet potato", "red skin sweet potato", "orange sweet potato", "yellow flesh sweet potato", "orange flesh sweet potato", "japanese sweet potato", "long sweet potato"],  # MUST check before potato!
        "Thịt lợn": ["pork", "raw pork", "pork meat", "fresh pork", "pork slices", "raw pork slices"],
        "Thịt gà": ["chicken", "raw chicken", "whole chicken", "poultry", "hen", "rooster", "chicken meat", "fresh chicken"],
        "Hàu": ["oyster", "oysters", "raw oysters", "fresh oysters"],
        "Thịt bò": ["beef", "raw beef", "beef steak", "red meat beef"],
        "Trứng": ["egg", "eggs", "chicken egg"],
        "Tôm": ["shrimp", "prawn", "prawns"],
        "Cua": ["crab", "fresh crab", "live crab"],
        "Cá": ["fish", "fresh fish", "fish fillet"],
        "Cà rốt": ["carrot", "carrots", "fresh carrot"],
        "Cà chua": ["tomato", "tomatoes", "fresh tomato"],
        "Cam": ["orange fruit", "fresh orange"],
        "Khoai tây": ["potato", "potatoes", "raw potato", "fresh potato", "yellow potato", "white potato", "brown potato", "round potatoes", "oval potatoes"],  # Check after sweet potato
    }
    
    # PHẦN 3: Không force seafood nếu có rau củ/quả trong top 5
    blocking_veg_fruit = ["Cà rốt", "Cà chua", "Cam", "Khoai lang", "Bí đỏ"]
    seafood_ingredients = ["Cá", "Cua", "Hải sản", "Tôm", "Sò", "Hàu"]
    
    # Tìm best veg/fruit trong top 5
    best_veg_fruit = None
    best_veg_fruit_score = 0.0
    for c in grouped_candidates[:5]:
        if c.get("name") in blocking_veg_fruit:
            score = float(c.get("score", 0) or 0)
            if score > best_veg_fruit_score:
                best_veg_fruit = c.get("name")
                best_veg_fruit_score = score
    
    # Kiểm tra sweet potato signal để tránh force Khoai tây sai
    strong_sweet_signal = has_strong_sweet_potato_signal(top_prompts, grouped_candidates)
    strong_potato_signal = has_strong_potato_signal(top_prompts, grouped_candidates)
    
    # Kiểm tra milk words để tránh nhận sai thành gà
    milk_words = ["milk", "glass of milk", "pouring milk", "cow milk", "fresh milk", "white milk", "cup of milk", "bottle of milk"]
    has_milk_signal = False
    
    # Kiểm tra sausage words để tránh nhận sai thành gà
    sausage_words = ["sausage", "sausages", "hot dog", "hotdog", "frankfurter", "wiener"]
    has_sausage_signal = False
    
    for item in top_prompts[:5]:
        prompt = str(item.get("prompt", "")).lower()
        if any(word in prompt for word in milk_words):
            has_milk_signal = True
        if any(word in prompt for word in sausage_words):
            has_sausage_signal = True
    
    # PHẦN 5: Kiểm tra Khoai lang trước khi xử lý Khoai tây
    # Đếm prompt counts trước
    sweet_prompt_count = sum(1 for item in top_prompts[:10] if str(item.get("ingredient", "")) == "Khoai lang")
    potato_prompt_count = sum(1 for item in top_prompts[:10] if str(item.get("ingredient", "")) == "Khoai tây")
    
    # PHẦN 3: Tính rank và score cho potato/sweet potato để guard
    potato_candidate = next((c for c in grouped_candidates if c.get("name") == "Khoai tây"), None)
    sweet_potato_candidate = next((c for c in grouped_candidates if c.get("name") == "Khoai lang"), None)
    potato_rank = grouped_candidates.index(potato_candidate) + 1 if potato_candidate else 999
    sweet_potato_rank = grouped_candidates.index(sweet_potato_candidate) + 1 if sweet_potato_candidate else 999
    
    for idx, item in enumerate(top_prompts[:8]):
        ingredient = str(item.get("ingredient", "")).strip()
        prompt = str(item.get("prompt", "")).lower()
        score = float(item.get("score", 0) or 0)
        
        # Ưu tiên Khoai lang với strong signal
        # CHỈ force nếu trong top 3, score cao, có >= 2 sweet prompts và không bị potato áp đảo
        if ingredient == "Khoai lang":
            if idx <= 2 and score >= 0.30 and sweet_prompt_count >= 2:
                # Không force nếu Khoai tây áp đảo
                if not (potato_prompt_count >= 3 and potato_prompt_count > sweet_prompt_count):
                    words = force_rules.get("Khoai lang", [])
                    if any(word in prompt for word in words):
                        logger.info("[FORCE ACCEPT] Sweet potato from top prompt: %.3f (count=%d)", score, sweet_prompt_count)
                        return "Khoai lang"
    
    for item in top_prompts[:8]:
        ingredient = str(item.get("ingredient", "")).strip()
        prompt = str(item.get("prompt", "")).lower()
        score = float(item.get("score", 0) or 0)
        
        # Ưu tiên Sữa với threshold thấp hơn
        if ingredient == "Sữa" and score >= 0.16:
            words = force_rules.get("Sữa", [])
            if any(word in prompt for word in words):
                logger.info("[FORCE ACCEPT] Milk from top prompt: %.3f", score)
                return "Sữa"
        
        # Ưu tiên Xúc xích với threshold thấp
        if ingredient == "Xúc xích" and score >= 0.13:
            words = force_rules.get("Xúc xích", [])
            if any(word in prompt for word in words):
                logger.info("[FORCE ACCEPT] Sausage from top prompt: %.3f", score)
                return "Xúc xích"
        
        # Ưu tiên rau củ/quả
        if ingredient in blocking_veg_fruit and score >= 0.27:
            words = force_rules.get(ingredient, [])
            if any(word in prompt for word in words):
                logger.info("[FORCE ACCEPT] Vegetable/Fruit from top prompt: %s %.3f", ingredient, score)
                return ingredient
        
        # Không force accept Thịt gà nếu có dấu hiệu sữa hoặc xúc xích
        if ingredient == "Thịt gà" and (has_milk_signal or has_sausage_signal):
            logger.info("[FORCE REJECT] Chicken blocked by milk/sausage signal")
            continue
        
        # PHẦN 3: FORCE Khoai tây chỉ khi có tín hiệu potato rõ VÀ rank <= 5 VÀ prompt count >= 2
        if ingredient == "Khoai tây":
            # Guard: không cho phép force Khoai tây khi rank quá thấp
            if potato_rank > 5 and potato_prompt_count < 2:
                log_rejection_once_fn(
                    "potato_guard_skip:force_accept_rank_low",
                    "[POTATO_GUARD_SKIPPED] %s",
                    {
                        "reason": "potato_rank_too_low_no_prompt_evidence",
                        "potatoRank": potato_rank,
                        "potatoScore": potato_candidate.get("score", 0) if potato_candidate else 0,
                        "potatoTopPromptCount": potato_prompt_count,
                        "currentTopCandidate": grouped_candidates[0].get("name") if grouped_candidates else None,
                    }
                )
                continue
            
            if strong_sweet_signal:
                logger.info("[FORCE REJECT] Potato blocked by strong sweet potato signal")
                continue
            elif strong_potato_signal and score >= 0.18:
                words = force_rules.get("Khoai tây", [])
                if any(word in prompt for word in words):
                    logger.info("[FORCE ACCEPT] Potato from top prompt due to strong potato signal: %.3f", score)
                    return "Khoai tây"
            else:
                # Không force potato nếu không có strong potato signal
                continue
        
        # KHÔNG force seafood nếu có rau củ/quả trong top 5 với score gần bằng
        if ingredient in seafood_ingredients and best_veg_fruit and best_veg_fruit_score >= score - 0.08:
            logger.info("[FORCE REJECT] Seafood %s blocked by vegetable/fruit %s (%.3f vs %.3f)", 
                       ingredient, best_veg_fruit, score, best_veg_fruit_score)
            continue
        
        # PHẦN 1: Siết chặt meat/seafood forcing với score và margin thresholds
        if ingredient in MEAT_FORCE_NAMES or ingredient in SEAFOOD_FORCE_NAMES:
            # Tìm candidate của ingredient này
            candidate = next((c for c in grouped_candidates if c.get("name") == ingredient), None)
            if not candidate:
                continue
            
            forced_score = float(candidate.get("score", 0) or 0)
            candidate_rank = grouped_candidates.index(candidate)
            
            # Tìm second best candidate để tính margin
            second_candidate = grouped_candidates[1] if len(grouped_candidates) > 1 and candidate_rank == 0 else grouped_candidates[0]
            second_score = float(second_candidate.get("score", 0) or 0)
            margin = forced_score - second_score if candidate_rank == 0 else 0
            
            # Check meat threshold
            if ingredient in MEAT_FORCE_NAMES:
                if forced_score < MEAT_FORCE_MIN_SCORE or margin < FORCE_MIN_MARGIN:
                    log_rejection_once_fn(
                        f"force_reject:meat:{ingredient}",
                        "[FORCE_REJECT_LOW_CONFIDENCE] %s",
                        {
                            "ingredient": ingredient,
                            "ingredientGroup": "meat",
                            "forcedScore": forced_score,
                            "secondScore": second_score,
                            "margin": margin,
                            "minScore": MEAT_FORCE_MIN_SCORE,
                            "minMargin": FORCE_MIN_MARGIN,
                            "reason": f"score {forced_score} < {MEAT_FORCE_MIN_SCORE} or margin {margin} < {FORCE_MIN_MARGIN}",
                        }
                    )
                    continue
            
            # Check seafood threshold
            if ingredient in SEAFOOD_FORCE_NAMES:
                if forced_score < SEAFOOD_FORCE_MIN_SCORE or margin < FORCE_MIN_MARGIN:
                    log_rejection_once_fn(
                        f"force_reject:seafood:{ingredient}",
                        "[FORCE_REJECT_LOW_CONFIDENCE] %s",
                        {
                            "ingredient": ingredient,
                            "ingredientGroup": "seafood",
                            "forcedScore": forced_score,
                            "secondScore": second_score,
                            "margin": margin,
                            "minScore": SEAFOOD_FORCE_MIN_SCORE,
                            "minMargin": FORCE_MIN_MARGIN,
                            "reason": f"score {forced_score} < {SEAFOOD_FORCE_MIN_SCORE} or margin {margin} < {FORCE_MIN_MARGIN}",
                        }
                    )
                    continue
        
        if ingredient in force_rules and score >= 0.18:
            words = force_rules[ingredient]
            if any(word in prompt for word in words):
                return ingredient
    return None


def _get_smart_message(candidates: list[dict[str, Any]]) -> str:
    """Trả về message phù hợp dựa trên candidates"""
    if not candidates:
        return FAIL_MESSAGE
    
    seafood_ingredients = {"Hàu", "Sò", "Cua", "Tôm", "Hải sản", "Cá"}
    top_candidate = candidates[0].get("name", "")
    
    # Đếm số lượng hải sản trong top 3
    seafood_count = sum(1 for c in candidates[:3] if c.get("name") in seafood_ingredients)
    
    if top_candidate in seafood_ingredients or seafood_count >= 2:
        return "Có thể đây là hải sản. Hãy chọn nguyên liệu phù hợp."
    
    return LOW_CONFIDENCE_MESSAGE



def warmup_clip_model() -> None:
    """Warm up CLIP model on startup to avoid timeout on first request"""
    if not _is_ingredient_recognition_enabled():
        logger.info("[CLIP WARMUP SKIPPED] Feature disabled via ENABLE_INGREDIENT_IMAGE_RECOGNITION=false")
        return
    
    try:
        logger.info("[CLIP WARMUP START]")
        model, processor = get_clip_model()
        if model is None or processor is None:
            logger.warning("[CLIP WARMUP SKIPPED] model unavailable")
            return
        
        # Build text features to cache prompts
        get_text_features(model, processor)
        logger.info("[CLIP WARMUP DONE]")
    except Exception as exc:
        logger.exception("[CLIP WARMUP ERROR] %s", exc)
