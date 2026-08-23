/** Contratos da API, espelhando os schemas do back-end. */

export type SeatKind = "WHEELCHAIR" | "COMPANION" | "OBESE" | "REDUCED_MOBILITY";

export type SessionStatus = "DRAFT" | "PUBLISHED" | "CANCELLED";
export type OrderStatus = "PENDING" | "PAID" | "DECLINED" | "EXPIRED" | "CANCELLED";
export type TicketStatus = "RESERVED" | "VALID" | "USED" | "CANCELLED";
export type GateResult = "VALID" | "INVALID" | "ALREADY_USED" | "WRONG_SESSION";

export type AudioType = "DUBBED" | "SUBTITLED" | "NATIONAL";
export type ScreenFormat = "TWO_D" | "THREE_D";

export const AUDIO: Record<AudioType, string> = {
  DUBBED: "Dublado",
  SUBTITLED: "Legendado",
  NATIONAL: "Nacional",
};

export const FORMATO: Record<ScreenFormat, string> = {
  TWO_D: "2D",
  THREE_D: "3D",
};

/** Classificação indicativa brasileira.
 *
 *  As cores são as do sistema oficial — verde para livre, subindo até preto
 *  para dezoito anos. O número aparece sempre escrito junto: cor sozinha
 *  excluiria quem não distingue matiz. */
const CLASSIFICACOES: Record<string, { rotulo: string; cor: string; texto: string; descricao: string }> = {
  L: { rotulo: "L", cor: "#0f8a3c", texto: "#fff", descricao: "Livre para todos os públicos" },
  "10": { rotulo: "10", cor: "#0f7fbd", texto: "#fff", descricao: "Não recomendado para menores de 10 anos" },
  "12": { rotulo: "12", cor: "#e0a800", texto: "#1a1206", descricao: "Não recomendado para menores de 12 anos" },
  "14": { rotulo: "14", cor: "#e07b1f", texto: "#1a1206", descricao: "Não recomendado para menores de 14 anos" },
  "16": { rotulo: "16", cor: "#d13b30", texto: "#fff", descricao: "Não recomendado para menores de 16 anos" },
  "18": { rotulo: "18", cor: "#1a1a1a", texto: "#fff", descricao: "Não recomendado para menores de 18 anos" },
};

const SEM_CLASSIFICACAO = {
  rotulo: "?",
  cor: "#3a3640",
  texto: "#a49d95",
  descricao: "Classificação indicativa não informada",
};

export function classificacao(valor: string | null | undefined) {
  if (!valor) return SEM_CLASSIFICACAO;
  // "Livre" aparece por extenso em alguns registros do catálogo.
  const chave = valor.trim().toUpperCase() === "LIVRE" ? "L" : valor.trim().toUpperCase();
  return CLASSIFICACOES[chave] ?? { ...SEM_CLASSIFICACAO, rotulo: valor, descricao: `Classificação ${valor}` };
}

/** Rótulo e sigla de cada natureza de poltrona.
 *
 *  A sigla existe para o mapa não depender só de cor: quem não distingue
 *  verde de âmbar precisa conseguir achar a poltrona acessível igual.
 *  Ver decisão D16. */
export const ASSENTO: Record<SeatKind, { rotulo: string; sigla: string }> = {
  WHEELCHAIR: { rotulo: "Espaço para cadeira de rodas", sigla: "♿" },
  COMPANION: { rotulo: "Poltrona de acompanhante", sigla: "AC" },
  OBESE: { rotulo: "Assento largo", sigla: "AL" },
  REDUCED_MOBILITY: { rotulo: "Mobilidade reduzida", sigla: "MR" },
};

export interface CatalogItem {
  id: string;
  title: string;
  age_rating?: string | null;
  overview: string | null;
  release_year: number | null;
  poster_url: string | null;
  backdrop_url: string | null;
  rating: number | null;
  runtime_minutes: number | null;
  genres: string[];
}

export interface CatalogPage {
  items: CatalogItem[];
  page: number;
  total_pages: number;
  total_results: number;
}

export interface SpecialSeat {
  seat_code: string;
  kind: SeatKind;
}

export interface Sector {
  id: string;
  name: string;
  rows: number;
  seats_per_row: number;
  display_order: number;
  capacity: number;
  special_seats: SpecialSeat[];
  aisles: number[];
}

export interface Room {
  id: string;
  name: string;
  location: string | null;
  active: boolean;
  capacity: number;
  sectors: Sector[];
}

export interface Movie {
  catalog_id: string;
  title: string;
  overview: string | null;
  poster_url: string | null;
  backdrop_url: string | null;
  runtime_minutes: number | null;
  year: number | null;
  age_rating: string | null;
}

export interface SessionDetail {
  id: string;
  movie: Movie;
  room_id: string;
  room_name: string;
  room_location: string | null;
  starts_at: string;
  status: SessionStatus;
  audio: AudioType;
  screen_format: ScreenFormat;
  capacity: number;
  prices: { sector: Sector; price_cents: number }[];
  min_price_cents: number | null;
  max_price_cents: number | null;
  /** Ingressos que ocupam poltrona. Só vem na visão do organizador. */
  tickets_sold?: number | null;
}

export interface SessionListItem {
  id: string;
  title: string;
  poster_url: string | null;
  year: number | null;
  runtime_minutes: number | null;
  age_rating: string | null;
  audio: AudioType;
  screen_format: ScreenFormat;
  starts_at: string;
  room_name: string;
  room_location: string | null;
  min_price_cents: number | null;
  max_price_cents: number | null;
}

/** Um dia da barra de datas da vitrine, com quantas sessões tem. */
export interface DayInCartaz {
  date: string;
  total: number;
}

/** Resultado da criação em lote: o que entrou e o que ficou de fora. */
export interface BatchResult {
  created: SessionDetail[];
  skipped: { date: string; reason: string }[];
}

export interface SessionPage {
  items: SessionListItem[];
  total: number;
  page: number;
  total_pages: number;
}

export interface Seat {
  code: string;
  taken: boolean;
  kind: SeatKind | null;
}

export interface SectorMap {
  id: string;
  name: string;
  rows: number;
  seats_per_row: number;
  display_order: number;
  price_cents: number;
  /** Posições depois das quais há corredor. [3, 9] = blocos de 3, 6 e 3. */
  aisles: number[];
  seats: Seat[];
}

export interface SeatMap {
  session_id: string;
  movie_title: string;
  starts_at: string;
  room_name: string;
  capacity: number;
  available: number;
  sectors: SectorMap[];
}

export interface Ticket {
  id: string;
  order_id: string;
  seat_code: string;
  sector_name: string;
  seat_kind: SeatKind | null;
  price_cents: number;
  status: TicketStatus;
  used_at: string | null;
  code: string | null;
  share_token: string | null;
}

export interface TicketDetail extends Ticket {
  movie_title: string;
  movie_poster_url: string | null;
  starts_at: string;
  room_name: string;
  room_location: string | null;
}

export interface Order {
  id: string;
  session_id: string;
  movie_title: string;
  starts_at: string;
  room_name: string;
  status: OrderStatus;
  total_cents: number;
  created_at: string;
  expires_at: string | null;
  paid_at: string | null;
  decline_reason: string | null;
  tickets: Ticket[];
}

export interface GateCheck {
  result: GateResult;
  message: string;
  ticket: TicketDetail | null;
  used_at: string | null;
}
