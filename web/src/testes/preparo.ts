/**
 * Preparo do ambiente de testes.
 *
 * Roda antes de cada arquivo de teste: adiciona as asserções de DOM do
 * jest-dom e limpa o que sobra entre um caso e outro, para que nenhum teste
 * dependa do estado deixado pelo anterior.
 */
import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

afterEach(() => {
  cleanup();
  localStorage.clear();
  vi.restoreAllMocks();
});
