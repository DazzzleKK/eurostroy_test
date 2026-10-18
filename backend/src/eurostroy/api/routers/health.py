"""Проверка живости: база и S3."""

from __future__ import annotations

from fastapi import APIRouter, Response, status

from eurostroy.api.deps import ContainerDep
from eurostroy.api.schemas import HealthOut

router = APIRouter(prefix="/api", tags=["health"])


@router.get(
    "/healthz",
    response_model=HealthOut,
    responses={503: {"model": HealthOut, "description": "Зависимость недоступна"}},
)
async def healthz(container: ContainerDep, response: Response) -> HealthOut:
    report = await container.health()
    if not report.ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthOut(
        status="ok" if report.ok else "degraded",
        db=report.db,
        storage=report.storage,
    )
