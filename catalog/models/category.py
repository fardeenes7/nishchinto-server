"""
Category model.

Hierarchical categories are per-shop. Supports one level of parent nesting
(effectively unlimited depth but only one parent reference). We use a simple
adjacency list — full tree queries handled in selectors via recursive CTEs.
"""
import uuid

from django.db import models
from django.utils.text import slugify

from core.models import TenantModel


class Category(TenantModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shop = models.ForeignKey(
        "shops.Shop",
        on_delete=models.CASCADE,
        related_name="categories",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
    )
    name = models.CharField(max_length=255)
    slug = models.CharField(max_length=255, db_index=False)  # covered by compound index
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        # Enforce slug uniqueness per shop at the DB level (excludes soft-deleted)
        constraints = [
            models.UniqueConstraint(
                fields=["shop", "slug"],
                condition=models.Q(deleted_at__isnull=True),
                name="uq_category_shop_slug_active",
            )
        ]
        indexes = [
            models.Index(
                fields=["shop", "parent"],
                name="category_shop_parent_idx",
                condition=models.Q(deleted_at__isnull=True),
            ),
            models.Index(
                fields=["shop", "sort_order"],
                name="category_shop_sort_idx",
                condition=models.Q(deleted_at__isnull=True),
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.shop_id})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
