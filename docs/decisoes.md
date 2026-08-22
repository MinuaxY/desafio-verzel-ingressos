# Decisões Técnicas

Registro das escolhas e do que foi descartado. Vai versionado no repositório em `docs/decisoes.md` — o desafio pede explicitamente para ver como o projeto foi conduzido.

---

## D1 — Back-end: Python + FastAPI

**Alternativas:** NestJS · Spring Boot
**Por quê:** velocidade de escrita em 5 dias e documentação OpenAPI automática — o avaliador abre `/docs` e navega pela API sem Postman. Spring Boot descartado pelo custo de cerimônia no prazo.
**Custo aceito:** duas linguagens no projeto, com troca de contexto entre back e front.

## D2 — Front-end: React + Vite

React é obrigatório pelo enunciado. Vite pelo build rápido e configuração mínima. Next.js descartado: com FastAPI no back, SSR e API routes não agregam e só somariam complexidade.

## D3 — Catálogo externo: TMDb *(revisada em 20/08)*

**Decisão original:** Ticketmaster Discovery.
**Por que mudou:** a Ticketmaster não liberou a chave — o e-mail de ativação nunca chegou. Com 5 dias, esperar por terceiro era risco alto demais.
**Por que TMDb é melhor, e não apenas o que sobrou:**
- Elimina uma redundância conceitual. Na Ticketmaster o evento já vem com data e local, e o organizador redefiniria os dois por cima. Com TMDb o catálogo entrega só a obra — título, sinopse, pôster — e **tudo que é evento passa a ser criação do organizador**, exatamente como o enunciado descreve.
- Pôsteres e backdrops em alta resolução, com sinopse já em `pt-BR`. Material visual real em vez de placeholder, o que sustenta o critério de interface do desafio.
- Integração mais simples: busca e detalhe, sem venues e classifications aninhados.

**Validada em 20/08** com chamada real a `/search/movie` — HTTP 200.

## D4 — Sessões de cinema com mapa de assentos *(revisada em 20/08)*

**Decisão original:** venda por pista/setor e quantidade, que fazia sentido para shows.
**Por que mudou:** o catálogo passou a ser de filmes, e cinema pede assento marcado. Vender sessão de cinema por quantidade seria incoerente com o domínio.
**Ganho colateral:** mapa de assentos está listado entre os opcionais que contam na avaliação, e simplifica a D5.
**Custo:** mais interface na Sprint 3. Mitigado por uma sala pequena — 8 fileiras × 12 poltronas, um grid clicável.

## D5 — Não vender o mesmo assento duas vezes *(simplificada pela D4)*

**Descartado:** ler disponibilidade, validar na aplicação e depois gravar — abre janela de corrida entre duas compras simultâneas.
**Escolhido:** **índice único em `(sessao_id, assento)`**. O banco recusa a segunda venda por definição, sem lock explícito e sem lógica de concorrência na aplicação. A violação de constraint é traduzida numa mensagem clara ao usuário.
**A validar na Sprint 3:** teste com requisições concorrentes disputando o mesmo assento.

## D6 — QR não-forjável

**Descartado:** QR contendo o ID do ingresso — qualquer pessoa geraria um código válido.
**Escolhido:** o QR carrega o identificador **mais uma assinatura criptográfica** gerada com segredo do servidor. A portaria verifica a assinatura *e* o estado do ingresso no banco. Sem o segredo não há como forjar.
**Detalhe:** o segredo do ingresso é separado do segredo do JWT. Comprometer a sessão de um usuário não deve permitir emitir ingressos.

## D7 — Identidade visual

*(a preencher — Sprint 1, T10)*

O desafio é explícito sobre fugir do visual genérico de projeto gerado por IA. Registrar aqui paleta, tipografia, referência adotada e o raciocínio.

## D8 — Catálogo atrás de um contrato de provedor

