from rest_framework import serializers

from .models import Campaign, DailyPerformanceRollup


class CampaignSerializer(serializers.ModelSerializer):
    class Meta:
        model = Campaign
        fields = [
            "id",
            "name",
            "vertical",
            "channel",
            "target_cpl",
            "status",
            "start_date",
            "end_date",
        ]


class DailyPerformanceRollupSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyPerformanceRollup
        fields = [
            "id",
            "campaign",
            "date",
            "spend",
            "leads",
            "calls",
            "conversions",
            "cpl",
            "roas",
        ]
