<!-- Espelho de "Product Backlog", do vault de anotações do projeto (Obsidian).
     Versionado aqui porque o desafio pede os artefatos de processo junto do código. -->

# Product Backlog — Desafio Elite Dev Verzel

**Recebido:** 17/08 · **Entregue:** 22/08/2026 · **Revisado até** 23/08 · **Prazo:** 23/08

> ✅ **Projeto concluído.** Este arquivo virou registro do que foi entregue.
> Ver [Diário das Sprints](diario.md) para a ordem dos fatos, [Aprendizados](aprendizados.md) para o que
> ficou de lição, e Entrega para o checklist final.
>
> A entrega saiu um dia antes do prazo. O dia que sobrou foi usado em melhorias de
> gestão, numa revisão de código que achou três defeitos, e no volume da vitrine —
> tudo registrado abaixo.

## Produto

**Plataforma de sessões de cinema e ingressos.** O organizador cria sessões a partir do
catálogo de filmes do TMDb, definindo sala, horário e preço por setor. O cliente navega
pelas sessões em cartaz, escolhe a poltrona no mapa da sala, paga de forma simulada e recebe
um ingresso com código em QR — que pode compartilhar por link. Na entrada, a portaria lê o
QR pela câmera e valida.

| | |
|---|---|
| **Repositório** | github.com/MinuaxY/desafio-verzel-ingressos |
| **Aplicação** | desafio-verzel-ingressos.vercel.app |
| **API** | verzel-ingressos-api.onrender.com/docs |
| **Commits** | 29 |
| **Testes** | 364 — 242 no back, 122 no front |
| **Decisões documentadas** | 33 |
| **Migrations** | 8 |

## Stack

| Camada | Escolha |
|---|---|
| Front | React 19 + Vite + TypeScript, CSS próprio |
| Back | Python + FastAPI, camadas router → service → repository |
| Banco | PostgreSQL 16 |
| Catálogo | TMDb, atrás de contrato trocável |
| Publicação | Vercel (front) + Render (API e banco) |

---

## Requisitos obrigatórios — todos atendidos

### Front-end
- ✅ Navegação e busca pelas sessões publicadas, com data, local e preço
- ✅ Criação e gerenciamento de sessões pelo organizador
- ✅ Reserva com seleção de lugar em mapa de assentos
- ✅ Pagamento simulado, com confirmação **e** recusa
- ✅ "Meus ingressos", com o ingresso e o QR
- ✅ Tela de portaria com os quatro retornos: válido, inválido, já utilizado, sessão errada
- ✅ Leitura do QR pela câmera, com digitação manual como alternativa

### Back-end
- ✅ Gestão das chamadas ao TMDb, com cache e provedor trocável
- ✅ Autenticação com três papéis: Organizador, Cliente, Portaria
- ✅ Armazenamento de sessões, reservas e ingressos
- ✅ Garantia de que o mesmo lugar não seja vendido duas vezes
- ✅ QR não-forjável, com assinatura HMAC
- ✅ Compartilhamento por link
- ✅ Validação sem permitir reuso
- ✅ Cobrança simulada, sem transação real

### Não funcionais
- ✅ README detalhado, testado em clone limpo
- ✅ Seed com organizador, dois clientes, portaria e sessões publicadas
- ✅ Deploy publicado (+1 ponto)

---

## Opcionais entregues

- ✅ Busca e filtro de sessões
- ✅ Painel do organizador
- ✅ Cancelamento com devolução ao estoque
- ✅ Mapa de assentos
- ✅ Docker Compose completo
- ✅ Testes (364)
- ✅ Aplicação publicada

## Feito por iniciativa, sem estar no enunciado

- **Acessibilidade nas poltronas** — quatro naturezas gravadas no banco, marcadas no mapa
  sem depender de cor. Nasceu de uma pergunta, não do PDF. Ver [Decisões técnicas](decisoes.md), D16.
- **Classificação indicativa** vinda do catálogo, com as cores do sistema brasileiro (D21)
- **Áudio e formato de exibição** por sessão — dublado/legendado, 2D/3D (D21)
- **Corredores na planta da sala**, configuráveis por setor (D25)
- **Landing pública** com prévia do cartaz (D22)
- **Numeração contínua de fileiras** na sala inteira (D23)

## Depois da entrega — 22 e 23/08

O prazo era 23/08 e a entrega saiu em 22/08. O tempo que sobrou virou isto:

**Gestão da programação** (D27–D29)
- Repetir a sessão em vários dias, por calendário e não por regra de recorrência
- Editar e remover salas e sessões, com as travas que cada estado exige
- Filtro por dia na vitrine, com dia vazio desabilitado em vez de clicável

**Cancelamento, que estava quebrado** (D30–D31)
- Cancelar uma sessão não invalidava os ingressos dela: o QR passava na portaria de uma
  sessão cancelada. Provado com o fluxo real antes de corrigir.
- Cancelar passou a exigir sessão vazia, com um passo separado para desfazer os pedidos
- O pedido registra **quem** cancelou, senão o cliente acharia que a desistência foi dele
- Sessão cancelada deixou de ocupar o horário da sala, que ficava preso para sempre

**Revisão de código** (D33) — três defeitos, achados sondando caminhos de borda
- Preço zero era aceito pela API: o cliente reservava e nunca conseguia pagar
- Uma rota-andaime que prometia a própria remoção no docstring e tinha ficado
- A portaria perdia a sessão da lista no instante em que ela começava

**Volume na vitrine** — o seed criava 4 sessões numa sala, o que não exercita paginação,
filtro nem busca. Passou a criar três salas de geometrias diferentes e dez dias de
programação: cerca de 90 sessões.

---

## Fora de escopo — decisão nossa, documentada no README

Validação de elegibilidade para assento acessível · meia-entrada · testes de front para as
páginas de checkout, portaria e painel do organizador (verificadas manualmente)

---

## Definition of Done — como foi aplicada

- Funciona ponta a ponta pelo navegador, não só no Swagger ✅
- Testes cobrindo a regra, não só o caminho feliz ✅
- Erro previsto tem tratamento e mensagem clara ✅
- Commit com mensagem descritiva empurrado no mesmo dia ✅
- Decisão relevante registrada em [Decisões técnicas](decisoes.md) ✅
