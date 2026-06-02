# Vills — Pacote de homologação F1

Este pacote contém os arquivos corrigidos após a auditoria completa da F1
(51 cenários de teste executados, lint limpo, formatação aplicada) e os
4 novos arquivos de teste que elevam a cobertura de 35% para ~79%.

## O que mudou

### Correções de lógica (3 arquivos)
- vills/tenancy/models.py     — enum migrado para StrEnum (mais seguro)
- vills/core/model_router.py  — enum migrado para StrEnum
- vills/core/feedback_loop.py — enum migrado para StrEnum

### Correções de formatação (10 arquivos)
Todos os demais .py em vills/ — apenas `ruff format` aplicado, sem mudança de comportamento.

### Testes novos (4 arquivos) + conftest atualizado
- tests/test_model_router.py — 7 testes (fallback, circuit breaker, timeout)
- tests/test_tenancy.py      — 12 testes (context, prompt engine, resolver)
- tests/test_feedback.py     — 4 testes (registro, score, escopo)
- tests/test_compressor.py   — 6 testes (compressão, bordas)
- tests/conftest.py          — fixture db_session adicionada
- tests/test_settings.py     — usa ValidationError (lint B017)

## Como aplicar

1. Extraia este pacote na RAIZ do projeto (C:\agenteViLLs\vills), substituindo os arquivos.
2. No PowerShell:
   git status                          # confere o que mudou
   docker compose up -d postgres redis # banco precisa estar no ar p/ testes
   uv run pytest -v                    # deve dar ~40 passed
   uv run ruff check .                 # deve dar "All checks passed!"
3. Se tudo verde:
   git add .
   git commit -m "F1 homologada: testes + lint (cobertura 35% -> 79%)"
   git push

## Importante
A suíte de testes precisa de Postgres no ar (os modelos usam tipos nativos
do Postgres: JSONB e UUID). Rode `docker compose up -d postgres` antes do pytest.
