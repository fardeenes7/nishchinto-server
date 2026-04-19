from django.urls import path
from media.api.views import ConfirmUploadView, MediaDeleteView, PresignedUploadURLView

urlpatterns = [
    path("upload-url/", PresignedUploadURLView.as_view(), name="media-upload-url"),
    path("confirm/", ConfirmUploadView.as_view(), name="media-confirm-upload"),
    path("<uuid:media_id>/", MediaDeleteView.as_view(), name="media-delete"),
]
