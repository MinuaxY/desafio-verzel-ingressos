"""Ponto de entrada da API."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.core.http_security import install as install_security_headers
from app.routers import auth, catalog, gate, orders, rooms, sessions

settings = get_settings()

app = FastAPI(
    title="Verzel Ingressos",
    description="Plataforma de sessões de cinema e ingressos. Desafio Elite Dev.",
    version="0.1.0",
)

install_security_headers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(catalog.router)
app.include_router(rooms.router)
app.include_router(sessions.publico)
app.include_router(sessions.gestao)
app.include_router(orders.mapa)
app.include_router(orders.compra)
app.include_router(orders.carteira)
app.include_router(gate.gate)
app.include_router(gate.compartilhado)


@app.get("/health", tags=["Infra"])
def health() -> dict[str, str]:
    return {"status": "ok"}
