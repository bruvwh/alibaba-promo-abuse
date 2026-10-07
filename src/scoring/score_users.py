"""Score eligible user-weeks for one prediction date and upsert results to BigQuery."""

from __future__ import annotations

import argparse
import json
import re
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import db_dtypes  # Register BigQuery DATE values when converting query results.
from google.cloud import bigquery

PROJECT_ID = "alibaba-promo-abuse-1790454859"
FEATURE_DATASET = "promo_abuse_features"
FEATURE_TABLE = "user_behavior_features"
SCORE_TABLE = "user_risk_scores"
MODEL_VERSION = "hist_gradient_boosting_leaves31_v1"
MAX_BYTES_BILLED = 1_000_000_000


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--prediction-date",
        required=True,
        type=date.fromisoformat,
        help="Prediction snapshot date in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--project-id",
        default=PROJECT_ID,
        help="Google Cloud project containing the feature and score tables.",
    )
    return parser.parse_args()


def load_scoring_inputs(root: Path):
    artifact_dir = root / "data" / "processed" / "model_comparison"
    model_path = artifact_dir / "selected_gradient_boosting.joblib"
    feature_path = artifact_dir / "feature_columns.json"
    if not model_path.is_file() or not feature_path.is_file():
        raise FileNotFoundError(
            "Final model artifacts are missing. Run notebook 06 through its save cell first."
        )
    model = joblib.load(model_path)
    features = json.loads(feature_path.read_text())
    if len(features) != 31 or len(features) != len(set(features)):
        raise ValueError("Feature metadata does not match the selected model's 31 predictors.")
    if any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) for name in features):
        raise ValueError("Feature metadata contains an invalid BigQuery column name.")
    return model, features


def fetch_features(
    client: bigquery.Client,
    project_id: str,
    prediction_date: date,
    features: list[str],
) -> pd.DataFrame:
    table = f"`{project_id}.{FEATURE_DATASET}.{FEATURE_TABLE}`"
    columns = ", ".join(["user_id", "prediction_date", *features])
    sql = f"SELECT {columns} FROM {table} WHERE prediction_date = DATE '{prediction_date.isoformat()}'"
    estimate = client.query(
        sql,
        job_config=bigquery.QueryJobConfig(dry_run=True, use_query_cache=False),
    )
    print(f"Estimated feature scan: {estimate.total_bytes_processed / 1_000_000:.1f} MB")
    if estimate.total_bytes_processed > MAX_BYTES_BILLED:
        raise RuntimeError("Feature query exceeds the 1 GB billing cap.")
    job = client.query(
        sql,
        job_config=bigquery.QueryJobConfig(maximum_bytes_billed=MAX_BYTES_BILLED),
    )
    frame = job.result().to_dataframe(create_bqstorage_client=False)
    if frame.empty:
        raise ValueError(f"No eligible users found for {prediction_date}.")
    if frame["prediction_date"].nunique() != 1:
        raise ValueError("Feature query returned more than one prediction date.")
    if frame["prediction_date"].iloc[0].isoformat() != prediction_date.isoformat():
        raise ValueError("Returned prediction date does not match the request.")
    if frame["user_id"].isna().any() or frame["user_id"].duplicated().any():
        raise ValueError("Expected one non-null row per user on the requested date.")
    if frame[features].isna().to_numpy().any():
        # Recency and the redemption ratio may be null; their fitted pipeline imputes them.
        allowed = {
            "days_since_last_offline_purchase",
            "days_since_last_offline_redemption",
            "days_since_last_online_click",
            "offline_redemption_rate_30d",
        }
        unexpected = [c for c in features if frame[c].isna().any() and c not in allowed]
        if unexpected:
            raise ValueError(f"Unexpected missing predictors: {unexpected}")
    if np.isinf(frame[features].to_numpy(dtype=float)).any():
        raise ValueError("Infinite predictor values found.")
    return frame


