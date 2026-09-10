from collections import defaultdict
from decimal import Decimal, InvalidOperation

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from config.authentication import ServiceTokenAuthentication
from .models import BudgetRecommendation, Daypart, Spot, SpotPerformance, Station
from .serializers import (
    BudgetRecommendationSerializer,
    SpotDetailSerializer,
    SpotSerializer,
)

WRITE_AUTH = [ServiceTokenAuthentication, JWTAuthentication]


class SpotViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SpotSerializer

    def get_queryset(self):
        queryset = Spot.objects.all()
        campaign_id = self.request.query_params.get("campaign_id")
        if campaign_id:
            queryset = queryset.filter(campaign_id=campaign_id)
        return queryset


@api_view(["GET"])
def spot_performance(request, pk):
    """GET /api/spots/{id}/performance/ — a spot plus its call/conversion/CPL performance."""
    spot = get_object_or_404(Spot, pk=pk)
    return Response(SpotDetailSerializer(spot).data)


@api_view(["GET"])
def get_recommendation(request, pk):
    """GET /api/recommendations/{id}/ — retrieve a single stored recommendation."""
    recommendation = get_object_or_404(BudgetRecommendation, pk=pk)
    return Response(BudgetRecommendationSerializer(recommendation).data)


@api_view(["POST"])
@authentication_classes(WRITE_AUTH)
@permission_classes([IsAuthenticated])
def apply_recommendation(request, pk):
    """
    POST /api/recommendations/{id}/apply/ — marks a recommendation as applied.

    This service has no opinion on whether applying it is safe; that's the
    MCP server's risk-scoring guardrail's job (PLANNING.md §7). This endpoint
    is the guardrail's execution step once a reallocate_budget action has
    cleared auto-execute or been approved by a human — it does not decide
    that on its own, it only records the fact once told to.
    """
    recommendation = get_object_or_404(BudgetRecommendation, pk=pk)
    if recommendation.applied:
        return Response({"error": "recommendation already applied"}, status=400)

    recommendation.applied = True
    recommendation.applied_at = timezone.now()
    recommendation.save()
    return Response(BudgetRecommendationSerializer(recommendation).data)


