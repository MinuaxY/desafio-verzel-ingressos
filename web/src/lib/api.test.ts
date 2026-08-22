import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, request, tokenStorage } from "./api";

function respondeCom(corpo: unknown, status = 200) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => corpo,
  } as Response);
}

describe("tokenStorage", () => {
  it("guarda, lê e apaga o token", () => {
    expect(tokenStorage.get()).toBeNull();
    tokenStorage.set("abc123");
    expect(tokenStorage.get()).toBe("abc123");
    tokenStorage.clear();
    expect(tokenStorage.get()).toBeNull();
  });
});

describe("request", () => {
  beforeEach(() => tokenStorage.clear());

  it("envia o token quando existe", async () => {
    const fetchFalso = respondeCom({ ok: true });
    vi.stubGlobal("fetch", fetchFalso);
    tokenStorage.set("meu-token");

    await request("/auth/me");

    const [, opcoes] = fetchFalso.mock.calls[0];
    expect(opcoes.headers.Authorization).toBe("Bearer meu-token");
  });

  it("não envia token em rota pública", async () => {
    const fetchFalso = respondeCom({ items: [] });
    vi.stubGlobal("fetch", fetchFalso);
    tokenStorage.set("meu-token");

    await request("/sessions", { auth: false });

    const [, opcoes] = fetchFalso.mock.calls[0];
    expect(opcoes.headers.Authorization).toBeUndefined();
  });

  it("serializa o corpo e marca o tipo do conteúdo", async () => {
    const fetchFalso = respondeCom({ id: "1" }, 201);
    vi.stubGlobal("fetch", fetchFalso);

    await request("/orders", { method: "POST", body: { session_id: "x" } });

    const [, opcoes] = fetchFalso.mock.calls[0];
    expect(opcoes.method).toBe("POST");
    expect(opcoes.headers["Content-Type"]).toBe("application/json");
    expect(JSON.parse(opcoes.body)).toEqual({ session_id: "x" });
  });

  it("204 devolve vazio sem tentar interpretar o corpo", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 204 } as Response));
    await expect(request("/algo")).resolves.toBeUndefined();
  });
});

describe("tradução de erro", () => {
  it("usa o detail do FastAPI quando é texto", async () => {
    vi.stubGlobal("fetch", respondeCom({ detail: "Sessão não encontrada" }, 404));

    await expect(request("/sessions/x")).rejects.toThrow("Sessão não encontrada");
  });

  it("usa a primeira mensagem quando o detail é lista de validação", async () => {
    // O FastAPI devolve array de objetos para erro de validação; sem esta
    // tradução, a tela mostraria "[object Object]".
    vi.stubGlobal(
      "fetch",
      respondeCom({ detail: [{ loc: ["body", "email"], msg: "e-mail inválido" }] }, 422),
    );

    await expect(request("/auth/register", { method: "POST", body: {} })).rejects.toThrow(
      "e-mail inválido",
    );
  });

  it("erro de servidor tem mensagem genérica, não corpo cru", async () => {
    vi.stubGlobal("fetch", respondeCom({}, 500));
    await expect(request("/algo")).rejects.toThrow(/servidor encontrou um erro/i);
  });

  it("servidor fora do ar vira frase legível, não 'Failed to fetch'", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));

    await expect(request("/sessions")).rejects.toThrow(/não foi possível falar com o servidor/i);
  });

  it("o status vem junto, para a tela reagir ao caso", async () => {
    // 401 manda para o login; 409 recarrega o mapa de assentos. Sem o status,
    // toda falha viraria a mesma mensagem genérica.
    vi.stubGlobal("fetch", respondeCom({ detail: "poltrona ocupada" }, 409));

    await expect(request("/orders", { method: "POST", body: {} })).rejects.toMatchObject({
      status: 409,
      name: "ApiError",
    });
  });

  it("falha de rede tem status 0, distinguível de erro do servidor", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));

    await request("/x").catch((e) => {
      expect(e).toBeInstanceOf(ApiError);
      expect(e.status).toBe(0);
    });
  });
});
