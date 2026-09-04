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

---

## Pós-devolutiva — 1.1, a fronteira de confiança do cadastro

A Verzel não aprovou o projeto e mandou uma devolutiva detalhada. O ponto mais grave: o
cadastro público aceitava `role` e o gravava como veio — dava para pedir ORGANIZER e receber o
painel, ou GATE e receber a portaria.

Fui verificar antes de corrigir, como no cancelamento:

```
cadastro pedindo ORGANIZER -> 201, papel concedido: ORGANIZER
   painel do organizador: 200 · cria sala: 201
cadastro pedindo GATE -> 201 · acessa a portaria: 200
```

O que mais me chamou atenção: **não era descuido, era a premissa**. A tela perguntava "Como
você vai usar" e oferecia Cliente ou Organizador, como se papel fosse preferência. Num sistema
de bilheteria não é — cliente é autoatendimento, os outros dois são concedidos.

A suíte inteira dependia do defeito: todo teste registrava com papel explícito. Virou um helper
único no conftest, e o token continua vindo do login normal.

Também apareceu um problema que a devolutiva não citou e a correção deixou à vista: a portaria
valida ingresso de qualquer organizador, porque um usuário GATE não pertence a cinema nenhum.
Ficou anotado, fora do escopo desta etapa.

### Decisão tomada
D34.

---

## Pós-devolutiva — 1.2, a invariante que morava só no serviço

`SessionSectorPrice` apontava para `sessions.id` e `sectors.id` de forma independente. Nada no
banco impedia gravar o preço de um setor de outra sala — só o serviço conferia.

A solução foi a clássica de modelagem relacional, e é bonita de ver funcionando: **duas chaves
estrangeiras compostas que compartilham a coluna `room_id`**. Uma exige que a sessão esteja
naquela sala, a outra exige o mesmo do setor; sendo a mesma coluna, as duas falam da mesma
sala. A regra sai do Python e vira um estado que o banco não consegue representar.

O preço foi uma coluna derivável a mais na tabela. É a troca que a técnica pede: é justamente o
compartilhamento dela que prova a regra.

**Nenhum teste existente precisou mudar** — que era o resultado esperado, porque a regra já
valia, só não estava garantida. Os cinco novos escrevem direto no banco, por baixo do serviço,
já que é esse o caminho que a checagem em Python nunca cobriu.

Puxei o item 1.4 para esta migration: o `CHECK` do preço subiu de `>= 0` para `>= 1`. Mesma
tabela, mesma linha — separar seria uma segunda migration para mudar a mesma coisa.

Também ficou decidido o idioma dos identificadores: **inglês**. A varredura é a próxima etapa;
o código novo já nasce assim.

### Decisões tomadas
D35 e D36.

---

## Onde paramos — 27/08, fim do dia

Bloco 1 do ciclo pós-devolutiva **quase fechado**: 1.1, 1.2 e 1.4 entregues. Falta a 1.3.

**A próxima etapa é a 1.3 — conflito de agenda por intervalo.** Hoje `exists_at` compara
`starts_at ==`, então duas sessões de duas horas na mesma sala, às 20:00 e às 20:01, não
colidem. O caminho já levantado:

- Usar `movie_runtime_minutes`, que já existe no model, mais uma folga de limpeza da sala
- `EXCLUDE USING gist (room_id WITH =, tstzrange(...) WITH &&)`, que exige a extensão `btree_gist`
- Cuidado com a D31: sessão cancelada não pode entrar na exclusão, então a constraint precisa
  do mesmo `WHERE status <> 'CANCELLED'` do índice de horário
- `movie_runtime_minutes` é anulável — decidir a duração presumida quando o catálogo não informa
- Diferente da 1.2, **esta vai quebrar testes**: há vários criando sessões em horários próximos
  na mesma sala

Depois dela vem o bloco 2, que é a varredura de idioma (2.1, inglês, decidido na D36) mais o
enxugamento de comentário (2.2). Combinamos fazer os dois juntos, porque tocam nos mesmos
arquivos e separá-los dobraria o trabalho.

