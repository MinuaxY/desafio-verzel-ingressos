# Imagem do front. Build em dois estágios: o Node compila, o nginx serve.
#
# O que vai para produção é só HTML, CSS e JS estáticos — o node_modules
# inteiro, com centenas de megabytes, fica para trás no primeiro estágio.

FROM node:22-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

# A URL da API entra no momento da build, não em tempo de execução: o Vite
# substitui import.meta.env no código gerado, e depois disso o valor está
# fixo no bundle. Trocar de API exige rebuild — é o custo de servir estático.
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build


FROM nginx:1.27-alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
  CMD wget --quiet --tries=1 --spider http://localhost/ || exit 1
