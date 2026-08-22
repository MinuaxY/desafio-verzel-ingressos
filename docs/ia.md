# Como a IA foi usada neste projeto

O enunciado pede este relato, e recomenda o uso de IA. Então aqui vai o registro honesto:
o que a ferramenta fez, o que eu fiz, onde ela errou e como as decisões foram tomadas.

---

## Ferramenta

**Claude Code** (Claude Opus 5), assistente de linha de comando com acesso ao sistema de
arquivos, ao terminal e ao navegador. Foi a única ferramenta de IA usada — não houve Copilot,
ChatGPT nem geradores de interface.

O modo de trabalho foi conversacional: eu definia o objetivo e as restrições, a ferramenta
propunha, eu decidia, ela implementava, e eu verificava no navegador.

---

## O que a IA fez

**A maior parte do código.** Modelos, migrations, endpoints, serviços, testes, componentes
React e CSS foram escritos pela ferramenta. Não faz sentido fingir o contrário: são cerca de
8.800 linhas em cinco dias de calendário e três de trabalho efetivo.

Também fez o trabalho de apoio que consome tempo e não aparece: gerar migrations, rodar a
suíte de testes, subir e derrubar servidores, diagnosticar processos travados, e verificar o
fluxo no navegador de ponta a ponta.

---

## O que eu fiz

### Escolhi a stack, contra a recomendação

A ferramenta recomendou NestJS, com o argumento de que TypeScript no back e no front reduz
troca de contexto. Escolhi **Python com FastAPI**, porque é onde eu produzo mais rápido e
porque a documentação OpenAPI automática entrega valor direto a quem for avaliar.

### Escolhi o catálogo, e mudei quando travou

Escolhi a Ticketmaster por ser mais fiel ao domínio de ingressos. A chave nunca foi liberada,
e no primeiro dia eu decidi migrar para o TMDb em vez de esperar. A troca acabou melhorando o
modelo — está detalhado em [`decisoes.md`](decisoes.md), D3 e D4.

### Recusei a simplificação sugerida no preço

A ferramenta recomendou preço único por sessão, para caber no prazo. Escolhi **setores com
preços diferentes**, porque é como cinema funciona de verdade e porque o mapa de assentos fica
mais rico.

### Refinei a modelagem da sala

A ferramenta ofereceu duas opções: layout embutido na sessão, ou entidade Sala reutilizável.
Em vez de escolher uma, perguntei qual era a consequência prática da primeira. Ao entender que
eu redigitaria a geometria a cada sessão, escolhi a Sala reutilizável — **e pedi um atalho para
cadastrar sala nova dentro do fluxo de criar sessão**, que nenhuma das duas opções previa.

### Peguei um ponto cego da IA: acessibilidade

Perguntei se assentos para pessoas com deficiência e obesas tinham sido considerados. Não
tinham — nem no modelo, nem no plano. A ferramenta admitiu o esquecimento e sugeriu tratar como
tarefa de front-end, o que eu recusei.

Assento acessível virou característica da **sala**, gravada no banco, com validação de
geometria e marcação visual que não depende de cor. Salas de espetáculo no Brasil têm exigência
legal disso, e a pergunta chegou no dia em que ainda era barato: se tivesse aparecido no último
dia, seria migration sobre dados já criados.

Esta é a parte do projeto que mais me representa, e ela nasceu de uma pergunta, não de um
prompt pedindo código.

### Pedi a vitrine pública, e ela mudou a arquitetura

Pedi uma tela inicial com Entrar e Criar conta no canto superior direito, mostrando uma prévia
do conteúdo. A ferramenta apontou uma consequência que eu não tinha visto: para mostrar sessões
a quem não tem conta, a listagem precisa ser **pública** — o que mudava uma premissa do dia
seguinte. Decidimos abrir a vitrine desde o início. Ver `decisoes.md`, D10.

### Mandei travar as decisões caras primeiro

No fim do segundo dia, pedi para adiantar o que pudesse mudar mais tarde, para evitar
retrabalho no fim. Isso virou uma sessão inteira de modelagem — sala, setores, sessões, preços,
dinheiro em centavos, horário com fuso — antes de qualquer tela existir. Foi a decisão de
processo que mais economizou tempo, porque o dia seguinte foi só consumir uma API pronta.

### Testei e achei defeitos

O texto dos botões-link sumia no hover, e eu reportei. Era um conflito de especificidade no
CSS que afetava todos os links estilizados como botão, não só o que eu tinha visto.

---

## Onde a IA errou

Registro porque acho que conta mais que a lista de acertos.

**Esqueceu acessibilidade por completo.** Não estava no modelo nem no planejamento, e só entrou
porque eu perguntei.

**Afirmou uma proteção que não existia.** Ao implementar o link de compartilhamento, escreveu
na documentação que o link "não é chave de entrada" — mas o endpoint devolvia o código do QR,
então era. Ela mesma pegou o erro ao reler o próprio código e corrigiu a descrição, mantendo o
comportamento, que estava certo: quem recebe um ingresso compartilhado precisa conseguir entrar.

**Escreveu testes que batiam na API externa de verdade.** Um teste falhou e revelou que o cache
de configuração impedia a troca de provedor. Os testes estavam consultando o TMDb pela rede em
vez de usar dados locais. Depois da correção, a suíte caiu de 7,5s para 3,8s.

**Publicou arquivos que não examinou.** Ao commitar com `git add -A`, levou junto quatro assets
do template do Vite, incluindo o favicon roxo deles — que ficou na aba do navegador por dois
dias. Foi descoberto no terceiro dia.

**Matou o processo errado.** Ao reiniciar o servidor, encerrou o processo pai do uvicorn e
deixou o filho servindo código antigo, o que produziu quinze minutos de diagnóstico de um bug
que não existia.

**Errou o próprio CSS na primeira tentativa de corrigir.** A correção do hover funcionou para a
cor do texto, mas anulou o clareamento do fundo. Precisou de uma segunda passada.

---

## O que eu faria diferente

Perguntaria mais cedo sobre o que **não** estava no enunciado. A pergunta sobre acessibilidade
rendeu a melhor parte do projeto e levou trinta segundos para ser feita. Se eu tivesse feito o
mesmo tipo de pergunta no primeiro dia — sobre o que um cinema de verdade precisa e o PDF não
menciona — provavelmente teria encontrado outras.

---

## Artefatos de processo

Versionados neste repositório, como o enunciado pede:

- [`decisoes.md`](decisoes.md) — 20 decisões técnicas, cada uma com a alternativa descartada e
  o motivo. É o documento que melhor mostra como o projeto foi conduzido.

Fora do repositório, num vault Obsidian pessoal, ficaram o Product Backlog, o Diário das
Sprints — que registra o que deu errado a cada dia — e o quadro Kanban. O conteúdo relevante
deles está refletido aqui e no README.