**Também na fila, fora do backlog original:** a portaria valida ingresso de qualquer
organizador, porque um usuário GATE não pertence a cinema nenhum. Apareceu durante a D34.

---

## Pós-devolutiva — 1.3, a sala reservada por intervalo

Fecha o bloco 1. A trava de agenda comparava só igualdade de horário: duas sessões de duas horas
às 20:00 e às 20:01 na mesma sala passavam sem violar nada.

O caminho previsto — `EXCLUDE USING gist` — funcionou, mas com uma surpresa no meio. Tentei
calcular o intervalo na própria expressão do índice e o Postgres recusou: **`timestamptz +
interval` é estável, não imutável**, e índice exige imutável. Coluna gerada falha igual. Testei
as duas hipóteses no banco antes de escolher, em vez de descobrir na migration.

Duas coisas que só apareceram implementando:

**A migration precisou resolver 27 pares sobrepostos** nos dados existentes. Cancelar um de cada
par, preferindo manter quem já vendeu ingresso — um dos pares tinha venda, e a sessão
sobreviveu. Cancelar em vez de apagar porque cancelada não ocupa (D31) e o registro fica.

**O seed produzia a própria sobreposição.** A grade fixa tinha intervalos de 150 a 180 minutos e
o filme mais longo ocupa 192. Reescrevi a programação para empilhar pela duração real de cada
filme, arredondando para o próximo quarto de hora. Ficou mais realista do que a grade fixa era.

Menos quebra do que eu previa: dos 254 testes, só os 3 de concorrência falharam, porque montam a
sessão direto sem passar pelo serviço.

**Um teste do front quebrou sem eu ter tocado nele.** `/1 de setembro/` casa também com "11 de
setembro", e a barra mostra duas semanas — dependendo do dia em que a suíte roda, os dois
aparecem juntos e a busca falha por ambiguidade. Estava latente desde que o teste foi escrito, e
hoje calhou de ser 30/08. Mesma armadilha de `Poltrona A1` casando com `A10`, que já tinha
acontecido antes: **regex sem âncora em rótulo que contém número**.

### Decisão tomada
D37.

---

## Pós-devolutiva — 2.1 e 2.2, idioma e comentário

Bloco 2 fechado. As duas etapas juntas porque tocam nos mesmos arquivos.

**A primeira ferramenta de renomeação teve de ser jogada fora.** Usava expressão regular com
limite de palavra e trocou dentro de strings: o CLI virou `create-organizador` e docstrings em
português ganharam verbos em inglês no meio da frase — *"cancel exige resolver com quem
comprou"*. Revertei tudo e refiz com o tokenizador do Python, trocando só tokens `NAME` por
posição. O módulo tem um caso de prova mostrando que string, comentário e número passam
intactos.

**O caminho inverso também mordeu.** `@pytest.mark.parametrize` nomeia o argumento por *string*,
e o `label()` do SQLAlchemy também. Como as strings ficaram intactas — corretamente —, oito
decoradores e um label quebraram e precisaram ser alinhados a mão. Foi o único jeito de
descobrir: rodando a suíte.

**Medi antes de decidir sobre o front, e a medição mudou a decisão.** Ia renomear os 31
arquivos, mas a crítica era sobre alternar idiomas *dentro da mesma unidade*, e no front isso
não acontece: 24 declarações portuguesas, 1 inglesa, zero arquivos misturando. O back-end é que
misturava. Renomear o front seria um refactor grande, sem tokenizador de TypeScript, para
corrigir um problema que não existe lá.

**No comentário, parei antes do número.** `order_service.py` foi de 18% para 13% e `session.py`
de 38% para 31%. Podia ter ido mais fundo, mas o que restou responde por que a coluna é
materializada, por que o `primaryjoin` é explícito, por que a duração presumida existe — nada
disso se lê no código. Cortar a partir daí seria apagar informação para melhorar a métrica.

### Decisões tomadas
D36 (ampliada) e D38.

---

## Onde paramos — 30/08, madrugada

