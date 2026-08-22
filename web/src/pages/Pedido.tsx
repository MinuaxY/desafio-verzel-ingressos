import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { ApiError, request } from "../lib/api";
import { dataHora, reais, tempoRestante } from "../lib/formato";
import type { Order } from "../lib/tipos";
import { Campo } from "../components/Campo";
import { Carregando } from "../components/Carregando";

/** Cartões com desfecho fixo. Ficam à vista porque o pagamento é simulado e
 *  quem estiver avaliando precisa conseguir provocar a recusa de propósito.
 *  Ver decisão D18. */
const CARTOES = [
  { numero: "4111 1111 1111 1111", efeito: "aprova" },
  { numero: "4000 0000 0000 0002", efeito: "recusa" },
  { numero: "4000 0000 0000 9995", efeito: "sem saldo" },
];

export function Pedido() {
  const { id = "" } = useParams();
  const navigate = useNavigate();

  const [pedido, setPedido] = useState<Order | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const [pagando, setPagando] = useState(false);
  const [cartao, setCartao] = useState({ card_number: "", card_holder: "" });
  const [agora, setAgora] = useState(Date.now());
  const [cancelando, setCancelando] = useState(false);

  useEffect(() => {
    request<Order>(`/orders/${id}`)
      .then(setPedido)
      .catch((e) => setErro(e.message))
      .finally(() => setCarregando(false));
  }, [id]);

  // Relógio do prazo. O pedido prende as poltronas por tempo limitado, e o
  // cliente precisa ver quanto resta em vez de descobrir que expirou ao clicar.
  useEffect(() => {
    if (pedido?.status !== "PENDING") return;
    const t = setInterval(() => setAgora(Date.now()), 1000);
    return () => clearInterval(t);
  }, [pedido?.status]);

  async function pagar(e: React.FormEvent) {
    e.preventDefault();
    setErro("");
    setPagando(true);
    try {
      const atualizado = await request<Order>(`/orders/${id}/pay`, {
        method: "POST",
        body: cartao,
      });
      setPedido(atualizado);
      if (atualizado.status === "PAID") {
        navigate("/meus-ingressos", { state: { recemComprado: atualizado.id } });
      }
    } catch (err) {
      setErro(err instanceof ApiError ? err.message : "Não foi possível pagar.");
    } finally {
      setPagando(false);
    }
  }

  async function cancelar() {
    const pago = pedido?.status === "PAID";
    const aviso = pago
      ? "Cancelar esta compra? As poltronas voltam para o estoque e os ingressos deixam de valer."
      : "Cancelar este pedido? As poltronas voltam para o estoque.";
    if (!window.confirm(aviso)) return;

    setErro("");
    setCancelando(true);
    try {
      setPedido(await request<Order>(`/orders/${id}/cancel`, { method: "POST" }));
    } catch (err) {
      setErro(err instanceof ApiError ? err.message : "Não foi possível cancelar.");
    } finally {
      setCancelando(false);
    }
  }

  if (carregando) return <Carregando texto="Carregando pedido" />;

  if (!pedido) {
    return (
      <section className="stack" style={{ gap: "var(--space-4)", maxWidth: "50ch" }}>
        <h1>Pedido não encontrado</h1>
        <p className="muted">{erro}</p>
        <Link className="btn btn--ghost" to="/em-cartaz" style={{ alignSelf: "flex-start" }}>
          Voltar ao cartaz
        </Link>
      </section>
    );
  }

  const expirado = pedido.expires_at ? new Date(pedido.expires_at).getTime() <= agora : false;
  const podePagar = pedido.status === "PENDING" && !expirado;

  return (
    <section className="stack" style={{ gap: "var(--space-6)", maxWidth: "44rem" }}>
      <header className="stack" style={{ gap: "var(--space-2)" }}>
        <h1>Pagamento</h1>
        <p className="muted">
          {pedido.movie_title} — {dataHora(pedido.starts_at)} — {pedido.room_name}
        </p>
      </header>

      <div className="resumo">
        <h2 className="resumo__titulo">Seu pedido</h2>
        <ul className="resumo__itens">
          {pedido.tickets.map((t) => (
            <li key={t.id}>
              <span>
                {t.sector_name} · poltrona <strong>{t.seat_code}</strong>
              </span>
              <span>{reais(t.price_cents)}</span>
            </li>
          ))}
        </ul>
        <p className="resumo__total">
          <span>Total</span>
          <strong>{reais(pedido.total_cents)}</strong>
        </p>
      </div>

      {pedido.status === "DECLINED" && (
        <div className="alert alert--error" role="alert">
          <div className="stack" style={{ gap: "var(--space-2)" }}>
            <strong>Pagamento recusado — {pedido.decline_reason}</strong>
            <span>
              As poltronas voltaram para o estoque e nenhum ingresso foi emitido.{" "}
              <Link to={`/sessao/${pedido.session_id}`}>Escolher os lugares de novo</Link>.
            </span>
          </div>
        </div>
      )}

      {(pedido.status === "EXPIRED" || expirado) && (
        <div className="alert alert--error" role="alert">
          <span>
            O prazo para pagar acabou e as poltronas voltaram ao estoque.{" "}
            <Link to={`/sessao/${pedido.session_id}`}>Escolher de novo</Link>.
          </span>
        </div>
      )}

      {pedido.status === "CANCELLED" && (
        <div className="alert alert--error">
          <span>
            Este pedido foi cancelado e as poltronas voltaram para o estoque.{" "}
            <Link to={`/sessao/${pedido.session_id}`}>Escolher de novo</Link>.
          </span>
        </div>
      )}

      {/* Compra paga também pode ser cancelada: é o opcional de devolução ao
          estoque que o enunciado lista, e o back já garante que ingresso já
          utilizado na portaria não é desfeito. */}
      {pedido.status === "PAID" && (
        <div className="cancelamento">
          <div className="stack" style={{ gap: "2px" }}>
            <strong style={{ fontSize: "var(--text-sm)" }}>Mudou de ideia?</strong>
            <span className="faint" style={{ fontSize: "var(--text-xs)" }}>
              As poltronas voltam para o estoque e os ingressos deixam de valer.
            </span>
          </div>
          <button
            className="btn btn--ghost btn--perigo btn--mini"
            type="button"
            onClick={cancelar}
            disabled={cancelando}
          >
            {cancelando ? "Cancelando…" : "Cancelar compra"}
          </button>
        </div>
      )}

      {podePagar && (
        <>
          {pedido.expires_at && (
            <p className="prazo" role="status">
              As poltronas ficam reservadas por mais{" "}
              <strong>{tempoRestante(pedido.expires_at)}</strong>
            </p>
          )}

          {erro && (
            <p className="alert alert--error" role="alert">
              {erro}
            </p>
          )}

          <form className="stack" style={{ gap: "var(--space-4)" }} onSubmit={pagar}>
            <Campo
              label="Número do cartão"
              name="card_number"
              inputMode="numeric"
              autoComplete="off"
              required
              placeholder="0000 0000 0000 0000"
              value={cartao.card_number}
              onChange={(e) => setCartao({ ...cartao, card_number: e.target.value })}
            />
            <Campo
              label="Nome impresso no cartão"
              name="card_holder"
              autoComplete="off"
              required
              minLength={2}
              placeholder="Como está no cartão"
              value={cartao.card_holder}
              onChange={(e) => setCartao({ ...cartao, card_holder: e.target.value })}
            />

            <div className="rodape-acao">
              <button
                className="btn btn--ghost btn--perigo"
                type="button"
                onClick={cancelar}
                disabled={pagando || cancelando}
              >
                {cancelando ? "Cancelando…" : "Cancelar pedido"}
              </button>
              <button className="btn btn--primary" type="submit" disabled={pagando}>
                {pagando ? "Processando…" : `Pagar ${reais(pedido.total_cents)}`}
              </button>
            </div>
          </form>

          <div className="simulado">
            <p className="simulado__aviso">
              Pagamento simulado — nenhuma cobrança é feita. Use um destes cartões:
            </p>
            <ul className="simulado__lista">
              {CARTOES.map((c) => (
                <li key={c.numero}>
                  <button
                    type="button"
                    className="simulado__cartao"
                    onClick={() =>
                      setCartao({ card_number: c.numero, card_holder: cartao.card_holder || "TESTE" })
                    }
                  >
                    <code>{c.numero}</code>
                    <span className="faint">{c.efeito}</span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </>
      )}
    </section>
  );
}
