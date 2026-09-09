from django.db.models import Count, Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import viewsets
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from config.authentication import ServiceTokenAuthentication
from .models import CallEvent, ClientAgentPool, RoutingRule
from .serializers import CallEventSerializer, RoutingRuleSerializer

WRITE_AUTH = [ServiceTokenAuthentication, JWTAuthentication]


class RoutingRuleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = RoutingRule.objects.all()
    serializer_class = RoutingRuleSerializer


@api_view(["GET"])
def call_events(request):
    """GET /api/calls/?campaign_id=&start=&end="""
    campaign_id = request.query_params.get("campaign_id")
    if not campaign_id:
        return Response({"error": "campaign_id is required"}, status=400)

    events = CallEvent.objects.filter(campaign_id=campaign_id)
    start = request.query_params.get("start")
    end = request.query_params.get("end")
    if start:
        events = events.filter(timestamp__date__gte=start)
    if end:
        events = events.filter(timestamp__date__lte=end)

    return Response(CallEventSerializer(events, many=True).data)


@api_view(["GET"])
def call_summary(request):
    """
    GET /api/calls/summary/?campaign_id=

    Pool distribution is the key data the demo scenario in PLANNING.md §9
    depends on — detecting call volume quietly shifting into a lower-
    converting, non-certified pool.
    """
    campaign_id = request.query_params.get("campaign_id")
    if not campaign_id:
        return Response({"error": "campaign_id is required"}, status=400)

    events = CallEvent.objects.filter(campaign_id=campaign_id)
    total = events.count()

    outcome_breakdown = {
        row["outcome"]: row["count"]
        for row in events.values("outcome").annotate(count=Count("id"))
    }

    pool_rows = events.values(
        "routed_pool", "routed_pool__name", "routed_pool__is_certified_medicare"
    ).annotate(
        call_count=Count("id"),
        conversion_count=Count("id", filter=Q(outcome=CallEvent.Outcome.CONVERSION)),
    )

    pool_distribution = []
    for row in pool_rows:
        call_count = row["call_count"]
        conversion_count = row["conversion_count"]
        pool_distribution.append(
            {
                "pool_id": row["routed_pool"],
                "pool_name": row["routed_pool__name"],
                "is_certified_medicare": row["routed_pool__is_certified_medicare"],
                "call_count": call_count,
                "pct_of_total": round((call_count / total) * 100, 1) if total else 0.0,
                "conversion_count": conversion_count,
                "conversion_rate": round(conversion_count / call_count, 4) if call_count else 0.0,
            }
        )
    pool_distribution.sort(key=lambda p: -p["call_count"])

    return Response(
        {
            "campaign_id": int(campaign_id),
            "total_calls": total,
            "outcome_breakdown": outcome_breakdown,
            "pool_distribution": pool_distribution,
        }
    )


@api_view(["POST"])
@authentication_classes(WRITE_AUTH)
@permission_classes([IsAuthenticated])
def ingest_call_events(request):
    """
    POST /api/webhooks/call-events/

    Maestro360-sim's own receiver (PLANNING.md §9). Body: {date, events: [
    {campaign_id, timestamp, routed_pool_id, wait_time_seconds,
    duration_seconds, outcome}]}. If that date already has events for the
    campaign, the payload is skipped so a replay doesn't double volume.
    """
    date = request.data.get("date")
    events = request.data.get("events")
    if not date or not isinstance(events, list) or not events:
        return Response({"error": "date and a non-empty events list are required"}, status=400)

    created, skipped, errors = [], [], []
    campaign_ids = {row.get("campaign_id") for row in events if row.get("campaign_id") is not None}
    for campaign_id in campaign_ids:
        if CallEvent.objects.filter(campaign_id=campaign_id, timestamp__date=date).exists():
            skipped.append({"campaign_id": campaign_id, "date": date})
            events = [row for row in events if row.get("campaign_id") != campaign_id]

    to_create = []
    for row in events:
        pool = ClientAgentPool.objects.filter(id=row.get("routed_pool_id")).first()
        ts = parse_datetime(row.get("timestamp") or "")
        if ts is not None and timezone.is_naive(ts):
            ts = timezone.make_aware(ts)
        if pool is None or ts is None or row.get("campaign_id") is None:
            errors.append({"row": row, "error": "campaign_id, timestamp, and routed_pool_id are required"})
            continue
        to_create.append(
            CallEvent(
                campaign_id=row["campaign_id"],
                timestamp=ts,
                routed_pool=pool,
                wait_time_seconds=row.get("wait_time_seconds", 0),
                duration_seconds=row.get("duration_seconds", 0),
                outcome=row.get("outcome", CallEvent.Outcome.NO_ANSWER),
            )
        )
    CallEvent.objects.bulk_create(to_create)
    return Response({"created_count": len(to_create), "skipped": skipped, "errors": errors})
