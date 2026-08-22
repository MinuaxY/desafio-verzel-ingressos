"""Cabeçalhos de segurança e tratamento de erro que não vaza estrutura."""
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# Cabeçalhos que valem para uma API JSON.
#
# Nada de Content-Security-Policy aqui: a API não serve HTML, e a política que
# importa é a do front, servido pelo nginx. Colocar uma CSP nesta resposta daria
# sensação de proteção sem proteger nada.
CABECALHOS = {
    # O navegador não deve adivinhar o tipo do conteúdo. Sem isto, um JSON com
    # conteúdo controlado pelo usuário pode ser interpretado como HTML.
    "X-Content-Type-Options": "nosniff",
    # Ninguém precisa embutir a API num iframe.
    "X-Frame-Options": "DENY",
    # A URL da API não deve vazar para terceiros pelo cabeçalho de origem.
    "Referrer-Policy": "no-referrer",
    # A API não usa câmera, microfone nem localização; o front usa câmera na
    # portaria, e quem libera isso é o documento dele, não esta resposta.
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}

# HSTS só faz sentido sob HTTPS. Em desenvolvimento, http://localhost, o
# cabeçalho seria ignorado pelo navegador — ou pior, prenderia o localhost em
# https numa máquina de quem estiver avaliando.
HSTS = "max-age=31536000; includeSubDomains"


class CabecalhosDeSeguranca(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        resposta = await call_next(request)
        for nome, valor in CABECALHOS.items():
            resposta.headers.setdefault(nome, valor)

        # O proxy da plataforma informa o esquema original em X-Forwarded-Proto.
        if request.headers.get("x-forwarded-proto") == "https":
            resposta.headers.setdefault("Strict-Transport-Security", HSTS)

        return resposta


def instalar(app: FastAPI) -> None:
    app.add_middleware(CabecalhosDeSeguranca)

    @app.exception_handler(RequestValidationError)
    async def erro_de_validacao(_request: Request, exc: RequestValidationError):
        """Devolve só o que o cliente precisa saber.

        A resposta padrão do FastAPI inclui `ctx` e `input`, que descrevem o
        parser por dentro e devolvem de volta o que foi enviado. Nada disso
        ajuda quem está usando a API, e ajuda quem está sondando.
        """
        limpos = [
            {"loc": erro.get("loc", []), "msg": erro.get("msg", "Valor inválido")}
            for erro in exc.errors()
        ]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail": limpos},
        )
