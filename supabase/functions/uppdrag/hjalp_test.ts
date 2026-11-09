// deno test --allow-net=jsr.io hjalp_test.ts
import { assertEquals } from "jsr:@std/assert@1";
import {
  arRobot,
  giltigaOmraden,
  enkelWebp,
  giltigtBildnamn,
  lasBild,
  renJpeg,
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

const bytes = (...b: number[]) => new Uint8Array(b);
const dataUrl = (typ: string, b: Uint8Array) => `data:${typ};base64,${btoa(String.fromCharCode(...b))}`;
const riff = (block: string) =>
  new Uint8Array([..."RIFF"].map((c) => c.charCodeAt(0)).concat([40, 0, 0, 0], [..."WEBP"].map((c) => c.charCodeAt(0)), [...block].map((c) => c.charCodeAt(0)), Array(24).fill(0)));
// FFD8, APP0 JFIF med längd 4, sedan SOS.
const jpegRen = bytes(0xff, 0xd8, 0xff, 0xe0, 0x00, 0x04, 0x4a, 0x46, 0xff, 0xda, 0x00, 0x02, 0x00);
const jpegExif = bytes(0xff, 0xd8, 0xff, 0xe1, 0x00, 0x04, 0x45, 0x78, 0xff, 0xda, 0x00, 0x02, 0x00);

Deno.test("bilden: enkel WebP och JPEG utan EXIF går igenom, resten stoppas", () => {
  assertEquals(enkelWebp(riff("VP8 ")), true);
  assertEquals(enkelWebp(riff("VP8L")), true);
  assertEquals(enkelWebp(riff("VP8X")), false);
  assertEquals(renJpeg(jpegRen), true);
  assertEquals(renJpeg(jpegExif), false);
  assertEquals(lasBild(undefined), null);
  assertEquals(lasBild(""), null);
  const ok = lasBild(dataUrl("image/webp", riff("VP8 ")));
  assertEquals(typeof ok === "object" && ok !== null && ok.typ, "image/webp");
  assertEquals(lasBild(dataUrl("image/webp", riff("VP8X"))), "fel");
  assertEquals(lasBild(dataUrl("image/jpeg", jpegExif)), "fel");
  assertEquals(lasBild(dataUrl("image/png", jpegRen)), "fel");
  assertEquals(lasBild(dataUrl("image/jpeg", riff("VP8 "))), "fel");
  assertEquals(lasBild("data:image/webp;base64,@@@"), "fel");
  assertEquals(lasBild(`data:image/webp;base64,${"A".repeat(420000)}`), "fel");
  assertEquals(lasBild(42), "fel");
});

Deno.test("bildens namn är slumpat och har ett känt slut", () => {
  assertEquals(giltigtBildnamn("3f1c2a9e-1b2c-4d5e-8f90-0a1b2c3d4e5f.webp"), true);
  assertEquals(giltigtBildnamn("3f1c2a9e-1b2c-4d5e-8f90-0a1b2c3d4e5f.png"), false);
  assertEquals(giltigtBildnamn("../3f1c2a9e-1b2c-4d5e-8f90-0a1b2c3d4e5f.webp"), false);
});
