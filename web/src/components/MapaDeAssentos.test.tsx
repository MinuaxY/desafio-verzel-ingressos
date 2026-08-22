import { semNbsp } from "../testes/moeda";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { Mock } from "vitest";

import { MapaDeAssentos } from "./MapaDeAssentos";
import type { Escolha } from "./MapaDeAssentos";
import type { Seat, SectorMap, SeatKind } from "../lib/tipos";

function poltronas(
  letras: string[],
  porFileira: number,
  extras: { ocupadas?: string[]; tipos?: Record<string, SeatKind> } = {},
): Seat[] {
  const { ocupadas = [], tipos = {} } = extras;
  return letras.flatMap((letra) =>
    Array.from({ length: porFileira }, (_, i) => {
      const code = `${letra}${i + 1}`;
      return { code, taken: ocupadas.includes(code), kind: tipos[code] ?? null };
    }),
  );
}

function setor(over: Partial<SectorMap> = {}): SectorMap {
  return {
    id: "setor-plateia",
    name: "Plateia",
    rows: 2,
    seats_per_row: 12,
    display_order: 0,
    price_cents: 3000,
    aisles: [3, 9],
    seats: poltronas(["A", "B"], 12),
    ...over,
  };
}

function monta(
  over: {
    setores?: SectorMap[];
    escolhidos?: Escolha[];
    maximo?: number;
    onAlternar?: Mock;
  } = {},
) {
  const onAlternar: Mock = over.onAlternar ?? vi.fn();
  render(
    <MapaDeAssentos
      setores={over.setores ?? [setor()]}
      escolhidos={over.escolhidos ?? []}
      onAlternar={onAlternar}
      maximo={over.maximo ?? 10}
    />,
  );
  return { onAlternar };
}

/** Acha uma poltrona pelo código exato.
 *
 *  A vírgula é obrigatória na expressão: sem ela, /Poltrona A1/ casaria também
 *  com A10, A11 e A12, e o teste falharia por ambiguidade em vez de por
 *  defeito. */
function poltrona(codigo: string) {
  return screen.getByLabelText(new RegExp(`Poltrona ${codigo},`));
}

/** As poltronas de uma fileira, na ordem em que aparecem na tela. */
function fileira(letra: string) {
  return screen
    .getAllByRole("button")
    .filter((b) => b.getAttribute("aria-label")?.startsWith(`Poltrona ${letra}`));
}

describe("orientação da sala", () => {
  it("a tela fica depois das poltronas no documento", () => {
    // A tela embaixo e as fileiras crescendo para cima é como se lê uma planta
    // de sala. Ver decisão D23.
    const { container } = render(
      <MapaDeAssentos setores={[setor()]} escolhidos={[]} onAlternar={vi.fn()} maximo={10} />,
    );
    const sala = container.querySelector(".sala")!;
    const posicaoTela = [...sala.children].findIndex((el) => el.classList.contains("tela"));
    const posicaoSetor = [...sala.children].findIndex((el) => el.classList.contains("setor"));
    expect(posicaoTela).toBeGreaterThan(posicaoSetor);
  });

  it("as fileiras aparecem da mais ao fundo para a mais próxima da tela", () => {
    const { container } = render(
      <MapaDeAssentos setores={[setor()]} escolhidos={[]} onAlternar={vi.fn()} maximo={10} />,
    );
    const letras = [...container.querySelectorAll(".fileira")].map(
      (f) => f.querySelector(".fileira__letra")?.textContent,
    );
    expect(letras).toEqual(["B", "A"]);
  });

  it("o setor mais ao fundo é desenhado primeiro", () => {
    const vip = setor({
      id: "setor-vip",
      name: "VIP",
      display_order: 1,
      rows: 1,
      seats_per_row: 8,
      aisles: [],
      seats: poltronas(["C"], 8),
    });
    const { container } = render(
      <MapaDeAssentos setores={[setor(), vip]} escolhidos={[]} onAlternar={vi.fn()} maximo={10} />,
    );
    const nomes = [...container.querySelectorAll(".setor__nome")].map((n) => n.textContent);
    expect(nomes).toEqual(["VIP", "Plateia"]);
  });

  it("a letra da fileira aparece nas duas pontas", () => {
    const { container } = render(
      <MapaDeAssentos setores={[setor()]} escolhidos={[]} onAlternar={vi.fn()} maximo={10} />,
    );
    const primeira = container.querySelector(".fileira")!;
    expect(primeira.querySelectorAll(".fileira__letra")).toHaveLength(2);
  });
});