def score_features(frame: pd.DataFrame, model, features: list[str], model_version: str) -> pd.DataFrame:
    scores = model.predict_proba(frame[features].astype("float64"))[:, 1]
    if not np.isfinite(scores).all() or ((scores < 0) | (scores > 1)).any():
        raise ValueError("Model returned an invalid risk score.")
    scored_at = datetime.now(timezone.utc)
    result = frame[["user_id", "prediction_date"]].copy()
    result["prediction_date"] = pd.to_datetime(result["prediction_date"])
    result["risk_score"] = scores.astype(float)
    result["model_version"] = model_version
    result["scored_at"] = scored_at
    if result["user_id"].duplicated().any():
        raise ValueError("Scoring produced duplicate users for the requested date.")
    # Break equal-score ties by user_id so output ranks do not depend on query row order.
    result = result.sort_values(
        ["risk_score", "user_id"], ascending=[False, True], kind="mergesort"
    ).reset_index(drop=True)
    result["risk_rank"] = np.arange(1, len(result) + 1, dtype="int64")
    return result


def upsert_scores(
    client: bigquery.Client,
    project_id: str,
    prediction_date: date,
    scores: pd.DataFrame,
) -> None:
    dataset = f"{project_id}.{FEATURE_DATASET}"
    target = f"`{dataset}.{SCORE_TABLE}`"
    stage_name = f"_user_risk_scores_stage_{uuid.uuid4().hex[:12]}"
    stage = f"{dataset}.{stage_name}"
    ddl = f"""
    CREATE TABLE IF NOT EXISTS {target} (
      user_id INT64 NOT NULL,
      prediction_date DATE NOT NULL,
      risk_score FLOAT64 NOT NULL,
      risk_rank INT64 NOT NULL,
      model_version STRING NOT NULL,
      scored_at TIMESTAMP NOT NULL
    )
    PARTITION BY prediction_date
    CLUSTER BY user_id
    """
    client.query(ddl).result()
    job_config = bigquery.LoadJobConfig(
        schema=[
            bigquery.SchemaField("user_id", "INT64", mode="REQUIRED"),
            bigquery.SchemaField("prediction_date", "DATE", mode="REQUIRED"),
            bigquery.SchemaField("risk_score", "FLOAT64", mode="REQUIRED"),
            bigquery.SchemaField("risk_rank", "INT64", mode="REQUIRED"),
            bigquery.SchemaField("model_version", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("scored_at", "TIMESTAMP", mode="REQUIRED"),
        ],
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )
    try:
        client.load_table_from_dataframe(scores, stage, job_config=job_config).result()
        merge = f"""
        MERGE {target} AS target
        USING `{stage}` AS source
          ON target.user_id = source.user_id
         AND target.prediction_date = source.prediction_date
        WHEN MATCHED THEN UPDATE SET
          risk_score = source.risk_score,
          risk_rank = source.risk_rank,
          model_version = source.model_version,
          scored_at = source.scored_at
        WHEN NOT MATCHED THEN INSERT
          (user_id, prediction_date, risk_score, risk_rank, model_version, scored_at)
        VALUES
          (source.user_id, source.prediction_date, source.risk_score,
           source.risk_rank, source.model_version, source.scored_at)
        WHEN NOT MATCHED BY SOURCE
          AND target.prediction_date = DATE '{prediction_date.isoformat()}'
        THEN DELETE
        """
        client.query(merge).result()
    finally:
        client.delete_table(stage, not_found_ok=True)
    print(f"Upserted {len(scores):,} user scores to {project_id}.{FEATURE_DATASET}.{SCORE_TABLE}")


def main() -> None:
    args = parse_args()
    root = project_root()
    model, features = load_scoring_inputs(root)
    client = bigquery.Client(project=args.project_id)
    frame = fetch_features(client, args.project_id, args.prediction_date, features)
    scores = score_features(frame, model, features, MODEL_VERSION)
    print("Highest-risk accounts:")
    print(scores[["user_id", "prediction_date", "risk_score", "risk_rank"]].head(10).to_string(index=False))
    upsert_scores(client, args.project_id, args.prediction_date, scores)


if __name__ == "__main__":
    main()
