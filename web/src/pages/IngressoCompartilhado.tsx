import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { request } from "../lib/api";
import type { TicketDetail } from "../lib/tipos";
import { Carregando } from "../components/Carregando";
import { Ingresso } from "../components/Ingresso";
import { Marca } from "../components/Marca";

/**
 * Ingresso aberto por link, sem conta.
 *
 * Fora do layout autenticado de propósito: quem chega aqui recebeu o link de
 * outra pessoa e não tem sessão nenhuma. Mostrar cabeçalho de conta e botão de
 * sair só confundiria.
 */
export function IngressoCompartilhado() {
  const { token = "" } = useParams();
  const [ingresso, setIngresso] = useState<TicketDetail | null>(null);
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState(true);

  useEffect(() => {
    request<TicketDetail>(`/shared/${token}`, { auth: false })
      .then(setIngresso)
      .catch((e) => setErro(e.message))
      .finally(() => setCarregando(false));
  }, [token]);

  return (
    <main className="compartilhado">
      <div className="compartilhado__interno">
        <Link to="/em-cartaz" aria-label="Início" style={{ alignSelf: "flex-start" }}>
          <Marca tamanho={22} />
        </Link>

        {carregando ? (
          <Carregando texto="Abrindo ingresso" />
        ) : ingresso ? (
          <>
            <div className="stack" style={{ gap: "var(--space-2)" }}>
              <h1 style={{ fontSize: "var(--text-xl)" }}>Ingresso compartilhado</h1>
              <p className="muted" style={{ fontSize: "var(--text-sm)" }}>
                Apresente este código na entrada. Ele vale para uma pessoa.
              </p>
            </div>

            {/* Sem botão de compartilhar de novo: quem chegou por link já tem o
                link, e repetir a ação só polui a tela. */}
            <Ingresso ingresso={ingresso} compartilhavel={false} />
          </>
        ) : (
          <div className="stack" style={{ gap: "var(--space-3)" }}>
            <h1 style={{ fontSize: "var(--text-xl)" }}>Ingresso não encontrado</h1>
            <p className="muted">{erro || "O link pode estar incorreto ou ter expirado."}</p>
            <Link className="btn btn--ghost" to="/em-cartaz" style={{ alignSelf: "flex-start" }}>
              Ver o que está em cartaz
            </Link>
          </div>
        )}
      </div>
    </main>
  );
}
