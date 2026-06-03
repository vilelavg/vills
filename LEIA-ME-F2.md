# Vills — Pacote F2 (Segurança + Memória + Fila)

24 arquivos: 19 novos + settings.py (modificado) + conftest.py (atualizado) + 4 testes.

## O que tem aqui

### Segurança (vills/security/)
- roles.py       — Role enum (admin/operator/viewer) com hierarquia
- models.py      — AgencyUser (quem faz login)
- passwords.py   — hashing bcrypt (sem passlib; bcrypt direto)
- vault.py       — criptografia de segredos por tenant (Fernet)
- auth.py        — JWT access + refresh + revogação no Redis
- mfa.py         — TOTP (pyotp)
- rbac.py        — dependências FastAPI: auth -> tenant -> papel (bloqueia cross-tenant)
- audit.py       — AuditLog append-only (LGPD)

### Memória (vills/memory/)
- models.py        — MemoryChunk com embedding pgvector
- embeddings.py    — serviço de embeddings com provider plugável
- hybrid_search.py — RAG híbrido (pgvector + pg_trgm), isolado por tenant

### Workers (vills/workers/)
- app.py    — Celery configurado (broker Redis)
- tasks.py  — tasks assíncronas (health_ping de exemplo)
- locks.py  — lock distribuído via Redis (idempotência)

### API
- api/v1/auth.py — endpoints login/refresh/logout

### Modificados
- core/settings.py — campos JWT, encryption, celery, mfa
- tests/conftest.py — registra modelos F2 + cria extensões vector/pg_trgm antes do create_all

### Migration
- 0002_security_and_memory.py — cria extensões ANTES das tabelas (R3)

## ANTES de aplicar — instalar dependências novas

Adicione ao pyproject.toml em [project] dependencies:
    "python-jose[cryptography]>=3.3",
    "bcrypt>=4.1",
    "pyotp>=2.9",
    "qrcode>=8.0",
    "celery[redis]>=5.4",
    "pgvector>=0.3",

Depois: uv sync

## ANTES de aplicar — atualizar o .env

Adicione ao .env:
    JWT_SECRET_KEY=<gere uma chave aleatória forte>
    ENCRYPTION_KEY=<gere outra chave aleatória forte>
    CELERY_BROKER_URL=redis://localhost:6380/1

Para gerar chaves no PowerShell:
    python -c "import secrets; print(secrets.token_urlsafe(48))"

## Aplicar

1. Extraia na raiz do projeto, substituindo settings.py e conftest.py.
2. Atualize pyproject.toml e .env (acima).
3. uv sync
4. docker compose up -d postgres redis
5. uv run alembic upgrade head   (aplica a migration 0002)
6. uv run python -m pytest -v
7. uv run ruff check .

Esperado: todos passam. Os testes de memory_chunks precisam de pg_trgm,
que a imagem pgvector/pgvector:pg16 já tem.

## Importante (R2 — Celery no Windows)
O worker Celery roda no container Linux via docker-compose. Não rode o worker
direto no Windows. Para subir o worker em dev:
    docker compose up worker
