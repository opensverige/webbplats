#!/usr/bin/env python3
"""Bygger 404-sidan.

Vercel serverar site/404.html för statiska bygget. Utan den får besökaren
plattformens egen engelska felsida, vilket är extra synligt just nu när gamla
länkar från den tidigare sajten fortfarande cirkulerar.

Sidan är avsiktligt noindex och står inte i sitemap.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
BASE = "https://opensverige.se"
DISCORD = "https://discord.gg/ZbV4qB34um"

BESKRIVNING = (
    "Sidan du sökte finns inte på opensverige.se. "
    "Hitta vidare till startsidan, bloggen eller showcase."
)

SIDA = f"""<!doctype html><html lang="sv"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Sidan finns inte — opensverige</title>
<meta name="description" content="{BESKRIVNING}">
<meta name="robots" content="noindex,follow">
<meta name="theme-color" content="#fbfaf7">
<meta name="author" content="opensverige">
<meta property="og:type" content="website">
<meta property="og:site_name" content="opensverige">
<meta property="og:locale" content="sv_SE">
<meta property="og:title" content="Sidan finns inte — opensverige">
<meta property="og:description" content="{BESKRIVNING}">
<meta property="og:url" content="{BASE}/404">
<meta property="og:image" content="{BASE}/assets/og-image.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="opensverige — Sveriges öppna community för AI-agenter, MCP och vibecoding">
<meta property="og:image:type" content="image/jpeg">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Sidan finns inte — opensverige">
<meta name="twitter:description" content="{BESKRIVNING}">
<meta name="twitter:image" content="{BASE}/assets/og-image.jpg">
<link rel="icon" href="/favicon/favicon.ico" sizes="32x32">
<link rel="icon" type="image/png" href="/favicon/favicon-96x96.png" sizes="96x96">
<link rel="apple-touch-icon" href="/favicon/apple-touch-icon.png">
<link rel="manifest" href="/favicon/site.webmanifest">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&display=swap">
<script type="application/ld+json">
{{"@context":"https://schema.org","@type":"WebPage","name":"Sidan finns inte",
"description":"{BESKRIVNING}","inLanguage":"sv-SE",
"isPartOf":{{"@id":"{BASE}/#website"}}}}
</script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
:root{{--ink:#151515;--body:#2b2724;--bg:#fbfaf7;--hair:#e4e2dc;--accent:#b72c07;
  --muted:#5b5651;--serif:'Instrument Serif',Georgia,serif;
  --mono:ui-monospace,SFMono-Regular,Menlo,monospace;
  --snap:cubic-bezier(.16,1,.3,1);--t:150ms var(--snap)}}
html{{-webkit-text-size-adjust:100%}}
body{{background:var(--bg);color:var(--ink);
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;
  -webkit-font-smoothing:antialiased}}
a{{color:inherit}}
.top{{height:52px;display:flex;align-items:center;padding:0 20px;
  border-bottom:1px solid var(--hair)}}
.back{{display:flex;align-items:center;gap:7px;font-family:var(--mono);font-size:11px;
  letter-spacing:.1em;text-transform:uppercase;color:var(--muted);text-decoration:none;
  transition:color var(--t)}}
.back:hover{{color:var(--accent)}}
.wrap{{max-width:672px;margin:0 auto;padding:72px 20px 40px}}
.kod{{font-family:var(--mono);font-size:11px;letter-spacing:.14em;text-transform:uppercase;
  color:var(--muted)}}
h1{{font-family:var(--serif);font-weight:400;font-size:46px;line-height:1.04;
  letter-spacing:-.015em;margin-top:16px}}
.txt{{font-size:17.5px;line-height:1.68;color:var(--body);margin-top:20px;max-width:44ch}}
.ut{{display:flex;flex-wrap:wrap;gap:10px;margin-top:34px}}
.ut a{{display:inline-flex;align-items:center;gap:7px;padding:9px 15px;
  border:1px solid var(--hair);border-radius:9px;font-size:14px;text-decoration:none;
  background:#fff;transition:border-color var(--t),color var(--t),transform var(--t)}}
.ut a:hover{{border-color:var(--accent);color:var(--accent);transform:translateY(-1px)}}
.ut a:focus-visible{{outline:2px solid var(--accent);outline-offset:2px}}
.vh{{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);
  white-space:nowrap}}
@media(min-width:640px){{
  .top{{padding:0 40px}} .wrap{{padding:104px 40px 56px}} h1{{font-size:62px}}
  .txt{{font-size:19px;line-height:1.72}}
}}
</style>
</head>
<body>
<div class="top"><a class="back" href="/">← opensverige</a></div>
<main class="wrap">
  <p class="kod">Fel 404</p>
  <h1>Sidan finns inte.</h1>
  <p class="txt">Länken kan vara gammal, eller så blev det ett stavfel.
  Ingen fara — allt annat ligger kvar.</p>
  <nav class="ut" aria-label="Hitta vidare">
    <a href="/">Startsidan <span aria-hidden="true">→</span></a>
    <a href="/blogg">Blogg <span aria-hidden="true">→</span></a>
    <a href="/showcase">Showcase <span aria-hidden="true">→</span></a>
    <a href="/bli-medlem">Bli medlem <span aria-hidden="true">→</span></a>
    <a href="{DISCORD}" target="_blank" rel="noopener">Discord
      <span aria-hidden="true">↗</span><span class="vh">, öppnas i ny flik</span></a>
  </nav>
</main>
</body></html>
"""


def main() -> None:
    (SITE / "404.html").write_text(SIDA, encoding="utf-8")
    print("404-sidan byggd")


if __name__ == "__main__":
    main()