**Contexto:** a indisponibilidade da chave da Ticketmaster travou o início do projeto por depender de um terceiro.
**Escolhido:** o catálogo é consumido por meio de uma interface, com duas implementações trocáveis por variável de ambiente — `TmdbProvider`, que fala com a API real, e `FixtureProvider`, que serve dados locais.
**Por quê:** o desenvolvimento e os testes deixam de depender de rede, de chave e de rate limit; a aplicação continua demonstrável se a API externa cair no meio de uma avaliação; e a dependência externa fica isolada num único ponto do código.
**Custo:** uma camada de indireção a mais.

## D9 — bcrypt sem passlib

O ambiente roda Python 3.14, versão em que a combinação `passlib` + `bcrypt` é conhecida por quebrar. Uso direto da biblioteca `bcrypt`, que é o que o `passlib` faria por baixo, sem a camada intermediária.

## D10 — Vitrine pública e landing na raiz

**Contexto:** hoje `/` apenas redireciona para o login, e toda a aplicação vive atrás de
autenticação. A landing pretendida mostra cartazes das sessões em cartaz como prévia,
com Entrar e Criar conta no canto superior direito.

**Consequência que não é óbvia:** para exibir sessões a quem não tem conta, a listagem
precisa ser **pública**. Isso muda uma premissa da Sprint 2, que nasceria restrita ao
cliente autenticado.

**Escolhido:** a vitrine de sessões publicadas é aberta desde a Sprint 2. Autenticação
passa a ser exigida no momento da **reserva**, não da navegação.

**Por quê:**
- É como o domínio real funciona. Ingresso.com, Sympla e Eventim mostram o catálogo a
  qualquer visitante e só pedem conta na hora de comprar. Exigir login para *olhar* é
  atrito sem contrapartida.
- O enunciado pede "navegação e busca pelos eventos publicados" sem condicionar a estar
  autenticado.
- Decidir agora custa nada; decidir na Sprint 5 significaria abrir endpoints já escritos
  fechados, mexer em testes e refazer a navegação do front.

**Atenção:** o catálogo TMDb continua restrito ao organizador (D8). Público é o que já
foi publicado como sessão, não a busca no fornecedor externo — a chave da API externa
não deve ser gasta por tráfego anônimo.

## D11 — Sala reutilizável, com setores

**Alternativa:** layout definido em cada sessão (fileiras e poltronas digitadas na criação).
**Escolhido:** a sala é cadastrada uma vez, com seus setores, e reaproveitada por quantas
sessões o organizador quiser.
**Por quê:** com o layout na sessão, cada nova sessão exigiria redigitar a geometria — e,
pior, duas sessões da mesma sala poderiam divergir por erro de digitação, sem nada no
sistema impedindo. O custo é uma tabela e um CRUD a mais; a alternativa cobraria esse
preço em dado inconsistente.
**Consequência na interface:** o fluxo de criar sessão precisa de um atalho para cadastrar
sala nova, para não obrigar o organizador a sair do caminho quando a sala não existe ainda.

## D12 — Preço por setor, definido na sessão

**Escolhido:** o setor pertence à **sala** e descreve geometria — onde ficam as poltronas
VIP. O preço pertence à **sessão**.
**Por quê:** a mesma sala tem preço de terça e preço de sábado. Guardar o valor no setor
obrigaria a duplicar salas só para variar preço.
**Trava associada:** publicar exige preço para **todos** os setores da sala. Sem isso a
sessão iria ao ar com um setor sem valor, e o erro só apareceria quando alguém tentasse
comprar aquela poltrona.

## D13 — A sessão guarda uma cópia dos dados do filme

