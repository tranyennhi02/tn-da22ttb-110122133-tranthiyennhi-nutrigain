from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.entities import Food, Meal, MealConsumptionLog, MealPlanItem


class NutritionStatisticsService:
    VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
    UTC = timezone.utc
    MEAL_LABELS = {
        "breakfast": "Bữa sáng",
        "lunch": "Bữa trưa",
        "dinner": "Bữa tối",
        "snack": "Bữa phụ",
    }
    MEAL_ORDER = ["breakfast", "lunch", "dinner", "snack"]

    def _to_number(self, value, default: float = 0.0) -> float:
        try:
            if value is None:
                return float(default)
            return float(value)
        except (TypeError, ValueError):
            return float(default)

    def _normalize_meal_type(self, meal_type: str | None) -> str:
        key = str(meal_type or "").strip().lower()
        return key if key in self.MEAL_LABELS else "snack"

    def _meal_label(self, meal_type: str | None) -> str:
        return self.MEAL_LABELS.get(self._normalize_meal_type(meal_type), "Bữa ăn")

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
