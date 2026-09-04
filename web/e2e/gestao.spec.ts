/**
 * A gestão da programação, pelos olhos do organizador.
 *
 * Este é o fluxo mais longo do sistema e o último que só tinha verificação
 * manual: escolher filme no catálogo, sala, horário e preço de cada setor,
 * repetir em outros dias, publicar, tirar do cartaz e excluir.
 *
 * ## Por que 09:15, e por que quarenta dias à frente
 *
 * A sala é reservada pelo intervalo que a sessão ocupa (D37), com uma restrição
 * de exclusão no banco. Criar sessão em cima do que o seed já programou daria
 * conflito legítimo — e o teste ficaria vermelho por dado, não por defeito.
 *
 * O horário 09:15 não existe na programação semeada, então serve de assinatura:
 * é assim que a limpeza reconhece o que **este** teste criou, sem risco de
 * apagar sessão do seed. O título não serviria — "Toy Story 5" está nos dois.
 */
import { expect, test, type Page } from "@playwright/test";

import { CONTAS, entrar } from "./fluxos";

const HORA = "09:15";
const BUSCA = "toy";

/** Bem depois dos dez dias que o seed programa. */
function diaLivre(maisDias = 0) {
  const d = new Date();
  d.setDate(d.getDate() + 40 + maisDias);
  return d.toISOString().slice(0, 10);
}

/** Confirma o passo destrutivo no diálogo da própria tela.
 *  Escopado ao `<dialog>` de propósito: o botão da linha e o do diálogo têm o
 *  mesmo rótulo, e sem isso o seletor ficaria ambíguo. Ver decisão D42. */
async function confirmarNoDialogo(page: Page, acao: string) {
  const dialogo = page.locator("dialog.confirmacao");
  await expect(dialogo).toBeVisible();
  await dialogo.getByRole("button", { name: acao, exact: true }).click();
  await expect(dialogo).toBeHidden();
}

/** As linhas que este teste criou, reconhecidas pelo horário-assinatura. */
function minhasSessoes(page: Page) {
  return page.locator(".linha-sessao").filter({ hasText: HORA });
}

/** Remove o que o teste criou, para a próxima execução encontrar a sala livre.
 *  Rascunho sai direto; publicada precisa voltar a rascunho antes (D28). */
async function limpar(page: Page) {
  await page.goto("/organizador");
  await expect(page.getByRole("heading", { name: "Minhas sessões" })).toBeVisible();

  for (let volta = 0; volta < 12; volta++) {
    const restantes = await minhasSessoes(page).count();
    if (restantes === 0) break;

    // A contagem total é que precisa cair. Esperar a *primeira* linha sumir não
    // funciona: `first()` é um locator, não um instantâneo — assim que uma sai,
    // ele passa a apontar para a seguinte e a espera nunca termina.
    const linha = minhasSessoes(page).first();
    const despublicar = linha.getByRole("button", { name: "Despublicar" });
    if (await despublicar.count()) {
      await despublicar.click();
      await expect(linha.getByRole("button", { name: "Excluir" })).toBeVisible();
    }

    await linha.getByRole("button", { name: "Excluir" }).click();
    await confirmarNoDialogo(page, "Excluir");
    await expect(minhasSessoes(page)).toHaveCount(restantes - 1, { timeout: 10_000 });
  }
  await expect(minhasSessoes(page)).toHaveCount(0);
}

async function preencheNovaSessao(page: Page, dia: string) {
  await page.goto("/organizador/nova-sessao");

  await page.getByLabel("Buscar filme").fill(BUSCA);
  await page.getByRole("button", { name: "Buscar", exact: true }).click();
  await page.locator(".resultado").first().click();
  await expect(page.getByRole("button", { name: "Trocar" })).toBeVisible();

  await page.getByLabel("Escolha a sala").selectOption({ index: 1 });
  await page.getByLabel("Início da sessão").fill(`${dia}T${HORA}`);

  // Todo setor precisa de preço: sem isso a sessão iria ao ar com um setor sem
  // valor, e a própria tela trava o botão. Ver decisão D35.
  const precos = page.locator('input[aria-label^="Preço do setor"]');
  for (let i = 0; i < (await precos.count()); i++) {
    await precos.nth(i).fill("32,00");
  }
}