**Descartado:** guardar só o id do TMDb e consultar a API a cada exibição.
**Escolhido:** título, sinopse, pôster, duração e ano são copiados para a sessão no momento
da criação, ao lado do id de origem.
**Por quê:** ingresso é documento, não consulta ao vivo. Se o TMDb sair do ar, mudar o
título traduzido ou trocar o pôster, o ingresso que alguém comprou precisa continuar
mostrando o que foi vendido. Como efeito colateral, a vitrine não depende de rede externa
para renderizar.
**Custo aceito:** dado duplicado que não acompanha correções feitas no catálogo. É o
comportamento desejado — o que foi vendido não deve mudar sozinho.

## D14 — Dinheiro em centavos inteiros, tempo sempre com fuso

**Dinheiro:** valores trafegam e são gravados como **centavos inteiros**, nunca float.
`0.1 + 0.2` não dá `0.3` em ponto flutuante, e esse erro aparece no centavo depois que já
existe ingresso emitido — quando corrigir significa mexer em dado vendido.

**Tempo:** todo horário é gravado com fuso. Sessão de cinema é hora local, e o horário sem
fuso é ambíguo. A API **recusa** horário sem fuso na entrada, em vez de assumir um e gravar
errado.

Ambas são baratas agora e caras depois: mudar exige reescrever dados existentes.

## D15 — Assento derivado da geometria, não pré-criado

**Descartado:** gerar uma linha por poltrona quando a sessão é criada — 88 registros por
sessão que só interessam se alguém comprar.
**Escolhido:** o código da poltrona (A1, A2, B1…) é derivado das fileiras e poltronas do
setor. O assento vira registro no banco no momento da compra.
**Consequência para a Sprint 3:** a garantia de não vender duas vezes será um **índice único
parcial** em (sessão, setor, poltrona), ignorando pedidos recusados. O banco recusa a venda
dupla por definição, e um pagamento negado libera a poltrona sem trabalho extra.

## D16 — Poltronas acessíveis fazem parte do modelo

**Origem:** pergunta do Paulo em 20/08 — "considerou assentos especiais para deficientes e
obesos, ou isso fica para o front?". Não tinha considerado; era ponto cego.

**Descartado:** tratar como assunto de interface, desenhando um ícone diferente no mapa.
Isso seria decoração: sem registro no banco, o sistema não teria como saber que aquele
lugar é reservado a quem precisa dele, e nenhuma regra futura poderia se apoiar nisso.

**Escolhido:** a poltrona acessível é característica da **sala**, marcada por código no
cadastro do setor. Quatro naturezas: espaço para cadeira de rodas, poltrona de
acompanhante, assento largo e lugar de mobilidade reduzida.

**Por quê:** salas de espetáculo no Brasil têm exigência legal de lugares acessíveis
(Lei 10.098 e NBR 9050). Um sistema de cinema que ignora isso está incompleto como
produto, não apenas como código. O enunciado também convida explicitamente a incluir o
que melhoraria a proposta, desde que explicado.

**Só a exceção vira registro:** poltrona comum não gera linha. A sala de 88 lugares do
seed guarda 10 registros, não 88.

**Trava:** a poltrona precisa existir na geometria do setor. Marcar a G1 num setor que vai
até a fileira F criaria um lugar que o sistema acha que existe e a sala não tem.

**Fora de escopo, e por quê:**
- **Validar elegibilidade** — não há como conferir laudo pelo sistema, e cinemas reais
  checam na entrada. Marcar sem verificar é o comportamento do mundo real.
- **Meia-entrada** — abriria uma frente de regra de preço que não cabe no prazo.

Ambos vão ao README como limite consciente, não como esquecimento.

## D17 — Link de compartilhamento com token próprio

**Contexto:** o enunciado pede que o cliente compartilhe um ingresso por link.

**Escolhido:** o ingresso ganha um `share_token` opaco, diferente do código assinado do QR.
A página aberta pelo link mostra o ingresso **e o QR**.

**O que isto não é:** não é uma segunda camada de proteção. Quem abre o link consegue
entrar com o ingresso — e precisa conseguir: comprar três lugares e mandar um para cada
amigo é o caso de uso, e um link que não passasse na portaria não serviria para nada.

