from django.db import models


class ClientAgentPool(models.Model):
    # Reuses the same vertical values/labels as OneSource360-sim's
    # Campaign.Vertical so the two services can be correlated by value
    # string even though they don't share a database (PLANNING.md §5).
    class Vertical(models.TextChoices):
        MEDICARE_ADVANTAGE = "medicare_advantage", "Medicare Advantage"
        INSURANCE = "insurance", "Insurance"
        HOME_SERVICES = "home_services", "Home Services"

    name = models.CharField(max_length=100)
    vertical_specialty = models.CharField(max_length=32, choices=Vertical.choices)
    historical_conversion_rate = models.DecimalField(max_digits=5, decimal_places=4)
    # PLANNING.md §9: the real compliance detail behind the demo's headline
    # scenario — Pool B is not Medicare-certified and converts lower, so
    # call volume quietly shifting into it is both a performance and a
    # compliance problem.
    is_certified_medicare = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class RoutingRule(models.Model):
    priority = models.PositiveIntegerField()
    pool = models.ForeignKey(ClientAgentPool, on_delete=models.CASCADE, related_name="routing_rules")
    description = models.TextField()

    class Meta:
        ordering = ["priority"]

    def __str__(self):
        return f"#{self.priority} — {self.pool.name}"


class CallEvent(models.Model):
    # No ForeignKey: the Campaign this call belongs to lives in
    # OneSource360-sim's own database. Services are independent (own DB,
    # HTTP-only) per PLANNING.md §5, so cross-service references are plain
    # external ids, not FKs.
    class Outcome(models.TextChoices):
        CONVERSION = "conversion", "Conversion"
        NO_ANSWER = "no_answer", "No Answer"
        VOICEMAIL = "voicemail", "Voicemail"
        DROPPED = "dropped", "Dropped"

    campaign_id = models.PositiveIntegerField()
    timestamp = models.DateTimeField()
    routed_pool = models.ForeignKey(ClientAgentPool, on_delete=models.CASCADE, related_name="call_events")
    wait_time_seconds = models.PositiveIntegerField()
    duration_seconds = models.PositiveIntegerField()
    outcome = models.CharField(max_length=16, choices=Outcome.choices)

    class Meta:
        ordering = ["timestamp"]

    def __str__(self):
        return f"Call #{self.id} — campaign {self.campaign_id} @ {self.timestamp}"
