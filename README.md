# Alibaba O2O Promotion-Abuse Risk Scoring

An end-to-end portfolio project that turns Alibaba O2O online and offline behavior into point-in-time user-week features, evaluates risk models against controlled abuse scenarios, and writes ranked batch scores to BigQuery.

The project supports investigation prioritization and behavioral analysis. Model scores do not automatically ban customers, restrict coupons, or trigger other enforcement actions.

## Data and interpretation

The public Alibaba O2O Coupon Usage dataset was designed for coupon-redemption prediction and contains no confirmed promotion-abuse labels. Because the public source lacks abuse outcomes, **evaluation ground truth was constructed through controlled abuse scenarios injected into copies of the historical behavioral data**. Scenario episodes are stored separately from behavioral events.

Model results describe performance on these constructed scenarios. They are not verified real-world fraud-detection performance, and some findings may reflect the scenario-generation rules. Do not interpret behavioral associations as proof of how actual Alibaba customers who abuse promotions behave. Original source files remain separate and immutable.

## Architecture

1. **Source validation and ingestion:** Python validates the source files and loads immutable raw data to Google Cloud Storage and BigQuery.
2. **dbt transformations:** Staging models standardize schemas; canonical facts split source rows into atomic events; daily tables aggregate behavior; the scoring-population model applies historical eligibility rules.
3. **Point-in-time features:** `promo_abuse_features.user_behavior_features` contains one row per eligible user-week. Every predictor uses the 30 days before the prediction date, excluding that date.
4. **Outcome labels and splits:** `user_outcome_labels` identifies a controlled episode overlapping the next seven days. `user_modeling_dataset` joins labels to features and assigns fixed chronological splits.
5. **Model comparison:** Logistic regression, random forest, and histogram gradient boosting are compared using the same validation weeks and review capacities.
6. **Batch scoring:** `src/scoring/score_users.py` scores one prediction date and idempotently upserts the ranked results to BigQuery.

Online and offline merchant identifiers are treated as separate namespaces. The data lacks device, IP, transaction amount, session, account-age, and exact-location fields, so the project does not infer those signals.

## Prediction and evaluation design

- **Observation:** `user_id + prediction_date`
- **Scoring cadence:** weekly, February 1 through June 6, 2016
- **Eligible population:** at least five historical atomic events and one coupon receipt in the previous 30 days
- **Feature window:** `[prediction_date - 30 days, prediction_date)`
- **Outcome window:** `[prediction_date, prediction_date + 7 days)`
- **Training dates:** February 1–April 25, 2016
- **Validation dates:** May 2–May 16, 2016
- **Test dates:** May 23–June 6, 2016

The same user can appear in multiple weeks and splits, matching recurring weekly scoring. Confidence intervals for validation comparisons resample users with all their weekly observations together. The final test period was held out until model selection was complete.

## Model results

The selected candidate is scikit-learn `HistGradientBoostingClassifier` with 31 leaves, 200 iterations, learning rate 0.05, minimum leaf size 30, and L2 regularization 1.0. It was selected using validation performance, then refit on training plus validation data for the final test evaluation.

On the three held-out test weeks (137,183 user-weeks; 1,549 positives; 1.129% prevalence):

| Metric | Selected model | Constant-prevalence reference |
|---|---:|---:|
| Average precision | 0.39763 | 0.01129 |
| ROC-AUC | 0.95952 | 0.50000 |
| Brier score (lower is better) | 0.00866 | 0.01116 |
| Log loss (lower is better) | 0.03508 | 0.06186 |

At 250 user-week reviews per prediction date, the model found 433 of 1,549 positive user-weeks across the test (57.7% precision, 28.0% recall, 317 false positives). At 100 per week, precision was 80.7% and recall 15.6%; at 500 per week, precision was 40.5% and recall 39.3%. These review capacities are illustrative, not an approved business policy. A user can contribute more than one reviewed user-week.

A user-cluster bootstrap on validation estimated a 0.033 average-precision advantage for 31-leaf boosting over the depth-20 random forest, with a 95% interval of 0.022–0.045. This comparison is conditional on validation and can be optimistic because validation was used to compare candidates. Test results are the final held-out performance estimate for the controlled scenarios, but only cover three weeks.

See [docs/model_card.md](docs/model_card.md) for intended use, methods, metrics, and limitations.

## Batch scoring

The final fitted model and its feature list are local artifacts produced by notebook 06 under the ignored `data/processed/model_comparison/` directory. Regenerate them by running notebooks 04–06 in order; they are intentionally not committed.

With Google Cloud OAuth configured and the project `.venv` installed, score one date from the built scoring population:

```bash
.venv/bin/python src/scoring/score_users.py --prediction-date 2016-06-06
```

The script reads `user_behavior_features` for that date, checks the 31 predictors, estimates the query scan, and enforces a 1 GB billed-byte cap. It writes user ID, prediction date, risk score, rank, model version, and scoring timestamp to:

`alibaba-promo-abuse-1790454859.promo_abuse_features.user_risk_scores`

The table is partitioned by prediction date. Re-running a date updates that date's rows and removes stale rows for the same date. The example June 6 run scored 49,298 eligible users; a follow-up BigQuery audit verified unique users and ranks 1–49,298.

## Reproducing the workflow

- `notebooks/03_behavioral_eda.ipynb`: training-period behavioral EDA.
- `notebooks/04_modeling_dataset.ipynb`: dbt feature and label builds, logistic baseline, validation checks, and local comparison-artifact export.
- `notebooks/05_model_comparison.ipynb`: logistic, random-forest, and boosting comparisons plus user-cluster bootstrap.
- `notebooks/06_final_test_evaluation.ipynb`: one-time held-out test evaluation and selected-model export.
- `notebooks/07_batch_scoring.ipynb`: example batch scoring and warehouse-output audit.

The dbt profile, source abuse-generation code, source data, and fitted model artifacts are private or local. Supply valid project-local credentials and data before reproducing cloud steps. See [docs/reproducing.md](docs/reproducing.md) for setup and local checks. This is a reproducible batch portfolio workflow, not a continuously scheduled production service.
