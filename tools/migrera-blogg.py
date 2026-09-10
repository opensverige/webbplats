#!/usr/bin/env python3
"""Migrerar bloggposter från MDX (gamla Next-sajten) till statiska HTML-sidor.

Engångsverktyg. Efter körning är HTML-filerna källan — sajten har inget byggsteg.
Körs: python3 tools/migrera-blogg.py
"""

import html
import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MDX_DIR = Path(
    "/Users/baltsar/Documents/Cursor/OPENSVERIGE/Opensverige_2.se/content/blogg"
)
OUT_DIR = ROOT / "site" / "blogg"
TEMPLATE_SRC = ROOT / "tools" / "mallar" / "artikel.html"

BASE = "https://opensverige.se"
DISCORD = "https://discord.gg/ZbV4qB34um"

MANADER = "jan feb mar apr maj jun jul aug sep okt nov dec".split()

# Rubriker som ska renderas som AEO-svarsruta istället för vanlig sektion
SVARSRUBRIKER = {"kort svar", "den korta versionen"}

KICKERS = {
    "mcp-vs-rest": "MCP · Arkitektur",
    "vad-ar-ai-agenter": "Intro · Agenter",
    "fortnox-agent-guide": "Guide · Fortnox",
    "gollum-testet": "Community · Verktyg",
    "bygg-spel-med-ai": "Guide · Hackathon",
}

# Handskrivna meta descriptions. Autoutdrag ur brödtexten ger oläsbara resultat
# när posten börjar med en rubrik eller ett kodblock.
BESKRIVNINGAR = {
    "mcp-vs-rest": "REST är för human-to-machine. MCP är för agent-to-tool. När du ska använda vilket — och hur du lägger ett MCP-lager ovanpå ett befintligt REST-API.",
    "vad-ar-ai-agenter": "En AI-agent planerar, beslutar och utför — en chatbot svarar bara. Så skiljer de sig, vad agenter kräver och varför multi-agent-system ändrar allt.",
    "fortnox-agent-guide": "Steg för steg: koppla Fortnox till en AI-agent med OpenClaw och fortnox-skill. Installation, API-nycklar och första frågan om obetalda fakturor.",
    "gollum-testet": "Shippar du eller hoardar du idéer? Två axlar, fyra arketyper och ett test på tio frågor som visar vilken typ av AI-builder du faktiskt är.",
    "bygg-spel-med-ai": "Bygg ett spelbart spel på en vecka med AI som medbyggare. Verktygslåda, arbetsflöde och checklista för hackathonet — Kaplay, Godot via MCP och vibecoding.",
}


def las_frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        raise ValueError("saknar frontmatter")
    meta = {}
    for rad in m.group(1).splitlines():
        if ":" not in rad:
            continue
        nyckel, varde = rad.split(":", 1)
        varde = varde.strip()
        if varde.startswith("["):
            meta[nyckel.strip()] = [
                v.strip().strip("'\"") for v in varde.strip("[]").split(",") if v.strip()
            ]
        else:
            meta[nyckel.strip()] = varde.strip("'\"")
    return meta, m.group(2).strip()


def inline(text):
    """Konverterar inline-markdown. Escapar först, injicerar taggar sen."""
    text = html.escape(text, quote=False)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", text)

    def lank(m):
        etikett, url = m.group(1), m.group(2)
        if url.startswith("http"):
            return f'<a href="{url}" rel="noopener">{etikett}</a>'
        return f'<a href="{url}">{etikett}</a>'

    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", lank, text)


def till_html(md):
    """Konverterar brödtext-markdown till artikel-HTML. Returnerar (svarsruta, kropp)."""
    svar = None
    ut = []
    rader = md.split("\n")
    i = 0
    forsta_stycket = True

    while i < len(rader):
        rad = rader[i]

        # Kodblock
        if rad.startswith("```"):
            i += 1
            kod = []
            while i < len(rader) and not rader[i].startswith("```"):
                kod.append(rader[i])
                i += 1
            i += 1
            ut.append(
                "<pre><code>" + html.escape("\n".join(kod), quote=False) + "</code></pre>"
            )
            continue

        # Rubriker
        if rad.startswith("### "):
            ut.append(f"<h3>{inline(rad[4:].strip())}</h3>")
            i += 1
            continue
        if rad.startswith("## "):
            rubrik = rad[3:].strip()
            if rubrik.lower() in SVARSRUBRIKER and svar is None:
                # Nästa icke-tomma stycke blir svarsrutan
                i += 1
                while i < len(rader) and not rader[i].strip():
                    i += 1
                svar = (rubrik, inline(rader[i].strip()) if i < len(rader) else "")
                i += 1
                continue
            ut.append(f"<h2>{inline(rubrik)}</h2>")
            i += 1
            continue

        # Listor
        if re.match(r"^[-*] ", rad):
            poster = []
            while i < len(rader) and re.match(r"^[-*] ", rader[i]):
                poster.append(inline(rader[i][2:].strip()))
                i += 1
            ut.append("<ul>" + "".join(f"<li>{p}</li>" for p in poster) + "</ul>")
            continue
        if re.match(r"^\d+\. ", rad):
            poster = []
            while i < len(rader) and re.match(r"^\d+\. ", rader[i]):
                poster.append(inline(re.sub(r"^\d+\.\s*", "", rader[i]).strip()))
                i += 1
            ut.append("<ol>" + "".join(f"<li>{p}</li>" for p in poster) + "</ol>")
            continue

        # Stycke
        if rad.strip():
            block = []
            while i < len(rader) and rader[i].strip() and not re.match(
                r"^(#{2,3} |[-*] |\d+\. |```)", rader[i]
            ):
                block.append(rader[i].strip())
                i += 1
            klass = ' class="lead"' if forsta_stycket and not svar else ""
            forsta_stycket = False
            ut.append(f"<p{klass}>{inline(' '.join(block))}</p>")
            continue

        i += 1

    return svar, "\n  ".join(ut)


