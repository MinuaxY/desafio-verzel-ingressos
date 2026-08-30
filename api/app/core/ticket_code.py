"""Código do ingresso — o conteúdo do QR.

Formato: `<id-curto>.<assinatura>`, onde a assinatura é um HMAC-SHA256 do id
truncado. Só o id seria adivinhável; a assinatura exige o segredo do servidor.
Ver decisão D6 para o resto do raciocínio.
"""
import base64
import hashlib
import hmac
import uuid

from app.config import get_settings

# 100 bits de assinatura: folga contra força bruta, e o QR continua pequeno o
# bastante para leitura rápida em câmera de celular.
SIGNATURE_LENGTH = 20


def _sign(ticket_id: uuid.UUID) -> str:
    secret = get_settings().ticket_secret.encode("utf-8")
    digest = hmac.new(secret, ticket_id.bytes, hashlib.sha256).digest()
    return base64.b32encode(digest).decode("ascii")[:SIGNATURE_LENGTH]


def _short_id(ticket_id: uuid.UUID) -> str:
    # Base32 e não hexadecimal: alfabeto menor, mais tolerante a leitura manual
    # quando a câmera falha e alguém digita o código olhando para um papel.
    return base64.b32encode(ticket_id.bytes).decode("ascii").rstrip("=")


def issue(ticket_id: uuid.UUID) -> str:
    return f"{_short_id(ticket_id)}.{_sign(ticket_id)}"


def verify(code: str) -> uuid.UUID | None:
    """Devolve o id do ingresso se o código for autêntico; None se não for."""
    # Espaços e minúsculas são tolerados: quem digita na portaria está lendo de
    # um papel, não copiando e colando.
    clean = code.strip().replace(" ", "").replace("-", "").upper()
    if clean.count(".") != 1:
        return None

    id_part, signature = clean.split(".")

    try:
        raw = base64.b32decode(id_part + "=" * (-len(id_part) % 8))
        ticket_id = uuid.UUID(bytes=raw)
    except (ValueError, TypeError):
        return None

    # compare_digest e não ==: a comparação que sai no primeiro byte diferente
    # vaza, pelo tempo de resposta, quanto da assinatura estava certo.
    if not hmac.compare_digest(signature, _sign(ticket_id)):
        return None

    return ticket_id
