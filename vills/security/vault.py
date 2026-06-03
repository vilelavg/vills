"""Vault — criptografia de segredos por tenant.

Usa Fernet com chave derivada do tenant_id + chave mestra do ambiente.
A abstração permite trocar para AWS KMS na F4 sem alterar os consumidores.
"""

import base64
import hashlib
import uuid

from cryptography.fernet import Fernet

from vills.core.settings import get_settings


def _derive_key(tenant_id: uuid.UUID) -> bytes:
    """Deriva uma chave Fernet determinística por tenant.

    Combina a chave mestra (env) com o tenant_id. Tenants diferentes
    têm chaves diferentes — vazar a chave de um não compromete outros.
    """
    master = get_settings().encryption_key.get_secret_value().encode()
    digest = hashlib.sha256(master + tenant_id.bytes).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt_for_tenant(tenant_id: uuid.UUID, plaintext: str) -> str:
    f = Fernet(_derive_key(tenant_id))
    return f.encrypt(plaintext.encode()).decode()


def decrypt_for_tenant(tenant_id: uuid.UUID, ciphertext: str) -> str:
    f = Fernet(_derive_key(tenant_id))
    return f.decrypt(ciphertext.encode()).decode()
