import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient, type SupabaseClient } from "jsr:@supabase/supabase-js@2";
import {
  bekraftaUrl,
  epostOk,
  esc,
  farligtInnehall,
  fornamn,
  giltigtPersonnamn,
  giltigtTokenFormat,
  hashaToken,
  nyToken,
  omsandBeslut,
  sha256Hex,
} from "./hjalp.ts";

/**
 * Medlemsanmalan enligt stadgarna § 4, i tva steg.
 *
 *   POST /medlem            formularet. Sparar en vantande anmalan och mejlar
 *                           en engangslank. Ingen medlem skapas har.
 *   POST /medlem/bekrafta   lanken. Skapar medlemsraden, delar ut numret och
 *                           skickar valkomstmejlet.
 *
 * Publik endpoint (verify_jwt = false) — formularet ar oppet for alla, vilket
 * IL 7 kap. 10 § kraver. Skyddet ligger i origin-kontroll, honeypot, strikt
 * validering, hastighetsbegransning och att adressen maste bekraftas.
 *
 * § 4 sager att medlem ar den som anmaler sig och accepterar stadgarna. En
 * anmalan nagon annan skickat i ditt namn ar inte din anmalan. Bekraftelsen
 * ar darfor inte ett extra villkor for medlemskap utan sattet foreningen vet
 * att det ar du som anmalt dig. Se supabase/README.md.
 */
const ALLOWED_ORIGINS = [
  "https://opensverige.se",
  "https://www.opensverige.se",
  "https://opensverige-draft.vercel.app",
  "http://localhost:3011",
  "http://localhost:3000",
];
// Stadgarna ar antagna 2026-04-23 och har aldrig andrats. Nagon § 11-
// stadgeandring har inte skett, sa versionen ar 1.0.
const STADGAR_VERSION = "1.0";
// Taken per natverk ar med flit hoga: pa en meetup kan ett helt rum anmala
// sig fran samma wifi. Detta ska gora ett skript fran en maskin ohallbart,
// inte stoppa en publik.
const TAK_10MIN = 20;
const TAK_DYGN = 50;
// Resends gratisniva ar 100 mejl per dygn. Vi stannar under, sa ett skript
// inte kan tomma kvoten och darmed hindra riktiga anmalningar.
const TAK_UTSKICK_DYGN = 90;
const LANK_GILTIG_MS = 24 * 3600 * 1000;
// Obekraftade anmalningar ar personuppgifter utan medlemskap bakom. De
// stadas bort en vecka efter att lanken gatt ut.
const STADA_EFTER_MS = 7 * 86400000;

type AnmalanRad = {
  id: string;
  token_hash: string;
  namn: string;
  epost: string;
  typ: string;
  firmanamn: string | null;
  orgnr: string | null;
  foretradare: string | null;
  discord: string | null;
  kalla: string;
  stadgar_version: string;
  skapad_at: string;
  utgar_at: string;
  bekraftad_at: string | null;
  skickade: number;
  senast_skickad_at: string;
};
type AnmalanInsert = Omit<AnmalanRad, "id" | "skapad_at" | "bekraftad_at" | "skickade" | "senast_skickad_at"> & {
  skapad_at?: string;
  bekraftad_at?: string | null;
  skickade?: number;
  senast_skickad_at?: string;
};
type MedlemRad = {
  id: string;
  nummer: number;
  namn: string;
  epost: string;
  typ: string;
  firmanamn: string | null;
  orgnr: string | null;
  foretradare: string | null;
  discord: string | null;
  stadgar_version: string;
  stadgar_accepterad_at: string;
  kalla: string;
  anmald_at: string;
  uttradd_at: string | null;
};
type MedlemInsert = Omit<MedlemRad, "id" | "nummer" | "anmald_at" | "uttradd_at" | "stadgar_accepterad_at"> & {
  stadgar_accepterad_at?: string;
};
type ForsokRad = { ip_hash: string; at: string };
type UtskickRad = { at: string };
// Bara de kolumner funktionen ror. Schemat i sin helhet finns i schema.sql.
type Database = {
  public: {
    Tables: {
      medlemmar: { Row: MedlemRad; Insert: MedlemInsert; Update: Partial<MedlemInsert>; Relationships: [] };
      anmalningar: { Row: AnmalanRad; Insert: AnmalanInsert; Update: Partial<AnmalanInsert>; Relationships: [] };
      anmalan_forsok: { Row: ForsokRad; Insert: { ip_hash: string; at?: string }; Update: Partial<ForsokRad>; Relationships: [] };
      utskick: { Row: UtskickRad; Insert: { at?: string }; Update: Partial<UtskickRad>; Relationships: [] };
    };
    Views: Record<string, never>;
    Functions: Record<string, never>;
    Enums: Record<string, never>;
    CompositeTypes: Record<string, never>;
  };
};
type Db = SupabaseClient<Database>;

