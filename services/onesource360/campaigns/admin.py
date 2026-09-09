from django.contrib import admin

from .models import Campaign, DailyPerformanceRollup


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ["name", "vertical", "channel", "target_cpl", "status"]
    list_filter = ["vertical", "channel", "status"]


@admin.register(DailyPerformanceRollup)
class DailyPerformanceRollupAdmin(admin.ModelAdmin):
    list_display = ["campaign", "date", "spend", "leads", "cpl"]
    list_filter = ["campaign"]
    ordering = ["-date"]
