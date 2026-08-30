<!-- Espelho de "Aprendizados", do vault de anotações do projeto (Obsidian).
     Versionado aqui porque o desafio pede os artefatos de processo junto do código. -->

# Aprendizados — Desafio Verzel

O que ficou de transferível para os próximos projetos. Não é resumo do que foi feito
([Diário das Sprints](diario.md) cobre isso): é o que mudaria a forma de trabalhar da próxima vez.

Cada item tem o episódio concreto que o originou, para não virar máxima solta.

---

## 1. Deploy não é a última etapa. É um teste de arquitetura.

**O que aconteceu:** publicar foi a primeira coisa da reta final, não a última. Em menos de
uma hora, achou dois defeitos que a máquina de desenvolvimento escondia:

- O `requirements.txt` pinava `email-validator==2.4.1`, **versão que não existe**. A
  instalação local tinha sido feita sem pin, então nada acusava. Qualquer pessoa que
  clonasse o repositório e seguisse o README não conseguiria instalar as dependências.
- O seed duplicava sessões entre dias diferentes — e o README afirmava o contrário.

**A lição:** deploy força o projeto a provar que roda fora da sua máquina. Variáveis de
ambiente de verdade, banco limpo, dependências resolvidas do zero. É o único jeito de
descobrir o que está preso ao seu ambiente sem perceber.

**Na prática:** publique cedo, mesmo que incompleto. O primeiro deploy é diagnóstico.

---

## 2. Trave as decisões que ficam presas no banco. Deixe as telas para depois.

**O que aconteceu:** no fim do segundo dia, a decisão de adiantar a modelagem — sala,
setores, sessões, preços, dinheiro em centavos, horário com fuso — antes de existir qualquer
tela. Foi a decisão de processo que mais economizou tempo.

**Por quê:** tela é barata de refazer; schema com dado já criado, não. Quando a classificação
indicativa entrou depois, ela precisou de migration com `server_default` temporário e um
remendo no seed para completar as sessões que já existiam em produção. Isso multiplicado por
cada campo teria sido inviável.

**O teste para saber se uma decisão é dessas:** *se eu mudar isso semana que vem, preciso
mexer em dado que já existe?* Se sim, decida agora.

---

## 3. Pergunte o que **não** está no enunciado.

**O que aconteceu:** a pergunta "considerou assentos para deficientes e obesos?" levou trinta
segundos e virou a parte do projeto que mais se destaca — quatro naturezas de poltrona
gravadas no banco, com marcação que não depende de cor.

Não estava no PDF. A IA tinha deixado passar. E o próprio enunciado convidava: *"se você
olhar a proposta e pensar 'isso ficaria melhor com tal coisa', faça e conte no README por
quê"*.

**A lição:** requisito escrito é o piso, não o teto. A pergunta que rende é *"o que um
cinema de verdade precisa que este PDF não menciona?"* — e ela custa quase nada.

**O que faria diferente:** fazer essa pergunta no **primeiro** dia, não no terceiro.
Provavelmente teria encontrado outras coisas na mesma linha.

---

## 4. Meça antes de concluir. E desconfie quando a medida diz que está certo.

**Dois episódios opostos, e os dois ensinam:**

**Quando a medida corrigiu a intuição:** o texto do botão sumia no hover. A primeira
correção parecia funcionar, mas medir mostrou que o fundo tinha parado de clarear — eu tinha
usado `var(--bg)`, exatamente a cor do fundo da página. Contraste 1,32, pior que antes.

**Quando a medida escondeu o problema:** o bloco VIP parecia desalinhado. A medição dizia que
o centro estava em 633px, igual ao da plateia — tecnicamente centralizado. Mas três corredores
em posições que não conversam fazem o olho ler bagunça mesmo com os centros iguais. Quem
apontou foi o olho humano; a régua teria dado o problema por resolvido.

**A lição:** medida serve para desmentir intuição errada, não para substituir julgamento.
Quando alguém diz "está estranho" e a medida diz "está certo", provavelmente a medida está
medindo a coisa errada.

---

## 5. Em interface funcional, sutileza é defeito.

**O que aconteceu:** a poltrona ocupada precisou de **quatro tentativas**. Transparente com
opacidade baixa sumia na legenda. Cor chapada não funcionou — qualquer cinza fica perto do
fundo ou perto da poltrona livre. Hachura ficou tímida demais para leitura de relance. Só o
símbolo explícito resolveu, e a resposta final veio de olhar como o UCI faz: a silhueta de
uma pessoa sentada.

**Por que as três primeiras falharam:** todas tentavam marcar ausência com abstração. Um mapa
de assentos é lido em um segundo, de relance, às vezes no escuro. Elegância que exige
tradução é ruído.

**A lição:** antes de inventar, olhe como o problema já foi resolvido no domínio. Não é falta
de originalidade — convenção estabelecida carrega décadas de teste com usuários reais.

---

## 6. O que descrimina o sistema deve ser dado, não regra fixa no código.

