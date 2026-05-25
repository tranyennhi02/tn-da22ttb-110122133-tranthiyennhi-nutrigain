from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from sqlalchemy.engine import make_url
from sqlalchemy import MetaData, Table, and_, func, inspect, or_, select, update
from sqlalchemy.exc import SQLAlchemyError


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ROOT_ENV = PROJECT_ROOT / ".env"
BACKEND_ENV = PROJECT_ROOT / "backend" / ".env"

_DATABASE_URL_WAS_PREEXISTING = "DATABASE_URL" in os.environ

if ROOT_ENV.exists():
    load_dotenv(ROOT_ENV)
if BACKEND_ENV.exists():
    load_dotenv(BACKEND_ENV, override=False)


def _running_in_docker() -> bool:
    return Path("/.dockerenv").exists()


def _resolve_database_url_for_runtime() -> None:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url or _running_in_docker():
        return

    if _DATABASE_URL_WAS_PREEXISTING:
        return

    try:
        parsed = make_url(database_url)
    except Exception:
        return

    if parsed.host not in {"db", "localhost", "127.0.0.1"}:
        return

    local_host = os.getenv("DB_HOST", "127.0.0.1").strip() or "127.0.0.1"
    try:
        local_port = int(os.getenv("DB_PORT", "3307"))
    except ValueError:
        local_port = 3307

    os.environ["DATABASE_URL"] = str(parsed.set(host=local_host, port=local_port))


_resolve_database_url_for_runtime()

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

PEXELS_SEARCH_URL = "https://api.pexels.com/v1/search"
PENDING_REVIEW_NOTE = "Ảnh lấy từ Pexels, cần admin kiểm duyệt"

VI_TO_EN_QUERY = {
    "banh quy bo sua": "butter cookies",
    "banh quy": "cookies",
    "banh bong lan": "sponge cake",
    "banh mi trang": "white bread",
    "banh mi": "bread",
    "banh cuon": "bread roll",
    "banh bo sua": "butter cake",
    "banh eclair": "eclair pastry",
    "sua dau nanh": "soy milk",
    "sua chua": "yogurt",
    "sua": "milk",
    "thit heo": "pork meat",
    "thit bo": "beef meat",
    "thit ga": "chicken breast",
    "ca hoi": "salmon",
    "ca thu": "mackerel",
    "trung": "egg",
    "ca rot": "carrot",
    "bong cai xanh": "broccoli",
    "rau cai": "mustard greens",
    "ca chua": "tomato",
    "khoai lang": "sweet potato",
    "khoai tay": "potato",
    "chuoi": "banana",
    "tao": "apple",
    "cam": "orange fruit",
    "dau tay": "strawberry",
    "dau phu": "tofu",
    "yen mach": "oatmeal",
    "gao lut": "brown rice",
    "ot chuong": "bell pepper",
    "rau bina": "spinach",
    "uc ga": "chicken breast",
}

OPTIONAL_CREDIT_COLUMNS = {
    "image_credit": "photographer",
    "image_source_url": "source_url",
    "image_license": "license",
}

APPROVED_IMAGE_STATUSES = {"approved", "accepted", "active"}
REJECTED_IMAGE_STATUSES = {"rejected", "declined", "hidden"}
PENDING_IMAGE_STATUSES = {"pending", "needs_review", "review"}


logger = logging.getLogger("fetch_pexels_food_images")


@dataclass(frozen=True)
class PexelsImage:
    image_url: str
    photographer: str | None
    source_url: str | None


@dataclass(frozen=True)
class FoodImageState:
    image_status: str
    image_source_type: str
    image_url: str | None
    has_verified_image: bool
    has_pending_review: bool
    has_rejected_image: bool
    has_valid_name: bool


def normalize_vi(value: str) -> str:
    text = unicodedata.normalize("NFD", value.strip().lower())
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    return text.replace("đ", "d")


def display_name(food: Food) -> str | None:
    for value in (
        food.dish_name_vi,
        food.name_vi,
        food.display_name,
        food.name,
        food.original_name,
    ):
        text = str(value or "").strip()
        if text:
            return text
    return None


def normalize_image_status(status: Any) -> str:
    return str(status or "").strip().lower()


def is_approved_status(status: Any) -> bool:
    return normalize_image_status(status) in APPROVED_IMAGE_STATUSES


