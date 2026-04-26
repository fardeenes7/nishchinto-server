from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AffiliateViewSet

router = DefaultRouter()
router.register(r'', AffiliateViewSet, basename='affiliate')

urlpatterns = [
    path('', include(router.urls)),
]