**Blocos 1 e 2 do ciclo pós-devolutiva estão fechados.** Tudo o que a Verzel apontou como
prioridade — escalada de privilégio, invariantes no banco, padronização de vocabulário e
excesso de comentário — foi endereçado, em D34 a D38.

### A próxima etapa é o bloco 3, o front-end

É o maior, e a devolutiva disse ser o de maior ganho de percepção: *"o maior ganho viria de
aproximar o frontend do nível de cuidado do backend"*.

**3.1 — rodada de produto.** Revisar responsividade, espaçamentos, estados de carregamento e
erro, feedback após ação, consistência dos formulários e comportamento das páginas completas.

**3.2 — testes E2E** de checkout, portaria e painel do organizador. Playwright seria o caminho;
hoje essas três páginas só foram verificadas manualmente no navegador, o que está declarado nas
limitações do README.

### O que já está levantado para o bloco 3

- **`occupies_until` não é exposto na API.** A coluna existe desde a D37 e a tela poderia usá-la
  para mostrar "termina às 22:23" na sessão — é informação que o cliente quer e que hoje o front
  não tem como calcular sozinho.
- **A portaria tem uma lista de sessões do turno** (`GET /gate/sessions`, D33) que a tela usa,
  mas o seletor não mostra qual está em andamento agora. Detalhe de produto barato.
- **O idioma do front fica em português**, decidido e medido na D36 — não é pendência.

### Fora do backlog original, ainda em aberto

- **A portaria valida ingresso de qualquer organizador.** Um usuário GATE não pertence a cinema
  nenhum. Apareceu durante a D34 e é modelagem nova.
- **`test_melhorias.py` tem 78 testes e virou saco de gatos:** começou nas melhorias de gestão
  (D26–D29) e recebeu cancelamento, defeitos da revisão, invariante de preço e sobreposição de
  agenda. Dividir por assunto é baixo risco e melhora a leitura do repositório.

### Para retomar o ambiente

O Docker Desktop precisa estar rodando antes de qualquer coisa — a suíte usa Postgres de
verdade, e sem ele os 264 testes falham todos com erro de conexão, o que já me confundiu uma
vez. `docker compose up -d db`, esperar o `healthy`, e então `pytest`.

---

## Pós-devolutiva — 3.1, o front no celular

Comecei a rodada de produto pelo que dava para **medir**, não pelo que dava para opinar: abri o
ambiente publicado num viewport de 375px e anotei o que estava quebrado, com número.

### Três defeitos, todos invisíveis no desktop

**O cabeçalho transbordava 18px.** "Criar conta" ficava cortado — e, porque o transbordo é do
documento, a página inteira rolava de lado em **todas** as telas, não só no celular. Uma linha
de `flex-wrap: wrap` com `row-gap` abaixo de 40rem resolveu.

**O mapa da sala IMAX aparecia cortado dos dois lados.** Das 14 poltronas da fileira, apareciam
a 4 até a 11: faltavam três de cada lado, sem as letras das fileiras, com uma barra de rolagem
fininha como única pista de que havia mais coisa ali. A causa é uma armadilha de flexbox:
`align-items: center` **junto com** `overflow-x: auto`. Conteúdo mais largo que o contêiner
transborda para os dois lados, e o lado esquerdo fica inalcançável porque `scrollLeft` não
assume valor negativo — não existe rolagem para trás do zero.

A correção foi separar as duas responsabilidades em dois elementos: o de fora (`.setor__grade`)
rola, o trilho de dentro (`.setor__trilho`) centraliza com `width: fit-content` e
`margin-inline: auto`. Aproveitei para colocar sombras de rolagem só com CSS, usando
`background-attachment: local` e `scroll` — a sombra aparece no lado onde ainda há conteúdo
escondido, sem uma linha de JavaScript.

**A landing engolia a falha da API.** `Inicio.tsx` tinha um `.catch` que zerava o estado: se a
requisição falhasse, a seção de prévia sumia inteira — sem carregamento, sem erro, sem
explicação. É justamente o cenário mais provável em produção, porque o plano gratuito do Render
hiberna e a primeira visita paga até um minuto de espera. Passou a ter três desfechos
declarados, com quatro testes novos que trancam cada um.

