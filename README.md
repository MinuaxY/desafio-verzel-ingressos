# Verzel Ingressos

Plataforma de sessões de cinema e ingressos, feita para o **Desafio Elite Dev**.

O organizador cria sessões a partir do catálogo de filmes do TMDb, definindo sala, horário e
preço por setor. O cliente navega pelo que está em cartaz, escolhe a poltrona num mapa da
sala, paga de forma simulada e recebe um ingresso com código em QR — que pode compartilhar
por link. Na entrada, a portaria lê o QR pela câmera e libera, ou recusa com o motivo.

**Repositório:** https://github.com/MinuaxY/desafio-verzel-ingressos

## 🌐 Aplicação publicada

| | |
|---|---|
| **Aplicação** | https://desafio-verzel-ingressos.vercel.app |
| **API** (documentação navegável) | https://verzel-ingressos-api.onrender.com/docs |

Entre pelo acesso rápido na tela de login — não é preciso digitar credencial.

> **A primeira visita pode demorar até um minuto.** A API está no plano gratuito do Render,
> que hiberna o serviço depois de alguns minutos sem tráfego. A demora é o servidor
> acordando, não a aplicação sendo lenta: depois da primeira requisição, tudo responde
> normalmente. Se a tela disser que não conseguiu falar com o servidor, recarregue após
> alguns segundos.

> A **câmera da portaria** funciona no ambiente publicado, porque ele é HTTPS. Em celular,
> o navegador vai pedir permissão de câmera na primeira leitura.


---

## Sumário

