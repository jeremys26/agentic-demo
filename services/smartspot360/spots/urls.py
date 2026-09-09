from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("spots", views.SpotViewSet, basename="spot")

urlpatterns = [
    path("", include(router.urls)),
    path("spots/<int:pk>/performance/", views.spot_performance, name="spot-performance"),
    path("recommendations/", views.recommend_budget, name="recommend-budget"),
    path("recommendations/<int:pk>/", views.get_recommendation, name="get-recommendation"),
    path("recommendations/<int:pk>/apply/", views.apply_recommendation, name="apply-recommendation"),
    path("webhooks/spot-performance/", views.ingest_spot_performance, name="ingest-spot-performance"),
]
