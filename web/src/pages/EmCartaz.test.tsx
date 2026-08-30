import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { EmCartaz } from "./EmCartaz";
import type { SessionListItem, SessionPage } from "../lib/tipos";

function sessao(over: Partial<SessionListItem> = {}): SessionListItem {
  return {
    id: "s1",
    title: "A Odisseia",
    poster_url: "https://image.tmdb.org/t/p/w500/x.jpg",
    year: 2026,
    runtime_minutes: 172,
    age_rating: "14",
    audio: "SUBTITLED",
    screen_format: "THREE_D",
    starts_at: "2026-08-25T00:30:00Z",
    room_name: "Sala 1",
    room_location: "Centro",
    min_price_cents: 3200,
    max_price_cents: 5400,
    ...over,
  };
}

function pagina(itens: SessionListItem[]): SessionPage {
  return { items: itens, total: itens.length, page: 1, total_pages: 1 };
}

/** A vitrine faz duas chamadas: a lista de sessões e os dias que têm sessão,
 *  para a barra de datas. Um mock que responde a mesma coisa para as duas
 *  entregaria uma página onde o componente espera uma lista. */
function respondeCom(corpo: unknown, dias: { date: string; total: number }[] = []) {
  const fetchFalso = vi.fn((url: string, opcoes?: RequestInit) =>
    Promise.resolve({
      ok: true,
      status: 200,
      json: async () => (String(url).includes("/sessions/days") ? dias : corpo),
      _opcoes: opcoes,
    } as unknown as Response),
  );
  vi.stubGlobal("fetch", fetchFalso);
  return fetchFalso;
}

function monta() {
  render(
    <MemoryRouter>
      <EmCartaz />
    </MemoryRouter>,
  );
}

describe("vitrine com sessões", () => {
  it("lista o que está em cartaz", async () => {
    respondeCom(pagina([sessao(), sessao({ id: "s2", title: "Toy Story 5" })]));
    monta();

    expect(await screen.findByText("A Odisseia")).toBeInTheDocument();
    expect(screen.getByText("Toy Story 5")).toBeInTheDocument();
    expect(screen.getByText("2 sessões")).toBeInTheDocument();
  });

  it("cada cartaz mostra classificação, áudio, formato e faixa de preço", async () => {
    respondeCom(pagina([sessao()]));
    monta();

    await screen.findByText("A Odisseia");
    expect(screen.getByText("14")).toBeInTheDocument();
    expect(screen.getByText("Legendado")).toBeInTheDocument();
    expect(screen.getByText("3D")).toBeInTheDocument();
    expect(screen.getByText(/R\$\s?32,00 a R\$\s?54,00/)).toBeInTheDocument();
  });

  it("o cartaz leva para a sessão", async () => {
    respondeCom(pagina([sessao()]));
    monta();

    await screen.findByText("A Odisseia");
    expect(screen.getByRole("link")).toHaveAttribute("href", "/sessao/s1");
  });

  it("uma sessão só usa o singular", async () => {
    respondeCom(pagina([sessao()]));
    monta();
    expect(await screen.findByText("1 sessão")).toBeInTheDocument();
  });

  it("filme sem pôster não deixa buraco na grade", async () => {
    respondeCom(pagina([sessao({ poster_url: null })]));
    monta();

    await screen.findByText("A Odisseia");
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });

  it("não exige autenticação", async () => {
    // A vitrine é pública: pedir conta para olhar é atrito sem contrapartida.
    // Ver decisão D10.
    const fetchFalso = respondeCom(pagina([sessao()]));
    localStorage.setItem("verzel.token", "seria-enviado-se-a-rota-fosse-privada");
    monta();

    await screen.findByText("A Odisseia");
    for (const [, opcoes] of fetchFalso.mock.calls) {
      const cabecalhos = (opcoes?.headers ?? {}) as Record<string, string>;
      expect(cabecalhos.Authorization).toBeUndefined();
    }
  });
});

describe("barra de dias", () => {
  it("aparece quando há dias com sessão", async () => {
    const amanha = new Date();
    amanha.setDate(amanha.getDate() + 1);
    const iso = amanha.toISOString().slice(0, 10);

    respondeCom(pagina([sessao()]), [{ date: iso, total: 1 }]);
    monta();

    await screen.findByText("A Odisseia");
    expect(await screen.findByRole("button", { name: /todos/i })).toBeInTheDocument();
  });

  it("não aparece quando não há sessão nenhuma à frente", async () => {
    respondeCom(pagina([sessao()]), []);
    monta();

    await screen.findByText("A Odisseia");
    expect(screen.queryByRole("button", { name: /todos os dias/i })).not.toBeInTheDocument();
  });
});

describe("vitrine vazia", () => {
  it("explica que ainda não há sessões", async () => {
    respondeCom(pagina([]));
    monta();

    expect(await screen.findByText(/nenhuma sessão em cartaz/i)).toBeInTheDocument();
    expect(screen.getByText(/assim que o organizador publicar/i)).toBeInTheDocument();
  });
});

describe("busca", () => {
  it("consulta a API com o termo digitado", async () => {
    const fetchFalso = respondeCom(pagina([sessao()]));
    monta();
    await screen.findByText("A Odisseia");

    await userEvent.type(screen.getByRole("searchbox"), "toy");
    await userEvent.click(screen.getByRole("button", { name: "Buscar" }));

    await waitFor(() => {
      const urls = fetchFalso.mock.calls
        .map(([url]) => String(url))
        .filter((u) => !u.includes("/days"));
      expect(urls.some((u) => u.includes("search=toy"))).toBe(true);
    });
  });

  it("busca sem resultado diz o termo procurado", async () => {
    respondeCom(pagina([]));
    monta();
    await screen.findByText(/nenhuma sessão/i);

    await userEvent.type(screen.getByRole("searchbox"), "zzz");
    await userEvent.click(screen.getByRole("button", { name: "Buscar" }));

    expect(await screen.findByText(/nada em cartaz para "zzz"/i)).toBeInTheDocument();
  });

  it("com busca ativa aparece o botão de limpar", async () => {
    respondeCom(pagina([sessao()]));
    monta();
    await screen.findByText("A Odisseia");

    expect(screen.queryByRole("button", { name: "Limpar" })).not.toBeInTheDocument();

    await userEvent.type(screen.getByRole("searchbox"), "odis");
    await userEvent.click(screen.getByRole("button", { name: "Buscar" }));

    expect(await screen.findByRole("button", { name: "Limpar" })).toBeInTheDocument();
  });
});

describe("servidor fora do ar", () => {
  it("mostra recado legível em vez de tela quebrada", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    monta();

    expect(await screen.findByRole("alert")).toHaveTextContent(
      /não foi possível falar com o servidor/i,
    );
  });
});
