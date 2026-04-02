import os
import shutil
import uuid
from urllib.parse import urlparse
from urllib.request import urlretrieve

import boto3
from botocore.exceptions import ClientError


def configure_storage_env(level: str) -> str:
    # Single-bucket mode for simpler deployments.
    if (
        os.environ.get("AWS_ACCESS_KEY_ID")
        and os.environ.get("AWS_SECRET_ACCESS_KEY")
        and os.environ.get("OUTPUT_S3_BUCKET")
    ):
        os.environ.setdefault("AWS_REGION", "us-east-2")
        return os.environ["OUTPUT_S3_BUCKET"]

    if level not in ("stag", "prod"):
        raise ValueError("level must be 'stag' or 'prod'")

    if level == "stag":
        os.environ["AWS_ACCESS_KEY_ID"] = os.environ["STAG_AWS_ACCESS_KEY_ID"]
        os.environ["AWS_SECRET_ACCESS_KEY"] = os.environ["STAG_AWS_SECRET_ACCESS_KEY"]
        bucket = os.environ["STAG_S3_BUCKET"]
    else:
        os.environ["AWS_ACCESS_KEY_ID"] = os.environ["PROD_AWS_ACCESS_KEY_ID"]
        os.environ["AWS_SECRET_ACCESS_KEY"] = os.environ["PROD_AWS_SECRET_ACCESS_KEY"]
        bucket = os.environ["PROD_S3_BUCKET"]

    os.environ.setdefault("AWS_REGION", "us-east-2")
    return bucket


def get_s3_client():
    return boto3.client(
        "s3",
        aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
        region_name=os.environ.get("AWS_REGION", "us-east-2"),
    )


def download_to_local(source: str, local_path: str):
    if source.startswith("s3://"):
        parsed = urlparse(source)
        bucket = parsed.netloc
        key = parsed.path.lstrip("/")
        try:
            get_s3_client().download_file(bucket, key, local_path)
        except ClientError as exc:
            raise RuntimeError(f"Failed to download S3 object: {source} ({exc})") from exc
        return

    if source.startswith("http://") or source.startswith("https://"):
        urlretrieve(source, local_path)
        return

    shutil.copy(source, local_path)


def upload_asset(
    local_path: str,
    bucket: str,
    key_prefix: str,
    suffix: str,
    content_type: str,
) -> dict:
    key = f"{key_prefix.rstrip('/')}/{uuid.uuid4()}{suffix}"
    s3 = get_s3_client()
    s3.upload_file(local_path, bucket, key, ExtraArgs={"ContentType": content_type})
    presigned_url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=86400,
    )
    return {"s3_uri": f"s3://{bucket}/{key}", "presigned_url": presigned_url}


def upload_video(local_path: str, bucket: str, key_prefix: str) -> dict:
    return upload_asset(
        local_path=local_path,
        bucket=bucket,
        key_prefix=key_prefix,
        suffix=".mp4",
        content_type="video/mp4",
    )