// Vi sparar aldrig besokarens IP, bara en saltad hash av den. Salten ligger i
// ANMALAN_SALT, sa raderna gar inte att koppla till en adress utan den.
async function ipHash(ip: string): Promise<string> {
  const salt = Deno.env.get("ANMALAN_SALT") ?? "";
  return await sha256Hex(`${salt}:${ip}`);
}

function cors(origin: string | null): Record<string, string> {
  const ok = origin && ALLOWED_ORIGINS.includes(origin);
  return {
    "Access-Control-Allow-Origin": ok ? origin : ALLOWED_ORIGINS[0],
    "Access-Control-Allow-Headers": "content-type",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Content-Type": "application/json",
  };
}

function svar(status: number, body: unknown, headers: Record<string, string>): Response {
  return new Response(JSON.stringify(body), { status, headers });
}

const clean = (v: unknown, max = 200): string => typeof v === "string" ? v.trim().slice(0, max) : "";

// Unika indexen ligger pa lower(epost), darfor ilike. Jokertecken i adressen
// escapas, annars kunde ett understreck matcha fel rad.
const ilikeMonster = (epost: string): string => epost.replace(/[\\%_]/g, (c) => `\\${c}`);

const SIDFOT_TEXT = `opensverige · ideell förening · org.nr 802557-3422
https://opensverige.se`;
const SIDFOT_HTML = `<hr style="border:0;border-top:1px solid #e4e2dc;margin:28px 0 14px">
<p style="font:12px/1.6 ui-monospace,SFMono-Regular,monospace;color:#5b5651">
opensverige · ideell förening · org.nr 802557-3422<br>
<a href="https://opensverige.se" style="color:#5b5651">opensverige.se</a></p>`;
const STIL_DIV = `font:16px/1.6 -apple-system,Segoe UI,sans-serif;color:#151515;max-width:34em`;
const STIL_MONO = `font:13px/1.7 ui-monospace,SFMono-Regular,monospace;color:#5b5651`;

// Namnet ar text fran formularet. I HTML-delen escapas det, annars kunde en
// anmalan med "<a href=...>" som namn ge ett mejl med en lank vi inte skrivit,
// fran var egen signerade avsandare. Valideringen avvisar sant redan innan;
// detta ar andra lagret.
async function skickaBekrafta(epost: string, namn: string, lank: string): Promise<void> {
  const fornamnText = fornamn(namn);
  const fornamnHtml = esc(fornamnText);
  const text = `Hej ${fornamnText},

Den här adressen anmäldes nyss som medlem i opensverige, ideell förening.
Bekräfta att det var du:

${lank}

Länken gäller i 24 timmar och kan bara användas en gång. Först när du
bekräftat blir du medlem och får ditt medlemsnummer.

Var det inte du som anmälde dig? Då kan du strunta i det här mejlet.
Anmälan raderas av sig själv.

${SIDFOT_TEXT}`;

  const html = `<div style="${STIL_DIV}">
<p>Hej ${fornamnHtml},</p>
<p>Den här adressen anmäldes nyss som medlem i <b>opensverige</b>, ideell förening.
Bekräfta att det var du:</p>
<p><a href="${lank}" style="display:inline-block;background:#151515;color:#fff;padding:12px 22px;border-radius:3px;font-weight:700;text-decoration:none">Bekräfta min anmälan →</a></p>
<p style="${STIL_MONO}">Fungerar inte knappen? Kopiera adressen:<br>
<a href="${lank}" style="color:#b72c07;word-break:break-all">${lank}</a></p>
<p>Länken gäller i 24 timmar och kan bara användas en gång. Först när du
bekräftat blir du medlem och får ditt medlemsnummer.</p>
<p>Var det inte du som anmälde dig? Då kan du strunta i det här mejlet.
Anmälan raderas av sig själv.</p>
${SIDFOT_HTML}
</div>`;

  await skicka(epost, "Bekräfta din anmälan till opensverige", text, html);
}

