import datetime
import random

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from creatives.models import CreativeAsset, CreativePerformanceDaily, CreativeRefreshRequest

DEMO_START = datetime.date(2026, 8, 1)
DEMO_DAYS = 28
FLAGGED_CAMPAIGN_ID = 1  # OneSource360-sim's "Medicare Advantage – Southeast TV" (see its seed_data)


class Command(BaseCommand):
    """
    Seeds CR-114's CTR decline per PLANNING.md §9: ~2.1% early, falling through
    the flagged week (first-week vs last-week CTR clears the 20% refresh
    trigger). The creative is created 5 weeks before the flagged week starts,
    matching "CR-114 now 5 weeks old".
    """

    help = "Seed Captivator360-sim with CR-114's CTR decline from PLANNING.md §9"

    def handle(self, *args, **options):
        random.seed(360)
        user, _ = User.objects.get_or_create(username="demo", defaults={"email": "demo@localhost"})
        user.set_password("demo")
        user.save()

        flagged_week_start = DEMO_START + datetime.timedelta(days=21)
        created_date = flagged_week_start - datetime.timedelta(weeks=5)

        creative, _ = CreativeAsset.objects.update_or_create(
            campaign_id=FLAGGED_CAMPAIGN_ID,
            variant_label="CR-114",
            defaults=dict(
                channel=CreativeAsset.Channel.TV,
                created_date=created_date,
                is_active=True,
            ),
        )
        CreativePerformanceDaily.objects.filter(creative=creative).delete()
        CreativeRefreshRequest.objects.filter(creative=creative).delete()

        rows = []
        for day_offset in range(DEMO_DAYS):
            date = DEMO_START + datetime.timedelta(days=day_offset)
            week = day_offset // 7

            if week < 3:
                progress = day_offset / 20.0
                ctr = 0.021 - (0.021 - 0.018) * progress
            else:
                progress = (day_offset - 21) / 6.0
                ctr = 0.018 - (0.018 - 0.013) * progress

            ctr = round(ctr + random.uniform(-0.001, 0.001), 4)
            conversion_rate = round(max(0.02, ctr * 3.0 + random.uniform(-0.003, 0.003)), 4)
            impressions = random.randint(22000, 28000)

            rows.append(
                CreativePerformanceDaily(
                    creative=creative,
                    date=date,
                    impressions=impressions,
                    ctr=ctr,
                    conversion_rate=conversion_rate,
                )
            )
        CreativePerformanceDaily.objects.bulk_create(rows)

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded creative id={creative.id} '{creative.variant_label}' "
                f"with {len(rows)} days of performance for campaign_id={FLAGGED_CAMPAIGN_ID}"
            )
        )
