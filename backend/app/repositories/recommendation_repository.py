from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import bindparam, func, inspect, select, text
from sqlalchemy.orm import Session

from app.models.entities import FoodLog, FoodLogItem, Meal, MealPlan, MealPlanItem, RecommendationRequest


class RecommendationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_request_with_items(
        self,
        request_payload: dict,
        meal_items: list[dict],
    ) -> RecommendationRequest:
        import logging
        logger = logging.getLogger(__name__)

        self._delete_today_meal_plans(int(request_payload["user_id"]))
        request_row = RecommendationRequest(**request_payload)
        self.db.add(request_row)
        self.db.flush()

        logger.info(f"Created recommendation_request_id: {request_row.id}")

        total_kcal = sum(float(item.get("calories") or item.get("kcal") or 0.0) for item in meal_items)
        total_protein = sum(float(item.get("protein") or 0.0) for item in meal_items)
        total_fat = sum(float(item.get("fat") or 0.0) for item in meal_items)
        total_carbs = sum(float(item.get("carbs") or item.get("carb") or 0.0) for item in meal_items)
        
        target_kcal = float(request_payload.get("target_calories") or request_payload.get("target_kcal") or 0.0)

        meal_plan = MealPlan(
            user_id=int(request_payload["user_id"]),
            recommendation_request_id=request_row.id,
            plan_date=datetime.utcnow().date(),
            target_kcal=target_kcal,
            total_kcal=total_kcal,
            total_protein=total_protein,
            total_fat=total_fat,
            total_carbs=total_carbs,
            status="generated",
        )
        self.db.add(meal_plan)
        self.db.flush()

        logger.info(f"Created meal_plan_id: {meal_plan.id}")

        meal_sort_order = {"breakfast": 1, "lunch": 2, "snack": 3, "dinner": 4}
        meal_name_map = {"breakfast": "Bữa sáng", "lunch": "Bữa trưa", "snack": "Bữa phụ", "dinner": "Bữa tối"}

        grouped_items = {}
        for item in meal_items:
            if not isinstance(item, dict):
                logger.warning(f"Item is not a dict, skipping: {item}")
                continue
            meal_type = item.get("meal_type") or item.get("meal") or "meal"
            meal_type = str(meal_type).strip().lower()
            grouped_items.setdefault(meal_type, []).append(item)

        meal_rows: dict[str, Meal] = {}
        for meal_type, meal_type_items in grouped_items.items():
            meal_row = Meal(
                meal_plan_id=meal_plan.id,
                meal_type=meal_type,
                meal_name_vi=meal_name_map.get(meal_type, meal_type.title()),
                total_kcal=sum(float(item.get("calories") or item.get("kcal") or 0.0) for item in meal_type_items),
                total_protein=sum(float(item.get("protein") or 0.0) for item in meal_type_items),
                total_fat=sum(float(item.get("fat") or 0.0) for item in meal_type_items),
                total_carbs=sum(float(item.get("carbs") or item.get("carb") or 0.0) for item in meal_type_items),
                meal_order=meal_sort_order.get(meal_type, 99),
            )
            self.db.add(meal_row)
            self.db.flush()
            meal_rows[meal_type] = meal_row

        logger.info(f"created meals count: {len(meal_rows)}")

        created_items_count = 0
        for meal_type, meal_type_items in grouped_items.items():
            for idx, item in enumerate(meal_type_items):
                item_payload = dict(item)
                
                raw_food_id = str(item_payload.get("food_id", ""))
                actual_food_id = self.db.scalar(text("SELECT id FROM foods WHERE food_id = :food_id LIMIT 1"), {"food_id": raw_food_id})
                
                if actual_food_id is None:
                    logger.warning(f"Could not map food_id {raw_food_id} to foods.id. Skipping item {item_payload.get('name')}")
                    continue

                qty = float(item_payload.get("serving_grams") or item_payload.get("quantity_g") or 0.0)
                
                m_item = MealPlanItem(
                    meal_id=meal_rows[meal_type].id,
                    food_id=str(actual_food_id),
                    meal_role=str(item_payload.get("meal_role", "")),
                    quantity_g=qty if qty > 0 else None,
                    kcal=float(item_payload.get("calories") or item_payload.get("kcal") or 0.0),
                    protein=float(item_payload.get("protein") or 0.0),
                    fat=float(item_payload.get("fat") or 0.0),
                    carbs=float(item_payload.get("carbs") or item_payload.get("carb") or 0.0),
                    serving_display=str(item_payload.get("serving_display") or item_payload.get("portion_display") or ""),
                    reason=str(item_payload.get("reason", "")),
                    image_url=str(item_payload.get("image_url", "")),
                    image_badge=str(item_payload.get("image_badge", "")),
                    item_order=idx,
                )
                self.db.add(m_item)
                created_items_count += 1

        self.db.commit()
        logger.info(f"created meal_plan_items count: {created_items_count}")
        
        if created_items_count == 0:
            raise ValueError("No meal_plan_items were created")
            
        self.db.refresh(request_row)
        return request_row

    def _delete_today_meal_plans(self, user_id: int) -> None:
        today = datetime.utcnow().date()
        rows = list(
            self.db.scalars(
                select(MealPlan)
                .where(MealPlan.user_id == user_id)
                .where(MealPlan.plan_date == today)
            )
        )
        for meal_plan in rows:
            meals = list(self.db.scalars(select(Meal).where(Meal.meal_plan_id == meal_plan.id)))
            for m in meals:
                items = list(self.db.scalars(select(MealPlanItem).where(MealPlanItem.meal_id == m.id)))
                for item in items:
                    log_items = list(self.db.scalars(select(FoodLogItem).where(FoodLogItem.meal_plan_item_id == item.id)))
                    for log_item in log_items:
                        self.db.delete(log_item)
                    self.db.delete(item)
                self.db.delete(m)
            self.db.delete(meal_plan)
        if rows:
            self.db.flush()

    def get_today_meal_plan(self, user_id: int, target_date=None) -> MealPlan | None:
        target_date = target_date or datetime.utcnow().date()
        return self.db.scalar(
            select(MealPlan)
            .where(MealPlan.user_id == user_id)
            .where(MealPlan.plan_date == target_date)
            .order_by(MealPlan.created_at.desc())
        )

    def get_or_create_food_log(self, user_id: int, target_date=None) -> FoodLog:
        target_date = target_date or datetime.utcnow().date()
        row = self.db.scalar(
            select(FoodLog)
            .where(FoodLog.user_id == user_id)
            .where(FoodLog.log_date == target_date)
        )
        if row is not None:
            return row

        row = FoodLog(
            user_id=user_id,
            log_date=target_date,
            consumed_kcal=0.0,
            consumed_protein=0.0,
            consumed_fat=0.0,
            consumed_carbs=0.0,
            note=None,
        )
        self.db.add(row)
        self.db.flush()
        return row

    def set_meal_plan_item_eaten(
        self,
        user_id: int,
        meal_plan_item_id: int,
        eaten: bool = True,
        serving_grams: float | None = None,
    ) -> FoodLog:
        item = self.db.get(MealPlanItem, meal_plan_item_id)
        if item is None or item.meal is None or item.meal.meal_plan.user_id != user_id:
            raise ValueError("Meal plan item not found")

        food_log = self.get_or_create_food_log(user_id)
        existing = self.db.scalar(
            select(FoodLogItem)
            .where(FoodLogItem.food_log_id == food_log.id)
            .where(FoodLogItem.meal_plan_item_id == item.id)
        )

        if not eaten:
            if existing is not None:
                self.db.delete(existing)
                self.db.flush()
            self._recalculate_food_log_totals(food_log)
            self.db.commit()
            self.db.refresh(food_log)
            return food_log

        grams = serving_grams if serving_grams is not None else item.serving_grams
        if existing is None:
            existing = FoodLogItem(
                food_log_id=food_log.id,
                meal_plan_item_id=item.id,
                meal_type=item.meal_type,
                food_id=item.food_id,
                status="eaten",
                custom_name=item.name,
                quantity_g=grams,
                kcal=item.calories,
                protein=item.protein,
                fat=item.fat,
                carbs=item.carbs,
            )
            self.db.add(existing)
        else:
            existing.quantity_g = grams
            existing.kcal = item.calories
            existing.protein = item.protein
            existing.fat = item.fat
            existing.carbs = item.carbs

        self.db.flush()
        self._recalculate_food_log_totals(food_log)
        self.db.commit()
        self.db.refresh(food_log)
        return food_log

    def _recalculate_food_log_totals(self, food_log: FoodLog) -> None:
        totals = self.db.execute(
            select(
                func.coalesce(func.sum(FoodLogItem.kcal), 0.0),
                func.coalesce(func.sum(FoodLogItem.protein), 0.0),
                func.coalesce(func.sum(FoodLogItem.fat), 0.0),
                func.coalesce(func.sum(FoodLogItem.carbs), 0.0),
            ).where(FoodLogItem.food_log_id == food_log.id)
        ).one()
        food_log.consumed_kcal = float(totals[0] or 0.0)
        food_log.consumed_protein = float(totals[1] or 0.0)
        food_log.consumed_fat = float(totals[2] or 0.0)
        food_log.consumed_carbs = float(totals[3] or 0.0)

    def today_meal_plan_payload(self, user_id: int) -> dict:
        meal_plan = self.get_today_meal_plan(user_id)
        if meal_plan is None:
            return {
                "has_plan": False,
                "generate_required": True,
                "message": "Chưa có thực đơn hôm nay. Hãy bấm Tạo thực đơn hôm nay.",
                "meal_plan": None,
                "meals": [],
                "food_log": None,
            }

        food_log = self.db.scalar(
            select(FoodLog)
            .where(FoodLog.user_id == user_id)
            .where(FoodLog.log_date == datetime.utcnow().date())
        )
        eaten_item_ids = {
            int(item.meal_plan_item_id)
            for item in (food_log.items if food_log is not None else [])
            if item.meal_plan_item_id is not None
        }
        food_ids = [
            str(item.food_id)
            for meal in meal_plan.meals
            for item in meal.items
        ]
        food_metadata = self._food_metadata_by_ids(food_ids)

        meals = []
        for meal in sorted(meal_plan.meals, key=lambda row: row.sort_order):
            items = []
            for item in meal.items:
                metadata = food_metadata.get(str(item.food_id), {})
                items.append(
                    {
                        "id": item.id,
                        "food_id": item.food_id,
                        "name": metadata.get("dish_name_vi") or item.name,
                        "category": metadata.get("clean_category") or item.category,
                        "food_group": metadata.get("food_group_vi"),
                        "serving_grams": metadata.get("recommended_serving_g") or item.serving_grams,
                        "serving_display": metadata.get("serving_display"),
                        "image_url": metadata.get("image_url"),
                        "image_source_type": metadata.get("image_source_type"),
                        "image_verified": bool(metadata.get("image_verified", False)),
                        "calories": item.calories,
                        "protein": item.protein,
                        "fat": item.fat,
                        "carbs": item.carbs,
                        "status": "eaten" if item.id in eaten_item_ids else "suggested",
                        "is_eaten": item.id in eaten_item_ids,
                    }
                )
            meals.append(
                {
                    "id": meal.id,
                    "meal_type": meal.meal_type,
                    "title": meal.meal_name_vi,
                    "total_calories": meal.total_kcal,
                    "total_protein": meal.total_protein,
                    "total_fat": meal.total_fat,
                    "total_carbs": meal.total_carbs,
                    "items": items,
                }
            )

        return {
            "has_plan": True,
            "generate_required": False,
            "message": "",
            "meal_plan": {
                "id": meal_plan.id,
                "date": meal_plan.created_at.date().isoformat(),
                "target_calories": meal_plan.target_kcal,
                "total_calories": meal_plan.total_kcal,
                "total_protein": meal_plan.total_protein,
                "total_fat": meal_plan.total_fat,
                "total_carbs": meal_plan.total_carbs,
            },
            "meals": meals,
            "food_log": None
            if food_log is None
            else {
                "id": food_log.id,
                "consumed_kcal": food_log.consumed_kcal,
                "consumed_protein": food_log.consumed_protein,
                "consumed_fat": food_log.consumed_fat,
                "consumed_carbs": food_log.consumed_carbs,
            },
        }

    def _food_metadata_by_ids(self, food_ids: list[str]) -> dict[str, dict]:
        if not food_ids:
            return {}
        inspector = inspect(self.db.bind)
        food_columns = {column["name"] for column in inspector.get_columns("foods")}
        id_column = "food_id" if "food_id" in food_columns else "id" if "id" in food_columns else None
        if id_column is None:
            return {}
        selected_columns = [
            "dish_name_vi",
            "clean_category",
            "food_group_vi",
            "recommended_serving_g",
            "serving_display",
            "image_url",
            "image_source_type",
            "image_verified",
        ]
        select_parts = [f"CAST({id_column} AS CHAR) AS food_id"]
        for column in selected_columns:
            select_parts.append(column if column in food_columns else f"NULL AS {column}")
        rows = self.db.execute(
            text(
                f"""
                SELECT {", ".join(select_parts)}
                FROM foods
                WHERE {id_column} IN :food_ids
                """
            ).bindparams(bindparam("food_ids", expanding=True)),
            {"food_ids": tuple(food_ids)},
        ).mappings().all()
        return {str(row["food_id"]): dict(row) for row in rows}

    def list_recent_requests(
        self,
        limit: int = 10,
        user_id: int | None = None,
        period: str = "all",
    ) -> list[RecommendationRequest]:
        query = select(RecommendationRequest).order_by(RecommendationRequest.created_at.desc())
        if user_id is not None:
            query = query.where(RecommendationRequest.user_id == user_id)
        if period in {"day", "week"}:
            from datetime import datetime, timedelta

            delta = timedelta(days=1 if period == "day" else 7)
            query = query.where(RecommendationRequest.created_at >= datetime.utcnow() - delta)
        query = query.limit(limit)
        return list(self.db.scalars(query).unique())

    def get_request(self, request_id: int, user_id: int | None = None) -> RecommendationRequest | None:
        query = select(RecommendationRequest).where(RecommendationRequest.id == request_id)
        if user_id is not None:
            query = query.where(RecommendationRequest.user_id == user_id)
        return self.db.scalars(query).unique().first()

    @staticmethod
    def to_history_payload(rows: list[RecommendationRequest]) -> list[dict]:
        payload = []
        for row in rows:
            created_at = row.created_at.replace(tzinfo=timezone.utc).isoformat(timespec="seconds")
            payload.append(
                {
                    "id": row.id,
                    "created_at": created_at,
                    "target_calories": row.target_calories,
                    "bmr": row.bmr,
                    "tdee": row.tdee,
                    "recommended_calories": row.recommended_calories,
                    "relative_error_pct": row.relative_error_pct,
                    "precision_pct": row.precision_pct,
                }
            )
        return payload

    @staticmethod
    def to_history_detail_payload(row: RecommendationRequest) -> dict:
        item = RecommendationRepository.to_history_payload([row])[0]
        meal_plan_payload: dict[str, list[dict]] = {}
        if row.meal_plans:
            meal_plan = row.meal_plans[0]
            for meal in meal_plan.meals:
                for meal_item in meal.items:
                    # Chuyển đổi tên thuộc tính từ model mới về response API
                    meal_plan_payload.setdefault(meal.meal_type, []).append(
                        {
                            "food_id": meal_item.food_id,
                            "name": meal_item.reason, # Just random payload mapping based on old names
                            "image_url": meal_item.image_url,
                            "category": meal_item.meal_role,
                            "calories": meal_item.kcal,
                            "protein": meal_item.protein,
                            "fat": meal_item.fat,
                            "carbs": meal_item.carbs,
                            "score": 0.0,
                        }
                    )
        item["meal_plan"] = meal_plan_payload
        return item