// Kvittot. Skickas efter att medlemskapet registrerats, aldrig som villkor
// for det: gar mejlet inte fram ar personen medlem anda.
async function skickaValkomst(epost: string, namn: string, nummer: number | null): Promise<void> {
  const fornamnText = fornamn(namn);
  const fornamnHtml = esc(fornamnText);
  const rad = nummer ? `Medlemsnummer: ${nummer}\n` : "";
  const text = `Hej ${fornamnText},

Du är nu medlem i opensverige, ideell förening.

${rad}Stadgar: version ${STADGAR_VERSION}

Kallelse till årsmötet skickas till den här adressen. Vill du byta adress
eller gå ur räcker det att du mejlar opensverige@gmail.com.

Medlemsavgiften är frivillig. Medlemskapet gäller oavsett.

Communityt finns i Discorden:
https://discord.gg/ZbV4qB34um

${SIDFOT_TEXT}`;

  const html = `<div style="${STIL_DIV}">
<p>Hej ${fornamnHtml},</p>
<p>Du är nu medlem i <b>opensverige</b>, ideell förening.</p>
<p style="${STIL_MONO}">
${nummer ? `Medlemsnummer: ${nummer}<br>` : ""}Stadgar: version ${STADGAR_VERSION}</p>
<p>Kallelse till årsmötet skickas till den här adressen. Vill du byta adress
eller gå ur räcker det att du mejlar
<a href="mailto:opensverige@gmail.com" style="color:#b72c07">opensverige@gmail.com</a>.</p>
<p>Medlemsavgiften är frivillig. Medlemskapet gäller oavsett.</p>
<p><a href="https://discord.gg/ZbV4qB34um" style="color:#b72c07">Communityt finns i Discorden →</a></p>
${SIDFOT_HTML}
</div>`;

  await skicka(epost, "Välkommen till opensverige", text, html);
}

