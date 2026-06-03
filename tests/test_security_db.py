import pytest

from vills.security.audit import AuditLogger
from vills.security.models import AgencyUser
from vills.security.passwords import hash_password, verify_password
from vills.security.roles import Role
from vills.tenancy.models import Agency, TenantStatus


async def _make_agency(session, slug="webxp"):
    ag = Agency(name=slug, slug=slug, status=TenantStatus.ACTIVE, config={})
    session.add(ag)
    await session.flush()
    return ag


async def test_user_persists_and_password_verifies(db_session):
    ag = await _make_agency(db_session)
    u = AgencyUser(
        agency_id=ag.id,
        email="admin@webxp.com",
        hashed_password=hash_password("senha123"),
        role=Role.ADMIN,
        is_active=True,
        mfa_enabled=False,
    )
    db_session.add(u)
    await db_session.commit()
    assert u.id is not None
    assert verify_password("senha123", u.hashed_password)


async def test_email_unique_per_agency(db_session):
    from sqlalchemy.exc import IntegrityError

    ag = await _make_agency(db_session)
    db_session.add(
        AgencyUser(
            agency_id=ag.id,
            email="a@b.com",
            hashed_password="x",
            role=Role.VIEWER,
            is_active=True,
            mfa_enabled=False,
        )
    )
    await db_session.commit()
    db_session.add(
        AgencyUser(
            agency_id=ag.id,
            email="a@b.com",
            hashed_password="y",
            role=Role.ADMIN,
            is_active=True,
            mfa_enabled=False,
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.commit()


async def test_audit_log_records(db_session):
    ag = await _make_agency(db_session)
    logger = AuditLogger(db_session)
    entry = await logger.log(
        tenant_id=ag.id,
        action="user.login",
        actor_email="admin@webxp.com",
        metadata={"ip": "1.2.3.4"},
    )
    await db_session.commit()
    assert entry.id is not None
    assert entry.action == "user.login"
    assert entry.metadata_ == {"ip": "1.2.3.4"}
