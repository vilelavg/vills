"""Hashing de senhas com bcrypt.

Usa a biblioteca bcrypt diretamente (não passlib, que está sem manutenção
e quebra com bcrypt >= 4.1). bcrypt limita senhas a 72 bytes — truncamos
de forma explícita e segura antes de hashear.
"""

import bcrypt

_MAX_BYTES = 72


def _truncate(plain: str) -> bytes:
    """bcrypt ignora bytes além de 72. Truncamos explicitamente para evitar erro."""
    return plain.encode("utf-8")[:_MAX_BYTES]


def hash_password(plain: str) -> str:
    hashed = bcrypt.hashpw(_truncate(plain), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_truncate(plain), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False
