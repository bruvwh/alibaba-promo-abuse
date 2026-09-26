# Alibaba Promotion Abuse Detection

## Objective

Build an end-to-end machine learning system that uses historical Alibaba O2O
customer behavior to predict whether a user will engage in promotion-abuse
behavior during the following 7 days.

The project uses real Alibaba online and offline behavioral data with
semi-synthetic promotion-abuse ground truth.

## Raw Data Sources

### Offline Events

Grain:
One offline user-merchant/coupon interaction.

Available behavior includes:
- Normal purchases
- Coupon receiptsModeling grain:
user_id + prediction_date

Prediction cadence:
weekly

History window:
previous 30 days

Outcome window:
following 7 days

Eligibility:
>= 5 historical events
AND
>= 1 coupon receipt
during the previous 30 days
- Coupon redemptions
- Merchant interactions
- Discount information
- Distance
- Event dates

### Online Events

Grain:
One online user action.

Available behavior includes:
- Clicks
- Purchases
- Coupon receipts
- Merchant interactions
- Discount information
- Event dates

Online and offline merchant IDs represent separate merchant namespaces.

User IDs can occur in both datasets and provide the common entity used to
combine behavioral information across channels.

## Modeling Grain

One row represents:

user_id + prediction_date

Prediction cadence:
weekly

History window:
previous 30 days

Outcome window:
following 7 days

Eligibility:
>= 5 historical events
AND
>= 1 coupon receipt
during the previous 30 days

A user may therefore appear multiple times at different prediction dates.


## Feature Window

For each prediction date, features are calculated using only behavior from
the previous 30 calendar days.

Shorter windows such as 7-day activity may also be calculated inside the
30-day historical period.

No information occurring on or after the prediction date may be used as a
feature.

## Label Window

The target represents whether the user begins or participates in a
promotion-abuse episode during the next 7 days.

Target:

abuse_next_7d = 1 if an abuse episode overlaps the future 7-day window
abuse_next_7d = 0 otherwise

## Synthetic Ground Truth

Semi-synthetic abuse will be represented in a separate abuse-episode table.

Ground-truth grain:

one user + one abuse episode

The source behavioral tables will contain realistic semi-synthetic abuse
activity while the ground-truth table records the corresponding abuse
episodes.

The modeling pipeline will transform abuse episodes into user-level
future-window labels.

## Cross-Channel Modeling

Offline and online events remain separate raw and staging tables.

Features are calculated separately for each channel and later joined at:

user_id + prediction_date

The final model may therefore use both online and offline behavioral history.

The main prediction target represents promotion abuse in either channel.

## Candidate Prediction Schedule

Prediction snapshots will initially be generated weekly from:

2016-02-01 through 2016-06-06

Each prediction date uses:

- Previous 30 days for features
- Following 7 days for the target

## Candidate Modeling Population

A user must have sufficient observable behavior before a prediction is made.

Initial eligibility rule:

- At least 5 historical events across online and offline channels during
  the previous 30 days
- At least 1 coupon receipt in either channel during the previous 30 days

These thresholds will be validated against the real dataset before being
finalized.

## Evaluation Split

Data will be split chronologically rather than randomly.

Candidate split:

Training:
2016-02-01 through 2016-04-25 prediction dates

Validation:
2016-05-02 through 2016-05-16 prediction dates

Test:
2016-05-23 through 2016-06-06 prediction dates

This prevents future observations from being used to evaluate models trained
on later behavior.