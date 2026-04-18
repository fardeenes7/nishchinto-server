from django.urls import path
from .views import WaitlistCreateView, AdminWaitlistView, AdminWaitlistApproveView

urlpatterns = [
    # Public
    path('waitlist/', WaitlistCreateView.as_view(), name='waitlist_create'),
    
    # Operations
    path('admin/waitlist/', AdminWaitlistView.as_view(), name='admin_waitlist_list'),
    path('admin/waitlist/<int:pk>/approve/', AdminWaitlistApproveView.as_view(), name='admin_waitlist_approve'),
]
