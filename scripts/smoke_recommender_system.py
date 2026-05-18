from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def configure_database_url(explicit_database_url: str | None) -> None:
    if explicit_database_url:
        os.environ["DATABASE_URL"] = explicit_database_url
        return
    if os.getenv("SMOKE_DATABASE_URL"):
        os.environ["DATABASE_URL"] = os.environ["SMOKE_DATABASE_URL"]
        return

    database_url = os.getenv("DATABASE_URL", "")
    running_outside_docker = not Path("/.dockerenv").exists()
    if running_outside_docker and "@db:3306" in database_url:
        host_port = os.getenv("DB_PORT", "3307")
        os.environ["DATABASE_URL"] = database_url.replace("@db:3306", f"@127.0.0.1:{host_port}")


def strip_accents(value: object) -> str:
    text = str(value or "")
    text = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in text if unicodedata.category(ch) != "Mn")


def contains_word(text: str, term: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text, re.IGNORECASE) is not None


def item_text(item: dict[str, Any]) -> str:
    fields = (
        "name",
        "original_name",
        "category",
        "normalized_category",
        "food_group",
        "meal_role",
        "culinary_role",
        "quality_flags",
    )
    return " ".join(str(item.get(field) or "") for field in fields)


def text_blob(value: object) -> str:
    if isinstance(value, dict):
        return " ".join(text_blob(item) for item in value.values())
    if isinstance(value, list):
        return " ".join(text_blob(item) for item in value)
    return str(value or "")


REAL_BEEF_TERMS = ("thit bo", "bo nac", "bo nuong", "bo xao", "bo luoc", "lean beef", "grilled beef", "stir fried beef", "boiled beef")
PROCESSED_TERMS = ("biawurst", "xuc xich", "sausage", "processed", "thit che bien")
SWEET_TERMS = ("keo", "candy", "sweets")
NATURAL_FRUIT_TERMS = ("dau", "strawberry", "chuoi", "banana", "tao", "apple", "cam", "orange", "viet quat", "blueberry", "mam xoi", "raspberry")


def normalized_item_text(item: dict[str, Any]) -> str:
    return strip_accents(item_text(item)).lower()


def item_has_any(item: dict[str, Any], terms: tuple[str, ...]) -> bool:
    normalized = normalized_item_text(item)
    return any(term in normalized for term in terms)


def item_is_beef(item: dict[str, Any]) -> bool:
    normalized = normalized_item_text(item)
    has_beef_name = "beef" in normalized or "thit bo" in normalized or contains_word(normalized, "bo")
    has_meat_category = "protein_meat" in normalized or "meat" in normalized
    return has_beef_name and has_meat_category


def item_is_real_beef(item: dict[str, Any]) -> bool:
    return item_is_beef(item) and item_has_any(item, REAL_BEEF_TERMS) and not item_has_any(item, PROCESSED_TERMS)


def item_is_processed_or_sweet(item: dict[str, Any]) -> bool:
    normalized = normalized_item_text(item)
    return (
        item_has_any(item, PROCESSED_TERMS)
        or item_has_any(item, SWEET_TERMS)
        or "dessert_sweets" in normalized
        or "processed_meat" in normalized
    )


def item_is_natural_fruit(item: dict[str, Any]) -> bool:
    normalized = normalized_item_text(item)
    return "fruit" in normalized and item_has_any(item, NATURAL_FRUIT_TERMS)


def parse_profile_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    return [part.strip() for part in str(value).replace(",", ";").split(";") if part.strip()]


def assert_close(actual: object, expected: float, tolerance: float = 0.05) -> None:
    assert actual is not None, f"expected {expected}, got None"
    assert abs(float(actual) - expected) <= tolerance, f"expected {expected}, got {actual}"


def api_request(
    method: str,
    base_url: str,
    path: str,
    *,
    token: str | None = None,
    data: dict[str, Any] | None = None,
    timeout: int = 180,
) -> tuple[int, dict[str, Any]]:
    url = base_url.rstrip("/") + path
    headers = {"Accept": "application/json"}
    body = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if data is not None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            payload = response.read().decode("utf-8")
            return response.getcode(), json.loads(payload) if payload else {}
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode("utf-8", errors="replace")
        try:
            return exc.code, json.loads(payload)
        except json.JSONDecodeError:
            return exc.code, {"error": payload}


@dataclass
class SmokeState:
    args: argparse.Namespace
    db: Any | None = None
    user: Any | None = None
    token: str | None = None
    setup_error: str | None = None
    latest_response: dict[str, Any] = field(default_factory=dict)
    latest_items: list[dict[str, Any]] = field(default_factory=list)
    latest_meals: list[dict[str, Any]] = field(default_factory=list)
    latest_plan_id: int | None = None
    multi_run_results: list[str] = field(default_factory=list)

    def require_setup(self) -> None:
        if self.setup_error:
            raise AssertionError(f"setup failed: {self.setup_error}")
        if self.db is None or self.user is None or not self.token:
            raise AssertionError("setup did not create DB session, test user, and API token")


