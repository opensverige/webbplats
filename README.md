# opensverige.se

Källkoden till [opensverige.se](https://opensverige.se) — Sveriges öppna community
för AI-agenter och vibecoding.

Handskriven statisk HTML. Inga ramverk, inga byggberoenden, ingen JavaScript-bundle.
Sidorna byggs av några Python-skript och serveras som filer.

## Struktur

```
site/     sajten som den ligger på webben
tools/    byggskript och kontroller
```

Undersidorna i `site/` genereras från mallar av skripten i `tools/`.
Förstasidan `site/index.html` underhålls för hand.

## Bygga

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

## Live-data

Antalet som är online hämtas från Discords publika widget vid sidladdning.
Ingen nyckel behövs. Går hämtningen inte igenom töms remsan hellre än att visa
en gammal siffra som påstår sig vara aktuell.

## Innehåll

Bloggposter och sidor ligger som HTML i `site/`. Vill du bidra med ett gästinlägg
är det enklast att höra av sig i [Discorden](https://discord.gg/ZbV4qB34um).

## Om logotyperna

Logotyperna i `site/assets/logos/` är respektive företags varumärken och används
enbart för att identifiera verktygen. De ingår inte i något fritt användande.
