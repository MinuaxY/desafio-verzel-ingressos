<!-- Espelho de "Decisões técnicas", do vault de anotações do projeto (Obsidian).
     Versionado aqui porque o desafio pede os artefatos de processo junto do código. -->

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

**Correção posterior:** o texto original desta decisão dizia que a portaria confere
"assinatura e banco", como se isso cobrisse tudo. Cobria o estado do *ingresso*, e não o da
*sessão* — um ingresso de sessão cancelada passava. Ver D30.

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

## D25 — Corredores são dado da sala, não regra visual

**Pedido do Paulo em 22/08:** "corredores entre blocos seria o ideal, daria a impressão real
de como é a sala para o cliente, mesmo vendo apenas o layout no site".

**Descartado:** dividir os blocos por uma regra fixa no front — a cada N poltronas, por
exemplo. Seria mais barato, mas produziria o mesmo desenho para salas diferentes, e o ponto
é justamente representar a sala que existe.

**Escolhido:** cada setor guarda as posições dos corredores. `[3, 9]` numa fileira de 12
poltronas produz blocos de 3, 6 e 3. O organizador define no cadastro da sala, e o formulário
mostra em tempo real como a fileira vai ficar dividida.

**Por que importa:** o corredor é o que transforma uma grade em planta. Com ele, quem está
comprando vê que a poltrona escolhida fica na ponta, junto da passagem — informação que muda
a escolha do lugar, e que uma grade uniforme esconde.

**No desenho:** o vão entre blocos é três vezes o vão entre poltronas vizinhas. Menos que isso
o olho lê como espaçamento, não como passagem.

**Trava:** corredor na posição 0 ou na última poltrona é recusado. Não separaria nada — seria
um espaço na borda do bloco.

## D26 — Revisão de segurança no fim, e o que ficou de fora

**Origem:** pergunta do Paulo em 22/08 — "você avaliou segurança de dados, LGPD, segurança de
rota?". Havia decisões de segurança espalhadas pelo projeto, mas **nenhuma revisão
sistemática**. São coisas diferentes.

**O que a revisão encontrou e foi corrigido:**

- **Login sem limite de tentativas.** O achado mais relevante: nenhuma senha resiste a
  tentativas ilimitadas. Cinco por minuto, contadas por **IP e e-mail juntos** — só por IP
  puniria uma rede compartilhada inteira quando uma pessoa erra a senha; só por e-mail
  deixaria alguém bloquear a conta de outra pessoa de propósito.
- **Nenhum cabeçalho de segurança.** Entraram `nosniff`, `X-Frame-Options`,
  `Referrer-Policy` e `Permissions-Policy`; HSTS só sob HTTPS, porque em `localhost` o
  navegador o ignoraria — ou pior, prenderia a máquina de quem avalia em https.
- **Erro de validação devolvia o parser por dentro**, com `ctx` e `input` — este último
  devolvendo de volta o que a pessoa enviou. Passa a devolver só local e motivo.
- **A resposta anunciava `server: uvicorn`**, que só entrega a stack a quem procura alvo.

**O que ficou de fora, e a razão:**

**Token em `localStorage` em vez de cookie `httpOnly`.** Cookie seria mais seguro contra XSS,
mas front e API estão em domínios diferentes — Vercel e Render. Cookie entre domínios exige
`SameSite=None`, o que **reabre CSRF** e passaria a exigir token anti-CSRF. Trocaria uma
exposição por outra, e exigiria refazer a autenticação num projeto já validado. A correção de
verdade começa por pôr front e API no mesmo domínio.

**Revogação de token.** Exige lista compartilhada entre instâncias, que o projeto não tem.

**Aparato de LGPD** — política, consentimento, direitos do titular. Não foi implementado
porque **exclusão de conta feita pela metade é pior que ausente**: sem política de retenção
definida, apagar um usuário levaria junto ingressos já validados, que são registro
operacional. A decisão correta seria anonimizar, e isso é discussão de produto.

**O que aprendi com isso:** decisões pontuais de segurança durante o desenvolvimento não
substituem uma passada dedicada no fim. As quatro correções eram baratas e nenhuma teria
aparecido sem alguém perguntar.

## D27 — Repetir sessão: dias escolhidos, não regra

**Pedido do Paulo em 22/08:** criar a mesma sessão em vários dias sem repetir o formulário
inteiro.

**Descartado:** uma regra do tipo "toda sexta até tal data". Programação de cinema não é
regular — um filme roda de quinta a domingo numa semana e só no fim de semana na seguinte —,
e uma regra que não cobre isso obrigaria a apagar depois o que ela criou a mais.

**Escolhido:** o organizador marca os dias num calendário de quatro semanas, com atalhos para
os casos comuns ("toda sexta", "sextas, sábados e domingos"). O dia do horário principal já
vem marcado e travado: desmarcá-lo ali não cancelaria a sessão, só confundiria.

