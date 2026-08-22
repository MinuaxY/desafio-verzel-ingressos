import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { request } from "../lib/api";
import type { TicketDetail } from "../lib/tipos";
import { Carregando } from "../components/Carregando";
import { Ingresso } from "../components/Ingresso";

export function MeusIngressos() {
  const [ingressos, setIngressos] = useState<TicketDetail[] | null>(null);
  const [erro, setErro] = useState("");

  useEffect(() => {
    request<TicketDetail[]>("/me/tickets")
      .then(setIngressos)
      .catch((e) => setErro(e.message));
  }, []);

  if (!ingressos && !erro) return <Carregando texto="Carregando seus ingressos" />;

  // Ingresso já utilizado desce para o fim: o que interessa é o próximo.
  const ordenados = [...(ingressos ?? [])].sort((a, b) => {
    const usado = Number(a.status === "USED") - Number(b.status === "USED");
    return usado !== 0 ? usado : a.starts_at.localeCompare(b.starts_at);
  });

  return (
    <section className="stack" style={{ gap: "var(--space-6)" }}>
      <header className="stack" style={{ gap: "var(--space-2)" }}>
        <h1>Meus ingressos</h1>
        <p className="muted">Apresente o código na entrada.</p>
      </header>

      {erro && (
        <p className="alert alert--error" role="alert">
          {erro}
        </p>
      )}

      {ordenados.length === 0 ? (
        <div className="vazio">
          <p style={{ fontWeight: 600 }}>Você ainda não tem ingressos</p>
          <p className="muted" style={{ fontSize: "var(--text-sm)" }}>
            Escolha uma sessão e garanta o seu lugar.
          </p>
          <Link className="btn btn--primary" to="/em-cartaz">
            Ver o que está em cartaz
          </Link>
        </div>
      ) : (
        <div className="stack" style={{ gap: "var(--space-5)" }}>
          {ordenados.map((i) => (
            <Ingresso key={i.id} ingresso={i} comLinkDoPedido />
          ))}
        </div>
      )}
    </section>
  );
}
