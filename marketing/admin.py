from django.contrib import admin

from marketing.models import WaitlistEntry, SocialConnection, ProductSocialPostLog


@admin.register(WaitlistEntry)
class WaitlistEntryAdmin(admin.ModelAdmin):
    list_display = ["email", "phone_number", "status", "created_at"]
    search_fields = ["email", "phone_number"]
    list_filter = ["status"]


@admin.register(SocialConnection)
class SocialConnectionAdmin(admin.ModelAdmin):
    list_display = ["shop", "provider", "page_name", "status", "token_expires_at", "updated_at"]
    search_fields = ["shop__name", "page_name", "page_id"]
    list_filter = ["provider", "status"]


@admin.register(ProductSocialPostLog)
class ProductSocialPostLogAdmin(admin.ModelAdmin):
    list_display = ["shop", "product", "connection", "status", "retry_count", "published_at", "created_at"]
    search_fields = ["product__name", "connection__page_name", "external_post_id", "idempotency_key"]
    list_filter = ["status", "connection__provider"]
