from __future__ import annotations

import logging
from celery import shared_task
from django.db import transaction

from core.services.ai_gateway import AIGateway

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    queue="ai_rag",
    name="messenger.tasks.embed_faq_entry",
)
def embed_faq_entry(self, *, faq_entry_id: str) -> None:
    """
    Generate pgvector embedding for a FAQEntry and persist to DB.
    """
    from messenger.models import FAQEntry

    try:
        entry = FAQEntry.objects.get(id=faq_entry_id, deleted_at__isnull=True)
    except FAQEntry.DoesNotExist:
        logger.warning("embed_faq_entry: FAQEntry %s not found", faq_entry_id)
        return

    text = f"Category: {entry.category}\nQuestion: {entry.question}\nAnswer: {entry.answer}"
    gateway = AIGateway(str(entry.shop_id))

    try:
        vector = gateway.call_embedding(text=text)
        entry.embedding = vector
        entry.save(update_fields=["embedding", "updated_at"])
        logger.info("Embedded FAQEntry %s successfully.", faq_entry_id)
    except Exception as exc:
        logger.error("Embedding failed for FAQEntry %s: %s", faq_entry_id, exc)
        self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    queue="ai_rag",
    name="messenger.tasks.embed_product_specs",
)
def embed_product_specs(self, *, product_id: str) -> None:
    """
    Generate pgvector embedding for Product Specs and persist to DB.
    Includes: Name, Description, and Specifications JSON.
    """
    from catalog.models import Product

    try:
        product = Product.objects.get(id=product_id, deleted_at__isnull=True)
    except Product.DoesNotExist:
        logger.warning("embed_product_specs: Product %s not found", product_id)
        return

    # Build semantic text representation
    specs_str = "\n".join([f"{k}: {v}" for k, v in product.specifications.items()])
    text = (
        f"Product Name: {product.name}\n"
        f"Description: {product.description}\n"
        f"Specs:\n{specs_str}"
    )
    
    gateway = AIGateway(str(product.shop_id))

    try:
        vector = gateway.call_embedding(text=text)
        product.embedding = vector
        product.save(update_fields=["embedding", "updated_at"])
        logger.info("Embedded Product %s successfully.", product_id)
    except Exception as exc:
        logger.error("Embedding failed for Product %s: %s", product_id, exc)
        self.retry(exc=exc)
