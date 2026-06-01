from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import bindparam, func, inspect, select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.entities import FoodLog, FoodLogItem, Meal, MealConsumptionLog, MealPlan, MealPlanItem, RecommendationRequest


def _protein_excess_warning(total_protein: float, target_protein: float) -> str:
    excess_g = max(int(round(float(total_protein or 0.0) - float(target_protein or 0.0))), 0)
    return (
        f"Protein đang vượt mục tiêu {excess_g}g. "
        "Nên giảm bớt món đạm và tăng năng lượng "
        "bằng tinh bột, trái cây hoặc chất béo tốt."
    )


class RecommendationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def _today_local_date() -> datetime.date:
        try:
            tz = ZoneInfo(settings.app_timezone or "Asia/Ho_Chi_Minh")
        except Exception:
            tz = ZoneInfo("Asia/Ho_Chi_Minh")
        return datetime.now(tz).date()

    @staticmethod
    def filter_model_payload(model, payload: dict) -> dict:
        import logging
        logger = logging.getLogger(__name__)
        valid_columns = {column.name for column in model.__table__.columns}
        clean_payload = {k: v for k, v in payload.items() if k in valid_columns}
        invalid_keys = set(payload.keys()) - valid_columns
        if invalid_keys:
            logger.warning("Ignored invalid fields for %s: %s", model.__name__, invalid_keys)
        return clean_payload


    @staticmethod
    def resolve_food_db_id(db: Session, raw_food_id) -> str | None:
        if raw_food_id is None:
            return None
        try:
            numeric_id = int(raw_food_id)
            row_id = db.scalar(text("SELECT id FROM foods WHERE id = :id LIMIT 1"), {"id": numeric_id})
            if row_id is not None:
                return str(row_id)
        except (ValueError, TypeError):
            pass
            
        row_id = db.scalar(text("SELECT id FROM foods WHERE food_id = :food_id LIMIT 1"), {"food_id": str(raw_food_id)})
        if row_id is not None:
            return str(row_id)
        return None

    @staticmethod
    def resolve_food_db_ids(db: Session, raw_food_ids: list[object]) -> dict[str, str | None]:
        import logging
        logger = logging.getLogger(__name__)

        unique_ids = [str(food_id) for food_id in dict.fromkeys(raw_food_ids) if str(food_id or "").strip()]
        resolved: dict[str, str | None] = {food_id: None for food_id in unique_ids}
        if not unique_ids:
            return resolved

        try:
            food_columns = {column["name"] for column in inspect(db.bind).get_columns("foods")}
        except Exception as exc:
            logger.warning("Bulk food id resolution could not inspect foods table: %s", exc)
            food_columns = set()

        if "id" in food_columns:
            numeric_lookup: dict[int, str] = {}
            for raw_id in unique_ids:
                try:
                    numeric_lookup[int(raw_id)] = raw_id
                except (TypeError, ValueError):
                    continue
            if numeric_lookup:
                try:
                    rows = db.execute(
                        text("SELECT CAST(id AS CHAR) AS resolved_id FROM foods WHERE id IN :ids").bindparams(
                            bindparam("ids", expanding=True)
                        ),
                        {"ids": list(numeric_lookup.keys())},
                    ).mappings()
                    for row in rows:
                        resolved_id = str(row["resolved_id"])
                        original = numeric_lookup.get(int(resolved_id), resolved_id)
                        resolved[original] = resolved_id
                except Exception as exc:
                    logger.warning("Bulk numeric food id resolution failed; falling back per item: %s", exc)

        if "food_id" in food_columns:
            unresolved = [raw_id for raw_id, value in resolved.items() if value is None]
            if unresolved:
                try:
                    rows = db.execute(
                        text("SELECT CAST(food_id AS CHAR) AS resolved_id FROM foods WHERE food_id IN :food_ids").bindparams(
                            bindparam("food_ids", expanding=True)
                        ),
                        {"food_ids": unresolved},
                    ).mappings()
                    for row in rows:
                        resolved_id = str(row["resolved_id"])
                        if resolved_id in resolved:
                            resolved[resolved_id] = resolved_id
                except Exception as exc:
                    logger.warning("Bulk string food id resolution failed; falling back per item: %s", exc)

        for raw_id, value in list(resolved.items()):
            if value is None:
                resolved[raw_id] = RecommendationRepository.resolve_food_db_id(db, raw_id)
        return resolved

    def create_request_with_items(
        self,
        request_payload: dict,
        meal_items: list[dict],
        meal_plan_status: str = "valid",
    ) -> RecommendationRequest:
        import logging
        from fastapi import HTTPException, status
        from sqlalchemy.exc import IntegrityError
        logger = logging.getLogger(__name__)

        self.mark_today_meal_plans_status(int(request_payload["user_id"]), "invalid")
        clean_request_payload = self.filter_model_payload(RecommendationRequest, request_payload)

        request_row = RecommendationRequest(**clean_request_payload)
        self.db.add(request_row)
        self.db.flush()

        logger.info(f"Created recommendation_request_id: {request_row.id}")

        total_kcal = sum(float(item.get("calories") or item.get("kcal") or 0.0) for item in meal_items)
        total_protein = sum(float(item.get("protein") or 0.0) for item in meal_items)
        total_fat = sum(float(item.get("fat") or 0.0) for item in meal_items)
        total_carbs = sum(float(item.get("carbs") or item.get("carb") or 0.0) for item in meal_items)
        
        target_kcal = float(request_payload.get("target_calories") or request_payload.get("target_kcal") or 0.0)

        user_id_int = int(request_payload["user_id"])
        today_date = datetime.utcnow().date()

        # Handle existing meal plan for today to prevent UniqueConstraint error
        from app.models.entities import MealPlan, Meal, MealPlanItem, FoodLogItem, MealConsumptionLog
        existing_plan = self.db.scalar(
            select(MealPlan).where(MealPlan.user_id == user_id_int, MealPlan.plan_date == today_date)
        )
        if existing_plan:
            # Check if there are consumption logs
            has_logs = self.db.scalar(
                select(MealConsumptionLog.id)
                .where(MealConsumptionLog.meal_plan_id == existing_plan.id)
                .limit(1)
            )

            # Always mark old plan as superseded instead of deleting
            # This preserves meal history and consumption logs
            existing_plan.status = "superseded"
            self.db.flush()
            print("[MEAL PLAN SUPERSEDED]", {
                "user_id": user_id_int,
                "old_plan_id": existing_plan.id,
                "had_consumption_logs": has_logs is not None,
                "old_plan_date": existing_plan.plan_date.isoformat() if existing_plan.plan_date else None,
            })

        meal_plan = MealPlan(
            user_id=user_id_int,
            recommendation_request_id=request_row.id,
            plan_date=today_date,
            target_kcal=target_kcal,
            target_protein=float(request_payload.get("target_protein") or 0.0),
            target_fat=float(request_payload.get("target_fat") or 0.0),
            target_carbs=float(request_payload.get("target_carbs") or 0.0),
            total_kcal=total_kcal,
            total_protein=total_protein,
            total_fat=total_fat,
            total_carbs=total_carbs,
            status=meal_plan_status,
            note=json.dumps(
                {
                    "available_ingredients": list(request_payload.get("available_ingredients") or request_payload.get("ingredients") or []),
                    "ingredient_coverage": request_payload.get("ingredient_coverage") or request_payload.get("coverage_debug") or None,
                },
                ensure_ascii=False,
            ),
        )
        self.db.add(meal_plan)
        self.db.flush()

        print("[MEAL PLAN SAVED]", {
            "user_id": user_id_int,
            "meal_plan_id": meal_plan.id,
            "created_at": meal_plan.created_at.isoformat() if meal_plan.created_at else None,
            "updated_at": meal_plan.updated_at.isoformat() if meal_plan.updated_at else None,
            "plan_date": meal_plan.plan_date.isoformat() if meal_plan.plan_date else None,
            "status": meal_plan.status,
        })

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
            meal_rows[meal_type] = meal_row
        self.db.add_all(meal_rows.values())
        self.db.flush()

        logger.info(f"created meals count: {len(meal_rows)}")

        created_items_count = 0
        skipped_items: list[dict] = []
        raw_food_ids = [
            str(item.get("food_id", ""))
            for meal_type_items in grouped_items.values()
            for item in meal_type_items
            if isinstance(item, dict)
        ]
        resolved_food_ids = self.resolve_food_db_ids(self.db, raw_food_ids)
        meal_item_rows: list[MealPlanItem] = []
        for meal_type, meal_type_items in grouped_items.items():
            meal_kcal_sum = 0.0
            meal_protein_sum = 0.0
            meal_fat_sum = 0.0
            meal_carbs_sum = 0.0
            for idx, item in enumerate(meal_type_items):
                item_payload = dict(item)
                
                raw_food_id = str(item_payload.get("food_id", ""))
                resolved_food_id = resolved_food_ids.get(raw_food_id)

                if not resolved_food_id:
                    logger.warning(f"Skip item because food does not exist: {raw_food_id}")
                    skipped_items.append(
                        {
                            "meal_type": meal_type,
                            "food_id": raw_food_id,
                            "reason": "food_id_not_found",
                        }
                    )
                    continue

                qty = float(item_payload.get("serving_grams") or item_payload.get("quantity_g") or 0.0)
                
                m_item = MealPlanItem(
                    meal_id=meal_rows[meal_type].id,
                    food_id=resolved_food_id,
                    meal_role=str(item_payload.get("meal_role", "")),
                    quantity_g=qty if qty > 0 else None,
                    kcal=float(item_payload.get("calories") or item_payload.get("kcal") or 0.0),
                    protein=float(item_payload.get("protein") or 0.0),
                    fat=float(item_payload.get("fat") or 0.0),
                    carbs=float(item_payload.get("carbs") or item_payload.get("carb") or 0.0),
                    serving_display=str(item_payload.get("serving_display") or item_payload.get("portion_display") or ""),
                    reason=str(item_payload.get("reason", "")),
                    image_url=str(item_payload.get("image_url", "")),
                    image_badge=str(item_payload.get("image_badge") or ""),
                    item_order=idx,
                )
                meal_item_rows.append(m_item)
                created_items_count += 1
                meal_kcal_sum += float(m_item.kcal or 0.0)
                meal_protein_sum += float(m_item.protein or 0.0)
                meal_fat_sum += float(m_item.fat or 0.0)
                meal_carbs_sum += float(m_item.carbs or 0.0)

            # Keep meal totals from inserted payload values to avoid lazy-relationship timing issues.
            meal_rows[meal_type].total_kcal = meal_kcal_sum
            meal_rows[meal_type].total_protein = meal_protein_sum
            meal_rows[meal_type].total_fat = meal_fat_sum
            meal_rows[meal_type].total_carbs = meal_carbs_sum

        if meal_item_rows:
            self.db.add_all(meal_item_rows)

        # Recalculate meal plan totals
        meal_plan.total_kcal = sum(m.total_kcal for m in meal_rows.values())
        meal_plan.total_protein = sum(m.total_protein for m in meal_rows.values())
        meal_plan.total_fat = sum(m.total_fat for m in meal_rows.values())
        meal_plan.total_carbs = sum(m.total_carbs for m in meal_rows.values())

        if created_items_count == 0 or meal_plan.total_kcal <= 0:
            detail = "Meal plan không có món hợp lệ, vui lòng kiểm tra dữ liệu foods."
            logger.error(
                "Recommendation failed: %s",
                detail,
            )
            logger.error(
                "422 diagnostics | created_items_count=%s total_kcal=%s incoming_item_count=%s skipped_count=%s",
                created_items_count,
                meal_plan.total_kcal,
                len(meal_items),
                len(skipped_items),
            )
            if skipped_items:
                logger.error("Skipped items detail (first 30): %s", skipped_items[:30])
            self.db.rollback()
            meal_plan.status = "invalid"
            raise HTTPException(status_code=422, detail=detail)

        try:
            self.db.commit()
        except IntegrityError as e:
            self.db.rollback()
            logger.exception("Failed to create meal plan items due to integrity error.")
            detail = "Không thể tạo thực đơn vì một số món không tồn tại trong bảng foods."
            logger.error("Recommendation failed: %s", detail)
            raise HTTPException(status_code=422, detail=detail)

        logger.info(f"created meal_plan_items count: {created_items_count}")
        inserted_items = meal_item_rows
        actual_total_kcal = sum(float(item.kcal or 0.0) for item in inserted_items)
        if str(os.getenv("DEBUG_RECOMMENDER", "false")).strip().lower() in {"1", "true", "yes", "on"}:
            logger.warning("DEBUG_INSERTED_TOTAL_KCAL=%s inserted_count=%s", actual_total_kcal, len(inserted_items))
        if len(inserted_items) < len(meal_items):
            logger.warning(
                "Inserted fewer items than sample. inserted_count=%s sample_count=%s",
                len(inserted_items),
                len(meal_items),
            )
            if skipped_items:
                logger.warning("Skipped items (first 30): %s", skipped_items[:30])
        self.db.refresh(request_row)
        return request_row

    def mark_today_meal_plans_status(self, user_id: int, status: str) -> None:
        today = datetime.utcnow().date()
        rows = list(
            self.db.scalars(
                select(MealPlan)
                .where(MealPlan.user_id == user_id)
                .where(MealPlan.plan_date == today)
                .where(MealPlan.status.in_(["draft", "valid", "generated", "needs_regeneration"]))
            )
        )
        for meal_plan in rows:
            meal_plan.status = status
        if rows:
            self.db.flush()

    def mark_meal_plan_status(self, user_id: int, meal_plan_id: int, status: str) -> None:
        meal_plan = self.db.scalar(
            select(MealPlan)
            .where(MealPlan.user_id == user_id)
            .where(MealPlan.id == meal_plan_id)
        )
        if meal_plan is not None:
            meal_plan.status = status
            self.db.flush()

    def meal_plan_food_ids(self, user_id: int, meal_plan_id: int) -> list[str]:
        meal_plan = self.db.scalar(
            select(MealPlan)
            .where(MealPlan.user_id == user_id)
            .where(MealPlan.id == meal_plan_id)
        )
        if meal_plan is None:
            return []
        return [
            str(item.food_id)
            for meal in meal_plan.meals
            for item in meal.items
            if item.food_id
        ]

    def get_today_meal_plan(self, user_id: int, target_date=None) -> MealPlan | None:
        target_date = target_date or self._today_local_date()
        valid_plan = self.db.scalar(
            select(MealPlan)
            .where(MealPlan.user_id == user_id)
            .where(MealPlan.plan_date == target_date)
            .where(MealPlan.status.in_(["valid", "needs_regeneration", "major_adjustment", "minor_adjustment"]))
            .order_by(MealPlan.updated_at.desc(), MealPlan.created_at.desc(), MealPlan.id.desc())
        )
        if valid_plan is not None:
            try:
                metadata = json.loads(valid_plan.note or "{}") if valid_plan.note else {}
            except Exception:
                metadata = {}
            selected_available_ingredients = metadata.get("available_ingredients") if isinstance(metadata, dict) else []
            selected_item_names = [
                str(item.reason or item.food_id or "")
                for meal in valid_plan.meals
                for item in meal.items
                if item is not None
            ]
            print("[TODAY MEAL PLAN SELECTED]", {
                "user_id": user_id,
                "selected_plan_id": valid_plan.id,
                "selected_created_at": valid_plan.created_at.isoformat() if valid_plan.created_at else None,
                "selected_updated_at": valid_plan.updated_at.isoformat() if valid_plan.updated_at else None,
                "selected_generated_at": None,
                "plan_date": valid_plan.plan_date.isoformat() if valid_plan.plan_date else None,
                "status": valid_plan.status,
                "today_plan_count": int(self.db.scalar(
                    select(func.count(MealPlan.id))
                    .where(MealPlan.user_id == user_id)
                    .where(MealPlan.plan_date == target_date)
                    .where(MealPlan.status.in_(["valid", "needs_regeneration", "major_adjustment", "minor_adjustment"]))
                ) or 0),
            })
            print("[MEAL PLAN TODAY SELECT DEBUG]", {
                "user_id": user_id,
                "today": target_date.isoformat() if target_date else None,
                "selected_plan_id": valid_plan.id,
                "selected_created_at": valid_plan.created_at.isoformat() if valid_plan.created_at else None,
                "selected_updated_at": valid_plan.updated_at.isoformat() if valid_plan.updated_at else None,
                "selected_available_ingredients": selected_available_ingredients if isinstance(selected_available_ingredients, list) else [],
                "selected_item_names": selected_item_names,
            })
            return valid_plan
        return None

    def get_or_create_food_log(self, user_id: int, target_date=None) -> FoodLog:
        target_date = target_date or self._today_local_date()
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

        grams = serving_grams if serving_grams is not None else item.quantity_g
        if existing is None:
            existing = FoodLogItem(
                food_log_id=food_log.id,
                meal_plan_item_id=item.id,
                meal_type=item.meal.meal_type,
                food_id=item.food_id,
                status="eaten",
                custom_name=item.reason,
                quantity_g=grams,
                kcal=item.kcal,
                protein=item.protein,
                fat=item.fat,
                carbs=item.carbs,
            )
            self.db.add(existing)
        else:
            existing.quantity_g = grams
            existing.kcal = item.kcal
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
                "meal_logs": [],
                "consumption_logs": [],
                "eaten_items": [],
                "meal_consumptions": [],
                "logs": [],
                "food_log": None,
            }

        try:
            meal_plan_metadata = json.loads(meal_plan.note or "{}") if meal_plan.note else {}
        except Exception:
            meal_plan_metadata = {}
        available_ingredients = meal_plan_metadata.get("available_ingredients") if isinstance(meal_plan_metadata, dict) else []
        ingredient_coverage = meal_plan_metadata.get("ingredient_coverage") if isinstance(meal_plan_metadata, dict) else None

        today = self._today_local_date()
        food_log = self.db.scalar(
            select(FoodLog)
            .where(FoodLog.user_id == user_id)
            .where(FoodLog.log_date == today)
        )
        eaten_by_item_id = {}
        eaten_by_food_id = {}
        if food_log is not None:
            for log_item in food_log.items:
                if str(log_item.status or "").lower() != "eaten":
                    continue
                eaten_at = log_item.updated_at or log_item.created_at
                eaten_meta = {
                    "eaten_at": eaten_at.isoformat() if eaten_at else None,
                    "eaten_date": food_log.log_date.isoformat() if food_log.log_date else today.isoformat(),
                }
                if log_item.meal_plan_item_id is not None:
                    eaten_by_item_id[int(log_item.meal_plan_item_id)] = eaten_meta
                if log_item.food_id is not None:
                    eaten_by_food_id[str(log_item.food_id)] = eaten_meta

        consumption_logs = self.db.execute(
            select(MealConsumptionLog)
            .where(MealConsumptionLog.user_id == user_id)
            .where(MealConsumptionLog.meal_plan_id == meal_plan.id)
            .where(MealConsumptionLog.status.in_(["eaten", "EATEN", "consumed", "CONSUMED"]))
            .where(func.date(MealConsumptionLog.consumed_at) == today)
            .order_by(MealConsumptionLog.consumed_at.desc(), MealConsumptionLog.created_at.desc(), MealConsumptionLog.id.desc())
        ).scalars().all()

        meal_consumption_logs = []
        for log in consumption_logs:
            if log.food_id is None:
                continue
            eaten_at = log.consumed_at or log.created_at
            consumed_date = eaten_at.date().isoformat() if eaten_at else today.isoformat()
            meal_consumption_logs.append(
                {
                    "id": log.id,
                    "meal_plan_id": log.meal_plan_id,
                    "meal_type": log.meal_type,
                    "food_id": log.food_id,
                    "item_id": None,
                    "food_name": None,
                    "item_name": None,
                    "is_eaten": str(log.status or "").lower() == "eaten",
                    "eaten": str(log.status or "").lower() == "eaten",
                    "consumed": str(log.status or "").lower() == "eaten",
                    "status": log.status,
                    "consumed_at": eaten_at.isoformat() if eaten_at else None,
                    "consumed_date": consumed_date,
                }
            )
            eaten_by_food_id[str(log.food_id)] = {
                "eaten_at": eaten_at.isoformat() if eaten_at else None,
                "eaten_date": consumed_date,
            }

        print("[TODAY CONSUMPTION LOGS SELECTED]", {
            "user_id": user_id,
            "meal_plan_id": meal_plan.id if meal_plan else None,
            "logs_count": len(meal_consumption_logs),
            "logs_preview": [
                {
                    "meal_type": log["meal_type"],
                    "food_id": log["food_id"],
                    "item_id": log["item_id"],
                    "is_eaten": log["is_eaten"],
                    "status": log["status"],
                }
                for log in meal_consumption_logs[:10]
            ],
        })

        food_ids = [
            str(item.food_id)
            for meal in meal_plan.meals
            for item in meal.items
        ]
        food_metadata = self._food_metadata_by_ids(food_ids)

        meals = []
        for meal in sorted(meal_plan.meals, key=lambda row: row.meal_order):
            items = []
            for item in meal.items:
                metadata = food_metadata.get(str(item.food_id), {})
                eaten_meta = (
                    eaten_by_item_id.get(int(item.id))
                    or eaten_by_food_id.get(str(item.food_id))
                    or eaten_by_food_id.get(str(item.id))
                )
                is_eaten = eaten_meta is not None
                items.append(
                    {
                        "id": item.id,
                        "meal_plan_item_id": item.id,
                        "food_id": item.food_id,
                        "name": metadata.get("dish_name_vi") or item.reason or "Món ăn",
                        "category": metadata.get("clean_category") or item.meal_role,
                        "food_group": metadata.get("food_group_vi"),
                        "serving_grams": item.quantity_g or metadata.get("recommended_serving_g"),
                        "serving_display": item.serving_display or metadata.get("serving_display"),
                        "image_url": metadata.get("image_url"),
                        "image_source_type": metadata.get("image_source_type"),
                        "image_verified": bool(metadata.get("image_verified", False)),
                        "calories": item.kcal,
                        "protein": item.protein,
                        "fat": item.fat,
                        "carbs": item.carbs,
                        "status": "eaten" if is_eaten else "suggested",
                        "is_eaten": is_eaten,
                        "eaten_at": eaten_meta.get("eaten_at") if eaten_meta else None,
                        "eaten_date": eaten_meta.get("eaten_date") if eaten_meta else None,
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
                "date": meal_plan.plan_date.isoformat() if meal_plan.plan_date else meal_plan.created_at.date().isoformat(),
                "status": meal_plan.status,
                "target_kcal": meal_plan.target_kcal,
                "target_calories": meal_plan.target_kcal,
                "total_kcal": meal_plan.total_kcal,
                "total_calories": meal_plan.total_kcal,
                "total_protein_g": meal_plan.total_protein,
                "total_protein": meal_plan.total_protein,
                "total_fat_g": meal_plan.total_fat,
                "total_fat": meal_plan.total_fat,
                "total_carbs_g": meal_plan.total_carbs,
                "total_carbs": meal_plan.total_carbs,
                "available_ingredients": available_ingredients if isinstance(available_ingredients, list) else [],
                "ingredient_coverage": ingredient_coverage if isinstance(ingredient_coverage, dict) else None,
            },
            "validation": self._validate_today_meal_plan_payload(meal_plan),
            "meals": meals,
            "meal_logs": meal_consumption_logs,
            "consumption_logs": meal_consumption_logs,
            "eaten_items": meal_consumption_logs,
            "meal_consumptions": meal_consumption_logs,
            "logs": meal_consumption_logs,
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

    @staticmethod
    def _validate_today_meal_plan_payload(meal_plan: MealPlan) -> dict:
        target_kcal = float(meal_plan.target_kcal or 0.0)
        total_kcal = float(meal_plan.total_kcal or 0.0)
        kcal_diff = total_kcal - target_kcal
        kcal_diff_abs = abs(kcal_diff)
        kcal_diff_pct = (kcal_diff_abs / target_kcal) * 100 if target_kcal > 0 else 100.0
        target_protein = float(meal_plan.target_protein or 0.0)
        target_fat = float(meal_plan.target_fat or 0.0)
        target_carbs = float(meal_plan.target_carbs or 0.0)
        protein_ratio = float(meal_plan.total_protein or 0.0) / target_protein if target_protein > 0 else 1.0
        fat_ratio = float(meal_plan.total_fat or 0.0) / target_fat if target_fat > 0 else 1.0
        carbs_ratio = float(meal_plan.total_carbs or 0.0) / target_carbs if target_carbs > 0 else 1.0
        has_items = any(meal.items for meal in meal_plan.meals)
        if not meal_plan.meals or not has_items or total_kcal <= 0:
            plan_status = "invalid"
        elif kcal_diff_pct <= 10 and 0.9 <= protein_ratio <= 1.1 and 0.8 <= fat_ratio <= 1.2 and 0.8 <= carbs_ratio <= 1.2:
            plan_status = "valid"
        elif kcal_diff_pct <= 10 and protein_ratio <= 1.15 and fat_ratio >= 0.7 and carbs_ratio <= 1.3:
            plan_status = "minor_adjustment"
        else:
            plan_status = "major_adjustment"
        is_valid = plan_status == "valid"
        warnings = []
        protein_over_major = protein_ratio > 1.15
        if protein_over_major:
            warnings.append(_protein_excess_warning(float(meal_plan.total_protein or 0.0), target_protein))
        reason = None
        if protein_over_major and warnings:
            reason = warnings[0]
        elif not is_valid:
            direction = "cao hơn" if kcal_diff > 0 else "thấp hơn"
            reason = (
                f"Thực đơn hiện tại đạt {round(total_kcal)} kcal, {direction} mục tiêu "
                f"{round(target_kcal)} kcal khoảng {round(kcal_diff_abs)} kcal, "
                f"tương đương {kcal_diff_pct:.2f}%. Vui lòng tạo lại để có thực đơn phù hợp hơn."
            )
        return {
            "status": plan_status,
            "is_valid": is_valid,
            "isValid": is_valid,
            "reason": reason,
            "targetKcal": target_kcal,
            "totalKcal": total_kcal,
            "kcalDiff": kcal_diff,
            "kcalDiffPct": kcal_diff_pct,
            "target_kcal": target_kcal,
            "total_kcal": total_kcal,
            "kcal_diff": kcal_diff,
            "kcal_diff_pct": kcal_diff_pct,
            "errors": [] if is_valid else [reason],
            "warnings": warnings,
        }

    def restore_meal_plan(
        self,
        user_id: int,
        source_meal_plan_id: int | None,
        source_date: str | None,
        meals: list[dict],
        reset_consumption: bool = True,
    ) -> dict:
        """Restore a meal plan from history as today's active plan."""
        import logging
        logger = logging.getLogger(__name__)
        
        today = self._today_local_date()
        
        # Validate meals data
        if not meals or not isinstance(meals, list):
            raise ValueError("Meals data is required for restoration")
        
        # Calculate totals from meals
        total_kcal = 0.0
        total_protein = 0.0
        total_fat = 0.0
        total_carbs = 0.0
        
        for meal in meals:
            items = meal.get("items", [])
            for item in items:
                total_kcal += float(item.get("calories", 0) or item.get("kcal", 0) or 0)
                total_protein += float(item.get("protein", 0) or item.get("protein_g", 0) or 0)
                total_fat += float(item.get("fat", 0) or item.get("fat_g", 0) or 0)
                total_carbs += float(item.get("carbs", 0) or item.get("carbs_g", 0) or 0)
        
        # Get target from user's latest meal plan or use calculated totals
        latest_plan = self.db.scalar(
            select(MealPlan)
            .where(MealPlan.user_id == user_id)
            .order_by(MealPlan.created_at.desc())
            .limit(1)
        )
        
        target_kcal = latest_plan.target_kcal if latest_plan else total_kcal
        target_protein = latest_plan.target_protein if latest_plan else total_protein
        target_fat = latest_plan.target_fat if latest_plan else total_fat
        target_carbs = latest_plan.target_carbs if latest_plan else total_carbs
        
        # Create new meal plan for today
        new_meal_plan = MealPlan(
            user_id=user_id,
            recommendation_request_id=None,
            plan_date=today,
            target_kcal=target_kcal,
            target_protein=target_protein,
            target_fat=target_fat,
            target_carbs=target_carbs,
            total_kcal=total_kcal,
            total_protein=total_protein,
            total_fat=total_fat,
            total_carbs=total_carbs,
            status="valid",
            note=f"Restored from {'meal plan ' + str(source_meal_plan_id) if source_meal_plan_id else 'history'} on {source_date or 'unknown date'}",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        self.db.add(new_meal_plan)
        self.db.flush()
        
        logger.info("[RESTORE MEAL PLAN] Created new plan id=%s for user=%s date=%s", new_meal_plan.id, user_id, today)
        
        # Create meals and items
        meal_type_order = {"breakfast": 1, "morning_snack": 2, "lunch": 3, "afternoon_snack": 4, "dinner": 5, "evening_snack": 6}
        
        for meal_data in meals:
            meal_type = meal_data.get("meal_type", "")
            meal_order = meal_type_order.get(meal_type, 99)
            
            meal_kcal = 0.0
            meal_protein = 0.0
            meal_fat = 0.0
            meal_carbs = 0.0
            
            items_data = meal_data.get("items", [])
            for item in items_data:
                meal_kcal += float(item.get("calories", 0) or item.get("kcal", 0) or 0)
                meal_protein += float(item.get("protein", 0) or item.get("protein_g", 0) or 0)
                meal_fat += float(item.get("fat", 0) or item.get("fat_g", 0) or 0)
                meal_carbs += float(item.get("carbs", 0) or item.get("carbs_g", 0) or 0)
            
            new_meal = Meal(
                meal_plan_id=new_meal_plan.id,
                meal_type=meal_type,
                meal_name_vi=meal_data.get("title") or meal_data.get("meal_name_vi"),
                meal_order=meal_order,
                total_kcal=meal_kcal,
                total_protein=meal_protein,
                total_fat=meal_fat,
                total_carbs=meal_carbs,
                created_at=datetime.utcnow(),
            )
            
            self.db.add(new_meal)
            self.db.flush()
            
            # Create meal items
            for idx, item_data in enumerate(items_data):
                food_id = item_data.get("food_id", "")
                
                new_item = MealPlanItem(
                    meal_id=new_meal.id,
                    food_id=str(food_id),
                    meal_role=item_data.get("category") or item_data.get("meal_role"),
                    quantity_g=item_data.get("serving_grams") or item_data.get("quantity_g"),
                    kcal=float(item_data.get("calories", 0) or item_data.get("kcal", 0) or 0),
                    protein=float(item_data.get("protein", 0) or item_data.get("protein_g", 0) or 0),
                    fat=float(item_data.get("fat", 0) or item_data.get("fat_g", 0) or 0),
                    carbs=float(item_data.get("carbs", 0) or item_data.get("carbs_g", 0) or 0),
                    serving_display=item_data.get("serving_display"),
                    reason=item_data.get("name") or item_data.get("food_name"),
                    image_url=item_data.get("image_url") or item_data.get("imageUrl"),
                    image_badge=None,
                    item_order=idx,
                    created_at=datetime.utcnow(),
                )
                
                self.db.add(new_item)
            
        # Reset consumption logs if requested
        if reset_consumption:
            # Delete today's meal consumption logs for this user
            self.db.execute(
                text("""
                    DELETE FROM meal_consumption_logs 
                    WHERE user_id = :user_id 
                    AND DATE(consumed_at) = :today
                """),
                {"user_id": user_id, "today": today}
            )
            
            # Delete today's food log items
            food_log = self.db.scalar(
                select(FoodLog)
                .where(FoodLog.user_id == user_id)
                .where(FoodLog.log_date == today)
            )
            
            if food_log:
                self.db.execute(
                    text("DELETE FROM food_log_items WHERE food_log_id = :food_log_id"),
                    {"food_log_id": food_log.id}
                )
                food_log.consumed_kcal = 0.0
                food_log.consumed_protein = 0.0
                food_log.consumed_fat = 0.0
                food_log.consumed_carbs = 0.0
            
            logger.info("[RESTORE MEAL PLAN] Reset consumption logs for user=%s date=%s", user_id, today)
        
        self.db.commit()
        
        # Return the same format as today_meal_plan_payload
        return self.today_meal_plan_payload(user_id)

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
