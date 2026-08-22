/** Contratos da API, espelhando os schemas do back-end. */

export type SeatKind = "WHEELCHAIR" | "COMPANION" | "OBESE" | "REDUCED_MOBILITY";

export type SessionStatus = "DRAFT" | "PUBLISHED" | "CANCELLED";
export type OrderStatus = "PENDING" | "PAID" | "DECLINED" | "EXPIRED" | "CANCELLED";
export type TicketStatus = "RESERVED" | "VALID" | "USED" | "CANCELLED";
export type GateResult = "VALID" | "INVALID" | "ALREADY_USED" | "WRONG_SESSION";

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
}

export interface SessionDetail {
  id: string;
  movie: Movie;
  room_id: string;
  room_name: string;
  room_location: string | null;
  starts_at: string;
  status: SessionStatus;
  capacity: number;
  prices: { sector: Sector; price_cents: number }[];
  min_price_cents: number | null;
  max_price_cents: number | null;
}

export interface SessionListItem {
  id: string;
  title: string;
  poster_url: string | null;
  year: number | null;
  runtime_minutes: number | null;
  starts_at: string;
  room_name: string;
  room_location: string | null;
  min_price_cents: number | null;
  max_price_cents: number | null;
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
