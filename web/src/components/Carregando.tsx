/** `inline` para quando o que carrega é um pedaço da tela, e não a tela toda:
 *  ocupar 60dvh no meio de um formulário empurraria o resto para fora da vista. */
export function Carregando({
  texto = "Carregando",
  inline = false,
}: {
  texto?: string;
  inline?: boolean;
}) {
  return (
    <div
      role="status"
      aria-live="polite"
      style={
        inline
          ? { color: "var(--text-faint)", fontSize: "var(--text-sm)" }
          : {
              minHeight: "60dvh",
              display: "grid",
              placeItems: "center",
              color: "var(--text-faint)",
              fontSize: "var(--text-sm)",
            }
      }
    >
      {texto}…
    </div>
  );
}
