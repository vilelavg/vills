import uuid
from dataclasses import FrozenInstanceError

import pytest
from vills.core.prompt_engine import PromptEngine, PromptTemplateNotFoundError
from vills.tenancy.context import TenantContext


def _agency_ctx(**kw):
    base = {"agency_id": uuid.uuid4(), "agency_slug": "webxp", "agency_config": {"tone": "formal"}}
    base.update(kw)
    return TenantContext(**base)


def _client_ctx():
    return TenantContext(
        agency_id=uuid.uuid4(),
        agency_slug="webxp",
        agency_config={"tone": "formal", "language": "pt-BR"},
        client_id=uuid.uuid4(),
        client_slug="clinica",
        client_segment="odontologia",
        client_config={"tone": "acolhedor"},
    )


def test_agency_scope_not_client():
    t = _agency_ctx()
    assert not t.is_client_scope
    assert t.scope_label == "webxp"


def test_client_scope():
    t = _client_ctx()
    assert t.is_client_scope
    assert t.scope_label == "webxp/clinica"


def test_merge_client_overrides_agency():
    t = _client_ctx()
    merged = t.merged_config()
    assert merged["tone"] == "acolhedor"
    assert merged["language"] == "pt-BR"


def test_merge_does_not_mutate_original():
    t = _client_ctx()
    merged = t.merged_config()
    merged["tone"] = "hackeado"
    assert t.client_config["tone"] == "acolhedor"


def test_context_is_immutable():
    t = _agency_ctx()
    with pytest.raises(FrozenInstanceError):
        t.agency_slug = "outro"


def test_prompt_renders_segment_and_tone():
    pe = PromptEngine(templates_dir="vills/prompts")
    out = pe.render("system_base", _client_ctx())
    assert "odontologia" in out
    assert "acolhedor" in out
    assert "em nome do cliente" in out


def test_prompt_agency_scope():
    pe = PromptEngine(templates_dir="vills/prompts")
    out = pe.render("system_base", _agency_ctx(agency_config={}))
    assert "operação interna" in out
    assert "profissional e cordial" in out


def test_prompt_missing_template_raises():
    pe = PromptEngine(templates_dir="vills/prompts")
    with pytest.raises(PromptTemplateNotFoundError):
        pe.render("nao_existe", _agency_ctx())


async def test_resolver_agency_and_client(db_session):
    from vills.tenancy.models import Agency, AgencyClient, TenantStatus
    from vills.tenancy.resolver import TenantResolver

    ag = Agency(name="WebXP", slug="webxp", status=TenantStatus.ACTIVE, config={"tone": "formal"})
    db_session.add(ag)
    await db_session.flush()
    cl = AgencyClient(
        agency_id=ag.id,
        name="Clinica",
        slug="clinica",
        status=TenantStatus.ACTIVE,
        segment="odontologia",
        config={},
    )
    db_session.add(cl)
    await db_session.commit()

    res = TenantResolver(db_session)
    ctx_ag = await res.resolve("webxp")
    assert ctx_ag.agency_slug == "webxp" and not ctx_ag.is_client_scope
    ctx_cl = await res.resolve("webxp", "clinica")
    assert ctx_cl.is_client_scope and ctx_cl.client_segment == "odontologia"


async def test_resolver_not_found(db_session):
    from vills.tenancy.resolver import TenantNotFoundError, TenantResolver

    res = TenantResolver(db_session)
    with pytest.raises(TenantNotFoundError):
        await res.resolve("naoexiste")


async def test_resolver_inactive_blocks(db_session):
    from vills.tenancy.models import Agency, TenantStatus
    from vills.tenancy.resolver import TenantInactiveError, TenantResolver

    ag = Agency(name="Susp", slug="susp", status=TenantStatus.SUSPENDED, config={})
    db_session.add(ag)
    await db_session.commit()
    res = TenantResolver(db_session)
    with pytest.raises(TenantInactiveError):
        await res.resolve("susp")


async def test_homonymous_clients_isolated(db_session):
    from vills.tenancy.models import Agency, AgencyClient, TenantStatus
    from vills.tenancy.resolver import TenantResolver

    for slug in ("webxp", "outra"):
        ag = Agency(name=slug, slug=slug, status=TenantStatus.ACTIVE, config={})
        db_session.add(ag)
        await db_session.flush()
        db_session.add(
            AgencyClient(
                agency_id=ag.id,
                name="Clinica",
                slug="clinica",
                status=TenantStatus.ACTIVE,
                segment="x",
                config={},
            )
        )
    await db_session.commit()

    res = TenantResolver(db_session)
    a = await res.resolve("webxp", "clinica")
    b = await res.resolve("outra", "clinica")
    assert a.client_id != b.client_id
