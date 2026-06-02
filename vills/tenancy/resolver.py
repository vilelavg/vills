"""Resolve agência e cliente a partir de slugs/IDs e monta o TenantContext."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vills.tenancy.context import TenantContext
from vills.tenancy.models import Agency, AgencyClient, TenantStatus


class TenantNotFoundError(Exception):
    """Agência ou cliente não encontrado."""


class TenantInactiveError(Exception):
    """Agência ou cliente existe mas não está ativo."""


class TenantResolver:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def resolve(
        self,
        agency_slug: str,
        client_slug: str | None = None,
    ) -> TenantContext:
        agency = await self._get_agency(agency_slug)
        if agency.status != TenantStatus.ACTIVE:
            raise TenantInactiveError(f"Agência '{agency_slug}' está {agency.status}")

        if client_slug is None:
            return TenantContext(
                agency_id=agency.id,
                agency_slug=agency.slug,
                agency_config=agency.config,
            )

        client = await self._get_client(agency.id, client_slug)
        if client.status != TenantStatus.ACTIVE:
            raise TenantInactiveError(f"Cliente '{client_slug}' está {client.status}")

        return TenantContext(
            agency_id=agency.id,
            agency_slug=agency.slug,
            agency_config=agency.config,
            client_id=client.id,
            client_slug=client.slug,
            client_segment=client.segment,
            client_config=client.config,
        )

    async def _get_agency(self, slug: str) -> Agency:
        result = await self._session.execute(select(Agency).where(Agency.slug == slug))
        agency = result.scalar_one_or_none()
        if agency is None:
            raise TenantNotFoundError(f"Agência '{slug}' não encontrada")
        return agency

    async def _get_client(self, agency_id: uuid.UUID, slug: str) -> AgencyClient:
        result = await self._session.execute(
            select(AgencyClient).where(
                AgencyClient.agency_id == agency_id,
                AgencyClient.slug == slug,
            )
        )
        client = result.scalar_one_or_none()
        if client is None:
            raise TenantNotFoundError(f"Cliente '{slug}' não encontrado na agência")
        return client
