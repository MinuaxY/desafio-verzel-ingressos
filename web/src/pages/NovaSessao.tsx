import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { ApiError, request } from "../lib/api";
import { duracao, reais } from "../lib/formato";
import type { AudioType, CatalogItem, CatalogPage, Room, ScreenFormat, SessionDetail } from "../lib/tipos";
import { AUDIO, FORMATO } from "../lib/tipos";
import { Classificacao } from "../components/Selos";
import { Campo } from "../components/Campo";

/** Converte "32,00" ou "32.00" em centavos, sem passar por float. */
function paraCentavos(texto: string): number {
  const limpo = texto.replace(/[^\d,.]/g, "").replace(",", ".");
  if (!limpo) return 0;
  const [inteiros, decimais = ""] = limpo.split(".");
  return Number(inteiros || 0) * 100 + Number(decimais.padEnd(2, "0").slice(0, 2));
}

/** Horário local no formato que o input datetime-local usa, com fuso somado
 *  na hora de enviar — a API recusa horário sem fuso. Ver decisão D14. */
function comFuso(valorLocal: string): string {
  return new Date(valorLocal).toISOString();
}

export function NovaSessao() {
  const navigate = useNavigate();

  const [termo, setTermo] = useState("");
  const [resultados, setResultados] = useState<CatalogItem[] | null>(null);
  const [buscando, setBuscando] = useState(false);
  const [filme, setFilme] = useState<CatalogItem | null>(null);

  const [salas, setSalas] = useState<Room[]>([]);
  const [salaId, setSalaId] = useState("");
  const [quando, setQuando] = useState("");
  const [audio, setAudio] = useState<AudioType>("SUBTITLED");
  const [formato, setFormato] = useState<ScreenFormat>("TWO_D");
  const [precos, setPrecos] = useState<Record<string, string>>({});

  const [erro, setErro] = useState("");
  const [salvando, setSalvando] = useState(false);

  useEffect(() => {
    request<Room[]>("/rooms")
      .then((r) => {
        setSalas(r);
        if (r.length === 1) setSalaId(r[0].id);
      })
      .catch((e) => setErro(e.message));
  }, []);

  const sala = salas.find((s) => s.id === salaId) ?? null;

  async function buscar(e: React.FormEvent) {
    e.preventDefault();
    if (!termo.trim()) return;
    setBuscando(true);
    setErro("");
    try {
      const r = await request<CatalogPage>(`/catalog/search?q=${encodeURIComponent(termo)}`);
      setResultados(r.items);
    } catch (err) {
      setErro(err instanceof ApiError ? err.message : "Não foi possível buscar no catálogo.");
    } finally {
      setBuscando(false);
    }
  }

  async function criar(e: React.FormEvent, publicar: boolean) {
    e.preventDefault();
    if (!filme || !sala || !quando) return;

    setErro("");
    setSalvando(true);
    try {
      const sessao = await request<SessionDetail>("/organizer/sessions", {
        method: "POST",
        body: {
          catalog_id: filme.id,
          room_id: sala.id,
          starts_at: comFuso(quando),
          audio,
          screen_format: formato,
          prices: sala.sectors.map((s) => ({
            sector_id: s.id,
            price_cents: paraCentavos(precos[s.id] ?? ""),
          })),
          publish: publicar,
        },
      });
      navigate("/organizador", { state: { criada: sessao.id } });
    } catch (err) {
      setErro(err instanceof ApiError ? err.message : "Não foi possível criar a sessão.");
    } finally {
      setSalvando(false);
    }
  }

  const pronto = Boolean(
    filme && sala && quando && sala.sectors.every((s) => paraCentavos(precos[s.id] ?? "") > 0),
  );

  return (
    <section className="stack" style={{ gap: "var(--space-6)", maxWidth: "48rem" }}>
      <header className="stack" style={{ gap: "var(--space-2)" }}>
        <h1>Nova sessão</h1>
        <p className="muted">Escolha o filme, a sala, o horário e o preço de cada setor.</p>
      </header>

      {erro && (
        <p className="alert alert--error" role="alert">
          {erro}
        </p>
      )}

      {/* 1 — filme */}
      <div className="etapa">
        <h2 className="etapa__titulo">
          <span className="etapa__numero">1</span> Filme
        </h2>

        {filme ? (
          <div className="escolhido">
            {filme.poster_url && <img src={filme.poster_url} alt="" />}
            <div className="stack" style={{ gap: "var(--space-2)", flex: 1, minWidth: 0 }}>
              <strong>{filme.title}</strong>
              <span className="faint" style={{ fontSize: "var(--text-sm)" }}>
                {[filme.release_year, duracao(filme.runtime_minutes), filme.genres.join(", ")]
                  .filter(Boolean)
                  .join(" · ")}
              </span>
              <span className="ficha">
                <Classificacao valor={filme.age_rating ?? null} tamanho="mini" />
                <span className="faint" style={{ fontSize: "var(--text-xs)" }}>
                  classificação do catálogo
                </span>
              </span>
            </div>
            <button className="btn btn--ghost btn--mini" type="button" onClick={() => setFilme(null)}>
              Trocar
            </button>
          </div>
        ) : (
          <>
            <form className="busca" onSubmit={buscar}>
              <input
                className="field__input busca__campo"
                placeholder="Buscar filme no catálogo"
                aria-label="Buscar filme"
                value={termo}
                onChange={(e) => setTermo(e.target.value)}
              />
              <button className="btn btn--primary" type="submit" disabled={buscando}>
                {buscando ? "Buscando…" : "Buscar"}
              </button>
            </form>

            {resultados && resultados.length === 0 && (
              <p className="faint" style={{ fontSize: "var(--text-sm)" }}>
                Nada encontrado para "{termo}".
              </p>
            )}

            {resultados && resultados.length > 0 && (
              <ul className="resultados">
                {resultados.slice(0, 8).map((f) => (
                  <li key={f.id}>
                    <button type="button" className="resultado" onClick={() => setFilme(f)}>
                      {f.poster_url ? (
                        <img src={f.poster_url} alt="" loading="lazy" />
                      ) : (
                        <span className="resultado__sem-arte" aria-hidden="true">
                          🎬
                        </span>
                      )}
                      <span className="stack" style={{ gap: "2px", minWidth: 0 }}>
                        <strong className="resultado__titulo">{f.title}</strong>
                        <span className="faint" style={{ fontSize: "var(--text-xs)" }}>
                          {f.release_year ?? "—"}
                        </span>
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </>
        )}
      </div>

      {/* 2 — sala */}
      <div className="etapa">
        <h2 className="etapa__titulo">
          <span className="etapa__numero">2</span> Sala
        </h2>

        {salas.length === 0 ? (
          <div className="vazio" style={{ padding: "var(--space-5)" }}>
            <p style={{ fontWeight: 600 }}>Você ainda não tem salas</p>
            <p className="muted" style={{ fontSize: "var(--text-sm)" }}>
              A sala guarda o layout de poltronas e é reaproveitada por todas as sessões.
            </p>
            <Link className="btn btn--primary" to="/organizador/salas">
              Cadastrar sala
            </Link>
          </div>
        ) : (
          <div className="stack" style={{ gap: "var(--space-3)" }}>
            <div className="field">
              <label className="field__label" htmlFor="sala">
                Escolha a sala
              </label>
              <select
                id="sala"
                className="field__input"
                value={salaId}
                onChange={(e) => setSalaId(e.target.value)}
              >
                <option value="">Selecione…</option>
                {salas.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name} — {s.capacity} lugares
                  </option>
                ))}
              </select>
            </div>

            <Link className="link-discreto" to="/organizador/salas">
              A sala que preciso não está aqui — cadastrar outra
            </Link>
          </div>
        )}
      </div>

      {/* 3 — horario e precos */}
      <div className="etapa">
        <h2 className="etapa__titulo">
          <span className="etapa__numero">3</span> Exibição, horário e preços
        </h2>

        <div className="stack" style={{ gap: "var(--space-4)" }}>
          {/* Áudio e formato são desta sessão, não do filme: o mesmo título
              roda dublado às 16h e legendado às 21h. */}
          <div className="exibicao">
            <div className="field">
              <label className="field__label" htmlFor="audio">
                Áudio
              </label>
              <select
                id="audio"
                className="field__input"
                value={audio}
                onChange={(e) => setAudio(e.target.value as AudioType)}
              >
                {Object.entries(AUDIO).map(([v, rotulo]) => (
                  <option key={v} value={v}>
                    {rotulo}
                  </option>
                ))}
              </select>
            </div>

            <div className="field">
              <label className="field__label" htmlFor="formato">
                Formato de tela
              </label>
              <select
                id="formato"
                className="field__input"
                value={formato}
                onChange={(e) => setFormato(e.target.value as ScreenFormat)}
              >
                {Object.entries(FORMATO).map(([v, rotulo]) => (
                  <option key={v} value={v}>
                    {rotulo}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <Campo
            label="Início da sessão"
            name="quando"
            type="datetime-local"
            required
            value={quando}
            onChange={(e) => setQuando(e.target.value)}
          />

          {sala ? (
            <div className="stack" style={{ gap: "var(--space-3)" }}>
              {sala.sectors.map((s) => (
                <div key={s.id} className="preco-setor">
                  <div className="stack" style={{ gap: "2px" }}>
                    <strong>{s.name}</strong>
                    <span className="faint" style={{ fontSize: "var(--text-xs)" }}>
                      {s.rows} × {s.seats_per_row} = {s.capacity} lugares
                      {s.special_seats.length > 0 && `, ${s.special_seats.length} acessíveis`}
                    </span>
                  </div>
                  <div className="preco-setor__campo">
                    <span className="faint">R$</span>
                    <input
                      className="field__input"
                      inputMode="decimal"
                      placeholder="0,00"
                      aria-label={`Preço do setor ${s.name}`}
                      value={precos[s.id] ?? ""}
                      onChange={(e) => setPrecos({ ...precos, [s.id]: e.target.value })}
                    />
                  </div>
                </div>
              ))}

              <p className="faint" style={{ fontSize: "var(--text-xs)" }}>
                Todo setor precisa de preço — sem isso a sessão iria ao ar com um setor sem valor.
              </p>
            </div>
          ) : (
            <p className="faint" style={{ fontSize: "var(--text-sm)" }}>
              Escolha a sala para definir os preços de cada setor.
            </p>
          )}
        </div>
      </div>

      <div className="rodape-acao">
        <button
          className="btn btn--ghost"
          type="button"
          disabled={!pronto || salvando}
          onClick={(e) => criar(e, false)}
        >
          Salvar rascunho
        </button>
        <button
          className="btn btn--primary"
          type="button"
          disabled={!pronto || salvando}
          onClick={(e) => criar(e, true)}
        >
          {salvando ? "Salvando…" : "Publicar sessão"}
        </button>
      </div>

      {sala && Object.keys(precos).length > 0 && (
        <p className="faint" style={{ fontSize: "var(--text-sm)" }}>
          Faixa de preço:{" "}
          {reais(Math.min(...sala.sectors.map((s) => paraCentavos(precos[s.id] ?? "0"))))} a{" "}
          {reais(Math.max(...sala.sectors.map((s) => paraCentavos(precos[s.id] ?? "0"))))}
        </p>
      )}
    </section>
  );
}
