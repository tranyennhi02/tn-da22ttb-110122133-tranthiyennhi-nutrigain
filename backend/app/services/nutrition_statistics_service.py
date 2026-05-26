from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.entities import Food, FoodLog, FoodLogItem, Meal, MealConsumptionLog, MealPlanItem


class NutritionStatisticsService:
    VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
    UTC = timezone.utc
    MEAL_LABELS = {
        "breakfast": "Bữa sáng",
        "lunch": "Bữa trưa",
        "dinner": "Bữa tối",
    }
    MEAL_ORDER = ["breakfast", "lunch", "dinner"]

    def _to_number(self, value, default: float = 0.0) -> float:
        try:
            if value is None:
                return float(default)
            return float(value)
        except (TypeError, ValueError):
            return float(default)

    def _normalize_meal_type(self, meal_type: str | None) -> str:
        key = str(meal_type or "").strip().lower()
        return key if key in self.MEAL_ORDER else ""

    def _meal_label(self, meal_type: str | None) -> str:
        return self.MEAL_LABELS.get(self._normalize_meal_type(meal_type), "Bữa ăn")

    def _parse_date(self, value: str | None, fallback: date | None = None) -> date:
        if value:
            try:
                return datetime.strptime(value, "%Y-%m-%d").date()
            except ValueError:
                pass
        return fallback or self._local_now().date()

    def _parse_month(self, value: str | None) -> tuple[int, int]:
        source = value or self._local_now().strftime("%Y-%m")
        try:
            year_text, month_text = source.split("-")
            return int(year_text), int(month_text)
        except (TypeError, ValueError):
            now = self._local_now()
            return now.year, now.month

    def _parse_year(self, value: str | None) -> int:
        try:
            return int(value) if value else self._local_now().year
        except (TypeError, ValueError):
            return self._local_now().year

    def _history_totals(self, items: list[dict]) -> dict:
        return {
            "calories": round(sum(self._to_number(item.get("calories")) for item in items), 2),
            "protein": round(sum(self._to_number(item.get("protein")) for item in items), 2),
            "fat": round(sum(self._to_number(item.get("fat")) for item in items), 2),
            "carbs": round(sum(self._to_number(item.get("carbs")) for item in items), 2),
        }

    def _history_food_name(self, food: Food | None, meal_item: MealPlanItem | None, fallback: str | None = None) -> str:
        return (
            getattr(food, "display_name", None)
            or getattr(food, "dish_name_vi", None)
            or getattr(food, "name_vi", None)
            or getattr(food, "name", None)
            or getattr(meal_item, "reason", None)
            or fallback
            or "Món ăn"
        )

    def _history_serving_display(self, food: Food | None, meal_item: MealPlanItem | None) -> str:
        return (
            getattr(meal_item, "serving_display", None)
            or getattr(food, "serving_display", None)
            or getattr(food, "portion_display", None)
            or "Theo kế hoạch"
        )

    def _history_image_url(self, food: Food | None, meal_item: MealPlanItem | None) -> str | None:
        return (
            getattr(meal_item, "image_url", None)
            or getattr(food, "image_url", None)
            or getattr(food, "image", None)
            or None
        )

    def get_eating_history(
        self,
        db: Session,
        user,
        mode: str = "day",
        date_value: str | None = None,
        month_value: str | None = None,
        year_value: str | None = None,
    ) -> dict:
        normalized_mode = mode if mode in {"day", "month", "year"} else "day"
        query = (
            db.query(FoodLogItem, FoodLog, MealPlanItem, Meal, Food)
            .join(FoodLog, FoodLogItem.food_log_id == FoodLog.id)
            .outerjoin(MealPlanItem, FoodLogItem.meal_plan_item_id == MealPlanItem.id)
            .outerjoin(Meal, MealPlanItem.meal_id == Meal.id)
            .outerjoin(Food, Food.food_id == FoodLogItem.food_id)
            .filter(FoodLog.user_id == user.id)
            .filter(FoodLogItem.status == "eaten")
            .filter(FoodLogItem.meal_type.in_(self.MEAL_ORDER))
        )

        if normalized_mode == "day":
            target_date = self._parse_date(date_value)
            query = query.filter(FoodLog.log_date == target_date)
        elif normalized_mode == "month":
            target_year, target_month = self._parse_month(month_value)
            query = query.filter(func.extract("year", FoodLog.log_date) == target_year).filter(func.extract("month", FoodLog.log_date) == target_month)
        else:
            target_year = self._parse_year(year_value)
            query = query.filter(func.extract("year", FoodLog.log_date) == target_year)

        items: list[dict] = []
        seen_keys: set[tuple] = set()
        rows = query.order_by(FoodLog.log_date.asc(), FoodLogItem.created_at.asc(), FoodLogItem.id.asc()).all()
        for log_item, food_log, meal_item, meal, food in rows:
            meal_type = self._normalize_meal_type(log_item.meal_type or getattr(meal, "meal_type", None))
            if meal_type not in self.MEAL_ORDER:
                continue
            eaten_at = log_item.updated_at or log_item.created_at or datetime.combine(food_log.log_date, time.min)
            meal_plan_id = getattr(meal, "meal_plan_id", None)
            key = (food_log.log_date.isoformat(), meal_plan_id, meal_type, log_item.meal_plan_item_id, str(log_item.food_id or ""))
            seen_keys.add(key)
            items.append({
                "id": log_item.meal_plan_item_id or log_item.id,
                "meal_plan_id": meal_plan_id,
                "meal_plan_item_id": log_item.meal_plan_item_id,
                "meal_type": meal_type,
                "meal_title": self._meal_label(meal_type),
                "food_id": str(log_item.food_id or getattr(meal_item, "food_id", "") or ""),
                "name": self._history_food_name(food, meal_item, log_item.custom_name),
                "serving_display": self._history_serving_display(food, meal_item),
                "calories": round(self._to_number(log_item.kcal or getattr(meal_item, "kcal", 0.0)), 2),
                "protein": round(self._to_number(log_item.protein or getattr(meal_item, "protein", 0.0)), 2),
                "fat": round(self._to_number(log_item.fat or getattr(meal_item, "fat", 0.0)), 2),
                "carbs": round(self._to_number(log_item.carbs or getattr(meal_item, "carbs", 0.0)), 2),
                "image_url": self._history_image_url(food, meal_item),
                "eaten_date": food_log.log_date.isoformat(),
                "eaten_at": eaten_at.isoformat() if eaten_at else None,
            })

        log_query = (
            db.query(MealConsumptionLog, MealPlanItem, Meal, Food)
            .outerjoin(Meal, (MealConsumptionLog.meal_plan_id == Meal.meal_plan_id) & (func.lower(Meal.meal_type) == func.lower(MealConsumptionLog.meal_type)))
            .outerjoin(MealPlanItem, (MealPlanItem.meal_id == Meal.id) & (MealPlanItem.food_id == MealConsumptionLog.food_id))
            .outerjoin(Food, Food.food_id == MealConsumptionLog.food_id)
            .filter(MealConsumptionLog.user_id == user.id)
            .filter(MealConsumptionLog.status == "eaten")
            .filter(MealConsumptionLog.meal_type.in_(self.MEAL_ORDER))
        )

        if normalized_mode == "day":
            target_date = self._parse_date(date_value)
            log_query = log_query.filter(func.date(MealConsumptionLog.consumed_at) == target_date)
        elif normalized_mode == "month":
            target_year, target_month = self._parse_month(month_value)
            log_query = log_query.filter(func.extract("year", MealConsumptionLog.consumed_at) == target_year).filter(func.extract("month", MealConsumptionLog.consumed_at) == target_month)
        else:
            target_year = self._parse_year(year_value)
            log_query = log_query.filter(func.extract("year", MealConsumptionLog.consumed_at) == target_year)

        for log, meal_item, meal, food in log_query.order_by(MealConsumptionLog.consumed_at.asc(), MealConsumptionLog.id.asc()).all():
            meal_type = self._normalize_meal_type(log.meal_type or getattr(meal, "meal_type", None))
            if meal_type not in self.MEAL_ORDER:
                continue
            eaten_at = log.consumed_at or log.created_at
            eaten_date = eaten_at.date() if eaten_at else self._local_now().date()
            key = (eaten_date.isoformat(), log.meal_plan_id, meal_type, getattr(meal_item, "id", None), str(log.food_id or ""))
            if key in seen_keys:
                continue
            items.append({
                "id": getattr(meal_item, "id", None) or log.id,
                "meal_plan_id": log.meal_plan_id,
                "meal_plan_item_id": getattr(meal_item, "id", None),
                "meal_type": meal_type,
                "meal_title": self._meal_label(meal_type),
                "food_id": str(log.food_id or getattr(meal_item, "food_id", "") or ""),
                "name": self._history_food_name(food, meal_item, str(log.food_id or "")),
                "serving_display": self._history_serving_display(food, meal_item),
                "calories": round(self._to_number(log.kcal or getattr(meal_item, "kcal", 0.0)), 2),
                "protein": round(self._to_number(log.protein or getattr(meal_item, "protein", 0.0)), 2),
                "fat": round(self._to_number(getattr(meal_item, "fat", 0.0)), 2),
                "carbs": round(self._to_number(getattr(meal_item, "carbs", 0.0)), 2),
                "image_url": self._history_image_url(food, meal_item),
                "eaten_date": eaten_date.isoformat(),
                "eaten_at": eaten_at.isoformat() if eaten_at else None,
            })

        items.sort(key=lambda item: (item.get("eaten_date") or "", item.get("eaten_at") or "", item.get("meal_type") or ""))
        return {
            "items": items,
            "totals": self._history_totals(items),
        }

    def _local_now(self) -> datetime:
        return datetime.now(self.VN_TZ)

    def _localize(self, value: datetime | None) -> datetime:
        if value is None:
            return self._local_now()
        if value.tzinfo is None:
            return value.replace(tzinfo=self.UTC).astimezone(self.VN_TZ)
        return value.astimezone(self.VN_TZ)

    def _range_bounds(self, target_range: str) -> tuple[datetime, datetime, date, date]:
        now_vn = self._local_now()
        if target_range == "today":
            start_local = datetime.combine(now_vn.date(), time.min, tzinfo=self.VN_TZ)
            end_local = start_local + timedelta(days=1)
        elif target_range == "month":
            start_local = datetime(now_vn.year, now_vn.month, 1, tzinfo=self.VN_TZ)
            end_local = datetime(now_vn.year + (1 if now_vn.month == 12 else 0), 1 if now_vn.month == 12 else now_vn.month + 1, 1, tzinfo=self.VN_TZ)
        else:
            start_local = datetime(now_vn.year, 1, 1, tzinfo=self.VN_TZ)
            end_local = datetime(now_vn.year + 1, 1, 1, tzinfo=self.VN_TZ)

        start_utc = start_local.astimezone(self.UTC).replace(tzinfo=None)
        end_utc = end_local.astimezone(self.UTC).replace(tzinfo=None)
        return start_utc, end_utc, start_local.date(), end_local.date()

    def _create_meal_bucket(self, meal_type: str) -> dict:
        return {
            "label": self._meal_label(meal_type),
            "kcal": 0.0,
            "protein": 0.0,
            "carbs": 0.0,
            "fat": 0.0,
            "items_count": 0,
            "items": [],
        }

    def _create_day_bucket(self, local_date: date) -> dict:
        return {
            "date": local_date.isoformat(),
            "label": local_date.strftime("%d/%m/%Y"),
            "kcal": 0.0,
            "protein": 0.0,
            "carbs": 0.0,
            "fat": 0.0,
            "items_count": 0,
            "meals": {meal_type: self._create_meal_bucket(meal_type) for meal_type in self.MEAL_ORDER},
        }

    def _create_month_bucket(self, month_key: str) -> dict:
        year_text, month_text = month_key.split("-")
        return {
            "month": month_key,
            "label": f"Tháng {int(month_text)}/{year_text}",
            "kcal": 0.0,
            "protein": 0.0,
            "carbs": 0.0,
            "fat": 0.0,
            "items_count": 0,
            "days_count": 0,
            "days": [],
        }

    def _resolve_consumed_item(self, db: Session, log: MealConsumptionLog) -> dict:
        local_dt = self._localize(self._resolve_timestamp(log))
        meal_type = self._normalize_meal_type(log.meal_type)
        meal_item = None
        food = None

        if log.meal_plan_id and log.food_id:
            meal_item = (
                db.query(MealPlanItem)
                .join(Meal, MealPlanItem.meal_id == Meal.id)
                .filter(Meal.meal_plan_id == log.meal_plan_id)
                .filter(func.lower(Meal.meal_type) == meal_type)
                .filter(MealPlanItem.food_id == str(log.food_id))
                .order_by(MealPlanItem.item_order.asc(), MealPlanItem.id.asc())
                .first()
            )

        if log.food_id:
            food = db.query(Food).filter(Food.food_id == str(log.food_id)).first()

        kcal = self._to_number(getattr(log, "kcal", None))
        protein = self._to_number(getattr(log, "protein", None))
        carbs = 0.0
        fat = 0.0

        if meal_item is not None:
            kcal = kcal or self._to_number(getattr(meal_item, "kcal", None))
            protein = protein or self._to_number(getattr(meal_item, "protein", None))
            carbs = self._to_number(getattr(meal_item, "carbs", None))
            fat = self._to_number(getattr(meal_item, "fat", None))

        if food is not None:
            kcal = kcal or self._to_number(getattr(food, "calories", None) or getattr(food, "kcal", None) or getattr(food, "energy_kcal", None))
            protein = protein or self._to_number(getattr(food, "protein", None) or getattr(food, "protein_g", None))
            carbs = carbs or self._to_number(getattr(food, "carbs", None) or getattr(food, "carbs_g", None))
            fat = fat or self._to_number(getattr(food, "fat", None) or getattr(food, "fat_g", None))

        grams = self._to_number(getattr(meal_item, "quantity_g", None) or getattr(food, "recommended_serving_g", None), default=0.0)
        portion = (
            getattr(meal_item, "serving_display", None)
            or getattr(food, "serving_display", None)
            or getattr(food, "image_alt_vi", None)
            or ""
        )
        name = (
            getattr(food, "display_name", None)
            or getattr(food, "dish_name_vi", None)
            or getattr(food, "name_vi", None)
            or getattr(food, "name", None)
            or getattr(meal_item, "reason", None)
            or str(log.food_id or "Món ăn")
        )

        return {
            "id": str(getattr(log, "id", None) or getattr(meal_item, "id", None) or log.food_id or f"{local_dt.isoformat()}-{meal_type}"),
            "name": name,
            "portion": portion,
            "grams": grams or None,
            "kcal": round(kcal, 2),
            "protein": round(protein, 2),
            "carbs": round(carbs, 2),
            "fat": round(fat, 2),
            "eaten_at": local_dt.isoformat(),
            "meal_type": meal_type,
            "meal_label": self._meal_label(meal_type),
        }

    def _resolve_timestamp(self, log: MealConsumptionLog) -> datetime:
        return log.consumed_at or log.created_at

    def _empty_response(self, target_range: str) -> dict:
        empty_meals = {meal_type: self._create_meal_bucket(meal_type) for meal_type in self.MEAL_ORDER}
        return {
            "success": True,
            "range": target_range,
            "summary": {
                "total_kcal": 0.0,
                "total_protein": 0.0,
                "total_carbs": 0.0,
                "total_fat": 0.0,
                "meals_count": 0,
                "eaten_items_count": 0,
            },
            "daily": [],
            "monthly": [],
            "meals": empty_meals,
            "message": "Chưa có dữ liệu món đã ăn.",
        }

    def _finalize_day(self, day_bucket: dict) -> dict:
        for meal_bucket in day_bucket["meals"].values():
            meal_bucket["items_count"] = len(meal_bucket["items"])
        day_bucket["items_count"] = sum(meal_bucket["items_count"] for meal_bucket in day_bucket["meals"].values())
        return day_bucket

    def get_statistics(self, db: Session, user, target_range: str = "today") -> dict:
        normalized_range = target_range if target_range in {"today", "month", "year"} else "today"
        start_utc, end_utc, _, _ = self._range_bounds(normalized_range)

        logs = (
            db.query(MealConsumptionLog)
            .filter(MealConsumptionLog.user_id == user.id)
            .filter(MealConsumptionLog.consumed_at >= start_utc)
            .filter(MealConsumptionLog.consumed_at < end_utc)
            .order_by(MealConsumptionLog.consumed_at.asc())
            .all()
        )
        if not logs:
            return self._empty_response(normalized_range)

        daily_index: dict[str, dict] = {}
        month_index: dict[str, dict] = {}
        overall_meals = {meal_type: self._create_meal_bucket(meal_type) for meal_type in self.MEAL_ORDER}
        totals = {"kcal": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0}

        for log in logs:
            item = self._resolve_consumed_item(db, log)
            local_date = self._localize(self._resolve_timestamp(log)).date()
            day_key = local_date.isoformat()
            month_key = local_date.strftime("%Y-%m")
            meal_type = item["meal_type"]

            day_bucket = daily_index.setdefault(day_key, self._create_day_bucket(local_date))
            month_bucket = month_index.setdefault(month_key, self._create_month_bucket(month_key))

            meal_day_bucket = day_bucket["meals"].setdefault(meal_type, self._create_meal_bucket(meal_type))
            meal_month_bucket = month_bucket.setdefault("meals", {}).setdefault(meal_type, self._create_meal_bucket(meal_type))
            meal_overall_bucket = overall_meals.setdefault(meal_type, self._create_meal_bucket(meal_type))

            for bucket in (meal_day_bucket, meal_month_bucket, meal_overall_bucket):
                bucket["kcal"] += item["kcal"]
                bucket["protein"] += item["protein"]
                bucket["carbs"] += item["carbs"]
                bucket["fat"] += item["fat"]
                bucket["items"].append(deepcopy(item))

            for bucket in (day_bucket, month_bucket,):
                bucket["kcal"] += item["kcal"]
                bucket["protein"] += item["protein"]
                bucket["carbs"] += item["carbs"]
                bucket["fat"] += item["fat"]
                bucket["items_count"] += 1

            totals["kcal"] += item["kcal"]
            totals["protein"] += item["protein"]
            totals["carbs"] += item["carbs"]
            totals["fat"] += item["fat"]

        daily = [self._finalize_day(day_bucket) for day_bucket in sorted(daily_index.values(), key=lambda entry: entry["date"])]
        month_buckets = []
        for month_key in sorted(month_index.keys()):
            month_bucket = month_index[month_key]
            month_days = [deepcopy(day) for day in daily if day["date"].startswith(month_key)]
            for day in month_days:
                day["items_count"] = int(day["items_count"])
            month_bucket["days"] = month_days
            month_bucket["days_count"] = len(month_days)
            month_bucket["items_count"] = sum(day["items_count"] for day in month_days)
            month_bucket["kcal"] = sum(day["kcal"] for day in month_days)
            month_bucket["protein"] = sum(day["protein"] for day in month_days)
            month_bucket["carbs"] = sum(day["carbs"] for day in month_days)
            month_bucket["fat"] = sum(day["fat"] for day in month_days)
            month_buckets.append(month_bucket)

        summary = {
            "total_kcal": round(totals["kcal"], 2),
            "total_protein": round(totals["protein"], 2),
            "total_carbs": round(totals["carbs"], 2),
            "total_fat": round(totals["fat"], 2),
            "meals_count": sum(1 for meal_bucket in overall_meals.values() if meal_bucket["items"]),
            "eaten_items_count": sum(len(meal_bucket["items"]) for meal_bucket in overall_meals.values()),
        }

        for meal_bucket in overall_meals.values():
            meal_bucket["items_count"] = len(meal_bucket["items"])
            meal_bucket["kcal"] = round(meal_bucket["kcal"], 2)
            meal_bucket["protein"] = round(meal_bucket["protein"], 2)
            meal_bucket["carbs"] = round(meal_bucket["carbs"], 2)
            meal_bucket["fat"] = round(meal_bucket["fat"], 2)

        if normalized_range == "today" and daily:
            month_buckets = month_buckets[:1]
        elif normalized_range == "month":
            month_buckets = []

        message = "Chưa có dữ liệu món đã ăn." if summary["eaten_items_count"] == 0 else "Thống kê đã được cập nhật."

        return {
            "success": True,
            "range": normalized_range,
            "summary": summary,
            "daily": daily,
            "monthly": month_buckets,
            "meals": overall_meals,
            "message": message,
        }