**Conflito não aborta o lote.** Dia em que a sala já está ocupada é pulado, e volta na
resposta com o motivo. Recusar tudo por causa de um dia jogaria fora o trabalho de escolher
os outros nove. Quando **nada** é criado, a tela mostra a lista em vez de navegar — senão o
organizador sairia achando que deu certo.

**Teto de 60 datas:** sem limite, um engano criaria centenas de sessões.

## D28 — Apagar de vez ou desativar depende do histórico

**Pedido:** poder excluir salas e sessões, sem permitir excluir sala em uso.

O caso não é um só, e tratar tudo como "excluir" perderia informação:

**Sala sem nenhuma sessão** é apagada de verdade. Não há histórico a preservar, e deixá-la
desativada só acumularia lixo na lista.

**Sala que já teve sessão** é desativada. Some da lista de escolha, mas continua existindo:
sessão passada aponta para ela, e quem comprou precisa continuar vendo onde foi.

**Sala com sessão futura** não sai de jeito nenhum — há gente podendo comprar para ela agora.
A resposta diz quantas sessões e o que fazer antes.

**Sessão** segue a mesma lógica: rascunho sem ingresso é apagado; publicada sai do cartaz com
despublicar; e sessão que já vendeu não some, porque quem comprou precisa continuar
enxergando o que comprou — para essa, o caminho é cancelar.

## D29 — Geometria da sala trava na primeira sessão

**Escolhido:** nome e endereço são editáveis sempre. Fileiras, poltronas, corredores e
poltronas acessíveis, **só enquanto a sala não tiver nenhuma sessão**.

**Por quê:** o ingresso guarda o código da poltrona. Mudar o layout depois de vender faria a
`F12` de alguém apontar para um lugar que não existe mais — e não há como corrigir isso sem
escolher entre mover a pessoa de lugar sem avisar ou invalidar o ingresso.

**A mesma razão vale para o horário da sessão:** não muda depois que alguém compra. O sistema
não tem como avisar quem já tem ingresso, e trocar a hora por baixo dessa pessoa é pior que
recusar a edição. Preço continua editável — vale para quem ainda vai comprar, e o ingresso
emitido guarda o valor que foi pago.

**Consequência na interface:** o formulário de edição de sala mostra só nome e endereço, e
explica por que o layout não está ali. Esconder sem explicar pareceria falta.

---

## D30 — Cancelar sessão exige sessão vazia

**Problema encontrado testando:** publiquei uma sessão, comprei um ingresso, cancelei a
sessão e levei o QR na portaria. Resultado: `VALID — Entrada liberada, Plateia, poltrona
C6`. O cancelamento mexia só no campo `status` da sessão; os ingressos continuavam válidos
e a portaria nunca olhava a sessão. Na prática, a única diferença entre cancelar e
despublicar era que cancelar não podia ser desfeito — irreversível e sem efeito.

**As duas operações existem porque respondem a perguntas diferentes:**

| | Despublicar | Cancelar |
|---|---|---|
| A sessão vai acontecer? | Sim | Não |
| Para de vender? | Sim | Sim |
| Quem já comprou entra? | Sim | Não existe esse caso |
| Reversível? | Sim, republicando | Não |

**Descartado:** cancelar invalidando em massa os ingressos vendidos, com uma confirmação
avisando quantos seriam atingidos. Chegou a ser implementado, e foi desfeito: o sistema não
manda e-mail nem estorna. A pessoa descobriria na porta do cinema, e o botão daria ao
organizador a sensação de ter resolvido algo que ele só apagou da própria tela.

**Escolhido:** cancelar só é aceito enquanto a sessão está **vazia**. Com ingresso vendido a
API responde 409 dizendo quantos são, e o painel já mostra o botão desabilitado com o
motivo. Para tirar do cartaz uma sessão que vai acontecer, o caminho é despublicar. Se ela
realmente não vai acontecer, o organizador cancela os pedidos primeiro — e aí lida com cada
cliente sabendo que está lidando.

**"Vazia" é medido pelo mesmo critério do índice que impede vender duas vezes:** ingresso
cancelado pelo cliente não conta, porque a poltrona voltou ao estoque. Uma sessão em que
todo mundo desistiu está vazia de novo e volta a poder ser cancelada.

**O passo que faltava:** recusar o cancelamento resolve o dano, mas deixa o organizador sem
saída para a sessão que realmente não vai acontecer. Existe então um **"cancelar os N pedidos
vendidos"**, separado, no painel — ao lado do botão travado, dizendo o que fazer e não só o
que não dá. Ele despublica a sessão antes de esvaziá-la: não dá para drenar uma sessão que
continua vendendo.

São duas decisões diferentes de propósito, e não um botão só. Desfazer a compra de pessoas
reais é a que pesa; embutir isso num botão chamado "cancelar sessão" faria o organizador
tomá-la sem perceber que tomou.

