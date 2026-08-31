<!-- Espelho de "Quadro", do vault de anotações do projeto (Obsidian).
     Versionado aqui porque o desafio pede os artefatos de processo junto do código. -->

# Quadro — Desafio Elite Dev Verzel

Instantâneo do kanban ao fim do projeto. As colunas viraram seções.

## ✅ Entregue — 22/08

- [x] Autenticacao com tres papeis e autorizacao (D1–D10)
- [x] Catalogo TMDb com provedor trocavel
- [x] Salas, setores e sessoes (D11–D15)
- [x] Poltronas acessiveis no modelo (D16)
- [x] Compra com assento marcado e pagamento simulado (D18)
- [x] Ingresso com QR nao-forjavel (D6)
- [x] Portaria com camera e quatro vereditos (D19)
- [x] Link de compartilhamento (D17)
- [x] Cancelamento com devolucao ao estoque
- [x] Landing publica (D22)
- [x] Classificacao indicativa e formato de exibicao (D21)
- [x] Sala continua, tela embaixo, corredores (D23–D25)
- [x] Deploy: Vercel + Render
- [x] Docker Compose completo
- [x] README e documento de uso de IA
- [x] Conferencia em clone limpo: 12 verificacoes, todas passaram


## ✅ Depois da entrega — 22 e 23/08

- [x] Revisao de seguranca e LGPD, com o que nao foi resolvido documentado
- [x] Gestao da programacao: repetir em varios dias, editar, remover, filtro por dia (D26–D29)
- [x] Cancelamento consertado: cancelar nao invalidava os ingressos da sessao (D30)
- [x] Cancelar todos os pedidos de uma sessao, como passo explicito (D30)
- [x] Sessao cancelada deixou de ocupar o horario da sala (D31)
- [x] Repetir em outros dias tambem na tela de edicao (D32)
- [x] Revisao de codigo: tres defeitos corrigidos (D33)
- [x] Volume na vitrine: tres salas, dez dias, ~90 sessoes
- [x] Artefatos de processo versionados no repositorio
- [x] 364 testes (242 back, 122 front)  → agora 371 (249 back, 122 front)


## Ciclo pos-devolutiva

- [x] 1.1 Escalada de privilegio no cadastro fechada (D34)
- [x] 1.2 Preco de setor com garantia relacional no banco (D35)
- [x] 1.3 Conflito de agenda por intervalo, nao por igualdade (D37)
- [x] 1.4 CheckConstraint do preco alinhado com o minimo da API (veio junto da D35)
- [x] 2.1 Identificadores do back-end em ingles (D36) — front medido e mantido
- [x] 2.2 Comentario enxuto: o porque fica, o quee a duplicacao saem (D38)
- [ ] 3.1 Rodada de produto no front-end  ← PROXIMA
      Achados medidos no ambiente publicado, em 375px:
      - [x] Cabecalho transborda 18px: "Criar conta" cortado e a pagina rola de lado em TODAS as telas
      - [x] Mapa da sala IMAX cortado dos dois lados no celular: aparecem as poltronas 4 a 11 de 14,
            com barra de rolagem fininha como unica pista e sem as letras das fileiras
      - [x] Poltrona 40px no dedo (32 ja cumpria o minimo AA; 44 e AAA)
      - [x] Inicio.tsx nao tem estado de carregamento nem de erro: o .catch engole a falha e a
            secao inteira de previa some, justo onde o Render hibernando custa ate um minuto
      - [ ] Sem estado de carregamento em NovaSessao, Portaria, Entrar e CriarConta
      - [ ] So 4 media queries em 1.322 linhas de CSS
- [ ] 3.2 Testes E2E de checkout, portaria e gestao
      - [ ] So 2 das 13 paginas tem teste (EmCartaz e Pedido)
- [ ] Portaria pertencer a um organizador (surgiu da D34)
- [ ] test_melhorias.py dividido por assunto — 78 testes, virou saco de gatos
- [ ] Expor occupies_until na API, para a tela mostrar quando a sessao termina


## Falta o Paulo fazer

- [ ] Ler e validar o docs/ia.md — escrito na sua voz
- [ ] Regenerar a chave do TMDb no painel e atualizar no Render
- [ ] Enviar o link em elitedev.verzel.com.br


## Se houvesse mais tempo

- [ ] Testes de front para checkout, portaria e painel do organizador
- [ ] Cache do catalogo e limite de tentativas em Redis, e nao em memoria por instancia
- [ ] Mapa de assentos em tempo real
- [ ] Aviso por e-mail e estorno quando o cinema cancela uma sessao
- [ ] Direitos do titular LGPD: exclusao e portabilidade de conta


## Avaliado e descartado

- [ ] Poltronas redondas e botao de exibir numeros — o carrinho ja mostra o codigo do lugar
- [ ] Descancelar uma sessao — desfaria a distincao entre cancelar e despublicar (D31)
- [ ] Cancelar sessao invalidando os ingressos em massa — chegou a ser implementado e foi
      desfeito: sem e-mail e sem estorno, o botao so limparia a tela do organizador (D30)
- [ ] Regra de recorrencia "toda sexta ate tal data" — programacao de cinema nao e regular (D27)
