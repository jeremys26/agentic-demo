from django.contrib import admin

from .models import CallEvent, ClientAgentPool, RoutingRule


@admin.register(ClientAgentPool)
class ClientAgentPoolAdmin(admin.ModelAdmin):
    list_display = ["name", "vertical_specialty", "historical_conversion_rate", "is_certified_medicare"]
    list_filter = ["vertical_specialty", "is_certified_medicare"]


@admin.register(RoutingRule)
class RoutingRuleAdmin(admin.ModelAdmin):
    list_display = ["priority", "pool", "description"]
    ordering = ["priority"]


@admin.register(CallEvent)
class CallEventAdmin(admin.ModelAdmin):
    list_display = ["id", "campaign_id", "timestamp", "routed_pool", "outcome"]
    list_filter = ["routed_pool", "outcome"]
    ordering = ["-timestamp"]
