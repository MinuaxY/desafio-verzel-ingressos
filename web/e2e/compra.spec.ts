/**
 * O caminho que o cliente percorre para sair com um ingresso na mão.
 *
 * É o fluxo central do produto e não tinha nenhum teste automatizado — estava
 * declarado como "verificado manualmente no navegador" nas limitações do README.
 * Roda nos dois projetos, e o de celular é o que importa: é onde se compra
 * ingresso, e onde os defeitos de layout aparecem.
 */
import { expect, test, type Page } from "@playwright/test";

const CLIENTE = { email: "cliente1@verzel.dev", senha: "verzel123" };
const CARTAO_QUE_APROVA = "4111 1111 1111 1111";

async function entrar(page: Page) {
  await page.goto("/entrar");
  await page.getByLabel("E-mail").fill(CLIENTE.email);
  await page.getByLabel("Senha").fill(CLIENTE.senha);
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(page).not.toHaveURL(/\/entrar/);
}

/** Poltrona livre e ocupada se distinguem pelo próprio rótulo acessível: a livre
 *  anuncia o preço, a vendida anuncia "ocupada". Procurar pelo preço é, ao mesmo
 *  tempo, escolher um lugar comprável e conferir que o rótulo diz o que deve. */
function poltronaLivre(page: Page) {
  return page.getByRole("button", { name: /^Poltrona .+R\$/ }).first();
}

/** Abre a primeira sessão do cartaz e espera o mapa da sala aparecer.
 *
 *  A espera é o ponto: a URL muda antes do React renderizar, e sem ela tanto a
 *  leitura do título quanto uma contagem de poltronas acontecem cedo demais —
 *  os dois erros aconteceram ao escrever este arquivo. */
async function abrePrimeiraSessao(page: Page) {
  await page.goto("/em-cartaz");
  // Pelo destino, e não pelo texto: a primeira versão procurava um link com
  // "ingressos" no nome e acertava "Meus ingressos", no cabeçalho.
  await page.locator('a[href^="/sessao/"]').first().click();
  await expect(page).toHaveURL(/\/sessao\//);
  await expect(poltronaLivre(page)).toBeVisible();
  return page.url();
}

/** Percorre o fluxo inteiro e devolve o que foi comprado. */
async function comprarUmaPoltrona(page: Page) {
  const urlDaSessao = await abrePrimeiraSessao(page);
  const filme = await page.getByRole("heading", { level: 1 }).innerText();

  // O código sai do rótulo antes do clique: é ele que precisa reaparecer no
  // ingresso, e é o que prova que a poltrona escolhida foi a poltrona emitida.
  const poltrona = poltronaLivre(page);
  const rotulo = (await poltrona.getAttribute("aria-label")) ?? "";
  const codigo = rotulo.match(/^Poltrona ([^,]+)/)?.[1] ?? "";
  expect(codigo, `rótulo inesperado na poltrona: "${rotulo}"`).not.toBe("");

  await poltrona.click();
  await expect(poltrona).toHaveAttribute("aria-pressed", "true");

  await page.getByRole("button", { name: /^Continuar$/ }).click();
  await expect(page).toHaveURL(/\/pedido\//);

  await page.getByLabel("Número do cartão").fill(CARTAO_QUE_APROVA);
  await page.getByLabel("Nome impresso no cartão").fill("PAULO FIGUEIREDO");
  await page.getByRole("button", { name: /^Pagar/ }).click();

  return { urlDaSessao, filme, codigo };
}

test("cliente compra um ingresso, do cartaz ao QR", async ({ page }) => {
  await entrar(page);
  const { filme, codigo } = await comprarUmaPoltrona(page);

  await expect(page).toHaveURL(/\/meus-ingressos/);
  const ingresso = page.locator(".ingresso").filter({ hasText: filme }).first();
  await expect(ingresso).toContainText(codigo);
  // A presença do QR é o que separa "pedido pago" de "ingresso emitido", que é
  // o que o cliente leva para a portaria. Procurado pelo papel e pelo texto
  // alternativo, então o teste também tranca a descrição para leitor de tela.
  await expect(ingresso.getByRole("img", { name: "Código QR do ingresso" })).toBeVisible();
});

test("a poltrona comprada volta ocupada para o próximo cliente", async ({ page }) => {
  // A face visível da garantia que o banco dá com índice único parcial: o
  // próximo a abrir a sala não deve nem conseguir clicar naquele lugar.
  await entrar(page);
  const { urlDaSessao, codigo } = await comprarUmaPoltrona(page);
  await expect(page).toHaveURL(/\/meus-ingressos/);

  await page.goto(urlDaSessao);
  const vendida = page.getByRole("button", { name: new RegExp(`^Poltrona ${codigo},`) });
  await expect(vendida).toBeVisible();
  await expect(vendida).toHaveAccessibleName(/ocupada/);
  await expect(vendida).toBeDisabled();
});
