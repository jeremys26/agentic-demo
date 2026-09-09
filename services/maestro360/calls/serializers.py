from rest_framework import serializers

from .models import CallEvent, ClientAgentPool, RoutingRule


class ClientAgentPoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientAgentPool
        fields = [
            "id",
            "name",
            "vertical_specialty",
            "historical_conversion_rate",
            "is_certified_medicare",
        ]


class RoutingRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoutingRule
        fields = ["id", "priority", "pool", "description"]


class CallEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = CallEvent
        fields = [
            "id",
            "campaign_id",
            "timestamp",
            "routed_pool",
            "wait_time_seconds",
            "duration_seconds",
            "outcome",
        ]
