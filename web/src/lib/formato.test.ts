import { semNbsp } from "../testes/moeda";
import { describe, expect, it, vi, afterEach } from "vitest";

import { dataHora, duracao, faixaDePreco, reais, tempoRestante } from "./formato";

describe("reais", () => {
  it("converte centavos para moeda brasileira", () => {
    // O espaço do Intl é um non-breaking space, não o espaço comum.
    expect(semNbsp(reais(3200))).toBe("R$ 32,00");
    expect(semNbsp(reais(5400))).toBe("R$ 54,00");
  });

  it("não perde centavos", () => {
    expect(semNbsp(reais(1))).toBe("R$ 0,01");
    expect(semNbsp(reais(99))).toBe("R$ 0,99");
  });

  it("soma de centavos não produz dízima", () => {
    // O motivo de o sistema inteiro trabalhar com inteiros: 0.1 + 0.2 em
    // ponto flutuante daria 0.30000000000000004. Ver decisão D14.
    const total = 10 + 20;
    expect(semNbsp(reais(total))).toBe("R$ 0,30");
  });

  it("formata valores altos com separador de milhar", () => {
    expect(semNbsp(reais(123456))).toBe("R$ 1.234,56");
  });
});

describe("faixaDePreco", () => {
  it("mostra um valor só quando os dois são iguais", () => {
    expect(semNbsp(faixaDePreco(3200, 3200))).toBe("R$ 32,00");
  });

  it("mostra a faixa quando há setores com preços diferentes", () => {
    expect(semNbsp(faixaDePreco(3200, 5400))).toBe("R$ 32,00 a R$ 54,00");
  });

  it("sessão sem preço não quebra a vitrine", () => {
    expect(semNbsp(faixaDePreco(null, null))).toBe("—");
  });

  it("com máximo ausente, mostra só o mínimo", () => {
    expect(semNbsp(faixaDePreco(3200, null))).toBe("R$ 32,00");
  });
});

describe("duracao", () => {
  it("mostra horas e minutos", () => {
    expect(duracao(143)).toBe("2h 23min");
  });

  it("hora cheia não mostra minutos", () => {
    expect(duracao(120)).toBe("2h");
  });

  it("menos de uma hora mostra só minutos", () => {
    expect(duracao(45)).toBe("45min");
  });

  it("filme sem duração no catálogo devolve vazio", () => {
    expect(duracao(null)).toBe("");
    expect(duracao(0)).toBe("");
  });
});

describe("dataHora", () => {
  it("formata em português, sem ponto no dia da semana", () => {
    const texto = dataHora("2026-08-23T22:00:00Z");
    expect(texto).toMatch(/ago/);
    expect(texto).toMatch(/\d{2}:\d{2}/);
  });
});

describe("tempoRestante", () => {
  afterEach(() => vi.useRealTimers());

  it("conta o que falta em minutos e segundos", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-08-23T20:00:00Z"));
    expect(tempoRestante("2026-08-23T20:14:30Z")).toBe("14:30");
  });

  it("preenche o segundo com zero à esquerda", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-08-23T20:00:00Z"));
    expect(tempoRestante("2026-08-23T20:05:07Z")).toBe("5:07");
  });

  it("prazo vencido mostra zero, nunca negativo", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-08-23T20:00:00Z"));
    expect(tempoRestante("2026-08-23T19:50:00Z")).toBe("0:00");
  });
});