### O achado mais desconfortável do dia

**Os 22 testes do mapa passaram sem uma linha de alteração.** Não porque o mapa estava certo,
mas porque jsdom não tem layout: `getBoundingClientRect` devolve zeros e não existe transbordo
para medir. A suíte de 126 testes de front não pegaria **nenhum** dos três defeitos de hoje.

Isso deixou de ser argumento teórico a favor da 3.2 e virou evidência. Subi a prioridade dela.

### Onde eu tinha exagerado

Citei os 44×44 da WCAG como requisito para a poltrona. São do nível **AAA** (critério 2.5.5). O
mínimo **AA** é o 2.5.8, de 24×24, que os 32px já cumpriam. Mantive os 40px, mas só sob
`pointer: coarse`, e pelo motivo certo: conforto no dedo, não conformidade. O item continua
válido; o que muda é a prioridade dele.

### As medidas, antes e depois

| | antes | depois |
|---|---|---|
| transbordo da página | 18px | 0 |
| rolagem inicial do mapa | travada à direita | `scrollLeft` 0, começa na poltrona 1 |
| poltronas visíveis | 4 a 11, de 14 | a fileira inteira, com as letras |
| poltrona no dedo | 32px | 40px |
| desktop em 750px | — | centralizado, sem rolagem, poltrona 32px |

### Decisões tomadas
D39.

---

## Onde paramos — 30/08, noite

**A 3.1 está pela metade, e a metade que saiu é a dos defeitos.** O que sobrou é a parte
estética, que faz sentido vir depois mesmo.

### O que falta na 3.1

- **Estado de carregamento em `NovaSessao`, `Portaria`, `Entrar` e `CriarConta`.** O caminho
  está aberto: `Inicio.tsx` estabeleceu o padrão de três estados
  (`"carregando" | "pronto" | "erro"`) e `Inicio.test.tsx` estabeleceu como testá-lo, com uma
  promessa controlada que só resolve quando o teste manda — é o que dá tempo de observar o
  carregamento antes do desfecho.
- **Responsividade além do que já foi medido.** São 5 media queries em 1.356 linhas de CSS. Só
  o cabeçalho e o mapa foram exercitados em 375px; o resto do sistema nunca foi.
- **Espaçamento, consistência dos formulários e feedback depois da ação.**

### A 3.2 subiu de prioridade

Só **3 das 13 páginas** têm teste — `EmCartaz`, `Pedido` e agora `Inicio`. Checkout, portaria e
painel do organizador nunca foram exercitados por automação, só à mão no navegador. E o dia de
hoje mostrou que existe uma classe inteira de defeito que **só aparece com layout de verdade**.
Playwright continua sendo o caminho.

### Continua em aberto, fora do backlog original

- A portaria valida ingresso de qualquer organizador — um usuário GATE não pertence a cinema
  nenhum. Apareceu na D34 e é modelagem nova.
- `occupies_until` existe no banco desde a D37 e não é exposto na API; a tela poderia mostrar
  quando a sessão termina.
- `test_melhorias.py` tem 78 testes de cinco assuntos diferentes.
- O seletor da portaria não indica qual sessão está em andamento agora.

### Contagem atual

**390 testes: 264 no back, 126 no front.** Os números que estavam anotados aqui (371, 249 e 122)
eram de antes dos blocos 1.2 e 1.3 e ficaram para trás.

### Para retomar o ambiente

Docker Desktop primeiro, sempre — sem ele os 264 testes de back falham todos com erro de
conexão, e isso já me confundiu uma vez. `docker compose up -d db`, esperar o `healthy`, e então
`pytest`. Para mexer no front com dados reais: `uvicorn` na 8000 e `npm run dev` na 5173.

---

## Pós-devolutiva — 3.1, o que a tela afirma sem saber

**O item do quadro estava errado, e conferir foi o que mostrou.** Estava escrito "sem estado de
carregamento em NovaSessao, Portaria, Entrar e CriarConta". Fui olhar as quatro antes de mexer:
as quatro **já tinham** feedback de envio — `Entrando…`, `Criando…`, `Salvando…`, `Verificando…`,
todas com o botão desabilitado enquanto a requisição corre. Se eu tivesse executado a tarefa como
estava escrita, teria "corrigido" o que já funcionava e passado ao largo do defeito.

