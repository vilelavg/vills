import time

import pytest
from vills.core.model_router import (
    CircuitOpenError,
    ModelRouter,
    TaskComplexity,
)


class _FakeMessages:
    def __init__(self, behavior: dict):
        self.behavior = behavior
        self.calls: list[str] = []

    async def create(self, model, system, messages, max_tokens):
        self.calls.append(model)
        b = self.behavior.get(model, "ok")
        if b == "fail":
            raise RuntimeError(f"{model} indisponível")
        if b == "timeout":
            import asyncio

            await asyncio.sleep(100)
        return {"model": model}


class _FakeClient:
    def __init__(self, behavior: dict | None = None):
        self.messages = _FakeMessages(behavior or {})


async def test_primary_model_used_when_healthy():
    r = ModelRouter(_FakeClient())
    resp = await r.complete(TaskComplexity.COMPLEX, "sys", [{"role": "user", "content": "x"}])
    assert resp["model"] == "claude-opus-4-8"


async def test_fallback_when_primary_fails():
    r = ModelRouter(_FakeClient({"claude-opus-4-8": "fail"}), max_retries=1)
    resp = await r.complete(TaskComplexity.COMPLEX, "sys", [{"role": "user", "content": "x"}])
    assert resp["model"] == "claude-sonnet-4-6"


async def test_circuit_open_when_all_fail():
    r = ModelRouter(
        _FakeClient({"claude-opus-4-8": "fail", "claude-sonnet-4-6": "fail"}),
        max_retries=1,
    )
    with pytest.raises(CircuitOpenError):
        await r.complete(TaskComplexity.COMPLEX, "sys", [{"role": "user", "content": "x"}])


async def test_breaker_opens_after_threshold():
    client = _FakeClient({"claude-opus-4-8": "fail", "claude-sonnet-4-6": "fail"})
    r = ModelRouter(client, max_retries=0, failure_threshold=3)
    for _ in range(3):
        with pytest.raises(CircuitOpenError):
            await r.complete(TaskComplexity.COMPLEX, "sys", [{"role": "user", "content": "x"}])
    assert r._breakers["claude-opus-4-8"].opened_at is not None


async def test_timeout_respected():
    r = ModelRouter(
        _FakeClient({"claude-opus-4-8": "timeout", "claude-sonnet-4-6": "timeout"}),
        max_retries=0,
        request_timeout=0.4,
    )
    start = time.monotonic()
    with pytest.raises(CircuitOpenError):
        await r.complete(TaskComplexity.COMPLEX, "sys", [{"role": "user", "content": "x"}])
    assert time.monotonic() - start < 3


async def test_fast_complexity_uses_haiku_first():
    client = _FakeClient()
    r = ModelRouter(client)
    await r.complete(TaskComplexity.FAST, "sys", [{"role": "user", "content": "x"}])
    assert client.messages.calls[0] == "claude-haiku-4-5"


async def test_breaker_recovers_after_window():
    import asyncio

    # Ambos falham para garantir CircuitOpenError e abertura do breaker do opus.
    client = _FakeClient({"claude-opus-4-8": "fail", "claude-sonnet-4-6": "fail"})
    r = ModelRouter(client, max_retries=0, failure_threshold=1, recovery_seconds=0.3)
    with pytest.raises(CircuitOpenError):
        await r.complete(TaskComplexity.COMPLEX, "sys", [{"role": "user", "content": "x"}])
    # Breaker do opus deve estar aberto logo após a falha.
    assert r._is_open("claude-opus-4-8")
    # Após a janela de recuperação, deve voltar a aceitar tentativas (meio-aberto).
    await asyncio.sleep(0.4)
    assert not r._is_open("claude-opus-4-8")
