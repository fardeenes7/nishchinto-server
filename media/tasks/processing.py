"""
Celery task: process_uploaded_media

Downloads the just-uploaded file from S3, converts it to WebP using Pillow,
re-uploads (overwriting), and updates the Media record with dimensions, MD5,
file size, and processing status.

Business rules enforced:
- 5 MB hard limit on images (Business Rules §1 - Technical Constraints)
- Backend-only WebP conversion (Phase 0.3 Step 1 requirement)
- EXIF data stripped (privacy)
"""
import hashlib
import io
import logging

import boto3
from celery import shared_task
from django.conf import settings
from PIL import Image

logger = logging.getLogger(__name__)

MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


def _get_s3_client():
    import boto3
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


@shared_task(
    bind=True,
    queue="media_processing",
    max_retries=3,
    default_retry_delay=30,
    autoretry_for=(Exception,),
)
def process_uploaded_media(self, *, media_id: str):
    """
    1. Download original file from S3
    2. Enforce 5 MB size limit
    3. Convert to WebP via Pillow (strip EXIF)
    4. Re-upload to same s3_key
    5. Update Media record
    """
    from media.models import Media

    try:
        media = Media.objects.get(id=media_id)
    except Media.DoesNotExist:
        logger.warning("process_uploaded_media: Media %s not found, skipping.", media_id)
        return

    media.processing_status = Media.ProcessingStatus.PROCESSING
    media.save(update_fields=["processing_status"])

    client = _get_s3_client()
    bucket = settings.AWS_STORAGE_BUCKET_NAME

    try:
        response = client.get_object(Bucket=bucket, Key=media.s3_key)
        raw_bytes = response["Body"].read()

        # ── Enforce 5 MB limit ──────────────────────────────────────────────
        if len(raw_bytes) > MAX_IMAGE_SIZE_BYTES:
            logger.warning(
                "Media %s exceeds 5 MB (%d bytes). Deleting from S3.",
                media_id,
                len(raw_bytes),
            )
            client.delete_object(Bucket=bucket, Key=media.s3_key)
            media.processing_status = Media.ProcessingStatus.FAILED
            media.save(update_fields=["processing_status"])
            return

        # ── Convert to WebP, strip EXIF ─────────────────────────────────────
        img = Image.open(io.BytesIO(raw_bytes))
        # EXIF strip: open without embedded color profile, re-save clean
        img_data = list(img.getdata())
        clean_img = Image.new(img.mode, img.size)
        clean_img.putdata(img_data)

        webp_buffer = io.BytesIO()
        clean_img.save(webp_buffer, format="WEBP", quality=85, method=4)
        webp_bytes = webp_buffer.getvalue()
        width, height = clean_img.size

        # ── Compute MD5 of final WebP bytes ────────────────────────────────
        md5 = hashlib.md5(webp_bytes).hexdigest()

        # ── Re-upload as WebP, replace original ────────────────────────────
        # Note: we overwrite at the same s3_key so CDN URLs stay consistent.
        client.put_object(
            Bucket=bucket,
            Key=media.s3_key,
            Body=webp_bytes,
            ContentType="image/webp",
            CacheControl="max-age=86400, public",
        )

        # ── Persist results ─────────────────────────────────────────────────
        media.width = width
        media.height = height
        media.md5_hash = md5
        media.file_size = len(webp_bytes)
        media.mime_type = "image/webp"
        media.processing_status = Media.ProcessingStatus.DONE
        media.save(
            update_fields=[
                "width", "height", "md5_hash", "file_size",
                "mime_type", "processing_status",
            ]
        )
        logger.info(
            "Media %s converted to WebP (%dx%d, %.1f KB).",
            media_id, width, height, len(webp_bytes) / 1024,
        )

    except Exception as exc:
        logger.exception("process_uploaded_media failed for %s: %s", media_id, exc)
        media.processing_status = Media.ProcessingStatus.FAILED
        media.save(update_fields=["processing_status"])
        raise
