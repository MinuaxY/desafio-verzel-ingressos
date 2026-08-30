import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { request } from "../lib/api";
import { dataHora, duracao, faixaDePreco } from "../lib/formato";
import type { DayInCartaz, SessionPage } from "../lib/tipos";
import { Carregando } from "../components/Carregando";
import { Classificacao, SelosDaSessao } from "../components/Selos";
import { BarraDeDias } from "../components/BarraDeDias";

/**
 * Vitrine pública. Não exige conta: quem procura sessão precisa ver o que
 * está em cartaz antes de decidir se cria cadastro. Ver decisão D10.
 */
export function EmCartaz() {
  const [params, setParams] = useSearchParams();
  const busca = params.get("busca") ?? "";
  const dia = params.get("dia");

  const [termo, setTermo] = useState(busca);
  const [pagina, setPagina] = useState<SessionPage | null>(null);
  const [dias, setDias] = useState<DayInCartaz[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");

  useEffect(() => {
    setCarregando(true);
    const query = new URLSearchParams();
    if (busca) query.set("search", busca);
    if (dia) query.set("day", dia);
    const sufixo = query.toString() ? `?${query}` : "";

    request<SessionPage>(`/sessions${sufixo}`, { auth: false })
      .then((r) => {
        setPagina(r);
        setErro("");
      })
      .catch((e) => setErro(e.message))
      .finally(() => setCarregando(false));
  }, [busca, dia]);

  // A barra de datas acompanha a busca, mas não o dia escolhido: ela precisa
  // continuar mostrando os outros dias para dar como voltar.
  useEffect(() => {
    const query = busca ? `?search=${encodeURIComponent(busca)}` : "";
    request<DayInCartaz[]>(`/sessions/days${query}`, { auth: false })
      .then(setDias)
      .catch(() => setDias([]));
  }, [busca]);

  /** Mexe num filtro preservando o outro. */
  function ajustar(mudanca: { busca?: string | null; dia?: string | null }) {
    const novo = new URLSearchParams(params);
    for (const [chave, valor] of Object.entries(mudanca)) {
      if (valor) novo.set(chave, valor);
      else novo.delete(chave);
    }
    setParams(novo);
  }

  function buscar(e: React.FormEvent) {
    e.preventDefault();
    ajustar({ busca: termo.trim() || null });
  }

  return (
    <section className="stack" style={{ gap: "var(--space-6)" }}>
      <header className="stack" style={{ gap: "var(--space-4)" }}>
        <div className="stack" style={{ gap: "var(--space-2)" }}>
          <h1>Em cartaz</h1>
          <p className="muted">Escolha a sessão, o lugar é seu.</p>
        </div>

        <form className="busca" onSubmit={buscar} role="search">
          <input
            className="field__input busca__campo"
            type="search"
            name="busca"
            placeholder="Buscar por filme"
            aria-label="Buscar sessões por filme"
            value={termo}
            onChange={(e) => setTermo(e.target.value)}
          />
          <button className="btn btn--primary" type="submit">
            Buscar
          </button>
          {busca && (
            <button
              className="btn btn--ghost"
              type="button"
              onClick={() => {
                setTermo("");
                ajustar({ busca: null });
              }}
            >
              Limpar
            </button>
          )}
        </form>

        <BarraDeDias
          dias={dias}
          selecionado={dia}
          onSelecionar={(d) => ajustar({ dia: d })}
        />
      </header>

      {erro && (
        <p className="alert alert--error" role="alert">
          {erro}
        </p>
      )}

      {carregando ? (
        <Carregando texto="Buscando sessões" />
      ) : !pagina || pagina.items.length === 0 ? (
        <div className="vazio">
          <p style={{ fontWeight: 600 }}>
            {busca
              ? `Nada em cartaz para "${busca}"`
              : dia
                ? "Nenhuma sessão neste dia"
                : "Nenhuma sessão em cartaz"}
          </p>
          <p className="muted" style={{ fontSize: "var(--text-sm)" }}>
            {busca
              ? "Tente outro termo, ou veja tudo que está disponível."
              : dia
                ? "Escolha outro dia na barra acima."
                : "Assim que o organizador publicar uma sessão, ela aparece aqui."}
          </p>
        </div>
      ) : (
        <>
          <p className="faint" style={{ fontSize: "var(--text-sm)" }}>
            {pagina.total} {pagina.total === 1 ? "sessão" : "sessões"}
          </p>

          <ul className="cartazes">
            {pagina.items.map((s) => (
              <li key={s.id}>
                <Link to={`/sessao/${s.id}`} className="cartaz">
                  <div className="cartaz__arte">
                    {s.poster_url ? (
                      <img src={s.poster_url} alt="" loading="lazy" />
                    ) : (
                      <span className="cartaz__sem-arte" aria-hidden="true">
                        🎬
                      </span>
                    )}
                    <Classificacao valor={s.age_rating} tamanho="mini" />
                  </div>

                  <div className="cartaz__info">
                    <h2 className="cartaz__titulo">{s.title}</h2>
                    <p className="faint" style={{ fontSize: "var(--text-xs)" }}>
                      {[s.year, duracao(s.runtime_minutes)].filter(Boolean).join(" · ")}
                    </p>
                    <SelosDaSessao audio={s.audio} formato={s.screen_format} />
                    <p className="cartaz__quando">{dataHora(s.starts_at)}</p>
                    <p className="muted" style={{ fontSize: "var(--text-sm)" }}>
                      {s.room_name}
                    </p>
                    <p className="cartaz__preco">
                      {faixaDePreco(s.min_price_cents, s.max_price_cents)}
                    </p>
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