test.beforeEach(async ({ page }) => {
  await entrar(page, CONTAS.organizador);
  await limpar(page);
});

test.afterEach(async ({ page }) => {
  await limpar(page);
});

test("o ciclo inteiro: publicar, aparecer no cartaz, despublicar e excluir", async ({ page }) => {
  const dia = diaLivre();
  await preencheNovaSessao(page, dia);

  await page.getByRole("button", { name: "Publicar sessão" }).click();
  await expect(page).toHaveURL(/\/organizador$/);

  const linha = minhasSessoes(page).first();
  await expect(linha).toBeVisible();
  await expect(linha).toContainText("Publicada");

  // O que o organizador publica é o que o cliente vê: a promessa da tela é
  // "publique e ela entra no cartaz na hora".
  await linha.getByRole("link", { name: "Ver no cartaz" }).click();
  await expect(page).toHaveURL(/\/sessao\//);
  await expect(page.getByRole("button", { name: /^Poltrona .+R\$/ }).first()).toBeVisible();

  await page.goto("/organizador");
  await minhasSessoes(page).first().getByRole("button", { name: "Despublicar" }).click();
  await expect(minhasSessoes(page).first()).toContainText("Rascunho");

  // Excluir só existe em rascunho — publicada sai do cartaz com despublicar, e
  // sessão com ingresso vendido não some. Ver decisão D28.
  await minhasSessoes(page).first().getByRole("button", { name: "Excluir" }).click();
  await confirmarNoDialogo(page, "Excluir");
  await expect(minhasSessoes(page)).toHaveCount(0);
});

test("repetir em outros dias cria uma sessão por dia marcado", async ({ page }) => {
  const dia = diaLivre();
  await preencheNovaSessao(page, dia);

  // A repetição vive num `<details>` fechado enquanto nada está marcado — ela é
  // exceção, não o caminho comum. Sem abrir, os dias existem no HTML mas não
  // são clicáveis.
  await page.locator(".repetir summary").click();

  // Dois dias a mais, marcados um a um. Não há regra de recorrência de
  // propósito: programação de cinema não é regular. Ver decisão D27.
  const grade = page.getByRole("group", { name: "Dias para repetir a sessão" });
  const disponiveis = grade.getByRole("button", { disabled: false });
  await disponiveis.nth(0).click();
  await disponiveis.nth(1).click();
  // O dia principal fica marcado e travado: tirá-lo daqui não cancelaria a
  // sessão, só confundiria.
  await expect(grade.getByRole("button", { disabled: true })).toHaveCount(1);

  await expect(page.getByRole("button", { name: "Publicar 3 sessões" })).toBeVisible();
  await page.getByRole("button", { name: "Publicar 3 sessões" }).click();

  await expect(page).toHaveURL(/\/organizador$/);
  await expect(minhasSessoes(page)).toHaveCount(3);
});

test("não deixa publicar sem preço em todos os setores", async ({ page }) => {
  await page.goto("/organizador/nova-sessao");

  await page.getByLabel("Buscar filme").fill(BUSCA);
  await page.getByRole("button", { name: "Buscar", exact: true }).click();
  await page.locator(".resultado").first().click();
  await page.getByLabel("Escolha a sala").selectOption({ index: 1 });
  await page.getByLabel("Início da sessão").fill(`${diaLivre()}T${HORA}`);

  // Filme, sala e horário prontos, preços em branco: o botão continua travado.
  // O erro que dá para prever vale mais como impedimento do que como recusa da
  // API depois do clique.
  const publicar = page.getByRole("button", { name: "Publicar sessão" });
  await expect(publicar).toBeDisabled();

  const precos = page.locator('input[aria-label^="Preço do setor"]');
  const setores = await precos.count();
  expect(setores, "esta sala precisa de mais de um setor para o teste valer").toBeGreaterThan(1);

  // O passo que importa: **um** preço preenchido e o resto em branco. Sem ele o
  // teste não distingue "todo setor tem preço" de "algum setor tem preço" — com
  // zero preenchidos as duas regras recusam igual, e a troca de `every` por
  // `some` passaria despercebida. Ver decisão D35.
  await precos.nth(0).fill("32,00");
  await expect(publicar).toBeDisabled();

  for (let i = 1; i < setores; i++) await precos.nth(i).fill("54,00");
  await expect(publicar).toBeEnabled();
});
