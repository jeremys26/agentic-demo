"""The config-driven tool registry described in PLANNING.md §7: each tool
module registers its handlers here via @register(...), and main.py loops
over the registry once to both (a) wire each handler into the MCP server via
mcp.tool() and (b) power the /tools and /catalog introspection endpoints — one
place that knows about every tool instead of two lists that can drift apart.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class RestCall:
    """One HTTP call a tool makes against its backing service.

    `path` may include `{argument_name}` placeholders filled from the tool's
    arguments. `query_from` maps tool argument name → query-string key
    (empty-string args are omitted). `when` is always / on_execute /
    per_campaign / per_spot / per_creative — the frontend uses it to explain
    N+1 or guardrail-gated calls that don't fire on every invocation.
    """

    method: str
    path: str
    query_from: dict[str, str] = field(default_factory=dict)
    body_from: tuple[str, ...] = ()
    when: str = "always"
    notes: str = ""


@dataclass
class ToolSpec:
    name: str
    func: Callable
    kind: str  # "read" or "write" — write tools get routed through the risk-scoring guardrail (§7)
    service: str  # which backing sim service this tool proxies to
    rest: tuple[RestCall, ...] = ()


_registry: list[ToolSpec] = []


def register(name: str, service: str, kind: str = "read", rest: list[RestCall] | None = None):
    def decorator(func):
        _registry.append(
            ToolSpec(name=name, func=func, kind=kind, service=service, rest=tuple(rest or []))
        )
        return func

    return decorator


def all_tools() -> list[ToolSpec]:
    return list(_registry)


def source_file_for(func: Callable) -> str:
    path = inspect.getfile(func)
    if "/app/" in path:
        return "mcp_server/" + path.split("/app/", 1)[1]
    marker = "mcp_server/"
    if marker in path:
        return path[path.index(marker) :]
    return path


def _source_of(func: Callable) -> str:
    try:
        return inspect.getsource(func)
    except (OSError, TypeError):
        return ""


def tool_schema(spec: ToolSpec) -> dict:
    """A lightweight parameter schema for the /tools and /catalog endpoints —
    not full JSON Schema (the MCP protocol's own tools/list already provides
    that via the Python MCP SDK's automatic Pydantic model generation); this
    is a plain, human-readable reference for anyone hitting the REST API
    directly, including the Systems inspector UI."""
    params = []
    for pname, param in inspect.signature(spec.func).parameters.items():
        annotation = param.annotation
        type_name = getattr(annotation, "__name__", str(annotation))
        params.append(
            {
                "name": pname,
                "type": type_name,
                "required": param.default is inspect.Parameter.empty,
            }
        )
    return {
        "name": spec.name,
        "service": spec.service,
        "kind": spec.kind,
        "description": inspect.getdoc(spec.func) or "",
        "parameters": params,
        "rest": [
            {
                "method": call.method,
                "path": call.path,
                "query_from": call.query_from,
                "body_from": list(call.body_from),
                "when": call.when,
                "notes": call.notes,
            }
            for call in spec.rest
        ],
        "source_file": source_file_for(spec.func),
        "source": _source_of(spec.func),
    }
