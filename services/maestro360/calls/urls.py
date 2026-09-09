from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("routing-rules", views.RoutingRuleViewSet, basename="routing-rule")

urlpatterns = [
    path("calls/summary/", views.call_summary, name="call-summary"),
    path("calls/", views.call_events, name="call-events"),
    path("webhooks/call-events/", views.ingest_call_events, name="ingest-call-events"),
    path("", include(router.urls)),
]
