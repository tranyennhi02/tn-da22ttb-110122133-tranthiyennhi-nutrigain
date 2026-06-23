from __future__ import annotations

import argparse
import json
import pickle
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


CATEGORICAL_FEATURES = [
    "clean_category",
    "food_group_vi",
    "meal_role",
]

NUMERIC_FEATURES = [
    "recommended_serving_g",
    "kcal_per_100g_clean",
    "protein_per_100g_clean",
    "fat_per_100g_clean",
    "carbs_per_100g_clean",
    "kcal_per_serving_clean",
    "protein_per_serving_clean",
    "fat_per_serving_clean",
    "carbs_per_serving_clean",
]

LABEL_COLUMN = "menu_eligible"
MODEL_TYPE = "RandomForestClassifier"

BACKEND_DIR = Path(__file__).resolve().parents[1]
MODEL_DIR = BACKEND_DIR / "ml_models"
MODEL_PATH = MODEL_DIR / "food_eligibility_model.pkl"
METADATA_PATH = MODEL_DIR / "food_eligibility_metadata.json"


def _one_hot_encoder() -> OneHotEncoder:
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:  # pragma: no cover - compatibility with older sklearn.
        return OneHotEncoder(handle_unknown="ignore", sparse=False)


def _normalize_label(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    text = str(value or "").strip().lower()
    return 1 if text in {"1", "true", "yes", "y", "eligible"} else 0


def _prepare_dataframe(csv_path: Path) -> tuple[pd.DataFrame, pd.Series, list[str], list[str]]:
    data = pd.read_csv(csv_path)
    if LABEL_COLUMN not in data.columns:
        raise ValueError(f"CSV must contain label column: {LABEL_COLUMN}")

    categorical_columns = [column for column in CATEGORICAL_FEATURES if column in data.columns]
    numeric_columns = [column for column in NUMERIC_FEATURES if column in data.columns]
    feature_columns = categorical_columns + numeric_columns

    if not feature_columns:
        data["__constant_feature"] = 1.0
        numeric_columns = ["__constant_feature"]
        feature_columns = ["__constant_feature"]

    frame = data[feature_columns].copy()
    for column in categorical_columns:
        frame[column] = frame[column].fillna("unknown").astype(str)
    for column in numeric_columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    labels = data[LABEL_COLUMN].apply(_normalize_label).astype(int)
    return frame, labels, categorical_columns, numeric_columns


def train(csv_path: Path) -> dict:
    features, labels, categorical_columns, numeric_columns = _prepare_dataframe(csv_path)
    stratify = labels if labels.nunique() > 1 and labels.value_counts().min() >= 2 else None
    test_size = 0.2 if len(features) >= 10 else 0.5

    X_train, X_test, y_train, y_test = train_test_split(
        features,
        labels,
        test_size=test_size,
        random_state=42,
        stratify=stratify,
    )

    transformers = []
    if categorical_columns:
        categorical_pipeline = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="constant", fill_value="unknown")),
                ("onehot", _one_hot_encoder()),
            ]
        )
        transformers.append(("categorical", categorical_pipeline, categorical_columns))
    if numeric_columns:
        numeric_pipeline = Pipeline(steps=[("imputer", SimpleImputer(strategy="median"))])
        transformers.append(("numeric", numeric_pipeline, numeric_columns))

    preprocessor = ColumnTransformer(transformers=transformers, remainder="drop")
    pipeline = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            (
                "model",
                RandomForestClassifier(
                    n_estimators=150,
                    random_state=42,
                    class_weight="balanced",
                    min_samples_leaf=2,
                ),
            ),
        ]
    )
    pipeline.fit(X_train, y_train)
    predictions = pipeline.predict(X_test)

    metrics = {
        "accuracy": float(accuracy_score(y_test, predictions)),
        "precision": float(precision_score(y_test, predictions, zero_division=0)),
        "recall": float(recall_score(y_test, predictions, zero_division=0)),
        "f1": float(f1_score(y_test, predictions, zero_division=0)),
        "confusion_matrix": confusion_matrix(y_test, predictions, labels=[0, 1]).tolist(),
    }

    trained_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    metadata = {
        "model_type": MODEL_TYPE,
        "label_column": LABEL_COLUMN,
        "feature_columns": list(features.columns),
        "metrics": metrics,
        "trained_at": trained_at,
        "dataset_row_count": int(len(features)),
    }

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    with MODEL_PATH.open("wb") as model_file:
        pickle.dump(
            {
                "model": pipeline,
                "feature_columns": list(features.columns),
                "categorical_columns": categorical_columns,
                "numeric_columns": numeric_columns,
                "label_column": LABEL_COLUMN,
                "trained_at": trained_at,
            },
            model_file,
        )
    METADATA_PATH.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return metadata


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train NutriGain food menu eligibility model")
    parser.add_argument("--csv", required=True, help="Path to foods CSV")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    csv_path = Path(args.csv).expanduser().resolve()
    metadata = train(csv_path)
    metrics = metadata["metrics"]
    print(f"accuracy: {metrics['accuracy']:.4f}")
    print(f"precision: {metrics['precision']:.4f}")
    print(f"recall: {metrics['recall']:.4f}")
    print(f"f1: {metrics['f1']:.4f}")
    print(f"confusion_matrix: {metrics['confusion_matrix']}")
    print(f"model_path: {MODEL_PATH}")
    print(f"metadata_path: {METADATA_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
