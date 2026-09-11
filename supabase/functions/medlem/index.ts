import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "jsr:@supabase/supabase-js@2";
/**
 * Medlemsanmalan enligt stadgarna § 4.
 * Publik endpoint (verify_jwt = false) — formularet ar oppet for alla, vilket
 * IL 7 kap. 10 § kraver. Skyddet ligger darfor i origin-kontroll, honeypot
 * och strikt validering istallet for i en token.
 */ const ALLOWED_ORIGINS = [
  "https://opensverige.se",
  "https://www.opensverige.se",
  "https://opensverige-draft.vercel.app",
  "http://localhost:3011",
  "http://localhost:3000"
];
const STADGAR_VERSION = "2026-09-10";
// Taken ar med flit hoga. Pa en meetup kan ett helt rum anmala sig fran samma
// wifi, och stadgarna § 4 later oss inte lagga till villkor for medlemskap.
// Detta ska gora ett skript fran en maskin ohallbart, inte stoppa en publik.
const TAK_10MIN = 20;
const TAK_DYGN = 100;

// Vi sparar aldrig besokarens IP, bara en saltad hash av den. Salten ligger i
// ANMALAN_SALT, sa raderna gar inte att koppla till en adress utan den.
async function ipHash(ip: string): Promise<string> {
  const salt = Deno.env.get("ANMALAN_SALT") ?? "";
  const bytes = new TextEncoder().encode(`${salt}:${ip}`);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest)).map((b)=>b.toString(16).padStart(2, "0")).join("");
}
function cors(origin: string | null) {
  const ok = origin && ALLOWED_ORIGINS.includes(origin);
  return {
    "Access-Control-Allow-Origin": ok ? origin : ALLOWED_ORIGINS[0],
    "Access-Control-Allow-Headers": "content-type",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Content-Type": "application/json"
  };
}
const clean = (v: unknown, max = 200): string =>typeof v === "string" ? v.trim().slice(0, max) : "";
// Skickas efter att medlemskapet registrerats, aldrig som villkor for det.
// Stadgarna § 4 sager att medlem ar den som anmaler sig, sa ett mejl som inte
// gar fram far inte pa nagot satt paverka medlemskapet.
async function skickaValkomst(epost: string, namn: string, nummer: number | null): Promise<void> {
  const nyckel = Deno.env.get("RESEND_API_KEY");
  if (!nyckel) return;
  const fornamn = namn.split(" ")[0];
  const rad = nummer ? `Medlemsnummer: ${nummer}\n` : "";
  const text = `Hej ${fornamn},

Du är nu medlem i opensverige, ideell förening.

${rad}Stadgar: version ${STADGAR_VERSION}

Kallelse till årsmötet skickas till den här adressen. Vill du byta adress
eller gå ur räcker det att du mejlar opensverige@gmail.com.

Medlemsavgiften är frivillig. Medlemskapet gäller oavsett.

Communityt finns i Discorden:
https://discord.gg/ZbV4qB34um

opensverige · ideell förening · org.nr 802557-3422
https://opensverige.se`;

  const html = `<div style="font:16px/1.6 -apple-system,Segoe UI,sans-serif;color:#151515;max-width:34em">
<p>Hej ${fornamn},</p>
<p>Du är nu medlem i <b>opensverige</b>, ideell förening.</p>
<p style="font:13px/1.7 ui-monospace,SFMono-Regular,monospace;color:#5b5651">
${nummer ? `Medlemsnummer: ${nummer}<br>` : ""}Stadgar: version ${STADGAR_VERSION}</p>
<p>Kallelse till årsmötet skickas till den här adressen. Vill du byta adress
eller gå ur räcker det att du mejlar
<a href="mailto:opensverige@gmail.com" style="color:#b72c07">opensverige@gmail.com</a>.</p>
<p>Medlemsavgiften är frivillig. Medlemskapet gäller oavsett.</p>
<p><a href="https://discord.gg/ZbV4qB34um" style="color:#b72c07">Communityt finns i Discorden →</a></p>
<hr style="border:0;border-top:1px solid #e4e2dc;margin:28px 0 14px">
<p style="font:12px/1.6 ui-monospace,SFMono-Regular,monospace;color:#5b5651">
opensverige · ideell förening · org.nr 802557-3422<br>
<a href="https://opensverige.se" style="color:#5b5651">opensverige.se</a></p>
</div>`;

  const svar = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${nyckel}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      from: "opensverige <noreply@send.opensverige.se>",
      to: [
        epost
      ],
      subject: "Välkommen till opensverige",
      text,
      html
    })
  });
  if (!svar.ok) throw new Error(`Resend svarade ${svar.status}: ${await svar.text()}`);
}

