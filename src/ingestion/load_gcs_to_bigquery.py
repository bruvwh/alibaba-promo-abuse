from __future__ import annotations

import argparse

from google.cloud import bigquery


DATASET_ID = "promo_abuse_raw"
LOCATION = "US"


OFFLINE_SCHEMA = [
    bigquery.SchemaField(
        "User_id",
        "INT64",
        mode="NULLABLE",
    ),
    bigquery.SchemaField(
        "Merchant_id",
        "INT64",
        mode="NULLABLE",
    ),
    bigquery.SchemaField(
        "Coupon_id",
        "STRING",
        mode="NULLABLE",
    ),
    bigquery.SchemaField(
        "Discount_rate",
        "STRING",
        mode="NULLABLE",
    ),
    bigquery.SchemaField(
        "Distance",
        "FLOAT64",
        mode="NULLABLE",
    ),
    bigquery.SchemaField(
        "Date_received",
        "STRING",
        mode="NULLABLE",
    ),
    bigquery.SchemaField(
        "Date",
        "STRING",
        mode="NULLABLE",
    ),
]


ONLINE_SCHEMA = [
    bigquery.SchemaField(
        "User_id",
        "INT64",
        mode="NULLABLE",
    ),
    bigquery.SchemaField(
        "Merchant_id",
        "INT64",
        mode="NULLABLE",
    ),
    bigquery.SchemaField(
        "Action",
        "INT64",
        mode="NULLABLE",
    ),
    bigquery.SchemaField(
        "Coupon_id",
        "STRING",
        mode="NULLABLE",
    ),
    bigquery.SchemaField(
        "Discount_rate",
        "STRING",
        mode="NULLABLE",
    ),
    bigquery.SchemaField(
        "Date_received",
        "STRING",
        mode="NULLABLE",
    ),
    bigquery.SchemaField(
        "Date",
        "STRING",
        mode="NULLABLE",
    ),
]


ABUSE_CASES_SCHEMA = [
    bigquery.SchemaField(
        "episode_id",
        "STRING",
        mode="REQUIRED",
    ),
    bigquery.SchemaField(
        "user_id",
        "INT64",
        mode="REQUIRED",
    ),
    bigquery.SchemaField(
        "channel",
        "STRING",
        mode="REQUIRED",
    ),
    bigquery.SchemaField(
        "abuse_start_date",
        "DATE",
        mode="REQUIRED",
    ),
    bigquery.SchemaField(
        "abuse_end_date",
        "DATE",
        mode="REQUIRED",
    ),
    bigquery.SchemaField(
        "confirmed_date",
        "DATE",
        mode="REQUIRED",
    ),
]


TABLES = {
    "offline_events": {
        "filename": "offline_events.csv",
        "schema": OFFLINE_SCHEMA,
    },
    "online_events": {
        "filename": "online_events.csv",
        "schema": ONLINE_SCHEMA,
    },
    "abuse_cases": {
        "filename": "abuse_cases.csv",
        "schema": ABUSE_CASES_SCHEMA,
    },
}


def create_dataset(
    client: bigquery.Client,
    project_id: str,
) -> None:

    dataset_ref = (
        f"{project_id}.{DATASET_ID}"
    )

    dataset = bigquery.Dataset(
        dataset_ref
    )

    dataset.location = LOCATION

    client.create_dataset(
        dataset,
        exists_ok=True,
    )

    print(
        f"DATASET READY: {dataset_ref}"
    )


def load_table(
    client: bigquery.Client,
    project_id: str,
    bucket_name: str,
    table_name: str,
    filename: str,
    schema: list[
        bigquery.SchemaField
    ],
) -> None:

    uri = (
        f"gs://{bucket_name}/"
        f"source/{filename}"
    )

    table_id = (
        f"{project_id}."
        f"{DATASET_ID}."
        f"{table_name}"
    )

    job_config = (
        bigquery.LoadJobConfig()
    )

    job_config.schema = schema

    job_config.source_format = (
        bigquery.SourceFormat.CSV
    )

    job_config.skip_leading_rows = 1

    job_config.write_disposition = (
        bigquery.WriteDisposition
        .WRITE_TRUNCATE
    )

    job_config.allow_quoted_newlines = True

    job_config.ignore_unknown_values = False

    print(
        f"\nLOAD: {uri}"
    )

    print(
        f"   -> {table_id}"
    )

    load_job = (
        client.load_table_from_uri(
            uri,
            table_id,
            job_config=job_config,
            location=LOCATION,
        )
    )

    load_job.result()

    table = client.get_table(
        table_id
    )

    print(
        f"PASS: {table_name}"
    )

    print(
        f"Rows: {table.num_rows:,}"
    )


def main() -> None:

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--project",
        required=True,
        help="GCP project ID",
    )

    parser.add_argument(
        "--bucket",
        required=True,
        help="GCS bucket name",
    )

    args = parser.parse_args()

    print(
        "\nAlibaba Promotion Abuse"
        "\nBigQuery Raw Ingestion\n"
    )

    client = bigquery.Client(
        project=args.project
    )

    create_dataset(
        client,
        args.project,
    )

    for table_name, config in (
        TABLES.items()
    ):

        load_table(
            client=client,
            project_id=args.project,
            bucket_name=args.bucket,
            table_name=table_name,
            filename=config[
                "filename"
            ],
            schema=config[
                "schema"
            ],
        )

    print(
        "\n================================"
    )

    print(
        "BIGQUERY RAW INGESTION COMPLETE"
    )

    print(
        "================================"
    )


if __name__ == "__main__":
    main()