**O pedido registra quem cancelou** (`cancelled_by_organizer`). Sem isso, o cliente abriria a
compra, leria "pedido cancelado" e concluiria que a desistência foi dele — o sistema
esconderia justamente o que precisa aparecer. A tela dele passa a dizer que o cinema cancelou
e que a devolução é com o organizador, em vez de oferecer "escolher de novo" numa sessão que
não existe mais. É o mais honesto que dá para ser sem apparato de e-mail e estorno, e a
falta desses dois está registrada como limitação conhecida.

**A portaria passou a conferir o estado da sessão de qualquer jeito.** No fluxo atual essa
checagem é redundante — não há como existir ingresso válido em sessão cancelada. Ela fica
porque a consequência de falhar é alguém entrar numa sala que não vai exibir nada, e porque
a regra do que pode ser cancelado é do organizador, enquanto a porta é a última linha. Mesma
lógica da D6: duas verificações independentes valem mais que uma bem feita.

---

## D31 — Sessão cancelada não ocupa a sala

**Impasse encontrado testando:** cancelei uma sessão e tentei recriá-la igual. "Já existe uma
sessão nessa sala nesse horário". Como cancelar não tem volta (D30), aquele horário daquela
sala ficava preso **para sempre** — e a linha cancelada seguia no painel sem nenhum botão.

**O erro não era a falta de um "descancelar".** Era uma pergunta respondida errado: a checagem
perguntava "existe alguma linha nessa sala nesse horário?", quando a pergunta é "existe alguma
sessão que **vai acontecer**". Cancelada é justamente o anúncio de que não vai.

**Escolhido:** cancelada deixa de ocupar a sala, na aplicação e no banco. A `UniqueConstraint`
de `(room_id, starts_at)` virou **índice parcial** com `WHERE status <> 'CANCELLED'` — a mesma
forma do índice que impede vender a poltrona duas vezes. O projeto já tinha a regra "cancelado
não ocupa" para assentos; ela só não tinha sido aplicada a horários.

**Descartado: um botão de "descancelar".** Ele desfaz a distinção que a D30 construiu.
Despublicar é reversível *porque* a sessão vai acontecer; cancelar é irreversível *porque* é o
anúncio de que não vai. Se dá para voltar atrás, as duas viram a mesma coisa com nomes
diferentes — que era exatamente o defeito original. Recriar a sessão também é mais honesto: é
uma sessão nova, com histórico próprio, em vez do anúncio anterior sendo apagado.

**Efeito colateral que o mesmo defeito causava:** a criação em lote usa a mesma checagem e
*pulava* o dia bloqueado por uma cancelada, informando "já havia sessão nessa sala nesse
horário" — um motivo falso.

**A cancelada que nunca vendeu nada pode ser apagada.** Ela não é registro de coisa alguma:
pela D30, estava vazia quando foi cancelada. Se chegou a ter pedido — cancelado depois ou não
—, fica, porque alguém pode precisar rastrear o que aconteceu com aquela compra. É a diferença
entre os dois campos que o painel recebe: `tickets_sold` conta quem ocupa poltrona hoje e
decide se dá para cancelar; `has_tickets` conta se algum dia houve pedido e decide se dá para
apagar.

---

## D32 — Repetir na edição cria cópias, não uma série

**Faltava:** a repetição em outros dias só existia na criação. Quem já tinha a sessão no ar e
quisesse colocá-la em mais dias tinha que refazer tudo do zero.

**Duas leituras de "repetir" na tela de edição, e elas são bem diferentes:**

1. *"Esta sessão se repete — aplique minhas edições às irmãs."* Exige um conceito de **série**
   que o projeto não tem: as sessões criadas em lote são linhas independentes, sem vínculo.
   Criá-lo significaria decidir o que se propaga (preço? horário?), o que acontece quando uma
   irmã vendeu e a outra não, e o que fazer quando uma é cancelada.
2. *"Crie cópias desta sessão em outros dias."*

**Escolhido: a segunda.** É o que a mesma tela de criação já faz, e o endpoint `/batch` já
recebe exatamente o que a sessão editada tem — filme, sala, áudio, formato, preços. Nenhuma
mudança no back-end: só a interface faltava. A primeira leitura fica registrada como ideia
descartada, não esquecida.

**O bloco fica fora do formulário de edição.** Repetir não altera esta sessão, cria outras.
Se estivesse dentro, "Salvar alterações" produziria sessões novas sem que ninguém tivesse
pedido.

**As cópias usam o que está no formulário, e não o que está salvo.** Quem ajusta o preço e
manda repetir espera que as cópias saiam com o preço ajustado — e o bloco diz isso em voz
alta, inclusive que vale para alterações ainda não salvas. Elas também nascem no mesmo estado
da original: repetir uma sessão que está no cartaz e receber rascunhos seria surpresa.

