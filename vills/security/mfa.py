"""MFA via TOTP (pyotp). Secret criptografado pelo vault antes de persistir."""

import pyotp


def generate_secret() -> str:
    """Gera um novo secret TOTP em base32."""
    return pyotp.random_base32()


def provisioning_uri(secret: str, email: str, issuer: str = "Vills") -> str:
    """URI para gerar o QR code que o usuário escaneia no app autenticador."""
    return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name=issuer)


def verify_code(secret: str, code: str) -> bool:
    """Valida um código de 6 dígitos. valid_window=1 tolera relógio levemente fora."""
    return pyotp.TOTP(secret).verify(code, valid_window=1)
