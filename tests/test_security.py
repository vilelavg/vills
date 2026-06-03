import uuid

import pytest

from vills.security.auth import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from vills.security.mfa import generate_secret, provisioning_uri, verify_code
from vills.security.passwords import hash_password, verify_password
from vills.security.roles import Role
from vills.security.vault import decrypt_for_tenant, encrypt_for_tenant


def test_role_hierarchy():
    assert Role.ADMIN.satisfies(Role.VIEWER)
    assert Role.OPERATOR.satisfies(Role.OPERATOR)
    assert not Role.VIEWER.satisfies(Role.ADMIN)


def test_password_hash_and_verify():
    h = hash_password("senha123")
    assert h != "senha123"
    assert verify_password("senha123", h)
    assert not verify_password("errada", h)


def test_password_over_72_bytes_does_not_crash():
    # bcrypt limita a 72 bytes; truncamento explícito evita erro
    long_pw = "a" * 200
    h = hash_password(long_pw)
    assert verify_password(long_pw, h)


def test_vault_roundtrip():
    tid = uuid.uuid4()
    enc = encrypt_for_tenant(tid, "segredo")
    assert decrypt_for_tenant(tid, enc) == "segredo"


def test_vault_isolates_tenants():
    t1, t2 = uuid.uuid4(), uuid.uuid4()
    enc = encrypt_for_tenant(t1, "segredo")
    with pytest.raises(Exception):
        decrypt_for_tenant(t2, enc)


def test_mfa_valid_and_invalid_code():
    import pyotp

    secret = generate_secret()
    assert verify_code(secret, pyotp.TOTP(secret).now())
    assert not verify_code(secret, "000000")


def test_mfa_uri_has_issuer():
    assert "Vills" in provisioning_uri(generate_secret(), "a@b.com")


def test_jwt_access_token_roundtrip():
    uid = uuid.uuid4()
    token = create_access_token(uid, "webxp", "admin")
    payload = decode_token(token)
    assert payload["sub"] == str(uid)
    assert payload["type"] == "access"
    assert payload["role"] == "admin"
    assert "jti" in payload


def test_jwt_refresh_token_roundtrip():
    uid = uuid.uuid4()
    token, jti = create_refresh_token(uid, "webxp")
    payload = decode_token(token)
    assert payload["type"] == "refresh"
    assert payload["jti"] == jti


def test_jwt_invalid_token_raises():
    with pytest.raises(TokenError):
        decode_token("nao.e.um.token.valido")
