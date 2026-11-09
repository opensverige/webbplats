// Rena hjälpfunktioner utan Deno.serve, så de går att testa:
//   deno test --allow-net=jsr.io hjalp_test.ts
//
// Några av dem finns också i ../medlem/hjalp.ts. Funktionerna driftsätts var för sig
// med sina egna filer, så den granskade anmälan aldrig påverkas av en ändring här.

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

export function fornamn(namn: string): string {
  return namn.split(/[\s ]+/)[0] ?? "";
}

// deno-lint-ignore no-control-regex
const KONTROLL = /[\u0000-\u001f\u007f]/;
export function farligtInnehall(s: string): boolean {
  return s.includes("<") || s.includes(">") || s.includes("://") || KONTROLL.test(s);
}

/**
 * Tio siffror i följd, med eller utan bindestreck, plus eller mellanslag före de fyra sista.
 * Fångar personnummer i alla vanliga former, och även en enskild firmas organisationsnummer,
 * som är detsamma. Ett aktiebolags nummer fångas också. Det hör inte hemma i en profil heller.
 */
const PERSONNUMMER = /\d{6}[-+ ]?\d{4}/;
export function harPersonnummer(s: string): boolean {
  return PERSONNUMMER.test(s);
}

export function giltigtNamn(s: string): boolean {
  return s.length > 0 && s.length <= 60 && !farligtInnehall(s) && !s.includes("@") && !harPersonnummer(s);
}

export function giltigText(s: string, max: number): boolean {
  return s.length > 0 && s.length <= max && !farligtInnehall(s) && !harPersonnummer(s);
}

export function epostOk(s: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(s);
}

/**
 * En publik https-adress, eller null. Inloggningsuppgifter i adressen och adresser utan punkt
 * i värdnamnet avvisas. Adressen sparas i den form URL-tolken ger, så att samma länk alltid
 * skrivs på samma sätt.
 */
export function httpsAdress(s: string): string | null {
  if (!s || s.length > 300) return null;
  let u: URL;
  try {
    u = new URL(s);
  } catch {
    return null;
  }
  if (u.protocol !== "https:") return null;
  if (u.username || u.password) return null;
  if (!u.hostname.includes(".") || u.hostname.endsWith(".")) return null;
  const href = u.href;
  if (href.length > 300 || /[\s<>"]/.test(href)) return null;
  return href;
}

export const ERBJUDER = ["uppdrag", "tjanster", "bada"] as const;
export type Erbjuder = (typeof ERBJUDER)[number];
export function giltigtErbjuder(s: string): s is Erbjuder {
  return (ERBJUDER as readonly string[]).includes(s);
}

/** Kommunkoden, fyra siffror. Kartan slår upp namnet och hoppar över en kod den inte känner. */
export function giltigKommun(s: string): boolean {
  return /^\d{4}$/.test(s);
}

/**
 * Högst tre områden ur kartans lista, i formen id. Kartan visar bara de id den känner till,
 * så ett område som tas bort ur listan försvinner från korten utan att något går sönder.
 */
export const MAX_OMRADEN = 3;
export function giltigaOmraden(v: unknown): string[] | null {
  if (!Array.isArray(v)) return null;
  const ut: string[] = [];
  for (const x of v) {
    if (typeof x !== "string" || !/^[a-z][a-z_]{1,39}$/.test(x)) return null;
    if (!ut.includes(x)) ut.push(x);
  }
  return ut.length <= MAX_OMRADEN ? ut : null;
}

/**
 * Bilden på kortet. Webbläsaren beskär den till en kvadrat och kodar om den, så att metadata som
 * plats försvinner. Funktionen godtar ändå bara det enkla formatet: WebP utan utökade block och
 * JPEG utan EXIF- och XMP-block. En bild med metadata stoppas i stället för att rensas.
 */
export const BILD_MAX_BYTES = 300 * 1024;
export type Bild = { bytes: Uint8Array; typ: "image/webp" | "image/jpeg" };

function base64Bytes(s: string): Uint8Array | null {
  if (!/^[A-Za-z0-9+/]+={0,2}$/.test(s)) return null;
  try {
    const bin = atob(s);
    const ut = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) ut[i] = bin.charCodeAt(i);
    return ut;
  } catch {
    return null;
  }
}

const ascii = (b: Uint8Array, fran: number, langd: number): string =>
  String.fromCharCode(...b.subarray(fran, fran + langd));

/** WebP med ett enda bildblock, VP8 eller VP8L. Det utökade formatet VP8X kan bära EXIF och XMP. */
export function enkelWebp(b: Uint8Array): boolean {
  return b.length > 30 && ascii(b, 0, 4) === "RIFF" && ascii(b, 8, 4) === "WEBP" &&
    (ascii(b, 12, 4) === "VP8 " || ascii(b, 12, 4) === "VP8L");
}

/** JPEG utan APP1 (EXIF och XMP) och utan APP13 (IPTC). Läser blocken fram till bilddatat. */
export function renJpeg(b: Uint8Array): boolean {
  if (b.length < 4 || b[0] !== 0xff || b[1] !== 0xd8) return false;
  let i = 2;
  while (i + 4 <= b.length) {
    if (b[i] !== 0xff) return false;
    const typ = b[i + 1];
    if (typ === 0xda) return true;
    if (typ === 0xe1 || typ === 0xed) return false;
    const langd = (b[i + 2] << 8) | b[i + 3];
    if (langd < 2) return false;
    i += 2 + langd;
  }
  return false;
}

/**
 * Läser bilden ur formuläret, en data-adress. Ger null när ingen ny bild skickades och "fel" när
 * det som skickades inte går igenom.
 */
export function lasBild(v: unknown): Bild | null | "fel" {
  if (v === undefined || v === null || v === "") return null;
  if (typeof v !== "string" || v.length > Math.ceil(BILD_MAX_BYTES / 3) * 4 + 40) return "fel";
  const m = /^data:(image\/webp|image\/jpeg);base64,(.+)$/.exec(v);
  if (!m) return "fel";
  const bytes = base64Bytes(m[2]);
  if (!bytes || bytes.length > BILD_MAX_BYTES) return "fel";
  const typ = m[1] as Bild["typ"];
  if (typ === "image/webp" ? !enkelWebp(bytes) : !renJpeg(bytes)) return "fel";
  return { bytes, typ };
}

/** Filnamnet i lagringen: slumpat, så att ingen kan gissa sig till en annans bild. */
export function bildFilnamn(typ: Bild["typ"]): string {
  return `${crypto.randomUUID()}.${typ === "image/webp" ? "webp" : "jpg"}`;
}

export function giltigtBildnamn(s: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.(webp|jpg)$/.test(s);
}

const TECKEN: Record<string, string> = { "å": "a", "ä": "a", "ö": "o", "é": "e", "ü": "u" };
/** Adressens del för profilen: namnet i små bokstäver och fyra slumpade tecken, så två Kim inte krockar. */
export function nySlug(namn: string, slump: string): string {
  const bas = namn
    .toLowerCase()
    .replace(/[åäöéü]/g, (c) => TECKEN[c] ?? c)
    .normalize("NFKD")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 40)
    .replace(/-+$/g, "");
  return bas ? `${bas}-${slump}` : `medlem-${slump}`;
}