**O componente de escolha de dias precisou saber em qual dos dois contextos está.** Na criação
o dia base é uma sessão que vai nascer junto e a contagem diz "3 sessões, contando o horário
principal"; na edição ele já existe, e prometer 3 para entregar 2 seria uma mentira pequena e
irritante.

---

## D33 — Revisão de código: três defeitos e o volume da vitrine

Revisão feita em 22/08, depois da entrega. Rodei os linters, li o código e sondei caminhos de
borda contra a API em vez de só ler. O que os testes já cobriam passou; o que não estava
coberto rendeu três defeitos.

**1. Sessão de graça travava o cliente.** A API aceitava preço zero (`ge=0`). O cliente
reservava a poltrona, e o pagamento simulado — que recusa valor zero, corretamente — nunca
aprovava. O pedido morria e a poltrona ficava presa até a reserva expirar. A tela de criação
já exigia preço maior que zero; **a API é que discordava da sua própria interface**. O mínimo
passou a ser um centavo, o que faz as duas concordarem e recusa o caso na porta em vez de no
meio do caminho. Sessão gratuita de verdade exigiria pular o gateway, e não é o que o
enunciado pede.

**2. Uma rota que prometia a própria remoção.** `GET /auth/organizer-only` existia só para o
teste de autorização por papel da Sprint 1, e o docstring dizia que sairia "quando os
endpoints reais de organizador passarem a exercer a mesma trava". Eles passaram, e ela ficou.
Não vazava nada — exigia o papel e devolvia o e-mail de quem chamou —, mas era andaime
contradizendo o próprio comentário. Removida, e os dois testes passaram a exercer a trava em
`/organizer/sessions`, que é onde ela vale.

**3. A portaria perdia a sessão no instante em que ela começava.** A tela lia `/sessions`, a
vitrine, que só mostra o que ainda vai começar — o que está certo para quem compra e errado
para quem está na porta. Às 20:01, com o público ainda entrando, a sessão sumia do seletor e
o operador perdia a checagem de "este ingresso é de outra sessão", justamente no momento em
que ela serve. A portaria ganhou `GET /gate/sessions`, com uma janela do turno: até seis
horas atrás e até dois dias à frente.

**Higiene, na mesma passada:** um import e um argumento de teste sem uso, nove linhas acima
das 100 colunas que o resto do projeto respeita, e um `Date.now()` reavaliado a cada render
por falta de inicializador preguiçoso. Os 80 avisos de `Depends()` em argumento padrão são
falso positivo — é o idioma do FastAPI.

**O volume da vitrine.** O seed criava quatro sessões numa sala. Quatro sessões não exercitam
paginação, filtro por dia nem busca — as três coisas que precisam ser vistas funcionando.
Agora são **três salas de geometrias diferentes** e uma programação de dez dias com os treze
filmes do catálogo: cerca de 90 sessões, nove páginas, todos os dias da barra preenchidos.
As salas variam de propósito — a Sala 2 tem setor único, para provar que o mapa fica bom sem
VIP; a Sala 3 tem quatro blocos e 132 lugares, o mapa no limite do que a tela acomoda.

A idempotência mudou de chave: antes comparava `(sala, filme, futuro)`, o que quebraria agora
que o mesmo filme roda em vários dias. Passou a usar `(sala, horário)` — a mesma chave do
índice do banco —, então rodar duas vezes no mesmo dia não duplica nada.

---

## D34 — O cadastro público não concede papel

**Defeito, apontado na devolutiva da Verzel:** `UserRegister` aceitava `role` do cliente e
`AuthService.register()` gravava esse valor como veio. Bastava mandar `"role": "ORGANIZER"` no
corpo do cadastro público para receber o painel do organizador — e `"GATE"` para validar
ingressos na portaria, papel que a própria tela de cadastro nem oferecia.

```
cadastro pedindo ORGANIZER -> 201, papel concedido: ORGANIZER
   painel do organizador: 200
   cria sala: 201
cadastro pedindo GATE -> 201
   acessa a portaria: 200
```

**Não foi descuido de implementação: foi a premissa.** A tela perguntava "Como você vai usar"
e oferecia Cliente ou Organizador, como se o papel fosse preferência de quem se cadastra. Num
sistema de bilheteria não é: cliente é autoatendimento, organizador é o cinema que contratou a
plataforma, e portaria é funcionário desse cinema. Os dois últimos são concedidos, não
escolhidos.

**Escolhido:** o cadastro público cria **sempre** cliente, e `role` deixou de ser campo de
entrada. Organizador e portaria vêm de `python -m app.admin`, que grava direto no banco.

