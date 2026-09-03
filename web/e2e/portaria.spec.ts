/**
 * A portaria, com os quatro vereditos, percorrida como o operador percorre.
 *
 * O ingresso não é forjado nem inserido no banco: é comprado pela tela, e o
 * código sai de onde o cliente o leria. Assim o teste cobre a costura inteira —
 * a compra emite, o QR mostra, e a portaria reconhece.
 *
 * A câmera fica de fora: exige permissão e hardware que não existem aqui. Sobra
 * a digitação manual, que existe no produto justamente para quando a câmera
 * falha, e que é o caminho que a portaria usa quando o aparelho não coopera.
 */
import { expect, test, type Page } from "@playwright/test";

import { CONTAS, codigoDoIngresso, comprarUmaPoltrona, entrar, sair } from "./fluxos";

// Em série e com uma aba só: os vereditos contam uma história em ordem — o
// ingresso entra, e por ter entrado não entra de novo. Separá-los em testes
// independentes exigiria uma compra por veredito, para provar menos.
test.describe.configure({ mode: "serial" });

test.describe("portaria: os quatro vereditos", () => {
  let page: Page;
  let codigo: string;
  let poltrona: string;
  let sessaoDoIngresso: string;

  test.beforeAll(async ({ browser }) => {
    page = await browser.newPage();

    await entrar(page, CONTAS.cliente);
    const compra = await comprarUmaPoltrona(page);
    codigo = await codigoDoIngresso(page, compra);
    poltrona = compra.poltrona;
    sessaoDoIngresso = compra.sessaoId;
    expect(codigo, "o ingresso saiu sem código").not.toBe("");

    await sair(page);
    await entrar(page, CONTAS.portaria);
    await expect(page.getByRole("heading", { name: "Portaria" })).toBeVisible();
  });

  test.afterAll(async () => {
    await page.close();
  });

  async function validar(valor: string) {
    const campo = page.getByLabel(/digite o código do ingresso/i);
    await campo.fill(valor);
    await page.getByRole("button", { name: "Validar" }).click();
  }

  /** O veredito é anunciado com `role="status"` e `aria-live`, porque na fila
   *  ninguém está olhando para a tela no instante da leitura. */
  function veredito() {
    return page.locator(".veredito");
  }

  test("ingresso de outra sessão é recusado antes de ser consumido", async () => {
    // Prender a porta a uma sessão diferente da do ingresso. Escolhido pelo
    // valor da opção, que é o id: pelo texto, duas exibições do mesmo filme
    // seriam indistinguíveis.
    const seletor = page.getByLabel(/sessão desta porta/i);
    await expect(seletor).toBeEnabled();
    const outra = await seletor.evaluate(
      (el: HTMLSelectElement, minha) =>
        [...el.options].find((o) => o.value && o.value !== minha)?.value ?? "",
      sessaoDoIngresso,
    );
    test.skip(outra === "", "O turno só tem a sessão deste ingresso.");

    await seletor.selectOption(outra);
    await validar(codigo);

    await expect(veredito()).toContainText("Sessão errada");
    await expect(veredito()).toContainText(/em outra sessão/i);
  });

  test("ingresso válido libera a entrada e diz onde a pessoa senta", async () => {
    await page.getByLabel(/sessão desta porta/i).selectOption("");
    await validar(codigo);

    await expect(veredito()).toContainText("Pode entrar");
    // A poltrona no veredito não é enfeite: é o que o operador fala em voz alta
    // para a pessoa que acabou de passar.
    await expect(veredito()).toContainText(poltrona);
  });

  test("o mesmo ingresso não entra duas vezes", async () => {
    // A conferência que a assinatura do QR sozinha não faz: o código continua
    // autêntico: o que mudou é o estado dele no banco.
    await validar(codigo);

    await expect(veredito()).toContainText("Já utilizado");
    await expect(veredito()).toContainText(/utilizado em \d{2}\/\d{2}/);
  });

  test("código inventado não vale, e não explica por quê", async () => {
    await validar("AAAAAAAA.BBBBBBBB");

    await expect(veredito()).toContainText("Não vale");
    // Detalhar o motivo ajudaria quem está tentando adivinhar. A mensagem é
    // deliberadamente seca — ver decisão D6.
    await expect(veredito()).not.toContainText(/assinatura|hmac|expirad/i);
  });
});
