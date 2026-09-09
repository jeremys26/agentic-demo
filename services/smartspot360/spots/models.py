from django.db import models


class Station(models.Model):
    class Medium(models.TextChoices):
        TV = "tv", "TV"
        RADIO = "radio", "Radio"

    market = models.CharField(max_length=100)
    medium = models.CharField(max_length=16, choices=Medium.choices)
    name = models.CharField(max_length=150)

    def __str__(self):
        return f"{self.name} ({self.market})"


class Daypart(models.Model):
    name = models.CharField(max_length=50)
    cost_multiplier = models.DecimalField(max_digits=4, decimal_places=2)

    def __str__(self):
        return self.name


class Spot(models.Model):
    # No ForeignKey: the Campaign this spot belongs to lives in OneSource360-sim's
    # own database. Services are independent (own DB, HTTP-only) per PLANNING.md
    # §5, so cross-service references are plain external ids, not FKs.
    campaign_id = models.PositiveIntegerField()
    station = models.ForeignKey(Station, on_delete=models.CASCADE, related_name="spots")
    daypart = models.ForeignKey(Daypart, on_delete=models.CASCADE, related_name="spots")
    air_date = models.DateField()
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    creative_label = models.CharField(max_length=50, blank=True)

    class Meta:
        ordering = ["air_date"]

    def __str__(self):
        return f"Spot #{self.id} — {self.station.name} / {self.daypart.name} on {self.air_date}"


class SpotPerformance(models.Model):
    spot = models.OneToOneField(Spot, on_delete=models.CASCADE, related_name="performance")
    calls = models.PositiveIntegerField(default=0)
    conversions = models.PositiveIntegerField(default=0)
    cpl = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"Performance for spot #{self.spot_id}"


class BudgetRecommendation(models.Model):
    # Same external-reference reasoning as Spot.campaign_id above.
    campaign_id = models.PositiveIntegerField()
    budget_amount = models.DecimalField(max_digits=10, decimal_places=2)
    allocation = models.JSONField()
    rationale = models.TextField()
    confidence = models.DecimalField(max_digits=4, decimal_places=3)
    created_at = models.DateTimeField(auto_now_add=True)
    # Set when the MCP server's risk-scoring guardrail (PLANNING.md §7) has
    # cleared this recommendation for execution — auto-executed immediately,
    # or approved by a human. This service has no opinion on risk; it just
    # records whether the reallocation it recommended actually went into
    # effect.
    applied = models.BooleanField(default=False)
    applied_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Recommendation for campaign {self.campaign_id} — ${self.budget_amount}"