**Por que separar, então:** para que o código de entrada não trafegue na URL, onde ficaria
registrado em histórico de navegador, log de servidor e cabeçalho de origem. O token na
barra de endereço é descartável; o código assinado vai no corpo da resposta.

## D18 — Pagamento simulado decidido pelo número do cartão

**Descartado:** sortear aprovação e recusa. Quem estivesse avaliando não conseguiria
provocar a recusa de propósito, e metade do fluxo que o enunciado pede explicitamente
ficaria invisível.

**Escolhido:** o desfecho vem do número do cartão, como nos ambientes de teste dos
provedores de verdade. Qualquer número válido aprova; dois números específicos sempre
recusam, um por "cartão recusado" e outro por "saldo insuficiente". Os números vão no
README.

**Consequência:** a recusa é demonstrável em um clique, e o teste que a cobre é
determinístico.

## D19 — A portaria sempre responde 200

**Descartado:** devolver 404 para ingresso inexistente e 409 para já utilizado.

**Escolhido:** a validação responde 200 com o veredito no corpo — `VALID`, `INVALID`,
`ALREADY_USED` ou `WRONG_SESSION`.

**Por quê:** "este ingresso já foi usado" é uma resposta bem-sucedida a uma pergunta
legítima, não uma falha de requisição. Com código de erro, a tela da portaria trataria o
caso mais importante do fluxo como exceção, e o operador veria uma mensagem de erro
genérica em vez do veredito.

**Detalhe de ordem:** sessão errada é verificada **antes** de reuso. Quem entrou
legitimamente numa sala e apareceu na porta errada precisa ouvir "sessão errada", e não
"já utilizado".

## D20 — Reserva expira e devolve o assento

**Problema:** um pedido que ninguém paga prenderia a poltrona para sempre.

**Escolhido:** o pedido nasce com prazo. Passado o prazo sem pagamento, os ingressos viram
cancelados e o pedido, expirado — e o índice único parcial faz a poltrona voltar ao estoque
sem nenhuma limpeza adicional.

**Onde a limpeza roda:** no caminho de quem usa, antes de qualquer leitura ou escrita de
disponibilidade, e não em tarefa agendada. O projeto não tem processo de fundo, e depender
de um seria depender de algo que a avaliação não vai ligar. O custo é um UPDATE que quase
sempre não encontra nada.

## D21 — Classificação indicativa vem do catálogo, formato vem da sessão

**Origem:** pedido do Paulo em 22/08 — "pensando como o UCI e o ingresso.com funcionam, quero
classificação de idade e o que a sala e o filme disponibilizam".

**A separação que importa:** são duas informações de naturezas diferentes, e misturá-las
daria errado depois.

- **Classificação indicativa é do filme.** Vem do TMDb e é copiada para a sessão junto com
  título e pôster, pela mesma razão da D13: o que foi vendido não muda sozinho.
- **Áudio e formato de tela são da sessão.** O mesmo título roda dublado às 16h e legendado
  às 21h, em 2D numa sala e 3D noutra. Guardar isso no filme obrigaria a duplicar filme.

**Detalhe do catálogo:** o TMDb devolve **várias** classificações por filme, uma por tipo de
lançamento — Duna é 14 no cinema e 12 no digital. Para sessão de cinema vale a de exibição
em sala, então a extração ordena por tipo e prefere as de cinema. Vem na mesma requisição do
detalhe, via `append_to_response`, sem gastar uma segunda chamada por filme.

**Guardada como texto, não como enum:** é dado de terceiro. Um valor inesperado deve aparecer
na tela como veio, e não derrubar a criação da sessão. Filme sem classificação registrada
publica normalmente.

**Na interface:** as cores são as do sistema brasileiro — verde para livre, subindo até preto
para dezoito anos — porque é assim que a faixa é reconhecida sem ler. Mas **o número está
sempre escrito**: cor sozinha excluiria quem não distingue matiz, e a informação é importante
demais para depender disso. Mesmo princípio da D16.