O que faltava era o **carregamento inicial**. E ali o problema não era ausência de aviso: era a
tela **afirmar com confiança uma coisa que ainda não sabia**.

### A sala que o organizador não tinha

`NovaSessao` decidia o que mostrar por `salas.length === 0` — que também é o valor inicial, antes
de `/rooms` responder. Enquanto a lista não chegava, e **para sempre** se ela falhasse, a tela
dizia *"Você ainda não tem salas"* com um botão convidando a cadastrar a primeira.

Para um organizador que tem três salas, isso não é uma tela sem polimento: é uma afirmação falsa
que empurra para o erro seguinte, criar uma sala duplicada.

### A porta que ficava permissiva em silêncio

`Portaria` tinha `.catch(() => {})`. Com `/gate/sessions` fora, o seletor continuava lá, com cara
de funcionando, oferecendo só *"Qualquer sessão"* — que é o modo permissivo. A conferência de
"ingresso de outra sessão" da D33 **se desarmava sozinha**, e a pessoa na porta não tinha como
saber.

Esse é o pior dos dois, e não por pouco. Não é uma tela feia: é uma proteção que se desliga sem
avisar, no aparelho e no momento em que ninguém vai investigar.

### O que foi feito

Três estados explícitos nas duas telas — `carregando | pronto | erro` —, o mesmo desenho que a
D39 tinha estabelecido na landing. Enquanto carrega, o seletor da portaria fica desabilitado,
porque não dá para escolher de uma lista que não chegou. No erro, a mensagem diz **o que se
perdeu**, e não só que algo falhou: *"um ingresso de outra sala vai ser aceito"*. Com botão de
tentar de novo, e sem travar a validação — a portaria existe para deixar gente entrar.

### Como conferi, depois do que aprendi ontem

Escrevi dez testes e **rodei os dois arquivos contra a versão antiga antes de aceitar que
funcionam**: 4 de 5 falham na portaria, 3 de 5 na nova sessão. Os que passam nas duas versões são
os caminhos felizes, que nunca estiveram quebrados — e é bom que passem nos dois.

Depois fui ao navegador em 375px e derrubei **um endpoint de cada vez, com o resto no ar**. Essa é
a falha parcial real: o servidor inteiro fora é o caso fácil, e não é o que estava escondido. O
erro apareceu, o "tentar de novo" recuperou — 26 opções de volta, seletor reativado — e o
transbordo de página ficou em 0.

### Um detalhe do lint que valeu obedecer

Meus dois avisos novos eram `set-state-in-effect`, e eram justos: eu chamava `setEstado("carregando")`
dentro do efeito, onde o estado inicial já era esse. A própria regra dizia o que fazer — atualizar
a partir do evento que causa a mudança. Movi a transição para o clique do "tentar de novo", que é
onde ela pertence. Voltou aos 4 avisos pré-existentes.

### Achado que ficou parado de propósito

`/gate/sessions` devolve **26 sessões de três dias diferentes**. O endpoint se chama "sessões do
turno" e não filtra por turno. No celular da porta, rolar 26 opções para achar a certa é pior do
que não ter seletor. É escopo de back-end e não entrou nesta etapa; foi para o quadro.

### Decisões tomadas
D40.

---

## Onde paramos — 31/08, fim do dia

**A 3.1 tem agora todos os defeitos funcionais corrigidos.** O que resta é a parte estética, que
é subjetiva e cabe decidir com calma.

### O que falta na 3.1

- **Responsividade além do que já foi medido.** São 5 media queries em 1.356 linhas de CSS, e só
  o cabeçalho e o mapa de assentos foram exercitados em 375px. As outras onze telas nunca foram.
- **Espaçamento, consistência dos formulários e feedback depois da ação.**

### A 3.2 continua sendo o maior ganho