**O que aconteceu:** os corredores da sala poderiam ser uma regra visual — "quebra a cada
quatro poltronas". Seria mais barato. Mas daria o mesmo desenho para salas diferentes, e o
ponto era representar **a sala que existe**.

Vira dado: cada setor guarda as posições dos corredores, e o organizador define no cadastro.

**O mesmo padrão apareceu em:** preço por setor (dado da sessão, não do setor), poltronas
acessíveis (dado da sala, não classe CSS), áudio e formato (dado da sessão, não do filme).

**A lição:** quando uma característica varia entre casos reais, ela é dado. Regra fixa no
código é o atalho que parece economia e vira limitação.

---

## 7. Teste específico encontra; teste genérico só confirma.

**O que aconteceu:** um teste do catálogo falhou e revelou que os testes estavam **batendo na
API do TMDb pela rede** — `get_settings` tinha `lru_cache`, e trocar a variável de ambiente
não surtia efeito. Depois da correção, a suíte caiu de 7,5s para 3,8s.

Um teste que só verificasse "a busca devolve resultados" teria passado, e o acoplamento
continuaria escondido. O que pegou foi um teste que afirmava algo preciso sobre **quais**
resultados.

**Outros exemplos no projeto:** o teste de concorrência com oito threads disputando a mesma
poltrona; o teste que garante que senha errada e e-mail inexistente respondem igual.

**A lição:** teste que só confirma o caminho feliz tem valor baixo. O que paga é o que afirma
uma consequência específica — e falha quando ela muda.

---

## 8. O build é diferente do verificador de tipos.

**Aconteceu duas vezes:**

- `tsc --noEmit` passou e `tsc -b` falhou por `erasableSyntaxOnly` do Vite 8.
- Depois dos testes de front, o `defineConfig` do Vite não conhecia a chave `test`. **Sem
  rodar o build, o deploy teria quebrado.**

**A lição:** valide com o comando que a esteira vai rodar, não com o atalho mais rápido. E
rode o build antes de todo push que vá para produção.

---

## 9. Documente o que foi descartado, não só o que foi escolhido.

**O que aconteceu:** as 25 decisões do projeto têm todas o mesmo formato — alternativa
descartada, escolha, motivo, custo aceito. O enunciado pedia isso, mas o efeito colateral foi
maior: escrever "o que eu não fiz e por quê" obrigou a ter um porquê.

Duas vezes a própria escrita corrigiu o código. Ao documentar o link de compartilhamento,
ficou evidente que a descrição afirmava uma proteção que o endpoint não tinha.

**A lição:** decisão sem alternativa registrada não é decisão, é acaso documentado. E o
exercício de escrever a alternativa é onde os erros aparecem.

---

## 10. Sobre trabalhar com IA

**O que funcionou:** dirigir por objetivo e restrição, não por instrução. As melhores partes
do projeto vieram de perguntas — "e assentos para deficientes?", "isso não está centralizado",
"a hachura ficou tímida" — e não de prompts pedindo código.

**O que exigiu atenção:** a ferramenta erra com a mesma confiança com que acerta. Esqueceu
acessibilidade por completo. Afirmou na documentação uma proteção que o código não tinha.
Publicou arquivos que não examinou. Matou o processo errado e gastou quinze minutos
diagnosticando um bug que não existia.

**A lição prática:** o valor não está em quanto código sai, está em quem decide. Revisar
afirmação por afirmação — especialmente as que soam convincentes — é o trabalho que sobra, e
é o trabalho que importa.

---

## 11. Decisão pontual de segurança não é revisão de segurança.

**O que aconteceu:** o projeto tinha bcrypt, autorização por papel, HMAC no ingresso e login
que não revela quais e-mails existem. Parecia coberto. Uma pergunta direta — *"você avaliou
segurança e LGPD?"* — expôs que **nunca houve uma passada dedicada**.

A revisão levou pouco mais de meia hora e achou quatro coisas, uma delas relevante: **o login
aceitava tentativas ilimitadas**. Nenhuma senha resiste a isso.

**A lição:** decisões tomadas ao longo do caminho cobrem o que você lembrou de considerar. A
revisão no fim cobre o que você não lembrou — que é justamente onde mora o problema. São
etapas diferentes, e a segunda não acontece sozinha.

**Vale para além de segurança:** o mesmo padrão apareceu na acessibilidade e no calendário.
Perguntar "o que eu não olhei?" é barato e rende mais que revisar o que já foi olhado.

---

## 12. Uma funcionalidade pode existir inteira e não fazer nada.

**O que aconteceu:** o cancelamento de sessão tinha botão, endpoint, teste e uma decisão
documentada. Uma pergunta — *"qual a diferença entre cancelar e despublicar?"* — me fez montar
o fluxo real em vez de responder de cabeça: publiquei, comprei um ingresso, cancelei a sessão
e levei o QR na portaria.

```
VALID — Entrada liberada, Plateia, poltrona C6
```

Cancelar só mudava um campo `status`. Os ingressos seguiam válidos e a portaria nunca olhava a
sessão. A única diferença real entre cancelar e despublicar era que cancelar não tinha volta —
irreversível e sem efeito nenhum.

