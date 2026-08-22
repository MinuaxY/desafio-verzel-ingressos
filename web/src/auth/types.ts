export type Role = "ORGANIZER" | "CUSTOMER" | "GATE";

export interface User {
  id: string;
  name: string;
  email: string;
  role: Role;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

/** Para onde cada papel vai depois de entrar. */
export const HOME_POR_PAPEL: Record<Role, string> = {
  ORGANIZER: "/organizador",
  CUSTOMER: "/em-cartaz",
  GATE: "/portaria",
};

export const NOME_DO_PAPEL: Record<Role, string> = {
  ORGANIZER: "Organizador",
  CUSTOMER: "Cliente",
  GATE: "Portaria",
};
