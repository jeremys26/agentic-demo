from django.contrib import admin

from .models import CreativeAsset, CreativePerformanceDaily, CreativeRefreshRequest


@admin.register(CreativeAsset)
class CreativeAssetAdmin(admin.ModelAdmin):
    list_display = ["variant_label", "campaign_id", "channel", "created_date", "is_active"]
    list_filter = ["channel", "is_active"]


@admin.register(CreativePerformanceDaily)
class CreativePerformanceDailyAdmin(admin.ModelAdmin):
    list_display = ["creative", "date", "impressions", "ctr", "conversion_rate"]
    list_filter = ["creative"]
    ordering = ["-date"]


@admin.register(CreativeRefreshRequest)
class CreativeRefreshRequestAdmin(admin.ModelAdmin):
    list_display = ["creative", "status", "requested_at"]
    list_filter = ["status"]
    ordering = ["-requested_at"]
