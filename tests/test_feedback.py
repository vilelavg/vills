import uuid

import pytest
from vills.core.feedback_loop import ActionOutcome, FeedbackLoop
from vills.tenancy.context import TenantContext


async def test_record_action(db_session):
    aid, cid = uuid.uuid4(), uuid.uuid4()
    ctx = TenantContext(agency_id=aid, agency_slug="webxp", client_id=cid, client_slug="clinica")
    fb = FeedbackLoop(db_session)
    log = await fb.record(
        ctx,
        module="m14_atendimento",
        action="resposta",
        outcome=ActionOutcome.SUCCESS,
        score=0.9,
    )
    await db_session.commit()
    assert log.id is not None
    assert log.tenant_id == aid
    assert log.client_id == cid
    assert log.outcome == ActionOutcome.SUCCESS


async def test_record_agency_scope_has_no_client(db_session):
    aid = uuid.uuid4()
    ctx = TenantContext(agency_id=aid, agency_slug="webxp")
    fb = FeedbackLoop(db_session)
    log = await fb.record(ctx, module="m02", action="relatorio")
    await db_session.commit()
    assert log.tenant_id == aid
    assert log.client_id is None
    assert log.outcome == ActionOutcome.PENDING


async def test_invalid_score_rejected(db_session):
    ctx = TenantContext(agency_id=uuid.uuid4(), agency_slug="webxp")
    fb = FeedbackLoop(db_session)
    with pytest.raises(ValueError):
        await fb.record(ctx, module="m", action="a", score=1.5)
    with pytest.raises(ValueError):
        await fb.record(ctx, module="m", action="a", score=-0.1)


async def test_score_boundaries_accepted(db_session):
    ctx = TenantContext(agency_id=uuid.uuid4(), agency_slug="webxp")
    fb = FeedbackLoop(db_session)
    low = await fb.record(ctx, module="m", action="a", score=0.0)
    high = await fb.record(ctx, module="m", action="b", score=1.0)
    await db_session.commit()
    assert low.score == 0.0
    assert high.score == 1.0
