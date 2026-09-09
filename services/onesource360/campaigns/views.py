from django.db.models import Sum
from rest_framework import viewsets
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from config.authentication import ServiceTokenAuthentication
from .models import Campaign, DailyPerformanceRollup
from .serializers import CampaignSerializer, DailyPerformanceRollupSerializer

WRITE_AUTH = [ServiceTokenAuthentication, JWTAuthentication]


class CampaignViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Campaign.objects.all()
    serializer_class = CampaignSerializer


@api_view(["GET"])
def performance(request):
    """
    GET /api/performance/?campaign_id=&start=&end=

    Returns the daily rollups for a campaign in a date range, plus a summary
    block. This is what the MCP server's get_campaign_performance tool calls
    (PLANNING.md §6/§7) — the summary's cpl vs target_cpl comparison is also
    the same logic the anomaly sweep will reuse later (§8).
    """
    campaign_id = request.query_params.get("campaign_id")
    start = request.query_params.get("start")
    end = request.query_params.get("end")

    if not campaign_id:
        return Response({"error": "campaign_id is required"}, status=400)

    try:
        campaign = Campaign.objects.get(id=campaign_id)
    except Campaign.DoesNotExist:
        return Response({"error": f"no campaign with id {campaign_id}"}, status=404)

    rollups = DailyPerformanceRollup.objects.filter(campaign=campaign)
    if start:
        rollups = rollups.filter(date__gte=start)
    if end:
        rollups = rollups.filter(date__lte=end)

    aggregates = rollups.aggregate(
        total_spend=Sum("spend"),
        total_leads=Sum("leads"),
        total_calls=Sum("calls"),
        total_conversions=Sum("conversions"),
    )

    # Blended CPL = total spend / total leads over the period, not an average
    # of each day's already-computed CPL — Avg("cpl") would understate swings
    # in a mixed baseline/spike range since it weights every day equally
    # regardless of volume, which would throw off the §9 anomaly threshold.
    total_spend = aggregates["total_spend"]
    total_leads = aggregates["total_leads"]
    avg_cpl = (
        round(float(total_spend) / total_leads, 2)
        if total_leads
        else None
    )
    target_cpl = campaign.target_cpl
    cpl_variance_pct = (
        round(float((avg_cpl - float(target_cpl)) / float(target_cpl)) * 100, 1)
        if avg_cpl is not None
        else None
    )

    return Response(
        {
            "campaign": CampaignSerializer(campaign).data,
            "daily_rollups": DailyPerformanceRollupSerializer(rollups, many=True).data,
            "summary": {
                **aggregates,
                "avg_cpl": avg_cpl,
                "target_cpl": target_cpl,
                "cpl_variance_pct": cpl_variance_pct,
            },
        }
    )


@api_view(["POST"])
@authentication_classes(WRITE_AUTH)
@permission_classes([IsAuthenticated])
def ingest_daily_performance(request):
    """
    POST /api/webhooks/daily-performance/

    OneSource360-sim's own receiver for a new day's warehouse drop
    (PLANNING.md §9 live event simulation). Accepts `rollups`: a list of
    {campaign_id, date, spend, leads, calls, conversions, cpl}. Duplicate
    (campaign, date) rows are skipped so replaying a day is idempotent.
    """
    rows = request.data.get("rollups")
    if not isinstance(rows, list) or not rows:
        return Response({"error": "rollups must be a non-empty list"}, status=400)

    created, skipped, errors = [], [], []
    for row in rows:
        campaign_id = row.get("campaign_id")
        date = row.get("date")
        if campaign_id is None or not date:
            errors.append({"row": row, "error": "campaign_id and date are required"})
            continue
        campaign = Campaign.objects.filter(id=campaign_id).first()
        if campaign is None:
            errors.append({"row": row, "error": f"no campaign with id {campaign_id}"})
            continue
        defaults = {
            "spend": row.get("spend", 0),
            "leads": row.get("leads", 0),
            "calls": row.get("calls", 0),
            "conversions": row.get("conversions", 0),
            "cpl": row.get("cpl", 0),
        }
        _, was_created = DailyPerformanceRollup.objects.get_or_create(
            campaign=campaign, date=date, defaults=defaults
        )
        (created if was_created else skipped).append({"campaign_id": campaign_id, "date": str(date)})

    return Response({"created": created, "skipped": skipped, "errors": errors})
