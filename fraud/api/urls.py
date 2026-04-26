from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FraudViewSet

router = DefaultRouter()
router.register(r'', FraudViewSet, basename='fraud')

urlpatterns = [
    path('', include(router.urls)),
]