- [Aplicação publicada](#-aplicação-publicada)
- [Stack](#stack)
- [Como executar](#como-executar)
- [Contas de teste](#contas-de-teste)
- [Cartões de teste](#cartões-de-teste)
- [Percorrendo o sistema em 5 minutos](#percorrendo-o-sistema-em-5-minutos)
- [Decisões que valem explicação](#decisões-que-valem-explicação)
- [Testes](#testes)
- [Estrutura](#estrutura)
- [Limitações conhecidas](#limitações-conhecidas)
- [Uso de IA](#uso-de-ia)

---

## Stack

| Camada | Escolha | Por quê |
|---|---|---|
| Front-end | React 19 + Vite + TypeScript | React é exigido pelo desafio; Vite pelo build rápido e configuração mínima |
| Back-end | Python + FastAPI | Documentação OpenAPI automática — dá para navegar a API inteira em `/docs` sem Postman |
| Banco | PostgreSQL 16 | Índice único **parcial**, que é o que garante não vender o mesmo assento duas vezes |
| Catálogo | TMDb | Atrás de um contrato trocável: roda com ou sem chave de API |

Sem Tailwind e sem biblioteca de componentes. O CSS é próprio, com tokens — a razão está em
[`docs/decisoes.md`](docs/decisoes.md#d7-identidade-visual).

---

## Como executar

### Caminho rápido: tudo em um comando

**Pré-requisito:** Docker.

```bash
docker compose up --build
```

Sobe banco, API e front. As migrations e os dados de demonstração são aplicados sozinhos na
partida. Quando terminar, acesse:

- **http://localhost:5173** — a aplicação
- **http://localhost:8000/docs** — a API, navegável

Para derrubar, `docker compose down`. Para zerar o banco junto, `docker compose down -v`.

---

### Caminho de desenvolvimento

Use este se for mexer no código: recarga automática, sem rebuild de imagem a cada alteração.

**Pré-requisitos:** Docker, Python 3.11+ e Node 18+.

#### 1. Banco de dados

```bash
docker compose up -d db
```

Sobe só o PostgreSQL 16, na porta 5432, com usuário, senha e base `verzel`/`verzel`/`verzel_ingressos`.
Espere o container ficar `healthy` — dá para conferir com `docker compose ps`.

#### 2. Back-end

```bash
cd api
python -m venv .venv
```

Ative o ambiente (`.venv\Scripts\activate` no Windows, `source .venv/bin/activate` no
Linux e macOS) e siga:

```bash
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload
```

A API sobe em **http://localhost:8000**, com documentação interativa em
**http://localhost:8000/docs**.

> **Sobre a chave do TMDb:** não é necessária para rodar. Sem `TMDB_READ_TOKEN` preenchido, o
> catálogo cai automaticamente num provedor local com 13 filmes reais capturados do TMDb, e o
> sistema funciona inteiro. Para usar a API de verdade, crie um token em
> [themoviedb.org/settings/api](https://www.themoviedb.org/settings/api) e preencha o `.env`.

#### 3. Front-end

Em outro terminal:

```bash
cd web
npm install
cp .env.example .env
npm run dev
```

A aplicação abre em **http://localhost:5173**.

---

## Contas de teste

Criadas pelo `python -m app.seed`. **Senha de todas: `verzel123`**

| Papel | E-mail | O que faz |
|---|---|---|
| Organizador | `organizador@verzel.dev` | Cadastra salas, cria e publica sessões |
| Cliente | `cliente1@verzel.dev` | Compra ingressos |
| Cliente | `cliente2@verzel.dev` | Serve para testar disputa pela mesma poltrona |
| Portaria | `portaria@verzel.dev` | Valida ingressos na entrada |

A tela de entrada tem **botões de acesso rápido** para os três papéis — não é preciso digitar
credencial para percorrer o sistema.

Rodar o seed de novo não duplica nada: a checagem é por filme e sala, não por horário.

O seed também cria uma sala de **88 lugares** (Plateia 6×12 e VIP 2×8), com **10 poltronas
acessíveis** marcadas, e **4 sessões publicadas** em horários futuros.

---

## Cartões de teste

O pagamento é **simulado**: não há transação financeira nem chamada a provedor externo. O
desfecho vem do número do cartão, como nos ambientes de teste dos provedores de verdade — a
recusa precisa ser provocável de propósito, senão metade do fluxo fica invisível.

| Número | Resultado |
|---|---|
| `4111 1111 1111 1111` | Aprovado |
| `4000 0000 0000 0002` | Recusado — cartão recusado pelo emissor |
| `4000 0000 0000 9995` | Recusado — saldo insuficiente |

Qualquer outro número com 13 a 19 dígitos também é aprovado. Os três ficam **clicáveis na
própria tela de pagamento**, para não precisar consultar este arquivo durante a avaliação.

---

## Percorrendo o sistema em 5 minutos

1. Abra **http://localhost:5173**. A vitrine é pública — não é preciso ter conta para ver o
   que está em cartaz nem para abrir o mapa de assentos.
2. Clique numa sessão. Veja o mapa da sala: poltronas acessíveis aparecem com sigla e borda
   tracejada, não apenas com cor.
3. Escolha dois lugares e clique em **Entrar e continuar**. Na tela de entrada, use o acesso
   rápido de **Cliente**.
4. Na tela de pagamento, clique no cartão `4000 0000 0000 0002` (**recusa**), preencha o nome
   e pague. O pedido é recusado, as poltronas **voltam ao estoque** e nenhum ingresso é emitido.
5. Volte ao cartaz, escolha lugares de novo e pague com `4111 1111 1111 1111`. Você cai em
   **Meus ingressos**, com o QR na tela.
6. Copie o código do ingresso, saia, e entre com o acesso rápido de **Portaria**.
7. Cole o código e valide: **✓ Pode entrar**. Valide o mesmo código de novo: **↻ Já utilizado**.
   Invente um código qualquer: **✕ Não vale**.
8. Para ver a criação de sessão, entre como **Organizador** → Nova sessão. A busca consulta o
   catálogo de filmes.

---

## Decisões que valem explicação

O registro completo — com o que foi **descartado** em cada caso — está em
[`docs/decisoes.md`](docs/decisoes.md). Quatro que respondem as perguntas mais prováveis:

### O mesmo assento não é vendido duas vezes

Verificar disponibilidade na aplicação sempre deixa uma janela: entre ler "está livre" e
gravar, outra compra pode ter gravado. Quem fecha essa janela é o banco, com um **índice único
parcial** em `(sessão, setor, poltrona)` que ignora ingressos cancelados.

Isso resolve dois problemas de uma vez. A segunda venda simultânea é recusada por definição,
sem lock explícito; e um pagamento recusado só precisa marcar o ingresso como cancelado — a
poltrona volta ao estoque sozinha, porque o índice deixa de enxergá-la.

Há um teste com **oito threads disputando a mesma poltrona ao mesmo tempo**: exatamente uma
vence, e nenhum pedido fantasma fica para trás.

### O QR não pode ser forjado

O código carrega o identificador do ingresso **mais uma assinatura HMAC-SHA256** feita com um
segredo do servidor. A portaria confere duas coisas, e precisa das duas: a assinatura prova
que o código saiu deste sistema, e a consulta ao banco prova que ele ainda vale e não foi
usado. Assinatura sozinha não impede reuso; banco sozinho não impede invenção.

O segredo do ingresso é separado do segredo do JWT: comprometer a sessão de um usuário não
pode dar o poder de emitir ingressos.

### A sessão guarda uma cópia do filme

Título, sinopse, pôster e duração são copiados do catálogo no momento em que a sessão é criada,
e não consultados a cada exibição. Se o TMDb sair do ar, mudar o título traduzido ou trocar o
pôster, o ingresso que alguém comprou continua mostrando o que foi vendido. Ingresso é
documento, não consulta ao vivo.

### Acessibilidade não é enfeite de tela

Salas de espetáculo no Brasil têm exigência legal de lugares acessíveis. A poltrona acessível
é característica da **sala**, gravada no banco, em quatro naturezas: espaço para cadeira de
rodas, poltrona de acompanhante, assento largo e mobilidade reduzida.

No mapa, elas têm **sigla e borda tracejada além da cor** — uma interface de acessibilidade que
depende de distinguir matiz é inacessível por construção. Pelo mesmo motivo, cada veredito da
portaria tem símbolo e palavra próprios, não só cor.

Isso não estava no enunciado. Está aqui porque um sistema de cinema que ignora acessibilidade
está incompleto como produto.

---

## Testes

```bash
cd api
python -m pytest -v
```

**135 testes**, rodando contra um banco Postgres separado (`verzel_test`), criado e destruído a
cada execução — o container precisa estar de pé. Usar o mesmo SGBD da aplicação evita que um
teste passe em SQLite e quebre em produção por causa de enum nativo ou índice parcial.

| Arquivo | Testes | Cobre |
|---|---|---|
| `test_portaria.py` | 29 | Quatro vereditos, código forjado, tolerância na digitação, link compartilhado |
| `test_compra.py` | 27 | Reserva, pagamento aprovado e recusado, devolução de assento, expiração |
| `test_sessions.py` | 21 | Criação, ciclo de vida, vitrine pública |
| `test_rooms.py` | 17 | Salas, setores, isolamento entre organizadores |
| `test_auth.py` | 13 | Cadastro, login, autorização por papel |
| `test_catalog.py` | 13 | Provedor trocável, cache, tradução de erro |
| `test_acessibilidade.py` | 12 | Marcação de poltronas, validação de geometria |
| `test_concorrencia.py` | 3 | Oito threads disputando a mesma poltrona |

---

## Estrutura

```
desafio-verzel-ingressos/
├── docker-compose.yml
├── docs/
│   ├── decisoes.md          decisões técnicas e o que foi descartado
│   └── ia.md                como a IA foi usada, e o que foi feito sem
├── api/
│   ├── alembic/versions/    4 migrations
│   ├── app/
│   │   ├── catalog/         provedor de catálogo (TMDb ou local)
│   │   ├── core/            segurança, dependências, código do ingresso
│   │   ├── models/          SQLAlchemy
│   │   ├── repositories/    acesso a dados
│   │   ├── routers/         endpoints
│   │   ├── schemas/         contratos de entrada e saída
│   │   ├── services/        regra de negócio
│   │   └── seed.py
│   └── tests/
└── web/
    └── src/
        ├── auth/            contexto e rotas protegidas
        ├── components/      mapa de assentos, ingresso, QR
        ├── lib/             cliente HTTP, tipos, formatação
        ├── pages/
        └── styles/          tokens e sistema visual
```

Camadas no back: `router → service → repository`. O router não conhece SQL, o service não
conhece HTTP.

---

## Limitações conhecidas

O que **não** está pronto, ou está pronto pela metade:

- **Não há testes automatizados de front-end.** Todo o front foi verificado manualmente no
  navegador, incluindo o fluxo completo de compra e as quatro respostas da portaria. Com mais
  tempo, o primeiro alvo seria o mapa de assentos.
- **O cache do catálogo é em memória**, então vale por instância. Com mais de um processo,
  cada um teria o próprio. Trocar por Redis seria o passo seguinte.
- **A limpeza de reservas vencidas roda no caminho de quem usa**, não em tarefa agendada. O
  projeto não tem processo de fundo, e depender de um seria depender de algo que a avaliação
  não vai ligar. O custo é um `UPDATE` que quase sempre não encontra nada.
- **A câmera da portaria exige HTTPS** fora de `localhost`. É restrição do navegador, não do
  código. No ambiente publicado isso está resolvido; rodando local em rede, use a digitação
  manual, que existe justamente para isso.
- **O ambiente publicado usa o plano gratuito do Render**, que hiberna após alguns minutos
  sem tráfego. A primeira requisição depois disso leva até um minuto. O banco gratuito
  também tem prazo de validade — o link não vive para sempre.
- **Elegibilidade para assento acessível não é validada.** O sistema não tem como conferir
  laudo, e cinemas reais checam na entrada. Marcar sem verificar é o comportamento do mundo real.
- **Meia-entrada não foi implementada.** Abriria uma frente de regra de preço que não cabia no
  prazo.
- **Não há recuperação de senha nem envio de ingresso por e-mail** — ambos dispensados pelo
  enunciado.

---

## Uso de IA

Este projeto foi construído com IA, e o relato está em [`docs/ia.md`](docs/ia.md): quais
ferramentas, em que partes, **o que foi feito sem IA**, e como as decisões foram conduzidas.

Os artefatos de processo — backlog, diário das sprints e o registro de decisões — estão
versionados junto do código, em `docs/`.
