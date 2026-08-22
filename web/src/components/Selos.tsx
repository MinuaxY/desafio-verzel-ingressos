import type { AudioType, ScreenFormat } from "../lib/tipos";
import { AUDIO, FORMATO, classificacao } from "../lib/tipos";

/**
 * Classificação indicativa.
 *
 * As cores são as do sistema brasileiro (verde para livre, subindo até preto
 * para dezoito anos), porque é assim que as pessoas reconhecem a faixa sem ler
 * o número. Mas o número está sempre escrito: só a cor não bastaria para quem
 * não distingue matiz, e a informação é importante demais para depender disso.
 */
export function Classificacao({ valor, tamanho = "normal" }: {
  valor: string | null;
  tamanho?: "normal" | "mini";
}) {
  const info = classificacao(valor);

  return (
    <span
      className={tamanho === "mini" ? "classind classind--mini" : "classind"}
      style={{ background: info.cor, color: info.texto }}
      title={info.descricao}
      aria-label={`Classificação indicativa: ${info.descricao}`}
    >
      {info.rotulo}
    </span>
  );
}

/** Como a sessão é exibida: áudio e formato de tela. */
export function SelosDaSessao({
  audio,
  formato,
  className = "",
}: {
  audio: AudioType;
  formato: ScreenFormat;
  className?: string;
}) {
  return (
    <span className={`selos ${className}`}>
      <span className="selo-sessao">{AUDIO[audio]}</span>
      <span className="selo-sessao selo-sessao--formato">{FORMATO[formato]}</span>
    </span>
  );
}
