import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { Pedido } from "./Pedido";
import type { Order } from "../lib/tipos";

function pedido(over: Partial<Order> = {}): Order {
  return {
    id: "p1",
    session_id: "s1",
    movie_title: "A Odisseia",
    starts_at: "2026-08-25T00:30:00Z",
    room_name: "Sala 1",
    status: "CANCELLED",
    total_cents: 3200,
    created_at: "2026-08-22T12:00:00Z",
    expires_at: null,
    paid_at: null,
    decline_reason: null,
    cancelled_by_organizer: false,
    tickets: [],
    ...over,
  };
}

function respondeCom(corpo: Order) {
  vi.stubGlobal(
    "fetch",
    vi.fn(() =>
      Promise.resolve({ ok: true, status: 200, json: async () => corpo } as unknown as Response),
    ),
  );
}

async function monta(corpo: Order) {
  respondeCom(corpo);
  render(
    <MemoryRouter>
      <Pedido />
    </MemoryRouter>,
  );
  return screen.findByText(/A Odisseia/i);
}

describe("pedido cancelado", () => {
  it("a desistência do cliente convida a escolher de novo", async () => {
    // A poltrona voltou ao estoque e a sessão continua de pé: o caminho
    // natural é voltar para ela.
    await monta(pedido({ cancelled_by_organizer: false }));

    expect(screen.getByText(/voltaram para o estoque/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /escolher de novo/i })).toHaveAttribute(
      "href",
      "/sessao/s1",
    );
  });

  it("o cancelamento pelo cinema diz quem cancelou e o que fazer", async () => {
    // Sem isso o cliente leria só "pedido cancelado" e concluiria que a
    // desistência foi dele. Ver decisão D30.
    await monta(pedido({ cancelled_by_organizer: true }));

    expect(screen.getByRole("alert")).toHaveTextContent(/cancelada pelo cinema/i);
    expect(screen.getByRole("alert")).toHaveTextContent(/devolução/i);
    expect(screen.queryByText(/voltaram para o estoque/i)).not.toBeInTheDocument();
  });

  it("não oferece voltar para a sessão que não vai mais acontecer", async () => {
    await monta(pedido({ cancelled_by_organizer: true }));

    expect(screen.queryByRole("link", { name: /escolher de novo/i })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: /outras sessões/i })).toHaveAttribute(
      "href",
      "/em-cartaz",
    );
  });

  it("pedido em pé não mostra aviso de cancelamento nenhum", async () => {
    await monta(pedido({ status: "PAID", paid_at: "2026-08-22T12:05:00Z" }));

    expect(screen.queryByText(/voltaram para o estoque/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/cancelada pelo cinema/i)).not.toBeInTheDocument();
  });
});
