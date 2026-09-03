/**
 * O caminho que o cliente percorre para sair com um ingresso na mão.
 *
 * É o fluxo central do produto e não tinha nenhum teste automatizado — estava
 * declarado como "verificado manualmente no navegador" nas limitações do README.
 * Roda nos dois projetos, e o de celular é o que importa: é onde se compra
 * ingresso, e onde os defeitos de layout aparecem.
 */
import { expect, test } from "@playwright/test";

import { CONTAS, comprarUmaPoltrona, entrar } from "./fluxos";

test("cliente compra um ingresso, do cartaz ao QR", async ({ page }) => {
  await entrar(page, CONTAS.cliente);
  const compra = await comprarUmaPoltrona(page);

  const ingresso = page.locator(".ingresso").filter({ hasText: compra.filme }).first();
  await expect(ingresso).toContainText(compra.poltrona);
  // A presença do QR é o que separa "pedido pago" de "ingresso emitido", que é
  // o que o cliente leva para a portaria. Procurado pelo papel e pelo texto
  // alternativo, então o teste também tranca a descrição para leitor de tela.
  await expect(ingresso.getByRole("img", { name: "Código QR do ingresso" })).toBeVisible();
});

test("a poltrona comprada volta ocupada para o próximo cliente", async ({ page }) => {
  // A face visível da garantia que o banco dá com índice único parcial: o
  // próximo a abrir a sala não deve nem conseguir clicar naquele lugar.
  await entrar(page, CONTAS.cliente);
  const compra = await comprarUmaPoltrona(page);

  await page.goto(compra.urlDaSessao);
  const vendida = page.getByRole("button", { name: new RegExp(`^Poltrona ${compra.poltrona},`) });
  await expect(vendida).toBeVisible();
  await expect(vendida).toHaveAccessibleName(/ocupada/);
  await expect(vendida).toBeDisabled();
});
