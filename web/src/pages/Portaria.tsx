import { useCallback, useEffect, useRef, useState } from "react";
import { Html5Qrcode } from "html5-qrcode";

import { ApiError, request } from "../lib/api";
import { dataHora } from "../lib/formato";
import { Carregando } from "../components/Carregando";
import type { GateCheck, GateResult, SessionListItem } from "../lib/tipos";

const LEITOR_ID = "leitor-qr";

/** Cada veredito tem cor, símbolo e palavra próprios.
 *
 *  Símbolo e palavra, e não só cor: a portaria é usada de relance, muitas
 *  vezes no escuro e por gente diferente a cada turno. Depender de matiz
 *  excluiria quem não distingue vermelho de verde. */
const VEREDITO: Record<GateResult, { rotulo: string; simbolo: string; classe: string }> = {
  VALID: { rotulo: "Pode entrar", simbolo: "✓", classe: "veredito--ok" },
  ALREADY_USED: { rotulo: "Já utilizado", simbolo: "↻", classe: "veredito--alerta" },
  WRONG_SESSION: { rotulo: "Sessão errada", simbolo: "⇄", classe: "veredito--alerta" },
  INVALID: { rotulo: "Não vale", simbolo: "✕", classe: "veredito--erro" },
};

export function Portaria() {
  const [sessoes, setSessoes] = useState<SessionListItem[]>([]);
  const [estadoSessoes, setEstadoSessoes] = useState<"carregando" | "pronto" | "erro">(
    "carregando",
  );
  const [sessaoId, setSessaoId] = useState("");
  const [codigo, setCodigo] = useState("");
  const [resultado, setResultado] = useState<GateCheck | null>(null);
  const [erro, setErro] = useState("");
  const [validando, setValidando] = useState(false);
  const [camera, setCamera] = useState(false);
  const [erroCamera, setErroCamera] = useState("");

  const leitor = useRef<Html5Qrcode | null>(null);
  const ultimoLido = useRef<{ codigo: string; quando: number } | null>(null);

  // Endpoint próprio da portaria, e não a vitrine: a vitrine esconde o que já
  // começou, e a sessão sumia da lista bem no meio da entrada — perdendo a
  // checagem de "ingresso de outra sessão" na hora em que ela mais serve.
  // Ver decisão D33.
  //
  // A falha aqui não é cosmética: sem a lista, a porta fica em "qualquer sessão",
  // que é o modo permissivo. O operador precisa saber que a checagem está
  // desarmada, em vez de descobrir depois. Ver decisão D40.
  const carregarSessoes = useCallback(() => {
    request<SessionListItem[]>("/gate/sessions")
      .then((s) => {
        setSessoes(s);
        setEstadoSessoes("pronto");
      })
      .catch(() => setEstadoSessoes("erro"));
  }, []);

  // A volta para "carregando" mora no clique, e não aqui: no primeiro carregamento
  // o estado já é esse, e mudá-lo dentro do efeito só provocaria outro render.
  useEffect(() => {
    carregarSessoes();
  }, [carregarSessoes]);

  function tentarSessoesDeNovo() {
    setEstadoSessoes("carregando");
    carregarSessoes();
  }

  // Desliga a câmera ao sair da tela: sem isso a luz do aparelho fica acesa
  // e a permissão continua em uso depois que o operador navegou para outro lugar.
  useEffect(() => {
    return () => {
      leitor.current?.stop().catch(() => {});
      leitor.current = null;
    };
  }, []);

  async function validar(valor: string) {
    const limpo = valor.trim();
    if (!limpo || validando) return;

    setValidando(true);
    setErro("");
    try {
      const r = await request<GateCheck>("/gate/validate", {
        method: "POST",
        body: { code: limpo, session_id: sessaoId || null },
      });
      setResultado(r);
      setCodigo("");
      // Vibração curta como confirmação tátil: na fila, o operador nem sempre
      // está olhando para a tela no momento da leitura.
      if (navigator.vibrate) navigator.vibrate(r.result === "VALID" ? 60 : [60, 60, 60]);
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : "Não foi possível validar.");
    } finally {
      setValidando(false);
    }
  }

  async function ligarCamera() {
    setErroCamera("");
    try {
      const instancia = new Html5Qrcode(LEITOR_ID);
      leitor.current = instancia;
      setCamera(true);

      await instancia.start(
        { facingMode: "environment" },
        { fps: 10, qrbox: { width: 240, height: 240 } },
        (texto) => {
          // A câmera dispara várias vezes o mesmo código enquanto ele está
          // enquadrado. Sem esta trava, o primeiro disparo validaria e o
          // segundo já responderia "já utilizado" — culpando o próprio leitor.
          const agora = Date.now();
          const repetido =
            ultimoLido.current?.codigo === texto && agora - ultimoLido.current.quando < 4000;
          if (repetido) return;

          ultimoLido.current = { codigo: texto, quando: agora };
          validar(texto);
        },
        () => {}, // quadro sem QR: silencioso, acontece o tempo todo
      );
    } catch {
      setCamera(false);
      leitor.current = null;
      setErroCamera(
        "Não foi possível abrir a câmera. Verifique a permissão do navegador — " +
          "fora de localhost, a câmera exige HTTPS. Use a digitação manual abaixo.",
      );
    }
  }

  async function desligarCamera() {
    try {
      await leitor.current?.stop();
    } catch {
      // Já estava parada.
    }
    leitor.current = null;
    setCamera(false);
  }

  const veredito = resultado ? VEREDITO[resultado.result] : null;

  return (
    <section className="stack" style={{ gap: "var(--space-5)", maxWidth: "40rem" }}>
      <header className="stack" style={{ gap: "var(--space-2)" }}>
        <h1>Portaria</h1>
        <p className="muted">Leia o QR do ingresso ou digite o código.</p>
      </header>

      <div className="field">
        <label className="field__label" htmlFor="sessao">
          Sessão desta porta
        </label>
        <select
          id="sessao"
          className="field__input"
          value={sessaoId}
          disabled={estadoSessoes !== "pronto"}
          onChange={(e) => setSessaoId(e.target.value)}
        >
          <option value="">Qualquer sessão</option>
          {sessoes.map((s) => (
            <option key={s.id} value={s.id}>
              {s.title} — {dataHora(s.starts_at)}
            </option>
          ))}
        </select>

        {estadoSessoes === "carregando" && <Carregando texto="Carregando as sessões do turno" inline />}

        {estadoSessoes === "erro" && (
          <div className="alert alert--error" role="alert">
            <div className="stack" style={{ gap: "var(--space-2)" }}>
              <strong>A porta está em “qualquer sessão”</strong>
              <span style={{ fontSize: "var(--text-sm)" }}>
                As sessões do turno não carregaram, então não dá para prender esta porta a uma
                delas: um ingresso de outra sala vai ser aceito. A leitura continua funcionando —
                o que falta é essa conferência.
              </span>
              <button
                type="button"
                className="btn btn--ghost"
                style={{ alignSelf: "flex-start" }}
                onClick={tentarSessoesDeNovo}
              >
                Tentar de novo
              </button>
            </div>
          </div>
        )}

        {estadoSessoes === "pronto" && (
          <span className="faint" style={{ fontSize: "var(--text-xs)" }}>
            {sessoes.length === 0
              ? "Nenhuma sessão neste turno. A porta aceita ingresso de qualquer sessão."
              : "Escolhendo a sessão, o ingresso de outra sala é recusado com aviso claro."}
          </span>
        )}
      </div>

      {veredito && resultado && (
        <div className={`veredito ${veredito.classe}`} role="status" aria-live="assertive">
          <span className="veredito__simbolo" aria-hidden="true">
            {veredito.simbolo}
          </span>
          <div className="stack" style={{ gap: "var(--space-1)" }}>
            <strong className="veredito__rotulo">{veredito.rotulo}</strong>
            <span className="veredito__mensagem">{resultado.message}</span>
            {resultado.ticket && (
              <span className="veredito__detalhe">
                {resultado.ticket.movie_title} · {resultado.ticket.sector_name}{" "}
                {resultado.ticket.seat_code}
              </span>
            )}
          </div>
        </div>
      )}

      <div className="camera">
        <div id={LEITOR_ID} className={camera ? "camera__video" : "camera__video camera__video--off"} />

        {!camera ? (
          <button className="btn btn--primary" type="button" onClick={ligarCamera}>
            Ligar câmera
          </button>
        ) : (
          <button className="btn btn--ghost" type="button" onClick={desligarCamera}>
            Desligar câmera
          </button>
        )}

        {erroCamera && (
          <p className="alert alert--error" role="alert" style={{ fontSize: "var(--text-sm)" }}>
            {erroCamera}
          </p>
        )}
      </div>

      <form
        className="stack"
        style={{ gap: "var(--space-3)" }}
        onSubmit={(e) => {
          e.preventDefault();
          validar(codigo);
        }}
      >
        <label className="field__label" htmlFor="codigo">
          Ou digite o código do ingresso
        </label>
        <div className="busca">
          <input
            id="codigo"
            className="field__input busca__campo"
            placeholder="XXXXXXXX.YYYYYYYY"
            autoComplete="off"
            autoCapitalize="characters"
            spellCheck={false}
            value={codigo}
            onChange={(e) => setCodigo(e.target.value)}
          />
          <button className="btn btn--primary" type="submit" disabled={validando || !codigo.trim()}>
            {validando ? "Verificando…" : "Validar"}
          </button>
        </div>
      </form>

      {erro && (
        <p className="alert alert--error" role="alert">
          {erro}
        </p>
      )}
    </section>
  );
}
