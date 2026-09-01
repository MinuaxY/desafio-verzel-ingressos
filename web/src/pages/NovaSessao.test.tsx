import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { NovaSessao } from "./NovaSessao";
import type { Room } from "../lib/tipos";

function sala(over: Partial<Room> = {}): Room {
  return {
    id: "r1",
    name: "Sala 1",
    location: "Centro",
    capacity: 120,
    sectors: [],
    ...over,
  };
}

/** A resposta de `/rooms` fica pendente até o teste decidir o desfecho.
 *  `chamadas` conta as idas, que é como se verifica o "tentar de novo". */
function salasControladas() {
  const pendentes: { ok: (r: Room[]) => void; falha: () => void }[] = [];

  vi.stubGlobal(
    "fetch",
    vi.fn((url: string) => {
      if (!String(url).includes("/rooms")) return Promise.reject(new Error("fora do teste"));
      return new Promise((resolve, reject) => {
        pendentes.push({
          ok: (r) => resolve({ ok: true, status: 200, json: async () => r } as Response),
          falha: () => reject(new Error("rede fora")),
        });
      });
    }),
  );

  return {
    responde: (r: Room[]) => pendentes[pendentes.length - 1].ok(r),
    falha: () => pendentes[pendentes.length - 1].falha(),
    chamadas: () => pendentes.length,
  };
}

function monta() {
  render(
    <MemoryRouter>
      <NovaSessao />
    </MemoryRouter>,
  );
}

const NEGA_TER_SALAS = /você ainda não tem salas/i;

afterEach(() => vi.unstubAllGlobals());

describe("nova sessão: o passo da sala não afirma o que não sabe", () => {
  it("enquanto carrega, não diz que o organizador não tem salas", () => {
    // O defeito que este teste tranca: a tela decidia pelo `salas.length === 0`,
    // que também é o estado inicial. Quem tinha salas era informado de que não
    // tinha, e convidado a cadastrar uma duplicada.
    salasControladas();
    monta();

    expect(screen.queryByText(NEGA_TER_SALAS)).not.toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(/carregando suas salas/i);
  });

  it("quando a busca falha, diz que falhou — e não que a lista está vazia", async () => {
    const salas = salasControladas();
    monta();
    salas.falha();

    const aviso = await screen.findByRole("alert");
    expect(aviso).toHaveTextContent(/não foi possível carregar suas salas/i);
    expect(screen.queryByText(NEGA_TER_SALAS)).not.toBeInTheDocument();
  });

  it("depois da falha, tentar de novo refaz a chamada", async () => {
    const salas = salasControladas();
    monta();
    salas.falha();

    await userEvent.click(await screen.findByRole("button", { name: /tentar de novo/i }));
    expect(salas.chamadas()).toBe(2);

    salas.responde([sala(), sala({ id: "r2", name: "Sala 2" })]);
    expect(await screen.findByRole("option", { name: /Sala 2/ })).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("com salas, oferece a escolha", async () => {
    const salas = salasControladas();
    monta();

    salas.responde([sala(), sala({ id: "r2", name: "Sala 2" })]);

    expect(await screen.findByRole("option", { name: /Sala 1/ })).toBeInTheDocument();
    expect(screen.queryByText(NEGA_TER_SALAS)).not.toBeInTheDocument();
  });

  it("sem sala nenhuma, aí sim convida a cadastrar a primeira", async () => {
    const salas = salasControladas();
    monta();

    salas.responde([]);

    expect(await screen.findByText(NEGA_TER_SALAS)).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole("status")).not.toBeInTheDocument());
    expect(screen.getByRole("link", { name: /cadastrar sala/i })).toBeInTheDocument();
  });
});
