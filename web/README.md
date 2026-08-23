# Front-end — Verzel Ingressos

React 19 + Vite + TypeScript. Para rodar o projeto inteiro, banco e API incluídos, veja o
[README na raiz](../README.md) — esta página cobre só o que é específico do front.

```bash
npm install
cp .env.example .env
npm run dev      # http://localhost:5173
npm test         # 122 testes, Vitest + Testing Library
npm run build    # tsc -b && vite build
npm run lint     # oxlint
```

O `.env` tem uma variável só: `VITE_API_URL`, apontando para a API. O padrão do
`.env.example` é `http://localhost:8000`.

## Como o código está organizado

```
src/
├── auth/         contexto de autenticação e rotas protegidas por papel
├── components/   mapa de assentos, ingresso com QR, escolha de dias, seletores
├── lib/          cliente HTTP, tipos do contrato da API, formatação
├── pages/        uma por rota
└── styles/       tokens e sistema visual
```

## Três coisas que não são óbvias

**Não há Tailwind nem biblioteca de componentes.** O CSS é próprio, sobre tokens declarados em
`styles/tokens.css`. A razão está em [`docs/decisoes.md`](../docs/decisoes.md), D7 — resumida:
uma interface montada com componentes prontos de terceiros teria a cara de qualquer outro
projeto, e o desafio pede o contrário disso.

**Dinheiro trafega em centavos inteiros**, nunca como decimal. O front formata para exibir, com
os helpers de `lib/formato.ts`. Ver D14.

**Datas locais não passam por `toISOString()`.** Ele converte para UTC, e depois das 21h no
Brasil o dia 22 vira 23 — a barra de datas passaria a oferecer amanhã como se fosse hoje. Os
componentes que lidam com dia do calendário usam um helper local `comoData()`. Há teste
cobrindo exatamente esse caso em `BarraDeDias.test.tsx`.

## Testes

Cobrem a lógica e os componentes com regra: o mapa de assentos, o ingresso, a rota protegida, a
vitrine, a escolha de dias e os avisos de pedido cancelado. As páginas de checkout, portaria e
painel do organizador foram verificadas manualmente no navegador, de ponta a ponta — está
declarado nas limitações do README principal.
