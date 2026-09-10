from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from config.authentication import ServiceTokenAuthentication
from .metrics import summarize_ctr
from .models import CreativeAsset, CreativePerformanceDaily, CreativeRefreshRequest
from .serializers import (
    CreativeAssetSerializer,
    CreativePerformanceDailySerializer,
    CreativeRefreshRequestSerializer,
)

WRITE_AUTH = [ServiceTokenAuthentication, JWTAuthentication]


def _ctr_summary(creative, threshold_pct=None):
    daily = list(creative.daily_performance.all())
    kwargs = {} if threshold_pct is None else {"threshold_pct": threshold_pct}
    summary = summarize_ctr([{"ctr": row.ctr} for row in daily], **kwargs)
    summary["days_of_data"] = len(daily)
    return daily, summary


class CreativeAssetViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CreativeAssetSerializer

    def get_queryset(self):
        queryset = CreativeAsset.objects.all()
        campaign_id = self.request.query_params.get("campaign_id")
        if campaign_id:
            queryset = queryset.filter(campaign_id=campaign_id)
        return queryset


@api_view(["GET"])
def creative_performance(request, pk):
    """GET /api/creatives/{id}/performance/ — a creative's daily history plus a summary."""
    creative = get_object_or_404(CreativeAsset, pk=pk)
    daily, summary = _ctr_summary(creative)

    return Response(
        {
            "creative": CreativeAssetSerializer(creative).data,
            "daily_performance": CreativePerformanceDailySerializer(daily, many=True).data,
            "summary": summary,
        }
    )


@api_view(["POST"])
@authentication_classes(WRITE_AUTH)
@permission_classes([IsAuthenticated])
def refresh_request(request, pk):
    """
    POST /api/creatives/{id}/refresh-request/ — {"reason": str}

    Creates the request as "pending". Whether it should
    actually happen is decided by the MCP server's risk-scoring guardrail
    (PLANNING.md §7), not by this endpoint.

    Idempotent per creative: the guardrail's execution step calls this and
    then immediately resolves it in one logical operation (mcp_server's
    _execute_request_creative_refresh). If the resolve call fails and gets
    retried, re-creating here would otherwise leave the first request
    orphaned in "pending" forever while a second one is created — returning
    the existing pending request instead avoids that pile-up.
    """
    creative = get_object_or_404(CreativeAsset, pk=pk)
    reason = request.data.get("reason")
    if not reason:
        return Response({"error": "reason is required"}, status=400)

    existing = creative.refresh_requests.filter(status=CreativeRefreshRequest.Status.PENDING).first()
    if existing is not None:
        return Response(CreativeRefreshRequestSerializer(existing).data, status=200)

    refresh = creative.refresh_requests.create(reason=reason)
    return Response(CreativeRefreshRequestSerializer(refresh).data, status=201)


@api_view(["POST"])
@authentication_classes(WRITE_AUTH)
@permission_classes([IsAuthenticated])
def resolve_refresh_request(request, pk):
    """
    POST /api/creatives/refresh-requests/{id}/resolve/ — {"status": "approved"|"rejected"}

    This service has no opinion on whether a refresh request should go
    through; that's the MCP server's risk-scoring guardrail's job
    (PLANNING.md §7). This endpoint is the guardrail's execution step —
    called immediately for an auto-executed action, or later once a human
    approves/rejects a queued one — it does not decide that on its own.
    """
    refresh = get_object_or_404(CreativeRefreshRequest, pk=pk)
    new_status = request.data.get("status")
    if new_status not in (CreativeRefreshRequest.Status.APPROVED, CreativeRefreshRequest.Status.REJECTED):
        return Response({"error": "status must be 'approved' or 'rejected'"}, status=400)
    if refresh.status != CreativeRefreshRequest.Status.PENDING:
        return Response({"error": f"refresh request already {refresh.status}"}, status=400)

    refresh.status = new_status
    refresh.save()
    return Response(CreativeRefreshRequestSerializer(refresh).data)


@api_view(["GET"])
def declining_creatives(request):
    """
    GET /api/creatives/declining/?campaign_id=&threshold=

    Returns creatives whose CTR has dropped at least `threshold` percent
    (default 20) versus their own first-week average. Backs the MCP tool
    get_declining_creatives.
    """
    campaign_id = request.query_params.get("campaign_id")
    if not campaign_id:
        return Response({"error": "campaign_id is required"}, status=400)
    threshold = float(request.query_params.get("threshold", 20))

    results = []
    for creative in CreativeAsset.objects.filter(campaign_id=campaign_id):
        _, summary = _ctr_summary(creative, threshold_pct=threshold)
        if summary["ctr_decline_pct"] is not None and summary["ctr_decline_pct"] >= threshold:
            data = CreativeAssetSerializer(creative).data
            data.update(summary)
            results.append(data)

    return Response(results)


@api_view(["POST"])
@authentication_classes(WRITE_AUTH)
@permission_classes([IsAuthenticated])
def ingest_creative_metrics(request):
    """
    POST /api/webhooks/creative-metrics/

    Captivator360-sim's own receiver (PLANNING.md §9). Body: {date, metrics: [
    {creative_id, impressions, ctr, conversion_rate}]}.
    Duplicate (creative, date) rows are skipped.
    """
    date = request.data.get("date")
    metrics = request.data.get("metrics")
    if not date or not isinstance(metrics, list) or not metrics:
        return Response({"error": "date and a non-empty metrics list are required"}, status=400)

    created, skipped, errors = [], [], []
    for row in metrics:
        creative = CreativeAsset.objects.filter(id=row.get("creative_id")).first()
        if creative is None:
            errors.append({"row": row, "error": "unknown creative_id"})
            continue
        _, was_created = CreativePerformanceDaily.objects.get_or_create(
            creative=creative,
            date=date,
            defaults={
                "impressions": row.get("impressions", 0),
                "ctr": row.get("ctr", 0),
                "conversion_rate": row.get("conversion_rate", 0),
            },
        )
        (created if was_created else skipped).append({"creative_id": creative.id, "date": date})

    return Response({"created": created, "skipped": skipped, "errors": errors})
