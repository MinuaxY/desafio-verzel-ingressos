import type { DayInCartaz } from "../lib/tipos";

const DIAS_NA_BARRA = 14;

const SEMANA = ["dom", "seg", "ter", "qua", "qui", "sex", "sáb"];

/** Data local no formato `YYYY-MM-DD`, sem passar por UTC.
 *
 *  `toISOString()` converteria para UTC e devolveria o dia seguinte para
 *  qualquer horário depois das 21h no Brasil — a barra mostraria amanhã como
 *  se fosse hoje. */
function comoData(d: Date): string {
  const mes = String(d.getMonth() + 1).padStart(2, "0");
  const dia = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${mes}-${dia}`;
}

/**
 * Escolha do dia, como nos sites de cinema.
 *
 * Mostra as próximas duas semanas, mas **desabilita os dias sem sessão**:
 * oferecer um dia vazio como se fosse opção é convidar o clique que não leva
 * a lugar nenhum. Quantas sessões cada dia tem vem do servidor.
 */
export function BarraDeDias({
  dias,
  selecionado,
  onSelecionar,
}: {
  dias: DayInCartaz[];
  selecionado: string | null;
  onSelecionar: (dia: string | null) => void;
}) {
  const porData = new Map(dias.map((d) => [d.date, d.total]));

  const hoje = new Date();
  hoje.setHours(0, 0, 0, 0);

  const datas = Array.from({ length: DIAS_NA_BARRA }, (_, i) => {
    const d = new Date(hoje);
    d.setDate(hoje.getDate() + i);
    return d;
  });

  // Nenhum dia à frente tem sessão: a barra não teria o que oferecer.
  if (porData.size === 0) return null;

  return (
    <div className="dias" role="group" aria-label="Escolher o dia">
      <button
        type="button"
        className={selecionado === null ? "dia dia--ativo dia--todos" : "dia dia--todos"}
        aria-pressed={selecionado === null}
        onClick={() => onSelecionar(null)}
      >
        <span className="dia__semana">Todos</span>
        <span className="dia__numero">os dias</span>
      </button>

      {datas.map((d, i) => {
        const chave = comoData(d);
        const total = porData.get(chave) ?? 0;
        const vazio = total === 0;
        const ativo = selecionado === chave;

        return (
          <button
            key={chave}
            type="button"
            className={[
              "dia",
              ativo && "dia--ativo",
              vazio && "dia--vazio",
              i === 0 && "dia--hoje",
            ]
              .filter(Boolean)
              .join(" ")}
            disabled={vazio}
            aria-pressed={ativo}
            aria-label={
              `${d.getDate()} de ${d.toLocaleDateString("pt-BR", { month: "long" })}` +
              (vazio ? ", sem sessões" : `, ${total} ${total === 1 ? "sessão" : "sessões"}`)
            }
            onClick={() => onSelecionar(chave)}
          >
            <span className="dia__semana">{i === 0 ? "Hoje" : SEMANA[d.getDay()]}</span>
            <span className="dia__numero">
              {String(d.getDate()).padStart(2, "0")}/{String(d.getMonth() + 1).padStart(2, "0")}
            </span>
          </button>
        );
      })}
    </div>
  );
}