describe("corredores", () => {
  it("dividem a fileira nos blocos certos", () => {
    // 12 poltronas com corredores em 3 e 9 viram 3, 6 e 3. Ver decisão D25.
    const { container } = render(
      <MapaDeAssentos setores={[setor()]} escolhidos={[]} onAlternar={vi.fn()} maximo={10} />,
    );
    const blocos = [...container.querySelector(".fileira")!.querySelectorAll(".bloco")];
    expect(blocos.map((b) => b.querySelectorAll(".poltrona").length)).toEqual([3, 6, 3]);
  });

  it("sem corredor, a fileira é um bloco só", () => {
    const { container } = render(
      <MapaDeAssentos
        setores={[setor({ aisles: [] })]}
        escolhidos={[]}
        onAlternar={vi.fn()}
        maximo={10}
      />,
    );
    const blocos = container.querySelector(".fileira")!.querySelectorAll(".bloco");
    expect(blocos).toHaveLength(1);
    expect(blocos[0].querySelectorAll(".poltrona")).toHaveLength(12);
  });

  it("corredor fora da fileira é ignorado em vez de gerar bloco vazio", () => {
    const { container } = render(
      <MapaDeAssentos
        setores={[setor({ aisles: [0, 12, 99] })]}
        escolhidos={[]}
        onAlternar={vi.fn()}
        maximo={10}
      />,
    );
    expect(container.querySelector(".fileira")!.querySelectorAll(".bloco")).toHaveLength(1);
  });

  it("nenhuma poltrona se perde ao dividir em blocos", () => {
    const { container } = render(
      <MapaDeAssentos setores={[setor()]} escolhidos={[]} onAlternar={vi.fn()} maximo={10} />,
    );
    const primeira = container.querySelector(".fileira")!;
    expect(primeira.querySelectorAll(".poltrona")).toHaveLength(12);
  });
});

describe("estados da poltrona", () => {
  it("livre mostra o número, sem a letra", () => {
    monta();
    expect(fileira("A")[0]).toHaveTextContent("1");
  });

  it("ocupada não é clicável", async () => {
    const { onAlternar } = monta({
      setores: [setor({ seats: poltronas(["A", "B"], 12, { ocupadas: ["A5"] }) })],
    });

    const a5 = screen.getByLabelText(/Poltrona A5.*ocupada/);
    expect(a5).toBeDisabled();

    await userEvent.click(a5);
    expect(onAlternar).not.toHaveBeenCalled();
  });

  it("ocupada mostra a silhueta em vez do número", () => {
    // Ver decisão D24: a figura de uma pessoa não pede tradução.
    const { container } = render(
      <MapaDeAssentos
        setores={[setor({ seats: poltronas(["A", "B"], 12, { ocupadas: ["A5"] }) })]}
        escolhidos={[]}
        onAlternar={vi.fn()}
        maximo={10}
      />,
    );
    const a5 = screen.getByLabelText(/Poltrona A5.*ocupada/);
    expect(a5.querySelector("svg")).toBeTruthy();
    expect(a5).not.toHaveTextContent("5");
    expect(container.querySelectorAll(".poltrona--ocupada svg").length).toBeGreaterThan(0);
  });

  it("acessível mostra a sigla, não só a cor", () => {
    // Interface de acessibilidade que depende de matiz é inacessível por
    // construção. Ver decisão D16.
    monta({
      setores: [
        setor({
          seats: poltronas(["A", "B"], 12, {
            tipos: { A1: "WHEELCHAIR", A2: "COMPANION", A3: "OBESE", B1: "REDUCED_MOBILITY" },
          }),
        }),
      ],
    });

    expect(screen.getByLabelText(/Poltrona A2.*acompanhante/i)).toHaveTextContent("AC");
    expect(screen.getByLabelText(/Poltrona A3.*largo/i)).toHaveTextContent("AL");
    expect(screen.getByLabelText(/Poltrona B1.*Mobilidade reduzida/i)).toHaveTextContent("MR");
  });

  it("o rótulo diz poltrona, setor, natureza e preço", () => {
    monta({
      setores: [setor({ seats: poltronas(["A", "B"], 12, { tipos: { A1: "WHEELCHAIR" } }) })],
    });
    const rotulo = poltrona("A1").getAttribute("aria-label")!;
    expect(rotulo).toContain("Plateia");
    expect(rotulo).toMatch(/cadeira de rodas/i);
    expect(rotulo).toMatch(/R\$/);
  });

  it("ocupada e acessível ao mesmo tempo: o rótulo mantém as duas informações", () => {
    monta({
      setores: [
        setor({
          seats: poltronas(["A", "B"], 12, {
            ocupadas: ["A1"],
            tipos: { A1: "REDUCED_MOBILITY" },
          }),
        }),
      ],
    });
    const rotulo = poltrona("A1").getAttribute("aria-label")!;
    expect(rotulo).toMatch(/Mobilidade reduzida/i);
    expect(rotulo).toMatch(/ocupada/i);
  });
});

