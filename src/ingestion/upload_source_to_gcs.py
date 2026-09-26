from __future__ import annotations

import argparse
import base64
import hashlib
from pathlib import Path

from google.cloud import storage


ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = ROOT / "data" / "source"

SOURCE_FILES = [
    "offline_events.csv",
    "online_events.csv",
    "abuse_cases.csv",
    "generation_summary.json",
]


def local_md5(path: Path) -> str:
    digest = hashlib.md5()

    with path.open("rb") as f:
        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return base64.b64encode(
        digest.digest()
    ).decode("utf-8")


def upload_file(
    bucket: storage.Bucket,
    local_path: Path,
    object_name: str,
) -> str:

    blob = bucket.blob(object_name)

    if blob.exists():
        blob.reload()

        local_hash = local_md5(
            local_path
        )

        if blob.md5_hash == local_hash:
            print(
                f"SKIP: {object_name} "
                f"already exists with matching checksum"
            )
            return "skipped"

        raise RuntimeError(
            f"{object_name} already exists "
            f"but does not match the local file."
        )

    print(
        f"UPLOAD: {local_path.name} "
        f"-> gs://{bucket.name}/{object_name}"
    )

    blob.upload_from_filename(
        str(local_path)
    )

    blob.reload()

    local_hash = local_md5(
        local_path
    )

    if blob.md5_hash != local_hash:
        raise RuntimeError(
            f"Checksum validation failed "
            f"for {object_name}"
        )

    print(
        f"PASS: checksum verified "
        f"for {object_name}"
    )

    return "uploaded"


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--bucket",
        required=True,
        help="Destination GCS bucket name",
    )

    parser.add_argument(
        "--prefix",
        default="source",
        help="Folder/prefix inside the bucket",
    )

    args = parser.parse_args()

    print(
        "\nAlibaba Promotion Abuse "
        "GCS Ingestion\n"
    )

    for filename in SOURCE_FILES:

        path = (
            SOURCE_DIR / filename
        )

        if not path.exists():
            raise FileNotFoundError(
                f"Missing source file: {path}"
            )

    client = storage.Client()

    bucket = client.bucket(
        args.bucket
    )

    if not bucket.exists():
        raise RuntimeError(
            f"Bucket does not exist: "
            f"{args.bucket}"
        )

    uploaded = 0
    skipped = 0

    for filename in SOURCE_FILES:

        local_path = (
            SOURCE_DIR / filename
        )

        object_name = (
            f"{args.prefix}/{filename}"
        )

        result = upload_file(
            bucket,
            local_path,
            object_name,
        )

        if result == "uploaded":
            uploaded += 1
        else:
            skipped += 1

    print(
        "\n================================"
    )

    print(
        "GCS INGESTION COMPLETE"
    )

    print(
        "================================"
    )

    print(
        f"Uploaded: {uploaded}"
    )

    print(
        f"Skipped:  {skipped}"
    )


if __name__ == "__main__":
    main()