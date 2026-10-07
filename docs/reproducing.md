# Reproducing the project

## Local environment

The project was developed with Python 3.13. From the repository root, create the project environment and install its pinned dependencies:

```bash
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Run the offline scoring checks:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

These tests cover deterministic tie-breaking, score and input validation, the documented missing-value allowance, and enforcement of the query scan cap. They do not access BigQuery.

## Data and warehouse steps

The source data, controlled-scenario generator, fitted model artifacts, and dbt credentials are not included in this repository. The original source files and generated scenario data are kept locally and are not committed. A clean clone therefore cannot reproduce the notebooks or warehouse tables until those private inputs are supplied.

The warehouse workflow uses dbt Core 1.12.5 with the BigQuery adapter 1.12.1. Configure a dbt profile named `alibaba_promo_abuse` in `dbt_promo_abuse/profiles.yml`, with access to the project and datasets referenced by the dbt project. Keep credentials out of version control. Run the dbt builds and notebooks in sequence as described in the root README; notebook 04 creates the modeling data and comparison artifacts, notebook 05 compares candidates, and notebook 06 performs the held-out test evaluation and exports the final scoring model.

The batch scoring CLI requires Google Cloud credentials with permission to read the feature table and create or update the scoring table. It performs a dry-run scan estimate and stops when the estimate exceeds 1 GB. To score a date, use the command in the README only after the feature table, model artifact, and credentials are available. Re-running a date replaces that date's prior scores, so this command writes to BigQuery.
