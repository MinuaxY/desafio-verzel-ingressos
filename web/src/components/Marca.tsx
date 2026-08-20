/**
 * Marca do produto. O quadrado com o recorte lateral remete ao ingresso
 * picotado na portaria — é o gesto que dá nome ao produto.
 */
export function Marca({ tamanho = 28 }: { tamanho?: number }) {
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: "var(--space-3)" }}>
      <svg width={tamanho} height={tamanho} viewBox="0 0 32 32" aria-hidden="true">
        <path
          d="M4 8a2 2 0 0 1 2-2h20a2 2 0 0 1 2 2v4a4 4 0 0 0 0 8v4a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-4a4 4 0 0 0 0-8V8Z"
          fill="var(--accent)"
        />
        <path d="M18 9v14" stroke="var(--on-accent)" strokeWidth="2" strokeDasharray="2 3" />
      </svg>
      <span
        style={{
          fontFamily: "var(--font-display)",
          fontWeight: 800,
          fontSize: "var(--text-lg)",
          letterSpacing: "-0.03em",
        }}
      >
        Verzel<span style={{ color: "var(--accent)" }}>Ingressos</span>
      </span>
    </span>
  );
}
