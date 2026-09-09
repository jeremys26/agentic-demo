import datetime
import random

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from calls.models import CallEvent, ClientAgentPool, RoutingRule

DEMO_START = datetime.date(2026, 8, 1)
DEMO_DAYS = 28
FLAGGED_CAMPAIGN_ID = 1  # OneSource360-sim's "Medicare Advantage – Southeast TV" (see its seed_data)


class Command(BaseCommand):
    """
    Seeds the Pool A/Pool B routing shift per PLANNING.md §9: Pool A (certified,
    31% conversion) handles ~90% of calls in the 3 baseline weeks; in the
    flagged week it hits capacity and Pool B (NOT Medicare-certified, 18%
    conversion) picks up ~35% of volume instead of its normal ~10%. This is
    the compliance-and-performance half of the compound-cause scenario.
    """

    help = "Seed Maestro360-sim with the Pool A/Pool B routing shift from PLANNING.md §9"

    def handle(self, *args, **options):
        random.seed(360)
        user, _ = User.objects.get_or_create(username="demo", defaults={"email": "demo@localhost"})
        user.set_password("demo")
        user.save()

        pool_a, _ = ClientAgentPool.objects.update_or_create(
            name="Pool A",
            defaults=dict(
                vertical_specialty=ClientAgentPool.Vertical.MEDICARE_ADVANTAGE,
                historical_conversion_rate=0.3100,
                is_certified_medicare=True,
            ),
        )
        pool_b, _ = ClientAgentPool.objects.update_or_create(
            name="Pool B",
            defaults=dict(
                vertical_specialty=ClientAgentPool.Vertical.INSURANCE,
                historical_conversion_rate=0.1800,
                is_certified_medicare=False,
            ),
        )

        RoutingRule.objects.all().delete()
        RoutingRule.objects.create(
            priority=1, pool=pool_a,
            description="Primary Medicare Advantage certified pool — route here first",
        )
        RoutingRule.objects.create(
            priority=2, pool=pool_b,
            description="Overflow pool — used only when Pool A is at capacity; not Medicare-certified",
        )

        CallEvent.objects.filter(campaign_id=FLAGGED_CAMPAIGN_ID).delete()

        events = []
        for day_offset in range(DEMO_DAYS):
            date = DEMO_START + datetime.timedelta(days=day_offset)
            week = day_offset // 7
            pool_b_share = 0.10 if week < 3 else 0.35

            daily_calls = random.randint(180, 230)
            for _ in range(daily_calls):
                pool = pool_b if random.random() < pool_b_share else pool_a
                hour = random.randint(8, 19)
                minute = random.randint(0, 59)
                ts = timezone.make_aware(
                    datetime.datetime.combine(date, datetime.time(hour, minute))
                )

                conversion_rate = float(pool.historical_conversion_rate)
                roll = random.random()
                if roll < conversion_rate:
                    outcome = CallEvent.Outcome.CONVERSION
                    duration = random.randint(180, 600)
                elif roll < conversion_rate + 0.15:
                    outcome = CallEvent.Outcome.VOICEMAIL
                    duration = random.randint(15, 60)
                elif roll < conversion_rate + 0.25:
                    outcome = CallEvent.Outcome.DROPPED
                    duration = random.randint(5, 30)
                else:
                    outcome = CallEvent.Outcome.NO_ANSWER
                    duration = 0

                events.append(
                    CallEvent(
                        campaign_id=FLAGGED_CAMPAIGN_ID,
                        timestamp=ts,
                        routed_pool=pool,
                        wait_time_seconds=random.randint(5, 120),
                        duration_seconds=duration,
                        outcome=outcome,
                    )
                )
        CallEvent.objects.bulk_create(events)

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(events)} call events for campaign_id={FLAGGED_CAMPAIGN_ID} "
                f"across {DEMO_DAYS} days (Pool A/Pool B routing shift in week 4)"
            )
        )
