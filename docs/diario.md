<!-- Espelho de "Diário das Sprints", do vault de anotações do projeto (Obsidian).
     Versionado aqui porque o desafio pede os artefatos de processo junto do código. -->

# Diário das Sprints

O que de fato aconteceu, em ordem, incluindo o que deu errado.

> ✅ **Projeto entregue em 22/08**, um dia antes do prazo, e revisado até 23/08.
> As lições generalizáveis estão em [Aprendizados](aprendizados.md); as escolhas técnicas, em
> [Decisões técnicas](decisoes.md); o resultado, em [Product Backlog](backlog.md).

---

## Sprint 1 — 19 e 20/08 — Fundação e autenticação ✅

**Meta:** os três papéis entram no sistema e o organizador enxerga o catálogo externo.

Nada de tela bonita. O objetivo era **matar risco**: se a chave da API não saísse, ou se a
autorização por papel não funcionasse, todo o resto travava.

### Entregue

| | Tarefa | Prova |
|---|---|---|
| T0 | Chave da API externa | HTTP 200 no TMDb, títulos em pt-BR |
| T1 | Repositório público + estrutura | github.com/MinuaxY/desafio-verzel-ingressos |
| T2 | PostgreSQL + Alembic | container *healthy*, migrations versionadas |
| T3 | `User` com papel | enum nativo `user_role` no banco |
| T4 | repository / service / router | camadas separadas |
| T5 | Cadastro e login | JWT carregando o papel |
| T6 | Autorização por papel | 403 para papel errado, 401 sem token |
| T7 | Seed | 4 usuários, idempotente |
| T8 | Catálogo TMDb | provedor trocável, com cache |
| T9 | Shell React | rotas protegidas por papel |
| T10 | Identidade visual | "sala escura", CSS próprio |
| T11 | Testes | 26 passando |

### O que deu errado

**A chave da Ticketmaster nunca chegou.** O e-mail de ativação não veio, e o T0 travou o
projeto inteiro logo no primeiro dia. A saída foi migrar para o TMDb — que acabou
encaixando melhor no modelo, porque entrega só a obra e deixa data, local e preço como
criação do organizador. Ver [Decisões técnicas](decisoes.md), D3.

Isso virou característica do produto: o catálogo ficou atrás de um contrato com duas
implementações, e a aplicação continua funcionando sem chave nenhuma. Ver D8.

**Os testes estavam batendo na API de verdade.** Um teste do catálogo falhou e revelou que
`get_settings` tem `lru_cache` — trocar a variável de ambiente não surtia efeito. Depois da
correção, o tempo caiu de 7,5s para 3,8s. Só apareceu porque o teste era específico o
bastante para notar a diferença.

**`erasableSyntaxOnly` no Vite 8.** O `tsc --noEmit` passou e o `tsc -b` falhou: atalho de
propriedade no construtor não é mais permitido. Lição: validar com o build de verdade, não
com o atalho.

### Decisões tomadas
D1 a D10.

---

## Adiantamento — 20/08 — Back-end da Sprint 2 ✅

**Motivo:** trazer para cedo o que fica preso no banco. Tela é barata de refazer; schema
com dado já criado, não.

### Entregue
- Modelo de sala reutilizável com setores (D11)
- Preço por setor, definido na sessão (D12)
- Sessão guardando cópia dos dados do filme (D13)
- Centavos inteiros e horário com fuso (D14)
- Assento derivado da geometria, não pré-criado (D15)
- API de salas e de sessões, com vitrine pública
- Poltronas acessíveis no modelo (D16)
- Seed com sala de 88 lugares, 10 acessíveis, e 4 sessões publicadas
- **76 testes**

### O que deu errado

**Atualizar preços violava a constraint.** O SQLAlchemy inseria os novos antes de apagar os
antigos, e o índice único de (sessão, setor) recusava. Resolvido com `flush` no meio — e os
novos passaram a ser montados **antes** de mexer nos atuais, para que uma validação que
falha não deixe a sessão sem preço nenhum.

**O seed criava sessões de madrugada.** Somar horas sobre "agora" em UTC dava sessão às
três da manhã. Nenhum cinema exibe nesse horário, e é o primeiro dado que o avaliador vê.
Passou a usar horários reais no fuso de São Paulo.

**Acentos embaralhados no console.** O terminal do Windows usa cp1252. Como quem roda o
seed é quem está avaliando, a saída precisa sair legível.

### Ponto cego pego pelo Paulo

**Assentos para pessoas com deficiência e obesas não estavam no modelo.** A pergunta veio
no momento certo — ainda era barato. Se aparecesse na Sprint 4, seria migration sobre sala
e sessões já criadas. Ver D16.

### Decisões tomadas
D11 a D16.

---

## 21/08 — Dia sem trabalho

O dia passou em branco. Descoberto na manhã de 22/08, quando o relógio da máquina
desmentiu o planejamento: restavam dois dias, não três, com quatro frentes abertas.
O escopo foi mantido, e coube.

---

## Sprint 2 a 5 — 22/08 — Tudo o que faltava ✅

Um dia só, na ordem: back-end de compra e portaria, front inteiro, deploy, documentação,
landing e testes de front.

### Entregue
- Compra com assento marcado, pagamento simulado e ingresso com QR assinado
- Portaria com câmera, digitação manual e os quatro vereditos
- Front completo nos três papéis
- **Publicado**: front na Vercel, API e banco no Render
- README, documento de IA e as 25 decisões versionadas
- Landing pública, classificação indicativa e formato de exibição
- Mapa de sala com numeração contínua, corredores e a tela embaixo
- **254 testes**: 163 no back, 91 no front

