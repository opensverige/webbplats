// deno test --allow-net=jsr.io hjalp_test.ts
import { assertEquals } from "jsr:@std/assert@1";
import {
  arRobot,
  giltigaOmraden,
  giltigFigur,
  giltigSlug,
  harPersonnummer,
  httpsAdress,
  lasProfil,
  nySlug,
  redigeraUrl,
} from "./hjalp.ts";

const giltig = {
  namn: "Kim Exempel",
  rubrik: "Bygger agenter och RAG åt mindre bolag",
  lank: "https://www.linkedin.com/in/kim-exempel",
  erbjuder: "uppdrag",
  kommun: "1480",
  distans: true,
  omraden: ["agenter_automation"],
  bolag_namn: "",
  bolag_webbplats: "",
  samtycke: true,
};

Deno.test("personnummer fångas i alla vanliga former", () => {
  for (const s of ["850101-1234", "8501011234", "19850101-1234", "198501011234", "850101+1234", "Firma 556000-0000"]) {
    assertEquals(harPersonnummer(s), true, s);
  }
  for (const s of ["Bygger agenter sedan 2019", "100 000 användare", "tel 070 123"]) {
    assertEquals(harPersonnummer(s), false, s);
  }
});

Deno.test("bara publika https-adresser", () => {
  assertEquals(httpsAdress("https://kim.se"), "https://kim.se/");
  assertEquals(httpsAdress("http://kim.se"), null);
  assertEquals(httpsAdress("javascript:alert(1)"), null);
  assertEquals(httpsAdress("https://user:pass@kim.se"), null);
  assertEquals(httpsAdress("https://localhost"), null);
  assertEquals(httpsAdress("https://kim.se/" + "a".repeat(300)), null);
});

Deno.test("områden: högst tre, i formen id, dubbletter räknas en gång", () => {
  assertEquals(giltigaOmraden(["agenter_automation", "agenter_automation"]), ["agenter_automation"]);
  assertEquals(giltigaOmraden(["a1"]), null);
  assertEquals(giltigaOmraden(["juridik", "robotik", "datorseende", "halsa"]), null);
  assertEquals(giltigaOmraden("juridik"), null);
});

Deno.test("slug av namnet, med slump på slutet", () => {
  assertEquals(nySlug("Åsa Öberg", "3f9a"), "asa-oberg-3f9a");
  assertEquals(nySlug("<<>>", "3f9a"), "medlem-3f9a");
  assertEquals(giltigSlug(nySlug("Kim Exempel Med Ett Mycket Långt Namn Som Fortsätter", "abcd")), true);
  assertEquals(giltigSlug("../hemligt"), false);
});

Deno.test("en giltig profil går igenom", () => {
  const r = lasProfil(giltig);
  assertEquals("falt" in r, true);
  if ("falt" in r) {
    assertEquals(r.falt.lank, "https://www.linkedin.com/in/kim-exempel");
    assertEquals(r.falt.bolag_namn, null);
    assertEquals(r.falt.kommun, "1480");
  }
});

Deno.test("felen pekar ut fälten", () => {
  const r = lasProfil({
    ...giltig,
    namn: "Kim <b>",
    rubrik: "Mitt personnummer är 850101-1234",
    lank: "http://kim.se",
    erbjuder: "allt",
    kommun: "Göteborg",
    distans: "ja",
    samtycke: false,
  });
  assertEquals("fel" in r ? r.fel : [], ["namn", "rubrik", "lank", "erbjuder", "kommun", "distans", "samtycke"]);
});

Deno.test("för lång text avvisas, kortas inte tyst", () => {
  const r = lasProfil({ ...giltig, rubrik: "a".repeat(91) });
  assertEquals("fel" in r ? r.fel : [], ["rubrik"]);
});

Deno.test("länken i mejlet går bara till våra egna adresser", () => {
  const tillatna = ["https://karta.opensverige.se", "http://localhost:4321"];
  assertEquals(redigeraUrl("https://ond.se", "T", tillatna), "https://karta.opensverige.se/uppdrag/redigera#t=T");
  assertEquals(redigeraUrl("http://localhost:4321", "T", tillatna), "http://localhost:4321/uppdrag/redigera#t=T");
});

Deno.test("robotar räknas inte som klick", () => {
  assertEquals(arRobot("Mozilla/5.0 (compatible; Googlebot/2.1)"), true);
  assertEquals(arRobot("facebookexternalhit/1.1"), true);
  assertEquals(arRobot(null), true);
  assertEquals(arRobot("Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) Safari/604.1"), false);
});

Deno.test("figuren är ett id ur kartans lista, och tom betyder att kartan väljer", () => {
  for (const f of ["f01", "f09", "f16"]) assertEquals(giltigFigur(f), true, f);
  for (const f of ["f00", "f17", "f1", "F01", "f01 ", "../f01", "f01.svg", ""]) assertEquals(giltigFigur(f), false, f);
  const utan = lasProfil(giltig);
  assertEquals("falt" in utan && utan.falt.figur, null);
  const med = lasProfil({ ...giltig, figur: "f07" });
  assertEquals("falt" in med && med.falt.figur, "f07");
  const fel = lasProfil({ ...giltig, figur: "f99" });
  assertEquals("fel" in fel && fel.fel, ["figur"]);
  const inteText = lasProfil({ ...giltig, figur: 7 });
  assertEquals("falt" in inteText && inteText.falt.figur, null);
});
