import "jsr:@supabase/functions-js@2/edge-runtime.d.ts";
import { createClient, type SupabaseClient } from "jsr:@supabase/supabase-js@2";
import {
  arRobot,
  epostOk,
  esc,
  fornamn,
  giltigSlug,
  giltigtTokenFormat,
  lasProfil,
  nySlug,
  nyToken,
  type Profilfalt,
  redigeraUrl,
  sha256Hex,
  slumpHex,
} from "./hjalp.ts";

/**
 * Tar uppdrag: föreningsmedlemmar som visar på AI-kartan att de är öppna för uppdrag eller
 * tjänster. Bara aktiva medlemmar som är fysiska personer kan lägga upp sig. Registret är
 * beviset, och en engångslänk till medlemmens e-post visar att inkorgen är hens.
 *
 *   GET    /uppdrag              publicerade profiler, öppet för alla
 *   GET    /uppdrag/k/<slug>     räknar ett klick och skickar vidare till medlemmens länk
 *   POST   /uppdrag/lank         mejlar en engångslänk, om adressen är en aktiv medlem
 *   POST   /uppdrag/session      byter länken mot en session på en timme
 *   PUT    /uppdrag/profil       sparar och publicerar, kräver session
 *   DELETE /uppdrag/profil       raderar profilen och dess klick, kräver session
 *
 * Profilerna ligger här och aldrig i kartans git, eftersom git sparar allt för alltid och en
 * borttagen profil då hade funnits kvar i historiken. Funktionen läser medlemsregistret men
 * skriver aldrig i det. Den granskade funktionen medlem rörs inte. Se supabase/README.md.
 */
const ALLOWED_ORIGINS = [
  "https://karta.opensverige.se",
  // Astro dev. Är 4321 upptagen tar Astro nästa port.
  "http://localhost:4321",
  "http://localhost:4322",
];
const KARTAN = "https://karta.opensverige.se";
const SAMTYCKE_VERSION = "2";
const LANK_GILTIG_MS = 30 * 60 * 1000;
const SESSION_MS = 60 * 60 * 1000;
// Samma nivå som anmälan. Skript från en maskin ska stoppas, inte ett rum på en meetup.
const TAK_10MIN = 20;
const TAK_DYGN = 60;
// Resends gratisnivå är 100 mejl per dygn, och anmälan räknar mot 90 i tabellen utskick.
// Länkarna här har ett eget tak under det, så att de aldrig kan tränga undan en anmälan.
const TAK_UTSKICK_DYGN = 90;
const TAK_LANKAR_DYGN = 30;
const TAK_LANKAR_PER_MEDLEM_TIMME = 3;
// En medlem som gått ur syns inte från samma stund. Profilen raderas efter 30 dagar.
const RADERA_EFTER_UTTRADE_MS = 30 * 86400000;
const KLICK_SPARAS_DAGAR = 90;

type Medlem = { id: string; namn: string; epost: string; typ: string; uttradd_at: string | null };
type ProfilRad = Profilfalt & {
  medlem_id: string;
  slug: string;
  samtycke_version: string;
  samtycke_at: string;
  skapad_at: string;
  uppdaterad_at: string;
};
type Publik = Omit<ProfilRad, "medlem_id" | "samtycke_version" | "samtycke_at" | "skapad_at">;
type Database = {
  public: {
    Tables: {
      medlemmar: { Row: Medlem; Insert: never; Update: never; Relationships: [] };
      uppdrag_profiler: {
        Row: ProfilRad;
        Insert: Omit<ProfilRad, "skapad_at" | "uppdaterad_at"> & { skapad_at?: string; uppdaterad_at?: string };
        Update: Partial<ProfilRad>;
        Relationships: [];
      };
      uppdrag_lankar: {
        Row: { token_hash: string; medlem_id: string; skapad_at: string; utgar_at: string; anvand_at: string | null };
        Insert: { token_hash: string; medlem_id: string; utgar_at: string };
        Update: { anvand_at?: string };
        Relationships: [];
      };
      uppdrag_sessioner: {
        Row: { session_hash: string; medlem_id: string; utgar_at: string };
        Insert: { session_hash: string; medlem_id: string; utgar_at: string };
        Update: never;
        Relationships: [];
      };
      uppdrag_klick: {
        Row: { medlem_id: string; dag: string; antal: number };
        Insert: never;
        Update: never;
        Relationships: [];
      };
      uppdrag_forsok: {
        Row: { ip_hash: string; at: string };
        Insert: { ip_hash: string };
        Update: never;
        Relationships: [];
      };
      utskick: { Row: { at: string }; Insert: { at?: string }; Update: never; Relationships: [] };
    };
    Views: { uppdrag_publika: { Row: Publik; Relationships: [] } };
    Functions: { uppdrag_rakna_klick: { Args: { p_slug: string }; Returns: string | null } };
    Enums: Record<string, never>;
    CompositeTypes: Record<string, never>;
  };
};
type Db = SupabaseClient<Database>;

