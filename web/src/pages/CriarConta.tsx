import { useState } from "react";
import type { FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { HOME_POR_PAPEL, NOME_DO_PAPEL } from "../auth/types";
import type { Role } from "../auth/types";
import { ApiError } from "../lib/api";
import { Campo } from "../components/Campo";
import { Marca } from "../components/Marca";

const SENHA_MINIMA = 8;

/** Portaria fica de fora: e conta operacional, criada por quem administra o
 *  cinema, nao por autocadastro. */
const PAPEIS_PUBLICOS: Role[] = ["CUSTOMER", "ORGANIZER"];

const DESCRICAO: Record<string, string> = {
  CUSTOMER: "Quero comprar ingressos",
  ORGANIZER: "Quero publicar sessões",
};

export function CriarConta() {
  const { user, registrar } = useAuth();
  const navigate = useNavigate();

  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
    role: "CUSTOMER" as Role,
  });
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);

  if (user) return <Navigate to={HOME_POR_PAPEL[user.role]} replace />;

  const senhaCurta = form.password.length > 0 && form.password.length < SENHA_MINIMA;

  async function enviar(e: FormEvent) {
    e.preventDefault();
    setErro("");
    setEnviando(true);
    try {
      const criado = await registrar(form);
      navigate(HOME_POR_PAPEL[criado.role], { replace: true });
    } catch (err) {
      setErro(err instanceof ApiError ? err.message : "Não foi possível criar a conta.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <main className="entrada">
      <div className="entrada__cartao">
        <Marca />

        <div className="stack" style={{ gap: "var(--space-2)", marginTop: "var(--space-6)" }}>
          <h1 style={{ fontSize: "var(--text-2xl)" }}>Criar conta</h1>
          <p className="muted" style={{ fontSize: "var(--text-sm)" }}>
            Leva menos de um minuto.
          </p>
        </div>

        <form
          className="stack"
          style={{ gap: "var(--space-4)", marginTop: "var(--space-6)" }}
          onSubmit={enviar}
        >
          {erro && (
            <p className="alert alert--error" role="alert">
              {erro}
            </p>
          )}

          <Campo
            label="Nome"
            name="name"
            required
            minLength={2}
            autoComplete="name"
            placeholder="Como devemos te chamar"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />

          <Campo
            label="E-mail"
            name="email"
            type="email"
            required
            autoComplete="email"
            placeholder="voce@exemplo.com"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
          />

          <Campo
            label="Senha"
            name="password"
            type="password"
            required
            minLength={SENHA_MINIMA}
            autoComplete="new-password"
            placeholder={"No mínimo " + SENHA_MINIMA + " caracteres"}
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            erro={senhaCurta ? "A senha precisa de ao menos " + SENHA_MINIMA + " caracteres." : undefined}
          />

          <fieldset className="papeis">
            <legend className="field__label">Como você vai usar</legend>
            {PAPEIS_PUBLICOS.map((papel) => (
              <label
                key={papel}
                className={form.role === papel ? "papeis__opcao papeis__opcao--ativa" : "papeis__opcao"}
              >
                <input
                  type="radio"
                  name="role"
                  value={papel}
                  className="sr-only"
                  checked={form.role === papel}
                  onChange={() => setForm({ ...form, role: papel })}
                />
                <span style={{ fontWeight: 600 }}>{NOME_DO_PAPEL[papel]}</span>
                <span className="faint" style={{ fontSize: "var(--text-xs)" }}>
                  {DESCRICAO[papel]}
                </span>
              </label>
            ))}
          </fieldset>

          <button className="btn btn--primary btn--block" type="submit" disabled={enviando}>
            {enviando ? "Criando…" : "Criar conta"}
          </button>
        </form>

        <p className="muted" style={{ fontSize: "var(--text-sm)", marginTop: "var(--space-5)" }}>
          Já tem conta? <Link to="/entrar">Entrar</Link>
        </p>
      </div>
    </main>
  );
}
