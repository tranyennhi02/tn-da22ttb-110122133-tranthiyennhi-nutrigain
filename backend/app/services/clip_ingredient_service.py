from __future__ import annotations

import io
import logging
import os
import re
import unicodedata
from typing import Any

from PIL import Image


logger = logging.getLogger("uvicorn.error")

FAIL_MESSAGE = "Không nhận diện được nguyên liệu rõ ràng. Bạn có thể nhập thủ công."

VALID_INGREDIENTS = [
    "Cơm",
    "Khoai lang",
    "Khoai tây",
    "Trứng",
    "Thịt heo",
    "Thịt bò",
    "Thịt gà",
    "Cá",
    "Đậu phụ",
    "Đậu nành",
    "Sữa",
    "Yến mạch",
    "Rau cải",
    "Cà rốt",
    "Bí đỏ",
    "Chuối",
    "Táo",
    "Cam",
]

CLIP_INGREDIENT_PROMPTS = {
    "Cơm": ["rice", "cooked white rice", "a bowl of rice", "steamed rice", "white rice", "com trang", "cơm trắng"],
    "Khoai lang": ["sweet potato", "boiled sweet potato", "purple sweet potato", "roasted sweet potato", "khoai lang"],
    "Khoai tây": ["potato", "potatoes", "boiled potato", "raw potato", "potato pieces", "khoai tay", "khoai tây"],
    "Trứng": ["egg", "eggs", "boiled eggs", "chicken eggs", "raw eggs", "fried egg", "trung ga", "trứng gà"],
    "Thịt heo": [
        "pork",
        "raw pork",
        "raw pork meat",
        "sliced pork",
        "pork belly",
        "lean pork",
        "fresh pork on a plate",
        "meat ingredient",
        "thit heo",
        "thịt heo",
    ],
    "Thịt bò": ["beef", "raw beef", "raw beef meat", "sliced beef", "beef steak", "lean beef", "fresh beef on a plate", "thit bo", "thịt bò"],
    "Thịt gà": ["chicken", "chicken meat", "raw chicken", "chicken breast", "cooked chicken", "fresh chicken meat", "thit ga", "thịt gà"],
    "Cá": ["fish", "fresh fish", "fish fillet", "cooked fish", "raw fish", "whole fish", "ca", "cá"],
    "Đậu phụ": ["tofu", "tofu cubes", "white tofu", "soy tofu", "bean curd", "dau phu", "đậu phụ"],
    "Đậu nành": ["soybeans", "soy beans", "edamame", "soy bean ingredient", "dau nanh", "đậu nành"],
    "Sữa": ["milk", "a glass of milk", "milk carton", "bottle of milk", "white milk", "sua", "sữa"],
    "Yến mạch": ["oats", "oatmeal", "rolled oats", "oat flakes", "yen mach", "yến mạch"],
    "Rau cải": ["leafy green vegetables", "bok choy", "mustard greens", "green vegetables", "fresh greens", "rau cai", "rau cải"],
    "Cà rốt": ["carrot", "carrots", "sliced carrots", "fresh carrots", "ca rot", "cà rốt"],
    "Bí đỏ": ["pumpkin", "pumpkin pieces", "squash", "pumpkin slices", "bi do", "bí đỏ"],
    "Chuối": ["banana", "bananas", "ripe banana", "yellow banana", "chuoi", "chuối"],
    "Táo": ["apple", "red apple", "green apple", "apples", "tao", "táo"],
    "Cam": ["orange fruit", "oranges", "orange slices", "fresh orange", "cam", "quả cam"],
}

FILENAME_INGREDIENT_PATTERNS = [
    ("Thịt heo", ["thit heo", "pork", "pig", "meat heo"]),
    ("Thịt bò", ["thit bo", "beef"]),
    ("Thịt gà", ["thit ga", "chicken"]),
    ("Trứng", ["trung", "egg"]),
    ("Cà rốt", ["ca rot", "carrot"]),
    ("Cá", ["ca", "fish"]),
    ("Sữa", ["sua", "milk"]),
    ("Chuối", ["chuoi", "banana"]),
    ("Khoai lang", ["khoai lang", "sweet potato"]),
    ("Khoai tây", ["khoai tay", "potato"]),
    ("Đậu phụ", ["dau phu", "tofu"]),
    ("Đậu nành", ["dau nanh", "soybean", "soy bean"]),
    ("Rau cải", ["rau cai", "vegetable", "greens", "bok choy"]),
    ("Bí đỏ", ["bi do", "pumpkin"]),
    ("Yến mạch", ["yen mach", "oat", "oatmeal"]),
    ("Cơm", ["com", "rice"]),
    ("Táo", ["tao", "apple"]),
    ("Cam", ["cam", "orange"]),
]

_model = None
_processor = None
_text_features = None
_prompt_meta: list[tuple[str, str]] | None = None


