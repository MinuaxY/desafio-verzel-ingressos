import { describe, expect, it } from "vitest";

import { ASSENTO, AUDIO, FORMATO, classificacao } from "./tipos";

describe("classificacao indicativa", () => {
  it("traduz as faixas brasileiras", () => {
    expect(classificacao("L").rotulo).toBe("L");
    expect(classificacao("12").rotulo).toBe("12");
    expect(classificacao("18").rotulo).toBe("18");
  });

  it("cada faixa tem cor própria", () => {
    const cores = ["L", "10", "12", "14", "16", "18"].map((v) => classificacao(v).cor);
    expect(new Set(cores).size).toBe(6);
  });

  it("o número aparece escrito, não só a cor", () => {
    // Cor sozinha excluiria quem não distingue matiz, e classificação
    // indicativa é informação séria demais para depender disso. Ver D21.
    for (const faixa of ["L", "10", "12", "14", "16", "18"]) {
      expect(classificacao(faixa).rotulo).toBe(faixa);
    }
  });

  it("cada faixa tem descrição legível para leitor de tela", () => {
    expect(classificacao("L").descricao).toMatch(/livre/i);
    expect(classificacao("16").descricao).toMatch(/16 anos/);
  });

  it("aceita 'Livre' por extenso, como alguns registros trazem", () => {
    expect(classificacao("Livre").rotulo).toBe("L");
    expect(classificacao("livre").rotulo).toBe("L");
  });

  it("filme sem classificação não quebra a tela", () => {
    for (const vazio of [null, undefined, ""]) {
      expect(classificacao(vazio).rotulo).toBe("?");
      expect(classificacao(vazio).descricao).toMatch(/não informada/i);
    }
  });

  it("valor inesperado do catálogo aparece como veio", () => {
    // É dado de terceiro: melhor mostrar o que chegou do que esconder.
    expect(classificacao("A2").rotulo).toBe("A2");
  });

  it("ignora espaços em volta", () => {
    expect(classificacao(" 14 ").rotulo).toBe("14");
  });
});

describe("rótulos de exibição", () => {
  it("traduz áudio e formato para português", () => {
    expect(AUDIO.DUBBED).toBe("Dublado");
    expect(AUDIO.SUBTITLED).toBe("Legendado");
    expect(AUDIO.NATIONAL).toBe("Nacional");
    expect(FORMATO.TWO_D).toBe("2D");
    expect(FORMATO.THREE_D).toBe("3D");
  });
});

describe("naturezas de poltrona", () => {
  it("cobre as quatro exigidas por sala de espetáculo", () => {
    expect(Object.keys(ASSENTO).sort()).toEqual(
      ["COMPANION", "OBESE", "REDUCED_MOBILITY", "WHEELCHAIR"].sort(),
    );
  });

  it("cada uma tem sigla curta, para caber na poltrona", () => {
    for (const { sigla } of Object.values(ASSENTO)) {
      expect(sigla.length).toBeLessThanOrEqual(2);
    }
  });

  it("as siglas são distintas entre si", () => {
    const siglas = Object.values(ASSENTO).map((a) => a.sigla);
    expect(new Set(siglas).size).toBe(siglas.length);
  });
});
