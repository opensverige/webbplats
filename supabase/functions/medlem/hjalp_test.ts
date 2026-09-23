import { assert, assertEquals, assertMatch, assertNotEquals } from "jsr:@std/assert@1";
import {
  epostOk,
  esc,
  farligtInnehall,
  fornamn,
  giltigtPersonnamn,
  giltigtTokenFormat,
  hashaToken,
  nyToken,
} from "./hjalp.ts";

Deno.test("esc kodar allt som kan bryta HTML", () => {
  assertEquals(esc(`<a href="x">Tom & Jerry's</a>`), "&lt;a href=&quot;x&quot;&gt;Tom &amp; Jerry&#39;s&lt;/a&gt;");
  assertEquals(esc("Åsa-Britt Öberg"), "Åsa-Britt Öberg");
  assertEquals(esc(""), "");
});

Deno.test("fornamn delar på alla slags blanktecken, inte bara mellanslag", () => {
  assertEquals(fornamn("Anna Andersson"), "Anna");
  assertEquals(fornamn("Anna\tAndersson"), "Anna");
  assertEquals(fornamn("Anna Andersson"), "Anna");
  assertEquals(fornamn("Anna"), "Anna");
});

Deno.test("farligtInnehall fångar taggar, URL:er och kontrolltecken", () => {
  assert(farligtInnehall("<a/href=https://evil.se>Klicka</a>"));
  assert(farligtInnehall("Anna https://evil.se"));
  assert(farligtInnehall("Anna\u0000"));
  assert(farligtInnehall("Anna\u001b[31m"));
  assert(!farligtInnehall("Kalles Bygg & Fix AB"));
  assert(!farligtInnehall("Nils-Åke O'Neill"));
  assert(!farligtInnehall("Zoë Ñ 李"));
});

Deno.test("giltigtPersonnamn avvisar snabel-a men tillåter vanliga namn", () => {
  assert(giltigtPersonnamn("Anna Andersson"));
  assert(giltigtPersonnamn("Nils-Åke O'Neill"));
  assert(!giltigtPersonnamn("anna@evil.se"));
  assert(!giltigtPersonnamn("<b>Anna</b>"));
  assert(!giltigtPersonnamn(""));
});

Deno.test("epostOk", () => {
  assert(epostOk("anna@exempel.se"));
  assert(!epostOk("anna@exempel"));
  assert(!epostOk("anna exempel.se"));
  assert(!epostOk(""));
});

Deno.test("token är 43 tecken base64url och unik", () => {
  const a = nyToken();
  const b = nyToken();
  assertMatch(a, /^[A-Za-z0-9_-]{43}$/);
  assertNotEquals(a, b);
  assert(giltigtTokenFormat(a));
  assert(!giltigtTokenFormat(a + "x"));
  assert(!giltigtTokenFormat(a.slice(1)));
  assert(!giltigtTokenFormat("a".repeat(42) + "+"));
});

Deno.test("hashaToken är deterministisk sha256 hex", async () => {
  const h1 = await hashaToken("abc");
  const h2 = await hashaToken("abc");
  assertEquals(h1, h2);
  assertEquals(h1, "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
  assertNotEquals(await hashaToken("abd"), h1);
});

import { bekraftaUrl, omsandBeslut } from "./hjalp.ts";

Deno.test("bekraftaUrl pekar på produktionsdomänen om origin är okänd", () => {
  const tillatna = ["https://opensverige.se", "http://localhost:3000"];
  assertEquals(bekraftaUrl(null, "abc", tillatna), "https://opensverige.se/bekrafta?t=abc");
  assertEquals(bekraftaUrl("https://evil.se", "abc", tillatna), "https://opensverige.se/bekrafta?t=abc");
  assertEquals(bekraftaUrl("http://localhost:3000", "abc", tillatna), "http://localhost:3000/bekrafta?t=abc");
});

Deno.test("omsandBeslut: ny cykel när länken gått ut", () => {
  const nu = new Date("2026-09-24T12:00:00Z");
  const rad = { skickade: 3, senast_skickad_at: "2026-09-22T12:00:00Z", utgar_at: "2026-09-23T12:00:00Z" };
  assertEquals(omsandBeslut(rad, nu), "ny_cykel");
});

Deno.test("omsandBeslut: vänta om det gått under tio minuter", () => {
  const nu = new Date("2026-09-24T12:00:00Z");
  const rad = { skickade: 1, senast_skickad_at: "2026-09-24T11:55:00Z", utgar_at: "2026-09-25T11:55:00Z" };
  assertEquals(omsandBeslut(rad, nu), "vanta");
});

Deno.test("omsandBeslut: vänta när taket på tre är nått", () => {
  const nu = new Date("2026-09-24T12:00:00Z");
  const rad = { skickade: 3, senast_skickad_at: "2026-09-24T10:00:00Z", utgar_at: "2026-09-25T10:00:00Z" };
  assertEquals(omsandBeslut(rad, nu), "vanta");
});

Deno.test("omsandBeslut: skicka om annars", () => {
  const nu = new Date("2026-09-24T12:00:00Z");
  const rad = { skickade: 2, senast_skickad_at: "2026-09-24T11:00:00Z", utgar_at: "2026-09-25T11:00:00Z" };
  assertEquals(omsandBeslut(rad, nu), "omsand");
});
