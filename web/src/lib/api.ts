/**
 * Cliente HTTP da API.
 *
 * Concentra num lugar só o que toda chamada precisa: URL base, token e a
 * tradução do erro. O resto do app não monta requisição na mão.
 */
const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const TOKEN_KEY = "verzel.token";

export const tokenStorage = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t: string) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

/** Erro da API já traduzido. `status` permite reagir ao caso: 401 manda para
 *  o login, 403 mostra acesso negado, e assim por diante. */
export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

type Options = { method?: string; body?: unknown; auth?: boolean };

export async function request<T>(path: string, options: Options = {}): Promise<T> {
  const { method = "GET", body, auth = true } = options;

  const headers: Record<string, string> = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";

  const token = tokenStorage.get();
  if (auth && token) headers["Authorization"] = `Bearer ${token}`;

  let response: Response;
  try {
    response = await fetch(`${BASE}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    // Servidor fora do ar ou sem rede. Sem essa tradução o usuário veria
    // "Failed to fetch", que não diz nada a ninguém.
    throw new ApiError(0, "Não foi possível falar com o servidor. Ele está no ar?");
  }

  if (response.status === 204) return undefined as T;

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    throw new ApiError(response.status, extrairMensagem(data, response.status));
  }
  return data as T;
}

/** O FastAPI usa `detail` para erro simples e um array de objetos para falha
 *  de validação. Os dois viram uma frase legível. */
function extrairMensagem(data: unknown, status: number): string {
  const detail = (data as { detail?: unknown } | null)?.detail;

  if (typeof detail === "string") return detail;

  if (Array.isArray(detail)) {
    const primeiro = detail[0] as { msg?: string } | undefined;
    if (primeiro?.msg) return primeiro.msg;
  }

  if (status >= 500) return "O servidor encontrou um erro. Tente novamente.";
  return "Não foi possível completar a operação.";
}
