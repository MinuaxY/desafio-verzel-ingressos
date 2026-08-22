import { useState } from "react";

import { dataHora } from "../lib/formato";
import { ASSENTO } from "../lib/tipos";
import type { TicketDetail } from "../lib/tipos";
import { QRCode } from "./QRCode";

/**
 * O ingresso propriamente dito.
 *
 * O recorte entre o talão e o canhoto é a mesma ideia da marca: um ingresso de
 * papel picotado na entrada. O QR fica no canhoto, que é a parte que a
 * portaria lê.
 */
export function Ingresso({
  ingresso,
  compartilhavel = true,
}: {
  ingresso: TicketDetail;
  compartilhavel?: boolean;
}) {
  const [copiado, setCopiado] = useState<"link" | "codigo" | null>(null);
  const usado = ingresso.status === "USED";
  const tipo = ingresso.seat_kind ? ASSENTO[ingresso.seat_kind] : null;

  const linkPublico = ingresso.share_token
    ? `${window.location.origin}/ingresso/${ingresso.share_token}`
    : null;

  async function copiar(texto: string, qual: "link" | "codigo") {
    try {
      await navigator.clipboard.writeText(texto);
      setCopiado(qual);
      setTimeout(() => setCopiado(null), 2000);
    } catch {
      // Área de transferência bloqueada pelo navegador. O valor está visível
      // na tela de qualquer forma, então não vale interromper com um erro.
    }
  }

  return (
    <article className={usado ? "ingresso ingresso--usado" : "ingresso"}>
      <div className="ingresso__talao">
        {ingresso.movie_poster_url && (
          <img className="ingresso__poster" src={ingresso.movie_poster_url} alt="" />
        )}

        <div className="stack" style={{ gap: "var(--space-2)", minWidth: 0 }}>
          <h3 className="ingresso__filme">{ingresso.movie_title}</h3>
          <p className="ingresso__quando">{dataHora(ingresso.starts_at)}</p>
          <p className="muted" style={{ fontSize: "var(--text-sm)" }}>
            {ingresso.room_name}
            {ingresso.room_location && ` — ${ingresso.room_location}`}
          </p>

          <p className="ingresso__lugar">
            <span className="faint">{ingresso.sector_name}</span>
            <strong>{ingresso.seat_code}</strong>
            {tipo && <span className="etiqueta-acessivel">{tipo.rotulo}</span>}
          </p>

          {usado && (
            <p className="ingresso__carimbo">
              Utilizado{ingresso.used_at && ` em ${dataHora(ingresso.used_at)}`}
            </p>
          )}
        </div>
      </div>

      <div className="ingresso__canhoto">
        {ingresso.code ? (
          <>
            <QRCode valor={ingresso.code} tamanho={168} />
            <code className="ingresso__codigo">{ingresso.code}</code>

            <div className="ingresso__acoes">
              <button
                type="button"
                className="btn btn--ghost btn--mini"
                onClick={() => copiar(ingresso.code!, "codigo")}
              >
                {copiado === "codigo" ? "Copiado" : "Copiar código"}
              </button>

              {compartilhavel && linkPublico && (
                <button
                  type="button"
                  className="btn btn--ghost btn--mini"
                  onClick={() => copiar(linkPublico, "link")}
                >
                  {copiado === "link" ? "Copiado" : "Copiar link"}
                </button>
              )}
            </div>
          </>
        ) : (
          <p className="faint" style={{ fontSize: "var(--text-sm)", textAlign: "center" }}>
            O código aparece depois do pagamento.
          </p>
        )}
      </div>
    </article>
  );
}