## D22 — A raiz vira tela inicial, não redirecionamento

**Antes:** `/` mandava direto para a área de cada papel.

**Agora:** `/` é uma página de entrada com chamada, prévia das próximas sessões e os três
papéis explicados em um parágrafo cada. Entrar e Criar conta ficam no canto superior direito.

**Por quê:** quem chega pela primeira vez precisa entender o que o sistema faz antes de
decidir criar conta. O redirecionamento anterior jogava a pessoa numa lista sem contexto.

**A exceção:** quem entra como **portaria** continua indo direto para a tela de validação. É
uma tela operacional, usada em turno, e quem abre o sistema com esse papel quer trabalhar,
não ler apresentação.

**A prévia usa dados reais**, não ilustração: o pôster da próxima sessão é a arte da abertura.
Material de verdade convence mais que imagem genérica, e já estava disponível.

## D23 — A sala tem numeração contínua, e a tela fica embaixo

**Origem:** o Paulo apontou que o mapa não estava centralizado com a tela e que o VIP não
parecia estar em lugar nenhum da sala. Mandou como referência o mapa do UCI/Ingresso.com.

**O que o desenho anterior errava:** os setores eram retângulos empilhados, cada um começando
na fileira A. Uma sala com Plateia A–F e VIP A–B tinha **duas fileiras A**, e o ingresso diria
"A1" para dois assentos diferentes. Não era problema de layout: era o modelo não corresponder
a uma sala.

**Escolhido:**
- As fileiras correm pela sala inteira. Plateia A–F, VIP G–H. O deslocamento de cada setor é
  calculado a partir dos setores anteriores, não escrito nos dados — mudar o tamanho de um
  setor não obriga a reescrever os códigos do seguinte.
- A tela fica **embaixo**, e as fileiras crescem para cima. É como se lê uma planta de sala, e
  é a convenção dos sites de cinema. A fileira A é a mais próxima da tela.
- O VIP fica no fundo, longe da tela — que é onde ficam os lugares premium num cinema.
- A sala tem a largura do próprio conteúdo e é centralizada, para a tela ficar sobre as
  poltronas e não sobre o container.

**Trava nova:** a soma das fileiras de todos os setores não pode passar de 26. As fileiras são
nomeadas por letra, e sem esse limite o setor seguinte à fileira Z receberia caracteres que
não são letras.

**O que isso quebrou, e por que foi bom:** dois testes usavam "A1" no setor VIP e passaram a
falhar. Era o comportamento correto mudando — e a suíte avisou antes de qualquer pessoa ver.

## D24 — Poltrona ocupada mostra quem está sentado

**Quatro tentativas.** Transparente com opacidade baixa sumia na legenda, onde a amostra
aparece sozinha. Cor chapada não resolveu: qualquer cinza fica perto do fundo da página ou
perto da poltrona livre. Hachura ficou tímida demais para leitura de relance, que é como um
mapa de assentos é usado. O X funcionava, mas ainda pedia um segundo de tradução.

**Escolhido:** a silhueta de uma pessoa sentada, sobre azul-acinzentado — o que o UCI faz, e
agora entendo por quê. A figura não precisa ser interpretada: o lugar está ocupado porque tem
alguém nele.

O azul separa esse estado dos outros dois sem competir com o âmbar, que na interface inteira
significa ação. Os três estados ficam inconfundíveis: neutro escuro é livre, âmbar é escolhido,
azul com gente é ocupado — e nenhum depende de distinguir matiz para ser lido.

---

## Decisões pendentes

- [ ] Plataforma de deploy — FastAPI não roda confortavelmente na Vercel; avaliar Render ou Railway para a API, com o front na Vercel
- [ ] Biblioteca de leitura de QR pela câmera