@api_view(["POST"])
@authentication_classes(WRITE_AUTH)
@permission_classes([IsAuthenticated])
def recommend_budget(request):
    """
    POST /api/recommendations/ — {"campaign_id": int, "budget_amount": number}

    Deterministic weighted-scoring recommendation (PLANNING.md §6/§7): ranks
    this campaign's historical station/daypart combos by average CPL and
    allocates the proposed budget favoring the lowest-CPL combos. The
    `confidence` output feeds the MCP server's risk-scoring guardrail (§7).
    """
    campaign_id = request.data.get("campaign_id")
    budget_amount = request.data.get("budget_amount")

    if campaign_id is None or budget_amount is None:
        return Response({"error": "campaign_id and budget_amount are required"}, status=400)

    try:
        budget_amount = Decimal(str(budget_amount))
    except InvalidOperation:
        return Response({"error": "budget_amount must be a number"}, status=400)

    performances = SpotPerformance.objects.filter(
        spot__campaign_id=campaign_id, cpl__isnull=False
    ).select_related("spot__station", "spot__daypart")

    groups = defaultdict(list)
    for perf in performances:
        key = (perf.spot.station_id, perf.spot.daypart_id)
        groups[key].append(perf)

    if not groups:
        recommendation = BudgetRecommendation.objects.create(
            campaign_id=campaign_id,
            budget_amount=budget_amount,
            allocation=[],
            rationale=(
                "No historical spot performance data exists yet for this campaign, "
                "so there isn't enough information to recommend an allocation."
            ),
            confidence=Decimal("0.000"),
        )
        return Response(BudgetRecommendationSerializer(recommendation).data)

    stats = []
    total_samples = 0
    for (station_id, daypart_id), perfs in groups.items():
        avg_cpl = sum(p.cpl for p in perfs) / len(perfs)
        # A zero (or negative, from bad data) CPL can't be weighted by 1/avg_cpl
        # below — exclude rather than divide by zero.
        if avg_cpl <= 0:
            continue
        sample_size = len(perfs)
        total_samples += sample_size
        stats.append(
            {
                "station_id": station_id,
                "station_name": perfs[0].spot.station.name,
                "daypart_id": daypart_id,
                "daypart_name": perfs[0].spot.daypart.name,
                "avg_cpl": avg_cpl,
                "sample_size": sample_size,
            }
        )

    if not stats:
        recommendation = BudgetRecommendation.objects.create(
            campaign_id=campaign_id,
            budget_amount=budget_amount,
            allocation=[],
            rationale=(
                "No historical spot performance data with a usable cost-per-lead exists yet "
                "for this campaign, so there isn't enough information to recommend an allocation."
            ),
            confidence=Decimal("0.000"),
        )
        return Response(BudgetRecommendationSerializer(recommendation).data)

    stats.sort(key=lambda s: s["avg_cpl"])

    weights = [Decimal("1") / s["avg_cpl"] for s in stats]
    weight_total = sum(weights)

    allocation = []
    for stat, weight in zip(stats, weights):
        share = weight / weight_total
        allocated_amount = round(share * budget_amount, 2)
        allocation.append(
            {
                "station_id": stat["station_id"],
                "station_name": stat["station_name"],
                "daypart_id": stat["daypart_id"],
                "daypart_name": stat["daypart_name"],
                "avg_cpl": round(float(stat["avg_cpl"]), 2),
                "sample_size": stat["sample_size"],
                "allocated_amount": float(allocated_amount),
            }
        )

    top = stats[0]
    rationale = (
        f"{top['station_name']}'s {top['daypart_name']} daypart has historically produced "
        f"the lowest cost per lead (${round(float(top['avg_cpl']), 2)}) for this campaign, "
        f"based on {top['sample_size']} prior spot(s), so it receives the largest share "
        f"of the proposed budget."
    )

    confidence = min(Decimal("1.000"), (Decimal(total_samples) / Decimal(20)).quantize(Decimal("0.001")))

    recommendation = BudgetRecommendation.objects.create(
        campaign_id=campaign_id,
        budget_amount=budget_amount,
        allocation=allocation,
        rationale=rationale,
        confidence=confidence,
    )
    return Response(BudgetRecommendationSerializer(recommendation).data)


@api_view(["POST"])
@authentication_classes(WRITE_AUTH)
@permission_classes([IsAuthenticated])
def ingest_spot_performance(request):
    """
    POST /api/webhooks/spot-performance/

    SmartSpot360-sim's own receiver (PLANNING.md §9). Body: {date, spots: [
    {campaign_id, station_id, daypart_id, cost, creative_label, calls,
    conversions, cpl}]}. Idempotent per (campaign_id, station, daypart, date).
    """
    date = request.data.get("date")
    spots = request.data.get("spots")
    if not date or not isinstance(spots, list) or not spots:
        return Response({"error": "date and a non-empty spots list are required"}, status=400)

    created, skipped, errors = [], [], []
    for row in spots:
        station = Station.objects.filter(id=row.get("station_id")).first()
        daypart = Daypart.objects.filter(id=row.get("daypart_id")).first()
        campaign_id = row.get("campaign_id")
        if station is None or daypart is None or campaign_id is None:
            errors.append({"row": row, "error": "campaign_id, station_id, and daypart_id are required"})
            continue
        existing = Spot.objects.filter(
            campaign_id=campaign_id, station=station, daypart=daypart, air_date=date
        ).first()
        if existing is not None:
            skipped.append({"spot_id": existing.id, "date": date})
            continue
        spot = Spot.objects.create(
            campaign_id=campaign_id,
            station=station,
            daypart=daypart,
            air_date=date,
            cost=row.get("cost", 0),
            creative_label=row.get("creative_label", ""),
        )
        SpotPerformance.objects.create(
            spot=spot,
            calls=row.get("calls", 0),
            conversions=row.get("conversions", 0),
            cpl=row.get("cpl"),
        )
        created.append({"spot_id": spot.id, "date": date})

    return Response({"created": created, "skipped": skipped, "errors": errors})
