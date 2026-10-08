#!/usr/bin/env python3
"""Bygger bloggposterna till statiska HTML-sidor och skriver blogg-index.json.

Körs av deploy.py som första byggsteg. Tre källor:
- MDX från gamla Next-sajten (MDX_DIR, finns bara lokalt hos Baltsar)
- handskrivna HTML-poster (blogg-handskrivna.json)
- Markdown från Redaktionen i innehall/blogg/<slug>.md, som kommer via PR

  python3 tools/migrera-blogg.py             bygg sidorna och blogg-index.json
  python3 tools/migrera-blogg.py --kontroll  granska innehall/blogg utan att skriva (CI)
"""

import html
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MDX_DIR = Path(
    "/Users/baltsar/Documents/Cursor/OPENSVERIGE/Opensverige_2.se/content/blogg"
)
INNEHALL_DIR = ROOT / "innehall" / "blogg"
OUT_DIR = ROOT / "site" / "blogg"
TEMPLATE_SRC = ROOT / "tools" / "mallar" / "artikel.html"
# Poster som skrivs direkt i HTML saknar MDX-källa. De listas här, annars
# försvinner de ur blogg-index.json när det skrivs om vid varje bygge.
HANDSKRIVNA = ROOT / "tools" / "blogg-handskrivna.json"

BASE = "https://opensverige.se"
DISCORD = "https://discord.gg/ZbV4qB34um"

# Delningsbilden. Källan är tools/og/og.html.
OG_BILD = "/assets/og-bygg-skiten.jpg"
OG_ALT = "opensverige: Bygg skiten. En hand håller en röd kräfta."

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

# Redaktionens frontmatter är på svenska. Renderaren läser de engelska nycklarna.
NYCKLAR = {
    "titel": "title",
    "beskrivning": "description",
    "kicker": "kicker",
    "taggar": "tags",
    "forfattare": "author",
    "datum": "date",
}
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
KICKER = re.compile(r"^[^·\n]{2,30} · [^·\n]{2,30}$")
TAGG = re.compile(r"^[a-z0-9åäö]+(?:-[a-z0-9åäö]+)*$")
DATUM = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# Tecken som aldrig får finnas i en länkadress: de kan bryta sig ut ur href.
OSAKER_URL = re.compile(r"[\"'<>\s`]")
# Tabellstil från den handskrivna GPU-posten. Läggs bara på sidor som har en
# tabell, så att de gamla posterna inte ändras.
TABELL_CSS = (
    ".tw{margin-top:18px;overflow-x:auto;-webkit-overflow-scrolling:touch;"
    "border:1px solid var(--hair);border-radius:4px;background:var(--surface)}"
    "table{border-collapse:collapse;width:100%}.tw.wide table{min-width:640px}"
    "th,td{text-align:left;padding:11px 14px;border-bottom:1px solid #f0eeea;"
    "font-size:14.5px;line-height:1.45;vertical-align:top}"
    "th{font-family:var(--mono);font-size:9.5px;letter-spacing:.13em;text-transform:uppercase;"
    "color:var(--faint);font-weight:400;background:#faf9f6;white-space:nowrap}"
    "tr:last-child td{border-bottom:0}td:first-child{font-weight:600;color:var(--ink)}"
)


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
        # Bara http(s), relativa länkar och ankare. Allt annat, som javascript:
        # eller en adress med citattecken, blir ren text: innehåll från
        # Redaktionen kommer via en modell och ska aldrig kunna köra kod här.
        if OSAKER_URL.search(url):
            return etikett
        if url.startswith(("http://", "https://")):
            return f'<a href="{url}" rel="noopener">{etikett}</a>'
        if url.startswith(("/", "#")):
            return f'<a href="{url}">{etikett}</a>'
        return etikett

    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", lank, text)


def _celler(rad):
    return [c.strip() for c in rad.strip().strip("|").split("|")]


def till_html(md, utokad=False):
    """Konverterar brödtext-markdown till artikel-HTML. Returnerar (svarsruta, kropp).

    utokad slår på tabeller och citat. De gamla MDX-posterna renderas utan, så
    att deras sidor blir byte för byte desamma som innan.
    """
    svar = None
    ut = []
    rader = md.split("\n")
    i = 0
    forsta_stycket = True
    blockstart = r"^(#{2,3} |[-*] |\d+\. |```|\||> )" if utokad else r"^(#{2,3} |[-*] |\d+\. |```)"

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

        # Tabell (bara utökad): rubrikrad, avskiljare, rader
        if (
            utokad
            and rad.startswith("|")
            and i + 1 < len(rader)
            and re.match(r"^\|?\s*:?-{3,}", rader[i + 1])
        ):
            huvud = _celler(rad)
            i += 2
            kropp = []
            while i < len(rader) and rader[i].startswith("|"):
                kropp.append(_celler(rader[i]))
                i += 1
            th = "".join(f"<th>{inline(c)}</th>" for c in huvud)
            trs = "".join(
                "<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in kropp
            )
            bred = " wide" if len(huvud) > 3 else ""
            ut.append(
                f'<div class="tw{bred}"><table><thead><tr>{th}</tr></thead>'
                f"<tbody>{trs}</tbody></table></div>"
            )
            continue

        # Citat (bara utökad)
        if utokad and rad.startswith("> "):
            citat = []
            while i < len(rader) and rader[i].startswith("> "):
                citat.append(rader[i][2:].strip())
                i += 1
            ut.append(f"<blockquote><p>{inline(' '.join(citat))}</p></blockquote>")
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
            while i < len(rader) and rader[i].strip() and not re.match(blockstart, rader[i]):
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
    og_bild = BASE + OG_BILD

    # De gamla posterna har handskrivna värden här. Redaktionens poster bär
    # sina egna i frontmatter.
    beskrivning = (
        BESKRIVNINGAR.get(slug)
        or meta.get("description")
        or rensa_text(svar[1] if svar else kropp)
    )
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
                    "url": og_bild,
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
    kicker = KICKERS.get(slug) or meta.get("kicker") or "opensverige"

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
<meta property="og:image" content="{og_bild}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{html.escape(OG_ALT, quote=True)}">
<meta property="og:image:type" content="image/jpeg">
<meta property="article:published_time" content="{iso}">
<meta property="article:author" content="{html.escape(forfattare)}">
{tagg_meta}
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{html.escape(titel, quote=True)}">
<meta name="twitter:description" content="{html.escape(beskrivning, quote=True)}">
<meta name="twitter:image" content="{og_bild}">
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


