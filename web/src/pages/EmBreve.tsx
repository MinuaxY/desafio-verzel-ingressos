import { useAuth } from "../auth/AuthContext";

/**
 * Área de cada papel, ainda sem conteúdo.
 *
 * Existe para que a navegação por papel esteja de pé e verificável desde a
 * Sprint 1: cada usuário chega ao próprio lugar e não entra no dos outros.
 * O conteúdo entra nas sprints seguintes.
 */
export function EmBreve({
  titulo,
  descricao,
  sprint,
}: {
  titulo: string;
  descricao: string;
  sprint: string;
}) {
  const { user } = useAuth();

  return (
    <section className="stack" style={{ gap: "var(--space-5)", maxWidth: "60ch" }}>
      <div className="stack" style={{ gap: "var(--space-3)" }}>
        <h1>{titulo}</h1>
        <p className="muted">{descricao}</p>
      </div>

      <div className="aviso-obra">
        <span className="aviso-obra__etiqueta">{sprint}</span>
        <p className="muted" style={{ fontSize: "var(--text-sm)" }}>
          Esta área ainda não foi construída. A autenticação e a separação por papel já
          funcionam: você está autenticado como <strong>{user?.email}</strong> e só enxerga o
          que o seu papel permite.
        </p>
      </div>
    </section>
  );
}
