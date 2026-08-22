# Imagem da API.
#
# slim em vez da completa: a diferença é de centenas de megabytes, e nada aqui
# precisa de toolchain de compilação — todas as dependências têm wheel pronto.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# As dependências entram antes do código de propósito: enquanto o
# requirements.txt não mudar, o Docker reaproveita esta camada e a build
# seguinte não reinstala nada.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Usuário sem privilégio: se algo escapar dentro do contêiner, escapa como
# ninguém.
RUN useradd --create-home --uid 1000 verzel && chown -R verzel:verzel /app
USER verzel

EXPOSE 8000

CMD ["./start.sh"]
