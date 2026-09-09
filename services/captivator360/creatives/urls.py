from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("creatives", views.CreativeAssetViewSet, basename="creative")

urlpatterns = [
    path("creatives/declining/", views.declining_creatives, name="declining-creatives"),
    path("creatives/<int:pk>/performance/", views.creative_performance, name="creative-performance"),
    path("creatives/<int:pk>/refresh-request/", views.refresh_request, name="creative-refresh-request"),
    path(
        "creatives/refresh-requests/<int:pk>/resolve/",
        views.resolve_refresh_request,
        name="resolve-refresh-request",
    ),
    path("webhooks/creative-metrics/", views.ingest_creative_metrics, name="ingest-creative-metrics"),
    path("", include(router.urls)),
]
