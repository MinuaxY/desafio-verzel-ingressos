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

## Onde paramos — 30/08, fim do dia

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