const PUBLIKA_FALT =
  "slug, namn, rubrik, lank, erbjuder, kommun, distans, omraden, bolag_namn, bolag_webbplats, uppdaterad_at";

function corsSkyddad(origin: string | null): Record<string, string> {
  const ok = origin && ALLOWED_ORIGINS.includes(origin);
  return {
    "Access-Control-Allow-Origin": ok ? origin : ALLOWED_ORIGINS[0],
    "Access-Control-Allow-Headers": "content-type, x-uppdrag-session",
    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
    "Vary": "Origin",
    "Content-Type": "application/json",
    "Cache-Control": "no-store",
  };
}

function svar(status: number, body: unknown, headers: Record<string, string>): Response {
  return new Response(JSON.stringify(body), { status, headers });
}

const clean = (v: unknown, max = 200): string => (typeof v === "string" ? v.trim().slice(0, max) : "");
const ilikeMonster = (epost: string): string => epost.replace(/[\\%_]/g, (c) => `\\${c}`);

async function ipHash(ip: string): Promise<string> {
  const salt = Deno.env.get("ANMALAN_SALT") ?? "";
  return await sha256Hex(`uppdrag:${salt}:${ip}`);
}

function dbKlient(): Db {
  return createClient<Database>(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!, {
    auth: { persistSession: false },
  });
}

/* ---------- E-post ---------- */

const SIDFOT_TEXT = `opensverige · ideell förening · org.nr 802557-3422
https://karta.opensverige.se/uppdrag`;
const SIDFOT_HTML = `<hr style="border:0;border-top:1px solid #e4e2dc;margin:28px 0 14px">
<p style="font:12px/1.6 ui-monospace,SFMono-Regular,monospace;color:#5b5651">
opensverige · ideell förening · org.nr 802557-3422<br>
<a href="https://karta.opensverige.se/uppdrag" style="color:#5b5651">karta.opensverige.se/uppdrag</a></p>`;
const STIL_DIV = `font:16px/1.6 -apple-system,Segoe UI,sans-serif;color:#151515;max-width:34em`;
const STIL_MONO = `font:13px/1.7 ui-monospace,SFMono-Regular,monospace;color:#5b5651`;

