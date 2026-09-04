/**
 * O caminho que o cliente percorre para sair com um ingresso na mão.
 *
 * É o fluxo central do produto e não tinha nenhum teste automatizado — estava
 * declarado como "verificado manualmente no navegador" nas limitações do README.
 * Roda nos dois projetos, e o de celular é o que importa: é onde se compra
 * ingresso, e onde os defeitos de layout aparecem.
 */
import { expect, test } from "@playwright/test";

import {
  CONTAS,
  comprarUmaPoltrona,
  confirmarNoDialogo,
  entrar,
  reservarUmaPoltrona,
} from "./fluxos";

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

test("dá para desistir do pedido na tela de pagamento", async ({ page }) => {
  // O defeito que este teste tranca: a confirmação passava por `window.confirm`,
  // que é suprimido em silêncio em vários contextos. O botão ficava morto, sem
  // aviso nenhum, e a poltrona seguia presa até o prazo vencer. Ver decisão D42.
  await entrar(page, CONTAS.cliente);
  const reserva = await reservarUmaPoltrona(page);

  await page.getByRole("button", { name: "Cancelar pedido" }).click();
  await confirmarNoDialogo(page, "Cancelar pedido");

  await expect(page.getByText(/pedido foi cancelado/i)).toBeVisible();

  // A poltrona precisa voltar ao estoque de verdade, e não só a tela dizer que
  // voltou: desistir sem devolver o lugar seria pior do que não desistir.
  await page.goto(reserva.urlDaSessao);
  const devolvida = page.getByRole("button", { name: new RegExp(`^Poltrona ${reserva.poltrona},`) });
  await expect(devolvida).toBeEnabled();
  await expect(devolvida).toHaveAccessibleName(/R\$/);
});

test("voltar atrás na confirmação não cancela nada", async ({ page }) => {
  await entrar(page, CONTAS.cliente);
  await reservarUmaPoltrona(page);

  await page.getByRole("button", { name: "Cancelar pedido" }).click();
  await confirmarNoDialogo(page, "Voltar");

  // Continua sendo possível pagar: a desistência do passo de confirmação não
  // pode deixar o pedido num estado intermediário.
  await expect(page.getByRole("button", { name: /^Pagar/ })).toBeEnabled();
  await expect(page.getByText(/pedido foi cancelado/i)).toHaveCount(0);
});
