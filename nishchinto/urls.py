from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

# Optional drf-spectacular integration for API Schema
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from users.api.sso_views import SSOHubView
from catalog.api.urls import storefront_urlpatterns
from orders.api.urls import storefront_urlpatterns as order_storefront_urlpatterns

urlpatterns = [
    path('admin/', admin.site.urls),
    path('sso/hub/', SSOHubView.as_view(), name='sso_hub'),

    # Global Auth Token endpoints
    path('api/v1/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # OpenAPI Schema Configuration
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # App-specific endpoints
    path('api/v1/marketing/', include('marketing.api.urls')),
    path('api/v1/shops/', include('shops.api.urls')),
    path('api/v1/catalog/', include('catalog.api.urls')),
    path('api/v1/storefront/', include(storefront_urlpatterns + order_storefront_urlpatterns)),
    path('api/v1/media/', include('media.api.urls')),
    # path('api/v1/users/', include('users.api.urls')),
]
