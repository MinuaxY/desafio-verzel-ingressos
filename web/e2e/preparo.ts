/**
 * Conferência antes de qualquer teste de ponta a ponta.
 *
 * O Playwright sobe o Vite sozinho, mas não sobe a API nem o banco. Sem esta
 * checagem, a API fora do ar produziria dezenas de falhas de asserção sobre
 * telas vazias, e a causa real ficaria escondida no meio do relatório.
 *
 * Isso já aconteceu com a suíte de back-end — Docker parado, 264 testes
 * vermelhos por erro de conexão, e um bom tempo perdido procurando regressão
 * onde não havia. A mensagem abaixo é essa lição transformada em código.
 */
const API = process.env.VITE_API_URL ?? "http://localhost:8000";

const COMO_SUBIR = `
  A API não respondeu em ${API}.

  Na raiz do projeto:
      docker compose up -d db          e esperar o "healthy"

  Na pasta api/, com o ambiente virtual ativo:
      uvicorn app.main:app --port 8000

  Ou tudo de uma vez, sem desenvolver:
      docker compose up --build
`;

export default async function preparo() {
  let resposta: Response;
  try {
    resposta = await fetch(`${API}/health`);
  } catch {
    throw new Error(COMO_SUBIR);
  }
  if (!resposta.ok) throw new Error(COMO_SUBIR);

  // A API de pé não basta: o seed precisa ter deixado sessão em cartaz, senão
  // o teste de compra falharia por falta de dado e pareceria defeito de tela.
  const cartaz = await fetch(`${API}/sessions?per_page=1`).then((r) => r.json());
  if (!cartaz.items?.length) {
    throw new Error(
      "A API está no ar, mas não há sessão em cartaz. Rode o seed:\n" +
        "    python -m app.seed        (na pasta api/, com o ambiente virtual ativo)",
    );
  }
}

