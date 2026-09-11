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
function cors(origin) {
  const ok = origin && ALLOWED_ORIGINS.includes(origin);
  return {
    "Access-Control-Allow-Origin": ok ? origin : ALLOWED_ORIGINS[0],
    "Access-Control-Allow-Headers": "content-type",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Content-Type": "application/json"
  };
}
const clean = (v, max = 200)=>typeof v === "string" ? v.trim().slice(0, max) : "";
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
  const db = createClient(Deno.env.get("SUPABASE_URL"), Deno.env.get("SUPABASE_SERVICE_ROLE_KEY"), {
    auth: {
      persistSession: false
    }
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
  return new Response(JSON.stringify({
    ok: true,
    medlemsnummer: count ?? null,
    stadgar_version: STADGAR_VERSION
  }), {
    status: 201,
    headers
  });
});
