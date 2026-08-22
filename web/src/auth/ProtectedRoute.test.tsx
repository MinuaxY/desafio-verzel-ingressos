import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AuthProvider } from "./AuthContext";
import { ProtectedRoute } from "./ProtectedRoute";
import type { Role } from "./types";
import { tokenStorage } from "../lib/api";

function respondeUsuario(role: Role) {
  return vi.fn().mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => ({ id: "u1", name: "Fulano", email: "f@x.dev", role }),
  } as Response);
}

/** Monta as três áreas e entra numa delas, com o papel informado. */
function monta({ role, rota = "/organizador" }: { role: Role | null; rota?: string }) {
  if (role) {
    tokenStorage.set("token-valido");
    vi.stubGlobal("fetch", respondeUsuario(role));
  } else {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("sem sessão")));
  }

  render(
    <MemoryRouter initialEntries={[rota]}>
      <AuthProvider>
        <Routes>
          <Route path="/entrar" element={<h1>Tela de entrada</h1>} />
          <Route
            path="/organizador"
            element={
              <ProtectedRoute permitido={["ORGANIZER"]}>
                <h1>Painel do organizador</h1>
              </ProtectedRoute>
            }
          />
          <Route
            path="/portaria"
            element={
              <ProtectedRoute permitido={["GATE"]}>
                <h1>Portaria</h1>
              </ProtectedRoute>
            }
          />
          <Route path="/em-cartaz" element={<h1>Em cartaz</h1>} />
          <Route path="/meus-ingressos" element={<h1>Meus ingressos</h1>} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("ProtectedRoute", () => {
  beforeEach(() => tokenStorage.clear());

  it("deixa passar quem tem o papel certo", async () => {
    monta({ role: "ORGANIZER" });
    expect(await screen.findByText("Painel do organizador")).toBeInTheDocument();
  });

  it("manda para o login quem não entrou", async () => {
    monta({ role: null });
    expect(await screen.findByText("Tela de entrada")).toBeInTheDocument();
  });

  it("papel errado vai para a própria área, não para o login", async () => {
    // Mandar alguém já autenticado para a tela de entrar é confuso: parece que
    // a sessão caiu. O certo é levar para onde essa pessoa pode ir.
    monta({ role: "CUSTOMER" });

    expect(await screen.findByText("Em cartaz")).toBeInTheDocument();
    expect(screen.queryByText("Tela de entrada")).not.toBeInTheDocument();
  });

  it("portaria tentando o painel do organizador vai para a portaria", async () => {
    monta({ role: "GATE" });
    expect(await screen.findByText("Portaria")).toBeInTheDocument();
  });

  it("cliente entra na própria área", async () => {
    monta({ role: "CUSTOMER", rota: "/meus-ingressos" });
    expect(await screen.findByText("Meus ingressos")).toBeInTheDocument();
  });

  it("token inválido é descartado, e não deixa a sessão em limbo", async () => {
    tokenStorage.set("token-podre");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
        json: async () => ({ detail: "Token inválido ou expirado" }),
      } as Response),
    );

    render(
      <MemoryRouter initialEntries={["/organizador"]}>
        <AuthProvider>
          <Routes>
            <Route path="/entrar" element={<h1>Tela de entrada</h1>} />
            <Route
              path="/organizador"
              element={
                <ProtectedRoute permitido={["ORGANIZER"]}>
                  <h1>Painel do organizador</h1>
                </ProtectedRoute>
              }
            />
          </Routes>
        </AuthProvider>
      </MemoryRouter>,
    );

    expect(await screen.findByText("Tela de entrada")).toBeInTheDocument();
    await waitFor(() => expect(tokenStorage.get()).toBeNull());
  });

  it("enquanto verifica a sessão, não decide nada", () => {
    // Sem esta espera, quem recarrega a página seria jogado no login antes de
    // o servidor confirmar quem é.
    tokenStorage.set("token-valido");
    vi.stubGlobal("fetch", vi.fn(() => new Promise(() => {})));

    monta({ role: null, rota: "/organizador" });

    expect(screen.queryByText("Tela de entrada")).not.toBeInTheDocument();
    expect(screen.queryByText("Painel do organizador")).not.toBeInTheDocument();
  });
});
