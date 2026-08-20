"""Ponto de entrada da API."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import auth

settings = get_settings()

app = FastAPI(
    title="Verzel Ingressos",
    description="Plataforma de sessões de cinema e ingressos. Desafio Elite Dev.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)


@app.get("/health", tags=["Infra"])
def health() -> dict[str, str]:
    return {"status": "ok"}