**Descartado: ignorar o campo em silêncio.** Seria o comportamento REST usual para campo
desconhecido, e aqui está errado — quem mandasse `role: ORGANIZER` receberia 201 e uma conta de
cliente, saindo convencido de ter recebido o que pediu. O schema usa `extra="forbid"`, então a
resposta é 422 dizendo qual campo sobrou. Campo de segurança que a API descarta caladamente
ensina o cliente a acreditar em algo que nunca aconteceu.

**Descartado: um endpoint administrativo protegido.** Exigiria um papel de administrador que o
modelo não tem, e criar um só para hospedar essa operação traz mais superfície do que resolve.
Quem tem acesso ao servidor já pode tudo; a linha de comando não amplia nada.

**O que isso custou nos testes:** todos registravam com papel explícito, então a suíte inteira
dependia do defeito. Passaram a usar um helper único no `conftest`: cliente sai do cadastro
público, papel privilegiado é gravado direto no banco — e nos dois casos o token vem do login
normal, então o teste continua entrando pela mesma porta do usuário real.

**Fica em aberto, e é maior:** a portaria valida ingresso de **qualquer** organizador. Um
usuário GATE não pertence a um cinema. Amarrar funcionário ao organizador é modelagem nova, e
está anotada como próximo passo, não como parte desta correção.

---

## D35 — O preço aponta para um setor da sala daquela sessão, e quem garante é o banco

**Apontado na devolutiva:** `SessionSectorPrice` tinha `session_id` e `sector_id` referenciando
suas tabelas de forma **independente**. Nada no banco impedia gravar o preço de um setor de
outra sala. Só o serviço conferia — e invariante que vive apenas no serviço é invariante que a
próxima rota esquece.

**Escolhido: duas chaves estrangeiras compostas que compartilham `room_id`.**

```
FOREIGN KEY (session_id, room_id) REFERENCES sessions(id, room_id)
FOREIGN KEY (sector_id,  room_id) REFERENCES sectors (id, room_id)
```

A primeira exige que a sessão esteja naquela sala; a segunda exige o mesmo do setor. Sendo a
**mesma coluna** nas duas, elas falam necessariamente da mesma sala. A regra deixa de ser uma
conferência em Python e passa a ser um estado que o banco não consegue representar.

**O custo é uma coluna derivável.** `room_id` sai da sessão, então guardá-la é redundância. É a
troca que a técnica exige: é justamente o compartilhamento dessa coluna que prova a regra. Sem
ela, só sobrariam trigger ou checagem na aplicação — e a aplicação já era o problema.

**Descartado: trigger.** Faria a mesma coisa, em código imperativo, invisível no schema e
difícil de testar. Chave composta é declarativa: quem lê a tabela vê a regra.

**Descartado: `CHECK` com subconsulta.** O Postgres não permite — `CHECK` não enxerga outras
tabelas, exatamente para não depender de linhas que podem mudar depois.

**As chaves simples deram lugar às compostas**, com `ON DELETE CASCADE` preservado. Para o
Postgres aceitar as compostas foi preciso declarar `UNIQUE (id, room_id)` em `sessions` e em
`sectors`: trivialmente único por causa da chave primária, mas uma chave estrangeira só aponta
para colunas com unicidade declarada.

**Junto veio o item 1.4:** o `CHECK` do preço subiu de `>= 0` para `>= 1`. O banco aceitava zero
enquanto a API já recusava desde a D33, e sessão de graça deixa o cliente com um pedido que
nunca pode ser pago. Estava na mesma tabela e na mesma migration — separar seria uma segunda
migration para mudar a mesma linha.

**Nenhum teste existente precisou mudar**, o que era o resultado esperado: a regra já valia, só
não estava garantida. Os cinco novos escrevem **direto no banco**, por baixo do serviço, porque
é exatamente o caminho que a checagem em Python não cobre.

---

## D36 — Identificadores em inglês

**Apontado na devolutiva:** convivem `OrderService`, `SessionNotAvailable`, `customer_id` e
`price_cents` com `pedido`, `sessao`, `pagar`, `processar` e `resultado.aprovado`. O problema
não é a escolha do idioma: é alternar os dois dentro da mesma unidade de código.

Medido antes de decidir: **42 funções com nome em português contra 154 em inglês**, com classes
em inglês e métodos em português no mesmo arquivo.

**Escolhido: inglês nos identificadores** — nomes de função, variável, exceção, constraint e
contrato. Português continua onde é conteúdo, não código: mensagens ao usuário, docstrings,
comentários e documentação.

**Por quê:** é a menor migração (154 já estão assim contra 42), é o idioma dos frameworks que o
código chama o tempo todo, e é o que um revisor espera encontrar. Português nos identificadores
seria igualmente defensável como convenção — só custaria quase quatro vezes mais para chegar no
mesmo lugar.

**A varredura foi feita na etapa 2.1:** as 42 funções em português viraram zero, e com elas
variáveis, constantes, exceções e quatro parâmetros de query — `busca`, `dia`, `dias` e
`por_pagina` também eram contrato, então o front acompanhou no mesmo commit.

