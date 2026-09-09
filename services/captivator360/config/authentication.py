"""Service-token auth (MCP → this service) plus JWT (human users).

PLANNING.md §7/§14 phase 8: the MCP server holds a client-credentials-style
service token; a person logging into a Django API gets a JWT from
simplejwt. Reads stay AllowAny so the local console and healthchecks work
without a login wall; write endpoints (webhooks, mutations) require one of
these two credentials.
"""

import os

from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed


class ServicePrincipal:
    """A non-User principal representing the MCP server."""

    is_authenticated = True
    pk = None
    id = None
    username = "mcp-service"

    def __str__(self):
        return self.username


class ServiceTokenAuthentication(BaseAuthentication):
    """Looks at X-Service-Token, not Authorization, so it never collides
    with simplejwt's Bearer JWT parser (which raises on a non-JWT token)."""

    header = "X-Service-Token"

    def authenticate(self, request):
        token = request.headers.get(self.header)
        expected = os.environ.get("SERVICE_TOKEN", "")
        if not token:
            return None
        if not expected or token != expected:
            raise AuthenticationFailed("Invalid service token")
        return (ServicePrincipal(), None)
