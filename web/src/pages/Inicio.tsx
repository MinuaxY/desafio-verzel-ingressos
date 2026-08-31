import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { HOME_POR_PAPEL } from "../auth/types";
import { request } from "../lib/api";
import { dataHora, duracao, faixaDePreco } from "../lib/formato";
import type { SessionPage } from "../lib/tipos";
import { Classificacao, SelosDaSessao } from "../components/Selos";

const NA_PREVIA = 4;

/** Os três papéis, contados do ponto de vista de quem usa. */
const COMO_FUNCIONA = [
  {
    passo: "01",
    titulo: "O organizador publica",
    texto:
      "Escolhe o filme no catálogo, define a sala, o horário e o preço de cada setor. A sessão entra no cartaz na hora.",
  },
  {
    passo: "02",
    titulo: "Você escolhe o lugar",
    texto:
      "Vê o mapa da sala, marca a poltrona e paga. O ingresso chega com código em QR, e dá para mandar por link para quem vai junto.",
  },
  {
    passo: "03",
    titulo: "A portaria valida",
    texto:
      "Na entrada, a câmera lê o QR e responde na hora: liberado, já utilizado, inválido ou sessão errada.",
  },
];

export function Inicio() {
  const { user } = useAuth();
  const [pagina, setPagina] = useState<SessionPage | null>(null);
  // A prévia tem três desfechos, e a landing precisa saber em qual está: o
  // `.catch` silencioso fazia a seção inteira sumir sem explicar nada — logo
  // aqui, onde a primeira visita pega o servidor acordando e leva até um
  // minuto. Ver decisão D39.
  const [estado, setEstado] = useState<"carregando" | "pronto" | "erro">("carregando");

  useEffect(() => {
    request<SessionPage>(`/sessions?per_page=${NA_PREVIA}`, { auth: false })
      .then((r) => {
        setPagina(r);
        setEstado("pronto");
      })
      .catch(() => setEstado("erro"));
  }, []);

  const sessoes = pagina?.items ?? [];

  return (
    <div className="inicio">
      {/* ---------- Abertura ---------- */}
      <section className="abertura">
        <div className="abertura__texto">
          <p className="abertura__etiqueta">Sessões de cinema</p>
          <h1 className="abertura__titulo">
            Escolha o filme.
            <br />
            <span className="abertura__destaque">O lugar é seu.</span>
          </h1>
          <p className="abertura__linha">
            Poltrona marcada no mapa da sala, ingresso com código em QR e entrada validada na
            porta. Sem fila de bilheteria.
          </p>

          <div className="abertura__acoes">
            <Link className="btn btn--primary" to="/em-cartaz">
              Ver o que está em cartaz
            </Link>
            {!user && (
              <Link className="btn btn--ghost" to="/criar-conta">
                Criar conta
              </Link>
            )}
          </div>

          <p className="abertura__aviso">
            Ambiente de demonstração — os pagamentos são simulados e nenhuma cobrança é feita.
            {!user && (
              <>
                {" "}
                Há <Link to="/entrar">contas prontas</Link> para testar os três papéis.
              </>
            )}
          </p>
        </div>

        {/* O pôster da próxima sessão como arte da abertura: material real em vez
            de ilustração genérica. Decorativo, então fica escondido de leitores
            de tela — a mesma informação aparece logo abaixo, em texto. */}
        {sessoes[0]?.poster_url && (
          <div className="abertura__arte" aria-hidden="true">
            <img src={sessoes[0].poster_url} alt="" />
          </div>
        )}
      </section>

      {/* ---------- Prévia do cartaz ---------- */}
      {estado === "carregando" && (
        <section className="secao">
          <h2 className="secao__titulo">Próximas sessões</h2>
          <p className="muted" role="status">
            Carregando o cartaz. A primeira visita pode demorar até um minuto — o servidor
            hiberna quando fica sem uso.
          </p>
        </section>
      )}

      {estado === "erro" && (
        <section className="secao">
          <h2 className="secao__titulo">Próximas sessões</h2>
          <p className="alert alert--error" role="alert">
            Não foi possível carregar o cartaz agora.{" "}
            <Link to="/em-cartaz">Tentar de novo</Link>.
          </p>
        </section>
      )}

      {estado === "pronto" && sessoes.length === 0 && (
        <section className="secao">
          <h2 className="secao__titulo">Próximas sessões</h2>
          <p className="muted">Nenhuma sessão em cartaz no momento.</p>
        </section>
      )}

      {sessoes.length > 0 && (
        <section className="secao">
          <header className="secao__cabecalho">
            <h2 className="secao__titulo">Próximas sessões</h2>
            <Link className="link-discreto" to="/em-cartaz">
              Ver todas →
            </Link>
          </header>

          <ul className="cartazes">
            {sessoes.map((s) => (
              <li key={s.id}>
                <Link to={`/sessao/${s.id}`} className="cartaz">
                  <div className="cartaz__arte">
                    {s.poster_url ? (
                      <img src={s.poster_url} alt="" loading="lazy" />
                    ) : (
                      <span className="cartaz__sem-arte">🎬</span>
                    )}
                    <Classificacao valor={s.age_rating} tamanho="mini" />
                  </div>

                  <div className="cartaz__info">
                    <h3 className="cartaz__titulo">{s.title}</h3>
                    <p className="faint" style={{ fontSize: "var(--text-xs)" }}>
                      {[s.year, duracao(s.runtime_minutes)].filter(Boolean).join(" · ")}
                    </p>
                    <SelosDaSessao audio={s.audio} formato={s.screen_format} />
                    <p className="cartaz__quando">{dataHora(s.starts_at)}</p>
                    <p className="cartaz__preco">
                      {faixaDePreco(s.min_price_cents, s.max_price_cents)}
                    </p>
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* ---------- Como funciona ---------- */}
      <section className="secao">
        <h2 className="secao__titulo">Como funciona</h2>

        <ol className="passos">
          {COMO_FUNCIONA.map((p) => (
            <li key={p.passo} className="passo">
              <span className="passo__numero" aria-hidden="true">
                {p.passo}
              </span>
              <h3 className="passo__titulo">{p.titulo}</h3>
              <p className="muted" style={{ fontSize: "var(--text-sm)" }}>
                {p.texto}
              </p>
            </li>
          ))}
        </ol>
      </section>

      {/* ---------- Fecho ---------- */}
      <section className="fecho">
        <div className="stack" style={{ gap: "var(--space-2)" }}>
          <h2 style={{ fontSize: "var(--text-xl)" }}>
            {user ? "Bom filme." : "Pronto para escolher seu lugar?"}
          </h2>
          <p className="muted" style={{ fontSize: "var(--text-sm)" }}>
            {user
              ? "Sua área está a um clique."
              : "Criar conta leva menos de um minuto, e você já sai comprando."}
          </p>
        </div>

        <Link className="btn btn--primary" to={user ? HOME_POR_PAPEL[user.role] : "/criar-conta"}>
          {user ? "Ir para minha área" : "Criar conta"}
        </Link>
      </section>
    </div>
  );
}
