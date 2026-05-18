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

from sqlalchemy import MetaData, Table, and_, func, inspect, or_, select, update
from sqlalchemy.exc import SQLAlchemyError


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.database import SessionLocal, engine  # noqa: E402
from app.models.entities import Food  # noqa: E402


PEXELS_SEARCH_URL = "https://api.pexels.com/v1/search"
PENDING_REVIEW_NOTE = "Ảnh lấy từ Pexels, cần admin kiểm duyệt"

VI_TO_EN_QUERY = {
    "dau phu": "tofu",
    "sua dau nanh": "soy milk",
    "khoai lang": "sweet potato",
    "yen mach": "oatmeal",
    "gao lut": "brown rice",
    "banh quy bo sua": "butter cookies",
    "chuoi": "banana",
    "tao": "apple",
    "dau tay": "strawberry",
    "bong cai xanh": "broccoli",
    "ca chua": "tomato",
    "ot chuong": "bell pepper",
    "rau bina": "spinach",
    "trung": "egg",
    "uc ga": "chicken breast",
    "ca hoi": "salmon",
}

OPTIONAL_CREDIT_COLUMNS = {
    "image_credit": "photographer",
    "image_source_url": "source_url",
    "image_license": "license",
}


logger = logging.getLogger("fetch_pexels_food_images")


@dataclass(frozen=True)
class PexelsImage:
    image_url: str
    photographer: str | None
    source_url: str | None


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
    parser.add_argument("--limit", type=int, default=50, help="Maximum number of unverified foods to process.")
    parser.add_argument("--food-id", action="append", dest="food_ids", help="Specific food_id to process. Can be used multiple times.")
    parser.add_argument("--name", action="append", dest="names", help="Only process foods whose name contains this text. Can be used multiple times.")
    parser.add_argument("--per-page", type=int, default=1, help="Number of Pexels results to request per food.")
    parser.add_argument("--timeout", type=float, default=12.0, help="Pexels request timeout in seconds.")
    parser.add_argument("--sleep", type=float, default=0.25, help="Delay between Pexels requests in seconds.")
    parser.add_argument("--skip-unmapped", action="store_true", help="Skip foods that do not have a Vietnamese-to-English query mapping.")
    parser.add_argument("--eligible-only", action="store_true", default=True, help="Only process foods with menu_eligible=1. Enabled by default.")
    parser.add_argument("--all-foods", action="store_true", help="Process all unverified foods, including menu_eligible=0.")
    parser.add_argument("--refresh-pending", action="store_true", help="Refresh existing image_source_type='pexels' rows that are still unverified.")
    parser.add_argument("--dry-run", action="store_true", help="Call Pexels and print matches without updating the database.")
    parser.add_argument("--stats-only", action="store_true", help="Only print current image stats. Does not require PEXELS_API_KEY.")
    return parser.parse_args()


def food_filters(args: argparse.Namespace) -> list[Any]:
    filters: list[Any] = [
        or_(Food.image_verified.is_(False), Food.image_verified.is_(None)),
        or_(Food.image_source_type.is_(None), Food.image_source_type != "real"),
        or_(
            Food.dish_name_vi.is_not(None),
            Food.name_vi.is_not(None),
            Food.display_name.is_not(None),
            Food.name.is_not(None),
            Food.original_name.is_not(None),
        ),
    ]
    if args.eligible_only and not args.all_foods:
        filters.append(Food.menu_eligible.is_(True))
    if not args.refresh_pending:
        filters.append(or_(Food.image_source_type.is_(None), Food.image_source_type != "pexels"))
    if args.food_ids:
        filters.append(Food.food_id.in_([str(item).strip() for item in args.food_ids if str(item).strip()]))
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
            filters.append(or_(*name_filters))
    return filters


def current_stats(db) -> dict[str, int]:
    eligible_unverified_filter = and_(
        Food.menu_eligible.is_(True),
        or_(Food.image_verified.is_(False), Food.image_verified.is_(None)),
        or_(Food.image_source_type.is_(None), Food.image_source_type != "real"),
    )
    total_foods = int(db.scalar(select(func.count(Food.food_id))) or 0)
    eligible_total = int(db.scalar(select(func.count(Food.food_id)).where(Food.menu_eligible.is_(True))) or 0)
    eligible_without_verified = int(db.scalar(select(func.count(Food.food_id)).where(eligible_unverified_filter)) or 0)
    eligible_pexels_pending = int(
        db.scalar(
            select(func.count(Food.food_id)).where(
                Food.menu_eligible.is_(True),
                Food.image_source_type == "pexels",
                or_(Food.image_verified.is_(False), Food.image_verified.is_(None)),
            )
        )
        or 0
    )
    pexels_pending = int(
        db.scalar(
            select(func.count(Food.food_id)).where(
                Food.image_source_type == "pexels",
                or_(Food.image_verified.is_(False), Food.image_verified.is_(None)),
            )
        )
        or 0
    )
    verified = int(db.scalar(select(func.count(Food.food_id)).where(Food.image_verified.is_(True))) or 0)
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


def reflected_food_table() -> tuple[Table, set[str]]:
    inspector = inspect(engine)
    columns = {column["name"] for column in inspector.get_columns("foods")}
    table = Table("foods", MetaData(), autoload_with=engine)
    return table, columns


def short_error(exc: Exception) -> str:
    return str(exc).splitlines()[0]


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = parse_args()

    with SessionLocal() as db:
        if args.stats_only:
            try:
                stats = current_stats(db)
            except SQLAlchemyError as exc:
                logger.error("Cannot read image stats from database. Check DATABASE_URL/MySQL status. %s", short_error(exc))
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
        try:
            foods = list(
                db.scalars(
                    select(Food)
                    .where(*food_filters(args))
                    .order_by(Food.food_id.asc())
                    .limit(limit)
                )
            )
            food_table, columns = reflected_food_table()
        except SQLAlchemyError as exc:
            logger.error("Cannot read foods from database. Check DATABASE_URL/MySQL status. %s", short_error(exc))
            return 1

        updated = 0
        skipped_no_query = 0
        skipped_no_photo = 0
        skipped_verified = 0
        skipped_no_name = 0

        for food in foods:
            name = display_name(food)
            if not name:
                skipped_no_name += 1
                logger.info("Skip %s: no valid food name", food.food_id)
                continue
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
                    result = db.execute(
                        update(food_table)
                        .where(food_table.c.food_id == food.food_id)
                        .where(or_(food_table.c.image_verified.is_(False), food_table.c.image_verified.is_(None)))
                        .where(or_(food_table.c.image_source_type.is_(None), food_table.c.image_source_type != "real"))
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
            stats = current_stats(db)
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
        print(f"Skipped because already verified during run: {skipped_verified}")
        print_stats(stats)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
