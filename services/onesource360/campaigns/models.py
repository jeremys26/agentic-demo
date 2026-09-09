from django.db import models


class Campaign(models.Model):
    """Vertical and Channel are TextChoices, not lookup tables.

    PLANNING.md §6 listed them as models; they stayed as choices because
    they have no attributes of their own, and promoting them to tables
    wouldn't change anything the rest of the system does.
    """

    class Vertical(models.TextChoices):
        MEDICARE_ADVANTAGE = "medicare_advantage", "Medicare Advantage"
        INSURANCE = "insurance", "Insurance"
        HOME_SERVICES = "home_services", "Home Services"

    class Channel(models.TextChoices):
        TV = "tv", "TV"
        RADIO = "radio", "Radio"
        DIRECT_MAIL = "direct_mail", "Direct Mail"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        ENDED = "ended", "Ended"

    name = models.CharField(max_length=200)
    vertical = models.CharField(max_length=32, choices=Vertical.choices)
    channel = models.CharField(max_length=32, choices=Channel.choices)
    target_cpl = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.name


class DailyPerformanceRollup(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="rollups")
    date = models.DateField()
    spend = models.DecimalField(max_digits=10, decimal_places=2)
    leads = models.PositiveIntegerField()
    calls = models.PositiveIntegerField(default=0)
    conversions = models.PositiveIntegerField(default=0)
    cpl = models.DecimalField(max_digits=10, decimal_places=2)
    roas = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    class Meta:
        unique_together = ("campaign", "date")
        ordering = ["date"]

    def __str__(self):
        return f"{self.campaign.name} — {self.date}"
