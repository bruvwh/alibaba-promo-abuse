"""Offline tests for batch scoring input checks and deterministic ranking."""
from datetime import date
import unittest

import numpy as np
import pandas as pd

from src.scoring.score_users import fetch_features, score_features


class ScoreByValue:
    def predict_proba(self, frame):
        score = frame["value"].to_numpy(dtype=float)
        return np.column_stack([1 - score, score])


class FakeQueryJob:
    def __init__(self, frame=None, estimate=100):
        self.total_bytes_processed = estimate
        self.frame = frame

    def result(self):
        return self

    def to_dataframe(self, create_bqstorage_client=False):
        return self.frame.copy()


class FakeBigQueryClient:
    def __init__(self, frame, estimate=100):
        self.frame = frame
        self.estimate = estimate
        self.calls = 0

    def query(self, sql, job_config):
        self.calls += 1
        if job_config.dry_run:
            return FakeQueryJob(estimate=self.estimate)
        return FakeQueryJob(frame=self.frame)


class ScoringTests(unittest.TestCase):
    def test_score_ranks_are_deterministic_for_tied_scores(self):
        features = ["value"]
        model = ScoreByValue()
        frames = [
            pd.DataFrame({
                "user_id": [9, 2, 4],
                "prediction_date": [date(2016, 6, 6)] * 3,
                "value": [0.1, 0.1, 0.9],
            }),
            pd.DataFrame({
                "user_id": [4, 9, 2],
                "prediction_date": [date(2016, 6, 6)] * 3,
                "value": [0.9, 0.1, 0.1],
            }),
        ]
        ranked = [score_features(frame, model, features, "test") for frame in frames]
        for output in ranked:
            self.assertEqual(output["user_id"].tolist(), [4, 2, 9])
            self.assertEqual(output["risk_rank"].tolist(), [1, 2, 3])
        pd.testing.assert_series_equal(ranked[0]["risk_score"], ranked[1]["risk_score"])

    def test_rejects_duplicate_users(self):
        frame = pd.DataFrame({
            "user_id": [7, 7],
            "prediction_date": [date(2016, 6, 6)] * 2,
            "value": [0.4, 0.8],
        })
        with self.assertRaisesRegex(ValueError, "duplicate users"):
            score_features(frame, ScoreByValue(), ["value"], "test")

    def test_rejects_nonfinite_or_out_of_range_scores(self):
        frame = pd.DataFrame({
            "user_id": [1, 2],
            "prediction_date": [date(2016, 6, 6)] * 2,
            "value": [0.2, 0.4],
        })
        for invalid in [np.nan, 1.2]:
            class InvalidModel:
                def predict_proba(self, values):
                    return np.column_stack([[0.5, 0.5], [invalid, invalid]])

            with self.subTest(invalid=invalid):
                with self.assertRaisesRegex(ValueError, "invalid risk score"):
                    score_features(frame, InvalidModel(), ["value"], "test")

    def test_fetch_allows_only_documented_missing_predictors(self):
        frame = pd.DataFrame({
            "user_id": [1],
            "prediction_date": [date(2016, 6, 6)],
            "days_since_last_online_click": [None],
            "value": [0.3],
        })
        client = FakeBigQueryClient(frame)
        result = fetch_features(
            client, "test-project", date(2016, 6, 6),
            ["days_since_last_online_click", "value"],
        )
        self.assertEqual(client.calls, 2)
        self.assertTrue(result["value"].iloc[0] == 0.3)

    def test_fetch_rejects_unexpected_missing_predictor(self):
        frame = pd.DataFrame({
            "user_id": [1],
            "prediction_date": [date(2016, 6, 6)],
            "value": [None],
        })
        client = FakeBigQueryClient(frame)
        with self.assertRaisesRegex(ValueError, "Unexpected missing predictors"):
            fetch_features(
                client, "test-project", date(2016, 6, 6), ["value"]
            )

    def test_fetch_respects_scan_cap_before_data_query(self):
        frame = pd.DataFrame({
            "user_id": [1],
            "prediction_date": [date(2016, 6, 6)],
            "value": [0.2],
        })
        client = FakeBigQueryClient(frame, estimate=2_000_000_000)
        with self.assertRaisesRegex(RuntimeError, "1 GB billing cap"):
            fetch_features(client, "test-project", date(2016, 6, 6), ["value"])
        self.assertEqual(client.calls, 1)


if __name__ == "__main__":
    unittest.main()
