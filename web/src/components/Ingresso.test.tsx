import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Ingresso } from "./Ingresso";
import type { TicketDetail } from "../lib/tipos";

function ingresso(over: Partial<TicketDetail> = {}): TicketDetail {
  return {
    id: "t1",
    seat_code: "C9",
    sector_name: "Plateia",
    seat_kind: null,
    price_cents: 3200,
    status: "VALID",
    used_at: null,
    code: "ABCDEF123456.XYZ789",
    share_token: "11111111-2222-3333-4444-555555555555",
    movie_title: "A Odisseia",
    movie_poster_url: null,
    starts_at: "2026-08-25T00:30:00Z",
    room_name: "Sala 1",
    room_location: "Av. Paulista, 1000",
    ...over,
  };
}

describe("ingresso válido", () => {
  it("mostra filme, sala e poltrona", () => {
    render(<Ingresso ingresso={ingresso()} />);

    expect(screen.getByText("A Odisseia")).toBeInTheDocument();
    expect(screen.getByText("C9")).toBeInTheDocument();
    expect(screen.getByText(/Sala 1/)).toBeInTheDocument();
  });

  it("desenha o QR e mostra o código escrito", async () => {
    // O código escrito existe porque a portaria digita quando a câmera falha.
    render(<Ingresso ingresso={ingresso()} />);

    expect(screen.getByText("ABCDEF123456.XYZ789")).toBeInTheDocument();
    expect(await screen.findByAltText(/código qr/i)).toBeInTheDocument();
  });

  it("poltrona acessível aparece identificada", () => {
    render(<Ingresso ingresso={ingresso({ seat_kind: "WHEELCHAIR" })} />);
    expect(screen.getByText(/cadeira de rodas/i)).toBeInTheDocument();
  });
});

describe("ingresso sem pagamento", () => {
  it("não mostra QR nem código", () => {
    // Reserva não paga não é documento: sem ingresso, sem QR.
    render(<Ingresso ingresso={ingresso({ code: null, share_token: null })} />);

    expect(screen.getByText(/aparece depois do pagamento/i)).toBeInTheDocument();
    expect(screen.queryByAltText(/código qr/i)).not.toBeInTheDocument();
  });
});

describe("ingresso já utilizado", () => {
  it("recebe o carimbo com a data", () => {
    render(
      <Ingresso ingresso={ingresso({ status: "USED", used_at: "2026-08-25T01:00:00Z" })} />,
    );
    expect(screen.getByText(/utilizado/i)).toBeInTheDocument();
  });
});

describe("compartilhar", () => {
  it("copia o link do ingresso", async () => {
    const escrever = vi.fn().mockResolvedValue(undefined);
    vi.stubGlobal("navigator", { ...navigator, clipboard: { writeText: escrever } });

    render(<Ingresso ingresso={ingresso()} />);
    await userEvent.click(screen.getByRole("button", { name: /copiar link/i }));

    expect(escrever).toHaveBeenCalledWith(
      expect.stringContaining("/ingresso/11111111-2222-3333-4444-555555555555"),
    );
  });

  it("copia o código para digitar na portaria", async () => {
    const escrever = vi.fn().mockResolvedValue(undefined);
    vi.stubGlobal("navigator", { ...navigator, clipboard: { writeText: escrever } });

    render(<Ingresso ingresso={ingresso()} />);
    await userEvent.click(screen.getByRole("button", { name: /copiar código/i }));

    expect(escrever).toHaveBeenCalledWith("ABCDEF123456.XYZ789");
  });

  it("quando aberto por link, não oferece compartilhar de novo", () => {
    // Quem chegou pelo link já tem o link; repetir a ação só polui a tela.
    render(<Ingresso ingresso={ingresso()} compartilhavel={false} />);

    expect(screen.queryByRole("button", { name: /copiar link/i })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /copiar código/i })).toBeInTheDocument();
  });

  it("área de transferência bloqueada não quebra a tela", async () => {
    // Alguns navegadores negam a permissão. O valor está visível de qualquer
    // forma, então não vale interromper com erro.
    vi.stubGlobal("navigator", {
      ...navigator,
      clipboard: { writeText: vi.fn().mockRejectedValue(new Error("negado")) },
    });

    render(<Ingresso ingresso={ingresso()} />);
    await userEvent.click(screen.getByRole("button", { name: /copiar código/i }));

    expect(screen.getByText("A Odisseia")).toBeInTheDocument();
  });
});