def flatten_meals(response: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    meals = ((response.get("meal_plan") or {}).get("meals") or [])
    items: list[dict[str, Any]] = []
    for meal in meals:
        for item in meal.get("items") or []:
            item = dict(item)
            item["_meal_type"] = meal.get("meal_type") or meal.get("name") or ""
            items.append(item)
    return meals, items


def refresh_db_snapshot(state: SmokeState) -> None:
    if state.db is not None:
        state.db.rollback()
        state.db.expire_all()


def fail_if_forbidden_items(items: list[dict[str, Any]], rules: list[tuple[str, Callable[[str, str], bool]]]) -> None:
    violations: list[str] = []
    for item in items:
        raw = item_text(item).lower()
        normalized = strip_accents(raw).lower()
        for label, predicate in rules:
            if predicate(raw, normalized):
                violations.append(f"{item.get('_meal_type') or '?'}: {item.get('name')} ({label})")
    assert not violations, "forbidden items found: " + "; ".join(violations)


def vegetarian_forbidden_rules() -> list[tuple[str, Callable[[str, str], bool]]]:
    return [
        ("gà", lambda raw, normalized: contains_word(raw, "gà") or contains_word(normalized, "ga") or "chicken" in normalized or "turkey" in normalized),
        ("bò", lambda raw, normalized: contains_word(raw, "bò") or "thịt bò" in raw or "thit bo" in normalized or "beef" in normalized),
        ("heo", lambda raw, normalized: contains_word(raw, "heo") or contains_word(raw, "lợn") or "pork" in normalized),
        ("cá", lambda raw, normalized: contains_word(raw, "cá") or "protein_seafood" in normalized or "fish" in normalized or "salmon" in normalized or "tuna" in normalized),
        ("tôm", lambda raw, normalized: contains_word(raw, "tôm") or "shrimp" in normalized or "prawn" in normalized),
        ("mực", lambda raw, normalized: contains_word(raw, "mực") or "squid" in normalized),
        ("hải sản", lambda raw, normalized: "hải sản" in raw or "hai san" in normalized or "seafood" in normalized),
    ]


def disliked_rules() -> list[tuple[str, Callable[[str, str], bool]]]:
    return [
        ("gà", lambda raw, normalized: contains_word(raw, "gà") or contains_word(normalized, "ga") or "chicken" in normalized or "turkey" in normalized),
        ("bò", lambda raw, normalized: contains_word(raw, "bò") or "thịt bò" in raw or "thit bo" in normalized or "beef" in normalized),
    ]


def put_profile(state: SmokeState, payload: dict[str, Any]) -> None:
    code, response = api_request(
        "PUT",
        state.args.api_base,
        "/api/v1/users/me/profile",
        token=state.token,
        data=payload,
        timeout=state.args.timeout,
    )
    assert code == 200, f"profile PUT failed: HTTP {code} {response}"


def regenerate(state: SmokeState, payload: dict[str, Any]) -> dict[str, Any]:
    code, response = api_request(
        "POST",
        state.args.api_base,
        "/api/v1/meal-plans/regenerate",
        token=state.token,
        data=payload,
        timeout=state.args.timeout,
    )
    assert code == 200, f"regenerate failed: HTTP {code} {response}"
    meals, items = flatten_meals(response)
    assert items, "regenerate returned no meal items"
    return response


def meal_item_count_summary(response: dict[str, Any], expected: int) -> dict[str, dict[str, int]]:
    summary = (
        (response.get("validation") or {}).get("meal_item_count_summary")
        or (response.get("meal_plan") or {}).get("meal_item_count_summary")
        or {}
    )
    if summary:
        return {
            str(meal_type): {
                "expected": int(info.get("expected") or expected),
                "actual": int(info.get("actual") or 0),
            }
            for meal_type, info in summary.items()
        }
    meals, _ = flatten_meals(response)
    return {
        str(meal.get("meal_type") or ""): {"expected": expected, "actual": len(meal.get("items") or [])}
        for meal in meals
    }


def assert_item_count_contract(response: dict[str, Any], expected: int) -> tuple[int, list[str]]:
    summary = meal_item_count_summary(response, expected)
    validation = response.get("validation") or {}
    warning_text = strip_accents(text_blob(validation.get("warnings") or [])).lower()
    status = str(validation.get("status") or (response.get("meal_plan") or {}).get("status") or "")
    fill_debug = validation.get("meal_fill_debug") or []
    fill_debug_by_meal = {
        str(entry.get("meal_type") or "").lower(): entry
        for entry in fill_debug
        if isinstance(entry, dict)
    }
    shortages: list[str] = []
    missing_total = 0
    for meal_type in ("breakfast", "lunch", "dinner"):
        info = summary.get(meal_type) or {"expected": expected, "actual": 0}
        actual = int(info.get("actual") or 0)
        exp = int(info.get("expected") or expected)
        assert actual <= exp, f"{meal_type} has {actual}/{exp} items, more than requested"
        if actual < exp:
            shortages.append(f"{meal_type}={actual}/{exp}")
            missing_total += exp - actual
            debug_entry = fill_debug_by_meal.get(meal_type)
            assert debug_entry is not None, f"{meal_type} missing items but fill debug is absent; validation={validation}"
            hard_count = int(debug_entry.get("candidate_count_after_hard_filter") or 0)
            assert hard_count == 0, (
                f"{meal_type} still has {hard_count} hard-filter fill candidates but returned {actual}/{exp}; "
                f"debug={debug_entry}; validation={validation}"
            )
    if shortages:
        has_warning = any(term in warning_text for term in ("mon", "phu hop", "khong du", "chi tim duoc", "loai tru"))
        assert has_warning, f"missing items without clear warning: {shortages}; validation={validation}"
        assert status != "valid", f"missing items but status is valid: {shortages}; validation={validation}"
        if missing_total == 1:
            assert status in {"minor_adjustment", "major_adjustment"}, f"missing one item should adjust status, got {status}"
        else:
            assert status == "major_adjustment", f"missing multiple items should be major_adjustment, got {status}"
    return missing_total, shortages


def validation_warning_text(response: dict[str, Any]) -> str:
    validation = response.get("validation") or {}
    return strip_accents(text_blob(validation.get("warnings") or [])).lower()


def validation_info_text(response: dict[str, Any]) -> str:
    validation = response.get("validation") or {}
    return strip_accents(text_blob(validation.get("infos") or [])).lower()


def recommendation_explanations(response: dict[str, Any]) -> list[dict[str, Any]]:
    validation = response.get("validation") or {}
    explanations = response.get("recommendation_explanations") or validation.get("recommendation_explanations") or []
    return [entry for entry in explanations if isinstance(entry, dict)]


def assert_favorite_info(response: dict[str, Any], favorite: str, required_terms: list[str], *, reason: str | None = None) -> None:
    validation = response.get("validation") or {}
    info_text = validation_info_text(response)
    normalized_favorite = strip_accents(favorite).lower()
    missing_terms = [
        term
        for term in required_terms
        if strip_accents(term).lower() not in info_text
    ]
    assert "mon yeu thich" in info_text and normalized_favorite in info_text and not missing_terms, (
        f"missing favorite info for {favorite!r}; required={required_terms}; infos={validation.get('infos')}; validation={validation}"
    )
    warning_text = validation_warning_text(response)
    assert not ("mon yeu thich" in warning_text and normalized_favorite in warning_text), (
        f"favorite info for {favorite!r} leaked into serious warnings; validation={validation}"
    )
    if reason:
        matched = [
            entry
            for entry in recommendation_explanations(response)
            if (
                strip_accents(entry.get("food", "")).lower() == normalized_favorite
                or normalized_favorite in [strip_accents(str(food)).lower() for food in (entry.get("foods") or [])]
            )
            and entry.get("type") == "favorite_skipped"
            and entry.get("reason") == reason
        ]
        assert matched, (
            f"missing favorite_skipped explanation for {favorite!r}/{reason}; "
            f"explanations={recommendation_explanations(response)}"
        )


def assert_favorite_conflict_warning(response: dict[str, Any], favorite: str) -> None:
    assert_favorite_info(response, favorite, ["an chay"], reason="conflicts_with_vegetarian")


def assert_menu_eligible_items(state: SmokeState, items: list[dict[str, Any]]) -> None:
    from sqlalchemy import select

    from app.models.entities import Food

    food_ids = {str(item.get("food_id")) for item in items if item.get("food_id") is not None}
    if not food_ids:
        return
    rows = list(state.db.scalars(select(Food).where(Food.food_id.in_(food_ids))))
    ineligible = [row.food_id for row in rows if not bool(row.menu_eligible)]
    assert not ineligible, f"menu_eligible=0 items returned: {ineligible}"


def assert_hard_rules(state: SmokeState, response: dict[str, Any], *, vegetarian: bool = True) -> None:
    refresh_db_snapshot(state)
    _, items = flatten_meals(response)
    if vegetarian:
        fail_if_forbidden_items(items, vegetarian_forbidden_rules())
    fail_if_forbidden_items(items, disliked_rules())
    assert_menu_eligible_items(state, items)


def setup_state(state: SmokeState) -> None:
    args = state.args
    if "smoke" not in args.email.lower() and not args.allow_non_smoke_email:
        raise AssertionError("refusing to run against a non-smoke email; pass --allow-non-smoke-email to override")

    load_dotenv(ROOT_DIR / ".env")
    load_dotenv(BACKEND_DIR / ".env")
    configure_database_url(args.database_url)

    if str(ROOT_DIR) not in sys.path:
        sys.path.insert(0, str(ROOT_DIR))
    if str(BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(BACKEND_DIR))

    from sqlalchemy import select

    from app.core.database import SessionLocal
    from app.core.security import hash_password
    from app.models.entities import FoodLog, FoodLogItem, FoodRating, Meal, MealPlan, MealPlanItem
    from app.models.entities import RecommendationRequest, User, UserFavoriteFood, UserProfileEntity, WeightLog

    db = SessionLocal()
    state.db = db

    user = db.scalar(select(User).where(User.email == args.email.lower()))
    if user is None:
        user = User(
            email=args.email.lower(),
            password_hash=hash_password(args.password),
            full_name="NutriGain Smoke User",
            role="USER",
            status="ACTIVE",
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        user.password_hash = hash_password(args.password)
        user.full_name = "NutriGain Smoke User"
        user.role = "USER"
        user.status = "ACTIVE"
        user.is_active = True
        db.commit()
        db.refresh(user)

    if args.clean_before:
        item_ids = [
            int(row_id)
            for row_id in db.scalars(
                select(MealPlanItem.id)
                .join(Meal, MealPlanItem.meal_id == Meal.id)
                .join(MealPlan, Meal.meal_plan_id == MealPlan.id)
                .where(MealPlan.user_id == user.id)
            )
        ]
        if item_ids:
            for log_item in db.scalars(select(FoodLogItem).where(FoodLogItem.meal_plan_item_id.in_(item_ids))):
                log_item.meal_plan_item_id = None

        for log in list(db.scalars(select(FoodLog).where(FoodLog.user_id == user.id))):
            db.delete(log)
        for request in list(db.scalars(select(RecommendationRequest).where(RecommendationRequest.user_id == user.id))):
            db.delete(request)
        for plan in list(db.scalars(select(MealPlan).where(MealPlan.user_id == user.id))):
            db.delete(plan)
        for favorite in list(db.scalars(select(UserFavoriteFood).where(UserFavoriteFood.user_id == user.id))):
            db.delete(favorite)
        for rating in list(db.scalars(select(FoodRating).where(FoodRating.user_id == user.id))):
            db.delete(rating)
        for log in list(db.scalars(select(WeightLog).where(WeightLog.user_id == user.id))):
            db.delete(log)
        profile = db.scalar(select(UserProfileEntity).where(UserProfileEntity.user_id == user.id))
        if profile is not None:
            db.delete(profile)
        db.commit()
        db.refresh(user)

    code, payload = api_request(
        "POST",
        args.api_base,
        "/api/v1/auth/login",
        data={"email": args.email, "password": args.password},
        timeout=args.timeout,
    )
    if code != 200 or not payload.get("access_token"):
        raise AssertionError(f"login failed via API: HTTP {code} {payload}")
    api_user_id = int((payload.get("user") or {}).get("id") or 0)
    db.expire_all()
    db_user = db.scalar(select(User).where(User.email == args.email.lower()))
    if db_user is None:
        raise AssertionError("API login succeeded, but direct DB query cannot find the smoke user by email")
    if api_user_id and int(db_user.id) != api_user_id:
        raise AssertionError(
            f"API/DB user mismatch for {args.email}: API id={api_user_id}, direct DB id={db_user.id}. "
            "Pass --database-url/SMOKE_DATABASE_URL that points to the same DB as the backend API."
        )
    state.token = payload["access_token"]
    state.user = db_user


def case_profile_persistence(state: SmokeState) -> str:
    state.require_setup()
    from sqlalchemy import select

    from app.models.entities import UserProfileEntity

    old_profile = {
        "weight_kg": 42,
        "height_cm": 167,
        "age": 22,
        "sex": "female",
        "gender": "female",
        "activity_level": "moderate",
        "surplus_kcal": 250,
        "target_weight_kg": 56,
        "weight_gain_speed": "slow",
        "diet_type": "balanced",
        "budget_level": "standard",
        "items_per_meal": 3,
        "favorite_foods": ["sữa"],
        "disliked_foods": ["tôm"],
    }
    code, payload = api_request("PUT", state.args.api_base, "/api/v1/users/me/profile", token=state.token, data=old_profile, timeout=state.args.timeout)
    assert code == 200, f"old profile PUT failed: HTTP {code} {payload}"

    new_profile = {
        "weight_kg": 39,
        "height_cm": 167,
        "age": 22,
        "sex": "female",
        "gender": "female",
        "activity_level": "moderate",
        "surplus_kcal": 450,
        "target_weight_kg": 55,
        "weight_gain_speed": "moderate",
        "diet_type": "vegetarian",
        "budget_level": "standard",
        "items_per_meal": 4,
        "favorite_foods": ["chuối"],
        "disliked_foods": ["gà", "bò"],
    }
    code, payload = api_request("PUT", state.args.api_base, "/api/v1/users/me/profile", token=state.token, data=new_profile, timeout=state.args.timeout)
    assert code == 200, f"new profile PUT failed: HTTP {code} {payload}"

    refresh_db_snapshot(state)
    profile = state.db.scalar(select(UserProfileEntity).where(UserProfileEntity.user_id == state.user.id))
    assert profile is not None, "user_profiles row was not created"
    assert_close(profile.weight_kg, 39)
    assert_close(profile.target_weight_kg, 55)
    assert profile.diet_type == "vegetarian", f"expected diet_type vegetarian, got {profile.diet_type}"
    assert int(profile.items_per_meal or 0) == 4, f"expected items_per_meal 4, got {profile.items_per_meal}"
    assert parse_profile_list(profile.favorite_foods) == ["chuối"], f"favorite_foods stored as {profile.favorite_foods!r}"
    assert parse_profile_list(profile.disliked_foods) == ["gà", "bò"], f"disliked_foods stored as {profile.disliked_foods!r}"
    return "saved weight_kg=39, target_weight_kg=55, diet_type=vegetarian, items_per_meal=4"


def case_recommender_latest_profile(state: SmokeState) -> str:
    state.require_setup()
    code, payload = api_request(
        "POST",
        state.args.api_base,
        "/api/v1/meal-plans/regenerate",
        token=state.token,
        data={"randomSeed": 20260516, "excludePreviousItems": False},
        timeout=state.args.timeout,
    )
    assert code == 200, f"regenerate failed: HTTP {code} {payload}"
    snapshot = payload.get("profile_snapshot") or {}
    assert_close(snapshot.get("weight_kg"), 39)
    assert snapshot.get("diet_type") == "vegetarian", f"profile_snapshot diet_type={snapshot.get('diet_type')!r}"
    assert int(snapshot.get("items_per_meal") or 0) == 4, f"profile_snapshot items_per_meal={snapshot.get('items_per_meal')!r}"
    assert snapshot.get("weight_kg") != 42, "recommender used stale weight_kg=42"
    assert snapshot.get("diet_type") != "balanced", "recommender used stale diet_type=balanced"
    assert int(snapshot.get("items_per_meal") or 0) != 3, "recommender used stale items_per_meal=3"

    meals, items = flatten_meals(payload)
    assert items, "regenerate returned no meal items"
    state.latest_response = payload
    state.latest_meals = meals
    state.latest_items = items
    plan_id = (payload.get("meal_plan") or {}).get("id")
    state.latest_plan_id = int(plan_id) if plan_id is not None else None
    return f"profile_snapshot ok; generated {len(items)} items"


def case_vegetarian_filter(state: SmokeState) -> str:
    state.require_setup()
    assert state.latest_items, "regenerate response is missing; run case 2 first"
    rules = [
        ("gà", lambda raw, normalized: contains_word(raw, "gà") or contains_word(normalized, "ga") or "chicken" in normalized or "turkey" in normalized),
        ("bò", lambda raw, normalized: contains_word(raw, "bò") or "thịt bò" in raw or "thit bo" in normalized or "beef" in normalized),
        ("heo", lambda raw, normalized: contains_word(raw, "heo") or contains_word(raw, "lợn") or "pork" in normalized),
        ("cá", lambda raw, normalized: contains_word(raw, "cá") or "protein_seafood" in normalized or "fish" in normalized or "salmon" in normalized or "tuna" in normalized),
        ("tôm", lambda raw, normalized: contains_word(raw, "tôm") or "shrimp" in normalized or "prawn" in normalized),
        ("mực", lambda raw, normalized: contains_word(raw, "mực") or "squid" in normalized),
        ("hải sản", lambda raw, normalized: "hải sản" in raw or "hai san" in normalized or "seafood" in normalized),
    ]
    fail_if_forbidden_items(state.latest_items, rules)
    return "no animal meat/seafood terms detected"


def case_disliked_food_filter(state: SmokeState) -> str:
    state.require_setup()
    assert state.latest_items, "regenerate response is missing; run case 2 first"
    rules = [
        ("gà", lambda raw, normalized: contains_word(raw, "gà") or contains_word(normalized, "ga") or "chicken" in normalized or "turkey" in normalized),
        ("bò", lambda raw, normalized: contains_word(raw, "bò") or "thịt bò" in raw or "thit bo" in normalized or "beef" in normalized),
    ]
    fail_if_forbidden_items(state.latest_items, rules)
    return "no disliked terms gà/bò detected"


def case_items_per_meal(state: SmokeState) -> str:
    state.require_setup()
    assert state.latest_meals, "regenerate response is missing; run case 2 first"
    expected = 4
    required = {"breakfast", "lunch", "dinner"}
    validation = state.latest_response.get("validation") or {}
    validation_text = strip_accents(text_blob(validation)).lower()
    short_meals: list[str] = []
    overfilled_meals: list[str] = []
    seen = set()
    for meal in state.latest_meals:
        meal_type = str(meal.get("meal_type") or "").lower()
        if meal_type in required:
            seen.add(meal_type)
            count = len(meal.get("items") or [])
            if count < expected:
                short_meals.append(f"{meal_type}={count}/{expected}")
            if count > expected:
                overfilled_meals.append(f"{meal_type}={count}/{expected}")
    missing = sorted(required - seen)
    assert not overfilled_meals, "meals exceeded requested item count: " + ", ".join(overfilled_meals)
    if missing or short_meals:
        has_warning = any(term in validation_text for term in ("mon", "thieu", "khong du", "4", "can tang"))
        assert has_warning, f"silent shortage, missing={missing}, short={short_meals}, validation={validation}"
    return "breakfast/lunch/dinner honor 4 items, or shortages are warned"


def case_macro_validation(state: SmokeState) -> str:
    state.require_setup()
    from app.services.recommender_service import RecommenderService

    response = state.latest_response
    validation = response.get("validation") or {}
    meal_plan = response.get("meal_plan") or {}
    target = response.get("nutrition_target") or {}
    target_kcal = float(validation.get("targetKcal") or validation.get("target_kcal") or target.get("calorie_target") or 0)
    total_kcal = float(validation.get("totalKcal") or validation.get("total_kcal") or meal_plan.get("total_kcal") or 0)
    status = str(validation.get("status") or meal_plan.get("status") or "")
    if target_kcal > 0 and abs(total_kcal - target_kcal) / target_kcal > 0.15:
        assert status != "valid", f"status is valid despite kcal diff >15% ({total_kcal}/{target_kcal})"

    protein_target = float(target.get("protein_g") or response.get("target_protein") or 0)
    total_protein = float(meal_plan.get("total_protein_g") or 0)
    warnings_blob = strip_accents(text_blob(validation.get("warnings") or [])).lower()
    if protein_target > 0 and total_protein > protein_target * 1.15:
        assert status == "major_adjustment" or "protein" in warnings_blob or "dam" in warnings_blob, (
            f"protein is >115% but status/warnings are weak: protein={total_protein}, target={protein_target}, status={status}"
        )

    synthetic = RecommenderService._validate_generated_plan(
        total_kcal=1300,
        total_protein=140,
        total_fat=50,
        total_carbs=240,
        target={"calorie_target": 2000, "protein_g": 100, "fat_g": 60, "carbs_g": 260},
    )
    assert synthetic["status"] != "valid", f"synthetic >15% kcal diff returned valid: {synthetic}"
    assert synthetic["status"] == "major_adjustment", f"protein >115% should be major_adjustment, got {synthetic}"
    synthetic_text = strip_accents(text_blob(synthetic)).lower()
    assert "dat muc tieu" not in synthetic_text, f"serious warning still says Đạt mục tiêu: {synthetic}"
    return "actual plan and synthetic severe macro cases are not marked valid"


def case_favorite_foods(state: SmokeState) -> str:
    state.require_setup()
    from sqlalchemy import or_, select

    from app.models.entities import Food

    banana_filter = or_(
        Food.name.ilike("%banana%"),
        Food.display_name.ilike("%chuối%"),
        Food.dish_name_vi.ilike("%chuối%"),
        Food.name_vi.ilike("%chuối%"),
        Food.search_keywords.ilike("%chuối%"),
    )
    eligible_banana = state.db.scalar(select(Food).where(banana_filter, Food.menu_eligible.is_(True)).limit(1))
    validation = state.latest_response.get("validation") or {}
    target_kcal = float(validation.get("targetKcal") or validation.get("target_kcal") or 0)
    total_kcal = float(validation.get("totalKcal") or validation.get("total_kcal") or 0)
    missing_kcal = target_kcal > 0 and total_kcal < target_kcal * 0.95
    selected_banana = any("chuối" in item_text(item).lower() or "banana" in strip_accents(item_text(item)).lower() for item in state.latest_items)
    explanation_text = strip_accents(text_blob(state.latest_response)).lower()

    if eligible_banana is not None and missing_kcal:
        assert selected_banana or "chuoi" in explanation_text or "favorite" in explanation_text or "yeu thich" in explanation_text, (
            "eligible banana exists and kcal is missing, but banana was not selected and no warning/debug reason explains it"
        )
        return "eligible banana precondition true; selected or explained"
    if selected_banana:
        return "banana selected"
    return "no eligible banana+kcal-shortage precondition; favorite priority not required"


def case_meal_plan_user_ownership(state: SmokeState) -> str:
    state.require_setup()
    from sqlalchemy import select

    from app.models.entities import Meal, MealPlan, MealPlanItem

    refresh_db_snapshot(state)
    plan = None
    if state.latest_plan_id is not None:
        plan = state.db.get(MealPlan, state.latest_plan_id)
    if plan is None:
        plan = state.db.scalar(
            select(MealPlan)
            .where(MealPlan.user_id == state.user.id)
            .order_by(MealPlan.created_at.desc())
            .limit(1)
        )
    assert plan is not None, "meal_plans row not found after regenerate"
    assert int(plan.user_id) == int(state.user.id), f"meal_plan.user_id={plan.user_id}, current_user.id={state.user.id}"
    items = list(
        state.db.scalars(
            select(MealPlanItem)
            .join(Meal, MealPlanItem.meal_id == Meal.id)
            .where(Meal.meal_plan_id == plan.id)
        )
    )
    assert items, f"meal_plan_items empty for meal_plan_id={plan.id}"
    wrong_user_plans = list(
        state.db.scalars(
            select(MealPlan)
            .where(MealPlan.id == plan.id)
            .where(MealPlan.user_id != state.user.id)
        )
    )
    assert not wrong_user_plans, "same meal_plan id is visible under another user"
    return f"meal_plan_id={plan.id} belongs to user_id={state.user.id}; items={len(items)}"


def case_image_safety(state: SmokeState) -> str:
    state.require_setup()
    assert state.latest_items, "regenerate response is missing; run case 2 first"
    missing_fields = []
    for item in state.latest_items:
        for field_name in ("image_url", "image_source_type", "image_verified"):
            if field_name not in item:
                missing_fields.append(f"{item.get('name')} missing {field_name}")
    assert not missing_fields, "; ".join(missing_fields)

    dashboard_source = (ROOT_DIR / "frontend" / "src" / "views" / "DashboardView.jsx").read_text(encoding="utf-8")
    meal_card_source = (ROOT_DIR / "frontend" / "src" / "components" / "MealCard.jsx").read_text(encoding="utf-8")
    compact_dashboard = re.sub(r"\s+", " ", dashboard_source)
    compact_meal_card = re.sub(r"\s+", " ", meal_card_source)
    assert "imageVerified && normalizedImageSourceType === \"real\"" in compact_dashboard, (
        "Dashboard mapFoodPayload must require image_verified and image_source_type='real'"
    )
    assert "sourceType === \"real\"" in compact_meal_card and "verified && isReal && hasUrl" in compact_meal_card, (
        "MealCard shouldShowRealImage must require verified real images"
    )

    pexels_pending = {"image_url": "https://images.pexels.com/photos/test.jpeg", "image_source_type": "pexels", "image_verified": 0}
    verified = pexels_pending["image_verified"] in (True, 1, "1", "true")
    show_real = bool(pexels_pending["image_url"]) and verified and pexels_pending["image_source_type"] == "real"
    assert show_real is False, "pexels pending image would be treated as a real image"
    return "response has image fields; frontend gates real images by verified=1 and source_type='real'"


def case_a_vegetarian_five_items(state: SmokeState) -> str:
    state.require_setup()
    put_profile(
        state,
        {
            "weight_kg": 48,
            "height_cm": 167,
            "age": 22,
            "sex": "male",
            "gender": "male",
            "activity_level": "moderate",
            "surplus_kcal": 400,
            "target_weight_kg": 58,
            "weight_gain_speed": "moderate",
            "diet_type": "vegetarian",
            "budget_level": "flexible",
            "items_per_meal": 5,
            "favorite_foods": ["bò", "gà", "trứng"],
            "disliked_foods": [],
        },
    )
    response = regenerate(state, {"randomSeed": 2026051701, "excludePreviousItems": False})
    assert_hard_rules(state, response, vegetarian=True)
    assert_favorite_conflict_warning(response, "bò")
    assert_favorite_conflict_warning(response, "gà")
    assert_favorite_conflict_warning(response, "trứng")
    missing_total, shortages = assert_item_count_contract(response, expected=5)
    status = str((response.get("validation") or {}).get("status") or "")
    if missing_total == 0:
        assert status != "major_adjustment", f"favorite conflict alone should not force major_adjustment: validation={response.get('validation')}"
    return f"vegetarian favorite-conflict info ok; status={status}; missing_total={missing_total}; shortages={shortages or 'none'}"


def case_b_favorite_disliked_exclusion(state: SmokeState) -> str:
    state.require_setup()
    put_profile(
        state,
        {
            "weight_kg": 48,
            "height_cm": 167,
            "age": 22,
            "sex": "male",
            "gender": "male",
            "activity_level": "moderate",
            "surplus_kcal": 400,
            "target_weight_kg": 58,
            "weight_gain_speed": "moderate",
            "diet_type": "balanced",
            "budget_level": "flexible",
            "items_per_meal": 5,
            "favorite_foods": ["bò"],
            "disliked_foods": ["bò"],
        },
    )
    response = regenerate(state, {"randomSeed": 2026051704, "excludePreviousItems": False})
    _, items = flatten_meals(response)

    def item_is_beef(item: dict[str, Any]) -> bool:
        normalized_item = strip_accents(item_text(item)).lower()
        has_beef_name = "beef" in normalized_item or "thit bo" in normalized_item or contains_word(normalized_item, "bo")
        has_meat_category = "protein_meat" in normalized_item or "meat" in normalized_item
        return has_beef_name and has_meat_category

    assert not any(item_is_beef(item) for item in items), f"favorite/disliked beef was selected: {items}"
    assert_favorite_info(response, "bò", ["loại trừ"], reason="excluded_by_disliked_or_allergy")
    missing_total, shortages = assert_item_count_contract(response, expected=5)
    status = str((response.get("validation") or {}).get("status") or "")
    return f"favorite exclusion info ok; status={status}; missing_total={missing_total}; shortages={shortages or 'none'}"


def case_b_high_protein_fill(state: SmokeState) -> str:
    state.require_setup()
    put_profile(
        state,
        {
            "weight_kg": 39,
            "height_cm": 167,
            "age": 22,
            "sex": "female",
            "gender": "female",
            "activity_level": "moderate",
            "surplus_kcal": 450,
            "target_weight_kg": 55,
            "weight_gain_speed": "moderate",
            "diet_type": "vegetarian",
            "budget_level": "standard",
            "items_per_meal": 4,
            "favorite_foods": ["chuối"],
            "disliked_foods": ["gà", "bò"],
        },
    )
    response = regenerate(
        state,
        {
            "randomSeed": 2026051702,
            "excludePreviousItems": False,
            "targetKcal": 2350,
            "protein_target": 35,
        },
    )
    assert_hard_rules(state, response, vegetarian=True)
    missing_total, shortages = assert_item_count_contract(response, expected=4)
    validation = response.get("validation") or {}
    meal_plan = response.get("meal_plan") or {}
    protein_target = float((response.get("nutrition_target") or {}).get("protein_g") or 35)
    total_protein = float(meal_plan.get("total_protein_g") or 0)
    warning_text = strip_accents(text_blob(validation.get("warnings") or [])).lower()
    if total_protein > protein_target * 1.15:
        assert validation.get("status") == "major_adjustment" or "protein" in warning_text or "dam" in warning_text, (
            f"protein high without serious status/warning: total={total_protein}, target={protein_target}, validation={validation}"
        )
    return f"high-protein scenario ok; protein={total_protein:.1f}/{protein_target:.1f}; missing_total={missing_total}; shortages={shortages or 'none'}"


def case_balanced_beef_profile_protein_guard(state: SmokeState) -> str:
    state.require_setup()
    put_profile(
        state,
        {
            "weight_kg": 41,
            "height_cm": 156,
            "age": 22,
            "sex": "female",
            "gender": "female",
            "activity_level": "moderate",
            "target_weight_kg": 45,
            "weight_gain_speed": "moderate",
            "diet_type": "balanced",
            "budget_level": "flexible",
            "items_per_meal": 4,
            "favorite_foods": ["b\u00f2"],
            "disliked_foods": ["g\u00e0"],
        },
    )
    response = regenerate(
        state,
        {
            "randomSeed": 2026051703,
            "excludePreviousItems": False,
            "targetKcal": 2200,
            "protein_target": 35,
        },
    )
    meals, items = flatten_meals(response)
    fail_if_forbidden_items(
        items,
        [
            (
                "g\u00e0",
                lambda raw, normalized: contains_word(raw, "g\u00e0")
                or contains_word(normalized, "ga")
                or "chicken" in normalized
                or "turkey" in normalized,
            )
        ],
    )
    missing_total, shortages = assert_item_count_contract(response, expected=4)

    validation = response.get("validation") or {}
    meal_plan = response.get("meal_plan") or {}
    target = response.get("nutrition_target") or {}
    target_kcal = float(validation.get("targetKcal") or validation.get("target_kcal") or target.get("calorie_target") or 0)
    total_kcal = float(validation.get("totalKcal") or validation.get("total_kcal") or meal_plan.get("total_kcal") or 0)
    assert target_kcal > 0 and abs(total_kcal - target_kcal) / target_kcal <= 0.15, (
        f"kcal outside +/-15% target: total={total_kcal}, target={target_kcal}, validation={validation}"
    )

    protein_target = float(target.get("protein_g") or response.get("target_protein") or 0)
    total_protein = float(meal_plan.get("total_protein_g") or 0)
    status = str(validation.get("status") or meal_plan.get("status") or "")
    warning_text = validation_warning_text(response)
    info_text = validation_info_text(response)
    if protein_target > 0 and total_protein > protein_target * 1.15:
        assert status != "valid", f"protein >115% but status is valid: protein={total_protein}, target={protein_target}, validation={validation}"
        assert "protein" in warning_text and "vuot" in warning_text, (
            f"protein >115% without clear warning: protein={total_protein}, target={protein_target}, validation={validation}"
        )

    def item_is_beef(item: dict[str, Any]) -> bool:
        normalized_item = strip_accents(item_text(item)).lower()
        has_beef_name = "beef" in normalized_item or "thit bo" in normalized_item or contains_word(normalized_item, "bo")
        has_meat_category = "protein_meat" in normalized_item or "meat" in normalized_item
        return has_beef_name and has_meat_category

    selected_beef = any(item_is_beef(item) for item in items)
    if not selected_beef and protein_target > 0 and total_protein >= protein_target * 0.95:
        assert "mon yeu thich" in info_text and "bo" in info_text and ("protein" in info_text or "dam" in info_text), (
            f"favorite beef not selected while protein high, but no reason info: validation={validation}"
        )
        assert_favorite_info(response, "bò", ["protein"], reason="protein_near_or_above_target")
    protein_warning = next(
        (
            str(warning)
            for warning in (validation.get("warnings") or [])
            if "protein" in strip_accents(str(warning)).lower() and "vuot" in strip_accents(str(warning)).lower()
        ),
        "none",
    )

    dashboard_source = (ROOT_DIR / "frontend" / "src" / "views" / "DashboardView.jsx").read_text(encoding="utf-8")
    assert "proteinOverLimit" in dashboard_source and "buildProteinExcessMessage" in dashboard_source, (
        "Dashboard must derive warning status from protein excess, not kcal progress alone"
    )
    assert "safeValidation.isValid && !safeValidation.proteinOverLimit && safeProgress >= 95" in dashboard_source, (
        "Dashboard success notification must be suppressed when protein is over limit"
    )
    return (
        f"balanced beef profile ok; kcal={total_kcal:.0f}/{target_kcal:.0f}; "
        f"protein={total_protein:.1f}/{protein_target:.1f}; status={status}; "
        f"missing_total={missing_total}; shortages={shortages or 'none'}; meals={len(meals)}; "
        f"protein_warning={protein_warning}"
    )


def case_balanced_milk_five_item_fill(state: SmokeState) -> str:
    state.require_setup()
    from sqlalchemy import select

    from app.models.entities import Food

    put_profile(
        state,
        {
            "weight_kg": 41,
            "height_cm": 156,
            "age": 22,
            "sex": "female",
            "gender": "female",
            "activity_level": "moderate",
            "target_weight_kg": 45,
            "weight_gain_speed": "moderate",
            "diet_type": "balanced",
            "budget_level": "flexible",
            "items_per_meal": 5,
            "favorite_foods": ["b\u00f2", "s\u1eefa"],
            "disliked_foods": ["g\u00e0"],
        },
    )
    response = regenerate(state, {"randomSeed": 2026051801, "excludePreviousItems": False})
    meals, items = flatten_meals(response)
    fail_if_forbidden_items(
        items,
        [
            (
                "g\u00e0",
                lambda raw, normalized: contains_word(raw, "g\u00e0")
                or contains_word(normalized, "ga")
                or "chicken" in normalized
                or "turkey" in normalized,
            )
        ],
    )
    missing_total, shortages = assert_item_count_contract(response, expected=5)

    validation = response.get("validation") or {}
    meal_plan = response.get("meal_plan") or {}
    target = response.get("nutrition_target") or {}
    target_kcal = float(validation.get("targetKcal") or validation.get("target_kcal") or target.get("calorie_target") or 0)
    total_kcal = float(validation.get("totalKcal") or validation.get("total_kcal") or meal_plan.get("total_kcal") or 0)
    assert target_kcal > 0, f"missing kcal target: validation={validation}; target={target}"
    assert abs(total_kcal - target_kcal) / target_kcal <= 0.15, (
        f"kcal outside +/-15% target: total={total_kcal}, target={target_kcal}, validation={validation}"
    )

    selected_real_beef = any(item_is_real_beef(item) for item in items)
    selected_processed_beef = any(item_is_beef(item) and item_has_any(item, PROCESSED_TERMS) for item in items)
    selected_any_beef = any(item_is_beef(item) for item in items)
    low_priority_items = [str(item.get("name") or item.get("food_id")) for item in items if item_is_processed_or_sweet(item)]
    natural_fruit_selected = any(item_is_natural_fruit(item) for item in items)

    eligible_real_beef_available = False
    natural_fruit_available = False
    for food in state.db.scalars(select(Food).where(Food.menu_eligible.is_(True))):
        food_item = {
            "food_id": food.food_id,
            "name": food.name or food.display_name or food.name_vi or "",
            "original_name": food.original_name or "",
            "category": food.clean_category or food.category or "",
            "normalized_category": food.clean_category or "",
            "search_keywords": food.search_keywords or "",
            "quality_flags": food.quality_flags or "",
        }
        if not eligible_real_beef_available and item_is_real_beef(food_item):
            calories = float(food.kcal_per_serving_clean or food.calories or food.kcal_per_100g_clean or 0)
            protein = float(food.protein_per_serving_clean or food.protein or food.protein_per_100g_clean or 0)
            eligible_real_beef_available = calories > 0 and protein >= 0
        if not natural_fruit_available and item_is_natural_fruit(food_item):
            calories = float(food.kcal_per_serving_clean or food.calories or food.kcal_per_100g_clean or 0)
            natural_fruit_available = calories > 0
        if eligible_real_beef_available and natural_fruit_available:
            break

    assert len(low_priority_items) <= 2, f"too many processed/sweet items selected: {low_priority_items}"
    if selected_processed_beef and eligible_real_beef_available:
        assert selected_real_beef, f"processed beef selected while real beef candidate exists: {low_priority_items}; items={items}"
    if any(item_has_any(item, SWEET_TERMS) for item in items) and natural_fruit_available:
        assert natural_fruit_selected, f"sweet fruit/candy selected without natural fruit despite candidate availability: items={items}"
    if not selected_any_beef:
        info_text = validation_info_text(response)
        assert "mon yeu thich" in info_text and "bo" in info_text and "kcal/protein" in info_text, (
            f"favorite beef not selected without kcal/protein explanation: validation={validation}"
        )

    counts = {
        str(meal.get("meal_type") or ""): len(meal.get("items") or [])
        for meal in meals
        if str(meal.get("meal_type") or "") in {"breakfast", "lunch", "dinner"}
    }
    return (
        f"balanced milk fill ok; kcal={total_kcal:.0f}/{target_kcal:.0f}; "
        f"missing_total={missing_total}; shortages={shortages or 'none'}; "
        f"real_beef={selected_real_beef}; processed_beef={selected_processed_beef}; "
        f"low_priority={low_priority_items or 'none'}; counts={counts}"
    )


def case_c_regenerate_five_times(state: SmokeState) -> str:
    state.require_setup()
    put_profile(
        state,
        {
            "weight_kg": 47,
            "height_cm": 167,
            "age": 22,
            "sex": "male",
            "gender": "male",
            "activity_level": "moderate",
            "surplus_kcal": 400,
            "target_weight_kg": 58,
            "weight_gain_speed": "moderate",
            "diet_type": "vegetarian",
            "budget_level": "flexible",
            "items_per_meal": 5,
            "favorite_foods": ["bò"],
            "disliked_foods": ["gà"],
        },
    )
    run_summaries: list[str] = []
    shortage_runs = 0
    for index in range(5):
        seed = 2026051800 + index
        response = regenerate(state, {"randomSeed": seed, "excludePreviousItems": False})
        assert_hard_rules(state, response, vegetarian=True)
        assert_favorite_conflict_warning(response, "bò")
        missing_total, shortages = assert_item_count_contract(response, expected=5)
        if missing_total:
            shortage_runs += 1
        run_summaries.append(f"run{index + 1}:seed={seed}:missing={missing_total}:shortages={shortages or 'none'}")
    state.multi_run_results = run_summaries
    return f"5 regenerates ok; shortage_runs={shortage_runs}/5; " + " | ".join(run_summaries)


def run_case(index: int, name: str, func: Callable[[SmokeState], str], state: SmokeState) -> bool:
    try:
        detail = func(state)
    except Exception as exc:
        print(f"[FAIL] {index}. {name} - {exc}")
        return False
    print(f"[PASS] {index}. {name} - {detail}")
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="NutriGain recommender smoke tests")
    parser.add_argument("--api-base", default=os.getenv("SMOKE_API_BASE", "http://localhost:8000"))
    parser.add_argument("--database-url", default=os.getenv("SMOKE_DATABASE_URL"))
    parser.add_argument("--email", default=os.getenv("SMOKE_EMAIL", "nutrigain.smoke.recommender@example.com"))
    parser.add_argument("--password", default=os.getenv("SMOKE_PASSWORD", "SmokePass123!"))
    parser.add_argument("--timeout", type=int, default=int(os.getenv("SMOKE_TIMEOUT", "180")))
    parser.add_argument("--clean-before", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--allow-non-smoke-email", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    state = SmokeState(args=args)
    setup_started = time.perf_counter()
    try:
        setup_state(state)
        print(f"[PASS] setup - test user ready: {args.email}")
    except Exception as exc:
        state.setup_error = str(exc)
        print(f"[FAIL] setup - {exc}")

    cases: list[tuple[str, Callable[[SmokeState], str]]] = [
        ("Profile persistence", case_profile_persistence),
        ("Recommender uses latest profile", case_recommender_latest_profile),
        ("Vegetarian filter", case_vegetarian_filter),
        ("Disliked foods filter", case_disliked_food_filter),
        ("Items per meal", case_items_per_meal),
        ("Macro validation", case_macro_validation),
        ("Favorite foods", case_favorite_foods),
        ("Meal plan belongs to correct user", case_meal_plan_user_ownership),
        ("Image safety", case_image_safety),
        ("Case A vegetarian favorite conflict info", case_a_vegetarian_five_items),
        ("Case B favorite disliked exclusion info", case_b_favorite_disliked_exclusion),
        ("Vegetarian high-protein fill contract", case_b_high_protein_fill),
        ("Case C balanced beef protein guard", case_balanced_beef_profile_protein_guard),
        ("Balanced milk five-item fill", case_balanced_milk_five_item_fill),
        ("Repeated vegetarian 5-item contract", case_c_regenerate_five_times),
    ]
    passed = 0
    for index, (name, func) in enumerate(cases, start=1):
        if run_case(index, name, func, state):
            passed += 1

    elapsed = time.perf_counter() - setup_started
    failed = len(cases) - passed
    print(f"Summary: {passed} PASS, {failed} FAIL in {elapsed:.1f}s")
    if state.db is not None:
        state.db.close()
    return 0 if failed == 0 and not state.setup_error else 1


if __name__ == "__main__":
    raise SystemExit(main())
