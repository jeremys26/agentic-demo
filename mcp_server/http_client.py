"""Shared outbound HTTP to the sim services.

Every MCP → Django call sends X-Service-Token when SERVICE_TOKEN is set,
which is the client-credentials analogue from PLANNING.md §7: the gateway
authenticates as a service, not as a logged-in user.
"""

import os

import httpx

DEFAULT_TIMEOUT = 10.0


def service_headers() -> dict[str, str]:
    token = os.environ.get("SERVICE_TOKEN", "")
    if not token:
        return {}
    return {"X-Service-Token": token}


def service_client(**kwargs) -> httpx.AsyncClient:
    timeout = kwargs.pop("timeout", DEFAULT_TIMEOUT)
    headers = {**service_headers(), **kwargs.pop("headers", {})}
    return httpx.AsyncClient(timeout=timeout, headers=headers, **kwargs)
