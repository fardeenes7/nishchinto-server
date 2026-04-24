from django.urls import path

from webhooks.api.views import MetaWebhookIngestView

urlpatterns = [
    path("meta/", MetaWebhookIngestView.as_view(), name="webhook-meta-ingest"),
]
