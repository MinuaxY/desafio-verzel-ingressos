// defineConfig do vitest/config, e nao do vite: o do Vite nao conhece a
// chave `test`, e o build falha na checagem de tipos.
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: "./src/testes/preparo.ts",
    globals: true,
    // O arquivo de preparo e os utilitários de teste não são casos de teste.
    include: ["src/**/*.test.{ts,tsx}"],
    coverage: {
      provider: "v8",
      include: ["src/**/*.{ts,tsx}"],
      exclude: ["src/**/*.test.{ts,tsx}", "src/testes/**", "src/main.tsx"],
    },
  },
});
