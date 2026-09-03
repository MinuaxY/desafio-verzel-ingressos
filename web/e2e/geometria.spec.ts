/**
 * O que a suíte de unidade não consegue ver.
 *
 * jsdom não calcula layout: `getBoundingClientRect` devolve zeros, e largura,
 * transbordo e rolagem simplesmente não existem. Três defeitos reais passaram
 * pelos 126 testes de unidade sem que nenhum ficasse vermelho — o mapa da sala
 * cortado dos dois lados no celular e o cabeçalho empurrando a página inteira
 * para o lado. Ver decisão D39 e aprendizado 17.
 *
 * Este arquivo é a medição daquele dia virada teste: as mesmas contas, agora
 * rodando sozinhas.
 */
import { expect, test, type Page } from "@playwright/test";

/** Quanto o documento passa da largura da janela. Zero é o único valor aceitável:
 *  qualquer coisa acima faz a página inteira rolar de lado. */
function transbordoDaPagina(page: Page) {
  return page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
}

const PUBLICAS = ["/", "/em-cartaz", "/entrar", "/criar-conta"];

for (const caminho of PUBLICAS) {
  test(`${caminho} não rola de lado`, async ({ page }) => {
    await page.goto(caminho);
    // Pelo `main`, e não pelo cabeçalho: as telas de entrar e criar conta são
    // cartões soltos, sem a barra do topo. Medir antes de a tela existir daria
    // zero por engano — e zero é justamente o resultado que se quer provar.
    await expect(page.locator("main")).toBeVisible();
    // A origem histórica do defeito foi o cabeçalho: "Criar conta" transbordava
    // 18px e levava junto TODAS as telas do sistema, não só a que o mostrava.
    expect(await transbordoDaPagina(page)).toBe(0);
  });
}

test("a sala não rola de lado, e o mapa começa na primeira poltrona", async ({ page }) => {
  await page.goto("/em-cartaz");
  await page.locator('a[href^="/sessao/"]').first().click();

  const grade = page.locator(".setor__grade").first();
  await expect(grade).toBeVisible();

  expect(await transbordoDaPagina(page)).toBe(0);

  const medida = await grade.evaluate((el) => ({
    rolagemInicial: el.scrollLeft,
    precisaRolar: el.scrollWidth - el.clientWidth,
    trilho: el.querySelector<HTMLElement>(".setor__trilho")?.getBoundingClientRect() ?? null,
    caixa: el.getBoundingClientRect(),
  }));

  // O defeito da D39 em uma linha: com `align-items: center` num contêiner que
  // rola, o conteúdo transborda para os DOIS lados e o esquerdo fica
  // inalcançável, porque `scrollLeft` não assume valor negativo. Começar em zero
  // é o que garante que a poltrona 1 esteja a uma rolagem de distância.
  expect(medida.rolagemInicial).toBe(0);

  if (medida.precisaRolar === 0) {
    // Coube: então tem de estar centralizado, com folga igual dos dois lados.
    const folgaEsquerda = medida.trilho!.left - medida.caixa.left;
    const folgaDireita = medida.caixa.right - medida.trilho!.right;
    expect(Math.abs(folgaEsquerda - folgaDireita)).toBeLessThanOrEqual(1);
  } else {
    // Não coube: o trilho tem de encostar na borda esquerda, e não ficar
    // centralizado com um pedaço escondido atrás do começo.
    expect(medida.trilho!.left - medida.caixa.left).toBeLessThanOrEqual(1);
  }

  // A primeira poltrona da primeira fileira precisa estar dentro da área
  // visível da grade — era exatamente ela que sumia.
  const primeira = page.getByRole("button", { name: /^Poltrona / }).first();
  const dentro = await primeira.evaluate((el) => {
    const p = el.getBoundingClientRect();
    const g = el.closest(".setor__grade")!.getBoundingClientRect();
    return p.left >= g.left - 1 && p.right <= g.right + 1;
  });
  expect(dentro, "a primeira poltrona ficou fora da área visível do mapa").toBe(true);
});

test("no dedo, a poltrona tem alvo confortável", async ({ page }, info) => {
  test.skip(info.project.name !== "celular", "Só vale onde o ponteiro é grosso.");

  await page.goto("/em-cartaz");
  await page.locator('a[href^="/sessao/"]').first().click();

  const poltrona = page.getByRole("button", { name: /^Poltrona / }).first();
  await expect(poltrona).toBeVisible();
  const caixa = (await poltrona.boundingBox())!;

  // 24×24 é o mínimo da WCAG 2.5.8 (AA), que os 32px já cumpriam. Os 40px vêm
  // do 2.5.5 (AAA) e são conforto, não conformidade — mas uma vez escolhidos,
  // vale trancar para não regredirem sem querer.
  expect(caixa.width).toBeGreaterThanOrEqual(40);
  expect(caixa.height).toBeGreaterThanOrEqual(40);
});
