# Model Card: Controlled Promotion-Abuse Risk Ranking

## Model overview

This project ranks eligible user-week observations by predicted risk of a controlled promotion-abuse outcome during the following seven days. The selected model is a scikit-learn histogram gradient-boosting classifier.

## Intended use

The intended use is a portfolio demonstration of data engineering, behavioral analysis, machine learning, and batch risk ranking. Scores may illustrate how a promotions team could prioritize accounts for human review. They are not intended to automatically restrict promotions, suspend accounts, or decide customer eligibility.

## Data and labels

Behavioral inputs come from the public Alibaba O2O Coupon Usage dataset, which contains online and offline events from January through June 2016. This source dataset contains no confirmed abuse outcome labels. Evaluation ground truth was constructed through controlled abuse scenarios injected into copies of historical behavior; episode-level labels are maintained separately.

The controlled scenarios contain injected pre-event signals. Consequently, features can be associated with labels partly because of scenario-generation rules. The observed patterns do not establish real-world abuse behavior or verified operational effectiveness.

## Prediction design

- Grain: one user and prediction date.
- Cadence: weekly from February 1 through June 6, 2016.
- Eligibility: at least five historical atomic events and one coupon receipt in the prior 30 days.
- Predictors: behavior in `[prediction date - 30 days, prediction date)`.
- Label: whether a controlled episode overlaps `[prediction date, prediction date + 7 days)`.
- Training: February 1–April 25.
- Validation: May 2–May 16.
- Test: May 23–June 6.

Users can contribute observations in multiple weeks and splits. Merchant identifiers are not assumed to link across channels. Missing recency indicates no relevant event in the history window. Undefined redemption ratios remain missing and receive a missingness indicator in logistic regression.

## Selected model

`HistGradientBoostingClassifier` settings:

- 200 boosting iterations
- Learning rate 0.05
- Maximum 31 leaves per tree
- Minimum 30 observations per leaf
- L2 regularization 1.0
- Fixed random seed 42
- No class reweighting

The model was selected on validation data and refit on training plus validation before one held-out test evaluation. The test outcomes were not used for model tuning.

## Test performance

The test set contains 137,183 user-weeks and 1,549 positives (1.129% prevalence), across three prediction dates.

| Metric | Model | Constant-prevalence reference |
|---|---:|---:|
| Average precision | 0.39763 | 0.01129 |
| ROC-AUC | 0.95952 | 0.50000 |
| Brier score | 0.00866 | 0.01116 |
| Log loss | 0.03508 | 0.06186 |

For a review capacity of 250 user-weeks per prediction date, test precision was 57.7%, recall 28.0%, with 433 positives and 317 false positives across three dates. At 100 reviews per week, precision was 80.7% and recall 15.6%; at 500, precision was 40.5% and recall 39.3%.

Review capacity is illustrative. These counts are user-weeks, not necessarily distinct accounts. The evaluation covers only three held-out weeks and controlled labels, so it does not establish future or real-world performance.

## Calibration and explanation

Validation score-band analysis showed that predicted scores were not perfectly calibrated, especially in higher-score bands. The model should primarily be interpreted as a ranking model. The test evaluation reports aggregate Brier and log-loss values but does not include a final test score-band calibration table. Do not describe individual risk scores as verified probabilities without further calibration analysis.

Feature associations and coefficients are not causal effects. Correlated behavior counts, acceleration measures, and activity indicators make individual feature contributions difficult to interpret.

## Operational safeguards and limitations

- Scores support human review only; the scoring code does not perform enforcement.
- Historical data lacks device, IP, payment, session, account-age, transaction-value, and exact location signals.
- Duplicate-looking source rows cannot automatically be treated as errors because transaction identifiers are absent.
- Online purchase-per-click is not session-level conversion.
- Repeated users create dependence; validation comparison intervals resample users with their observations together.
- Validation was used to compare multiple candidates, so selected validation performance may be optimistic.
- The batch pipeline writes versioned score rows by prediction date and is idempotent for a rerun of that date. Scheduling, alerting, monitoring, access controls, and real-world validation are outside this portfolio implementation.
