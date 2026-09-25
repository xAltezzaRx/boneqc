import boto3
from botocore.config import Config

from app.core.config import get_settings


class ObjectStorage:
    def __init__(self) -> None:
        settings = get_settings()

        self.bucket = settings.s3_bucket

        self.client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name="us-east-1",
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
                connect_timeout=3,
                read_timeout=10,
                retries={"max_attempts": 2},
            ),
        )

    def healthcheck(self) -> None:
        self.client.head_bucket(Bucket=self.bucket)

    def put_bytes(
        self,
        *,
        key: str,
        data: bytes,
        content_type: str,
    ) -> None:
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )

    def get_bytes(self, *, key: str) -> bytes:
        response = self.client.get_object(
            Bucket=self.bucket,
            Key=key,
        )

        return response["Body"].read()

    def delete_object(self, *, key: str) -> None:
        self.client.delete_object(
            Bucket=self.bucket,
            Key=key,
        )


storage = ObjectStorage()
