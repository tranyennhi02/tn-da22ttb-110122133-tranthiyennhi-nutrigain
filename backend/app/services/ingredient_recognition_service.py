from __future__ import annotations

import io
import logging
import os
import re
import unicodedata

from fastapi import UploadFile


logger = logging.getLogger("uvicorn.error")

MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024
SUPPORTED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}

_clip_model = None
_clip_processor = None

FOOD_LABELS = [
    {
        "vi": "thịt heo",
        "prompts": [
            "a photo of raw pork meat",
            "a photo of pork chop",
            "a photo of sliced pork",
            "a photo of pork meat",
            "a photo of cooked pork",
        ],
    },
    {
        "vi": "thịt bò",
        "prompts": [
            "a photo of raw beef",
            "a photo of beef meat",
            "a photo of cooked beef",
        ],
    },
    {
        "vi": "thịt gà",
        "prompts": [
            "a photo of raw chicken meat",
            "a photo of chicken breast",
            "a photo of cooked chicken",
        ],
    },
    {
        "vi": "trứng",
        "prompts": [
            "a photo of eggs",
            "a photo of boiled egg",
            "a photo of fried egg",
            "a photo of egg",
        ],
    },
    {
        "vi": "sữa",
        "prompts": [
            "a photo of milk",
            "a glass of milk",
            "a bottle of milk",
        ],
    },
    {
        "vi": "cơm",
        "prompts": [
            "a photo of cooked white rice",
            "a bowl of rice",
            "a photo of rice",
        ],
    },
    {
        "vi": "khoai lang",
        "prompts": [
            "a photo of sweet potato",
            "a photo of purple sweet potato",
            "a photo of cooked sweet potato",
        ],
    },
    {
        "vi": "khoai tây",
        "prompts": [
            "a photo of potato",
            "a photo of potatoes",
            "a photo of cooked potato",
        ],
    },
    {
        "vi": "cà rốt",
        "prompts": [
            "a photo of carrot",
            "a photo of carrots",
        ],
    },
    {
        "vi": "chuối",
        "prompts": [
            "a photo of banana",
            "a photo of bananas",
        ],
    },
    {
        "vi": "cam",
        "prompts": [
            "a photo of orange fruit",
            "a photo of oranges",
        ],
    },
    {
        "vi": "táo",
        "prompts": [
            "a photo of apple fruit",
            "a photo of apples",
        ],
    },
    {
        "vi": "đậu phụ",
        "prompts": [
            "a photo of tofu",
            "a photo of bean curd",
        ],
    },
    {
        "vi": "rau cải",
        "prompts": [
            "a photo of leafy greens",
            "a photo of mustard greens",
            "a photo of green vegetables",
        ],
    },
    {
        "vi": "cá",
        "prompts": [
            "a photo of fish",
            "a photo of cooked fish",
            "a photo of raw fish",
        ],
    },
]


def get_clip_model():
    global _clip_model, _clip_processor
    
    try:
        from transformers import CLIPModel, CLIPProcessor
    except Exception as exc:
        logger.warning("[CLIP UNAVAILABLE] %s", exc)
        return None, None
        
    if _clip_model is None or _clip_processor is None:
        model_name = os.getenv("CLIP_MODEL_NAME", "openai/clip-vit-base-patch32")
        _clip_model = CLIPModel.from_pretrained(model_name)
        _clip_processor = CLIPProcessor.from_pretrained(model_name)
        _clip_model.eval()
    return _clip_model, _clip_processor


def _strip_accents(value: object) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    return "".join(ch for ch in text if unicodedata.category(ch) != "Mn")


def _normalize_key(value: object) -> str:
    return re.sub(r"\s+", " ", _strip_accents(value).lower()).strip()