def is_rejected_status(status: Any) -> bool:
    normalized = normalize_image_status(status)
    if normalized in REJECTED_IMAGE_STATUSES:
        return True
    return "tu choi" in normalized or "từ chối" in normalized


def is_pending_status(status: Any) -> bool:
    normalized = normalize_image_status(status)
    return normalized in PENDING_IMAGE_STATUSES


def get_food_image_state(food: Food) -> FoodImageState:
    direct_status = normalize_image_status(getattr(food, "image_status", None))
    source_type = normalize_image_status(getattr(food, "image_source_type", None))
    quality_note = normalize_image_status(getattr(food, "image_quality_note", None))
    image_url = getattr(food, "image_url", None)
    has_verified_image = bool(getattr(food, "image_verified", False)) or is_approved_status(direct_status)
    has_rejected_image = source_type == "rejected" or is_rejected_status(direct_status) or is_rejected_status(quality_note)
    has_pending_review = source_type == "pexels" and not has_verified_image or is_pending_status(direct_status)
    has_valid_name = bool(display_name(food))

    image_status = direct_status
    if not image_status:
        if has_rejected_image:
            image_status = "rejected"
        elif has_verified_image:
            image_status = "approved"
        elif has_pending_review:
            image_status = "pending"
        elif not image_url:
            image_status = "missing"
        else:
            image_status = source_type or "unknown"

    return FoodImageState(
        image_status=image_status,
        image_source_type=source_type,
        image_url=image_url,
        has_verified_image=has_verified_image,
        has_pending_review=has_pending_review,
        has_rejected_image=has_rejected_image,
        has_valid_name=has_valid_name,
    )


def is_food_eligible_for_auto_fetch(food: Food, *, include_rejected: bool = False) -> tuple[bool, str]:
    state = get_food_image_state(food)
    if bool(getattr(food, "excluded_from_recommendation", False)) or bool(getattr(food, "admin_rejected", False)):
        return False, "excluded food"
    if str(getattr(food, "status", "") or "").strip().lower() in {"rejected", "hidden", "inactive", "disabled", "admin_rejected"}:
        return False, "excluded food"

    if state.has_verified_image:
        return False, "already verified"

    if state.has_pending_review:
        return False, "already pending review"

    if state.has_rejected_image and not include_rejected:
        return False, "rejected image"

    if not state.has_valid_name:
        return False, "missing valid name"

    return True, "eligible"


def rejection_marker_condition(food_model: Any) -> Any:
    note_text = func.lower(func.coalesce(food_model.image_quality_note, ""))
    return or_(
        food_model.image_source_type == "rejected",
        note_text.like("%rejected%"),
        note_text.like("%declined%"),
        note_text.like("%tu choi%"),
        note_text.like("%từ chối%"),
    )


def build_auto_fetch_food_conditions(
    food_model: Any,
    *,
    include_rejected: bool = False,
    eligible_only: bool = True,
) -> list[Any]:
    conditions: list[Any] = [
        or_(
            food_model.dish_name_vi.is_not(None),
            food_model.name_vi.is_not(None),
            food_model.display_name.is_not(None),
            food_model.name.is_not(None),
            food_model.original_name.is_not(None),
        ),
        or_(food_model.image_verified.is_(False), food_model.image_verified.is_(None)),
        or_(food_model.image_source_type.is_(None), food_model.image_source_type != "real"),
        or_(food_model.image_source_type.is_(None), food_model.image_source_type != "pexels"),
    ]

    if eligible_only:
        conditions.append(food_model.menu_eligible.is_(True))
        if hasattr(food_model, "excluded_from_recommendation"):
            conditions.append(or_(food_model.excluded_from_recommendation.is_(False), food_model.excluded_from_recommendation.is_(None)))
        if hasattr(food_model, "admin_rejected"):
            conditions.append(or_(food_model.admin_rejected.is_(False), food_model.admin_rejected.is_(None)))

    if not include_rejected:
        conditions.append(or_(food_model.image_source_type.is_(None), food_model.image_source_type != "rejected"))
        conditions.append(~rejection_marker_condition(food_model))

    return conditions


def build_auto_fetch_food_query(
    food_model: Any,
    *,
    include_rejected: bool = False,
    eligible_only: bool = True,
) -> Any:
    return select(food_model).where(*build_auto_fetch_food_conditions(food_model, include_rejected=include_rejected, eligible_only=eligible_only))


