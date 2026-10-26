"""FastAPI dependencies."""

import hmac
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, Response, status

from forecheck.entrypoints.composition import Services, get_services

ServicesDep = Annotated[Services, Depends(get_services)]

# Data changes once a day. Let the CDN keep a response for an hour and serve a stale one while
# it fetches a fresh copy, so almost no visit reaches the database.
CACHE_CONTROL = "public, s-maxage=3600, stale-while-revalidate=86400"


def cacheable(response: Response) -> None:
    response.headers["Cache-Control"] = CACHE_CONTROL


def only_query_params(*allowed: str) -> Callable[[Request], None]:
    """Reject query parameters an endpoint does not know.

    Without this anyone could append ``?x=1``, ``?x=2`` and so on to get past the CDN cache and
    reach the database every time. With it the set of distinct cacheable URLs is small and fixed
    (stations x variables x periods), which is the protection a serverless host without shared
    state can offer.
    """

    def check(request: Request) -> None:
        unknown = sorted(set(request.query_params) - set(allowed))
        if unknown:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, f"Unknown query parameter: {', '.join(unknown)}"
            )

    return check


def require_cron_secret(
    services: ServicesDep, authorization: Annotated[str | None, Header()] = None
) -> None:
    """Vercel Cron sends ``Authorization: Bearer <CRON_SECRET>``. No secret: the route is off."""
    secret = services.settings.cron_secret
    if not secret:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    expected = f"Bearer {secret}"
    if authorization is None or not hmac.compare_digest(authorization.encode(), expected.encode()):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid cron secret")
