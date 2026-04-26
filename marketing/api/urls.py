from django.urls import path
from .views import WaitlistCreateView, AdminWaitlistView, AdminWaitlistApproveView
from .social_views import (
    SocialOAuthStartView,
    SocialOAuthCallbackView,
    SocialConnectionListCreateView,
    SocialConnectionDisconnectView,
    SocialPublishView,
    SocialBulkPublishView,
    ProductSocialActivityView,
)
from .ad_views import MetaAdsViewSet

urlpatterns = [
    # Meta Ads (v0.9)
    path('ads/available-accounts/', MetaAdsViewSet.as_view({'get': 'available_accounts'}), name='meta_ads_available_accounts'),
    path('ads/link-account/', MetaAdsViewSet.as_view({'post': 'link_account'}), name='meta_ads_link_account'),

    # Public
    path('waitlist/', WaitlistCreateView.as_view(), name='waitlist_create'),
    
    # Operations
    path('admin/waitlist/', AdminWaitlistView.as_view(), name='admin_waitlist_list'),
    path('admin/waitlist/<int:pk>/approve/', AdminWaitlistApproveView.as_view(), name='admin_waitlist_approve'),

    # Social connection + publishing (v0.4)
    path('social/connect/start/', SocialOAuthStartView.as_view(), name='social_oauth_start'),
    path('social/connect/callback/', SocialOAuthCallbackView.as_view(), name='social_oauth_callback'),
    path('social/connections/', SocialConnectionListCreateView.as_view(), name='social_connection_list_create'),
    path('social/connections/<uuid:connection_id>/disconnect/', SocialConnectionDisconnectView.as_view(), name='social_connection_disconnect'),
    path('social/publish/', SocialPublishView.as_view(), name='social_publish_single'),
    path('social/publish/bulk/', SocialBulkPublishView.as_view(), name='social_publish_bulk'),
    path('social/products/<uuid:product_id>/activity/', ProductSocialActivityView.as_view(), name='social_product_activity'),
]