def clean_ingredient_name(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""

    lower = text.lower()

    if re.search(r"\.(png|jpe?g|webp|gif|bmp|heic)$", lower):
        return ""

    if re.fullmatch(r"[a-z0-9_-]{16,}", lower):
        return ""

    if "/" in text or "\\" in text:
        return ""

    if "openai vision request failed" in lower:
        return ""

    return text


def _unique_ingredients(values: list[str]) -> list[str]:
    ingredients: list[str] = []
    seen: set[str] = set()

    for value in values:
        cleaned = clean_ingredient_name(value)
        key = _normalize_key(cleaned)
        if not key or key in seen:
            continue

        seen.add(key)
        ingredients.append(cleaned)

    return ingredients


def _recognition_response(
    ingredients: list[str],
    confidence: str,
    message: str,
    raw_note: str,
) -> dict:
    safe_ingredients = _unique_ingredients(ingredients)
    safe_confidence = confidence if confidence in {"low", "medium", "high"} else "low"

    return {
        "recognized_ingredients": safe_ingredients,
        "recognized_text": ", ".join(safe_ingredients),
        "confidence": safe_confidence,
        "message": message,
        "raw_note": raw_note,
    }


def _confidence_from_score(score: float, threshold: float) -> str:
    if score >= 0.35:
        return "high"
    if score >= threshold:
        return "medium"
    return "low"


def _clip_threshold() -> float:
    raw_threshold = os.getenv("CLIP_RECOGNITION_THRESHOLD", "0.18")
    try:
        return float(raw_threshold)
    except ValueError:
        return 0.18


def recognize_with_clip(image_bytes: bytes, content_type: str) -> dict:
    logger.info("[CLIP FOOD RECOGNITION START] content_type=%s size=%s", content_type, len(image_bytes))

    try:
        import torch
    except ImportError as exc:
        logger.warning("[CLIP UNAVAILABLE] %s", exc)
        return _recognition_response(
            [],
            "low",
            "Tính năng nhận diện AI chưa sẵn sàng trên môi trường này. Bạn có thể nhập thủ công.",
            "CLIP dependencies unavailable"
        )

    try:
        from PIL import Image as _Image
    except ImportError as exc:
        logger.warning("[CLIP UNAVAILABLE PIL] %s", exc)
        return _recognition_response(
            [],
            "low",
            "Tính năng nhận diện AI chưa sẵn sàng trên môi trường này. Bạn có thể nhập thủ công.",
            "Pillow unavailable"
        )

    image = _Image.open(io.BytesIO(image_bytes)).convert("RGB")
    model, processor = get_clip_model()
    
    if model is None or processor is None:
        return _recognition_response(
            [],
            "low",
            "Tính năng nhận diện AI chưa sẵn sàng trên môi trường này. Bạn có thể nhập thủ công.",
            "CLIP dependencies unavailable"
        )

    prompts: list[str] = []
    prompt_to_label: dict[str, str] = {}
    for item in FOOD_LABELS:
        label = item["vi"]
        for prompt in item["prompts"]:
            prompts.append(prompt)
            prompt_to_label[prompt] = label

    inputs = processor(
        text=prompts,
        images=image,
        return_tensors="pt",
        padding=True,
    )

    with torch.no_grad():
        outputs = model(**inputs)
        probs = outputs.logits_per_image.softmax(dim=1)[0]

    best_idx = int(torch.argmax(probs).item())
    best_prompt = prompts[best_idx]
    best_score = float(probs[best_idx].item())
    best_label = prompt_to_label[best_prompt]
    threshold = _clip_threshold()

    top_count = min(5, len(prompts))
    top_scores = []
    top_values = torch.topk(probs, k=top_count)
    for score, idx in zip(top_values.values, top_values.indices):
        prompt = prompts[int(idx.item())]
        top_scores.append(
            {
                "label_vi": prompt_to_label[prompt],
                "prompt": prompt,
                "score": round(float(score.item()), 4),
            }
        )

    logger.info("[CLIP FOOD TOP SCORES] %s", top_scores)
    logger.info(
        "[CLIP FOOD BEST MATCH] label=%s score=%.4f prompt=%s threshold=%.4f",
        best_label,
        best_score,
        best_prompt,
        threshold,
    )

    if best_score < threshold:
        logger.info("[CLIP FOOD NORMALIZED INGREDIENTS] []")
        return _recognition_response(
            [],
            "low",
            "Không nhận diện được nguyên liệu rõ ràng. Bạn có thể nhập thủ công.",
            f"CLIP local zero-shot score below threshold. best={best_label}, score={best_score:.3f}, prompt={best_prompt}",
        )

    ingredients = _unique_ingredients([best_label])
    confidence = _confidence_from_score(best_score, threshold)
    logger.info("[CLIP FOOD NORMALIZED INGREDIENTS] %s", ingredients)

    return _recognition_response(
        ingredients,
        confidence,
        f"Đã nhận diện: {', '.join(ingredients)}.",
        f"CLIP local zero-shot, best={best_label}, score={best_score:.3f}, prompt={best_prompt}",
    )


async def recognize_ingredients_from_image(file: UploadFile) -> dict:
    content_type = (file.content_type or "").lower()

    if content_type not in SUPPORTED_IMAGE_TYPES:
        return _recognition_response(
            [],
            "low",
            "Vui lòng chọn ảnh JPG, PNG hoặc WEBP.",
            f"Unsupported content_type={content_type or 'unknown'}.",
        )

    image_bytes = await file.read()
    if not image_bytes:
        return _recognition_response(
            [],
            "low",
            "Không nhận diện được nguyên liệu rõ ràng. Bạn có thể nhập thủ công.",
            "Empty image upload.",
        )

    if len(image_bytes) > MAX_IMAGE_SIZE_BYTES:
        return _recognition_response(
            [],
            "low",
            "Ảnh quá lớn. Vui lòng chọn ảnh dưới 5MB.",
            "Image size exceeds 5MB.",
        )

    provider = os.getenv("INGREDIENT_RECOGNITION_PROVIDER", "disabled").strip().lower()
    if provider == "disabled":
        return _recognition_response(
            [],
            "low",
            "Tính năng nhận diện AI chưa sẵn sàng trên môi trường này. Bạn có thể nhập thủ công.",
            "Ingredient recognition provider is disabled.",
        )

    if provider != "clip":
        return _recognition_response(
            [],
            "low",
            "Chưa cấu hình provider nhận diện nguyên liệu phù hợp. Bạn có thể nhập thủ công.",
            f"Unsupported ingredient recognition provider={provider}.",
        )

    try:
        return recognize_with_clip(image_bytes, content_type)
    except Exception:
        logger.exception("[CLIP FOOD RECOGNITION ERROR]")
        return _recognition_response(
            [],
            "low",
            "Không thể nhận diện ảnh lúc này. Bạn có thể nhập nguyên liệu thủ công.",
            "CLIP local recognition failed.",
        )
