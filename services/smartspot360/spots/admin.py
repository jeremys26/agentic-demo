from django.contrib import admin

from .models import BudgetRecommendation, Daypart, Spot, SpotPerformance, Station


@admin.register(Station)
class StationAdmin(admin.ModelAdmin):
    list_display = ["name", "market", "medium"]
    list_filter = ["medium", "market"]


@admin.register(Daypart)
class DaypartAdmin(admin.ModelAdmin):
    list_display = ["name", "cost_multiplier"]


@admin.register(Spot)
class SpotAdmin(admin.ModelAdmin):
    list_display = ["id", "campaign_id", "station", "daypart", "air_date", "cost"]
    list_filter = ["station", "daypart"]


@admin.register(SpotPerformance)
class SpotPerformanceAdmin(admin.ModelAdmin):
    list_display = ["spot", "calls", "conversions", "cpl"]


@admin.register(BudgetRecommendation)
class BudgetRecommendationAdmin(admin.ModelAdmin):
    list_display = ["campaign_id", "budget_amount", "confidence", "created_at"]
    list_filter = ["campaign_id"]
    ordering = ["-created_at"]
