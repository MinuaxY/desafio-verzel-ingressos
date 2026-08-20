export function Carregando({ texto = "Carregando" }: { texto?: string }) {
  return (
    <div
      role="status"
      aria-live="polite"
      style={{
        minHeight: "60dvh",
        display: "grid",
        placeItems: "center",
        color: "var(--text-faint)",
        fontSize: "var(--text-sm)",
      }}
    >
      {texto}…
    </div>
  );
}
