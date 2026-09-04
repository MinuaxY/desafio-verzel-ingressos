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
- [Gestão da programação](#gestão-da-programação)
- [Segurança e dados pessoais](#segurança-e-dados-pessoais)
- [Testes](#testes)
- [Estrutura](#estrutura)
- [Limitações conhecidas](#limitações-conhecidas)
- [Uso de IA](#uso-de-ia)
- [Artefatos de processo](#artefatos-de-processo)

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

O **cadastro público cria sempre cliente**. Organizador e portaria são contas concedidas, não
escolhidas, e vêm de um fluxo administrativo fora da API:

```bash
python -m app.admin criar-organizador "Cine Verzel" contato@cine.dev
python -m app.admin criar-portaria "Portaria Sala 1" portaria@cine.dev
python -m app.admin promover contato@cine.dev ORGANIZER
python -m app.admin listar
```

A senha é pedida no terminal, sem eco — passá-la como argumento a deixaria no histórico do
shell. O porquê disso não ser um endpoint está na decisão D34.

Rodar o seed de novo no mesmo dia não duplica nada: a chave é `(sala, horário)`, a mesma que o
banco usa para impedir duas sessões na mesma sala ao mesmo tempo.

O seed também cria **três salas** e uma programação de **dez dias** com os treze filmes do
catálogo local — cerca de **90 sessões publicadas**, o suficiente para a vitrine exercitar
paginação, filtro por dia e busca de verdade:

| Sala | Lugares | Desenho | Preços |
|---|---|---|---|
| Sala 1 — Cine Verzel | 88 | Plateia 6×12 (dois corredores) + VIP 2×8 | R$ 32 / R$ 54 |
| Sala 2 — Cine Verzel | 32 | Plateia 4×8, setor único, corredor central | R$ 26 |
| Sala 3 — Cine Verzel (IMAX) | 132 | Plateia 8×14 (três corredores) + VIP 2×10 | R$ 38 / R$ 62 |

As geometrias são diferentes de propósito: a Sala 2 mostra que o mapa fica bom sem VIP nenhum,
e a Sala 3 leva o desenho ao limite do que a tela acomoda. Ao todo são **23 poltronas
acessíveis** marcadas, das quatro naturezas.

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
   que está em cartaz nem para abrir o mapa de assentos. Use a **barra de datas** no topo para
   filtrar por dia: o seed publica cerca de 90 sessões em dez dias, então há o que filtrar.
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

### Se sobrar tempo — a gestão da programação

Estes três levam mais dois minutos e mostram a parte do sistema que mais tem regra por trás:

- **Repetir em vários dias.** Em Nova sessão, escolha filme, sala e horário, e abra *Repetir em
   outros dias*. Marque uma semana inteira e crie. Os dias em que a sala já está ocupada voltam
   numa lista, com o motivo, em vez de derrubar o lote.
- **Cancelar uma sessão que vendeu.** Compre um ingresso para uma sessão, volte ao painel do
   organizador e tente cancelá-la: o botão está desabilitado, dizendo quantos ingressos há. Ao
   lado dele existe **"cancelar os N pedidos vendidos"**, que é o passo explícito — depois dele,
   cancelar funciona. Abra o pedido como cliente: ele diz que **o cinema** cancelou.
- **Excluir e editar.** Rascunho pode ser apagado, publicada não; sala com sessão futura não é
   removida. Cada recusa vem com o motivo na tela.

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

## Gestão da programação

Além de criar sessão a sessão, o organizador tem:

**Repetir em vários dias.** Os dias são marcados num calendário de quatro semanas, com atalhos
para "toda sexta" e "sextas, sábados e domingos". Dia em que a sala já está ocupada é pulado, e
a lista do que ficou de fora volta com o motivo — um conflito não descarta o resto da seleção.
Está tanto na criação quanto na edição: na tela de editar, ele cria cópias da sessão em outros
dias, usando o que estiver no formulário.

**Despublicar e cancelar são coisas diferentes, e o sistema trata assim.**

| | Despublicar | Cancelar |
|---|---|---|
| A sessão vai acontecer? | Sim | Não |
| Para de vender? | Sim | Sim |
| Quem já comprou entra? | Sim | Não existe esse caso |
| Reversível? | Sim, republicando | Não |

Cancelar só é aceito com a sessão **vazia**. Com ingresso vendido, a API responde 409 dizendo
quantos são e o painel mostra o botão desabilitado com o motivo — porque o sistema não manda
e-mail nem estorna, e um cancelamento que só apaga a sessão da tela do organizador deixaria a
pessoa descobrindo na porta do cinema. Para esse caso existe um passo à parte, **"cancelar os
N pedidos vendidos"**, que desfaz as compras de propósito e explicitamente. O pedido guarda
**quem** cancelou, para o cliente ler "o cinema cancelou" em vez de achar que a desistência foi
dele.

Isso nasceu de um defeito real: cancelar mexia só no estado da sessão, e o QR de uma sessão
cancelada passava na portaria. Ver [D30](docs/decisoes.md).

**Editar e remover.** Rascunho pode ser apagado; publicada sai do cartaz com despublicar;
cancelada que nunca vendeu nada também pode ser apagada, mas a que teve pedido fica, para dar
como rastrear aquela compra.

**Sessão cancelada não ocupa a sala.** Como cancelar não tem volta, contá-la prenderia aquele
horário para sempre. É a mesma regra do índice que impede vender a poltrona duas vezes:
cancelado não ocupa. Ver [D31](docs/decisoes.md).

Sala segue a mesma lógica: **sala nunca usada é apagada de verdade; sala com histórico é
desativada**, porque sessão passada aponta para ela. **Sala com sessão futura não é
removida** — há gente podendo comprar para ela agora.

**A sala é reservada pelo intervalo que a sessão ocupa** — início, duração do filme e folga de
limpeza —, e não só pelo horário de início. Duas sessões de duas horas às 20:00 e às 20:01 na
mesma sala eram aceitas antes; agora o banco recusa, com uma constraint de exclusão. Ver
decisão D37.

**O layout da sala trava na primeira sessão.** Nome e endereço continuam editáveis, mas
fileiras, poltronas e corredores não: o ingresso guarda o código da poltrona, e mudar a
geometria faria a `F12` de alguém apontar para um lugar que deixou de existir. Pela mesma
razão, o horário de uma sessão não muda depois que alguém compra.

Para o cliente, a vitrine tem **filtro por dia** — uma barra com as próximas duas semanas,
onde dia sem sessão aparece desabilitado em vez de oferecer um clique que não leva a nada.

---

## Segurança e dados pessoais

Uma revisão dedicada foi feita no fim do projeto. O que segue é o resultado, incluindo o que
**não** foi resolvido.

### O que está protegido

| | |
|---|---|
| **Senhas** | bcrypt, nunca em texto. Hash calculado no servidor |
| **Autorização** | Verificada por papel em cada rota, com 403 distinto de 401, e coberta por testes |
| **Concessão de papel** | O cadastro público cria **sempre** cliente. Organizador e portaria vêm de `python -m app.admin`, fora da API |
| **Enumeração de contas** | Senha errada e e-mail inexistente devolvem exatamente a mesma resposta |
| **Recursos de terceiros** | Sala de outro organizador responde 404, não 403: confirmar a existência já entregaria informação |
| **Ingresso** | QR assinado com HMAC-SHA256 e segredo próprio, comparado em tempo constante |
| **Segredos** | Fora do repositório; em produção são gerados pela plataforma e ninguém os vê |
| **Força bruta** | Cinco tentativas de login por minuto, por IP **e** e-mail |
| **Cabeçalhos** | `nosniff`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, e HSTS sob HTTPS |
| **Mensagens de erro** | Validação devolve só local e motivo, sem o parser por dentro nem o valor enviado |
| **CORS** | Restrito às origens declaradas; verificado contra produção |
| **Injeção de SQL** | Consultas via SQLAlchemy, sem concatenação |
| **Invariantes no banco** | Índice único parcial contra venda dupla, chaves compostas ligando preço à sala da sessão, e constraint de exclusão impedindo duas sessões de ocuparem a mesma sala ao mesmo tempo |
| **Contêiner** | A API roda com usuário sem privilégio |

**Dado de pagamento não é retido.** O número do cartão chega, decide o desfecho e é
descartado — não existe coluna de cartão em tabela nenhuma, e nada disso vai para log.

### O que não foi resolvido, e por quê

**O token fica no `localStorage`, não em cookie `httpOnly`.** Cookie seria mais seguro contra
XSS, mas aqui há uma razão concreta contra: o front está na Vercel e a API no Render, em
domínios diferentes. Cookie entre domínios exige `SameSite=None`, o que **reabre CSRF** e
passaria a exigir token anti-CSRF. Trocaria uma exposição por outra, e exigiria refazer a
autenticação inteira num projeto já validado. Fica registrado como o primeiro item a mudar se
o sistema fosse a público — junto com pôr front e API no mesmo domínio.

**Não há revogação de token.** Sair apaga o token do navegador, mas o servidor aceitaria
aquele token até expirar, em oito horas. Revogar de verdade exige lista compartilhada entre
instâncias, e o projeto não tem esse armazenamento.

**O limite de tentativas vive em memória**, então vale por instância. Com mais de um processo,
cada um contaria por si — mesma limitação do cache do catálogo, mesma resposta: Redis seria o
passo seguinte.

**As contas de demonstração têm senha pública neste README.** É proposital, para a avaliação
ser possível sem cadastro — mas significa que, no ambiente publicado, qualquer pessoa pode
entrar como organizador e criar ou cancelar sessões. Isso é diferente de *se cadastrar* como
organizador, que a API recusa desde a decisão D34.

**A portaria valida ingresso de qualquer organizador.** Um usuário de portaria não pertence a
um cinema: o papel dá acesso à validação em geral, não à validação daquele local. Amarrar
funcionário ao organizador é modelagem que ainda não existe, e está na fila.

**A documentação da API está aberta em produção** (`/docs`). Desejável aqui, para a avaliação;
em sistema real, ficaria atrás de autenticação.

### LGPD

**A favor:** coleta mínima — nome, e-mail e hash de senha, nada além do necessário para o
sistema funcionar. Dado de pagamento não é retido. Nenhum dado pessoal aparece em URL.

**O que não existe, e um sistema em produção precisaria ter:**

- Política de privacidade e base legal declarada
- Registro de consentimento
- Direitos do titular: acesso, correção, **exclusão** e portabilidade — hoje o usuário não
  consegue apagar a própria conta
- Prazo de retenção e política de descarte
- Registro de quem acessou dado pessoal

Isso não foi implementado porque exclusão de conta feita pela metade é pior que ausente: sem
política de retenção definida, apagar um usuário levaria junto ingressos já validados, que são
registro operacional. A decisão certa seria anonimizar em vez de apagar — e essa é uma
discussão de produto, não de código.

Como o sistema não vai a público e não trata dado real, a ausência desse aparato é aceitável
aqui. Aparece nesta lista porque omitir seria pior.

---

## Testes

### Back-end

```bash
cd api
python -m pytest -v
```

**264 testes**, rodando contra um banco Postgres separado (`verzel_test`), criado e destruído a
cada execução — o container precisa estar de pé. Usar o mesmo SGBD da aplicação evita que um
teste passe em SQLite e quebre em produção por causa de enum nativo ou índice parcial.

| Arquivo | Testes | Cobre |
|---|---|---|
| `test_melhorias.py` | 78 | Gestão da programação, cancelamento, e os defeitos da revisão |
| `test_rooms.py` | 31 | Salas, setores, isolamento entre organizadores, edição e remoção |
| `test_portaria.py` | 29 | Quatro vereditos, código forjado, tolerância na digitação, link compartilhado |
| `test_compra.py` | 27 | Reserva, pagamento aprovado e recusado, devolução de assento, expiração |
| `test_sessions.py` | 21 | Criação, ciclo de vida, vitrine pública |
| `test_exibicao.py` | 16 | Classificação indicativa, áudio e formato da sessão |
| `test_seguranca.py` | 14 | Limite de tentativas, cabeçalhos, erro sem estrutura interna |
| `test_auth.py` | 20 | Cadastro, login, autorização por papel, fronteira de confiança |
| `test_catalog.py` | 13 | Provedor trocável, cache, tradução de erro |
| `test_acessibilidade.py` | 12 | Marcação de poltronas, validação de geometria |
| `test_concorrencia.py` | 3 | Oito threads disputando a mesma poltrona |

O `test_melhorias.py` cresceu por acúmulo: começou nas melhorias de gestão (D26–D29) e recebeu
o cancelamento (D30–D31) e os defeitos da revisão (D33). Num projeto que continuasse, seria
dividido por assunto — está aqui como está porque é o que foi feito, não o que ficaria bonito.

### Front-end

```bash
cd web
npm test
```

**136 testes** com Vitest e Testing Library. Cobrem a lógica e os componentes com regra —
`lib` em 95%, `components` em 83%, `auth` em 77%.

| Arquivo | Testes | Cobre |
|---|---|---|
| `MapaDeAssentos.test.tsx` | 22 | Orientação da sala, corredores, estados da poltrona, limite de seleção |
| `api.test.ts` | 11 | Tradução de erro do FastAPI, token, falha de rede |
| `formato.test.ts` | 16 | Moeda em centavos, faixa de preço, duração, prazo da reserva |
| `tipos.test.ts` | 12 | Classificação indicativa, rótulos, naturezas de poltrona |
| `EmCartaz.test.tsx` | 13 | Vitrine pública, busca, estado vazio, servidor fora do ar |
| `Ingresso.test.tsx` | 12 | QR, código, compartilhamento, ingresso não pago |
| `ProtectedRoute.test.tsx` | 7 | Acesso por papel, token inválido, espera pela sessão |
| `EscolhaDeDias.test.tsx` | 15 | Repetição em vários dias, atalhos, dia principal travado, contagem na edição |
| `BarraDeDias.test.tsx` | 10 | Filtro por dia, dia sem sessão, data sem escorregar para UTC |
| `Inicio.test.tsx` | 4 | Prévia do cartaz: carregando, erro, vazio e com sessões |
| `Pedido.test.tsx` | 4 | Quem cancelou o pedido: a desistência do cliente e o cancelamento pelo cinema |
| `Portaria.test.tsx` | 5 | Sessões do turno: carregando, falha que deixa a porta permissiva, retentativa |
| `NovaSessao.test.tsx` | 5 | O passo da sala não afirma que não há salas antes de saber |


### Ponta a ponta, em navegador de verdade

```bash
npm run e2e          # precisa do banco e da API de pé
```

**33 testes** em Playwright, rodando em dois projetos: `desktop` e `celular` — este fixado em
**375px de propósito**, porque foi onde os defeitos de layout apareceram e porque num aparelho
mais largo eles não reaparecem.

| Arquivo | Testes | Cobre |
|---|---|---|
| `compra.spec.ts` | 4 | Do cartaz ao QR: entrar, escolher poltrona, pagar. A poltrona vendida voltando ocupada. E desistir do pedido, com a poltrona voltando ao estoque |
| `geometria.spec.ts` | 6 | Nenhuma tela rola de lado, o mapa começa na primeira poltrona, alvo de 40px no dedo |
| `portaria.spec.ts` | 4 | Os quatro vereditos, com ingresso comprado pela tela: sessão errada, entrada liberada, reuso e código inventado |
| `gestao.spec.ts` | 3 | O ciclo do organizador: publicar, aparecer no cartaz, despublicar e excluir. Repetir em vários dias. E a trava do preço por setor |

Existem porque a suíte de unidade é cega para layout e não atravessa telas. E cada arquivo foi
conferido ao contrário, quebrando de propósito o que ele deveria proteger: revertendo a correção
da D39, quatro dos seis testes de geometria ficam vermelhos; fazendo a portaria parar de enviar a
sessão da porta, o ingresso de outra sala passa a receber "Pode entrar"; trocando o `every` por
`some` na trava de preço, a sessão passa a poder ir ao ar com um setor sem valor. Ver decisão D41.


---

## Estrutura

```
desafio-verzel-ingressos/
├── docker-compose.yml
├── docs/
│   ├── decisoes.md          as 42 decisões técnicas, e o que foi descartado em cada uma
│   ├── backlog.md           requisitos, o que foi entregue e o que ficou fora do escopo
│   ├── diario.md            o que aconteceu em ordem, incluindo o que deu errado
│   ├── quadro.md            o kanban ao fim do projeto
│   ├── aprendizados.md      as lições transferíveis, cada uma com o episódio que a originou
│   └── ia.md                como a IA foi usada, e o que foi feito sem
├── api/
│   ├── alembic/versions/    10 migrations
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
    ├── e2e/                 testes de ponta a ponta em navegador de verdade
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

- **Cinco das treze páginas têm teste de unidade.** A vitrine, o pedido, a landing, a portaria
  e a criação de sessão. O painel do organizador e a gestão da programação ainda só foram
  verificados manualmente no navegador.
- **Os testes de unidade não veem geometria** — e isso agora está coberto por outra suíte. O
  jsdom não calcula layout, então largura, transbordo e rolagem não existem para ele: um defeito
  real de recorte do mapa no celular passou pelos 22 testes do componente sem que nenhum ficasse
  vermelho (D39). Os testes de ponta a ponta em Playwright cobrem essa classe (D41); o que falta
  ali é a portaria e a gestão.
- **Cancelar a sessão não avisa nem estorna ninguém.** Quando o organizador desfaz os pedidos
  de uma sessão, o cliente descobre ao abrir a compra — que passa a dizer que o cinema
  cancelou e que a devolução é com o organizador. Falta o e-mail e falta o estorno, e é por
  isso que a operação é um passo separado e explícito em vez de um efeito colateral de
  cancelar a sessão. Ver decisão D30.
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

## Artefatos de processo

Estão versionados junto do código, em `docs/`, e não num anexo à parte. São o registro de como
o projeto foi conduzido — que é o que este desafio diz avaliar.

| | |
|---|---|
| [`decisoes.md`](docs/decisoes.md) | As **42 decisões técnicas**, cada uma com o que foi **descartado** e por quê |
| [`diario.md`](docs/diario.md) | O que aconteceu em ordem, **incluindo o que deu errado** — o dia perdido, o defeito no cancelamento, os erros que o deploy encontrou |
| [`backlog.md`](docs/backlog.md) | Requisitos do enunciado, o que foi entregue, o que foi feito por iniciativa e o que ficou fora do escopo de propósito |
| [`quadro.md`](docs/quadro.md) | O kanban ao fim do projeto, com uma coluna para o que foi **avaliado e descartado** |
| [`aprendizados.md`](docs/aprendizados.md) | As **21 lições** que ficaram, cada uma amarrada ao episódio concreto que a originou |
| [`ia.md`](docs/ia.md) | Onde a IA entrou, onde não entrou, e onde ela errou |

Os quatro primeiros são espelhos de um vault do Obsidian usado durante o projeto — por isso o
tom de anotação de trabalho, e não de documento escrito depois para parecer organizado.