Passamos de 3 para **5 das 13 páginas com teste** — entraram `Portaria` e `NovaSessao`. Ainda
faltam checkout, painel do organizador, salas, sessão, meus ingressos e as demais. E continua
valendo o que ontem mostrou: existe uma classe de defeito que **só aparece com layout de
verdade**, e nenhum teste em jsdom vai encontrá-la. Playwright.

### Em aberto, fora do backlog original

- A portaria valida ingresso de qualquer organizador — um usuário GATE não pertence a cinema
  nenhum. Apareceu na D34, é modelagem nova.
- `/gate/sessions` devolvendo três dias de sessões.
- O seletor da portaria não indica qual sessão está em andamento agora.
- `occupies_until` existe no banco desde a D37 e não é exposto na API.
- `test_melhorias.py` tem 78 testes de cinco assuntos.

### Contagem atual

**400 testes: 264 no back, 136 no front.** 40 decisões, 19 aprendizados.

### Para retomar o ambiente

Docker Desktop primeiro, sempre. `docker compose up -d db`, esperar o `healthy`, e então
`pytest`. Para o front com dados reais: `uvicorn app.main:app --port 8000` na pasta `api`, e
`npm run dev` na `web`. O `.claude/launch.json` que uso para o preview está no `.gitignore` — é
config de ferramenta, não faz parte do projeto que o avaliador clona.

---

## Pós-devolutiva — 3.2, o dia em que a rede de proteção passou a existir

**Começou com uma pergunta do Paulo:** existe algum conector ou plugin que ajude no front? Fui
conferir em vez de opinar — registro de conectores vazio, nenhuma skill a sugerir. A resposta
honesta era que a ferramenta que mais importava eu já tinha, o navegador do painel, e que o que
faltava **não era conector nenhum: era uma dependência de desenvolvimento.**

A distinção decidiu a etapa. O navegador que eu controlo existe enquanto a sessão existe; um
teste em `web/e2e/` fica versionado, roda com `npm run e2e`, entra em CI e qualquer avaliador que
clonar o repositório executa. Para um projeto julgado por processo, medição que ninguém consegue
repetir vale pouco.

### Três arquivos, e cada um conferido ao contrário

**`compra.spec.ts`** — o fluxo central, que era o único item das limitações do README declarado
como "verificado manualmente": entrar, escolher poltrona no mapa, pagar, chegar ao QR. Um segundo
teste compra e volta à sala para ver aquela poltrona ocupada e desabilitada — a face visível, na
tela, da garantia que o índice único parcial dá no banco.

**`geometria.spec.ts`** — as medições da D39 viradas teste. Revertendo componente e CSS daquela
correção, **quatro dos seis ficam vermelhos**. É assim que se sabe que reprovam o defeito que os
motivou.

**`portaria.spec.ts`** — os quatro vereditos, com o ingresso **comprado pela tela** e o código
lido de onde o cliente o leria. Um código injetado no banco provaria só a portaria; assim o teste
cobre a costura inteira. Ficam em série numa aba só, porque contam uma história em ordem: o
ingresso entra, e por ter entrado não entra de novo. Conferido desligando o envio da sessão da
porta — o ingresso de outra sala passou a receber "Pode entrar".

**`gestao.spec.ts`** — o ciclo do organizador, ponta a ponta, mais repetir em vários dias e a
trava do preço por setor.

### O aparelho largo demais

A primeira configuração usava o Pixel 7, de 412px. **Com ele, o cabeçalho quebrado da D39 passava
no teste** — sobra folga demais para o defeito aparecer. Fixei o projeto de celular em 375px, que
é onde os defeitos foram encontrados. Testar no aparelho largo é testar onde não dói.

### O comando que não checava nada

Ao fazer a checagem de tipos alcançar a pasta nova, descobri que **`npx tsc --noEmit` não
verificava coisa alguma** neste repositório: o `tsconfig.json` da raiz tem `files: []` e só
referências, então o comando termina com sucesso sem abrir arquivo nenhum.