async function skicka(till: string, amne: string, text: string, html: string): Promise<void> {
  const nyckel = Deno.env.get("RESEND_API_KEY");
  if (!nyckel) throw new Error("RESEND_API_KEY saknas");
  const res = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: { "Authorization": `Bearer ${nyckel}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      from: "opensverige <noreply@send.opensverige.se>",
      to: [till],
      subject: amne,
      text,
      html,
    }),
  });
  if (!res.ok) throw new Error(`Resend svarade ${res.status}: ${await res.text()}`);
}

// Dagskvoten raknas pa vara egna rader, inte hos Resend. Kanner vi inte till
// lage slapper vi igenom: en trasig rakning far inte stoppa anmalningar.
async function utskickKvar(db: Db): Promise<boolean> {
  const dygnSedan = new Date(Date.now() - 86400000).toISOString();
  const { count, error } = await db.from("utskick").select("*", { count: "exact", head: true }).gte("at", dygnSedan);
  if (error) {
    console.error("kunde inte rakna utskick", error.code, error.message);
    return true;
  }
  return (count ?? 0) < TAK_UTSKICK_DYGN;
}

async function loggaUtskick(db: Db): Promise<void> {
  await db.from("utskick").insert({ at: new Date().toISOString() });
}

async function hamtaNummer(db: Db, epost: string): Promise<number | null> {
  const { data } = await db.from("medlemmar").select("nummer").ilike("epost", ilikeMonster(epost)).is("uttradd_at", null).maybeSingle();
  return data?.nummer ?? null;
}

// Ingen cron finns. Vi stadar da och da i stallet, sa tabellerna inte vaxer
// i all evighet med rader ingen langre raknar pa.
async function stada(db: Db): Promise<void> {
  if (Math.random() >= 0.05) return;
  const nu = Date.now();
  const dygnSedan = new Date(nu - 86400000).toISOString();
  await db.from("anmalan_forsok").delete().lt("at", dygnSedan);
  await db.from("utskick").delete().lt("at", dygnSedan);
  await db.from("anmalningar").delete().lt("utgar_at", new Date(nu - STADA_EFTER_MS).toISOString());
}

// Steg 1: formularet. Sparar en vantande anmalan och mejlar lanken.
async function anmal(db: Db, body: Record<string, unknown>, origin: string | null, headers: Record<string, string>): Promise<Response> {
  const namn = clean(body.namn, 120);
  const epost = clean(body.epost, 160).toLowerCase();
  const typ = clean(body.typ) === "juridisk" ? "juridisk" : "fysisk";
  const firmanamn = clean(body.firmanamn, 160) || null;
  const orgnr = clean(body.orgnr, 20) || null;
  const foretradare = clean(body.foretradare, 120) || null;
  const discord = clean(body.discord, 80) || null;
  const kalla = clean(body.kalla) === "discord" ? "discord" : "webb";
  const accepterat = body.accepterat === true;
  const fel: string[] = [];
  // Taggar, URL:er och kontrolltecken avvisas redan har. Escaping i mejlet
  // ar andra lagret; det har ser till att inte ens textversionen kan bara
  // en klickbar adress nagon annan skrivit.
  if (!giltigtPersonnamn(namn)) fel.push("namn");
  if (!epostOk(epost)) fel.push("epost");
  if (!accepterat) fel.push("stadgar");
  if (typ === "juridisk" && (!firmanamn || !foretradare)) fel.push("firmanamn_foretradare");
  if (firmanamn && farligtInnehall(firmanamn)) fel.push("firmanamn");
  if (foretradare && !giltigtPersonnamn(foretradare)) fel.push("foretradare");
  if (discord && farligtInnehall(discord)) fel.push("discord");
  if (fel.length) return svar(422, { fel: "Ofullstandig anmalan.", falt: fel }, headers);

  if (!(await utskickKvar(db))) {
    return svar(503, { fel: "Dagens mejlkvot är slut. Försök igen i morgon." }, { ...headers, "Retry-After": "3600" });
  }

  const nu = new Date();
  const token = nyToken();
  const token_hash = await hashaToken(token);
  const utgar_at = new Date(nu.getTime() + LANK_GILTIG_MS).toISOString();
  const falt = { namn, epost, typ, firmanamn, orgnr, foretradare, discord, kalla, stadgar_version: STADGAR_VERSION };

  // Svaret ar detsamma oavsett om adressen ar ny, vantar pa bekraftelse eller
  // redan ar medlem. Skillnaden syns forst pa bekraftelsesidan, dit bara den
  // som ager inkorgen kommer. Sa kan ingen utifran testa sig fram till vilka
  // som ar med i foreningen.
  const { data: vantande, error: sokFel } = await db.from("anmalningar")
    .select("id, skickade, senast_skickad_at, utgar_at")
    .ilike("epost", ilikeMonster(epost)).is("bekraftad_at", null).maybeSingle();
  if (sokFel) {
    console.error("kunde inte soka anmalan", sokFel.code, sokFel.message);
    return svar(500, { fel: "Kunde inte spara anmalan." }, headers);
  }

  let nyRad = false;
  if (vantande) {
    const rad = vantande;
    const beslut = omsandBeslut(rad, nu);
    // For tatt eller for manga: svara som vanligt men skicka inget. Den som
    // vantar pa sitt mejl far beskedet pa sidan att vanta tio minuter.
    if (beslut === "vanta") return svar(200, { ok: true, stadgar_version: STADGAR_VERSION }, headers);
    const uppdatering: Partial<AnmalanInsert> = beslut === "ny_cykel"
      ? { ...falt, token_hash, utgar_at, skapad_at: nu.toISOString(), skickade: 1, senast_skickad_at: nu.toISOString() }
      : { ...falt, token_hash, utgar_at, skickade: rad.skickade + 1, senast_skickad_at: nu.toISOString() };
    const { error } = await db.from("anmalningar").update(uppdatering).eq("id", rad.id);
    if (error) {
      console.error("kunde inte uppdatera anmalan", error.code, error.message);
      return svar(500, { fel: "Kunde inte spara anmalan." }, headers);
    }
  } else {
    const { error } = await db.from("anmalningar").insert({ ...falt, token_hash, utgar_at });
    if (error) {
      // Kapplopning: tva anmalningar for samma adress samtidigt. Den forsta
      // vann och dess mejl ar pa vag, sa det har svaret kan lugnt saga ok.
      if (error.code === "23505") return svar(200, { ok: true, stadgar_version: STADGAR_VERSION }, headers);
      console.error("kunde inte spara anmalan", error.code, error.message);
      return svar(500, { fel: "Kunde inte spara anmalan." }, headers);
    }
    nyRad = true;
  }

  await loggaUtskick(db);
  try {
    await skickaBekrafta(epost, namn, bekraftaUrl(origin, token, ALLOWED_ORIGINS));
  } catch (e) {
    console.error("utskick misslyckades", e instanceof Error ? e.message : e);
    // Utan mejl finns ingen lank att klicka pa. Ta bort raden sa ett nytt
    // forsok inte stoppas av omsandningsregeln.
    if (nyRad) await db.from("anmalningar").delete().eq("token_hash", token_hash);
    return svar(502, { fel: "Kunde inte skicka bekräftelsemejlet. Försök igen om en stund." }, headers);
  }
  return svar(200, { ok: true, stadgar_version: STADGAR_VERSION }, headers);
}

// Steg 2: lanken. Har blir personen medlem.
async function bekrafta(db: Db, body: Record<string, unknown>, headers: Record<string, string>): Promise<Response> {
  const token = clean(body.token, 64);
  if (!giltigtTokenFormat(token)) return svar(400, { fel: "ogiltig" }, headers);
  const token_hash = await hashaToken(token);
  const { data, error } = await db.from("anmalningar").select("*").eq("token_hash", token_hash).maybeSingle();
  if (error) {
    console.error("kunde inte hamta anmalan", error.code, error.message);
    return svar(500, { fel: "Kunde inte hamta anmalan." }, headers);
  }
  const rad = data;
  if (!rad) return svar(404, { fel: "ogiltig" }, headers);
  const nu = new Date();
  if (!rad.bekraftad_at && new Date(rad.utgar_at).getTime() < nu.getTime()) return svar(410, { fel: "utgangen" }, headers);

  let status: "ny" | "redan" | "bekraftad";
  let nummer: number | null = null;
  if (rad.bekraftad_at) {
    // Lanken ar redan anvand, till exempel en omladdning av sidan. Visa
    // samma sida igen. Bara den som har lanken kommer hit.
    status = "bekraftad";
    nummer = await hamtaNummer(db, rad.epost);
  } else {
    // Forbruka lanken atomiskt: av tva samtidiga klick vinner bara ett.
    const { data: vunnen } = await db.from("anmalningar").update({ bekraftad_at: nu.toISOString() })
      .eq("id", rad.id).is("bekraftad_at", null).select("id").maybeSingle();
    if (!vunnen) {
      status = "bekraftad";
      nummer = await hamtaNummer(db, rad.epost);
    } else {
      // Stadgarna accepterades nar formularet skickades; medlemskapet borjar
      // nu, nar adressen bekraftats. anmald_at far darfor sitt default.
      const { data: medlem, error: insFel } = await db.from("medlemmar").insert({
        namn: rad.namn,
        epost: rad.epost,
        typ: rad.typ,
        firmanamn: rad.firmanamn,
        orgnr: rad.orgnr,
        foretradare: rad.foretradare,
        discord: rad.discord,
        kalla: rad.kalla,
        stadgar_version: rad.stadgar_version,
        stadgar_accepterad_at: rad.skapad_at,
      }).select("nummer").single();
      if (!insFel) {
        status = "ny";
        nummer = medlem.nummer;
      } else if (insFel.code === "23505") {
        // Adressen ar redan medlem. Numret ar permanent, sa hen far samma.
        status = "redan";
        nummer = await hamtaNummer(db, rad.epost);
      } else {
        console.error("insert misslyckades", insFel.code, insFel.message);
        // Lamna tillbaka lanken sa den gar att prova igen.
        await db.from("anmalningar").update({ bekraftad_at: null }).eq("id", rad.id);
        return svar(500, { fel: "Kunde inte spara medlemskapet." }, headers);
      }
      if (status === "ny") {
        // Kvittot far aldrig falla medlemskapet. Ar kvoten slut eller Resend
        // nere loggar vi och gar vidare: personen ar medlem, numret star pa
        // sidan.
        try {
          if (await utskickKvar(db)) {
            await loggaUtskick(db);
            await skickaValkomst(rad.epost, rad.namn, nummer);
          } else {
            console.error("valkomstmejl hoppades over: dagskvoten ar slut");
          }
        } catch (e) {
          console.error("utskick misslyckades", e instanceof Error ? e.message : e);
        }
      }
    }
  }
  return svar(200, {
    ok: true,
    status,
    medlemsnummer: nummer,
    anmalan: {
      namn: rad.namn,
      epost: rad.epost,
      typ: rad.typ,
      firmanamn: rad.firmanamn,
      orgnr: rad.orgnr,
      foretradare: rad.foretradare,
      discord: rad.discord,
      stadgar_version: rad.stadgar_version,
      stadgar_accepterad_at: rad.skapad_at,
    },
  }, headers);
}

Deno.serve(async (req) => {
  const origin = req.headers.get("origin");
  const headers = cors(origin);
  if (req.method === "OPTIONS") return new Response(null, { status: 204, headers });
  if (req.method !== "POST") return svar(405, { fel: "Endast POST." }, headers);
  if (origin && !ALLOWED_ORIGINS.includes(origin)) return svar(403, { fel: "Otillaten origin." }, headers);
  let body: Record<string, unknown>;
  try {
    body = await req.json();
  } catch {
    return svar(400, { fel: "Ogiltig JSON." }, headers);
  }
  if (typeof body !== "object" || body === null) return svar(400, { fel: "Ogiltig JSON." }, headers);

  const vag = new URL(req.url).pathname.replace(/\/+$/, "");
  const arBekrafta = vag.endsWith("/bekrafta");

  // Honeypot: falt som bara bottar fyller i.
  if (!arBekrafta && clean(body.webbplats)) return svar(200, { ok: true }, headers);

  const db: Db = createClient<Database>(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!, {
    auth: { persistSession: false },
  });

  // Rakna forst, spara sedan. Aven ogiltiga forsok raknas, annars kan man
  // spamma skrap gratis. Kanner vi inte igen avsandaren slapper vi igenom:
  // en trasig rakning far inte hindra nagon fran att bli medlem.
  // Cloudflare framfor Supabase satter cf-connecting-ip till den anslutande
  // klienten. x-forwarded-for kan klienten sjalv skicka med, och da hade
  // forsta vardet varit pahittat och taket gatt att kringga.
  const ip = (req.headers.get("cf-connecting-ip") ?? req.headers.get("x-real-ip") ??
    (req.headers.get("x-forwarded-for") ?? "").split(",")[0]).trim();
  if (ip) {
    const hash = await ipHash(ip);
    const dygnSedan = new Date(Date.now() - 86400000).toISOString();
    const { data: forsok, error: rlFel } = await db.from("anmalan_forsok").select("at").eq("ip_hash", hash).gte("at", dygnSedan);
    if (rlFel) {
      console.error("kunde inte rakna forsok", rlFel.code, rlFel.message);
    } else {
      const tioMinSedan = Date.now() - 600000;
      const rader = forsok;
      const senaste = rader.filter((f) => new Date(f.at).getTime() > tioMinSedan);
      if (rader.length >= TAK_DYGN || senaste.length >= TAK_10MIN) {
        return svar(429, { fel: "För många försök från samma nätverk. Försök igen om en stund." }, { ...headers, "Retry-After": "600" });
      }
      await db.from("anmalan_forsok").insert({ ip_hash: hash });
    }
  }
  await stada(db);

  return arBekrafta ? await bekrafta(db, body, headers) : await anmal(db, body, origin, headers);
});