**Duas exceções deliberadas, e não esquecimento:**

*Os nomes dos testes ficam em português.* A devolutiva pediu convenção única em "serviços,
exceções, variáveis e contratos" — código. `test_o_banco_recusa_setor_de_outra_sala` não é
identificador chamado por ninguém: é a especificação legível do comportamento, e traduzi-la
piora a leitura sem ganhar nada.

*Os comandos do CLI ficam em português.* `python -m app.admin criar-organizador` fala com quem
opera a plataforma, e o resto da saída do comando é em português. Traduzir só o verbo deixaria
a interface bilíngue.

**O front-end ficou como estava, e isso foi medido antes de decidir.** A crítica era alternar
os dois idiomas *dentro da mesma unidade de código*. No front isso não acontece: 24
declarações com raiz portuguesa contra 1 inglesa, e **zero arquivos misturando**. Renomear 31
arquivos — componentes, rotas, testes — traria o risco de um refactor grande sem tokenizador de
TypeScript, para corrigir um problema que não existe ali. O back-end era o que misturava, e é
onde os frameworks já falam inglês.

**A ferramenta de renomeação teve de ser refeita.** A primeira usava expressão regular com
limite de palavra e trocou dentro de strings e comentários: o CLI virou `create-organizador` e
docstrings em português ganharam verbos em inglês no meio da frase. A segunda usa o tokenizador
do Python e só troca tokens `NAME`, por posição, de trás para frente.

O caminho inverso também mordeu: `@pytest.mark.parametrize` nomeia o argumento **por string**, e
o `label()` do SQLAlchemy também. Como as strings ficaram intactas — corretamente —, oito
decoradores e um label precisaram ser alinhados a mão.

**`alembic/versions` não foi tocado.** Migration é registro histórico do que rodou no banco;
reescrevê-la falsificaria o passado e arriscaria o replay.

---

## D38 — O comentário guarda o porquê, não o quê

**Apontado na devolutiva:** trechos diretos vinham acompanhados de blocos explicando em detalhe
decisões **já registradas** em `docs/decisoes.md`. O código parecia narrado, e não escrito para
manutenção. `order_service.py` e `session.py` foram citados pelo nome.

**A crítica é justa, e o padrão era meu.** Escrevi esses blocos ao longo do projeto inteiro.

**Regra adotada:** o código diz *o quê*, o comentário diz *o porquê não-óbvio*, a documentação
guarda o contexto e o trade-off. Explicação longa de decisão vira ponteiro curto — `Ver decisão
D30` — em vez de repetir o conteúdo do documento.

**Resultado nos dois arquivos citados:** `order_service.py` de 18% para 13% de prosa,
`session.py` de 38% para 31%.

**Por que parei em 31% e não fui atrás de um número menor.** O que restou em `session.py` são
comentários de duas linhas respondendo por que a duração presumida existe, por que
`occupies_until` é materializada, por que o `primaryjoin` é explícito, por que as duas chaves
compartilham `room_id`. Nenhum deles é recuperável lendo o código — é exatamente o
"comportamento realmente não óbvio" que a devolutiva mandou manter. Perseguir a porcentagem a
partir daqui seria apagar informação para melhorar uma métrica.

---

## D37 — A sala é reservada pelo intervalo, não pelo instante

**Apontado na devolutiva:** o conflito de agenda considerava apenas igualdade de `room_id` e
`starts_at`. Duas sessões de duas horas na mesma sala, às 20:00 e às 20:01, não violavam nada —
e a sala ficava com duas plateias.

A pergunta estava errada, como na D31. Não é *"começam no mesmo instante"*, é *"ocupam a sala
ao mesmo tempo"*.

**Escolhido:** constraint de exclusão sobre o intervalo ocupado.

```sql
EXCLUDE USING gist (
    room_id WITH =,
    tstzrange(starts_at, occupies_until) WITH &&
) WHERE (status <> 'CANCELLED')
```

Ocupação é **início + duração do filme + folga de limpeza**, e não só a duração: o público sai,
a equipe limpa, a próxima entra. Sem a folga, duas sessões coladas passariam pela trava e a
sala teria plateia entrando enquanto a outra ainda sai.

**A coluna `occupies_until` é materializada, e isso não foi escolha estética.** Tentei calcular
na própria expressão do índice e o Postgres recusou:

```
ERROR: functions in index expression must be marked IMMUTABLE
```

`timestamptz + interval` é apenas **estável**, não imutável — somar meses depende do fuso. Coluna
gerada (`GENERATED ALWAYS AS ... STORED`) falha pelo mesmo motivo. Então a soma precisa estar
gravada, e quem grava é a aplicação, numa função só: `occupation_end()`. O `CHECK
(occupies_until > starts_at)` impede o caso em que a ocupação vazia passaria sem sobrepor nada.

