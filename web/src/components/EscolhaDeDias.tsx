const DIAS_OFERECIDOS = 28;
const SEMANA = ["dom", "seg", "ter", "qua", "qui", "sex", "sáb"];

/** Data local em `YYYY-MM-DD`, sem passar por UTC — `toISOString()` devolveria
 *  o dia seguinte para qualquer horário depois das 21h no Brasil. */
function comoData(d: Date): string {
  const mes = String(d.getMonth() + 1).padStart(2, "0");
  const dia = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${mes}-${dia}`;
}

function paraData(iso: string): Date {
  const [ano, mes, dia] = iso.split("-").map(Number);
  return new Date(ano, mes - 1, dia);
}

/**
 * Repetir a sessão em outros dias, no mesmo horário.
 *
 * Os dias são escolhidos um a um, e não por uma regra do tipo "toda sexta até
 * tal data". Programação de cinema não é regular — um filme roda de quinta a
 * domingo numa semana e só no fim de semana na seguinte —, e uma regra que não
 * cobre isso obrigaria a apagar depois o que ela criou a mais.
 * Ver decisão D27.
 */
export function EscolhaDeDias({
  baseISO,
  hora,
  selecionados,
  onMudar,
  baseJaExiste = false,
}: {
  /** O dia do horário principal, que já está marcado e não sai da lista. */
  baseISO: string;
  hora: string;
  selecionados: string[];
  onMudar: (dias: string[]) => void;
  /** Na edição o dia base é uma sessão que já existe, e não uma que será
   *  criada junto. Muda a contagem e o rótulo — dizer "serão criadas 3"
   *  quando só 2 nascem seria mentira pequena e irritante. */
  baseJaExiste?: boolean;
}) {
  const base = paraData(baseISO);
  if (Number.isNaN(base.getTime())) return null;

  const dias = Array.from({ length: DIAS_OFERECIDOS }, (_, i) => {
    const d = new Date(base);
    d.setDate(base.getDate() + i);
    return d;
  });

  function alternar(iso: string) {
    onMudar(
      selecionados.includes(iso)
        ? selecionados.filter((d) => d !== iso)
        : [...selecionados, iso],
    );
  }

  /** Marca de uma vez os mesmos dias da semana nas próximas quatro semanas. */
  function mesmoDiaDaSemana() {
    const iguais = dias
      .filter((d) => d.getDay() === base.getDay())
      .map(comoData)
      .filter((iso) => iso !== baseISO);
    onMudar(iguais);
  }

  function fimDeSemana() {
    const finais = dias
      .filter((d) => [0, 5, 6].includes(d.getDay()))
      .map(comoData)
      .filter((iso) => iso !== baseISO);
    onMudar(finais);
  }

  return (
    <details className="repetir" open={selecionados.length > 0}>
      <summary>
        Repetir em outros dias
        {selecionados.length > 0 && (
          <span className="repetir__contagem">+{selecionados.length}</span>
        )}
      </summary>

      <p className="faint" style={{ fontSize: "var(--text-xs)", margin: "var(--space-3) 0" }}>
        A mesma sessão, no mesmo horário{hora && ` (${hora})`}, nos dias marcados. Dia em que a
        sala já estiver ocupada é pulado, e você recebe a lista do que ficou de fora.
        {baseJaExiste && " O dia em destaque é o desta sessão, que já existe."}
      </p>

      <div className="repetir__atalhos">
        <button type="button" className="btn btn--ghost btn--mini" onClick={mesmoDiaDaSemana}>
          Toda {SEMANA[base.getDay()]}
        </button>
        <button type="button" className="btn btn--ghost btn--mini" onClick={fimDeSemana}>
          Sextas, sábados e domingos
        </button>
        {selecionados.length > 0 && (
          <button type="button" className="btn btn--ghost btn--mini" onClick={() => onMudar([])}>
            Limpar
          </button>
        )}
      </div>

      <div className="repetir__grade" role="group" aria-label="Dias para repetir a sessão">
        {dias.map((d) => {
          const iso = comoData(d);
          const ehBase = iso === baseISO;
          const marcado = ehBase || selecionados.includes(iso);

          return (
            <button
              key={iso}
              type="button"
              className={[
                "repetir__dia",
                marcado && "repetir__dia--marcado",
                ehBase && "repetir__dia--base",
              ]
                .filter(Boolean)
                .join(" ")}
              // O dia principal fica marcado e travado: tirá-lo daqui não
              // cancelaria a sessão, só confundiria.
              disabled={ehBase}
              aria-pressed={marcado}
              aria-label={
                `${d.getDate()} de ${d.toLocaleDateString("pt-BR", { month: "long" })}` +
                (ehBase ? (baseJaExiste ? ", esta sessão" : ", horário principal") : "")
              }
              onClick={() => alternar(iso)}
            >
              <span className="repetir__semana">{SEMANA[d.getDay()]}</span>
              <span className="repetir__numero">{String(d.getDate()).padStart(2, "0")}</span>
            </button>
          );
        })}
      </div>

      {selecionados.length > 0 && (
        <p className="repetir__resumo">
          {baseJaExiste ? (
            <>
              Serão criadas{" "}
              <strong>
                {selecionados.length} {selecionados.length === 1 ? "sessão" : "sessões"}
              </strong>
              , além desta.
            </>
          ) : (
            <>
              Serão criadas <strong>{selecionados.length + 1} sessões</strong>, contando o
              horário principal.
            </>
          )}
        </p>
      )}
    </details>
  );
}
