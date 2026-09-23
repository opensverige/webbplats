// Rena hjalpfunktioner utan Deno.serve, sa de gar att testa:
//   deno test --allow-net=jsr.io hjalp_test.ts

// Allt som kommer fran formularet ar text som ska visas, aldrig HTML.
// Escapas vid rendering, sa ett namn som "<a href=...>" blir synligt som
// bokstaver i mejlet i stallet for att bli en lank.
const ESC: Record<string, string> = {
  "&": "&amp;",
  "<": "&lt;",
  ">": "&gt;",
  '"': "&quot;",
  "'": "&#39;",
};
export function esc(s: string): string {
  return s.replace(/[&<>"']/g, (c) => ESC[c]);
}

// Forsta ordet, delat pa alla slags blanktecken. split(" ") delade bara pa
// vanligt mellanslag, sa ett namn med tabb eller hart mellanslag gick igenom
// i ett stycke.
export function fornamn(namn: string): string {
  return namn.split(/[\s ]+/)[0] ?? "";
}

// Taggar, URL:er och kontrolltecken har inget i ett namn att gora. Detta ar
// ett andra lager utover esc(): aven textversionen av mejlet ska vara ren,
// och dar hjalper ingen escaping mot en klickbar adress.
// deno-lint-ignore no-control-regex
const KONTROLL = /[\u0000-\u001f\u007f]/;
export function farligtInnehall(s: string): boolean {
  return s.includes("<") || s.includes(">") || s.includes("://") || KONTROLL.test(s);
}

// Personnamn: samma som ovan, plus att ett snabel-a aldrig hor hemma dar.
export function giltigtPersonnamn(s: string): boolean {
  return s.length > 0 && !farligtInnehall(s) && !s.includes("@");
}

export function epostOk(s: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(s);
}

// 256 bitar slump som base64url: 43 tecken, inga tecken som behover
// URL-kodas. Bara hashen sparas i databasen, sa en lackt tabell ger inga
// giltiga lankar.
export function nyToken(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(32));
  return base64url(bytes);
}

export function giltigtTokenFormat(t: string): boolean {
  return /^[A-Za-z0-9_-]{43}$/.test(t);
}

export async function sha256Hex(s: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s));
  return hex(new Uint8Array(digest));
}

export function hashaToken(t: string): Promise<string> {
  return sha256Hex(t);
}

function base64url(bytes: Uint8Array): string {
  let bin = "";
  for (const b of bytes) bin += String.fromCharCode(b);
  return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function hex(bytes: Uint8Array): string {
  return Array.from(bytes).map((b) => b.toString(16).padStart(2, "0")).join("");
}

// Lanken i mejlet pekar dit formularet skickades fran, om det ar en av vara
// egna adresser. Annars produktionen. Sa gar draft och localhost att testa
// hela vagen utan att en frammande origin nagonsin hamnar i ett mejl.
export function bekraftaUrl(origin: string | null, token: string, tillatna: readonly string[]): string {
  const bas = origin && tillatna.includes(origin) ? origin : tillatna[0];
  return `${bas}/bekrafta?t=${token}`;
}

// Omsandning av bekraftelsemejlet. Tre per lankcykel, tidigast tio minuter
// emellan. Har lanken gatt ut borjar en ny cykel, sa den som kommer tillbaka
// dagen efter inte ar last ute.
export const OMSAND_MAX = 3;
export const OMSAND_VANTA_MS = 10 * 60 * 1000;
export type Omsand = "ny_cykel" | "omsand" | "vanta";
export function omsandBeslut(
  rad: { skickade: number; senast_skickad_at: string; utgar_at: string },
  nu: Date,
): Omsand {
  if (new Date(rad.utgar_at).getTime() < nu.getTime()) return "ny_cykel";
  if (rad.skickade >= OMSAND_MAX) return "vanta";
  if (nu.getTime() - new Date(rad.senast_skickad_at).getTime() < OMSAND_VANTA_MS) return "vanta";
  return "omsand";
}