def recognize_ingredients_with_clip(image_bytes: bytes, filename: str | None = None) -> dict[str, Any]:
    filename_ingredient = recognize_ingredient_from_filename(filename)
    logger.info("[FILENAME FALLBACK RESULT] %s", filename_ingredient)
    if filename_ingredient:
        return ingredient_response(
            success=True,
            ingredients=[filename_ingredient],
            raw_labels=[],
            confidence=1.0,
            method="filename_fallback",
            message=f"Đã nhận diện từ tên file: {filename_ingredient}",
        )

    try:
        return recognize_with_clip(image_bytes)
    except Exception as exc:
        logger.warning("[CLIP INGREDIENT ERROR] %s", exc)
        return ingredient_response(
            success=False,
            ingredients=[],
            raw_labels=[],
            confidence=0,
            method="clip",
            message=FAIL_MESSAGE,
        )


def recognize_with_clip(image_bytes: bytes) -> dict[str, Any]:
    try:
        import torch
    except Exception as exc:
        logger.info("[CLIP MODEL STATUS] loaded=false")
        raise RuntimeError("Torch is unavailable for CLIP") from exc

    model, processor = get_clip_model()
    loaded = model is not None and processor is not None
    logger.info("[CLIP MODEL STATUS] loaded=%s", loaded)
    if not loaded:
        raise RuntimeError("CLIP model is unavailable")

    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    inputs = processor(images=image, return_tensors="pt")

    with torch.no_grad():
        image_features = model.get_image_features(**inputs)
        image_features = image_features / image_features.norm(dim=-1, keepdim=True)
        text_features, prompt_meta = get_text_features(model, processor)
        scores = (image_features @ text_features.T)[0]

    per_ingredient: dict[str, float] = {}
    for idx, score in enumerate(scores):
        label = prompt_meta[int(idx)][0]
        value = float(score.item())
        per_ingredient[label] = max(per_ingredient.get(label, -1.0), value)

    sorted_labels = sorted(per_ingredient.items(), key=lambda item: item[1], reverse=True)
    raw_labels = [{"label": label, "score": round(score, 4)} for label, score in sorted_labels[:3]]
    top_5 = [{"label": label, "score": round(score, 4)} for label, score in sorted_labels[:5]]
    logger.info("[CLIP INGREDIENT SCORES] %s", top_5)

    threshold = clip_threshold()
    logger.info("[CLIP THRESHOLD] %s", threshold)
    if not raw_labels:
        return ingredient_response(False, [], [], 0, "clip", FAIL_MESSAGE)

    top = raw_labels[0]
    confidence = float(top["score"])
    if confidence < threshold:
        return ingredient_response(False, [], raw_labels, confidence, "clip", FAIL_MESSAGE)

    label = str(top["label"])
    return ingredient_response(
        success=True,
        ingredients=[label],
        raw_labels=raw_labels,
        confidence=confidence,
        method="clip",
        message=f"Đã nhận diện: {label}",
    )


def get_clip_model():
    global _model, _processor
    if _model is not None and _processor is not None:
        logger.info("[CLIP MODEL STATUS] loaded=true")
        return _model, _processor

    try:
        from transformers import CLIPModel, CLIPProcessor
    except Exception as exc:
        logger.warning("[CLIP UNAVAILABLE] %s", exc)
        logger.info("[CLIP MODEL STATUS] loaded=false")
        return None, None

    model_name = os.getenv("CLIP_MODEL_NAME", "openai/clip-vit-base-patch32")
    _model = CLIPModel.from_pretrained(model_name)
    _processor = CLIPProcessor.from_pretrained(model_name)
    _model.eval()
    logger.info("[CLIP MODEL STATUS] loaded=true")
    return _model, _processor


def get_text_features(model, processor):
    global _text_features, _prompt_meta
    if _text_features is not None and _prompt_meta is not None:
        return _text_features, _prompt_meta

    import torch

    prompts: list[str] = []
    prompt_meta: list[tuple[str, str]] = []
    for label, label_prompts in CLIP_INGREDIENT_PROMPTS.items():
        for prompt in label_prompts:
            prompts.append(prompt)
            prompt_meta.append((label, prompt))

    inputs = processor(text=prompts, return_tensors="pt", padding=True)
    with torch.no_grad():
        text_features = model.get_text_features(**inputs)
        text_features = text_features / text_features.norm(dim=-1, keepdim=True)

    _text_features = text_features
    _prompt_meta = prompt_meta
    return _text_features, _prompt_meta


def recognize_ingredient_from_filename(filename: str | None) -> str | None:
    normalized = normalize_filename(filename)
    if not normalized:
        return None

    for ingredient, patterns in FILENAME_INGREDIENT_PATTERNS:
        for pattern in patterns:
            if phrase_in_text(pattern, normalized):
                return ingredient
    return None


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


def clip_threshold() -> float:
    raw = os.getenv("CLIP_INGREDIENT_THRESHOLD", "0.18")
    try:
        return float(raw)
    except ValueError:
        return 0.18


def ingredient_response(
    success: bool,
    ingredients: list[str],
    raw_labels: list[dict[str, Any]],
    confidence: float,
    method: str,
    message: str,
) -> dict[str, Any]:
    safe_ingredients = [item for item in ingredients if item in VALID_INGREDIENTS]
    response = {
        "success": bool(success and safe_ingredients),
        "ingredients": safe_ingredients,
        "raw_labels": raw_labels,
        "confidence": round(float(confidence or 0), 4),
        "method": method,
        "message": message if success and safe_ingredients else FAIL_MESSAGE,
    }
    logger.info("[INGREDIENT RECOGNITION RESULT] %s", response)
    return response
