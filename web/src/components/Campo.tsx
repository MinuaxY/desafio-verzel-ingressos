import type { InputHTMLAttributes } from "react";

interface Props extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  erro?: string;
}

export function Campo({ label, erro, id, ...props }: Props) {
  const inputId = id ?? props.name ?? label;
  const erroId = `${inputId}-erro`;

  return (
    <div className="field">
      <label className="field__label" htmlFor={inputId}>
        {label}
      </label>
      <input
        id={inputId}
        className="field__input"
        aria-invalid={erro ? "true" : undefined}
        aria-describedby={erro ? erroId : undefined}
        {...props}
      />
      {erro && (
        <span className="field__error" id={erroId}>
          {erro}
        </span>
      )}
    </div>
  );
}
