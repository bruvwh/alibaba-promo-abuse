from __future__ import annotations

from pathlib import Path
import hashlib
import json

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

RAW_DIR = ROOT / "data" / "raw"
SOURCE_DIR = ROOT / "data" / "source"
REPORT_DIR = ROOT / "reports"

RAW_OFFLINE = RAW_DIR / "ccf_offline_stage1_train.csv"
RAW_ONLINE = RAW_DIR / "ccf_online_stage1_train.csv"

SOURCE_OFFLINE = SOURCE_DIR / "offline_events.csv"
SOURCE_ONLINE = SOURCE_DIR / "online_events.csv"
ABUSE_CASES = SOURCE_DIR / "abuse_cases.csv"
GENERATION_SUMMARY = SOURCE_DIR / "generation_summary.json"

OUTPUT_REPORT = REPORT_DIR / "source_validation.json"


EXPECTED_OFFLINE_COLUMNS = [
    "User_id",
    "Merchant_id",
    "Coupon_id",
    "Discount_rate",
    "Distance",
    "Date_received",
    "Date",
]

EXPECTED_ONLINE_COLUMNS = [
    "User_id",
    "Merchant_id",
    "Action",
    "Coupon_id",
    "Discount_rate",
    "Date_received",
    "Date",
]

EXPECTED_CASE_COLUMNS = [
    "episode_id",
    "user_id",
    "channel",
    "abuse_start_date",
    "abuse_end_date",
    "confirmed_date",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b""
        ):
            h.update(chunk)

    return h.hexdigest()


def count_csv_rows(path: Path) -> int:
    with path.open("rb") as f:
        line_count = sum(1 for _ in f)

    return max(line_count - 1, 0)


def check_columns(
    path: Path,
    expected_columns: list[str]
) -> list[str]:

    columns = pd.read_csv(
        path,
        nrows=0
    ).columns.tolist()

    assert columns == expected_columns, (
        f"{path.name} schema mismatch.\n"
        f"Expected: {expected_columns}\n"
        f"Found:    {columns}"
    )

    return columns