async function skickaLank(epost: string, namn: string, lank: string): Promise<void> {
  const fornamnText = fornamn(namn);
  const text = `Hej ${fornamnText},

Här är din länk för att lägga upp eller ändra din profil under Tar uppdrag på AI-kartan:

${lank}

Länken gäller i 30 minuter och kan bara användas en gång.

Bad du inte om den? Då kan du strunta i mejlet. Inget ändras.

${SIDFOT_TEXT}`;
  const html = `<div style="${STIL_DIV}">
<p>Hej ${esc(fornamnText)},</p>
<p>Här är din länk för att lägga upp eller ändra din profil under <b>Tar uppdrag</b> på AI-kartan.</p>
<p><a href="${lank}" style="display:inline-block;background:#151515;color:#fff;padding:12px 22px;border-radius:3px;font-weight:700;text-decoration:none">Öppna min profil →</a></p>
<p style="${STIL_MONO}">Fungerar inte knappen? Kopiera adressen:<br>
<a href="${lank}" style="color:#b72c07;word-break:break-all">${lank}</a></p>
<p>Länken gäller i 30 minuter och kan bara användas en gång.</p>
<p>Bad du inte om den? Då kan du strunta i mejlet. Inget ändras.</p>
${SIDFOT_HTML}
</div>`;

  const nyckel = Deno.env.get("RESEND_API_KEY");
  if (!nyckel) throw new Error("RESEND_API_KEY saknas");
  const res = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: { "Authorization": `Bearer ${nyckel}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      from: "opensverige <noreply@send.opensverige.se>",
      to: [epost],
      subject: "Din länk till Tar uppdrag",
      text,
      html,
    }),
  });
  if (!res.ok) throw new Error(`Resend svarade ${res.status}: ${await res.text()}`);
}

/** Kör efter att svaret skickats, så att en medlem och en okänd adress får svar lika fort. */
function iBakgrunden(p: Promise<unknown>): void {
  const runtime = (globalThis as { EdgeRuntime?: { waitUntil(p: Promise<unknown>): void } }).EdgeRuntime;
  if (runtime) runtime.waitUntil(p);
  else p.catch(() => {});
}

/* ---------- Räkning och städning ---------- */

async function utskickKvar(db: Db): Promise<boolean> {
  const dygnSedan = new Date(Date.now() - 86400000).toISOString();
  const [alla, lankar] = await Promise.all([
    db.from("utskick").select("*", { count: "exact", head: true }).gte("at", dygnSedan),
    db.from("uppdrag_lankar").select("*", { count: "exact", head: true }).gte("skapad_at", dygnSedan),
  ]);
  if (alla.error || lankar.error) {
    console.error("kunde inte räkna utskick", alla.error?.message ?? lankar.error?.message);
    return false;
  }
  return (alla.count ?? 0) < TAK_UTSKICK_DYGN && (lankar.count ?? 0) < TAK_LANKAR_DYGN;
}

async function stada(db: Db): Promise<void> {
  if (Math.random() >= 0.05) return;
  const nu = Date.now();
  const dygnSedan = new Date(nu - 86400000).toISOString();
  await db.from("uppdrag_forsok").delete().lt("at", dygnSedan);
  await db.from("uppdrag_lankar").delete().lt("utgar_at", dygnSedan);
  await db.from("uppdrag_sessioner").delete().lt("utgar_at", new Date(nu).toISOString());
  const gransDag = new Date(nu - KLICK_SPARAS_DAGAR * 86400000).toISOString().slice(0, 10);
  await db.from("uppdrag_klick").delete().lt("dag", gransDag);
  const { data: gamla } = await db.from("medlemmar").select("id")
    .lt("uttradd_at", new Date(nu - RADERA_EFTER_UTTRADE_MS).toISOString());
  const ids = (gamla ?? []).map((m) => m.id);
  if (ids.length) {
    await db.from("uppdrag_klick").delete().in("medlem_id", ids);
    await db.from("uppdrag_profiler").delete().in("medlem_id", ids);
  }
}

/** Hastighetsgräns per nätverk, räknad på en saltad hash. Gäller bara anrop som skriver eller mejlar. */
async function forMangaForsok(db: Db, req: Request): Promise<boolean> {
  const ip = (req.headers.get("cf-connecting-ip") ?? req.headers.get("x-real-ip") ?? "").trim();
  if (!ip) return false;
  const hash = await ipHash(ip);
  const dygnSedan = new Date(Date.now() - 86400000).toISOString();
  const { data, error } = await db.from("uppdrag_forsok").select("at").eq("ip_hash", hash).gte("at", dygnSedan);
  if (error) {
    console.error("kunde inte räkna försök", error.message);
    return false;
  }
  const tioMinSedan = Date.now() - 600000;
  if (data.length >= TAK_DYGN || data.filter((f) => new Date(f.at).getTime() > tioMinSedan).length >= TAK_10MIN) {
    return true;
  }
  await db.from("uppdrag_forsok").insert({ ip_hash: hash });
  return false;
}

async function aktivMedlem(db: Db, id: string): Promise<Medlem | null> {
  const { data } = await db.from("medlemmar").select("id, namn, epost, typ, uttradd_at").eq("id", id).maybeSingle();
  return data && data.typ === "fysisk" && !data.uttradd_at ? data : null;
}

async function klickSenaste30(db: Db, medlemId: string): Promise<number> {
  const fran = new Date(Date.now() - 30 * 86400000).toISOString().slice(0, 10);
  const { data } = await db.from("uppdrag_klick").select("antal").eq("medlem_id", medlemId).gte("dag", fran);
  return (data ?? []).reduce((s, r) => s + r.antal, 0);
}

function egenProfil(p: ProfilRad | null) {
  if (!p) return null;
  const { medlem_id: _m, samtycke_version: _v, ...resten } = p;
  return resten;
}

/* ---------- Anropen ---------- */

async function lista(db: Db): Promise<Response> {
  const headers = {
    "Access-Control-Allow-Origin": "*",
    "Content-Type": "application/json",
    "Cache-Control": "public, max-age=60",
  };
  const { data, error } = await db.from("uppdrag_publika").select(PUBLIKA_FALT).order("uppdaterad_at", {
    ascending: false,
  });
  if (error) {
    console.error("kunde inte läsa profiler", error.message);
    return svar(500, { fel: "Kunde inte läsa profilerna." }, headers);
  }
  return svar(200, { antal: data.length, profiler: data }, headers);
}

async function klick(db: Db, req: Request, slug: string): Promise<Response> {
  const tillbaka = { Location: `${KARTAN}/uppdrag`, "Cache-Control": "no-store" };
  if (!giltigSlug(slug)) return new Response(null, { status: 302, headers: tillbaka });
  if (arRobot(req.headers.get("user-agent")) || req.method === "HEAD") {
    const { data } = await db.from("uppdrag_publika").select("lank").eq("slug", slug).maybeSingle();
    return new Response(null, {
      status: 302,
      headers: { Location: data?.lank ?? tillbaka.Location, "Cache-Control": "no-store" },
    });
  }
  const { data: lank, error } = await db.rpc("uppdrag_rakna_klick", { p_slug: slug });
  if (error) console.error("kunde inte räkna klick", error.message);
  return new Response(null, {
    status: 302,
    headers: { Location: lank || tillbaka.Location, "Cache-Control": "no-store" },
  });
}

async function begarLank(
  db: Db,
  body: Record<string, unknown>,
  origin: string | null,
  headers: Record<string, string>,
): Promise<Response> {
  const epost = clean(body.epost, 160).toLowerCase();
  if (!epostOk(epost)) return svar(422, { fel: "Skriv en e-postadress.", falt: ["epost"] }, headers);
  // Taket prövas före uppslaget, så att ett nej aldrig kan säga något om vem som är medlem.
  if (!(await utskickKvar(db))) {
    return svar(503, { fel: "Dagens mejlkvot är slut. Försök igen i morgon." }, { ...headers, "Retry-After": "3600" });
  }
  // Allt efter det här sker i bakgrunden. Svaret är detsamma, och lika snabbt, för alla adresser.
  iBakgrunden((async () => {
    const { data: medlem } = await db.from("medlemmar").select("id, namn, epost, typ, uttradd_at")
      .ilike("epost", ilikeMonster(epost)).is("uttradd_at", null).maybeSingle();
    if (!medlem || medlem.typ !== "fysisk") return;
    const timmeSedan = new Date(Date.now() - 3600000).toISOString();
    const { count } = await db.from("uppdrag_lankar").select("*", { count: "exact", head: true })
      .eq("medlem_id", medlem.id).gte("skapad_at", timmeSedan);
    if ((count ?? 0) >= TAK_LANKAR_PER_MEDLEM_TIMME) return;
    const token = nyToken();
    const token_hash = await sha256Hex(token);
    const { error } = await db.from("uppdrag_lankar").insert({
      token_hash,
      medlem_id: medlem.id,
      utgar_at: new Date(Date.now() + LANK_GILTIG_MS).toISOString(),
    });
    if (error) {
      console.error("kunde inte spara länken", error.message);
      return;
    }
    await db.from("utskick").insert({ at: new Date().toISOString() });
    try {
      await skickaLank(medlem.epost, medlem.namn, redigeraUrl(origin, token, ALLOWED_ORIGINS));
    } catch (e) {
      console.error("utskick misslyckades", e instanceof Error ? e.message : e);
      await db.from("uppdrag_lankar").delete().eq("token_hash", token_hash);
    }
  })());
  return svar(200, { ok: true }, headers);
}

async function startaSession(
  db: Db,
  body: Record<string, unknown>,
  headers: Record<string, string>,
): Promise<Response> {
  const token = clean(body.token, 64);
  if (!giltigtTokenFormat(token)) return svar(400, { fel: "Länken är inte giltig." }, headers);
  const token_hash = await sha256Hex(token);
  const nu = new Date();
  // Förbruka länken atomiskt: av två samtidiga öppningar vinner bara en.
  const { data: rad } = await db.from("uppdrag_lankar").update({ anvand_at: nu.toISOString() })
    .eq("token_hash", token_hash).is("anvand_at", null).gt("utgar_at", nu.toISOString())
    .select("medlem_id").maybeSingle();
  if (!rad) return svar(410, { fel: "Länken är använd eller har gått ut. Be om en ny." }, headers);
  const medlem = await aktivMedlem(db, rad.medlem_id);
  if (!medlem) return svar(410, { fel: "Länken är använd eller har gått ut. Be om en ny." }, headers);

  const session = nyToken();
  const utgar_at = new Date(nu.getTime() + SESSION_MS).toISOString();
  const { error } = await db.from("uppdrag_sessioner").insert({
    session_hash: await sha256Hex(session),
    medlem_id: medlem.id,
    utgar_at,
  });
  if (error) {
    console.error("kunde inte spara sessionen", error.message);
    return svar(500, { fel: "Kunde inte öppna profilen. Försök igen." }, headers);
  }
  const { data: profil } = await db.from("uppdrag_profiler").select("*").eq("medlem_id", medlem.id).maybeSingle();
  return svar(200, {
    session,
    utgar_at,
    profil: egenProfil(profil),
    forslag: { namn: medlem.namn },
    klick30: await klickSenaste30(db, medlem.id),
    samtycke_version: SAMTYCKE_VERSION,
  }, headers);
}

async function medlemForSession(db: Db, req: Request): Promise<Medlem | null> {
  const session = clean(req.headers.get("x-uppdrag-session"), 64);
  if (!giltigtTokenFormat(session)) return null;
  const { data } = await db.from("uppdrag_sessioner").select("medlem_id")
    .eq("session_hash", await sha256Hex(session)).gt("utgar_at", new Date().toISOString()).maybeSingle();
  return data ? await aktivMedlem(db, data.medlem_id) : null;
}

async function sparaProfil(
  db: Db,
  medlem: Medlem,
  body: Record<string, unknown>,
  headers: Record<string, string>,
): Promise<Response> {
  const last = lasProfil(body);
  if ("fel" in last) return svar(422, { fel: "Några fält behöver rättas.", falt: last.fel }, headers);
  const nu = new Date().toISOString();
  const samtycke = { samtycke_version: SAMTYCKE_VERSION, samtycke_at: nu };
  const { data: finns } = await db.from("uppdrag_profiler").select("slug").eq("medlem_id", medlem.id).maybeSingle();

  let profil: ProfilRad | null = null;
  if (finns) {
    const { data, error } = await db.from("uppdrag_profiler").update({ ...last.falt, ...samtycke, uppdaterad_at: nu })
      .eq("medlem_id", medlem.id).select("*").single();
    if (error) {
      console.error("kunde inte uppdatera profilen", error.code, error.message);
      return svar(500, { fel: "Kunde inte spara. Försök igen." }, headers);
    }
    profil = data;
  } else {
    // Adressen sätts en gång och ändras inte när namnet ändras, så en delad länk håller.
    for (let forsok = 0; forsok < 3 && !profil; forsok++) {
      const { data, error } = await db.from("uppdrag_profiler")
        .insert({ medlem_id: medlem.id, slug: nySlug(last.falt.namn, slumpHex(4)), ...last.falt, ...samtycke })
        .select("*").single();
      if (!error) profil = data;
      else if (error.code !== "23505") {
        console.error("kunde inte spara profilen", error.code, error.message);
        return svar(500, { fel: "Kunde inte spara. Försök igen." }, headers);
      }
    }
    if (!profil) return svar(500, { fel: "Kunde inte spara. Försök igen." }, headers);
  }
  return svar(200, { ok: true, profil: egenProfil(profil), klick30: await klickSenaste30(db, medlem.id) }, headers);
}

async function raderaProfil(db: Db, medlem: Medlem, headers: Record<string, string>): Promise<Response> {
  const [klickSvar, profilSvar] = await Promise.all([
    db.from("uppdrag_klick").delete().eq("medlem_id", medlem.id),
    db.from("uppdrag_profiler").delete().eq("medlem_id", medlem.id),
  ]);
  if (klickSvar.error || profilSvar.error) {
    console.error("kunde inte radera", klickSvar.error?.message ?? profilSvar.error?.message);
    return svar(500, { fel: "Kunde inte radera. Försök igen." }, headers);
  }
  return svar(200, { ok: true }, headers);
}

Deno.serve(async (req) => {
  const url = new URL(req.url);
  // Sökvägen efter funktionens namn, till exempel "/k/kim-e-3f9a" eller "".
  const vag = url.pathname.replace(/^.*?\/uppdrag/, "").replace(/\/+$/, "");
  const origin = req.headers.get("origin");
  const db = dbKlient();

  if ((req.method === "GET" || req.method === "HEAD") && vag.startsWith("/k/")) {
    return await klick(db, req, decodeURIComponent(vag.slice(3)));
  }
  if (req.method === "GET" && vag === "") return await lista(db);

  const headers = corsSkyddad(origin);
  if (req.method === "OPTIONS") return new Response(null, { status: 204, headers });
  if (origin && !ALLOWED_ORIGINS.includes(origin)) return svar(403, { fel: "Otillåten origin." }, headers);

  if (await forMangaForsok(db, req)) {
    return svar(429, { fel: "För många försök från samma nätverk. Försök igen om en stund." }, {
      ...headers,
      "Retry-After": "600",
    });
  }
  await stada(db);

  let body: Record<string, unknown> = {};
  if (req.method === "POST" || req.method === "PUT") {
    try {
      const b = await req.json();
      if (typeof b !== "object" || b === null || Array.isArray(b)) throw new Error();
      body = b as Record<string, unknown>;
    } catch {
      return svar(400, { fel: "Ogiltig JSON." }, headers);
    }
  }

  if (req.method === "POST" && vag === "/lank") {
    // Honeypot: ett fält som bara bottar fyller i.
    if (clean(body.webbplats)) return svar(200, { ok: true }, headers);
    return await begarLank(db, body, origin, headers);
  }
  if (req.method === "POST" && vag === "/session") return await startaSession(db, body, headers);

  if (vag === "/profil" && (req.method === "PUT" || req.method === "DELETE")) {
    const medlem = await medlemForSession(db, req);
    if (!medlem) return svar(401, { fel: "Sessionen har gått ut. Be om en ny länk." }, headers);
    return req.method === "PUT"
      ? await sparaProfil(db, medlem, body, headers)
      : await raderaProfil(db, medlem, headers);
  }
  return svar(404, { fel: "Finns inte." }, headers);
});
