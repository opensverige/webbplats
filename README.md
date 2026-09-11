<div align="center">

# opensverige

**Sveriges öppna community för AI-agenter, MCP och vibecoding.**

[![Discord](https://img.shields.io/discord/1466847548864987289?label=Discord&logo=discord&logoColor=white&color=b72c07&style=flat-square)](https://discord.gg/ZbV4qB34um)
[![Sajt](https://img.shields.io/badge/sajt-opensverige.se-b72c07?style=flat-square)](https://opensverige.se)
[![Kod: MIT](https://img.shields.io/badge/kod-MIT-b72c07?style=flat-square)](LICENSE)
[![Innehåll: CC BY 4.0](https://img.shields.io/badge/innehåll-CC%20BY%204.0-b72c07?style=flat-square)](#licens)

</div>

---

Vi är en ideell förening för dig som bygger med AI i Sverige. Agenter, MCP-servrar,
vibecodade helgprojekt — allt räknas. Ingen avgift, inga gatekeepers, ingen
politisk eller kommersiell agenda. Discorden är vardagsrummet, årsmötet bestämmer.

Halvfärdigt är standard. Trasigt är välkommet.

**→ [Gå med i Discorden](https://discord.gg/ZbV4qB34um)** — där sker allt<br>
**→ [Bli medlem i föreningen](https://opensverige.se/bli-medlem)** — gratis, tar en minut, ger dig en röst på årsmötet<br>
**→ [Läs varför vi finns](https://opensverige.se/varfor)**

Föreningen är registrerad hos Skatteverket, org.nr 802557-3422. Stadgarna,
medlemsvillkoren och integritetspolicyn ligger öppet på
[opensverige.se](https://opensverige.se).

---

## Det här repot

Källkoden till [opensverige.se](https://opensverige.se). Handskriven statisk HTML.
Inga ramverk, inga byggberoenden, ingen JavaScript-bundle. Sidorna byggs av några
Python-skript och serveras som filer.

```
site/       sajten som den ligger på webben
tools/      byggskript och kontroller
supabase/   medlemsformulärets backend
```

Undersidorna i `site/` genereras från mallar av skripten i `tools/`. Förstasidan
`site/index.html` underhålls för hand.

### Bygga

Kräver Python 3. Inga paket att installera.

```
python3 tools/verifiera.py        # länkkoll, sitemap mot faktiska filer, JSON-LD
python3 tools/deploy.py draft     # bygg med noindex, för förhandsvisning
python3 tools/deploy.py prod      # bygg indexerbart, för publicering
```

Lägg till `--push` för att deploya till Vercel.

`draft` sätter `noindex` på varje sida och `Disallow: /` i robots.txt, så en
förhandsvisning aldrig kan hamna i sökresultaten. `prod` städar bort de spåren
och vägrar bygga om något av dem är kvar.

### Medlemsformuläret

Anmälan går till en edge-funktion hos Supabase i Stockholm, som skriver till
registret och skickar ett välkomstmejl via Resend. Koden ligger i `supabase/`
tillsammans med schemat och en beskrivning av hur skyddet mot skräpanmälningar
fungerar. Inga nycklar finns i repot.

### Live-data

Antalet som är online hämtas från Discords publika widget vid sidladdning. Ingen
nyckel behövs. Går hämtningen inte igenom töms remsan hellre än att visa en gammal
siffra som påstår sig vara aktuell.

### Om logotyperna

Logotypremsan under Labs-kortet läser tio SVG:er ur `site/assets/logos/`. De
filerna ingår inte i repot — de är tredjepartsmaterial vi inte har rätt att sprida
vidare. Klonar du repot saknas de, och strimman visar filnamnen som alternativtext
i stället för bilder. Sajten fungerar i övrigt som vanligt.

Vill du köra den med logotyper får du lägga egna SVG:er i `site/assets/logos/` med
namnen som står i `site/index.html`. [Simple Icons](https://simpleicons.org) har de
flesta märkena under CC0.

---

## Bidra

Hittar du ett stavfel, en död länk eller något som är fel — öppna en issue eller
skicka en PR direkt. Du behöver inte fråga först.

Vill du skriva ett gästinlägg till bloggen, eller föreslå något större, är det
enklast att höra av sig i [Discorden](https://discord.gg/ZbV4qB34um).

Vi följer organisationens
[uppförandekod](https://github.com/opensverige/.github/blob/main/CODE_OF_CONDUCT.md)
och [riktlinjer för bidrag](https://github.com/opensverige/.github/blob/main/CONTRIBUTING.md).

## Licens

Koden är [MIT](LICENSE) — gör vad du vill med den.

Texterna på sajten, alltså blogginlägg och sidinnehåll, är
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.sv). Återanvänd dem
fritt, men ange opensverige som källa.

Logotyper och varumärken som nämns tillhör sina respektive ägare och omfattas inte
av någon av licenserna.
