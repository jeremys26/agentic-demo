from rest_framework import serializers

from .models import CreativeAsset, CreativePerformanceDaily, CreativeRefreshRequest


class CreativeAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreativeAsset
        fields = [
            "id",
            "campaign_id",
            "variant_label",
            "channel",
            "created_date",
            "is_active",
        ]


class CreativePerformanceDailySerializer(serializers.ModelSerializer):
    class Meta:
        model = CreativePerformanceDaily
        fields = [
            "id",
            "creative",
            "date",
            "impressions",
            "ctr",
            "conversion_rate",
        ]


class CreativeRefreshRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreativeRefreshRequest
        fields = ["id", "creative", "reason", "requested_at", "status"]
