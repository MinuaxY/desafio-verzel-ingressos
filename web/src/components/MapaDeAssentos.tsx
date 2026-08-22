import { ASSENTO } from "../lib/tipos";
import type { SectorMap, Seat } from "../lib/tipos";
import { reais } from "../lib/formato";

/**
 * Silhueta de quem já está sentado.
 *
 * Marcar poltrona vendida com símbolo abstrato — risco, hachura, X — sempre
 * exigiu um segundo de tradução. A figura de uma pessoa não exige nenhum: o
 * lugar está ocupado porque tem alguém nele. É o que os mapas de assento de
 * cinema usam, e por esse motivo.
 */
function Ocupante() {
  return (
    <svg viewBox="0 0 16 16" width="13" height="13" aria-hidden="true" focusable="false">
      <circle cx="8" cy="5" r="3.1" fill="currentColor" />
      <path d="M2.4 15c0-3.4 2.5-5.6 5.6-5.6s5.6 2.2 5.6 5.6Z" fill="currentColor" />
    </svg>
  );
}

export interface Escolha {
  sectorId: string;
  code: string;
  priceCents: number;
}

/**
 * Mapa da sala.
 *
 * As poltronas acessíveis são marcadas com sigla e borda tracejada, além da
 * cor: quem não distingue matiz precisa achá-las igual, e uma interface de
 * acessibilidade que depende de cor é inacessível por construção.
 * Ver decisão D16.
 */
export function MapaDeAssentos({
  setores,
  escolhidos,
  onAlternar,
  maximo,
}: {
  setores: SectorMap[];
  escolhidos: Escolha[];
  onAlternar: (setor: SectorMap, assento: Seat) => void;
  maximo: number;
}) {
  const selecionado = (setorId: string, code: string) =>
    escolhidos.some((e) => e.sectorId === setorId && e.code === code);

  const cheio = escolhidos.length >= maximo;

  /* A tela fica embaixo, e as fileiras crescem para cima — é como se olha uma
     planta de sala, e é a convenção dos sites de cinema. A fileira A é a mais
     próxima da tela; quanto mais alto no desenho, mais ao fundo da sala.
     Por isso os setores são desenhados do fundo para a frente, e as fileiras
     de cada um em ordem decrescente. */
  const doFundoParaTela = [...setores].sort((a, b) => b.display_order - a.display_order);

  return (
    // A sala tem a largura do conteúdo e é centralizada: assim a tela fica
    // sobre as poltronas, e não sobre o container inteiro. Um mapa alinhado à
    // esquerda com a tela ao centro não corresponde a sala nenhuma.
    <div className="sala">
      {doFundoParaTela.map((setor) => (
        <div key={setor.id} className="setor">
          <div className="setor__cabecalho">
            <h3 className="setor__nome">{setor.name}</h3>
            <span className="setor__preco">{reais(setor.price_cents)}</span>
          </div>

          <div className="setor__grade" role="group" aria-label={`Poltronas do setor ${setor.name}`}>
            {agrupaPorFileira(setor)
              .reverse()
              .map(([fileira, assentos]) => (
                <div key={fileira} className="fileira">
                  {/* A letra aparece nas duas pontas, como em sala de verdade.
                      Além de ser o costume, mantém as poltronas centradas — com
                      a letra só à esquerda, a fileira inteira ficava deslocada. */}
                <span className="fileira__letra" aria-hidden="true">
                  {fileira}
                </span>
                {assentos.map((assento) => {
                  const marcado = selecionado(setor.id, assento.code);
                  const bloqueado = assento.taken || (cheio && !marcado);
                  const tipo = assento.kind ? ASSENTO[assento.kind] : null;

                  return (
                    <button
                      key={assento.code}
                      type="button"
                      className={[
                        "poltrona",
                        assento.taken && "poltrona--ocupada",
                        marcado && "poltrona--escolhida",
                        assento.kind && "poltrona--acessivel",
                      ]
                        .filter(Boolean)
                        .join(" ")}
                      disabled={bloqueado}
                      aria-pressed={marcado}
                      aria-label={
                        `Poltrona ${assento.code}, ${setor.name}` +
                        (tipo ? `, ${tipo.rotulo}` : "") +
                        (assento.taken ? ", ocupada" : `, ${reais(setor.price_cents)}`)
                      }
                      title={tipo?.rotulo}
                      onClick={() => onAlternar(setor, assento)}
                    >
                      {/* Ocupada mostra a silhueta, não o número: o que
                          interessa numa poltrona vendida é que já tem alguém
                          nela. O número segue no rótulo do leitor de tela. */}
                      {assento.taken ? (
                        <Ocupante />
                      ) : tipo ? (
                        tipo.sigla
                      ) : (
                        assento.code.replace(/^[A-Z]/, "")
                      )}
                    </button>
                  );
                })}
                <span className="fileira__letra" aria-hidden="true">
                  {fileira}
                </span>
                </div>
              ))}
          </div>
        </div>
      ))}

      <div className="tela" aria-hidden="true">
        <span>TELA</span>
      </div>

      <Legenda />
    </div>
  );
}

function agrupaPorFileira(setor: SectorMap): [string, Seat[]][] {
  const mapa = new Map<string, Seat[]>();
  for (const assento of setor.seats) {
    const fileira = assento.code[0];
    if (!mapa.has(fileira)) mapa.set(fileira, []);
    mapa.get(fileira)!.push(assento);
  }
  return [...mapa.entries()];
}

function Legenda() {
  return (
    <div className="legenda">
      <span className="legenda__item">
        <span className="poltrona poltrona--amostra" aria-hidden="true" />
        Livre
      </span>
      <span className="legenda__item">
        <span className="poltrona poltrona--escolhida poltrona--amostra" aria-hidden="true" />
        Escolhida
      </span>
      <span className="legenda__item">
        <span className="poltrona poltrona--ocupada poltrona--amostra" aria-hidden="true">
          <Ocupante />
        </span>
        Ocupada
      </span>
      {Object.entries(ASSENTO).map(([chave, { rotulo, sigla }]) => (
        <span className="legenda__item" key={chave}>
          <span className="poltrona poltrona--acessivel poltrona--amostra" aria-hidden="true">
            {sigla}
          </span>
          {rotulo}
        </span>
      ))}
    </div>
  );
}