**O nome é `occupies_until`, e não `ends_at`,** porque não é o fim do filme: é quando a sala
volta a estar livre. Nome que promete uma coisa e entrega outra é o começo do próximo defeito.

**Encostar não é sobrepor.** `tstzrange` é fechado no início e aberto no fim, então uma sessão
pode começar exatamente no minuto em que a sala libera. É o que um cinema faz.

**O índice antigo foi removido.** Começar no mesmo instante é caso particular de sobrepor, e a
exclusão já cobre. Duas travas dizendo quase a mesma coisa é o tipo de duplicidade que faz quem
lê duvidar de qual vale.

**A migration teve de resolver os dados existentes:** havia **27 pares sobrepostos**, criados
sob a regra antiga. Ela cancela uma sessão de cada par — cancelar e não apagar, porque cancelada
não ocupa a sala (D31) e o registro continua existindo. A escolha de qual cancelar não é
arbitrária: **sai a que tem menos ingresso vendido**, porque cancelar uma sessão vendida
quebraria a promessa que a D30 protege; no empate, sai a que começa depois. Um dos 27 pares
tinha ingresso vendido, e a sessão sobreviveu.

**O seed produzia a própria sobreposição.** A grade fixa tinha intervalos de 150 a 180 minutos,
e o filme mais longo do catálogo ocupa 192. Em vez de alargar a grade, a programação passou a
ser **empilhada a partir da duração real** de cada filme, arredondando para o próximo quarto de
hora — que é como um cinema monta a grade, e resolve na origem em vez de esconder. O seed também
passou a consultar a ocupação antes de inserir: ele grava direto no banco, sem passar pelo
serviço, então precisa respeitar a trava por conta própria.

**Efeito colateral que valeu:** em `criar`, a busca do filme subiu para antes da checagem de
sala ocupada. A trava agora depende da duração, e a duração vem do catálogo.

---

## D39 — O front começa pelo celular, e o que estava quebrado lá

**A devolutiva pediu "revisar responsividade, espaçamentos e estados de erro".** Fui medir no
ambiente publicado a 375px em vez de tratar isso como acabamento, e o que apareceu não era
acabamento: era o produto não funcionando no aparelho em que mais se compra ingresso.

### O mapa da sala aparecia cortado dos dois lados

Na Sala 3 (IMAX, 14 poltronas por fileira) viam-se as poltronas **4 a 11**. As 1–3 e 12–14
ficavam fora, e as letras das fileiras nem apareciam. A única pista era uma barra de rolagem
fininha.

A causa é uma armadilha de flexbox: `.setor__grade` tinha `align-items: center` **junto com**
`overflow-x: auto`. Conteúdo mais largo que o contêiner transborda para os dois lados, e o lado
esquerdo fica **inalcançável** — `scrollLeft` não fica negativo.

**Escolhido: separar os papéis em dois elementos.** O de fora rola; um trilho interno com
`width: fit-content` e `margin-inline: auto` centraliza quando cabe e encosta na esquerda quando
não cabe.

**Descartado: encolher a poltrona para caber.** Já estavam em 32px; diminuir para caber 14 numa
tela de 375px levaria a ~20px, e trocaria um problema visível por um erro de toque.

**Descartado: pedir para girar o aparelho.** Empurra para o usuário um problema de layout.

**A rolagem ganhou sombra**, em CSS puro, que aparece só quando há o que rolar e some ao chegar
na ponta. Uma barra fininha não é convite; a sombra é.

### O cabeçalho transbordava 18px em todas as telas

"Criar conta" ficava cortado e a **página inteira rolava de lado** — em toda tela do sistema,
não só na landing. Passa a quebrar linha abaixo de 40rem.

### A poltrona no dedo

Sobe para 40px em `@media (pointer: coarse)`, e fica em 32px no mouse. **Correção de um exagero
meu:** eu tinha citado os 44×44 da WCAG como se fossem obrigatórios. São do nível **AAA**
(critério 2.5.5); o mínimo AA é **24×24** (2.5.8), que os 32px já cumpriam. É conforto no dedo,
não conformidade — o que muda a prioridade, não a validade.

### A landing engolia a falha da API

`Inicio.tsx` fazia `.catch(() => setPagina(null))`, e a seção de prévia inteira sumia: sem
carregamento, sem erro, sem explicação. No pior lugar possível — é onde a primeira visita pega o
Render acordando, o que o próprio README avisa que leva até um minuto.

Passou a ter os **três desfechos**: carregando (dizendo que o servidor pode estar acordando),
erro (com caminho para tentar de novo) e vazio. Quatro testes trancam os três.

### O que isso revelou sobre a suíte

**Os 22 testes do mapa passaram sem uma linha de alteração.** O defeito era invisível para eles
porque jsdom não tem layout: `getBoundingClientRect` devolve zeros, e não há transbordo para
medir. Nenhum teste de unidade pegaria isso.

