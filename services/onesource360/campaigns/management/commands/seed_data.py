import datetime
import random

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from campaigns.models import Campaign, DailyPerformanceRollup

DEMO_START = datetime.date(2026, 8, 1)
DEMO_DAYS = 28


class Command(BaseCommand):
    """
    Full Phase 2 seed per PLANNING.md §9: the headline compound-cause CPL
    spike on one campaign (kept first, so it lands as id=1 — SmartSpot360-sim,
    Captivator360-sim, and Maestro360-sim's own seed commands correlate their
    data to this same campaign_id), plus several more campaigns across
    verticals for realistic breadth. Only the first campaign gets the
    deliberate anomaly; the rest are steady, unremarkable performers.
    """

    help = "Seed OneSource360-sim with the PLANNING.md §9 demo scenario plus supporting campaigns"

    def handle(self, *args, **options):
        random.seed(360)
        self._ensure_demo_user()

        flagged = self._seed_flagged_campaign()
        self.stdout.write(self.style.SUCCESS(f"Seeded flagged campaign id={flagged.id} '{flagged.name}'"))

        steady_campaigns = [
            ("Medicare Advantage – Northeast TV", Campaign.Vertical.MEDICARE_ADVANTAGE, Campaign.Channel.TV, 48.00),
            ("Insurance – Southeast TV", Campaign.Vertical.INSURANCE, Campaign.Channel.TV, 38.00),
            ("Insurance – Midwest Direct Mail", Campaign.Vertical.INSURANCE, Campaign.Channel.DIRECT_MAIL, 52.00),
            ("Home Services – West Radio", Campaign.Vertical.HOME_SERVICES, Campaign.Channel.RADIO, 30.00),
            ("Home Services – Southeast TV", Campaign.Vertical.HOME_SERVICES, Campaign.Channel.TV, 34.00),
        ]
        for name, vertical, channel, target_cpl in steady_campaigns:
            campaign = self._seed_steady_campaign(name, vertical, channel, target_cpl)
            self.stdout.write(self.style.SUCCESS(f"Seeded steady campaign id={campaign.id} '{campaign.name}'"))

    def _seed_flagged_campaign(self):
        campaign, _ = Campaign.objects.update_or_create(
            name="Medicare Advantage – Southeast TV",
            defaults=dict(
                vertical=Campaign.Vertical.MEDICARE_ADVANTAGE,
                channel=Campaign.Channel.TV,
                target_cpl=45.00,
                status=Campaign.Status.ACTIVE,
                start_date=DEMO_START,
            ),
        )
        DailyPerformanceRollup.objects.filter(campaign=campaign).delete()

        rollups = []
        for day_offset in range(DEMO_DAYS):
            date = DEMO_START + datetime.timedelta(days=day_offset)
            week = day_offset // 7  # 0, 1, 2 = baseline weeks; 3 = flagged week

            spend = round(random.uniform(7100, 7250), 2)
            leads = random.randint(150, 165) if week < 3 else random.randint(100, 112)

            cpl = round(spend / leads, 2)
            calls = round(leads * random.uniform(1.4, 1.6))
            conversions = round(leads * random.uniform(0.55, 0.65))

            rollups.append(
                DailyPerformanceRollup(
                    campaign=campaign,
                    date=date,
                    spend=spend,
                    leads=leads,
                    calls=calls,
                    conversions=conversions,
                    cpl=cpl,
                )
            )
        DailyPerformanceRollup.objects.bulk_create(rollups)
        return campaign

    def _seed_steady_campaign(self, name, vertical, channel, target_cpl):
        """No anomaly: daily CPL wobbles gently around target_cpl for all 28 days."""
        campaign, _ = Campaign.objects.update_or_create(
            name=name,
            defaults=dict(
                vertical=vertical,
                channel=channel,
                target_cpl=target_cpl,
                status=Campaign.Status.ACTIVE,
                start_date=DEMO_START,
            ),
        )
        DailyPerformanceRollup.objects.filter(campaign=campaign).delete()

        daily_budget = round(float(target_cpl) * random.uniform(140, 170), 2)
        rollups = []
        for day_offset in range(DEMO_DAYS):
            date = DEMO_START + datetime.timedelta(days=day_offset)
            spend = round(daily_budget * random.uniform(0.94, 1.06), 2)
            cpl = round(float(target_cpl) * random.uniform(0.92, 1.08), 2)
            leads = max(1, round(spend / cpl))
            calls = round(leads * random.uniform(1.3, 1.6))
            conversions = round(leads * random.uniform(0.45, 0.60))

            rollups.append(
                DailyPerformanceRollup(
                    campaign=campaign,
                    date=date,
                    spend=spend,
                    leads=leads,
                    calls=calls,
                    conversions=conversions,
                    cpl=cpl,
                )
            )
        DailyPerformanceRollup.objects.bulk_create(rollups)
        return campaign

    def _ensure_demo_user(self):
        user, _ = User.objects.get_or_create(username="demo", defaults={"email": "demo@localhost"})
        user.set_password("demo")
        user.save()