describe("seleção", () => {
  it("clicar avisa qual setor e qual poltrona", async () => {
    const { onAlternar } = monta();

    await userEvent.click(screen.getByLabelText(/Poltrona A4/));

    expect(onAlternar).toHaveBeenCalledTimes(1);
    const [setorClicado, assento] = onAlternar.mock.calls[0];
    expect(setorClicado.name).toBe("Plateia");
    expect(assento.code).toBe("A4");
  });

  it("escolhida fica marcada como pressionada", () => {
    monta({ escolhidos: [{ sectorId: "setor-plateia", code: "A4", priceCents: 3000 }] });
    expect(screen.getByLabelText(/Poltrona A4/)).toHaveAttribute("aria-pressed", "true");
  });

  it("no limite, as não escolhidas ficam bloqueadas", async () => {
    const { onAlternar } = monta({
      escolhidos: [{ sectorId: "setor-plateia", code: "A1", priceCents: 3000 }],
      maximo: 1,
    });

    expect(screen.getByLabelText(/Poltrona A2/)).toBeDisabled();

    await userEvent.click(screen.getByLabelText(/Poltrona A2/));
    expect(onAlternar).not.toHaveBeenCalled();
  });

  it("no limite, a já escolhida continua clicável para desmarcar", async () => {
    // Se ela travasse junto, o usuário ficaria preso na própria escolha.
    const { onAlternar } = monta({
      escolhidos: [{ sectorId: "setor-plateia", code: "A1", priceCents: 3000 }],
      maximo: 1,
    });

    const a1 = poltrona("A1");
    expect(a1).not.toBeDisabled();

    await userEvent.click(a1);
    expect(onAlternar).toHaveBeenCalledTimes(1);
  });

  it("a mesma poltrona em setores diferentes não se confunde", () => {
    // As fileiras são contínuas na sala, mas o teste garante que a seleção
    // considera o setor, e não só o código. Ver decisão D23.
    const vip = setor({
      id: "setor-vip",
      name: "VIP",
      display_order: 1,
      rows: 1,
      seats_per_row: 4,
      aisles: [],
      seats: poltronas(["C"], 4),
    });
    monta({
      setores: [setor(), vip],
      escolhidos: [{ sectorId: "setor-vip", code: "C1", priceCents: 5000 }],
    });

    expect(screen.getByLabelText(/Poltrona C1, VIP/)).toHaveAttribute("aria-pressed", "true");
    expect(poltrona("A1")).toHaveAttribute("aria-pressed", "false");
  });
});

describe("legenda", () => {
  it("explica os três estados e as quatro naturezas", () => {
    const { container } = render(
      <MapaDeAssentos setores={[setor()]} escolhidos={[]} onAlternar={vi.fn()} maximo={10} />,
    );
    const legenda = container.querySelector(".legenda")!;

    for (const texto of ["Livre", "Escolhida", "Ocupada"]) {
      expect(within(legenda as HTMLElement).getByText(texto)).toBeTruthy();
    }
    expect(within(legenda as HTMLElement).getByText(/cadeira de rodas/i)).toBeTruthy();
    expect(within(legenda as HTMLElement).getByText(/assento largo/i)).toBeTruthy();
  });

  it("a amostra de ocupada traz a silhueta, e não fica vazia", () => {
    // Ela sumia justamente aqui, sozinha e fora do contexto do mapa.
    const { container } = render(
      <MapaDeAssentos setores={[setor()]} escolhidos={[]} onAlternar={vi.fn()} maximo={10} />,
    );
    const amostra = container.querySelector(".legenda .poltrona--ocupada")!;
    expect(amostra.querySelector("svg")).toBeTruthy();
  });
});

describe("preço do setor", () => {
  it("aparece no cabeçalho de cada setor", () => {
    const vip = setor({
      id: "setor-vip",
      name: "VIP",
      display_order: 1,
      price_cents: 5400,
      rows: 1,
      seats_per_row: 4,
      aisles: [],
      seats: poltronas(["C"], 4),
    });
    const { container } = render(
      <MapaDeAssentos setores={[setor(), vip]} escolhidos={[]} onAlternar={vi.fn()} maximo={10} />,
    );
    const precos = [...container.querySelectorAll(".setor__preco")].map((p) =>
      semNbsp(p.textContent),
    );
    expect(precos).toEqual(["R$ 54,00", "R$ 30,00"]);
  });
});
