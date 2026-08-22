import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { ApiError, request } from "../lib/api";
import { ASSENTO } from "../lib/tipos";
import type { Room, SeatKind } from "../lib/tipos";
import { Campo } from "../components/Campo";
import { Carregando } from "../components/Carregando";

interface SetorForm {
  name: string;
  rows: string;
  seats_per_row: string;
  aisles: string;
  special: { seat_code: string; kind: SeatKind }[];
}

const SETOR_VAZIO: SetorForm = {
  name: "",
  rows: "6",
  seats_per_row: "12",
  aisles: "3, 9",
  special: [],
};

/** Lê "3, 9" como [3, 9]. Aceita separador solto porque quem digita está
 *  descrevendo uma sala, não preenchendo um formato. */
function leCorredores(texto: string, poltronasPorFileira: number): number[] {
  return [
    ...new Set(
      texto
        .split(/[^\d]+/)
        .map((n) => Number(n))
        .filter((n) => n > 0 && n < poltronasPorFileira),
    ),
  ].sort((a, b) => a - b);
}

export function Salas() {
  const [salas, setSalas] = useState<Room[] | null>(null);
  const [erro, setErro] = useState("");
  const [salvando, setSalvando] = useState(false);
  const [criando, setCriando] = useState(false);

  const [nome, setNome] = useState("");
  const [local, setLocal] = useState("");
  const [setores, setSetores] = useState<SetorForm[]>([{ ...SETOR_VAZIO, name: "Plateia" }]);
  // Sala em edição de nome/endereço. A geometria não entra aqui: ela trava
  // depois da primeira sessão. Ver decisão D29.
  const [editando, setEditando] = useState<Room | null>(null);
  const [rascunho, setRascunho] = useState({ name: "", location: "" });
  const [agindo, setAgindo] = useState("");

  function carregar() {
    request<Room[]>("/rooms")
      .then(setSalas)
      .catch((e) => setErro(e.message));
  }

  useEffect(carregar, []);

  function atualizaSetor(i: number, mudanca: Partial<SetorForm>) {
    setSetores((atual) => atual.map((s, idx) => (idx === i ? { ...s, ...mudanca } : s)));
  }

  function alternaAcessivel(i: number, codigo: string, tipo: SeatKind) {
    setSetores((atual) =>
      atual.map((s, idx) => {
        if (idx !== i) return s;
        const existente = s.special.find((a) => a.seat_code === codigo);
        if (existente && existente.kind === tipo) {
          return { ...s, special: s.special.filter((a) => a.seat_code !== codigo) };
        }
        return {
          ...s,
          special: [...s.special.filter((a) => a.seat_code !== codigo), { seat_code: codigo, kind: tipo }],
        };
      }),
    );
  }

  async function criar(e: React.FormEvent) {
    e.preventDefault();
    setErro("");
    setSalvando(true);
    try {
      await request<Room>("/rooms", {
        method: "POST",
        body: {
          name: nome,
          location: local || null,
          sectors: setores.map((s, i) => ({
            name: s.name,
            rows: Number(s.rows),
            seats_per_row: Number(s.seats_per_row),
            display_order: i,
            special_seats: s.special,
            aisles: leCorredores(s.aisles, Number(s.seats_per_row) || 0),
          })),
        },
      });
      setNome("");
      setLocal("");
      setSetores([{ ...SETOR_VAZIO, name: "Plateia" }]);
      setCriando(false);
      carregar();
    } catch (err) {
      setErro(err instanceof ApiError ? err.message : "Não foi possível criar a sala.");
    } finally {
      setSalvando(false);
    }
  }

  function abrirEdicao(s: Room) {
    setEditando(s);
    setRascunho({ name: s.name, location: s.location ?? "" });
    setCriando(false);
    setErro("");
  }

  async function salvarEdicao(e: React.FormEvent) {
    e.preventDefault();
    if (!editando) return;

    setAgindo(editando.id);
    setErro("");
    try {
      await request<Room>(`/rooms/${editando.id}`, {
        method: "PATCH",
        body: { name: rascunho.name, location: rascunho.location },
      });
      setEditando(null);
      carregar();
    } catch (err) {
      setErro(err instanceof ApiError ? err.message : "Não foi possível salvar.");
    } finally {
      setAgindo("");
    }
  }

  async function remover(s: Room) {
    if (
      !window.confirm(
        `Remover a sala ${s.name}? Se ela já tiver sido usada em alguma sessão, fica ` +
          "guardada como inativa para o histórico não se perder.",
      )
    )
      return;

    setAgindo(s.id);
    setErro("");
    try {
      await request(`/rooms/${s.id}`, { method: "DELETE" });
      carregar();
    } catch (err) {
      setErro(err instanceof ApiError ? err.message : "Não foi possível remover.");
    } finally {
      setAgindo("");
    }
  }

  if (!salas && !erro) return <Carregando texto="Carregando salas" />;

  return (
    <section className="stack" style={{ gap: "var(--space-6)", maxWidth: "48rem" }}>
      <header className="cabecalho-acao">
        <div className="stack" style={{ gap: "var(--space-2)" }}>
          <h1>Salas</h1>
          <p className="muted">
            A sala guarda o layout de poltronas e é reaproveitada por todas as sessões.
          </p>
        </div>
        <div className="cabecalho-acao__botoes">
          <Link className="btn btn--ghost" to="/organizador">
            Sessões
          </Link>
          <button className="btn btn--primary" type="button" onClick={() => setCriando((v) => !v)}>
            {criando ? "Cancelar" : "Cadastrar sala"}
          </button>
        </div>
      </header>

      {erro && (
        <p className="alert alert--error" role="alert">
          {erro}
        </p>
      )}

      {editando && (
        <form className="etapa stack" style={{ gap: "var(--space-4)" }} onSubmit={salvarEdicao}>
          <h2 className="etapa__titulo">Editar {editando.name}</h2>

          <Campo
            label="Nome da sala"
            name="editar-nome"
            required
            value={rascunho.name}
            onChange={(e) => setRascunho({ ...rascunho, name: e.target.value })}
          />
          <Campo
            label="Endereço"
            name="editar-local"
            placeholder="Av. Paulista, 1000 — São Paulo"
            value={rascunho.location}
            onChange={(e) => setRascunho({ ...rascunho, location: e.target.value })}
          />

          <p className="faint" style={{ fontSize: "var(--text-xs)" }}>
            O layout de poltronas não aparece aqui porque ele trava assim que a sala recebe a
            primeira sessão — ingressos vendidos apontam para lugares específicos. Para uma
            configuração diferente, cadastre outra sala.
          </p>

          <div className="rodape-acao">
            <button
              className="btn btn--ghost"
              type="button"
              onClick={() => setEditando(null)}
            >
              Cancelar
            </button>
            <button
              className="btn btn--primary"
              type="submit"
              disabled={agindo === editando.id}
            >
              {agindo === editando.id ? "Salvando…" : "Salvar"}
            </button>
          </div>
        </form>
      )}

      {criando && (
        <form className="etapa stack" style={{ gap: "var(--space-4)" }} onSubmit={criar}>
          <h2 className="etapa__titulo">Nova sala</h2>

          <Campo
            label="Nome da sala"
            name="nome"
            required
            placeholder="Sala 1"
            value={nome}
            onChange={(e) => setNome(e.target.value)}
          />
          <Campo
            label="Endereço (opcional)"
            name="local"
            placeholder="Av. Paulista, 1000 — São Paulo"
            value={local}
            onChange={(e) => setLocal(e.target.value)}
          />

          {setores.map((setor, i) => {
            const fileiras = Array.from({ length: Number(setor.rows) || 0 }, (_, r) =>
              String.fromCharCode(65 + r),
            );
            const porFileira = Number(setor.seats_per_row) || 0;

            return (
              <fieldset key={i} className="setor-form">
                <legend className="field__label">Setor {i + 1}</legend>

                <div className="setor-form__linha">
                  <Campo
                    label="Nome"
                    name={`setor-${i}`}
                    required
                    placeholder="Plateia"
                    value={setor.name}
                    onChange={(e) => atualizaSetor(i, { name: e.target.value })}
                  />
                  <Campo
                    label="Fileiras"
                    name={`fileiras-${i}`}
                    type="number"
                    min={1}
                    max={26}
                    required
                    value={setor.rows}
                    onChange={(e) => atualizaSetor(i, { rows: e.target.value })}
                  />
                  <Campo
                    label="Poltronas por fileira"
                    name={`poltronas-${i}`}
                    type="number"
                    min={1}
                    max={40}
                    required
                    value={setor.seats_per_row}
                    onChange={(e) => atualizaSetor(i, { seats_per_row: e.target.value })}
                  />
                </div>

                <Campo
                  label="Corredores"
                  name={`corredores-${i}`}
                  placeholder="3, 9"
                  value={setor.aisles}
                  onChange={(e) => atualizaSetor(i, { aisles: e.target.value })}
                />
                <p className="faint" style={{ fontSize: "var(--text-xs)", marginTop: "-8px" }}>
                  Posições depois das quais há passagem. Com {setor.seats_per_row || "?"} poltronas
                  e corredores em {leCorredores(setor.aisles, Number(setor.seats_per_row) || 0).join(", ") || "nenhum"},
                  a fileira fica em blocos de{" "}
                  {(() => {
                    const total = Number(setor.seats_per_row) || 0;
                    const cortes = leCorredores(setor.aisles, total);
                    const blocos: number[] = [];
                    let anterior = 0;
                    for (const c of cortes) {
                      blocos.push(c - anterior);
                      anterior = c;
                    }
                    blocos.push(total - anterior);
                    return blocos.filter((b) => b > 0).join(" · ");
                  })()}
                  . Deixe vazio para um bloco só.
                </p>

                <details className="acessiveis">
                  <summary>
                    Poltronas acessíveis
                    {setor.special.length > 0 && ` (${setor.special.length} marcadas)`}
                  </summary>

                  <p className="faint" style={{ fontSize: "var(--text-xs)", margin: "var(--space-3) 0" }}>
                    Clique numa poltrona para marcá-la. Clicar de novo no mesmo tipo desmarca.
                  </p>

                  <div className="acessiveis__tipos">
                    {Object.entries(ASSENTO).map(([chave, { rotulo, sigla }]) => (
                      <span key={chave} className="acessiveis__tipo">
                        <strong>{sigla}</strong> {rotulo}
                      </span>
                    ))}
                  </div>

                  <div className="acessiveis__grade">
                    {fileiras.map((letra) => (
                      <div key={letra} className="fileira">
                        <span className="fileira__letra">{letra}</span>
                        {Array.from({ length: porFileira }, (_, n) => {
                          const codigo = `${letra}${n + 1}`;
                          const marcado = setor.special.find((a) => a.seat_code === codigo);
                          return (
                            <button
                              key={codigo}
                              type="button"
                              className={
                                marcado ? "poltrona poltrona--acessivel" : "poltrona"
                              }
                              title={marcado ? ASSENTO[marcado.kind].rotulo : codigo}
                              onClick={() => {
                                const tipos = Object.keys(ASSENTO) as SeatKind[];
                                const atual = marcado ? tipos.indexOf(marcado.kind) : -1;
                                const proximo = tipos[(atual + 1) % (tipos.length + 1)];
                                if (proximo === undefined) {
                                  alternaAcessivel(i, codigo, marcado!.kind);
                                } else {
                                  alternaAcessivel(i, codigo, proximo);
                                }
                              }}
                            >
                              {marcado ? ASSENTO[marcado.kind].sigla : n + 1}
                            </button>
                          );
                        })}
                      </div>
                    ))}
                  </div>
                </details>
              </fieldset>
            );
          })}

          <div className="rodape-acao">
            <button
              className="btn btn--ghost"
              type="button"
              onClick={() => setSetores([...setores, { ...SETOR_VAZIO }])}
            >
              Adicionar setor
            </button>
            <button className="btn btn--primary" type="submit" disabled={salvando}>
              {salvando ? "Salvando…" : "Criar sala"}
            </button>
          </div>
        </form>
      )}

      {salas && salas.length === 0 && !criando ? (
        <div className="vazio">
          <p style={{ fontWeight: 600 }}>Nenhuma sala cadastrada</p>
          <p className="muted" style={{ fontSize: "var(--text-sm)" }}>
            Cadastre uma sala para poder criar sessões.
          </p>
        </div>
      ) : (
        <ul className="lista-salas">
          {salas?.map((s) => (
            <li key={s.id} className="linha-sala">
              <div className="stack" style={{ gap: "var(--space-1)", flex: 1, minWidth: 0 }}>
                <strong>{s.name}</strong>
                {s.location && (
                  <span className="muted" style={{ fontSize: "var(--text-sm)" }}>
                    {s.location}
                  </span>
                )}
                <span className="faint" style={{ fontSize: "var(--text-xs)" }}>
                  {s.capacity} lugares ·{" "}
                  {s.sectors.map((st) => `${st.name} ${st.rows}×${st.seats_per_row}`).join(" · ")}
                  {s.sectors.some((st) => st.special_seats.length > 0) &&
                    ` · ${s.sectors.reduce((n, st) => n + st.special_seats.length, 0)} acessíveis`}
                </span>
              </div>

              <div className="linha-sessao__acoes">
                <button
                  className="btn btn--ghost btn--mini"
                  type="button"
                  disabled={agindo === s.id}
                  onClick={() => abrirEdicao(s)}
                >
                  Editar
                </button>
                <button
                  className="btn btn--ghost btn--mini btn--perigo"
                  type="button"
                  disabled={agindo === s.id}
                  onClick={() => remover(s)}
                >
                  Remover
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