Era o comando que eu vinha usando para dizer "tipos limpos". Por causa dele, um erro de tipo entrou
no repositório na D40 e **deixou o `npm run build` quebrado por algumas horas**. Corrigido, e o
comando certo — `tsc -b` — virou o script `npm run typecheck`, para o certo ser o óbvio.

### O teste que passou com a trava quebrada

O da trava de preço deixava **todos** os preços em branco. Troquei o `every` por `some` na regra —
de "todo setor tem preço" para "algum setor tem preço" — e ele continuou verde: com zero
preenchidos, as duas regras recusam igual. Preencher **um** preço e deixar o resto em branco é o
único estado em que discordam, e ali ficou vermelho na hora. Virou o aprendizado 20.

### Decisões tomadas
D41.

---

## O defeito que o Paulo achou passeando pelo sistema

**Abri o app para ele ver, e ele voltou dizendo que "Cancelar pedido" não fazia nada.**

Reproduzi e medi: o botão chamava `window.confirm`, e ali ele devolvia `false` em **zero
milissegundo**, sem nunca aparecer. Isolei antes de concluir — com o `confirm` respondido, o
cancelamento funcionava. A lógica estava certa; o diálogo é que falhava.

Podia ter parado em "é do painel de pré-visualização". Não parei, porque o `window.confirm` é
suprimido em silêncio em situações comuns demais para uma ação destrutiva depender dele: iframe de
outra origem, webview de aplicativo, e depois que o navegador oferece *"impedir esta página de
criar mais diálogos"* — e o painel do organizador dispara vários seguidos, que é exatamente o
padrão que provoca a oferta. Eram **cinco** pontos assim, todos destrutivos.

Houve um sinal que eu não li na hora: os testes E2E precisaram de `page.on("dialog", …)`. **Ter de
ensinar o robô a lidar com um diálogo que a aplicação não controla era o aviso** de que a
confirmação estava fora do alcance dela.

### O que isso custou de orgulho

Os testes de ponta a ponta que eu tinha acabado de escrever **passaram com o diálogo novo
posicionado no canto superior esquerdo da tela**. `toBeVisible()` era verdade, o botão era
clicável, o fluxo funcionava — e a aparência estava quebrada. Só apareceu porque olhei a captura.

A causa era o reset global `* { margin: 0 }` do próprio projeto, que anula o `margin: auto` com
que o navegador centraliza um `<dialog>` modal.

**Duas vezes no mesmo dia a mesma lição:** o dia começou provando que a suíte de unidade é cega
para geometria, e terminou descobrindo que a suíte nova é cega para aparência. Virou o
aprendizado 21.

### Decisões tomadas
D42.

---

## Onde paramos — 03/09, fim do dia

**O bloco 3 está com a 3.2 fechada e só a parte estética da 3.1 em aberto.**

### Contagem atual

**433 testes: 264 no back, 136 no front e 33 de ponta a ponta**, estes últimos em dois projetos —
desktop e celular a 375px. 42 decisões, 21 aprendizados.

### O que falta

- **A passada estética da 3.1:** responsividade das outras telas, espaçamento, consistência dos
  formulários e feedback depois da ação. Agora fica mais seguro de fazer — mexer no CSS com 33
  testes de layout e fluxo por trás é outra coisa.
- **A portaria pertencer a um organizador.** Um usuário GATE não pertence a cinema nenhum.
  Apareceu na D34 e continua sendo a única pendência que é regra de negócio faltando, e não
  melhoria.
- `/gate/sessions` devolvendo 26 sessões de três dias; o seletor não indicar a sessão em
  andamento; `occupies_until` não exposto na API; `test_melhorias.py` com 78 testes de cinco
  assuntos.

### Para retomar o ambiente

Docker Desktop primeiro. `docker compose up -d db`, esperar o `healthy`. Depois `uvicorn
app.main:app --port 8000` na pasta `api` e `npm run dev` na `web`. Para os testes de ponta a
ponta, `npm run e2e` — o `globalSetup` confere a API e o cartaz antes de começar, e falha com o
comando exato a rodar se faltar alguma coisa.

**E o comando de tipos é `npm run typecheck`, não `npx tsc --noEmit`.** O segundo passa sempre.
