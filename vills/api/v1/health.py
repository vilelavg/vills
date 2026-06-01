"""Health checks: liveness e readiness."""

from fastapi import APIRouter, Response, status

from vills.cache.client import ping_redis
from vills.db.session import ping_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def liveness() -> dict[str, str]:
    return {"status": "alive"}


@router.get("/health/ready")
async def readiness(response: Response) -> dict[str, object]:
    checks = {"database": await ping_db(), "redis": await ping_redis()}
    healthy = all(checks.values())
    if not healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "ready" if healthy else "not_ready", "checks": checks}