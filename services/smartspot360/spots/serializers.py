from rest_framework import serializers

from .models import BudgetRecommendation, Daypart, Spot, SpotPerformance, Station


class StationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Station
        fields = ["id", "market", "medium", "name"]


class DaypartSerializer(serializers.ModelSerializer):
    class Meta:
        model = Daypart
        fields = ["id", "name", "cost_multiplier"]


class SpotSerializer(serializers.ModelSerializer):
    station_name = serializers.CharField(source="station.name", read_only=True)
    daypart_name = serializers.CharField(source="daypart.name", read_only=True)
    station_medium = serializers.CharField(source="station.medium", read_only=True)

    class Meta:
        model = Spot
        fields = [
            "id",
            "campaign_id",
            "station",
            "station_name",
            "station_medium",
            "daypart",
            "daypart_name",
            "air_date",
            "cost",
            "creative_label",
        ]


class SpotPerformanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpotPerformance
        fields = ["id", "spot", "calls", "conversions", "cpl"]


class SpotDetailSerializer(serializers.ModelSerializer):
    performance = SpotPerformanceSerializer(read_only=True)
    station_medium = serializers.CharField(source="station.medium", read_only=True)

    class Meta:
        model = Spot
        fields = [
            "id",
            "campaign_id",
            "station",
            "station_medium",
            "daypart",
            "air_date",
            "cost",
            "creative_label",
            "performance",
        ]


class BudgetRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = BudgetRecommendation
        fields = [
            "id",
            "campaign_id",
            "budget_amount",
            "allocation",
            "rationale",
            "confidence",
            "created_at",
            "applied",
            "applied_at",
        ]
