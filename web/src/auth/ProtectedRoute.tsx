import { Navigate, useLocation } from "react-router-dom";
import type { ReactNode } from "react";

import { useAuth } from "./AuthContext";
import { HOME_POR_PAPEL } from "./types";
import type { Role } from "./types";
import { Carregando } from "../components/Carregando";

/**
 * Restringe uma rota a determinados papéis.
 *
 * Não autenticado vai para o login, guardando de onde veio para voltar
 * depois. Autenticado com papel errado é levado à própria área, e não ao
 * login: mandar alguém logado para a tela de entrar é confuso e faz parecer
 * que a sessão caiu.
 *
 * Isto é conveniência de navegação, não segurança — quem garante o acesso é
 * a API, que responde 403 de qualquer forma.
 */
export function ProtectedRoute({
  children,
  permitido,
}: {
  children: ReactNode;
  permitido: Role[];
}) {
  const { user, carregando } = useAuth();
  const location = useLocation();

  if (carregando) return <Carregando />;

  if (!user) return <Navigate to="/entrar" state={{ de: location.pathname }} replace />;

  if (!permitido.includes(user.role)) {
    return <Navigate to={HOME_POR_PAPEL[user.role]} replace />;
  }

  return <>{children}</>;
}
