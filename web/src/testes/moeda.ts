/**
 * Normaliza o espaço da moeda.
 *
 * O Intl usa espaço não separável (U+00A0) entre "R$" e o valor. Comparar com
 * espaço comum falha de um jeito confuso — os dois lados aparecem idênticos na
 * mensagem de erro.
 */
export function semNbsp(texto: string | null | undefined): string {
  return (texto ?? "").replace(/ /g, " ");
}