export function slumpHex(antal: number): string {
  const bytes = crypto.getRandomValues(new Uint8Array(Math.ceil(antal / 2)));
  return Array.from(bytes).map((b) => b.toString(16).padStart(2, "0")).join("").slice(0, antal);
}

export function giltigSlug(s: string): boolean {
  return s.length <= 60 && /^[a-z0-9]+(-[a-z0-9]+)*$/.test(s);
}

// 256 bitar slump som base64url. Bara hashen sparas, så en läckt tabell ger inga giltiga länkar.
export function nyToken(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(32));
  let bin = "";
  for (const b of bytes) bin += String.fromCharCode(b);
  return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

export function giltigtTokenFormat(t: string): boolean {
  return /^[A-Za-z0-9_-]{43}$/.test(t);
}

export async function sha256Hex(s: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s));
  return Array.from(new Uint8Array(digest)).map((b) => b.toString(16).padStart(2, "0")).join("");
}

/**
 * Länken i mejlet pekar dit formuläret skickades från, om det är en av våra adresser. Koden
 * ligger efter # och skickas därför aldrig till någon server, varken i loggar eller i statistik.
 */
export function redigeraUrl(origin: string | null, token: string, tillatna: readonly string[]): string {
  const bas = origin && tillatna.includes(origin) ? origin : tillatna[0];
  return `${bas}/uppdrag/redigera#t=${token}`;
}

/**
 * Länkförhandsvisare, sökmotorer och skript räknas inte som klick. Det är en grov sållning,
 * och den ska bara hålla siffran i rätt storleksordning.
 */
const ROBOT =
  /bot|crawl|spider|slurp|preview|facebookexternalhit|embedly|whatsapp|telegram|discord|slack|curl|wget|python|headless|monitor/i;
export function arRobot(ua: string | null): boolean {
  return !ua || ROBOT.test(ua);
}

export type Profilfalt = {
  namn: string;
  rubrik: string;
  lank: string;
  erbjuder: Erbjuder;
  kommun: string | null;
  distans: boolean;
  omraden: string[];
  bolag_namn: string | null;
  bolag_webbplats: string | null;
};

const text = (
  v: unknown,
  max: number,
): string => (typeof v === "string" ? v.trim().replace(/\s+/g, " ").slice(0, max + 1) : "");

/** Läser och prövar formuläret. Ger fälten, eller namnen på de fält som inte gick igenom. */
export function lasProfil(body: Record<string, unknown>): { falt: Profilfalt } | { fel: string[] } {
  const fel: string[] = [];
  const namn = text(body.namn, 60);
  const rubrik = text(body.rubrik, 90);
  const lank = httpsAdress(text(body.lank, 300));
  const erbjuder = text(body.erbjuder, 20);
  const kommunText = text(body.kommun, 4);
  const omraden = giltigaOmraden(body.omraden ?? []);
  const bolagNamn = text(body.bolag_namn, 80);
  const bolagWebbText = text(body.bolag_webbplats, 300);
  const bolagWebb = bolagWebbText ? httpsAdress(bolagWebbText) : null;

  if (!giltigtNamn(namn)) fel.push("namn");
  if (!giltigText(rubrik, 90)) fel.push("rubrik");
  if (!lank) fel.push("lank");
  if (!giltigtErbjuder(erbjuder)) fel.push("erbjuder");
  if (kommunText && !giltigKommun(kommunText)) fel.push("kommun");
  if (typeof body.distans !== "boolean") fel.push("distans");
  if (!omraden) fel.push("omraden");
  if (bolagNamn && !giltigText(bolagNamn, 80)) fel.push("bolag_namn");
  if (bolagWebbText && !bolagWebb) fel.push("bolag_webbplats");
  if (body.samtycke !== true) fel.push("samtycke");
  if (fel.length) return { fel };

  return {
    falt: {
      namn,
      rubrik,
      lank: lank!,
      erbjuder: erbjuder as Erbjuder,
      kommun: kommunText || null,
      distans: body.distans as boolean,
      omraden: omraden!,
      bolag_namn: bolagNamn || null,
      bolag_webbplats: bolagWebb,
    },
  };
}
