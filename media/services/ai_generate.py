import logging
import requests
import uuid
from django.conf import settings
from media.services.upload import confirm_media_upload, _get_s3_client

logger = logging.getLogger(__name__)

def save_ai_generated_image(*, shop_id: str, user_id: str, image_url: str) -> "Media":
    """
    Downloads an AI-generated image from a temporary URL and saves it to permanent storage.
    """
    try:
        # 1. Download image
        resp = requests.get(image_url, timeout=30)
        if resp.status_code != 200:
            raise ValueError(f"Failed to download image from AI provider (status {resp.status_code}).")

        # 2. Prepare S3 upload
        unique_id = uuid.uuid4().hex
        # We assume DALL-E 3 returns a PNG or WEBP. We save as webp.
        s3_key = f"shops/{shop_id}/media/ai_{unique_id}.webp"
        
        client = _get_s3_client()
        client.put_object(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=s3_key,
            Body=resp.content,
            ContentType="image/webp"
        )

        # 3. Create Media record
        media = confirm_media_upload(
            shop_id=shop_id,
            s3_key=s3_key,
            original_filename=f"ai_gen_{unique_id}.webp",
            user_id=user_id
        )
        
        logger.info("Saved AI generated image for shop %s as media %s", shop_id, media.id)
        return media

    except Exception as e:
        logger.error("Failed to save AI generated image: %s", e)
        raise e
