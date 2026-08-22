import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { BarraDeDias } from "./BarraDeDias";
import type { DayInCartaz } from "../lib/tipos";

/** Data local daqui a N dias, no formato que o componente usa.
 *
 *  Os testes trabalham com datas relativas ao dia real em vez de congelar o
 *  relógio: `useFakeTimers` paralisa também os temporizadores internos do
 *  userEvent, e o clique nunca completa. */
function daquiA(dias: number): string {
  const d = new Date();
  d.setHours(12, 0, 0, 0);
  d.setDate(d.getDate() + dias);
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

/** O rótulo que o componente escreve para a data, para achar o botão. */
function rotuloDe(dias: number): RegExp {
  const d = new Date();
  d.setDate(d.getDate() + dias);
  const mes = d.toLocaleDateString("pt-BR", { month: "long" });
  return new RegExp(`${d.getDate()} de ${mes}`, "i");
}

afterEach(() => vi.useRealTimers());

function monta(dias: DayInCartaz[], selecionado: string | null = null) {
  const onSelecionar = vi.fn();
  render(<BarraDeDias dias={dias} selecionado={selecionado} onSelecionar={onSelecionar} />);
  return { onSelecionar };
}

describe("barra de dias", () => {
  it("não aparece quando não há sessão nenhuma à frente", () => {
    // Uma barra de datas sem nenhuma data clicável só ocupa espaço.
    const { container } = render(
      <BarraDeDias dias={[]} selecionado={null} onSelecionar={vi.fn()} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("mostra duas semanas mais o atalho de todos os dias", () => {
    monta([{ date: daquiA(1), total: 2 }]);
    expect(screen.getAllByRole("button")).toHaveLength(15);
  });

  it("o primeiro dia é rotulado como Hoje", () => {
    monta([{ date: daquiA(0), total: 1 }]);
    expect(screen.getByText("Hoje")).toBeInTheDocument();
  });

  it("dia com sessão é clicável e avisa qual foi", async () => {
    const { onSelecionar } = monta([{ date: daquiA(2), total: 3 }]);

    await userEvent.click(screen.getByLabelText(new RegExp(`${rotuloDe(2).source}, 3 sessões`, "i")));
    expect(onSelecionar).toHaveBeenCalledWith(daquiA(2));
  });

  it("dia sem sessão fica visível mas não aceita clique", async () => {
    // Continua na tela para não abrir buraco na sequência de datas, mas
    // oferecer o clique que não leva a nada seria pior.
    const { onSelecionar } = monta([{ date: daquiA(2), total: 1 }]);

    const vazio = screen.getByLabelText(new RegExp(`${rotuloDe(3).source}, sem sessões`, "i"));
    expect(vazio).toBeDisabled();

    await userEvent.click(vazio);
    expect(onSelecionar).not.toHaveBeenCalled();
  });

  it("o rótulo diz quantas sessões o dia tem", () => {
    monta([{ date: daquiA(1), total: 1 }]);
    expect(
      screen.getByLabelText(new RegExp(`${rotuloDe(1).source}, 1 sessão$`, "i")),
    ).toBeInTheDocument();
  });

  it("o dia escolhido fica marcado", () => {
    monta([{ date: daquiA(2), total: 2 }], daquiA(2));

    expect(screen.getByLabelText(rotuloDe(2))).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: /todos/i })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
  });

  it("sem dia escolhido, 'Todos os dias' é que está marcado", () => {
    monta([{ date: daquiA(2), total: 2 }], null);
    expect(screen.getByRole("button", { name: /todos/i })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  it("'Todos os dias' limpa o filtro", async () => {
    const { onSelecionar } = monta([{ date: daquiA(2), total: 2 }], daquiA(2));

    await userEvent.click(screen.getByRole("button", { name: /todos/i }));
    expect(onSelecionar).toHaveBeenCalledWith(null);
  });

  it("a data não escorrega para o dia seguinte à noite", () => {
    // `toISOString()` converteria para UTC: às 22h no Brasil, o dia 22 viraria
    // 23, e a barra ofereceria amanhã como se fosse hoje.
    //
    // Aqui o relógio precisa mesmo ser congelado, então o clique é disparado
    // com fireEvent, que não depende de temporizador.
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 7, 22, 22, 30));

    const onSelecionar = vi.fn();
    render(
      <BarraDeDias
        dias={[{ date: "2026-08-22", total: 1 }]}
        selecionado={null}
        onSelecionar={onSelecionar}
      />,
    );

    fireEvent.click(screen.getByLabelText(/22 de agosto, 1 sessão/i));
    expect(onSelecionar).toHaveBeenCalledWith("2026-08-22");
  });
});
