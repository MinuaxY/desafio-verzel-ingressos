/** Formatação para exibição. Um lugar só, para a moeda e a data saírem
 *  iguais em toda a aplicação. */

const MOEDA = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });

/** Recebe centavos, devolve reais. Ver decisão D14. */
export function reais(centavos: number): string {
  return MOEDA.format(centavos / 100);
}

export function faixaDePreco(min: number | null, max: number | null): string {
  if (min === null) return "—";
  if (max === null || min === max) return reais(min);
  return `${reais(min)} a ${reais(max)}`;
}

const DATA_HORA = new Intl.DateTimeFormat("pt-BR", {
  weekday: "short",
  day: "2-digit",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
});

const DATA_CURTA = new Intl.DateTimeFormat("pt-BR", {
  day: "2-digit",
  month: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
});

export function dataHora(iso: string): string {
  return DATA_HORA.format(new Date(iso)).replace(".", "");
}

export function dataCurta(iso: string): string {
  return DATA_CURTA.format(new Date(iso));
}

export function duracao(minutos: number | null): string {
  if (!minutos) return "";
  const h = Math.floor(minutos / 60);
  const m = minutos % 60;
  return h > 0 ? `${h}h${m > 0 ? ` ${m}min` : ""}` : `${m}min`;
}

/** Quanto falta, em texto curto. Usado no relógio do checkout. */
export function tempoRestante(iso: string): string {
  const restam = Math.max(0, new Date(iso).getTime() - Date.now());
  const total = Math.floor(restam / 1000);
  const min = Math.floor(total / 60);
  const seg = total % 60;
  return `${min}:${String(seg).padStart(2, "0")}`;
}
