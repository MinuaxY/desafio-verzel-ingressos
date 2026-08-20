import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import { ApiError, request, tokenStorage } from "../lib/api";
import type { Role, TokenResponse, User } from "./types";

interface AuthContextValue {
  user: User | null;
  carregando: boolean;
  login: (email: string, password: string) => Promise<User>;
  registrar: (dados: {
    name: string;
    email: string;
    password: string;
    role: Role;
  }) => Promise<User>;
  sair: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  // Começa carregando: existe um token no storage e ainda não sabemos se
  // vale. Renderizar as rotas antes disso jogaria o usuário no login a cada
  // recarga de página.
  const [carregando, setCarregando] = useState(true);

  useEffect(() => {
    const token = tokenStorage.get();
    if (!token) {
      setCarregando(false);
      return;
    }
    request<User>("/auth/me")
      .then(setUser)
      .catch(() => tokenStorage.clear())
      .finally(() => setCarregando(false));
  }, []);

  const autenticar = useCallback(async (path: string, body: unknown) => {
    const resposta = await request<TokenResponse>(path, { method: "POST", body, auth: false });
    tokenStorage.set(resposta.access_token);
    setUser(resposta.user);
    return resposta.user;
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      carregando,
      login: (email, password) => autenticar("/auth/login", { email, password }),
      registrar: (dados) => autenticar("/auth/register", dados),
      sair: () => {
        tokenStorage.clear();
        setUser(null);
      },
    }),
    [user, carregando, autenticar],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth precisa estar dentro de AuthProvider");
  return ctx;
}

export { ApiError };
