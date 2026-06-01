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
        "cà chua",
        "ca chua",
        "quả cà chua",
        "qua ca chua",
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
        "boiled sweet potato",
        "purple sweet potato",
        "roasted sweet potato",
        "khoai lang",
    ],
    "Khoai tây": [
        "potato",
        "potatoes",
        "boiled potato",
        "raw potato",
        "potato pieces",
        "khoai tây",
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
    ("Khoai lang", ["khoai lang", "sweet potato"]),
    ("Khoai tây", ["khoai tay", "potato"]),
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
    forced = _force_accept_from_top_prompts(top_prompts, grouped_candidates)
    if forced:
        accepted_ingredients = [forced]
        logger.info("[INGREDIENT FORCE ACCEPTED FROM TOP PROMPT] %s", forced)

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
        
        # Accept Sữa nếu trong top 3 với score >= 0.14
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
        
        # Accept Xúc xích nếu trong top 3 với score >= 0.12
        if sausage_rank <= 3 and sausage_score >= 0.12:
            accepted_ingredients = ["Xúc xích"]
            logger.info("[INGREDIENT ACCEPTED] Sausage top3: %.3f", sausage_score)

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
    pumpkin_candidate = next(
        (c for c in grouped_candidates if c.get("name") == "Bí đỏ"),
        None,
    )

    # Accept Cà rốt nếu trong top 3 với score >= 0.28
    if not accepted_ingredients and carrot_candidate:
        carrot_score = float(carrot_candidate.get("score", 0) or 0)
        carrot_rank = grouped_candidates.index(carrot_candidate)
        if carrot_rank <= 3 and carrot_score >= 0.28:
            accepted_ingredients = ["Cà rốt"]
            logger.info("[INGREDIENT ACCEPTED] Carrot high confidence: %.3f", carrot_score)

    # Accept Cà chua nếu trong top 3 với score >= 0.27
    if not accepted_ingredients and tomato_candidate:
        tomato_score = float(tomato_candidate.get("score", 0) or 0)
        tomato_rank = grouped_candidates.index(tomato_candidate)
        if tomato_rank <= 3 and tomato_score >= 0.27:
            accepted_ingredients = ["Cà chua"]
            logger.info("[INGREDIENT ACCEPTED] Tomato high confidence: %.3f", tomato_score)

    # Accept Cam nếu trong top 3 với score >= 0.27
    if not accepted_ingredients and orange_candidate:
        orange_score = float(orange_candidate.get("score", 0) or 0)
        orange_rank = grouped_candidates.index(orange_candidate)
        if orange_rank <= 3 and orange_score >= 0.27:
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
        
        # Tìm best seafood candidate
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
        
        if pork_rank <= 5 and pork_score >= chicken_score - 0.03:
            accepted_ingredients = ["Thịt lợn"]
            logger.info("[INGREDIENT ACCEPTED] Pork over chicken guard", {
                "pork_score": pork_score,
                "chicken_score": chicken_score,
                "pork_rank": pork_rank,
            })

    # Relaxed rule for pork - accept if in top 3 with score >= 0.12
    if not accepted_ingredients and pork_candidate:
        pork_score = float(pork_candidate.get("score", 0) or 0)
        pork_rank = grouped_candidates.index(pork_candidate)
        
        if pork_rank <= 3 and pork_score >= 0.12:
            accepted_ingredients = ["Thịt lợn"]
            logger.info("[INGREDIENT ACCEPTED] Pork top3", {
                "score": pork_score,
                "rank": pork_rank,
            })

    if not accepted_ingredients and chicken_candidate:
        chicken_score = float(chicken_candidate.get("score", 0) or 0)
        chicken_rank = grouped_candidates.index(chicken_candidate)
        
        # Kiểm tra xem có candidate khác tốt hơn không
        best_candidate = grouped_candidates[0] if grouped_candidates else None
        best_name = best_candidate.get("name") if best_candidate else None
        best_score = float(best_candidate.get("score", 0) or 0) if best_candidate else 0
        
        # Kiểm tra top 5 có các nguyên liệu khác không
        top_names = [str(c.get("name") or "") for c in grouped_candidates[:5]]
        blocking_ingredients = ["Thịt lợn", "Thịt heo", "Thịt bò", "Xúc xích", "Sữa", "Cam", "Cà chua"]
        has_blocking_ingredient = any(name in top_names for name in blocking_ingredients)
        
        # Kiểm tra top prompts có từ sausage không
        sausage_words = ["sausage", "sausages", "hot dog", "hotdog", "frankfurter", "wiener"]
        top_prompt_text = " ".join(str(p.get("prompt", "")).lower() for p in top_prompts[:10])
        has_sausage_in_prompts = any(word in top_prompt_text for word in sausage_words)

        logger.info("[CHICKEN DEBUG] %s", {
            "rank": chicken_rank,
            "score": chicken_score,
            "candidate": chicken_candidate,
            "bestName": best_name,
            "bestScore": best_score,
            "hasBlockingIngredient": has_blocking_ingredient,
            "hasSausageInPrompts": has_sausage_in_prompts,
            "topPrompts": top_prompts[:10],
            "groupedTop10": grouped_candidates[:10],
        })

        # Thắt chặt rule cho gà: chỉ accept nếu rank <= 2 và score >= 0.16
        # KHÔNG accept nếu:
        # - Có pork/beef/sausage/milk/orange/tomato trong top 5
        # - Có candidate khác rõ hơn (score cao hơn >= 0.03)
        # - Có từ sausage trong top prompts
        should_accept_chicken = False
        if chicken_rank <= 2 and chicken_score >= 0.16:
            # Block nếu có blocking ingredient
            if has_blocking_ingredient:
                logger.info("[CHICKEN BLOCKED] Blocking ingredient in top 5: %s", top_names)
            # Block nếu có sausage signal
            elif has_sausage_in_prompts:
                logger.info("[CHICKEN BLOCKED] Sausage signal in prompts")
            elif best_name == "Thịt gà":
                should_accept_chicken = True
            elif best_score < chicken_score + 0.03:
                # Candidate khác không rõ hơn gà nhiều
                should_accept_chicken = True
        
        if should_accept_chicken:
            accepted_ingredients = ["Thịt gà"]
            logger.info("[INGREDIENT ACCEPTED] Chicken strict: %.3f", chicken_score)
    
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
        
        # Nếu score cao (>= 0.25), chấp nhận ngay (nếu không bị block)
        if best_name and best_score >= HIGH_CONFIDENCE_THRESHOLD:
            accepted_ingredients = [best_name]
            logger.info("[INGREDIENT ACCEPTED] High confidence: %s (%.3f)", best_name, best_score)
        
        # Nhánh riêng cho gà với threshold thấp hơn
        elif best_name == "Thịt gà" and best_score >= 0.15:
            accepted_ingredients = [best_name]
            logger.info("[INGREDIENT ACCEPTED] Chicken relaxed threshold: %s (%.3f)", best_name, best_score)
        
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
    
    # Use normalized ingredients
    accepted_ingredients = normalized_accepted_ingredients

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

    # Đã nhận diện được - KHÔNG trả candidates
    response_candidates = []

    response = _ingredient_response(
        success=True,
        ingredients=accepted_ingredients,
        candidates=[],
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
            logger.info("[CLIP MODEL LOADING] model=%s (first time only)", model_name)
            _model = CLIPModel.from_pretrained(model_name)
            _processor = CLIPProcessor.from_pretrained(model_name)
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
    response = {
        "success": bool(success and safe_ingredients),
        "ingredients": safe_ingredients,
        "candidates": safe_candidates,
        "confidence": (
            round(float(safe_candidates[0]["score"]), 4)
            if safe_candidates
            else (1.0 if success and safe_ingredients else 0.0)
        ),
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


def _force_accept_from_top_prompts(top_prompts: list[dict[str, Any]], grouped_candidates: list[dict[str, Any]]) -> str | None:
    """Kiểm tra xem có match mạnh từ top prompts không"""
    force_rules = {
        "Sữa": ["milk", "fresh milk", "cow milk", "glass of milk", "milk in a glass", "pouring milk", "white milk", "bottle of milk", "cup of milk"],
        "Xúc xích": ["sausage", "sausages", "hot dog", "hotdog", "frankfurter", "wiener", "sausage skewers", "processed sausage", "red sausage"],
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
        
        # KHÔNG force seafood nếu có rau củ/quả trong top 5 với score gần bằng
        if ingredient in seafood_ingredients and best_veg_fruit and best_veg_fruit_score >= score - 0.08:
            logger.info("[FORCE REJECT] Seafood %s blocked by vegetable/fruit %s (%.3f vs %.3f)", 
                       ingredient, best_veg_fruit, score, best_veg_fruit_score)
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
