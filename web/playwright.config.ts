/**
 * Testes de ponta a ponta, em navegador de verdade.
 *
 * Existem por um motivo concreto: a suíte de unidade roda em jsdom, que não
 * calcula layout. Um defeito real de recorte do mapa de assentos no celular
 * passou pelos 22 testes do componente sem que nenhum ficasse vermelho — largura,
 * transbordo e rolagem simplesmente não existem lá. Ver decisão D39.
 *
 * Rodar:  npm run e2e        (precisa do banco e da API de pé — ver `preparo.ts`)
 */
import { defineConfig, devices } from "@playwright/test";

const ENDERECO = "http://localhost:5173";

export default defineConfig({
  testDir: "./e2e",
  globalSetup: "./e2e/preparo.ts",

  // Estes testes compram poltrona de verdade num banco de verdade. Em paralelo,
  // dois trabalhadores disputariam a mesma sessão e um perderia por corrida —
  // exatamente a garantia que o back-end tem, e que aqui só produziria ruído.
  workers: 1,
  fullyParallel: false,

  // Repetir uma vez fora da máquina do desenvolvedor absorve lentidão de CI
  // sem esconder falha real: o relatório mostra que houve retentativa.
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "github" : "list",

  use: {
    baseURL: ENDERECO,
    // Rastro só do que falhou, e no que falhou na primeira tentativa: é onde
    // a linha do tempo com telas e rede paga o custo de gravar.
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },

  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    // O celular não é variação opcional: é onde mais se compra ingresso, e onde
    // estavam os três defeitos que o navegador encontrou e a unidade não.
    //
    // 375px de propósito, e não a largura do aparelho da moda: foi onde os
    // defeitos apareceram, e é o estreito comum que ainda circula. Com os 412px
    // do Pixel 7, o cabeçalho quebrado passava no teste — sobra folga bastante
    // para o defeito não aparecer. Testar no aparelho largo é testar onde não dói.
    {
      name: "celular",
      use: { ...devices["Pixel 7"], viewport: { width: 375, height: 812 } },
    },
  ],

  webServer: {
    command: "npm run dev",
    url: ENDERECO,
    reuseExistingServer: true,
    timeout: 60_000,
  },
});