def count_auto_fetch_foods(db, food_model: Any, *, include_rejected: bool = False, eligible_only: bool = True) -> int:
    eligible_query = build_auto_fetch_food_query(
        food_model,
        include_rejected=include_rejected,
        eligible_only=eligible_only,
    )
    eligible_subq = eligible_query.with_only_columns(food_model.food_id).order_by(None).subquery()
    return int(db.scalar(select(func.count()).select_from(eligible_subq)) or 0)


def build_search_query(name: str, *, skip_unmapped: bool = False) -> str | None:
    normalized = normalize_vi(name)
    for vi_name, english_query in sorted(VI_TO_EN_QUERY.items(), key=lambda item: len(item[0]), reverse=True):
        if vi_name in normalized:
            return english_query
    if skip_unmapped:
        return None
    return name.strip() or None


def fetch_pexels_image(api_key: str, query: str, *, per_page: int, timeout: float) -> PexelsImage | None:
    params = urllib.parse.urlencode(
        {
            "query": query,
            "per_page": max(1, min(per_page, 10)),
            "orientation": "landscape",
        }
    )
    request = urllib.request.Request(
        f"{PEXELS_SEARCH_URL}?{params}",
        headers={
            "Authorization": api_key,
            "User-Agent": "NutriGain/1.0 PexelsImageReviewScript",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        logger.warning("Pexels request failed for query=%r: HTTP %s", query, exc.code)
        return None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        logger.warning("Pexels request failed for query=%r: %s", query, exc)
        return None

    photos = payload.get("photos") if isinstance(payload, dict) else None
    if not photos:
        return None

    photo = photos[0]
    src = photo.get("src") or {}
    image_url = (src.get("medium") or src.get("large") or src.get("original") or "").strip()
    if not image_url:
        return None
    return PexelsImage(
        image_url=image_url,
        photographer=(photo.get("photographer") or "").strip() or None,
        source_url=(photo.get("url") or "").strip() or None,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch food image URLs from the official Pexels API and store them as pending admin review.",
    )
    parser.add_argument(
        "--database-url",
        help="Override DATABASE_URL for this run. Example: mysql+pymysql://user:pass@127.0.0.1:3307/food_recommender",
    )
    parser.add_argument("--limit", type=int, default=50, help="Maximum number of unverified foods to process.")
    parser.add_argument("--food-id", action="append", dest="food_ids", help="Specific food_id to process. Can be used multiple times.")
    parser.add_argument("--name", action="append", dest="names", help="Only process foods whose name contains this text. Can be used multiple times.")
    parser.add_argument("--per-page", type=int, default=1, help="Number of Pexels results to request per food.")
    parser.add_argument("--timeout", type=float, default=12.0, help="Pexels request timeout in seconds.")
    parser.add_argument("--sleep", type=float, default=0.25, help="Delay between Pexels requests in seconds.")
    parser.add_argument("--offset", type=int, default=0, help="Offset eligible foods before processing.")
    parser.add_argument("--skip-unmapped", action="store_true", help="Skip foods that do not have a Vietnamese-to-English query mapping.")
    parser.add_argument("--eligible-only", action="store_true", default=True, help="Only process foods with menu_eligible=1. Enabled by default.")
    parser.add_argument("--all-foods", action="store_true", help="Process all unverified foods, including menu_eligible=0.")
    parser.add_argument(
        "--include-rejected",
        action="store_true",
        help="Allow fetching new images for foods whose previous images were rejected.",
    )
    parser.add_argument("--refresh-pending", action="store_true", help="Refresh existing image_source_type='pexels' rows that are still unverified.")
    parser.add_argument("--dry-run", action="store_true", help="Call Pexels and print matches without updating the database.")
    parser.add_argument("--stats-only", action="store_true", help="Only print current image stats. Does not require PEXELS_API_KEY.")
    return parser.parse_args()


def import_db() -> tuple[Any, Any, Any]:
    if str(BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(BACKEND_DIR))

    from app.core.database import SessionLocal, engine  # noqa: E402
    from app.models.entities import Food  # noqa: E402

    return SessionLocal, engine, Food


def mask_database_url(database_url: str) -> str:
    if not database_url:
        return "<not set>"
    try:
        parsed = make_url(database_url)
    except Exception:
        return "<invalid DATABASE_URL>"
    if parsed.password:
        parsed = parsed.set(password="***")
    return str(parsed)


def suggest_database_fix(database_url: str) -> None:
    masked_url = mask_database_url(database_url)
    print("Cannot read foods from database.")
    print(f"DATABASE_URL: {masked_url}")
    print("If you are running locally on Windows:")
    print("- Check docker compose ps")
    print("- Check MySQL port 3307")
    print("- Check MYSQL_USER / MYSQL_PASSWORD in docker-compose.yml")
    print("- You can override with:")
    print("  mysql+pymysql://nutrigain:<password>@127.0.0.1:3307/food_recommender")
    print("If you are not sure about credentials, run this script inside the backend container instead.")


def bootstrap_database_url() -> str | None:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--database-url")
    known_args, _ = parser.parse_known_args()
    database_url = str(getattr(known_args, "database_url", "") or "").strip()
    if database_url:
        os.environ["DATABASE_URL"] = database_url
        return database_url
    return None


def food_filters(args: argparse.Namespace, food_model: Any) -> list[Any]:
    filters: list[Any] = [
        or_(food_model.image_verified.is_(False), food_model.image_verified.is_(None)),
        or_(food_model.image_source_type.is_(None), food_model.image_source_type != "real"),
        or_(
            food_model.dish_name_vi.is_not(None),
            food_model.name_vi.is_not(None),
            food_model.display_name.is_not(None),
            food_model.name.is_not(None),
            food_model.original_name.is_not(None),
        ),
    ]
    if args.eligible_only and not args.all_foods:
        filters.append(food_model.menu_eligible.is_(True))
        if hasattr(food_model, "excluded_from_recommendation"):
            filters.append(or_(food_model.excluded_from_recommendation.is_(False), food_model.excluded_from_recommendation.is_(None)))
        if hasattr(food_model, "admin_rejected"):
            filters.append(or_(food_model.admin_rejected.is_(False), food_model.admin_rejected.is_(None)))
        if not args.include_rejected:
            filters.append(or_(food_model.image_source_type.is_(None), food_model.image_source_type != "rejected"))
    if not args.refresh_pending:
        filters.append(or_(food_model.image_source_type.is_(None), food_model.image_source_type != "pexels"))
    if args.food_ids:
        filters.append(food_model.food_id.in_([str(item).strip() for item in args.food_ids if str(item).strip()]))
    if args.names:
        name_filters = []
        for raw_name in args.names:
            pattern = f"%{str(raw_name).strip()}%"
            name_filters.extend(
                [
                    food_model.dish_name_vi.ilike(pattern),
                    food_model.name_vi.ilike(pattern),
                    food_model.display_name.ilike(pattern),
                    food_model.name.ilike(pattern),
                    food_model.original_name.ilike(pattern),
                ]
            )
        if name_filters:
            filters.append(or_(*name_filters))
    return filters


def current_stats(db, food_model: Any) -> dict[str, int]:
    total_foods = int(db.scalar(select(func.count(food_model.food_id))) or 0)
    eligible_total = int(db.scalar(select(func.count(food_model.food_id)).where(food_model.menu_eligible.is_(True))) or 0)
    eligible_without_verified = count_auto_fetch_foods(db, food_model, include_rejected=False, eligible_only=True)
    eligible_pexels_pending = int(
        db.scalar(
            select(func.count(food_model.food_id)).where(
                food_model.menu_eligible.is_(True),
                food_model.image_source_type == "pexels",
                or_(food_model.image_verified.is_(False), food_model.image_verified.is_(None)),
            )
        )
        or 0
    )
    pexels_pending = int(
        db.scalar(
            select(func.count(food_model.food_id)).where(
                food_model.image_source_type == "pexels",
                or_(food_model.image_verified.is_(False), food_model.image_verified.is_(None)),
            )
        )
        or 0
    )
    verified = int(db.scalar(select(func.count(food_model.food_id)).where(food_model.image_verified.is_(True))) or 0)
    return {
        "total_foods": total_foods,
        "eligible_total": eligible_total,
        "eligible_without_verified_image": eligible_without_verified,
        "eligible_pexels_pending": eligible_pexels_pending,
        "pexels_pending": pexels_pending,
        "verified": verified,
    }


def print_stats(stats: dict[str, int]) -> None:
    print(f"Total foods: {stats['total_foods']}")
    print(f"Eligible foods total: {stats['eligible_total']}")
    print(f"Eligible foods without verified image: {stats['eligible_without_verified_image']}")
    print(f"Eligible Pexels pending review: {stats['eligible_pexels_pending']}")
    print(f"Pexels pending review: {stats['pexels_pending']}")
    print(f"Verified images: {stats['verified']}")


def reflected_food_table(engine: Any) -> tuple[Table, set[str]]:
    inspector = inspect(engine)
    columns = {column["name"] for column in inspector.get_columns("foods")}
    table = Table("foods", MetaData(), autoload_with=engine)
    return table, columns


def short_error(exc: Exception) -> str:
    return str(exc).splitlines()[0]


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    bootstrap_database_url()
    args = parse_args()

    if args.database_url:
        os.environ["DATABASE_URL"] = args.database_url.strip()

    SessionLocal, engine, Food = import_db()

    with SessionLocal() as db:
        if args.stats_only:
            try:
                stats = current_stats(db, Food)
            except SQLAlchemyError as exc:
                logger.error("Cannot read image stats from database. %s", short_error(exc))
                suggest_database_fix(os.getenv("DATABASE_URL", ""))
                return 1
            print_stats(stats)
            return 0

        api_key = os.getenv("PEXELS_API_KEY", "").strip()
        if not api_key:
            logger.error(
                "Missing PEXELS_API_KEY. Set it in the environment before running this script; no data was changed."
            )
            return 2

        limit = max(1, int(args.limit or 50))
        offset = max(0, int(args.offset or 0))
        try:
            eligible_only = bool(args.eligible_only and not args.all_foods)
            eligible_query = build_auto_fetch_food_query(
                Food,
                include_rejected=args.include_rejected,
                eligible_only=eligible_only,
            )
            if args.food_ids:
                food_ids = [str(item).strip() for item in args.food_ids if str(item).strip()]
                if food_ids:
                    eligible_query = eligible_query.where(Food.food_id.in_(food_ids))
            if args.names:
                name_filters = []
                for raw_name in args.names:
                    pattern = f"%{str(raw_name).strip()}%"
                    name_filters.extend(
                        [
                            Food.dish_name_vi.ilike(pattern),
                            Food.name_vi.ilike(pattern),
                            Food.display_name.ilike(pattern),
                            Food.name.ilike(pattern),
                            Food.original_name.ilike(pattern),
                        ]
                    )
                if name_filters:
                    eligible_query = eligible_query.where(or_(*name_filters))
            eligible_subq = eligible_query.with_only_columns(Food.food_id).order_by(None).subquery()
            eligible_total = int(db.scalar(select(func.count()).select_from(eligible_subq)) or 0)
            foods = list(db.scalars(eligible_query.order_by(Food.food_id.asc()).offset(offset).limit(limit)))
            food_table, columns = reflected_food_table(engine)
        except SQLAlchemyError as exc:
            logger.error("Cannot read foods from database. %s", short_error(exc))
            suggest_database_fix(os.getenv("DATABASE_URL", ""))
            return 1

        updated = 0
        skipped_no_query = 0
        skipped_no_photo = 0
        skipped_rejected = 0
        skipped_excluded = 0
        skipped_approved = 0
        skipped_pending = 0
        skipped_no_name = 0

        print(f"Eligible foods selected for this run: {len(foods)} / {eligible_total}")
        if eligible_total > 0 and not foods:
            logger.warning("[WARN] Eligible total > 0 but selected batch is empty. Check query/limit/offset.")

        for food in foods:
            name = display_name(food)
            eligible, reason = is_food_eligible_for_auto_fetch(food, include_rejected=args.include_rejected)
            if not eligible:
                if reason == "already verified":
                    skipped_approved += 1
                    logger.info("[SKIP APPROVED] food_id=%s name=%r reason=%s", food.food_id, name or "", reason)
                elif reason == "already pending review":
                    skipped_pending += 1
                    logger.info("[SKIP PENDING] food_id=%s name=%r reason=%s", food.food_id, name or "", reason)
                elif reason == "rejected image":
                    skipped_rejected += 1
                    logger.info("[SKIP REJECTED] food_id=%s name=%r reason=%s", food.food_id, name or "", reason)
                elif reason == "excluded food":
                    skipped_excluded += 1
                    logger.info("[SKIP EXCLUDED FOOD] food_id=%s name=%r reason=%s", food.food_id, name or "", reason)
                elif reason == "missing valid name":
                    skipped_no_name += 1
                    logger.info("Skip %s: %s", food.food_id, reason)
                else:
                    logger.info("Skip %s (%s): %s", food.food_id, name or "", reason)
                continue

            if not name:
                skipped_no_name += 1
                logger.info("Skip %s: no valid food name", food.food_id)
                continue

            logger.info("[FETCH ELIGIBLE] food_id=%s name=%r", food.food_id, name)

            query = build_search_query(name, skip_unmapped=args.skip_unmapped)
            if not query:
                skipped_no_query += 1
                logger.info("Skip %s (%s): no mapped query", food.food_id, name)
                continue

            image = fetch_pexels_image(api_key, query, per_page=args.per_page, timeout=args.timeout)
            if image is None:
                skipped_no_photo += 1
                logger.warning("Skip %s (%s): no Pexels photo for query=%r", food.food_id, name, query)
                time.sleep(max(0.0, args.sleep))
                continue

            values: dict[str, Any] = {
                "image_url": image.image_url,
                "image_alt_vi": name,
                "image_source_type": "pexels",
                "image_verified": False,
                "image_quality_note": PENDING_REVIEW_NOTE,
            }
            optional_values = {
                "photographer": image.photographer,
                "source_url": image.source_url,
                "license": "Pexels",
            }
            for column_name, value_key in OPTIONAL_CREDIT_COLUMNS.items():
                if column_name in columns:
                    values[column_name] = optional_values[value_key]

            if args.dry_run:
                updated += 1
                logger.info("Dry run: %s (%s) <= %s", food.food_id, name, image.image_url)
            else:
                try:
                    update_conditions = [
                        or_(food_table.c.image_verified.is_(False), food_table.c.image_verified.is_(None)),
                        or_(food_table.c.image_source_type.is_(None), food_table.c.image_source_type != "real"),
                    ]
                    if "excluded_from_recommendation" in columns:
                        update_conditions.append(
                            or_(
                                food_table.c.excluded_from_recommendation.is_(False),
                                food_table.c.excluded_from_recommendation.is_(None),
                            )
                        )
                    if "admin_rejected" in columns:
                        update_conditions.append(
                            or_(
                                food_table.c.admin_rejected.is_(False),
                                food_table.c.admin_rejected.is_(None),
                            )
                        )
                    if not args.include_rejected:
                        update_conditions.append(or_(food_table.c.image_source_type.is_(None), food_table.c.image_source_type != "rejected"))
                    result = db.execute(
                        update(food_table)
                        .where(food_table.c.food_id == food.food_id)
                        .where(*update_conditions)
                        .values(**values)
                    )
                except SQLAlchemyError as exc:
                    db.rollback()
                    logger.error("Cannot update %s. Check database connection/schema. %s", food.food_id, short_error(exc))
                    return 1
                if result.rowcount:
                    db.commit()
                    updated += 1
                    logger.info("Updated %s (%s) from query=%r", food.food_id, name, query)
                else:
                    db.rollback()
                    skipped_verified += 1
                    logger.info("Skip %s (%s): image became verified before update", food.food_id, name)

            time.sleep(max(0.0, args.sleep))

        try:
            stats = current_stats(db, Food)
        except SQLAlchemyError as exc:
            logger.warning("Could not read final image stats. %s", short_error(exc))
            stats = {
                "total_foods": -1,
                "eligible_total": -1,
                "eligible_without_verified_image": -1,
                "eligible_pexels_pending": -1,
                "pexels_pending": -1,
                "verified": -1,
            }
        action = "Matched" if args.dry_run else "Assigned"
        print(f"Foods scanned: {len(foods)}")
        print(f"{action} Pexels images this run: {updated}")
        print(f"Skipped without valid name: {skipped_no_name}")
        print(f"Skipped without query: {skipped_no_query}")
        print(f"Skipped without Pexels photo/request failed: {skipped_no_photo}")
        print(f"Skipped rejected: {skipped_rejected}")
        print(f"Skipped excluded foods: {skipped_excluded}")
        print(f"Skipped approved: {skipped_approved}")
        print(f"Skipped pending review: {skipped_pending}")
        print_stats(stats)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
