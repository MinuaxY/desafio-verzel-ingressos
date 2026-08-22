#!/bin/sh
# Partida da API em produção.
#
# As migrations rodam aqui, e não num passo manual do painel: um deploy que
# sobe código novo contra schema velho quebra de um jeito difícil de
# diagnosticar. O Alembic é idempotente — se já estiver na versão, não faz nada.
set -e

echo "→ aplicando migrations"
alembic upgrade head

# O seed é opcional e desligado por padrão. Numa avaliação, os dados de teste
# precisam existir; num ambiente real, criar usuários com senha conhecida seria
# um problema. Quem liga é quem hospeda, com SEED_ON_START=true.
if [ "${SEED_ON_START:-false}" = "true" ]; then
  echo "→ semeando dados de demonstração"
  python -m app.seed
fi

# A porta vem da plataforma. Render, Railway e Fly definem $PORT e esperam que
# o processo escute nela; fixar 8000 faria o serviço subir e nunca receber
# tráfego, sem erro nenhum no log.
PORTA="${PORT:-8000}"
echo "→ subindo em 0.0.0.0:${PORTA}"
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORTA}" --proxy-headers --forwarded-allow-ips='*'