É o argumento mais concreto para a etapa 3.2: essa classe de defeito — transbordo, corte,
alvo pequeno demais — só existe com layout de verdade, e só um navegador de verdade mede.

---

## D40 — Estado indeterminado não pode ser desenhado como estado determinado

**O item do quadro estava errado, e medir foi o que mostrou isso.** Estava escrito "sem estado
de carregamento em NovaSessao, Portaria, Entrar e CriarConta". Fui conferir os quatro: os quatro
**já tinham** feedback de envio — `Entrando…`, `Criando…`, `Salvando…`, `Verificando…`, todos com
o botão desabilitado. O que faltava não era isso. Era o **carregamento inicial**, e o problema
não era ausência de aviso: era a tela **afirmar com confiança uma coisa que ainda não sabia**.

### A sala que o organizador não tinha

`NovaSessao` decidia pelo `salas.length === 0` — que também é o valor inicial, antes de
`/rooms` responder. Enquanto a lista não chegava, e para sempre se ela falhasse, a tela dizia
**"Você ainda não tem salas"** com um botão para cadastrar a primeira.

Para um organizador com três salas, isso é uma afirmação falsa que empurra para o erro certo:
criar uma sala duplicada. E o `.catch` mandava a mensagem para o alerta geral da página, longe
do passo 2, onde a frase errada continuava.

### A porta que ficava permissiva em silêncio

`Portaria` tinha `.catch(() => {})`. Se `/gate/sessions` falhasse, o seletor continuava lá, com
cara de funcionando, oferecendo só **"Qualquer sessão"** — que é o modo permissivo. A conferência
de "ingresso de outra sessão" da D33 ficava desarmada, e a pessoa na porta não tinha como saber.

Esse é o pior dos dois. Não é uma tela feia: é uma **proteção que se desliga sozinha sem avisar**,
justamente no aparelho e no momento em que ninguém vai investigar.

**Escolhido: três estados explícitos** — `carregando | pronto | erro` —, o mesmo desenho da D39.
Enquanto carrega, o seletor fica desabilitado, porque não dá para escolher de uma lista que não
chegou. No erro, a mensagem diz **o que se perdeu**, e não só que algo falhou: "um ingresso de
outra sala vai ser aceito". Com botão de tentar de novo, e sem interromper a leitura — que
continua funcionando.

**Descartado: só trocar o `.catch` vazio por um alerta genérico.** "Erro ao carregar" não conta
que a porta ficou permissiva, que é a única parte que muda o que o operador faz.

**Descartado: bloquear a validação quando a lista falha.** A portaria existe para deixar gente
entrar; travar a fila por causa de uma conferência secundária troca um risco pequeno por uma
parada de operação.

**Descartado: distinguir carregando de erro por um `null` a mais no tipo.** Era o que já havia
(`SessionListItem[] | null`), e é exatamente a origem do defeito: um `null` tem que significar
duas coisas ao mesmo tempo, e quem lê escolhe a errada.

### O que ficou de regra

Toda tela que busca dado tem **três desfechos, não dois**. Quando o código só distingue dois, o
terceiro não some — ele se disfarça de um dos outros, e escolhe justamente o que parece normal:
lista vazia, nenhuma sala, qualquer sessão.

### Provado antes e depois

Dez testes novos, e os dois arquivos foram rodados **contra a versão antiga** para ver a falha:
4 de 5 falham na portaria, 3 de 5 em nova sessão. Os que passam nas duas versões são os caminhos
felizes, que nunca estiveram quebrados. Depois, conferido no navegador em 375px, derrubando um
endpoint de cada vez com o resto no ar — que é a falha parcial real, e não o servidor inteiro fora.

---

## Decisões que estavam pendentes

Estavam abertas quando este registro começou. Ficam aqui com o desfecho, e não apagadas: uma
lista de pendências que some não conta que foi resolvida — parece que foi esquecida.

- [x] **Plataforma de deploy.** FastAPI não roda confortavelmente na Vercel. Resolvido em
  20/08: front na **Vercel**, API e banco no **Render**, plano gratuito. O Render hiberna após
  alguns minutos sem tráfego, o que custa até um minuto na primeira visita — aceitável para
  uma avaliação, e está avisado no README.
- [x] **Biblioteca de leitura de QR pela câmera.** Resolvido com **html5-qrcode**, que resolve
  permissão de câmera e escolha de lente sozinha. A digitação manual continua ao lado, porque
  a câmera exige HTTPS fora de `localhost` e nem todo avaliador vai abrir pelo celular.

---

## Nenhuma decisão em aberto

O projeto foi entregue em 22/08 e revisado até 23/08. O que foi conscientemente deixado de
fora está em **Limitações conhecidas**, no README, e no quadro, na coluna "Avaliado e
descartado" — que é lugar de escolha registrada, não de pendência.