def parse_yyyymmdd(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(
        series,
        errors="coerce"
    )

    return pd.to_datetime(
        numeric.astype("Int64").astype(str),
        format="%Y%m%d",
        errors="coerce"
    )


def validate_online_actions(path: Path) -> set[int]:
    observed = set()

    for chunk in pd.read_csv(
        path,
        usecols=["Action"],
        chunksize=500_000
    ):
        values = (
            pd.to_numeric(
                chunk["Action"],
                errors="coerce"
            )
            .dropna()
            .astype(int)
            .unique()
        )

        observed.update(values.tolist())

    assert observed.issubset({0, 1, 2}), (
        f"Unexpected online Action values: {observed}"
    )

    return observed


def validate_source_dates(
    offline_path: Path,
    online_path: Path
) -> dict:

    min_date = pd.Timestamp("2016-01-01")
    max_behavior_date = pd.Timestamp("2016-06-30")

    offline_invalid = 0
    online_invalid = 0

    offline_min = None
    offline_max = None
    online_min = None
    online_max = None

    for chunk in pd.read_csv(
        offline_path,
        usecols=["Date_received", "Date"],
        chunksize=500_000
    ):

        received = parse_yyyymmdd(
            chunk["Date_received"]
        )

        purchased = parse_yyyymmdd(
            chunk["Date"]
        )

        dates = pd.concat(
            [received, purchased],
            ignore_index=True
        ).dropna()

        if len(dates) == 0:
            continue

        invalid = (
            (dates < min_date)
            | (dates > max_behavior_date)
        )

        offline_invalid += int(
            invalid.sum()
        )

        chunk_min = dates.min()
        chunk_max = dates.max()

        offline_min = (
            chunk_min
            if offline_min is None
            else min(offline_min, chunk_min)
        )

        offline_max = (
            chunk_max
            if offline_max is None
            else max(offline_max, chunk_max)
        )

    for chunk in pd.read_csv(
        online_path,
        usecols=[
            "Action",
            "Date_received",
            "Date"
        ],
        chunksize=500_000
    ):

        action = pd.to_numeric(
            chunk["Action"],
            errors="coerce"
        )

        event_date = pd.Series(
            pd.NaT,
            index=chunk.index,
            dtype="datetime64[ns]"
        )

        receipt_mask = action.eq(2)
        activity_mask = action.isin([0, 1])

        event_date.loc[
            receipt_mask
        ] = parse_yyyymmdd(
            chunk.loc[
                receipt_mask,
                "Date_received"
            ]
        )

        event_date.loc[
            activity_mask
        ] = parse_yyyymmdd(
            chunk.loc[
                activity_mask,
                "Date"
            ]
        )

        dates = event_date.dropna()

        if len(dates) == 0:
            continue

        invalid = (
            (dates < min_date)
            | (dates > max_behavior_date)
        )

        online_invalid += int(
            invalid.sum()
        )

        chunk_min = dates.min()
        chunk_max = dates.max()

        online_min = (
            chunk_min
            if online_min is None
            else min(online_min, chunk_min)
        )

        online_max = (
            chunk_max
            if online_max is None
            else max(online_max, chunk_max)
        )

    assert offline_invalid == 0, (
        f"Found {offline_invalid} "
        f"offline dates outside expected range."
    )

    assert online_invalid == 0, (
        f"Found {online_invalid} "
        f"online dates outside expected range."
    )

    return {
        "offline_min_date": (
            offline_min.strftime("%Y-%m-%d")
            if offline_min is not None
            else None
        ),
        "offline_max_date": (
            offline_max.strftime("%Y-%m-%d")
            if offline_max is not None
            else None
        ),
        "online_min_date": (
            online_min.strftime("%Y-%m-%d")
            if online_min is not None
            else None
        ),
        "online_max_date": (
            online_max.strftime("%Y-%m-%d")
            if online_max is not None
            else None
        ),
    }


def validate_abuse_cases(
    cases: pd.DataFrame,
    original_users: set[int]
) -> dict:

    assert (
        cases.columns.tolist()
        == EXPECTED_CASE_COLUMNS
    ), (
        "abuse_cases.csv schema mismatch."
    )

    assert cases["episode_id"].notna().all()
    assert cases["episode_id"].is_unique

    assert cases["user_id"].notna().all()

    cases["user_id"] = (
        pd.to_numeric(
            cases["user_id"],
            errors="raise"
        )
        .astype(int)
    )

    assert cases[
        "channel"
    ].isin(
        ["offline", "online", "both"]
    ).all(), (
        "Invalid channel found in abuse_cases."
    )

    for col in [
        "abuse_start_date",
        "abuse_end_date",
        "confirmed_date",
    ]:
        cases[col] = pd.to_datetime(
            cases[col],
            errors="raise"
        )

    assert (
        cases["abuse_end_date"]
        >= cases["abuse_start_date"]
    ).all(), (
        "Found abuse episode ending "
        "before it begins."
    )

    assert (
        cases["confirmed_date"]
        >= cases["abuse_end_date"]
    ).all(), (
        "Found confirmed_date before "
        "abuse episode ended."
    )

    expected_start = pd.Timestamp(
        "2016-02-01"
    )

    expected_end = pd.Timestamp(
        "2016-06-12"
    )

    assert (
        cases["abuse_start_date"]
        >= expected_start
    ).all(), (
        "Found abuse episode before "
        "first scoring period."
    )

    assert (
        cases["abuse_end_date"]
        <= expected_end
    ).all(), (
        "Found abuse episode beyond "
        "final 7-day outcome window."
    )

    case_users = set(
        cases["user_id"].unique()
    )

    missing_users = (
        case_users - original_users
    )

    assert not missing_users, (
        f"{len(missing_users)} abuse users "
        "do not exist in original Alibaba data."
    )

    return {
        "episodes": int(len(cases)),
        "unique_case_users": int(
            cases["user_id"].nunique()
        ),
        "channels": {
            str(k): int(v)
            for k, v in (
                cases["channel"]
                .value_counts()
                .to_dict()
                .items()
            )
        },
        "first_abuse_date": (
            cases[
                "abuse_start_date"
            ]
            .min()
            .strftime("%Y-%m-%d")
        ),
        "last_abuse_date": (
            cases[
                "abuse_end_date"
            ]
            .max()
            .strftime("%Y-%m-%d")
        ),
    }


def collect_original_users() -> set[int]:
    users = set()

    for path in [
        RAW_OFFLINE,
        RAW_ONLINE
    ]:
        for chunk in pd.read_csv(
            path,
            usecols=["User_id"],
            chunksize=500_000
        ):
            ids = (
                pd.to_numeric(
                    chunk["User_id"],
                    errors="coerce"
                )
                .dropna()
                .astype(int)
            )

            users.update(
                ids.tolist()
            )

    return users


def build_injected_event_index(
    raw_rows: int,
    source_path: Path,
    channel: str
) -> pd.DataFrame:

    skiprows = range(
        1,
        raw_rows + 1
    )

    if channel == "offline":

        df = pd.read_csv(
            source_path,
            skiprows=skiprows
        )

        receipt = df.loc[
            df["Date_received"].notna(),
            ["User_id", "Date_received"]
        ].copy()

        receipt["event_date"] = (
            parse_yyyymmdd(
                receipt["Date_received"]
            )
        )

        purchase = df.loc[
            df["Date"].notna(),
            ["User_id", "Date"]
        ].copy()

        purchase["event_date"] = (
            parse_yyyymmdd(
                purchase["Date"]
            )
        )

        events = pd.concat(
            [
                receipt[
                    ["User_id", "event_date"]
                ],
                purchase[
                    ["User_id", "event_date"]
                ],
            ],
            ignore_index=True
        )

    else:

        df = pd.read_csv(
            source_path,
            skiprows=skiprows
        )

        action = pd.to_numeric(
            df["Action"],
            errors="coerce"
        )

        event_date = pd.Series(
            pd.NaT,
            index=df.index,
            dtype="datetime64[ns]"
        )

        receipt_mask = action.eq(2)
        activity_mask = action.isin(
            [0, 1]
        )

        event_date.loc[
            receipt_mask
        ] = parse_yyyymmdd(
            df.loc[
                receipt_mask,
                "Date_received"
            ]
        )

        event_date.loc[
            activity_mask
        ] = parse_yyyymmdd(
            df.loc[
                activity_mask,
                "Date"
            ]
        )

        events = pd.DataFrame({
            "User_id": df["User_id"],
            "event_date": event_date,
        })

    events["User_id"] = pd.to_numeric(
        events["User_id"],
        errors="coerce"
    ).astype("Int64")

    return events.dropna(
        subset=[
            "User_id",
            "event_date"
        ]
    )


def validate_case_behavior(
    cases: pd.DataFrame,
    offline_events: pd.DataFrame,
    online_events: pd.DataFrame
) -> dict:

    offline_groups = {
        int(user): group["event_date"]
        for user, group
        in offline_events.groupby("User_id")
    }

    online_groups = {
        int(user): group["event_date"]
        for user, group
        in online_events.groupby("User_id")
    }

    missing_offline = []
    missing_online = []

    for row in cases.itertuples(
        index=False
    ):

        user_id = int(row.user_id)

        start = row.abuse_start_date
        end = row.abuse_end_date

        if row.channel in {
            "offline",
            "both"
        }:

            dates = offline_groups.get(
                user_id
            )

            valid = (
                dates is not None
                and (
                    (dates >= start)
                    & (dates <= end)
                ).any()
            )

            if not valid:
                missing_offline.append(
                    row.episode_id
                )

        if row.channel in {
            "online",
            "both"
        }:

            dates = online_groups.get(
                user_id
            )

            valid = (
                dates is not None
                and (
                    (dates >= start)
                    & (dates <= end)
                ).any()
            )

            if not valid:
                missing_online.append(
                    row.episode_id
                )

    assert not missing_offline, (
        f"{len(missing_offline)} cases "
        "have no injected offline activity "
        "during their abuse window."
    )

    assert not missing_online, (
        f"{len(missing_online)} cases "
        "have no injected online activity "
        "during their abuse window."
    )

    return {
        "cases_missing_offline_behavior":
            len(missing_offline),
        "cases_missing_online_behavior":
            len(missing_online),
    }


def main():

    print(
        "\nAlibaba Promotion Abuse "
        "Source Validation\n"
    )

    required_files = [
        RAW_OFFLINE,
        RAW_ONLINE,
        SOURCE_OFFLINE,
        SOURCE_ONLINE,
        ABUSE_CASES,
        GENERATION_SUMMARY,
    ]

    print(
        "1. Checking required files..."
    )

    for path in required_files:
        assert path.exists(), (
            f"Missing required file: {path}"
        )

    print("   PASS")

    print(
        "2. Loading generation summary..."
    )

    summary = json.loads(
        GENERATION_SUMMARY.read_text()
    )

    print("   PASS")

    print(
        "3. Verifying raw source hashes..."
    )

    offline_hash = sha256(
        RAW_OFFLINE
    )

    online_hash = sha256(
        RAW_ONLINE
    )

    assert (
        offline_hash
        == summary[
            "raw_offline_sha256"
        ]
    ), (
        "Raw offline file changed "
        "after generation."
    )

    assert (
        online_hash
        == summary[
            "raw_online_sha256"
        ]
    ), (
        "Raw online file changed "
        "after generation."
    )

    print("   PASS")

    print(
        "4. Checking schemas..."
    )

    check_columns(
        RAW_OFFLINE,
        EXPECTED_OFFLINE_COLUMNS
    )

    check_columns(
        SOURCE_OFFLINE,
        EXPECTED_OFFLINE_COLUMNS
    )

    check_columns(
        RAW_ONLINE,
        EXPECTED_ONLINE_COLUMNS
    )

    check_columns(
        SOURCE_ONLINE,
        EXPECTED_ONLINE_COLUMNS
    )

    print("   PASS")

    print(
        "5. Counting rows..."
    )

    raw_offline_rows = count_csv_rows(
        RAW_OFFLINE
    )

    source_offline_rows = (
        count_csv_rows(
            SOURCE_OFFLINE
        )
    )

    raw_online_rows = count_csv_rows(
        RAW_ONLINE
    )

    source_online_rows = (
        count_csv_rows(
            SOURCE_ONLINE
        )
    )

    assert (
        raw_offline_rows
        == summary[
            "original_offline_rows"
        ]
    )

    assert (
        source_offline_rows
        == summary[
            "source_offline_rows"
        ]
    )

    assert (
        raw_online_rows
        == summary[
            "original_online_rows"
        ]
    )

    assert (
        source_online_rows
        == summary[
            "source_online_rows"
        ]
    )

    assert (
        source_offline_rows
        >= raw_offline_rows
    )

    assert (
        source_online_rows
        >= raw_online_rows
    )

    print(
        f"   Offline: "
        f"{raw_offline_rows:,} -> "
        f"{source_offline_rows:,}"
    )

    print(
        f"   Online:  "
        f"{raw_online_rows:,} -> "
        f"{source_online_rows:,}"
    )

    print("   PASS")

    print(
        "6. Checking online Action values..."
    )

    actions = validate_online_actions(
        SOURCE_ONLINE
    )

    print(
        f"   Found actions: "
        f"{sorted(actions)}"
    )

    print("   PASS")

    print(
        "7. Validating event dates..."
    )

    date_summary = (
        validate_source_dates(
            SOURCE_OFFLINE,
            SOURCE_ONLINE
        )
    )

    print(
        "   Offline:",
        date_summary[
            "offline_min_date"
        ],
        "to",
        date_summary[
            "offline_max_date"
        ],
    )

    print(
        "   Online:",
        date_summary[
            "online_min_date"
        ],
        "to",
        date_summary[
            "online_max_date"
        ],
    )

    print("   PASS")

    print(
        "8. Collecting original users..."
    )

    original_users = (
        collect_original_users()
    )

    print(
        f"   {len(original_users):,} "
        f"unique users"
    )

    print("   PASS")

    print(
        "9. Validating abuse cases..."
    )

    cases = pd.read_csv(
        ABUSE_CASES
    )

    case_summary = (
        validate_abuse_cases(
            cases,
            original_users
        )
    )

    print(
        f"   Episodes: "
        f"{case_summary['episodes']:,}"
    )

    print(
        f"   Unique case users: "
        f"{case_summary['unique_case_users']:,}"
    )

    print(
        f"   Channels: "
        f"{case_summary['channels']}"
    )

    print("   PASS")

    print(
        "10. Validating injected "
        "behavior against cases..."
    )

    injected_offline = (
        build_injected_event_index(
            raw_offline_rows,
            SOURCE_OFFLINE,
            "offline"
        )
    )

    injected_online = (
        build_injected_event_index(
            raw_online_rows,
            SOURCE_ONLINE,
            "online"
        )
    )

    behavior_summary = (
        validate_case_behavior(
            cases,
            injected_offline,
            injected_online
        )
    )

    print("   PASS")

    report = {
        "status": "PASS",

        "raw_files": {
            "offline_rows":
                raw_offline_rows,
            "online_rows":
                raw_online_rows,
            "offline_sha256":
                offline_hash,
            "online_sha256":
                online_hash,
        },

        "source_files": {
            "offline_rows":
                source_offline_rows,
            "online_rows":
                source_online_rows,
            "offline_added_rows":
                (
                    source_offline_rows
                    - raw_offline_rows
                ),
            "online_added_rows":
                (
                    source_online_rows
                    - raw_online_rows
                ),
        },

        "dates": date_summary,

        "abuse_cases": case_summary,

        "behavior_validation":
            behavior_summary,
    }

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    OUTPUT_REPORT.write_text(
        json.dumps(
            report,
            indent=2
        )
    )

    print(
        "\n================================"
    )

    print(
        "SOURCE VALIDATION: PASS"
    )

    print(
        "================================"
    )

    print(
        f"\nValidation report written to:\n"
        f"{OUTPUT_REPORT.relative_to(ROOT)}"
    )


if __name__ == "__main__":
    main()