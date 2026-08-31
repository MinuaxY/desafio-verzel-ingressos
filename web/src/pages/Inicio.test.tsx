import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Inicio } from "./Inicio";
import { AuthProvider } from "../auth/AuthContext";
import type { SessionListItem, SessionPage } from "../lib/tipos";

function sessao(over: Partial<SessionListItem> = {}): SessionListItem {
  return {
    id: "s1",
    title: "A Odisseia",
    poster_url: null,
    year: 2026,
    runtime_minutes: 172,
    age_rating: "14",
    audio: "SUBTITLED",
    screen_format: "TWO_D",
    starts_at: "2026-09-25T00:30:00Z",
    room_name: "Sala 1",
    room_location: "Centro",
    min_price_cents: 3200,
    max_price_cents: 5400,
    ...over,
  };
}

/** A promessa fica pendente até ser resolvida pelo teste, para dar tempo de
 *  observar o estado de carregamento antes do desfecho. */
function fetchControlado() {
  let resolver!: (corpo: SessionPage) => void;
  let rejeitar!: () => void;
  const espera = new Promise<SessionPage>((ok, falha) => {
    resolver = ok;
    rejeitar = () => falha(new Error("rede fora"));
  });

  vi.stubGlobal(
    "fetch",
    vi.fn((url: string) =>
      String(url).includes("/sessions")
        ? espera.then((corpo) => ({ ok: true, status: 200, json: async () => corpo }) as Response)
        : Promise.reject(new Error("sem sessão")),
    ),
  );
  return { resolver, rejeitar };
}

function monta() {
  render(
    <MemoryRouter>
      <AuthProvider>
        <Inicio />
      </AuthProvider>
    </MemoryRouter>,
  );
}

afterEach(() => vi.unstubAllGlobals());

describe("landing: a prévia do cartaz tem três desfechos", () => {
  it("enquanto carrega, avisa que o servidor pode estar acordando", () => {
    // A hibernação do plano gratuito custa até um minuto na primeira visita, e
    // é justamente quando alguém abre o link pela primeira vez.
    fetchControlado();
    monta();

    expect(screen.getByRole("status")).toHaveTextContent(/até um minuto/i);
  });

  it("com sessões, mostra a prévia", async () => {
    const { resolver } = fetchControlado();
    monta();

    resolver({ items: [sessao(), sessao({ id: "s2", title: "Toy Story 5" })], total: 2, page: 1, total_pages: 1 });

    expect(await screen.findByText("A Odisseia")).toBeInTheDocument();
    expect(screen.getByText("Toy Story 5")).toBeInTheDocument();
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("quando a API falha, diz que falhou em vez de sumir com a seção", async () => {
    // O defeito que este teste tranca: um `.catch` silencioso fazia a seção
    // inteira desaparecer, sem carregamento, sem erro e sem explicação.
    const { rejeitar } = fetchControlado();
    monta();
    rejeitar();

    const aviso = await screen.findByRole("alert");
    expect(aviso).toHaveTextContent(/não foi possível carregar/i);
    expect(screen.getByRole("link", { name: /tentar de novo/i })).toBeInTheDocument();
  });

  it("sem sessão nenhuma, diz que não há — e não finge que está carregando", async () => {
    const { resolver } = fetchControlado();
    monta();

    resolver({ items: [], total: 0, page: 1, total_pages: 1 });

    expect(await screen.findByText(/nenhuma sessão em cartaz/i)).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole("status")).not.toBeInTheDocument());
  });
});
