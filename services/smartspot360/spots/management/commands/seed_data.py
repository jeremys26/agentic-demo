import datetime
import random

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from spots.models import BudgetRecommendation, Daypart, Spot, SpotPerformance, Station

DEMO_START = datetime.date(2026, 8, 1)
DEMO_DAYS = 28
FLAGGED_CAMPAIGN_ID = 1  # OneSource360-sim's "Medicare Advantage – Southeast TV" (see its seed_data)


class Command(BaseCommand):
    """
    Seeds the same station/daypart mix for every day of the demo window per
    PLANNING.md §9: "No change — spend mix identical to prior weeks" in the
    flagged week. This is deliberate negative evidence — checking
    SmartSpot360-sim first during the investigation should rule out a media-
    buy change, not find one.
    """

    help = "Seed SmartSpot360-sim with the flat station/daypart mix from PLANNING.md §9"

    def handle(self, *args, **options):
        random.seed(360)
        user, _ = User.objects.get_or_create(username="demo", defaults={"email": "demo@localhost"})
        user.set_password("demo")
        user.save()

        station_tv, _ = Station.objects.update_or_create(
            name="WSVN Miami", defaults=dict(market="Southeast", medium=Station.Medium.TV)
        )
        station_radio, _ = Station.objects.update_or_create(
            name="WQBA Miami", defaults=dict(market="Southeast", medium=Station.Medium.RADIO)
        )
        daypart_daytime, _ = Daypart.objects.update_or_create(
            name="Daytime", defaults=dict(cost_multiplier=1.00)
        )
        daypart_prime, _ = Daypart.objects.update_or_create(
            name="Prime", defaults=dict(cost_multiplier=1.50)
        )

        Spot.objects.filter(campaign_id=FLAGGED_CAMPAIGN_ID).delete()
        BudgetRecommendation.objects.filter(campaign_id=FLAGGED_CAMPAIGN_ID).delete()

        combos = [
            (station_tv, daypart_daytime, 210.00),
            (station_radio, daypart_prime, 95.00),
        ]

        spots_created = 0
        for day_offset in range(DEMO_DAYS):
            air_date = DEMO_START + datetime.timedelta(days=day_offset)
            for station, daypart, base_cost in combos:
                cost = round(base_cost * float(daypart.cost_multiplier) * random.uniform(0.95, 1.05), 2)
                spot = Spot.objects.create(
                    campaign_id=FLAGGED_CAMPAIGN_ID,
                    station=station,
                    daypart=daypart,
                    air_date=air_date,
                    cost=cost,
                    creative_label="CR-114",
                )
                # Media-buy performance stays flat across all 4 weeks — the
                # anomaly lives in Captivator360-sim and Maestro360-sim, not
                # here, so per-spot CPL wobbles gently but never spikes.
                calls = random.randint(8, 14)
                conversions = random.randint(3, 6)
                cpl = round(cost / max(conversions, 1), 2)
                SpotPerformance.objects.create(
                    spot=spot, calls=calls, conversions=conversions, cpl=cpl
                )
                spots_created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {spots_created} spots (2 station/daypart combos x {DEMO_DAYS} days) "
                f"for campaign_id={FLAGGED_CAMPAIGN_ID}"
            )
        )
