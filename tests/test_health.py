async def test_liveness(client):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "alive"


async def test_readiness_contract(client):
    resp = await client.get("/api/v1/health/ready")
    assert resp.status_code in (200, 503)
    body = resp.json()
    assert set(body["checks"]) == {"database", "redis"}


async def test_readiness_503_when_deps_down(client, monkeypatch):
    from vills.cache import client as cache_mod
    from vills.db import session as db_mod

    async def fake_false():
        return False

    monkeypatch.setattr(db_mod, "ping_db", fake_false)
    monkeypatch.setattr(cache_mod, "ping_redis", fake_false)

    resp = await client.get("/api/v1/health/ready")
    assert resp.status_code == 503
    assert resp.json()["status"] == "not_ready"
