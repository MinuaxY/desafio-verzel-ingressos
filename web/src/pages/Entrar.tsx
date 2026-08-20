import { useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { HOME_POR_PAPEL } from "../auth/types";
import { ApiError } from "../lib/api";
import { Campo } from "../components/Campo";
import { Marca } from "../components/Marca";

/** Contas criadas pelo seed. Ficam a mao porque o desafio pede que se possa
 *  percorrer o fluxo sem montar nada do zero. */
const DEMO = [
  { papel: "Organizador", email: "organizador@verzel.dev", faz: "cria sessões" },
  { papel: "Cliente", email: "cliente1@verzel.dev", faz: "compra ingressos" },
  { papel: "Portaria", email: "portaria@verzel.dev", faz: "valida na entrada" },
];
const SENHA_DEMO = "verzel123";

export function Entrar() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);

  if (user) return <Navigate to={HOME_POR_PAPEL[user.role]} replace />;

  async function entrar(comEmail: string, comSenha: string) {
    setErro("");
    setEnviando(true);
    try {
      const logado = await login(comEmail, comSenha);
      const destino = (location.state as { de?: string } | null)?.de;
      navigate(destino ?? HOME_POR_PAPEL[logado.role], { replace: true });
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : "Não foi possível entrar.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <main className="entrada">
      <div className="entrada__cartao">
        <Marca />

        <div className="stack" style={{ gap: "var(--space-2)", marginTop: "var(--space-6)" }}>
          <h1 style={{ fontSize: "var(--text-2xl)" }}>Entrar</h1>
          <p className="muted" style={{ fontSize: "var(--text-sm)" }}>
            Acesse para comprar ingressos ou gerenciar sessões.
          </p>
        </div>

        <form
          className="stack"
          style={{ gap: "var(--space-4)", marginTop: "var(--space-6)" }}
          onSubmit={(e) => {
            e.preventDefault();
            entrar(email, senha);
          }}
        >
          {erro && (
            <p className="alert alert--error" role="alert">
              {erro}
            </p>
          )}

          <Campo
            label="E-mail"
            name="email"
            type="email"
            autoComplete="email"
            required
            placeholder="voce@exemplo.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />

          <Campo
            label="Senha"
            name="senha"
            type="password"
            autoComplete="current-password"
            required
            placeholder="********"
            value={senha}
            onChange={(e) => setSenha(e.target.value)}
          />

          <button className="btn btn--primary btn--block" type="submit" disabled={enviando}>
            {enviando ? "Entrando…" : "Entrar"}
          </button>
        </form>

        <p className="muted" style={{ fontSize: "var(--text-sm)", marginTop: "var(--space-5)" }}>
          Ainda não tem conta? <Link to="/criar-conta">Criar conta</Link>
        </p>

        <div className="demo">
          <p className="demo__titulo">Acesso de demonstração</p>
          <div className="stack" style={{ gap: "var(--space-2)" }}>
            {DEMO.map((c) => (
              <button
                key={c.email}
                type="button"
                className="demo__opcao"
                disabled={enviando}
                onClick={() => entrar(c.email, SENHA_DEMO)}
              >
                <span className="demo__papel">{c.papel}</span>
                <span className="faint" style={{ fontSize: "var(--text-xs)" }}>
                  {c.faz}
                </span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </main>
  );
}
