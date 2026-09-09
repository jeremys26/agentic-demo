from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("campaigns", views.CampaignViewSet, basename="campaign")

urlpatterns = [
    path("", include(router.urls)),
    path("performance/", views.performance, name="performance"),
    path("webhooks/daily-performance/", views.ingest_daily_performance, name="ingest-daily-performance"),
]