def rensa_text(h):
    """Plockar ut ren text ur HTML för meta description."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", h)).strip()


def hamta_css():
    mall = TEMPLATE_SRC.read_text(encoding="utf-8")
    return re.search(r"<style>(.*?)</style>", mall, re.S).group(1)


def bygg_sida(slug, meta, svar, kropp, ord_antal, css):
    titel = meta["title"]
    forfattare = meta.get("author", "opensverige")
    taggar = meta.get("tags", [])
    iso = meta["date"]
    y, m, d = (int(x) for x in iso.split("-"))
    datum_kort = f"{d} {MANADER[m - 1]}"
    datum_lang = f"{d} {MANADER[m - 1]} {y}"
    lastid = max(1, round(ord_antal / 200))
    url = f"{BASE}/blogg/{slug}"

    beskrivning = BESKRIVNINGAR.get(slug) or rensa_text(svar[1] if svar else kropp)
    if len(beskrivning) > 160:
        beskrivning = beskrivning[:157].rsplit(" ", 1)[0] + "…"

    graf = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "BlogPosting",
                "@id": f"{url}#post",
                "headline": titel,
                "description": beskrivning,
                "url": url,
                "datePublished": iso,
                "dateModified": iso,
                "inLanguage": "sv-SE",
                "wordCount": ord_antal,
                "keywords": ", ".join(taggar),
                "author": {"@type": "Person", "name": forfattare},
                "publisher": {"@id": f"{BASE}/#organization"},
                "isPartOf": {"@id": f"{BASE}/blogg#blog"},
                "mainEntityOfPage": {"@type": "WebPage", "@id": url},
                "image": {
                    "@type": "ImageObject",
                    "url": f"{BASE}/assets/og-image.jpg",
                    "width": 1200,
                    "height": 630,
                },
            },
            {
                "@type": "BreadcrumbList",
                "@id": f"{url}#breadcrumb",
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": 1,
                        "name": "Start",
                        "item": f"{BASE}/",
                    },
                    {
                        "@type": "ListItem",
                        "position": 2,
                        "name": "Blogg",
                        "item": f"{BASE}/blogg",
                    },
                    {"@type": "ListItem", "position": 3, "name": titel},
                ],
            },
        ],
    }

    svarsruta = ""
    if svar:
        svarsruta = (
            f'\n  <div class="answer">\n'
            f'    <div class="l">{html.escape(svar[0])}</div>\n'
            f"    <p>{svar[1]}</p>\n"
            f"  </div>\n"
        )

    tagg_meta = "\n".join(
        f'<meta property="article:tag" content="{html.escape(t)}">' for t in taggar
    )
    initialer = forfattare[:2].lower()
    kicker = KICKERS.get(slug, "opensverige")

    return f"""<!doctype html><html lang="sv" class="js"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{html.escape(titel)} | opensverige</title>
