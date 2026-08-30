"""Código do ingresso — o conteúdo do QR.

O código é `<id-curto>.<assinatura>`. A assinatura é um HMAC-SHA256 do id, com
segredo que só o servidor conhece, truncado para caber num QR legível por
câmera de celular.

Por que não só o id: qualquer pessoa que visse um ingresso descobriria o
formato e geraria códigos válidos para outros ids. Com assinatura, forjar exige
o segredo.

A portaria confere duas coisas, e precisa das duas: a assinatura prova que o
código saiu daqui; a consulta ao banco prova que ele ainda vale e não foi
usado. Assinatura sozinha não impede reuso; banco sozinho não impede invenção.

Ver decisão D6.
"""
import base64
import hashlib
import hmac
import uuid

from app.config import get_settings

# 20 caracteres base32 carregam 100 bits de assinatura. Sobra folga contra
# tentativa por força bruta e o QR continua pequeno o bastante para leitura
# rápida em câmera de celular.
SIGNATURE_LENGTH = 20


def _assina(ticket_id: uuid.UUID) -> str:
    segredo = get_settings().ticket_secret.encode("utf-8")
    digest = hmac.new(segredo, ticket_id.bytes, hashlib.sha256).digest()
    return base64.b32encode(digest).decode("ascii")[:SIGNATURE_LENGTH]


def _id_curto(ticket_id: uuid.UUID) -> str:
    """UUID em base32 sem padding: 26 caracteres, só letras e dígitos.

    Base32 em vez de hexadecimal porque o alfabeto é menor e mais tolerante a
    leitura manual — o código também pode ser digitado na portaria quando a
    câmera falha.
    """
    return base64.b32encode(ticket_id.bytes).decode("ascii").rstrip("=")


def issue(ticket_id: uuid.UUID) -> str:
    return f"{_id_curto(ticket_id)}.{_assina(ticket_id)}"


def verify(code: str) -> uuid.UUID | None:
    """Devolve o id do ingresso se o código for autêntico; None se não for.

    Aceita o código com espaços ou em minúsculas: quem digita na portaria está
    olhando para um papel, não copiando e colando.
    """
    limpo = code.strip().replace(" ", "").replace("-", "").upper()
    if limpo.count(".") != 1:
        return None

    parte_id, signature = limpo.split(".")

    try:
        bruto = base64.b32decode(parte_id + "=" * (-len(parte_id) % 8))
        ticket_id = uuid.UUID(bytes=bruto)
    except (ValueError, TypeError):
        return None

    # compare_digest em vez de ==: comparação byte a byte que sai no primeiro
    # caractere diferente vaza, pelo tempo de resposta, quanto do código estava
    # certo — e isso é o suficiente para descobrir uma assinatura tentativa
    # após tentativa.
    if not hmac.compare_digest(signature, _assina(ticket_id)):
        return None

    return ticket_id