Deno.serve(async (req)=>{
  const origin = req.headers.get("origin");
  const headers = cors(origin);
  if (req.method === "OPTIONS") return new Response(null, {
    status: 204,
    headers
  });
  if (req.method !== "POST") return new Response(JSON.stringify({
    fel: "Endast POST."
  }), {
    status: 405,
    headers
  });
  if (origin && !ALLOWED_ORIGINS.includes(origin)) return new Response(JSON.stringify({
    fel: "Otillaten origin."
  }), {
    status: 403,
    headers
  });
  let body;
  try {
    body = await req.json();
  } catch  {
    return new Response(JSON.stringify({
      fel: "Ogiltig JSON."
    }), {
      status: 400,
      headers
    });
  }
  // Honeypot: falt som bara bottar fyller i.
  if (clean(body.webbplats)) return new Response(JSON.stringify({
    ok: true
  }), {
    status: 200,
    headers
  });
  const db = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!, {
    auth: {
      persistSession: false
    }
  });
  // Rakna forst, spara sedan. Aven ogiltiga forsok raknas, annars kan man
  // spamma skrap gratis. Kanner vi inte igen avsandaren slapper vi igenom:
  // en trasig rakning far inte hindra nagon fran att bli medlem.
  const ip = (req.headers.get("x-forwarded-for") ?? "").split(",")[0].trim();
  if (ip) {
    const hash = await ipHash(ip);
    const dygnSedan = new Date(Date.now() - 86400000).toISOString();
    const { data: forsok, error: rlFel } = await db.from("anmalan_forsok").select("at").eq("ip_hash", hash).gte("at", dygnSedan);
    if (rlFel) {
      console.error("kunde inte rakna forsok", rlFel.code, rlFel.message);
    } else {
      const tioMinSedan = Date.now() - 600000;
      const senaste = forsok.filter((f)=>new Date(f.at).getTime() > tioMinSedan);
      if (forsok.length >= TAK_DYGN || senaste.length >= TAK_10MIN) {
        return new Response(JSON.stringify({
          fel: "For manga anmalningar fran samma natverk. Forsok igen om en stund."
        }), {
          status: 429,
          headers: {
            ...headers,
            "Retry-After": "600"
          }
        });
      }
      await db.from("anmalan_forsok").insert({
        ip_hash: hash
      });
      // Ingen cron finns. Vi stadar da och da i stallet, sa tabellen inte
      // vaxer i all evighet med rader ingen langre raknar pa.
      if (Math.random() < 0.05) await db.from("anmalan_forsok").delete().lt("at", dygnSedan);
    }
  }
  const namn = clean(body.namn, 120);
  const epost = clean(body.epost, 160).toLowerCase();
  const typ = clean(body.typ) === "juridisk" ? "juridisk" : "fysisk";
  const firmanamn = clean(body.firmanamn, 160) || null;
  const orgnr = clean(body.orgnr, 20) || null;
  const foretradare = clean(body.foretradare, 120) || null;
  const discord = clean(body.discord, 80) || null;
  const kalla = clean(body.kalla) === "discord" ? "discord" : "webb";
  const accepterat = body.accepterat === true;
  const fel = [];
  if (!namn) fel.push("namn");
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(epost)) fel.push("epost");
  if (!accepterat) fel.push("stadgar");
  if (typ === "juridisk" && (!firmanamn || !foretradare)) fel.push("firmanamn_foretradare");
  if (fel.length) return new Response(JSON.stringify({
    fel: "Ofullstandig anmalan.",
    falt: fel
  }), {
    status: 422,
    headers
  });
  const { error } = await db.from("medlemmar").insert({
    namn,
    epost,
    typ,
    firmanamn,
    orgnr,
    foretradare,
    discord,
    kalla,
    stadgar_version: STADGAR_VERSION
  });
  if (error) {
    if (error.code === "23505") return new Response(JSON.stringify({
      fel: "Du ar redan medlem.",
      redan: true
    }), {
      status: 409,
      headers
    });
    console.error("insert misslyckades", error.code, error.message);
    return new Response(JSON.stringify({
      fel: "Kunde inte spara anmalan."
    }), {
      status: 500,
      headers
    });
  }
  const { count } = await db.from("medlemmar").select("id", {
    count: "exact",
    head: true
  }).is("uttradd_at", null);
  // Mejlet far inte kunna falla anmalan. Gar det fel loggar vi och svarar 201
  // anda — personen ar medlem, det ar bara kvittot som uteblev.
  try {
    await skickaValkomst(epost, namn, count ?? null);
  } catch (e) {
    console.error("valkomstmejl misslyckades", e instanceof Error ? e.message : e);
  }
  return new Response(JSON.stringify({
    ok: true,
    medlemsnummer: count ?? null,
    stadgar_version: STADGAR_VERSION
  }), {
    status: 201,
    headers
  });
});