**A lição:** todos os testes passavam, porque cada um verificava a parte que eu tinha pensado
em verificar — o status virou CANCELLED, sim. Nenhum perguntava *"e daí?"*. Teste de unidade
confirma que a peça mudou de estado; só o fluxo ponta a ponta responde se a mudança de estado
significa alguma coisa.

**O gatilho foi uma pergunta de usuário, não uma suspeita minha.** Quem pergunta "qual a
diferença entre esses dois botões?" está dizendo que não consegue distingui-los — e às vezes é
porque, de fato, não há diferença.

---

## 13. Quando duas partes do sistema discordam, uma delas está errada — e vale procurar qual.

**O que aconteceu:** a tela de criação de sessão exigia preço maior que zero. A API aceitava
zero. Ninguém tinha reparado porque o caminho normal passa pela tela.

Só que o pagamento simulado recusa valor zero, corretamente. Então bastava chegar à API por
outro caminho — e o botão de repetir que eu tinha acabado de criar era exatamente esse — para
o cliente reservar uma poltrona e **nunca conseguir pagar**.

**A lição:** validação repetida em duas camadas é certo, e é a prática recomendada. Repetida
com **regras diferentes** é um defeito esperando um caminho novo. Quando eu achar a mesma
regra escrita em dois lugares, comparar as duas versões custa um minuto.

---

## 14. Uma checagem pode responder com precisão a pergunta errada.

**O que aconteceu:** depois de tornar o cancelamento irreversível, cancelar uma sessão passou a
prender aquele horário daquela sala **para sempre** — não dava para recriar a sessão nem para
descancelar.

O reflexo era criar um "descancelar". Mas o erro estava antes: a checagem perguntava *"existe
alguma linha nessa sala nesse horário?"*, quando a pergunta é *"existe alguma sessão que **vai
acontecer**?"*. Sessão cancelada é justamente o anúncio de que não vai.

**A lição:** quando uma trava correta produz um beco sem saída, a saída raramente é adicionar
uma porta. É reler o que a trava está de fato perguntando. E o sistema **já tinha a regra
certa** noutro lugar — o índice que impede vender a poltrona duas vezes ignora ingresso
cancelado. A mesma ideia estava aplicada de forma inconsistente em dois pontos.

---

## 15. Documento é código que ninguém compila.

**O que aconteceu:** na conferência final, o README afirmava que os artefatos de processo
estavam versionados em `docs/` — e só as decisões estavam. As tabelas de teste somavam 196 de
242 casos reais. O registro de decisões ainda listava como "pendentes" duas escolhas tomadas
dias antes.

Nada disso quebrava o sistema. Todas eram afirmações do projeto sobre si mesmo que tinham
deixado de ser verdade sem ninguém perceber.

**A lição:** código que mente é pego pelo teste; documento que mente só é pego por alguém
conferindo linha a linha. E quem vai conferir primeiro é quem está avaliando. Vale tratar
número em documentação como o que ele é: uma afirmação que precisa ser reconferida sempre que
o que ela conta muda.

---

## 16. Teste que depende da data falha no dia errado, não no dia do erro.

**O que aconteceu:** um teste da barra de datas quebrou sem que eu tivesse tocado no front.
`/1 de setembro/` casava também com "11 de setembro", e a barra mostra duas semanas — só que
isso só produz ambiguidade quando o intervalo mostrado contém os dois. Estava latente desde que
o teste foi escrito e apareceu porque a suíte rodou em 30/08.

Foi a **segunda vez** que a mesma armadilha apareceu no projeto: antes tinha sido `Poltrona A1`
casando com `A10`, `A11` e `A12`.

**A lição:** regex sem âncora sobre rótulo que contém número é bomba-relógio, e o teste que a
contém passa com folga até o dia em que não passa. Quando o dado é gerado a partir de `hoje`, a
suíte tem uma dimensão a mais que ninguém está olhando — e a falha chega meses depois, longe do
commit que a criou.

---

## O que faria diferente no próximo

1. **Perguntar sobre o não-escrito no dia 1**, não no dia 3.
2. **Publicar no dia 1**, mesmo com uma tela só, para achar problemas de ambiente cedo.
3. **Escrever teste de front junto com a tela**, e não numa etapa separada no fim. Três dos
   erros encontrados eram dos próprios testes — teriam sido mais baratos de achar na hora.
4. **Conferir o calendário antes de planejar.** Um dia inteiro passou em branco e só foi
   percebido quando o relógio da máquina desmentiu o plano.
5. **Reservar uma passada de segurança**, como etapa própria e não como consequência das
   decisões do caminho. Meia hora achou quatro problemas.
6. **Percorrer o fluxo inteiro como usuário depois de cada funcionalidade**, e não só rodar os
   testes dela. O cancelamento passou em todos os testes e não fazia nada.
7. **Conferir a documentação contra o código antes de entregar**, como se fosse revisão de
   código. Foi o que achou a última leva de erros, e nenhum deles era de programação.
8. **Ancorar toda busca de teste feita por texto com número dentro**, e desconfiar de teste que
   monta o dado a partir de `hoje`.
