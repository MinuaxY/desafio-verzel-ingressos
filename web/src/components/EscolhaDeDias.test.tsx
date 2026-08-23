import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { EscolhaDeDias } from "./EscolhaDeDias";

function monta(
  over: { base?: string; selecionados?: string[]; baseJaExiste?: boolean } = {},
) {
  const onMudar = vi.fn();
  render(
    <EscolhaDeDias
      baseISO={over.base ?? "2026-08-28"}
      hora="19:00"
      selecionados={over.selecionados ?? []}
      onMudar={onMudar}
      baseJaExiste={over.baseJaExiste}
    />,
  );
  return { onMudar };
}

describe("escolha de dias para repetir", () => {
  it("oferece quatro semanas a partir do dia principal", () => {
    monta();
    // 28 dias mais os três botões de atalho.
    expect(document.querySelectorAll(".repetir__dia")).toHaveLength(28);
  });

  it("o dia principal já vem marcado e não sai", async () => {
    // Desmarcá-lo aqui não cancelaria a sessão, só confundiria.
    const { onMudar } = monta({ base: "2026-08-28" });

    const base = screen.getByLabelText(/28 de agosto, horário principal/i);
    expect(base).toBeDisabled();
    expect(base).toHaveAttribute("aria-pressed", "true");

    await userEvent.click(base);
    expect(onMudar).not.toHaveBeenCalled();
  });

  it("clicar num dia acrescenta à lista", async () => {
    const { onMudar } = monta({ base: "2026-08-28" });

    await userEvent.click(screen.getByLabelText(/^29 de agosto$/i));
    expect(onMudar).toHaveBeenCalledWith(["2026-08-29"]);
  });

  it("clicar de novo remove", async () => {
    const { onMudar } = monta({ base: "2026-08-28", selecionados: ["2026-08-29"] });

    await userEvent.click(screen.getByLabelText(/^29 de agosto$/i));
    expect(onMudar).toHaveBeenCalledWith([]);
  });

  it("o atalho do dia da semana marca as semanas seguintes", async () => {
    // 28/08/2026 é sexta.
    const { onMudar } = monta({ base: "2026-08-28" });

    await userEvent.click(screen.getByRole("button", { name: /toda sex/i }));

    const escolhidos = onMudar.mock.calls[0][0];
    expect(escolhidos).toEqual(["2026-09-04", "2026-09-11", "2026-09-18"]);
    expect(escolhidos).not.toContain("2026-08-28");
  });

  it("o atalho de fim de semana pega sexta, sábado e domingo", async () => {
    const { onMudar } = monta({ base: "2026-08-28" });

    await userEvent.click(screen.getByRole("button", { name: /sextas, sábados e domingos/i }));

    const escolhidos: string[] = onMudar.mock.calls[0][0];
    // Todos caem em sexta (5), sábado (6) ou domingo (0).
    for (const iso of escolhidos) {
      const [a, m, d] = iso.split("-").map(Number);
      expect([0, 5, 6]).toContain(new Date(a, m - 1, d).getDay());
    }
    expect(escolhidos).not.toContain("2026-08-28");
  });

  it("mostra quantas sessões serão criadas, contando a principal", () => {
    monta({ selecionados: ["2026-08-29", "2026-08-30"] });
    expect(screen.getByText(/3 sessões/)).toBeInTheDocument();
  });

  it("com dias marcados, aparece o atalho de limpar", async () => {
    const { onMudar } = monta({ selecionados: ["2026-08-29"] });

    await userEvent.click(screen.getByRole("button", { name: /limpar/i }));
    expect(onMudar).toHaveBeenCalledWith([]);
  });

  it("sem dias marcados, não há o que limpar", () => {
    monta({ selecionados: [] });
    expect(screen.queryByRole("button", { name: /limpar/i })).not.toBeInTheDocument();
  });

  it("avisa que dia ocupado é pulado, não perdido", () => {
    monta();
    expect(screen.getByText(/é pulado/i)).toBeInTheDocument();
  });

  it("na edição a contagem não soma o dia base, que já existe", () => {
    // A tela de edição repete a partir de uma sessão que já está criada.
    // Prometer "3 sessões" e entregar 2 seria mentira pequena e irritante.
    monta({ selecionados: ["2026-08-29", "2026-08-30"], baseJaExiste: true });

    expect(screen.getByText(/2 sessões/)).toBeInTheDocument();
    expect(screen.queryByText(/3 sessões/)).not.toBeInTheDocument();
  });

  it("na edição, uma sessão só é dita no singular", () => {
    monta({ selecionados: ["2026-08-29"], baseJaExiste: true });
    expect(screen.getByText(/1 sessão/)).toBeInTheDocument();
  });

  it("na edição o dia base é apresentado como esta sessão", () => {
    monta({ base: "2026-08-28", baseJaExiste: true });

    expect(screen.getByLabelText(/28 de agosto, esta sessão/i)).toBeDisabled();
    expect(screen.getByText(/o dia em destaque é o desta sessão/i)).toBeInTheDocument();
  });

  it("na criação o dia base continua sendo o horário principal", () => {
    monta({ base: "2026-08-28" });

    expect(screen.getByLabelText(/28 de agosto, horário principal/i)).toBeInTheDocument();
    expect(screen.queryByText(/o dia em destaque/i)).not.toBeInTheDocument();
  });

  it("data inválida não quebra a tela", () => {
    const { container } = render(
      <EscolhaDeDias baseISO="" hora="" selecionados={[]} onMudar={vi.fn()} />,
    );
    expect(container.firstChild).toBeNull();
  });
});
