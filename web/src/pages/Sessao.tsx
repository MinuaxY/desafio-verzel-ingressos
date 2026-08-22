import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { ApiError, request } from "../lib/api";
import { dataHora, duracao, reais } from "../lib/formato";
import type { Order, Seat, SeatMap, SectorMap, SessionDetail } from "../lib/tipos";
import { Carregando } from "../components/Carregando";
import { MapaDeAssentos } from "../components/MapaDeAssentos";
import type { Escolha } from "../components/MapaDeAssentos";

const MAX_POR_COMPRA = 10;

export function Sessao() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [sessao, setSessao] = useState<SessionDetail | null>(null);
  const [mapa, setMapa] = useState<SeatMap | null>(null);
  const [escolhidos, setEscolhidos] = useState<Escolha[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    setCarregando(true);
    Promise.all([
      request<SessionDetail>(`/sessions/${id}`, { auth: false }),
      request<SeatMap>(`/sessions/${id}/seats`, { auth: false }),
    ])
      .then(([s, m]) => {
        setSessao(s);
        setMapa(m);
        setErro("");
      })
      .catch((e) => setErro(e.message))
      .finally(() => setCarregando(false));
  }, [id]);

  function alternar(setor: SectorMap, assento: Seat) {
    setEscolhidos((atual) => {
      const jaTem = atual.some((e) => e.sectorId === setor.id && e.code === assento.code);
      if (jaTem) {
        return atual.filter((e) => !(e.sectorId === setor.id && e.code === assento.code));
      }
      if (atual.length >= MAX_POR_COMPRA) return atual;
      return [...atual, { sectorId: setor.id, code: assento.code, priceCents: setor.price_cents }];
    });
  }

  async function reservar() {
    // Quem não entrou vai para o login e volta para cá depois.
    if (!user) {
      navigate("/entrar", { state: { de: `/sessao/${id}` } });
      return;
    }

    setErro("");
    setEnviando(true);
    try {
      const pedido = await request<Order>("/orders", {
        method: "POST",
        body: {
          session_id: id,
          seats: escolhidos.map((e) => ({ sector_id: e.sectorId, seat_code: e.code })),
        },
      });
      navigate(`/pedido/${pedido.id}`);
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : "Não foi possível reservar.");
      // Alguém pode ter comprado enquanto esta tela estava aberta: recarrega o
      // mapa para o usuário ver a situação atual em vez de tentar de novo.
      if (e instanceof ApiError && e.status === 409) {
        request<SeatMap>(`/sessions/${id}/seats`, { auth: false }).then(setMapa).catch(() => {});
        setEscolhidos([]);
      }
    } finally {
      setEnviando(false);
    }
  }

  if (carregando) return <Carregando texto="Carregando sessão" />;

  if (!sessao || !mapa) {
    return (
      <section className="stack" style={{ gap: "var(--space-4)", maxWidth: "50ch" }}>
        <h1>Sessão não encontrada</h1>
        <p className="muted">{erro || "Ela pode ter sido cancelada ou já começado."}</p>
        <Link className="btn btn--ghost" to="/em-cartaz" style={{ alignSelf: "flex-start" }}>
          Ver o que está em cartaz
        </Link>
      </section>
    );
  }

  const total = escolhidos.reduce((soma, e) => soma + e.priceCents, 0);

  return (
    <section className="stack" style={{ gap: "var(--space-6)" }}>
      <header className="sessao__topo">
        {sessao.movie.poster_url && (
          <img className="sessao__poster" src={sessao.movie.poster_url} alt="" />
        )}

        <div className="stack" style={{ gap: "var(--space-3)" }}>
          <div className="stack" style={{ gap: "var(--space-1)" }}>
            <h1>{sessao.movie.title}</h1>
            <p className="faint" style={{ fontSize: "var(--text-sm)" }}>
              {[sessao.movie.year, duracao(sessao.movie.runtime_minutes)]
                .filter(Boolean)
                .join(" · ")}
            </p>
          </div>

          <p className="sessao__quando">{dataHora(sessao.starts_at)}</p>
          <p className="muted">
            {sessao.room_name}
            {sessao.room_location && ` — ${sessao.room_location}`}
          </p>

          {sessao.movie.overview && (
            <p className="muted" style={{ fontSize: "var(--text-sm)", maxWidth: "60ch" }}>
              {sessao.movie.overview}
            </p>
          )}

          <p className="faint" style={{ fontSize: "var(--text-sm)" }}>
            {mapa.available} de {mapa.capacity} lugares disponíveis
          </p>
        </div>
      </header>

      {erro && (
        <p className="alert alert--error" role="alert">
          {erro}
        </p>
      )}

      <div className="stack" style={{ gap: "var(--space-4)" }}>
        <h2 style={{ fontSize: "var(--text-lg)" }}>Escolha os lugares</h2>
        <MapaDeAssentos
          setores={mapa.sectors}
          escolhidos={escolhidos}
          onAlternar={alternar}
          maximo={MAX_POR_COMPRA}
        />
      </div>

      {escolhidos.length > 0 && (
        <div className="barra-compra" role="region" aria-label="Resumo da escolha">
          <div className="stack" style={{ gap: "2px" }}>
            <strong>
              {escolhidos.length} {escolhidos.length === 1 ? "lugar" : "lugares"}:{" "}
              {escolhidos.map((e) => e.code).join(", ")}
            </strong>
            <span className="muted" style={{ fontSize: "var(--text-sm)" }}>
              Total {reais(total)}
            </span>
          </div>

          <button
            className="btn btn--primary"
            type="button"
            onClick={reservar}
            disabled={enviando}
          >
            {enviando ? "Reservando…" : user ? "Continuar" : "Entrar e continuar"}
          </button>
        </div>
      )}
    </section>
  );
}
