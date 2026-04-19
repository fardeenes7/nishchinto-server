"""
Celery task: purge_orphaned_media

Scheduled daily at 02:00 UTC via Celery Beat.
Compares every S3 object key in the media bucket against DB records,
then deletes any S3 object with no corresponding (non-deleted) Media row.
"""
import logging

import boto3
from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)


def _get_s3_client():
    from typing import Any
    kwargs: dict[str, Any] = {
        "aws_access_key_id": settings.AWS_ACCESS_KEY_ID,
        "aws_secret_access_key": settings.AWS_SECRET_ACCESS_KEY,
        "region_name": getattr(settings, "AWS_S3_REGION_NAME", "us-east-1"),
    }
    endpoint = getattr(settings, "AWS_S3_ENDPOINT_URL", None)
    if endpoint:
        kwargs["endpoint_url"] = endpoint
    return boto3.client("s3", **kwargs)


@shared_task(queue="default", name="media.tasks.cleanup.purge_orphaned_media")
def purge_orphaned_media():
    """
    Paginate all S3 keys in the bucket, compare against active Media records,
    and delete any orphaned objects.

    An object is 'orphaned' if:
    - It lives under the shops/ prefix (tenant media)
    - It has no corresponding Media row with deleted_at IS NULL
    """
    from media.models import Media

    client = _get_s3_client()
    bucket = settings.AWS_STORAGE_BUCKET_NAME

    # Build a set of all valid (non-deleted) s3 keys for O(1) lookup
    active_keys = set(
        Media.objects.filter(deleted_at__isnull=True).values_list("s3_key", flat=True)
    )
    logger.info("purge_orphaned_media: %d active keys in DB.", len(active_keys))

    paginator = client.get_paginator("list_objects_v2")
    deleted_count = 0

    for page in paginator.paginate(Bucket=bucket, Prefix="shops/"):
        objects = page.get("Contents", [])
        to_delete = [
            {"Key": obj["Key"]}
            for obj in objects
            if obj["Key"] not in active_keys
        ]
        if to_delete:
            # Batch delete (up to 1000 per request per AWS spec)
            client.delete_objects(
                Bucket=bucket, Delete={"Objects": to_delete, "Quiet": True}
            )
            deleted_count += len(to_delete)
            logger.info(
                "purge_orphaned_media: Deleted %d orphaned objects.", len(to_delete)
            )

    logger.info(
        "purge_orphaned_media: Completed. Total deleted = %d.", deleted_count
    )
    return {"deleted": deleted_count}
