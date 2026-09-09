"""Live Postgres snapshot for the Systems inspector UI.

Serializes this service's own Django models (which map 1:1 onto its
logical database's tables) so the console can show the exact rows an MCP
tool is about to read. GET stays AllowAny like the rest of the local
console's reads — this is a demo inspector, not a production admin API.
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from django.apps import apps
from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response

SKIP_APPS = {"admin", "auth", "contenttypes", "sessions"}
MAX_LIMIT = 200
DEFAULT_LIMIT = 50


def _jsonable(value):
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (list, dict)):
        return value
    return str(value)


def _model_payload(model, limit, offset):
    fields = list(model._meta.concrete_fields)
    columns = [
        {
            "name": field.attname,
            "type": field.get_internal_type(),
            "nullable": field.null,
            "primary_key": field.primary_key,
        }
        for field in fields
    ]
    queryset = model.objects.all().order_by("pk")
    total = queryset.count()
    rows = [
        {field.attname: _jsonable(getattr(obj, field.attname)) for field in fields}
        for obj in queryset[offset : offset + limit]
    ]
    return {
        "model": model.__name__,
        "db_table": model._meta.db_table,
        "app_label": model._meta.app_label,
        "columns": columns,
        "total": total,
        "offset": offset,
        "limit": limit,
        "rows": rows,
    }


def _app_models():
    models = [
        model
        for model in apps.get_models()
        if model._meta.app_label not in SKIP_APPS and not model._meta.proxy
    ]
    models.sort(key=lambda model: model._meta.db_table)
    return models


@api_view(["GET"])
def inspect_tables(request):
    """
    GET /api/inspect/?table=&limit=&offset=

    Omit `table` to snapshot every app table. Pass a db_table or model name
    to page a single table (Maestro360's call events are thousands of rows).
    """
    try:
        limit = min(max(int(request.query_params.get("limit", DEFAULT_LIMIT)), 1), MAX_LIMIT)
        offset = max(int(request.query_params.get("offset", 0)), 0)
    except (TypeError, ValueError):
        return Response({"error": "limit and offset must be integers"}, status=400)

    models = _app_models()
    table = request.query_params.get("table")
    if table:
        match = next(
            (model for model in models if model._meta.db_table == table or model.__name__ == table),
            None,
        )
        if match is None:
            return Response({"error": f"unknown table {table}"}, status=404)
        models = [match]

    return Response(
        {
            "database": settings.DATABASES["default"]["NAME"],
            "tables": [_model_payload(model, limit, offset) for model in models],
        }
    )
