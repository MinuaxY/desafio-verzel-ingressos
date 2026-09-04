/**
 * Passos que mais de um teste de ponta a ponta precisa percorrer.
 *
 * Ficam aqui, e não duplicados nos specs, porque são caminho de usuário e não
 * detalhe de um teste: a portaria só tem o que validar depois que alguém
 * comprou, e é a mesma compra do spec de compra.
 */
import { expect, type Page } from "@playwright/test";

export const CONTAS = {
  cliente: { email: "cliente1@verzel.dev", senha: "verzel123" },
  organizador: { email: "organizador@verzel.dev", senha: "verzel123" },
  portaria: { email: "portaria@verzel.dev", senha: "verzel123" },
};

export const CARTAO_QUE_APROVA = "4111 1111 1111 1111";

export async function entrar(page: Page, conta: { email: string; senha: string }) {
  await page.goto("/entrar");
  await page.getByLabel("E-mail").fill(conta.email);
  await page.getByLabel("Senha").fill(conta.senha);
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(page).not.toHaveURL(/\/entrar/);
}

export async function sair(page: Page) {
  await page.getByRole("button", { name: "Sair" }).click();
  await expect(page.getByRole("link", { name: "Entrar" })).toBeVisible();
}

/** Poltrona livre e ocupada se distinguem pelo próprio rótulo acessível: a livre
 *  anuncia o preço, a vendida anuncia "ocupada". Procurar pelo preço é, ao mesmo
 *  tempo, escolher um lugar comprável e conferir que o rótulo diz o que deve. */
export function poltronaLivre(page: Page) {
  return page.getByRole("button", { name: /^Poltrona .+R\$/ }).first();
}

/** Abre a primeira sessão do cartaz e espera o mapa da sala aparecer.
 *
 *  A espera é o ponto: a URL muda antes do React renderizar, e sem ela tanto a
 *  leitura do título quanto uma contagem de poltronas acontecem cedo demais —
 *  os dois erros aconteceram ao escrever estes testes. */
export async function abrePrimeiraSessao(page: Page) {
  await page.goto("/em-cartaz");
  // Pelo destino, e não pelo texto: a primeira versão procurava um link com
  // "ingressos" no nome e acertava "Meus ingressos", no cabeçalho.
  await page.locator('a[href^="/sessao/"]').first().click();
  await expect(page).toHaveURL(/\/sessao\//);
  await expect(poltronaLivre(page)).toBeVisible();
  return page.url();
}

/** Confirma um passo destrutivo no diálogo da própria tela.
 *  Escopado ao `<dialog>`: o botão que abre e o que confirma costumam ter o
 *  mesmo rótulo, e sem isso o seletor ficaria ambíguo. Ver decisão D42. */
export async function confirmarNoDialogo(page: Page, acao: string) {
  const dialogo = page.locator("dialog.confirmacao");
  await expect(dialogo).toBeVisible();
  await dialogo.getByRole("button", { name: acao, exact: true }).click();
  await expect(dialogo).toBeHidden();
}

export interface Compra {
  urlDaSessao: string;
  sessaoId: string;
  filme: string;
  /** Código da poltrona, como "H1". */
  poltrona: string;
}

/** Escolhe uma poltrona e para na tela de pagamento, sem pagar. É o estado em
 *  que o pedido prende a poltrona por tempo limitado. */
export async function reservarUmaPoltrona(page: Page): Promise<Compra> {
  const urlDaSessao = await abrePrimeiraSessao(page);
  const sessaoId = urlDaSessao.split("/sessao/")[1];
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

  return { urlDaSessao, sessaoId, filme, poltrona: codigo };
}

/** Percorre o fluxo inteiro e devolve o que foi comprado.
 *  Termina em /meus-ingressos, com o ingresso emitido. */
export async function comprarUmaPoltrona(page: Page): Promise<Compra> {
  const compra = await reservarUmaPoltrona(page);

  await page.getByLabel("Número do cartão").fill(CARTAO_QUE_APROVA);
  await page.getByLabel("Nome impresso no cartão").fill("PAULO FIGUEIREDO");
  await page.getByRole("button", { name: /^Pagar/ }).click();
  await expect(page).toHaveURL(/\/meus-ingressos/);

  return compra;
}

/** O código que vai no QR, lido da própria tela do cliente — é o mesmo que ele
 *  mostraria na portaria. Pressupõe estar em /meus-ingressos. */
export async function codigoDoIngresso(page: Page, compra: Compra) {
  const ingresso = page.locator(".ingresso").filter({ hasText: compra.filme }).first();
  await expect(ingresso).toContainText(compra.poltrona);
  return (await ingresso.locator(".ingresso__codigo").first().innerText()).trim();
}
