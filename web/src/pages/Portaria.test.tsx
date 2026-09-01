import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Portaria } from "./Portaria";
import type { SessionListItem } from "../lib/tipos";

// A leitora de QR toca em câmera e permissão, que não existem no jsdom. O que
// está sob teste aqui é a lista de sessões do turno, não a leitura.
vi.mock("html5-qrcode", () => ({
  Html5Qrcode: class {
    start = vi.fn();
    stop = vi.fn(() => Promise.resolve());
  },
}));

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

/** Mantém a resposta pendente até o teste decidir o desfecho, para dar tempo de
 *  observar o carregamento. `rodada` permite responder diferente na segunda
 *  chamada, que é o que o "tentar de novo" dispara. */
function gateControlado() {
  const pendentes: { ok: (s: SessionListItem[]) => void; falha: () => void }[] = [];

  vi.stubGlobal(
    "fetch",
    vi.fn((url: string) => {
      if (!String(url).includes("/gate/sessions")) return Promise.reject(new Error("fora do teste"));
      return new Promise((resolve, reject) => {
        pendentes.push({
          ok: (s) => resolve({ ok: true, status: 200, json: async () => s } as Response),
          falha: () => reject(new Error("rede fora")),
        });
      });
    }),
  );

  return {
    responde: (s: SessionListItem[]) => pendentes[pendentes.length - 1].ok(s),
    falha: () => pendentes[pendentes.length - 1].falha(),
    chamadas: () => pendentes.length,
  };
}

const seletor = () => screen.getByLabelText(/sessão desta porta/i);

afterEach(() => vi.unstubAllGlobals());

describe("portaria: a lista de sessões do turno tem três desfechos", () => {
  it("enquanto carrega, não deixa escolher uma sessão que ainda não chegou", () => {
    gateControlado();
    render(<Portaria />);

    expect(seletor()).toBeDisabled();
    expect(screen.getByRole("status")).toHaveTextContent(/carregando as sessões do turno/i);
  });

  it("quando a lista falha, avisa que a porta ficou no modo permissivo", async () => {
    // O defeito que este teste tranca: um `.catch(() => {})` deixava o seletor
    // com aparência de funcionando, mostrando só "Qualquer sessão". A conferência
    // de sessão errada ficava desarmada sem que ninguém na porta soubesse.
    const gate = gateControlado();
    render(<Portaria />);
    gate.falha();

    const aviso = await screen.findByRole("alert");
    expect(aviso).toHaveTextContent(/qualquer sessão/i);
    expect(aviso).toHaveTextContent(/de outra sala vai ser aceito/i);
  });

  it("depois da falha, tentar de novo refaz a chamada", async () => {
    const gate = gateControlado();
    render(<Portaria />);
    gate.falha();

    await userEvent.click(await screen.findByRole("button", { name: /tentar de novo/i }));
    expect(gate.chamadas()).toBe(2);

    gate.responde([sessao()]);
    expect(await screen.findByRole("option", { name: /A Odisseia/ })).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("com sessões, lista as do turno e explica o que a escolha faz", async () => {
    const gate = gateControlado();
    render(<Portaria />);

    gate.responde([sessao(), sessao({ id: "s2", title: "Toy Story 5" })]);

    expect(await screen.findByRole("option", { name: /A Odisseia/ })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /Toy Story 5/ })).toBeInTheDocument();
    await waitFor(() => expect(seletor()).toBeEnabled());
    expect(screen.getByText(/recusado com aviso claro/i)).toBeInTheDocument();
  });

  it("turno sem sessão diz isso — e não fica parecendo que falhou", async () => {
    const gate = gateControlado();
    render(<Portaria />);

    gate.responde([]);

    expect(await screen.findByText(/nenhuma sessão neste turno/i)).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
