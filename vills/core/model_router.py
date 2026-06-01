"""ModelRouter — escolhe o modelo Claude por complexidade, com fallback
e circuit breaker. Resolve os pontos críticos de resiliência do diagnóstico."""

import asyncio
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

from vills.observability.logging import get_logger

log = get_logger(__name__)


class TaskComplexity(str, Enum):
    FAST = "fast"
    STANDARD = "standard"
    COMPLEX = "complex"


MODEL_CHAINS: dict[TaskComplexity, list[str]] = {
    TaskComplexity.FAST: ["claude-haiku-4-5", "claude-sonnet-4-6"],
    TaskComplexity.STANDARD: ["claude-sonnet-4-6", "claude-haiku-4-5"],
    TaskComplexity.COMPLEX: ["claude-opus-4-8", "claude-sonnet-4-6"],
}


@dataclass
class _BreakerState:
    failures: int = 0
    opened_at: float | None = None


class CircuitOpenError(Exception):
    """O circuit breaker está aberto — modelo indisponível no momento."""


class ModelRouter:
    def __init__(
        self,
        client: Any,
        max_retries: int = 2,
        failure_threshold: int = 5,
        recovery_seconds: float = 30.0,
        request_timeout: float = 60.0,
    ) -> None:
        self._client = client
        self._max_retries = max_retries
        self._failure_threshold = failure_threshold
        self._recovery_seconds = recovery_seconds
        self._request_timeout = request_timeout
        self._breakers: dict[str, _BreakerState] = {}

    def _breaker(self, model: str) -> _BreakerState:
        return self._breakers.setdefault(model, _BreakerState())

    def _is_open(self, model: str) -> bool:
        state = self._breaker(model)
        if state.opened_at is None:
            return False
        if time.monotonic() - state.opened_at >= self._recovery_seconds:
            state.opened_at = None
            state.failures = 0
            return False
        return True

    def _record_failure(self, model: str) -> None:
        state = self._breaker(model)
        state.failures += 1
        if state.failures >= self._failure_threshold:
            state.opened_at = time.monotonic()
            log.warning("circuit_opened", model=model, failures=state.failures)

    def _record_success(self, model: str) -> None:
        self._breakers[model] = _BreakerState()

    async def complete(
        self,
        complexity: TaskComplexity,
        system: str,
        messages: list[dict[str, Any]],
        max_tokens: int = 4096,
    ) -> Any:
        """Tenta cada modelo da cadeia até um responder."""
        chain = MODEL_CHAINS[complexity]
        last_error: Exception | None = None

        for model in chain:
            if self._is_open(model):
                log.info("circuit_skip", model=model)
                continue

            for attempt in range(self._max_retries + 1):
                try:
                    async with asyncio.timeout(self._request_timeout):
                        response = await self._client.messages.create(
                            model=model,
                            system=system,
                            messages=messages,
                            max_tokens=max_tokens,
                        )
                    self._record_success(model)
                    return response
                except Exception as exc:  # noqa: BLE001
                    last_error = exc
                    self._record_failure(model)
                    log.warning(
                        "model_call_failed",
                        model=model,
                        attempt=attempt,
                        error=str(exc),
                    )
                    if attempt < self._max_retries:
                        await asyncio.sleep(min(2**attempt, 8))

        raise CircuitOpenError(
            f"Todos os modelos da cadeia {complexity} falharam"
        ) from last_error
