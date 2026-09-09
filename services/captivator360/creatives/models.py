from django.db import models


class CreativeAsset(models.Model):
    # No ForeignKey: the Campaign this creative belongs to lives in
    # OneSource360-sim's own database. Services are independent (own DB,
    # HTTP-only) per PLANNING.md §5, so cross-service references are plain
    # external ids, not FKs.
    class Channel(models.TextChoices):
        TV = "tv", "TV"
        RADIO = "radio", "Radio"
        DIRECT_MAIL = "direct_mail", "Direct Mail"

    campaign_id = models.PositiveIntegerField()
    variant_label = models.CharField(max_length=50)
    channel = models.CharField(max_length=32, choices=Channel.choices)
    created_date = models.DateField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.variant_label


class CreativePerformanceDaily(models.Model):
    creative = models.ForeignKey(
        CreativeAsset, on_delete=models.CASCADE, related_name="daily_performance"
    )
    date = models.DateField()
    impressions = models.PositiveIntegerField(default=0)
    ctr = models.DecimalField(max_digits=5, decimal_places=4)
    conversion_rate = models.DecimalField(max_digits=5, decimal_places=4)

    class Meta:
        unique_together = ("creative", "date")
        ordering = ["date"]

    def __str__(self):
        return f"{self.creative.variant_label} — {self.date}"


class CreativeRefreshRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    creative = models.ForeignKey(
        CreativeAsset, on_delete=models.CASCADE, related_name="refresh_requests"
    )
    reason = models.TextField()
    requested_at = models.DateTimeField(auto_now_add=True)
    # This service stores request state only. Whether a refresh auto-executes,
    # needs human approval, or is blocked is decided by the MCP server's
    # risk-scoring guardrail (PLANNING.md §7), not here.
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)

    class Meta:
        ordering = ["-requested_at"]

    def __str__(self):
        return f"Refresh request for {self.creative.variant_label} ({self.status})"
