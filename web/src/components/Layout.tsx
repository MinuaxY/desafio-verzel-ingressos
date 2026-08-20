import { Link, Outlet } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { HOME_POR_PAPEL, NOME_DO_PAPEL } from "../auth/types";
import { Marca } from "./Marca";

/** Moldura das telas autenticadas: identidade, quem está logado e a saída. */
export function Layout() {
  const { user, sair } = useAuth();

  return (
    <div className="app">
      <header className="topo">
        <div className="topo__interno">
          <Link to={user ? HOME_POR_PAPEL[user.role] : "/"} aria-label="Início">
            <Marca tamanho={24} />
          </Link>

          {user && (
            <div className="topo__conta">
              <span className="topo__papel">{NOME_DO_PAPEL[user.role]}</span>
              <span className="muted" style={{ fontSize: "var(--text-sm)" }}>
                {user.name}
              </span>
              <button type="button" className="btn btn--ghost topo__sair" onClick={sair}>
                Sair
              </button>
            </div>
          )}
        </div>
      </header>

      <main className="conteudo">
        <Outlet />
      </main>
    </div>
  );
}
