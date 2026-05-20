from __future__ import annotations

import json
import logging
import pickle
from pathlib import Path
from typing import Optional

import pandas as pd


logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parents[2]
DEFAULT_MODEL_PATH = BACKEND_DIR / "ml_models" / "food_eligibility_model.pkl"
DEFAULT_METADATA_PATH = BACKEND_DIR / "ml_models" / "food_eligibility_metadata.json"


class MLFoodEligibilityService:
    def __init__(
        self,
        model_path: str | Path = DEFAULT_MODEL_PATH,
        metadata_path: str | Path = DEFAULT_METADATA_PATH,
    ) -> None:
        self.model_path = Path(model_path)
        self.metadata_path = Path(metadata_path)
        self._model = None
        self._feature_columns: list[str] = []
        self._trained_at: str | None = None
        self._loaded_mtime: float | None = None
        self._load_error: str | None = None

    def _reset_disabled(self, reason: str | None = None) -> None:
        self._model = None
        self._feature_columns = []
        self._trained_at = None
        self._loaded_mtime = None
        self._load_error = reason

    def _load_metadata(self) -> dict:
        if not self.metadata_path.exists():
            return {}
        try:
            return json.loads(self.metadata_path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("Unable to read ML food eligibility metadata: %s", exc)
            return {}

    def _ensure_loaded(self) -> None:
        if not self.model_path.exists():
            if self._model is not None or self._load_error != "model_not_found":
                self._reset_disabled("model_not_found")
            return

        model_mtime = self.model_path.stat().st_mtime
        if self._model is not None and self._loaded_mtime == model_mtime:
            return

        try:
            with self.model_path.open("rb") as model_file:
                bundle = pickle.load(model_file)

            metadata = self._load_metadata()
            if isinstance(bundle, dict):
                model = bundle.get("model") or bundle.get("pipeline")
                feature_columns = list(
                    bundle.get("feature_columns") or metadata.get("feature_columns") or []
                )
                trained_at = bundle.get("trained_at") or metadata.get("trained_at")
            else:
                model = bundle
                feature_columns = list(metadata.get("feature_columns") or [])
                trained_at = metadata.get("trained_at")

            if model is None or not feature_columns:
                self._reset_disabled("invalid_model_bundle")
                return

            self._model = model
            self._feature_columns = feature_columns
            self._trained_at = trained_at
            self._loaded_mtime = model_mtime
            self._load_error = None
        except Exception as exc:
            self._reset_disabled("load_failed")
            logger.warning("Food eligibility ML model disabled because loading failed: %s", exc)

    def get_metadata(self) -> dict:
        self._ensure_loaded()
        return {
            "ml_enabled": self._model is not None,
            "model_path": str(self.model_path),
            "trained_at": self._trained_at,
        }

    def _food_value(self, food: object, column: str) -> object:
        if hasattr(food, "get"):
            return food.get(column, None)
        return getattr(food, column, None)

    def get_food_ml_score(self, food: object) -> Optional[float]:
        self._ensure_loaded()
        if self._model is None:
            return None

        try:
            values = {
                column: self._food_value(food, column)
                for column in self._feature_columns
            }
            frame = pd.DataFrame([values], columns=self._feature_columns)
            if hasattr(self._model, "predict_proba"):
                probabilities = self._model.predict_proba(frame)
                raw_classes = getattr(self._model, "classes_", None)
                classes = list(raw_classes) if raw_classes is not None else []
                positive_index = 1
                if classes:
                    for positive_value in (1, True, "1", "true", "eligible"):
                        if positive_value in classes:
                            positive_index = classes.index(positive_value)
                            break
                score = float(probabilities[0][positive_index])
            else:
                prediction = self._model.predict(frame)[0]
                score = float(prediction)
            return max(0.0, min(1.0, score))
        except Exception as exc:
            logger.warning("Food eligibility ML score skipped for one candidate: %s", exc)
            return None


ml_food_eligibility_service = MLFoodEligibilityService()