<meta name="description" content="{html.escape(beskrivning, quote=True)}">
<link rel="canonical" href="{url}">
<meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1">
<meta name="theme-color" content="#fbfaf7">
<meta name="author" content="{html.escape(forfattare)}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="opensverige">
<meta property="og:locale" content="sv_SE">
<meta property="og:title" content="{html.escape(titel, quote=True)}">
<meta property="og:description" content="{html.escape(beskrivning, quote=True)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{BASE}/assets/og-image.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="article:published_time" content="{iso}">
<meta property="article:author" content="{html.escape(forfattare)}">
{tagg_meta}
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{html.escape(titel, quote=True)}">
<meta name="twitter:description" content="{html.escape(beskrivning, quote=True)}">
<meta name="twitter:image" content="{BASE}/assets/og-image.jpg">
<link rel="icon" href="/favicon/favicon.ico" sizes="32x32">
<link rel="icon" type="image/png" href="/favicon/favicon-96x96.png" sizes="96x96">
<link rel="apple-touch-icon" href="/favicon/apple-touch-icon.png">
<link rel="manifest" href="/favicon/site.webmanifest">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Familjen+Grotesk:ital,wght@0,400..700;1,400..700&family=JetBrains+Mono:wght@400;500&family=Instrument+Serif:ital@0;1&display=swap" rel="stylesheet">
<style>{css}</style>
<script type="application/ld+json">
{json.dumps(graf, ensure_ascii=False, indent=2)}
</script>
</head><body>
<div class="prog" id="prog"></div>

<header class="top">
  <a class="back" href="/blogg">← Blogg</a>
  <span class="rt">{lastid} min</span>
</header>

<article class="prose">
  <div class="kicker">{html.escape(kicker)}</div>
  <h1>{html.escape(titel)}</h1>
  <div class="byline"><span>{html.escape(forfattare)}</span><span class="d">·</span><span>{datum_lang}</span><span class="d">·</span><span>{lastid} min</span></div>
{svarsruta}
  {kropp}

  <hr>
  <div class="author"><div class="av">{html.escape(initialer)}</div><div><div class="n">{html.escape(forfattare)}</div><div class="r">opensverige · publicerat {datum_lang}</div></div></div>
</article>

<div class="mcta" id="mcta">
  <div class="n">Frågor? <b>600+</b> builders i tråden</div>
  <a class="dbtn" href="{DISCORD}" rel="noopener"><svg viewBox="0 0 127 96"><path d="M107.7 8.07A105.15 105.15 0 0 0 81.47 0a72.06 72.06 0 0 0-3.36 6.83 97.68 97.68 0 0 0-29.11 0A72.37 72.37 0 0 0 45.64 0a105.89 105.89 0 0 0-26.25 8.09C2.79 32.65-1.71 56.6.54 80.21a105.73 105.73 0 0 0 32.17 16.15 77.7 77.7 0 0 0 6.89-11.11 68.42 68.42 0 0 1-10.85-5.18c.91-.66 1.8-1.34 2.66-2a75.57 75.57 0 0 0 64.32 0c.87.71 1.76 1.39 2.66 2a68.68 68.68 0 0 1-10.87 5.19 77 77 0 0 0 6.89 11.1 105.25 105.25 0 0 0 32.19-16.14c2.64-27.38-4.51-51.11-18.9-72.15ZM42.45 65.69C36.18 65.69 31 60 31 53s5-12.74 11.43-12.74S54 46 53.89 53s-5.05 12.69-11.44 12.69Zm42.24 0C78.41 65.69 73.25 60 73.25 53s5-12.74 11.44-12.74S96.23 46 96.12 53s-5.04 12.69-11.43 12.69Z"/></svg>Fråga</a>
</div>

<script>
const prog=document.getElementById('prog'), mcta=document.getElementById('mcta');
let t=false;
addEventListener('scroll',()=>{{if(t)return;t=true;requestAnimationFrame(()=>{{
  const y=scrollY,max=document.body.scrollHeight-innerHeight;
  prog.style.width=Math.min(100,(y/max)*100)+'%';
  mcta.classList.toggle('show', y>300);
  t=false;}});}},{{passive:true}});
</script>
</body></html>
""", {
        "slug": slug,
        "titel": titel,
        "datum": iso,
        "datum_kort": datum_kort,
        "lastid": lastid,
        "beskrivning": beskrivning,
        "taggar": taggar,
        "forfattare": forfattare,
    }


def main():
    css = hamta_css()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    index = []

    for mdx in sorted(MDX_DIR.glob("*.mdx")):
        slug = mdx.stem
        meta, kropp_md = las_frontmatter(mdx.read_text(encoding="utf-8"))
        svar, kropp = till_html(kropp_md)
        ord_antal = len(rensa_text(kropp).split()) + len(
            rensa_text(svar[1]).split() if svar else []
        )
        sida, info = bygg_sida(slug, meta, svar, kropp, ord_antal, css)
        (OUT_DIR / f"{slug}.html").write_text(sida, encoding="utf-8")
        index.append(info)
        print(f"  {slug}.html  {ord_antal} ord, {info['lastid']} min, svarsruta={bool(svar)}")

    (ROOT / "tools" / "blogg-index.json").write_text(
        json.dumps(
            sorted(index, key=lambda p: p["datum"], reverse=True),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\n{len(index)} poster skrivna till {OUT_DIR}")


if __name__ == "__main__":
    main()
