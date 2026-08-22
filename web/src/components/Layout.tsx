import { Link, NavLink, Outlet } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { NOME_DO_PAPEL } from "../auth/types";
import type { Role } from "../auth/types";
import { Marca } from "./Marca";

/** O que cada papel enxerga na navegação. Visitante sem conta vê só o cartaz. */
const MENU: Record<Role, { para: string; rotulo: string }[]> = {
  CUSTOMER: [
    { para: "/em-cartaz", rotulo: "Em cartaz" },
    { para: "/meus-ingressos", rotulo: "Meus ingressos" },
  ],
  ORGANIZER: [
    { para: "/organizador", rotulo: "Sessões" },
    { para: "/organizador/salas", rotulo: "Salas" },
    { para: "/em-cartaz", rotulo: "Cartaz" },
  ],
  GATE: [{ para: "/portaria", rotulo: "Portaria" }],
};

export function Layout() {
  const { user, sair } = useAuth();
  const itens = user
    ? MENU[user.role]
    : [
        { para: "/", rotulo: "Início" },
        { para: "/em-cartaz", rotulo: "Em cartaz" },
      ];

  return (
    <div className="app">
      <header className="topo">
        <div className="topo__interno">
          <div className="topo__esquerda">
            <Link to="/" aria-label="Início">
              <Marca tamanho={24} />
            </Link>

            <nav className="menu" aria-label="Navegação principal">
              {itens.map((i) => (
                <NavLink
                  key={i.para}
                  to={i.para}
                  className={({ isActive }) => (isActive ? "menu__item menu__item--ativo" : "menu__item")}
                  end={i.para === "/organizador" || i.para === "/"}
                >
                  {i.rotulo}
                </NavLink>
              ))}
            </nav>
          </div>

          {user ? (
            <div className="topo__conta">
              <span className="topo__papel">{NOME_DO_PAPEL[user.role]}</span>
              <span className="muted topo__nome">{user.name}</span>
              <button type="button" className="btn btn--ghost topo__sair" onClick={sair}>
                Sair
              </button>
            </div>
          ) : (
            // Visitante: entrar e criar conta ficam no canto superior direito.
            <div className="topo__conta">
              <Link className="btn btn--ghost topo__sair" to="/entrar">
                Entrar
              </Link>
              <Link className="btn btn--primary topo__sair" to="/criar-conta">
                Criar conta
              </Link>
            </div>
          )}
        </div>
      </header>

      <main className="conteudo">
        <Outlet />
      </main>

      <footer className="rodape">
        <span className="faint">
          Verzel Ingressos — projeto do Desafio Elite Dev. Pagamentos são simulados.
        </span>
      </footer>
    </div>
  );
}
