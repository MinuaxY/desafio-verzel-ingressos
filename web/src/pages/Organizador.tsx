import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { ApiError, request } from "../lib/api";
import { dataHora, faixaDePreco } from "../lib/formato";
import type { SessionDetail } from "../lib/tipos";
import { Carregando } from "../components/Carregando";
import { Classificacao, SelosDaSessao } from "../components/Selos";

const SITUACAO = {
  DRAFT: { rotulo: "Rascunho", classe: "selo--rascunho" },
  PUBLISHED: { rotulo: "Publicada", classe: "selo--publicada" },
  CANCELLED: { rotulo: "Cancelada", classe: "selo--cancelada" },
};

export function Organizador() {
  const [sessoes, setSessoes] = useState<SessionDetail[] | null>(null);
  const [erro, setErro] = useState("");
  const [agindo, setAgindo] = useState("");

  function carregar() {
    request<SessionDetail[]>("/organizer/sessions")
      .then(setSessoes)
      .catch((e) => setErro(e.message));
  }

  useEffect(carregar, []);

  async function excluir(s: SessionDetail) {
    if (
      !window.confirm(
        `Excluir a sessão de ${s.movie.title}? Isso apaga o rascunho de vez.`,
      )
    )
      return;

    setAgindo(s.id);
    setErro("");
    try {
      await request(`/organizer/sessions/${s.id}`, { method: "DELETE" });
      setSessoes((atual) => atual?.filter((x) => x.id !== s.id) ?? null);
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : "Não foi possível excluir.");
    } finally {
      setAgindo("");
    }
  }

  async function acao(id: string, caminho: string, confirmacao?: string) {
    if (confirmacao && !window.confirm(confirmacao)) return;

    setAgindo(id);
    setErro("");
    try {
      const atualizada = await request<SessionDetail>(`/organizer/sessions/${id}/${caminho}`, {
        method: "POST",
      });
      setSessoes((atual) => atual?.map((s) => (s.id === id ? atualizada : s)) ?? null);
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : "Não foi possível concluir.");
    } finally {
      setAgindo("");
    }
  }

  if (!sessoes && !erro) return <Carregando texto="Carregando suas sessões" />;

  return (
    <section className="stack" style={{ gap: "var(--space-6)" }}>
      <header className="cabecalho-acao">
        <div className="stack" style={{ gap: "var(--space-2)" }}>
          <h1>Minhas sessões</h1>
          <p className="muted">Publique uma sessão e ela entra no cartaz na hora.</p>
        </div>
        <div className="cabecalho-acao__botoes">
          <Link className="btn btn--ghost" to="/organizador/salas">
            Salas
          </Link>
          <Link className="btn btn--primary" to="/organizador/nova-sessao">
            Nova sessão
          </Link>
        </div>
      </header>

      {erro && (
        <p className="alert alert--error" role="alert">
          {erro}
        </p>
      )}

      {sessoes && sessoes.length === 0 ? (
        <div className="vazio">
          <p style={{ fontWeight: 600 }}>Nenhuma sessão ainda</p>
          <p className="muted" style={{ fontSize: "var(--text-sm)" }}>
            Escolha um filme do catálogo, defina sala, horário e preço.
          </p>
          <Link className="btn btn--primary" to="/organizador/nova-sessao">
            Criar a primeira
          </Link>
        </div>
      ) : (
        <ul className="lista-sessoes">
          {sessoes?.map((s) => {
            const situacao = SITUACAO[s.status];
            const ocupado = agindo === s.id;

            return (
              <li key={s.id} className="linha-sessao">
                {s.movie.poster_url && (
                  <img className="linha-sessao__poster" src={s.movie.poster_url} alt="" />
                )}

                <div className="stack" style={{ gap: "var(--space-1)", minWidth: 0, flex: 1 }}>
                  <div className="linha-sessao__topo">
                    <h2 className="linha-sessao__titulo">{s.movie.title}</h2>
                    <span className={`selo ${situacao.classe}`}>{situacao.rotulo}</span>
                  </div>
                  <p className="linha-sessao__quando">{dataHora(s.starts_at)}</p>
                  <p className="muted" style={{ fontSize: "var(--text-sm)" }}>
                    {s.room_name} · {s.capacity} lugares ·{" "}
                    {faixaDePreco(s.min_price_cents, s.max_price_cents)}
                  </p>
                  <div className="ficha">
                    <Classificacao valor={s.movie.age_rating} tamanho="mini" />
                    <SelosDaSessao audio={s.audio} formato={s.screen_format} />
                  </div>
                </div>

                <div className="linha-sessao__acoes">
                  {s.status !== "CANCELLED" && (
                    <Link
                      className="btn btn--ghost btn--mini"
                      to={`/organizador/sessao/${s.id}`}
                    >
                      Editar
                    </Link>
                  )}

                  {s.status === "PUBLISHED" && (
                    <>
                      <Link className="btn btn--ghost btn--mini" to={`/sessao/${s.id}`}>
                        Ver no cartaz
                      </Link>
                      <button
                        className="btn btn--ghost btn--mini"
                        type="button"
                        disabled={ocupado}
                        onClick={() => acao(s.id, "unpublish")}
                      >
                        Despublicar
                      </button>
                    </>
                  )}

                  {s.status === "DRAFT" && (
                    <>
                      <button
                        className="btn btn--primary btn--mini"
                        type="button"
                        disabled={ocupado}
                        onClick={() => acao(s.id, "publish")}
                      >
                        Publicar
                      </button>
                      {/* Excluir só aparece em rascunho: publicada sai do
                          cartaz com despublicar, e sessão com ingresso
                          vendido não some. Ver decisão D28. */}
                      <button
                        className="btn btn--ghost btn--mini btn--perigo"
                        type="button"
                        disabled={ocupado}
                        onClick={() => excluir(s)}
                      >
                        Excluir
                      </button>
                    </>
                  )}

                  {s.status !== "CANCELLED" && (
                    <button
                      className="btn btn--ghost btn--mini btn--perigo"
                      type="button"
                      disabled={ocupado}
                      onClick={() =>
                        acao(
                          s.id,
                          "cancel",
                          `Cancelar a sessão de ${s.movie.title}? Isso não pode ser desfeito.`,
                        )
                      }
                    >
                      Cancelar
                    </button>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
