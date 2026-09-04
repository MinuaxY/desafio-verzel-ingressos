import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Confirmação de ação destrutiva, dentro da própria tela.
 *
 * Substitui o `window.confirm`, que **é suprimido em silêncio** em situações
 * mais comuns do que parece: dentro de iframe de outra origem, depois que o
 * navegador oferece "impedir esta página de criar mais diálogos", em webview de
 * aplicativo e no painel de pré-visualização usado no desenvolvimento. Nesses
 * casos ele devolve `false` na hora, sem nunca aparecer — e o botão fica morto,
 * sem nenhuma explicação, que é a pior forma de falhar. Ver decisão D42.
 *
 * O `<dialog>` do HTML é DOM comum, e não diálogo do navegador: ninguém o
 * suprime. E vem com o que interessa pronto — foco preso dentro dele, Esc para
 * sair e fundo inerte —, que uma div com `position: fixed` teria de imitar.
 */
export interface PedidoDeConfirmacao {
  titulo: string;
  descricao?: string;
  /** Rótulo do botão que confirma. "Excluir" diz mais do que "OK". */
  acao: string;
  perigo?: boolean;
}

export function useConfirmacao() {
  const [pedido, setPedido] = useState<PedidoDeConfirmacao | null>(null);
  const elemento = useRef<HTMLDialogElement>(null);
  const responder = useRef<((ok: boolean) => void) | null>(null);
  const resposta = useRef(false);

  const confirmar = useCallback((p: PedidoDeConfirmacao) => {
    resposta.current = false;
    setPedido(p);
    return new Promise<boolean>((ok) => {
      responder.current = ok;
    });
  }, []);

  useEffect(() => {
    if (pedido) elemento.current?.showModal();
  }, [pedido]);

  function fechar(ok: boolean) {
    resposta.current = ok;
    elemento.current?.close();
  }

  // Um ponto de saída só. O Esc fecha o `<dialog>` por conta própria, sem passar
  // por `fechar`, e sem isto a promessa ficaria pendente para sempre.
  function aoFechar() {
    setPedido(null);
    responder.current?.(resposta.current);
    responder.current = null;
    resposta.current = false;
  }

  const dialogo = (
    <dialog ref={elemento} className="confirmacao" onClose={aoFechar}>
      {pedido && (
        <div className="stack" style={{ gap: "var(--space-3)" }}>
          <h2 className="confirmacao__titulo">{pedido.titulo}</h2>
          {pedido.descricao && <p className="confirmacao__texto">{pedido.descricao}</p>}
          <div className="confirmacao__acoes">
            {/* Voltar vem primeiro no DOM de propósito: o `<dialog>` foca o
                primeiro elemento focável, e num passo destrutivo a tecla Enter
                sem querer deve desistir, não destruir. */}
            <button type="button" className="btn btn--ghost" onClick={() => fechar(false)}>
              Voltar
            </button>
            <button
              type="button"
              className={`btn ${pedido.perigo ? "btn--destruir" : "btn--primary"}`}
              onClick={() => fechar(true)}
            >
              {pedido.acao}
            </button>
          </div>
        </div>
      )}
    </dialog>
  );

  return { confirmar, dialogo };
}