def las_innehall(fil):
    """Läser en Redaktionen-post och översätter frontmatter till renderarens nycklar."""
    meta, kropp = las_frontmatter(fil.read_text(encoding="utf-8"))
    return {NYCKLAR.get(k, k): v for k, v in meta.items()}, kropp


def granska_innehall(fil, upptagna):
    """Fel i en Redaktionen-post. Tom lista betyder att den går att publicera."""
    slug = fil.stem
    fel = []
    if not SLUG.match(slug):
        fel.append("filnamnet ska vara små bokstäver, siffror och bindestreck")
    if slug in upptagna:
        fel.append("sluggen finns redan på bloggen")
    try:
        meta, kropp = las_innehall(fil)
    except (OSError, ValueError) as exc:
        return [f"{fil.name}: {exc}"]
    titel = meta.get("title")
    if not isinstance(titel, str) or not 5 <= len(titel) <= 70:
        fel.append("titel saknas eller är längre än 70 tecken")
    beskrivning = meta.get("description")
    if not isinstance(beskrivning, str) or not 30 <= len(beskrivning) <= 155:
        fel.append("beskrivning ska vara 30–155 tecken")
    kicker = meta.get("kicker")
    if not isinstance(kicker, str) or not KICKER.match(kicker):
        fel.append("kicker ska se ut som 'Guide · Agenter'")
    taggar = meta.get("tags")
    if not isinstance(taggar, list) or not 1 <= len(taggar) <= 6 or not all(TAGG.match(t) for t in taggar):
        fel.append("taggar ska vara 1–6 ord med små bokstäver, som [guide, mcp]")
    forfattare = meta.get("author")
    if not isinstance(forfattare, str) or not 2 <= len(forfattare) <= 60:
        fel.append("forfattare saknas")
    datum = meta.get("date")
    if not isinstance(datum, str) or not DATUM.match(datum):
        fel.append("datum ska vara ÅÅÅÅ-MM-DD")
    else:
        try:
            date.fromisoformat(datum)
        except ValueError:
            fel.append("datum är inget riktigt datum")
    if not any(re.match(rf"^## {re.escape(r)}\s*$", rad, re.I) for rad in kropp.split("\n") for r in SVARSRUBRIKER):
        fel.append("rubriken '## Kort svar' saknas")
    try:
        till_html(kropp, utokad=True)
    except Exception as exc:  # noqa: BLE001 — allt som fäller renderingen är ett fel i posten
        fel.append(f"går inte att rendera: {exc}")
    return [f"{fil.name}: {f}" for f in fel]


def upptagna_sluggar():
    sluggar = set(KICKERS) | {p.stem for p in MDX_DIR.glob("*.mdx")}
    sluggar |= {p["slug"] for p in json.loads(HANDSKRIVNA.read_text(encoding="utf-8"))}
    return sluggar


def innehallsfiler():
    return sorted(INNEHALL_DIR.glob("*.md")) if INNEHALL_DIR.exists() else []


def kontroll():
    upptagna = upptagna_sluggar()
    fel = [f for fil in innehallsfiler() for f in granska_innehall(fil, upptagna)]
    for rad in fel:
        print(f"FEL {rad}")
    print(f"{len(innehallsfiler())} poster i innehall/blogg granskade, {len(fel)} fel")
    return 1 if fel else 0


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

    upptagna = upptagna_sluggar()
    for fil in innehallsfiler():
        fel = granska_innehall(fil, upptagna)
        if fel:
            raise SystemExit("Redaktionens post klarar inte granskningen:\n" + "\n".join(fel))
        meta, kropp_md = las_innehall(fil)
        svar, kropp = till_html(kropp_md, utokad=True)
        ord_antal = len(rensa_text(kropp).split()) + len(
            rensa_text(svar[1]).split() if svar else []
        )
        sidans_css = css + TABELL_CSS if '<div class="tw' in kropp else css
        sida, info = bygg_sida(fil.stem, meta, svar, kropp, ord_antal, sidans_css)
        (OUT_DIR / f"{fil.stem}.html").write_text(sida, encoding="utf-8")
        index.append(info)
        print(f"  {fil.stem}.html  Redaktionen, {ord_antal} ord, {info['lastid']} min")

    for post in json.loads(HANDSKRIVNA.read_text(encoding="utf-8")):
        if not (OUT_DIR / f"{post['slug']}.html").exists():
            raise FileNotFoundError(f"handskriven post saknar sida: {post['slug']}.html")
        index.append(post)
        print(f"  {post['slug']}.html  handskriven, {post['lastid']} min")

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
    if "--kontroll" in sys.argv[1:]:
        sys.exit(kontroll())
    main()
