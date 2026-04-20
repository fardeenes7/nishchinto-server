from marketing.models import SocialConnection, ProductSocialPostLog


def list_social_connections(*, shop_id: str):
    return SocialConnection.objects.filter(
        shop_id=shop_id,
        deleted_at__isnull=True,
    ).order_by("-created_at")


def list_product_social_logs(*, shop_id: str, product_id: str):
    return ProductSocialPostLog.objects.select_related("connection").filter(
        shop_id=shop_id,
        product_id=product_id,
        deleted_at__isnull=True,
    ).order_by("-created_at")
