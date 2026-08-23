import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { ApiError, request } from "../lib/api";
import { dataHora, duracao, reais } from "../lib/formato";
import { AUDIO, FORMATO } from "../lib/tipos";
import type { AudioType, BatchResult, ScreenFormat, SessionDetail } from "../lib/tipos";
import { Campo } from "../components/Campo";
import { Carregando } from "../components/Carregando";
import { EscolhaDeDias } from "../components/EscolhaDeDias";
import { Classificacao } from "../components/Selos";

/** Converte "32,00" em centavos, sem passar por float. Ver decisão D14. */
function paraCentavos(texto: string): number {
  const limpo = texto.replace(/[^\d,.]/g, "").replace(",", ".");
  if (!limpo) return 0;
  const [inteiros, decimais = ""] = limpo.split(".");
  return Number(inteiros || 0) * 100 + Number(decimais.padEnd(2, "0").slice(0, 2));
}

function emReais(centavos: number): string {
  return (centavos / 100).toFixed(2).replace(".", ",");
}

/** ISO com fuso → valor aceito pelo input `datetime-local`, no fuso local. */
function paraCampoLocal(iso: string): string {
  const d = new Date(iso);
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`;
}

export function EditarSessao() {
  const { id = "" } = useParams();
  const navigate = useNavigate();

  const [sessao, setSessao] = useState<SessionDetail | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const [salvando, setSalvando] = useState(false);
  const [salvo, setSalvo] = useState(false);

  const [quando, setQuando] = useState("");
  const [audio, setAudio] = useState<AudioType>("SUBTITLED");
  const [formato, setFormato] = useState<ScreenFormat>("TWO_D");
  const [precos, setPrecos] = useState<Record<string, string>>({});

  const [diasExtras, setDiasExtras] = useState<string[]>([]);
  const [repetindo, setRepetindo] = useState(false);
  const [lote, setLote] = useState<BatchResult | null>(null);
  const [erroLote, setErroLote] = useState("");

  useEffect(() => {
    request<SessionDetail>(`/organizer/sessions/${id}`)
      .then((s) => {
        setSessao(s);
        setQuando(paraCampoLocal(s.starts_at));
        setAudio(s.audio);
        setFormato(s.screen_format);
        setPrecos(
          Object.fromEntries(s.prices.map((p) => [p.sector.id, emReais(p.price_cents)])),
        );
      })
      .catch((e) => setErro(e.message))
      .finally(() => setCarregando(false));
  }, [id]);

  async function salvar(e: React.FormEvent) {
    e.preventDefault();
    if (!sessao) return;

    const semPreco = sessao.prices
      .filter((p) => paraCentavos(precos[p.sector.id] ?? "") <= 0)
      .map((p) => p.sector.name);
    if (semPreco.length > 0) {
      setErro(`Defina um preço maior que zero para: ${semPreco.join(", ")}.`);
      return;
    }

    setErro("");
    setSalvo(false);
    setSalvando(true);
    try {
      const atualizada = await request<SessionDetail>(`/organizer/sessions/${id}`, {
        method: "PATCH",
        body: {
          starts_at: new Date(quando).toISOString(),
          audio,
          screen_format: formato,
          prices: sessao.prices.map((p) => ({
            sector_id: p.sector.id,
            price_cents: paraCentavos(precos[p.sector.id] ?? ""),
          })),
        },
      });
      setSessao(atualizada);
      setSalvo(true);
    } catch (err) {
      setErro(err instanceof ApiError ? err.message : "Não foi possível salvar.");
    } finally {
      setSalvando(false);
    }
  }

  /** Cria cópias desta sessão em outros dias.
   *
   *  Ação à parte do "salvar": ela não altera esta sessão, cria outras. Usa o
   *  que está no formulário — horário, áudio, formato e preços —, e não o que
   *  está salvo, porque quem ajusta o preço e manda repetir espera que as
   *  cópias saiam com o preço ajustado. Ver decisão D32. */
  async function repetir() {
    if (!sessao || diasExtras.length === 0) return;

    // Sem esta conferência, um campo de preço apagado criaria as cópias todas
    // a R$ 0,00 — e a API agora recusa isso com um erro de validação cru.
    // Ver decisão D33.
    const semPreco = sessao.prices
      .filter((p) => paraCentavos(precos[p.sector.id] ?? "") <= 0)
      .map((p) => p.sector.name);
    if (semPreco.length > 0) {
      setLote(null);
      setErroLote(`Defina um preço maior que zero para: ${semPreco.join(", ")}.`);
      return;
    }

    setErroLote("");
    setLote(null);
    setRepetindo(true);
    try {
      const resultado = await request<BatchResult>("/organizer/sessions/batch", {
        method: "POST",
        body: {
          catalog_id: sessao.movie.catalog_id,
          room_id: sessao.room_id,
          dates: diasExtras,
          time_of_day: `${quando.split("T")[1] ?? ""}:00`.slice(0, 8),
          audio,
          screen_format: formato,
          prices: sessao.prices.map((p) => ({
            sector_id: p.sector.id,
            price_cents: paraCentavos(precos[p.sector.id] ?? ""),
          })),
          // As cópias nascem no mesmo estado desta: repetir uma sessão que
          // está no cartaz e receber rascunhos seria surpresa.
          publish: sessao.status === "PUBLISHED",
        },
      });
      setLote(resultado);
      setDiasExtras([]);
    } catch (err) {
      setErroLote(err instanceof ApiError ? err.message : "Não foi possível repetir a sessão.");
    } finally {
      setRepetindo(false);
    }
  }

  if (carregando) return <Carregando texto="Carregando sessão" />;

  if (!sessao) {
    return (
      <section className="stack" style={{ gap: "var(--space-4)", maxWidth: "50ch" }}>
        <h1>Sessão não encontrada</h1>
        <p className="muted">{erro}</p>
        <Link className="btn btn--ghost" to="/organizador" style={{ alignSelf: "flex-start" }}>
          Voltar
        </Link>
      </section>
    );
  }

  return (
    <section className="stack" style={{ gap: "var(--space-6)", maxWidth: "44rem" }}>
      {/* Fica no topo porque o "Cancelar" do formulário ficou no meio da
          página depois do bloco de repetir, e sair da tela não deveria exigir
          rolar até achá-lo. Link e não navigate(-1): a edição só se alcança
          pela lista, e o histórico do navegador pode vir de fora do app. */}
      <Link className="voltar" to="/organizador">
        ← Minhas sessões
      </Link>

      <header className="stack" style={{ gap: "var(--space-2)" }}>
        <h1>Editar sessão</h1>
        <p className="muted">
          O filme e a sala não mudam. Para trocá-los, crie outra sessão — assim quem já
          comprou não recebe uma coisa diferente da que escolheu.
        </p>
      </header>

      <div className="escolhido">
        {sessao.movie.poster_url && <img src={sessao.movie.poster_url} alt="" />}
        <div className="stack" style={{ gap: "var(--space-2)", flex: 1, minWidth: 0 }}>
          <strong>{sessao.movie.title}</strong>
          <span className="faint" style={{ fontSize: "var(--text-sm)" }}>
            {[sessao.movie.year, duracao(sessao.movie.runtime_minutes)]
              .filter(Boolean)
              .join(" · ")}{" "}
            · {sessao.room_name}
          </span>
          <span className="ficha">
            <Classificacao valor={sessao.movie.age_rating} tamanho="mini" />
            <span className="faint" style={{ fontSize: "var(--text-xs)" }}>
              agora em {dataHora(sessao.starts_at)}
            </span>
          </span>
        </div>
      </div>

      {erro && (
        <p className="alert alert--error" role="alert">
          {erro}
        </p>
      )}
      {salvo && (
        <p className="alert alert--success" role="status">
          Alterações salvas.
        </p>
      )}

      <form className="etapa stack" style={{ gap: "var(--space-4)" }} onSubmit={salvar}>
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
        <p className="faint" style={{ fontSize: "var(--text-xs)", marginTop: "-8px" }}>
          O horário não pode mudar depois que alguém compra: o sistema não teria como avisar
          quem já tem ingresso.
        </p>

        <div className="stack" style={{ gap: "var(--space-3)" }}>
          {sessao.prices.map((p) => (
            <div key={p.sector.id} className="preco-setor">
              <div className="stack" style={{ gap: "2px" }}>
                <strong>{p.sector.name}</strong>
                <span className="faint" style={{ fontSize: "var(--text-xs)" }}>
                  {p.sector.capacity} lugares · hoje {reais(p.price_cents)}
                </span>
              </div>
              <div className="preco-setor__campo">
                <span className="faint">R$</span>
                <input
                  className="field__input"
                  inputMode="decimal"
                  aria-label={`Preço do setor ${p.sector.name}`}
                  value={precos[p.sector.id] ?? ""}
                  onChange={(e) => setPrecos({ ...precos, [p.sector.id]: e.target.value })}
                />
              </div>
            </div>
          ))}
          <p className="faint" style={{ fontSize: "var(--text-xs)" }}>
            Preço novo vale para quem ainda vai comprar. Ingresso já emitido guarda o valor
            que foi pago.
          </p>
        </div>

        <div className="rodape-acao">
          <button
            className="btn btn--ghost"
            type="button"
            disabled={salvando}
            onClick={() => navigate("/organizador")}
          >
            Cancelar
          </button>
          <button className="btn btn--primary" type="submit" disabled={salvando}>
            {salvando ? "Salvando…" : "Salvar alterações"}
          </button>
        </div>
      </form>

      {/* Repetir fica fora do formulário de propósito: não altera esta sessão,
          cria outras. Misturar as duas coisas num botão só faria "salvar"
          produzir sessões sem que ninguém tivesse pedido. Ver decisão D32. */}
      <div className="etapa stack" style={{ gap: "var(--space-4)" }}>
        <div className="stack" style={{ gap: "var(--space-2)" }}>
          <h2 style={{ fontSize: "var(--text-lg)" }}>Repetir esta sessão</h2>
          <p className="faint" style={{ fontSize: "var(--text-sm)" }}>
            Cria cópias em outros dias, com o mesmo filme e a mesma sala. Elas usam o horário,
            o áudio, o formato e os preços que estão no formulário acima — inclusive
            alterações que você ainda não salvou.
          </p>
        </div>

        {quando && (
          <EscolhaDeDias
            baseISO={quando.split("T")[0]}
            hora={quando.split("T")[1] ?? ""}
            selecionados={diasExtras}
            onMudar={setDiasExtras}
            baseJaExiste
          />
        )}

        {erroLote && (
          <p className="alert alert--error" role="alert">
            {erroLote}
          </p>
        )}

        {lote && (
          <div
            className={`alert ${lote.created.length > 0 ? "alert--success" : "alert--error"}`}
            role="status"
          >
            <div className="stack" style={{ gap: "var(--space-2)" }}>
              <strong>
                {lote.created.length === 0
                  ? "Nenhuma sessão foi criada"
                  : `${lote.created.length} ${
                      lote.created.length === 1 ? "sessão criada" : "sessões criadas"
                    }`}
              </strong>
              {/* O que ficou de fora vem com o motivo: o lote pula o dia
                  ocupado em vez de abortar tudo. Ver decisão D27. */}
              {lote.skipped.length > 0 && (
                <ul style={{ paddingLeft: "var(--space-5)", fontSize: "var(--text-sm)" }}>
                  {lote.skipped.map((p) => (
                    <li key={p.date}>
                      {p.date.split("-").reverse().join("/")} — {p.reason}
                    </li>
                  ))}
                </ul>
              )}
              {lote.created.length > 0 && (
                <Link to="/organizador">Ver na lista de sessões</Link>
              )}
            </div>
          </div>
        )}

        <div className="rodape-acao">
          <button
            className="btn btn--primary"
            type="button"
            disabled={repetindo || diasExtras.length === 0}
            onClick={repetir}
          >
            {repetindo
              ? "Criando…"
              : diasExtras.length === 0
                ? "Escolha os dias acima"
                : `Criar ${diasExtras.length} ${
                    diasExtras.length === 1 ? "sessão" : "sessões"
                  }`}
          </button>
        </div>
      </div>
    </section>
  );
}