### O que o deploy encontrou
Duas coisas que a máquina de desenvolvimento escondia: um pin de dependência para uma
versão que **não existe** — ninguém que clonasse o repositório conseguiria instalar — e o
seed duplicando sessões entre dias diferentes, com o README afirmando o contrário.

### O que os testes de front encontraram
Três erros meus nos próprios testes, e um no build: o `defineConfig` do Vite não conhece a
chave `test`, e o `tsc -b` reprovava. Sem rodar o build, o deploy teria quebrado.

### O que o Paulo pegou
O mapa de assentos não correspondia a uma sala — setores empilhados, cada um começando na
fileira A, duas fileiras "A" na mesma sala. E a poltrona ocupada, que precisou de quatro
tentativas até parar de ser abstração e virar a silhueta de quem está sentado.

### Conferência final
Clone limpo do GitHub, `docker compose up --build`, e o roteiro do README percorrido inteiro:
**12 verificações, todas passaram**. Nenhum segredo no repositório.

### Decisões tomadas
D17 a D25.

---

## 22/08, noite — Gestão da programação

Com a entrega feita e um dia de prazo sobrando, quatro melhorias anotadas durante os testes:
botão de cancelar na criação, editar e remover salas e sessões, repetir a sessão em vários
dias, e filtro por dia para o cliente.

A repetição virou uma decisão de produto: escolher os dias **um a um** num calendário, e não
declarar uma regra do tipo "toda sexta até tal data". Programação de cinema não é regular, e
uma regra que não cobre isso obriga a apagar depois o que ela criou a mais.

### Decisões tomadas
D26 a D29.

---

## 22/08, noite — O cancelamento estava quebrado

Uma pergunta do Paulo — *"qual a diferença do cancelado para o despublicar?"* — abriu o maior
defeito do projeto.

Fui verificar em vez de responder de cabeça, e montei o fluxo real: publiquei uma sessão,
comprei um ingresso, cancelei a sessão e levei o QR na portaria.

```
PORTARIA: VALID — Entrada liberada, Plateia, poltrona C6
```

Cancelar só mexia no campo `status` da sessão. Os ingressos continuavam válidos e a portaria
nunca olhava a sessão. Na prática, **a única diferença entre cancelar e despublicar era que
cancelar não podia ser desfeito** — irreversível e sem efeito nenhum.

O que veio depois foi tão instrutivo quanto. Minha primeira correção — cancelar invalidando os
ingressos em massa, com uma confirmação avisando quantos — chegou a ser implementada e o Paulo
mandou desfazer: o sistema não manda e-mail nem estorna, então o botão daria ao organizador a
sensação de ter resolvido algo que ele só apagou da própria tela. Cancelar passou a **exigir
sessão vazia**, com um passo separado e explícito para desfazer as compras.

Aí apareceu o efeito colateral: como cancelar não tem volta e a sessão cancelada continuava
ocupando o horário da sala, aquele horário ficava preso para sempre. O erro não era a falta de
um "descancelar" — era a checagem respondendo a pergunta errada. Ela perguntava "existe alguma
linha nessa sala nesse horário", quando a pergunta é "existe alguma sessão que **vai
acontecer**".

### Decisões tomadas
D30 a D32.

---

## 22/08, madrugada — Revisão de código

Pedido do Paulo: revisar, depurar, corrigir e dar volume à vitrine.

Rodei os linters, li o código e — o que rendeu — **sondei caminhos de borda contra a API** em
vez de só ler. Tudo que os testes já cobriam passou. Os três defeitos estavam fora da
cobertura:

1. **Sessão de graça travava o cliente.** A API aceitava preço zero, e o pagamento simulado
   recusa valor zero, corretamente. O cliente reservava a poltrona e nunca conseguia pagar. O
   detalhe que fecha o diagnóstico: a tela de criação já exigia preço maior que zero. **A API
   discordava da própria interface.**
2. **Uma rota-andaime** cujo docstring prometia que ela sairia "quando os endpoints reais
   passarem a exercer a mesma trava". Eles passaram, e ela ficou.
3. **A portaria perdia a sessão no instante em que ela começava**, porque lia a vitrine — que
   esconde o que já começou. Certo para quem compra, errado para quem está na porta, com o
   público ainda entrando.

E o volume: o seed criava quatro sessões numa sala. Quatro sessões não exercitam paginação,
filtro por dia nem busca — as três coisas que precisam ser vistas funcionando. Passou a criar
três salas de geometrias diferentes e dez dias de programação, com os treze filmes do catálogo.

### Decisões tomadas
D33.

---

## 23/08 — Fechamento

Revisão dos documentos antes do envio. O README afirmava que os artefatos de processo estavam
versionados em `docs/`, e só as decisões estavam — o backlog, este diário e o quadro viviam
apenas no Obsidian. As tabelas de teste do README também tinham ficado para trás: somavam 196
de 242 casos reais, e o registro de decisões ainda listava como "pendentes" duas escolhas
tomadas há dias.

Nada disso quebrava o sistema. Todas eram afirmações do projeto sobre si mesmo que tinham
deixado de ser verdade — que é o tipo de erro que só aparece quando alguém confere documento
contra código, um por um.
