#!/usr/bin/env python3
"""Bygger innehållssidorna som portats från den gamla Next-sajten.

Engångsverktyg, som migrera-blogg.py. Efter körning är HTML-filerna källan.
Sidor: /varfor, /integritet, /blogg, /showcase
"""

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
BASE = "https://opensverige.se"
DISCORD = "https://discord.gg/ZbV4qB34um"

DISCORD_SVG = (
    '<svg viewBox="0 0 127 96"><path d="M107.7 8.07A105.15 105.15 0 0 0 81.47 0a72.06 '
    "72.06 0 0 0-3.36 6.83 97.68 97.68 0 0 0-29.11 0A72.37 72.37 0 0 0 45.64 0a105.89 "
    "105.89 0 0 0-26.25 8.09C2.79 32.65-1.71 56.6.54 80.21a105.73 105.73 0 0 0 32.17 "
    "16.15 77.7 77.7 0 0 0 6.89-11.11 68.42 68.42 0 0 1-10.85-5.18c.91-.66 1.8-1.34 "
    "2.66-2a75.57 75.57 0 0 0 64.32 0c.87.71 1.76 1.39 2.66 2a68.68 68.68 0 0 "
    "1-10.87 5.19 77 77 0 0 0 6.89 11.1 105.25 105.25 0 0 0 "
    "32.19-16.14c2.64-27.38-4.51-51.11-18.9-72.15ZM42.45 65.69C36.18 65.69 31 60 31 "
    "53s5-12.74 11.43-12.74S54 46 53.89 53s-5.05 12.69-11.44 12.69Zm42.24 0C78.41 "
    "65.69 73.25 60 73.25 53s5-12.74 11.44-12.74S96.23 46 96.12 53s-5.04 12.69-11.43 "
    '12.69Z"/></svg>'
)

MANADER = "jan feb mar apr maj jun jul aug sep okt nov dec".split()

EXTRA_CSS = """
/* listningssidor */
.lista{max-width:760px;margin:0 auto;padding:30px var(--gut) 90px}
@media(min-width:860px){.lista{padding:54px var(--gut) 110px}}
.lista h1{font-size:clamp(30px,7.4vw,46px);font-weight:600;letter-spacing:-.04em;line-height:1.06}
.lista .intro{font-size:18px;line-height:1.55;color:var(--muted);margin-top:16px;max-width:60ch}
@media(min-width:640px){.lista .intro{font-size:19.5px}}
.rad{display:block;padding:20px 0;border-bottom:1px solid var(--hair);text-decoration:none;transition:padding-left var(--t)}
.rad:first-of-type{border-top:1px solid var(--hair)}
.rad:hover{padding-left:8px}
.rad .rt{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}
.rad .rn{font-size:19px;font-weight:600;letter-spacing:-.025em;color:var(--ink)}
@media(min-width:640px){.rad .rn{font-size:21px}}
.rad:hover .rn{color:var(--accent)}
.rad .rd{display:block;font-size:16px;line-height:1.55;color:var(--muted);margin-top:7px;max-width:62ch}
.rad .rm{display:block;font-family:var(--mono);font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--faint);margin-top:9px}
.pill{display:inline-flex;align-items:center;height:19px;padding:0 7px;border-radius:2px;background:#f1efeb;
  font-family:var(--mono);font-size:9.5px;letter-spacing:.11em;text-transform:uppercase;color:var(--muted)}
.pill.live{background:rgba(59,165,93,.13);color:#2c7a45}
.pill.oss{background:rgba(183,44,7,.09);color:var(--accent)}
.pill.wip{background:rgba(180,140,20,.14);color:#7a5c10}
/* projektkort med djup */
.proj{padding:22px 0;border-bottom:1px solid var(--hair)}
.proj:first-of-type{border-top:1px solid var(--hair)}
.proj .pn{display:flex;align-items:baseline;gap:9px;flex-wrap:wrap;font-size:19px;font-weight:600;letter-spacing:-.025em}
@media(min-width:640px){.proj .pn{font-size:21px}}
.proj .pn a{text-decoration:none;transition:color var(--t)}
.proj .pn a:hover{color:var(--accent)}
.proj .pt{font-size:16.5px;line-height:1.55;color:var(--muted);margin-top:7px;max-width:62ch}
.proj .pd{margin-top:13px;display:grid;gap:3px}
.proj .pd dt{font-family:var(--mono);font-size:9.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--faint);margin-top:8px}
.proj .pd dd{font-size:15.5px;line-height:1.55;color:var(--body);max-width:64ch}
.proj .pm{font-family:var(--mono);font-size:10.5px;letter-spacing:.09em;text-transform:uppercase;color:var(--faint);margin-top:13px}
/* hackathon-arkiv */
.arkiv{margin:22px 0 0;padding:15px 17px;border:1px solid var(--hair);border-left:2px solid var(--faint);
  border-radius:2px;background:#f6f4f0}
.arkiv p{font-size:15.5px;line-height:1.5;color:var(--muted);margin:0}
.fakta{display:grid;gap:0;margin-top:30px;border-top:1px solid var(--hair)}
.fakta div{display:flex;gap:14px;padding:11px 0;border-bottom:1px solid var(--hair);font-size:16px}
.fakta dt,.fakta .fl{font-family:var(--mono);font-size:10px;letter-spacing:.13em;text-transform:uppercase;
  color:var(--faint);min-width:88px;padding-top:3px}
.fakta .fv{color:var(--ink)}
.krit{display:flex;gap:12px;padding:13px 0;border-bottom:1px solid var(--hair)}
.krit .kn{font-family:var(--mono);font-size:11px;color:var(--accent);min-width:26px;padding-top:2px}
.krit .kt{font-size:16.5px;font-weight:600;letter-spacing:-.02em}
.krit .kb{font-size:15.5px;line-height:1.55;color:var(--muted);margin-top:4px}
.krit .kv{margin-left:auto;font-family:var(--mono);font-size:11px;color:var(--faint);white-space:nowrap;padding-top:3px}
.res{margin-top:9px}
.res .rg{font-family:var(--mono);font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);margin-top:22px}
.res .ri{padding:10px 0;border-bottom:1px solid var(--hair)}
.res .ri a{font-size:16px;font-weight:600;text-decoration:none}
.res .ri a:hover{color:var(--accent)}
.res .ri span{display:block;font-size:15px;line-height:1.5;color:var(--muted);margin-top:3px}
.grupp{margin-top:44px}
.grupp .gl{font-family:var(--mono);font-size:10.5px;letter-spacing:.16em;text-transform:uppercase;color:var(--accent);margin-bottom:6px}
.slutcta{margin-top:52px;padding-top:30px;border-top:1px solid var(--hair);display:flex;gap:12px;flex-wrap:wrap;align-items:center}
.slutcta .st{font-size:16.5px;color:var(--muted);flex:1;min-width:190px}
.dbtn.dc{background:var(--discord);color:#fff}
.dbtn.dc:hover{background:#4752c4}
.dbtn.ghost{background:transparent;color:var(--ink);border:1px solid var(--hair)}
.dbtn.ghost:hover{border-color:var(--ink);background:transparent}
/* prosasidor */
.prose h3{font-size:18px;font-weight:600;letter-spacing:-.02em;margin-top:32px}
@media(min-width:640px){.prose h3{font-size:20px}}
.prose ol{list-style:none;margin-top:18px;counter-reset:o}
.prose ol li{counter-increment:o;padding-left:26px}
.prose ol li::before{content:counter(o) ".";position:absolute;left:0;top:0;width:auto;height:auto;background:none;
  font-family:var(--mono);font-size:12px;color:var(--faint)}
.callout{margin:26px 0 0;padding:18px;border:1px solid var(--hair);border-left:2px solid var(--accent);border-radius:2px;background:#fdfcfa}
.callout p{margin:0;font-size:17px;line-height:1.55;color:var(--ink)}
.punch{font-family:var(--serif);font-size:25px;line-height:1.3;margin-top:30px}
@media(min-width:640px){.punch{font-size:29px}}
.stats{display:flex;gap:28px;margin-top:30px;padding:22px 0;border-top:1px solid var(--hair);border-bottom:1px solid var(--hair)}
.stats div{display:flex;flex-direction:column;gap:3px}
.stats .v{font-size:26px;font-weight:600;letter-spacing:-.03em}
.stats .l{font-family:var(--mono);font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:var(--faint)}
"""


def las_artikel_css():
    mall = (ROOT / "tools" / "mallar" / "artikel.html").read_text(encoding="utf-8")
    return re.search(r"<style>(.*?)</style>", mall, re.S).group(1)


def head(cfg, css, jsonld, og_typ="website"):
    url = BASE + cfg["sokvag"]
    b = html.escape(cfg["beskrivning"], quote=True)
    t = html.escape(cfg["titel"])
    ogt = html.escape(cfg.get("og_titel", cfg["titel"]), quote=True)
    ld = json.dumps(jsonld, ensure_ascii=False, indent=2)
    return f"""<!doctype html><html lang="sv" class="js"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{t}</title>
<meta name="description" content="{b}">
<link rel="canonical" href="{url}">
<meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1">
<meta name="theme-color" content="#fbfaf7">
<meta name="author" content="opensverige">
<meta property="og:type" content="{og_typ}">
<meta property="og:site_name" content="opensverige">
<meta property="og:locale" content="sv_SE">
<meta property="og:title" content="{ogt}">
<meta property="og:description" content="{b}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{BASE}/assets/og-image.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{ogt}">
<meta name="twitter:description" content="{b}">
<meta name="twitter:image" content="{BASE}/assets/og-image.jpg">
<link rel="icon" href="/favicon/favicon.ico" sizes="32x32">
<link rel="icon" type="image/png" href="/favicon/favicon-96x96.png" sizes="96x96">
<link rel="apple-touch-icon" href="/favicon/apple-touch-icon.png">
<link rel="manifest" href="/favicon/site.webmanifest">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Familjen+Grotesk:ital,wght@0,400..700;1,400..700&family=JetBrains+Mono:wght@400;500&family=Instrument+Serif:ital@0;1&display=swap" rel="stylesheet">
<style>{css}{EXTRA_CSS}</style>
<script type="application/ld+json">
{ld}
</script>
</head><body>"""


def brodsmula(namn, sokvag):
    return {
        "@type": "BreadcrumbList",
        "@id": f"{BASE}{sokvag}#breadcrumb",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Start", "item": f"{BASE}/"},
            {"@type": "ListItem", "position": 2, "name": namn, "item": f"{BASE}{sokvag}"},
        ],
    }


def toppbar(tillbaka="/", etikett="opensverige", hoger=""):
    return f"""
<header class="top">
  <a class="back" href="{tillbaka}">← {etikett}</a>
  <span class="rt">{hoger}</span>
</header>
"""


def discord_cta(text):
    return f"""
<div class="slutcta">
  <p class="st">{text}</p>
  <a class="dbtn dc" href="{DISCORD}" rel="noopener">{DISCORD_SVG}Gå med i Discord</a>
</div>
"""


# ---------------------------------------------------------------- showcase

PROJEKT = [
    {
        "namn": "Agent Readiness Scanner",
        "slug": "agent-readiness-scanner",
        "url": "https://agent.opensverige.se",
        "beskrivning": "Skannar din sajt och visar vad AI-agenter ser — och vad som blockerar dem. 13 kontroller, 30 sekunder.",
        "taggar": ["scanner", "agentredo", "sajtanalys", "seo"],
        "status": "live",
        "kategori": "DeveloperApplication",
    },
    {
        "namn": "AI-Infra",
        "slug": "ai-infra",
        "url": "https://infra.opensverige.se",
        "beskrivning": "Jämför svenska och europeiska AI-leverantörer på datasuveränitet, modeller, pris och GDPR. Varje uppgift källbelagd och verifierad.",
        "taggar": ["jämförelse", "ai-infra", "datasuveränitet", "gdpr"],
        "status": "live",
        "kategori": "BusinessApplication",
    },
    {
        "namn": "grunden.ai",
        "slug": "grunden-ai",
        "url": "https://grunden.ai",
        "beskrivning": "Svensk AI-infrastruktur med OpenAI-kompatibelt API och EU-jurisdiktion. Startade i opensverige — nu i drift.",
        "taggar": ["ai-infra", "llm-api", "datasuveränitet", "eu"],
        "status": "live",
        "kategori": "DeveloperApplication",
    },
    {
        "namn": "Agent Arena",
        "slug": "agent-arena",
        "url": "https://battle.opensverige.se",
        "beskrivning": "AI-agenter tävlar mot varandra i schack, logik och Minesweeper. Realtidsranking — släpp in din agent och klättra.",
        "taggar": ["arena", "multi-agent", "leaderboard", "pvp"],
        "status": "live",
        "kategori": "GameApplication",
    },
    {
        "namn": "KAMMAREN",
        "slug": "kammaren",
        "url": "https://kammaren.nu",
        "beskrivning": "Sovereign AI för svenska AB-ägare. Beräknar optimal lön, utdelning och 3:12-strategi. Dina siffror på din maskin.",
        "taggar": ["skatteoptimering", "3:12", "sovereign-ai"],
        "status": "live",
        "kategori": "FinanceApplication",
    },
    {
        "namn": "FAVER",
        "slug": "faver",
        "url": "https://faver-one.vercel.app/map",
        "beskrivning": "Hitta de bästa rabatterna i matbutikerna runt dig i realtid. Sätt på GPS eller droppa en pin, skanna och se alla rabatter.",
        "taggar": ["matpris", "gps", "realtime", "butik"],
        "status": "live",
        "kategori": "LifestyleApplication",
    },
    {
        "namn": "LunarAIstorm",
        "slug": "lunaraistorm",
        "url": "https://lunaraistorm.se",
        "beskrivning": "Socialt nätverk för AI-agenter, inspirerat av LunarStorm. Agenter möts, klottrar i gästböcker och diskuterar dygnet runt.",
        "taggar": ["openclaw", "multi-agent", "open source"],
        "status": "live",
        "kategori": "SocialNetworkingApplication",
    },
    {
        "namn": "fortnox-skill",
        "slug": "fortnox-skill",
        "url": "https://github.com/opensverige/fortnox-skill",
        "beskrivning": "OpenClaw-skill som kopplar en AI-agent direkt till Fortnox. Fakturor, kunder och bokföring via chatt.",
        "taggar": ["openclaw", "fortnox", "mcp"],
        "status": "oss",
        "kategori": "kod",
    },
    {
        "namn": "Gollum-testet",
        "slug": "gollum-testet",
        "url": "/gollum",
        "beskrivning": "Är du builder eller hoardar du idéer? Tio frågor, två axlar, fyra arketyper. 90 sekunder.",
        "taggar": ["quiz", "community"],
        "status": "live",
        "kategori": "WebApplication",
    },
]

STATUS_ETIKETT = {"live": "live", "oss": "öppen källkod", "wip": "byggs nu"}


def las_lab():
    """Projektdjup från gamla /lab, nycklat på slug."""
    rader = json.loads((ROOT / "tools" / "lab-data.json").read_text(encoding="utf-8"))
    return {r["slug"]: r for r in rader}


def projektschema(p):
    if p["kategori"] == "kod":
        return {
            "@type": "SoftwareSourceCode",
            "name": p["namn"],
            "description": p["beskrivning"],
            "url": p["url"],
            "codeRepository": p["url"],
            "keywords": ", ".join(p["taggar"]),
        }
    return {
        "@type": "SoftwareApplication",
        "name": p["namn"],
        "description": p["beskrivning"],
        "url": p["url"] if p["url"].startswith("http") else BASE + p["url"],
        "applicationCategory": p["kategori"],
        "operatingSystem": "Web",
        "inLanguage": "sv-SE",
        "keywords": ", ".join(p["taggar"]),
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "SEK"},
    }


def bygg_showcase(css):
    lab = las_lab()
    idrift = []
    ilabbet = []

    # Projekt i drift, berikade med djup från labbet där det finns
    for pr in PROJEKT:
        d = dict(pr)
        l = lab.get(pr["slug"])
        if l:
            d["avsnitt"] = l["description"]
            d["stack"] = next(
                (m["value"] for m in l["meta"] if m["label"] == "Stack" and isinstance(m["value"], str)),
                None,
            )
        idrift.append(d)

    # Projekt som bara fanns i labbet
    kanda = {pr["slug"] for pr in PROJEKT}
    for slug, l in lab.items():
        if slug in kanda:
            continue
        primar = next((x for x in l["links"] if x.get("primary")), l["links"][0] if l["links"] else None)
        ilabbet.append({
            "namn": l["title"],
            "slug": slug,
            "url": primar["href"] if primar else "",
            "beskrivning": l["tagline"],
            "taggar": [x.lower() for x in l["tags"]],
            "status": "wip",
            "kategori": "kod",
            "avsnitt": l["description"],
            "stack": next(
                (m["value"] for m in l["meta"] if m["label"] == "Stack" and isinstance(m["value"], str)),
                None,
            ),
        })
    ilabbet.sort(key=lambda x: x["namn"].lower())

    alla = idrift + ilabbet
    cfg = {
        "sokvag": "/showcase",
        "titel": "Showcase — projekt byggda av opensverige-communityn",
        "og_titel": "opensverige showcase — projekt byggda av communityn",
        "beskrivning": (
            "AI-agenter, MCP-servrar och verktyg byggda av opensverige-communityn. "
            f"{len(alla)} öppna projekt från svenska builders i Stockholm, Göteborg och Malmö."
        ),
    }

    jsonld = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "CollectionPage",
                "@id": f"{BASE}/showcase#collection",
                "name": "opensverige showcase",
                "description": cfg["beskrivning"],
                "url": f"{BASE}/showcase",
                "inLanguage": "sv-SE",
                "isPartOf": {"@id": f"{BASE}/#website"},
                "about": {"@id": f"{BASE}/#organization"},
                "mainEntity": {
                    "@type": "ItemList",
                    "numberOfItems": len(alla),
                    "itemListElement": [
                        {"@type": "ListItem", "position": i + 1, "item": projektschema(p)}
                        for i, p in enumerate(alla)
                    ],
                },
            },
            brodsmula("Showcase", "/showcase"),
        ],
    }

    def kort(p):
        extern = p["url"].startswith("http")
        rel = ' rel="noopener"' if extern else ""
        vard = p["url"].replace("https://", "").rstrip("/") if extern else p["url"]
        pill = f'<span class="pill {p["status"]}">{STATUS_ETIKETT[p["status"]]}</span>'
        rubrik = (
            f'<a href="{p["url"]}"{rel}>{html.escape(p["namn"])}</a>'
            if p["url"]
            else html.escape(p["namn"])
        )
        h = [
            f'<article class="proj" id="{p["slug"]}">',
            f'  <h2 class="pn">{rubrik} {pill}</h2>',
            f'  <p class="pt">{html.escape(p["beskrivning"])}</p>',
        ]
        if p.get("avsnitt"):
            h.append("  <dl class=\"pd\">")
            for a in p["avsnitt"]:
                h.append(f'    <dt>{html.escape(a["label"])}</dt><dd>{html.escape(a["body"])}</dd>')
            h.append("  </dl>")
        meta = [x for x in [vard, p.get("stack")] if x]
        h.append(
            f'  <p class="pm">{" · ".join(html.escape(m) for m in meta)}'
            f'{" · " if meta else ""}{" · ".join(html.escape(t) for t in p["taggar"])}</p>'
        )
        h.append("</article>")
        return "\n".join(h)

    # Rubriken renderas bara när det finns något halvfärdigt att visa. En tom
    # grupp lovar pågående byggen som inte finns.
    labbgrupp = f"""
  <div class="grupp">
    <div class="gl">I labbet</div>
    <p class="intro" style="margin-top:8px">Halvfärdigt är standard. Det här byggs just nu — hoppa in.</p>
{chr(10).join(kort(p) for p in ilabbet)}
  </div>
""" if ilabbet else ""

    return (
        head(cfg, css, jsonld)
        + toppbar(hoger=f"{len(alla)} projekt")
        + f"""
<main class="lista">
  <h1>Det här ramlade ut.</h1>
  <p class="intro">Ingen beställde dem. Någon började bygga i Discorden och andra hängde på. Allt är öppet — testa, forka eller posta ditt eget.</p>

  <div class="grupp">
    <div class="gl">I drift</div>
{chr(10).join(kort(p) for p in idrift)}
  </div>
{labbgrupp}
{discord_cta("Det som byggs just nu ligger i Discorden. Posta ditt bygge där — vi lägger upp det här.")}
</main>
</body></html>
"""
    )


# ---------------------------------------------------------------- blogg

def bygg_blogg(css):
    poster = json.loads((ROOT / "tools" / "blogg-index.json").read_text(encoding="utf-8"))
    cfg = {
        "sokvag": "/blogg",
        "titel": "Blogg — guider om AI-agenter, MCP och vibecoding",
        "og_titel": "opensverige blogg",
        "beskrivning": "Guider och genomgångar om AI-agenter, MCP, OpenClaw och vibecoding. Skrivet av builders i opensverige. Gästinlägg är öppna för alla.",
    }

    jsonld = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Blog",
                "@id": f"{BASE}/blogg#blog",
                "name": "opensverige blogg",
                "description": cfg["beskrivning"],
                "url": f"{BASE}/blogg",
                "inLanguage": "sv-SE",
                "isPartOf": {"@id": f"{BASE}/#website"},
                "publisher": {"@id": f"{BASE}/#organization"},
                "blogPost": [
                    {
                        "@type": "BlogPosting",
                        "@id": f'{BASE}/blogg/{p["slug"]}#post',
                        "headline": p["titel"],
                        "description": p["beskrivning"],
                        "url": f'{BASE}/blogg/{p["slug"]}',
                        "datePublished": p["datum"],
                        "author": {"@type": "Person", "name": p["forfattare"]},
                        "keywords": ", ".join(p["taggar"]),
                    }
                    for p in poster
                ],
            },
            brodsmula("Blogg", "/blogg"),
        ],
    }

    rader = []
    for p in poster:
        y, m, d = (int(x) for x in p["datum"].split("-"))
        rader.append(
            f'<a class="rad" href="/blogg/{p["slug"]}">\n'
            f'  <span class="rt"><span class="rn">{html.escape(p["titel"])}</span></span>\n'
            f'  <span class="rd">{html.escape(p["beskrivning"])}</span>\n'
            f'  <span class="rm">{d} {MANADER[m-1]} {y} · {p["lastid"]} min · '
            f'{" · ".join(html.escape(t) for t in p["taggar"])}</span>\n'
            f"</a>"
        )

    return (
        head(cfg, css, jsonld)
        + toppbar(hoger=f"{len(poster)} inlägg")
        + f"""
<main class="lista">
  <h1>Blogg.</h1>
  <p class="intro">Guider, genomgångar och åsikter. Vill du skriva? Gästinlägg är öppna för alla — hör av dig i Discorden.</p>

  <div class="grupp">
    {chr(10).join('    ' + r for r in rader)}
  </div>
{discord_cta("Vill du skriva ett gästinlägg? Säg till i Discorden.")}
</main>
</body></html>
"""
    )


# ---------------------------------------------------------------- varfor

def bygg_varfor(css):
    cfg = {
        "sokvag": "/varfor",
        "titel": "Varför opensverige finns",
        "og_titel": "Varför opensverige finns",
        "beskrivning": "Grundaren Baltsar om varför opensverige finns. 600+ svenska builders som slutade vänta. Verkstad, inte konferens. Halvfärdigt är standard.",
    }

    # Frågorna står på ett ställe och används både till texten och till
    # FAQPage-datan. Skulle de definieras var för sig hinner de glida isär,
    # och strukturerad data som säger något annat än sidan är värre än ingen.
    fragor = [
        ("Nyfiken?", "Välkommen."),
        ("Vill du tjäna pengar?", "Lös ett problem och ta betalt. Ingen stoppar dig."),
        ("Vill du lurka?", "Också okej. Men vågen rör sig med eller utan dig."),
        (
            "Sponsras ni av något företag?",
            "Nej. Ingen leverantör har köpt sig plats här. Ingen betalar för att "
            "nämnas. Föreningen är ideell och medlemmarna bestämmer på årsmötet.",
        ),
        (
            "Driver ni en politisk agenda?",
            "Nej. Vi tar inte partipolitisk ställning och företräder ingen rörelse. "
            "Det enda vi driver är att fler ska kunna bygga själva.",
        ),
        (
            "Hur vet jag att ni är ärliga om verktygen?",
            "Vi rekommenderar det som fungerar. Vi säger till när något inte gör det. "
            "Ingen affär och ingen sponsor påverkar vad som står här. Byter vi åsikt "
            "är det för att verktyget ändrades.",
        ),
    ]
    faq_html = "\n\n".join(
        f"  <h3>{html.escape(f)}</h3>\n  <p>{html.escape(s)}</p>" for f, s in fragor
    )

    jsonld = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "FAQPage",
                "@id": f"{BASE}/varfor#faq",
                "isPartOf": {"@id": f"{BASE}/varfor#webpage"},
                "inLanguage": "sv-SE",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": f,
                        "acceptedAnswer": {"@type": "Answer", "text": s},
                    }
                    for f, s in fragor
                ],
            },
            {
                "@type": "AboutPage",
                "@id": f"{BASE}/varfor#webpage",
                "url": f"{BASE}/varfor",
                "name": cfg["titel"],
                "description": cfg["beskrivning"],
                "inLanguage": "sv-SE",
                "isPartOf": {"@id": f"{BASE}/#website"},
                "about": {"@id": f"{BASE}/#organization"},
                "mainEntity": {"@id": f"{BASE}/varfor#baltsar"},
            },
            {
                "@type": "Person",
                "@id": f"{BASE}/varfor#baltsar",
                "name": "Baltsar",
                "alternateName": "Gustaf Garnow",
                "jobTitle": "Grundare, opensverige",
                "description": "Creative technologist. Grundade opensverige 2025. Bygger Kammaren — en AI-assistent för svenska småföretagare.",
                "url": f"{BASE}/varfor",
                "worksFor": {"@id": f"{BASE}/#organization"},
                "knowsAbout": [
                    "AI-agenter",
                    "Vibecoding",
                    "Model Context Protocol",
                    "OpenClaw",
                    "Hermes",
                    "Grokbot",
                    "Automation för svenska småföretag",
                ],
            },
            brodsmula("Varför", "/varfor"),
        ],
    }

    return (
        head(cfg, css, jsonld, og_typ="article")
        + toppbar(hoger="4 min")
        + f"""
<article class="prose">
  <div class="kicker">Grundaren</div>
  <h1>Varför opensverige finns</h1>
  <div class="byline"><span>Baltsar</span><span class="d">·</span><span>Grundare</span></div>

  <blockquote>Jag startade det här för att jag var trött på att bygga ensam. Det blev en verkstad.</blockquote>

  <p class="lead">Jag heter Baltsar. Creative technologist. Digital designer från början, numera djupt nere i AI-agenter, vibecoding och allt som gör mellanhänder nervösa.</p>

  <p>Jag bygger Kammaren — en AI-assistent för svenska småföretagare. Öppen kod, inga svarta lådor, dina siffror på din maskin. Det projektet lärde mig en sak: <b>att bygga ensam suger.</b></p>

  <p>Inte för att det är svårt. Utan för att ingen sa till mig att min arkitektur var skit. AI:n sa "bra jobbat!" varje gång. Jag satt i en dopaminloop i tre månader och <b>shippade ingenting.</b></p>

  <p class="punch">Jag visste att fler satt i samma fälla. Och det stämde.</p>

  <h2>Sverige har konferenser. Vi har en verkstad.</h2>

  <p>Mellanhänderna tar 15 000 kr för att förklara det du kan bygga själv på en kväll. <b>Vi bygger det de säljer. Fast gratis. Fast öppet.</b></p>

  <p>Vi satt i våra kammare. Alla satt i sina kammare.</p>

  <ul>
    <li>Prompta.</li>
    <li>Få beröm.</li>
    <li>Prompta igen.</li>
    <li>Shippa aldrig.</li>
    <li>Tro att idén är guld.</li>
    <li>Vakta den som Gollum.</li>
  </ul>

  <p>Ingen snor din idé. <b>De bygger sin egen med tre prompts medan du sover.</b> Vi byggde ett test på det — <a href="/gollum">Gollum-testet</a>.</p>

  <p>opensverige är 600+ builders som slutade vänta. Nybörjare, veteraner, designers, systemare, folk utan titel som bara löser problem. Inga möten. Inga stakeholders. Ett GitHub-repo och en Discord.</p>

  <p><b>Vi är i survival mode.</b> Vi har inget kontor. Inga chefer. Inget att förlora. Det gör oss snabbare än varje konsultbolag i det här landet.</p>

  <p>Varje mellanhand som tar betalt för att stå mellan dig och dina siffror, mellan dig och ditt system, mellan dig och din egen kod — <b>vi bygger bort dem.</b></p>

  <h2>Vanliga frågor</h2>

{faq_html}

  <div class="stats">
    <div><span class="v">600+</span><span class="l">builders</span></div>
    <div><span class="v">3</span><span class="l">städer</span></div>
    <div><span class="v">1</span><span class="l">Discord</span></div>
  </div>

  <p>Nybörjare, veteraner, designers, systemare — folk utan titel som löser problem. Stockholm, Göteborg, Malmö. Vi träffas fysiskt. Vi delar kod. Vi skickar pull requests på varandras projekt klockan 23. Det finns inget annat community i Sverige som gör det här.</p>

  <p>Jag vet inte vart det här landar. Ingen vet. Men <b>600+ personer bygger varje dag</b> och det stoppas inte av ett möte.</p>

  <p>Halvfärdigt är standard. Trasigt är välkommet.</p>

  <p class="punch">What's the fucking output?</p>
{discord_cta("Sluta lurka. Börja bygga.")}
</article>
</body></html>
"""
    )


# ---------------------------------------------------------------- integritet

def bygg_integritet(css):
    cfg = {
        "sokvag": "/integritet",
        "titel": "Integritetspolicy — opensverige",
        "og_titel": "Integritetspolicy — opensverige",
        "beskrivning": "Vi samlar in så lite data som möjligt. Vi säljer ingenting, trackar dig inte som person och använder inte din data för att träna AI-modeller.",
    }

    jsonld = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebPage",
                "@id": f"{BASE}/integritet#webpage",
                "url": f"{BASE}/integritet",
                "name": cfg["titel"],
                "description": cfg["beskrivning"],
                "inLanguage": "sv-SE",
                "datePublished": "2026-03-25",
                "dateModified": "2026-09-10",
                "isPartOf": {"@id": f"{BASE}/#website"},
                "about": {"@id": f"{BASE}/#organization"},
            },
            brodsmula("Integritetspolicy", "/integritet"),
        ],
    }

    return (
        head(cfg, css, jsonld)
        + toppbar(hoger="Uppdaterad 2026-09-11")
        + """
<article class="prose">
  <div class="kicker">Policy</div>
  <h1>Integritetspolicy</h1>
  <div class="byline"><span>Baltsar (Gustaf Garnow)</span><span class="d">·</span><span>25 mar 2026</span><span class="d">·</span><span><a href="mailto:opensverige@gmail.com">opensverige@gmail.com</a></span></div>

  <div class="callout">
    <p>Vi samlar in så lite data som möjligt. Vi säljer ingenting. Vi trackar inte dig som person. Om du vill att vi tar bort något — säg till.</p>
  </div>

  <h2>Vad opensverige.se samlar in</h2>

  <h3>Medlemsregistret</h3>
  <p>Anmäler du dig som medlem sparar vi <b>namn och e-postadress</b>, och ditt <b>Discord-användarnamn</b> om du fyller i det. Anmäler du en juridisk person sparar vi även <b>firmanamn, organisationsnummer och namnet på den som företräder er</b>. Vi noterar vilken version av stadgarna du accepterade och när.</p>
  <p><b>Vi frågar aldrig efter personnummer.</b> Föreningen tar inte emot betalningar via sajten och lagrar inga betaluppgifter — medlemsavgiften är frivillig enligt § 4.</p>
  <p><b>Varför.</b> Registret är föreningens röstlängd enligt § 8. Vi behöver det för att kunna kalla till årsmöte, veta vem som får rösta och kunna nå dig som medlem. Den lagliga grunden är <b>avtal</b> (GDPR artikel 6.1b) — medlemskapet är en överenskommelse mellan dig och föreningen.</p>
  <p><b>Vem ser det.</b> Styrelsen. Registret ligger hos Supabase i Stockholm och är inte läsbart utifrån. Vi delar det inte med någon, och det publiceras aldrig.</p>
  <p><b>Vem mer behandlar uppgifterna.</b> Två leverantörer, båda inom EU och båda enbart på vårt uppdrag. <b>Supabase</b> lagrar registret i Stockholm. <b>Resend</b> skickar välkomstmejlet från Irland och sparar mottagaradress och ämnesrad i sin logg i trettio dagar. Ingen av dem får använda uppgifterna till något eget.</p>
  <p><b>Hur länge.</b> Så länge du är medlem. Går du ur raderas inte raden automatiskt — den märks med utträdesdatum så att tidigare röstlängder går att styrka i efterhand. Vill du bli helt borttagen ur registret räcker det att du säger till.</p>
  <p><b>Skräpskydd.</b> När formuläret skickas sparar vi en envägshash av din IP-adress i högst ett dygn, för att hindra massanmälningar. Själva adressen sparas aldrig, och hashen går inte att räkna baklänges till den. Grunden är <b>berättigat intresse</b> (artikel 6.1f) av att skydda röstlängden.</p>
  <p><b>Välkomstmejlet.</b> Blir du medlem får du ett kvitto med ditt medlemsnummer. Det är den enda post vi skickar automatiskt. Vi har inget nyhetsbrev och lägger dig inte i någon utskickslista.</p>

  <h3>Webbplatsen</h3>
  <p><b>Vercel Analytics</b> — anonymiserad besöksstatistik. Inga cookies. Ingen personidentifiering. Vi ser sidvisningar och ungefärligt land, inte vem du är.</p>
  <p><b>Inga tredjepartscookies.</b> Vi använder inte Google Analytics, Facebook Pixel eller liknande spårningsverktyg.</p>
  <p><b>Email</b> — om du skickar email till oss sparar vi meddelandet och din adress för att kunna svara. Vi delar den inte med någon.</p>

  <h3>Gollum-testet</h3>
  <p>Testet körs helt i din webbläsare. <b>Inga svar sparas på någon server.</b> Vi samlar inte in dina resultat. Om du delar ditt resultat på sociala medier är det ditt val.</p>

  <h3>Discord-servern</h3>
  <p>Servern drivs på Discords plattform och lyder under <a href="https://discord.com/privacy" rel="noopener">Discords integritetspolicy</a>. Vi kontrollerar inte vilken data Discord samlar in.</p>
  <p><b>Arcane (XP-bot)</b> trackar aktivitet för rollsystemet. Det hanteras av Arcane och lyder under deras villkor.</p>
  <p><b>Moderering</b> — vi läser publika meddelanden för att upprätthålla serverreglerna. Vi loggar inte konversationer systematiskt.</p>

  <h3>GitHub</h3>
  <p>Om du bidrar med kod via pull requests eller issues blir ditt GitHub-användarnamn publikt synligt. Det är standard för öppen källkod. Vi kontrollerar inte GitHubs datainsamling.</p>

  <h3>Meetup.com</h3>
  <p>Om du anmäler dig till events via Meetup lyder det under <a href="https://www.meetup.com/privacy/" rel="noopener">Meetups integritetspolicy</a>. Vi ser ditt Meetup-namn och om du anmält dig. Inget mer.</p>

  <h2>Vad vi inte gör</h2>
  <ul>
    <li>Vi säljer aldrig din data till någon.</li>
    <li>Vi delar aldrig din information med annonsörer.</li>
    <li>Vi kontaktar aldrig din arbetsgivare baserat på information du delat i communityn.</li>
    <li>Vi använder inte din data för att träna AI-modeller.</li>
  </ul>

  <h2>Cookies</h2>
  <p>opensverige.se använder <b>inga cookies</b> utöver de som krävs för grundläggande funktionalitet. Inga tredjepartscookies. Ingen cookie-banner behövs.</p>

  <h2>Laglig grund</h2>
  <p><b>Medlemsregistret</b> behandlas med stöd av <b>avtal</b> (GDPR artikel 6.1b). Medlemskapet är en överenskommelse mellan dig och föreningen, och registret är röstlängden enligt § 8.</p>
  <p>Övrig behandling vilar på <b>berättigat intresse</b> (artikel 6.1f) för att driva communityn och skydda den mot missbruk. För email-kommunikation baseras behandlingen på <b>samtycke</b> — du kontaktade oss.</p>
  <p>Vi fattar inga automatiserade beslut som har rättslig eller liknande effekt på dig (GDPR artikel 22). Ingen profilering används för att fatta sådana beslut.</p>

  <h2>Dina rättigheter enligt GDPR</h2>
  <p>Du har rätt att:</p>
  <ul>
    <li>Begära tillgång till din data</li>
    <li>Begära rättelse av felaktig data</li>
    <li>Begära radering av din data</li>
    <li>Invända mot behandling</li>
    <li>Lämna klagomål till Integritetsskyddsmyndigheten (IMY)</li>
  </ul>
  <p>Kontakta <a href="mailto:opensverige@gmail.com">opensverige@gmail.com</a> för alla förfrågningar.</p>

  <h2>Ändringar</h2>
  <p>Vi uppdaterar denna policy vid behov. Senaste versionen finns alltid på opensverige.se/integritet.</p>
</article>
</body></html>
"""
    )


# ---------------------------------------------------------------- hackathon

def bygg_hackathon(css):
    """Arkivsida. Eventet gick ut 2026-06-14 — ingen nedräkning kvar,
    men regler och resurser bevaras eftersom bloggposten länkar dit."""
    data = json.loads((ROOT / "tools" / "hackathon-data.json").read_text(encoding="utf-8"))
    sv = data["CONTENT"]["sv"]
    delad = data["SHARED"]

    cfg = {
        "sokvag": "/hackathon",
        "titel": "Spelhackathon — regler, kriterier och resurser | opensverige",
        "og_titel": "opensverige spelhackathon",
        "beskrivning": "Skapa ett litet spel på en vecka. Regler, bedömningskriterier, priser och hela verktygslådan från opensverige spelhackathon. Arkiverat.",
    }

    jsonld = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Event",
                "@id": f"{BASE}/hackathon#event",
                "name": "opensverige spelhackathon",
                "description": sv["tagline"],
                "url": f"{BASE}/hackathon",
                "startDate": "2026-06-07",
                "endDate": delad["deadlineISO"],
                "eventStatus": "https://schema.org/EventScheduled",
                "eventAttendanceMode": "https://schema.org/OnlineEventAttendanceMode",
                "inLanguage": "sv-SE",
                "isAccessibleForFree": True,
                "location": {
                    "@type": "VirtualLocation",
                    "url": delad["discordUrl"],
                    "name": "opensverige Discord",
                },
                "organizer": {"@id": f"{BASE}/#organization"},
            },
            {
                "@type": "WebPage",
                "@id": f"{BASE}/hackathon#webpage",
                "url": f"{BASE}/hackathon",
                "name": cfg["titel"],
                "description": cfg["beskrivning"],
                "inLanguage": "sv-SE",
                "isPartOf": {"@id": f"{BASE}/#website"},
            },
            brodsmula("Hackathon", "/hackathon"),
        ],
    }

    # Källdatan är skriven i presens för ett pågående event. Arkivsidan omformulerar.
    ARKIVTEMPUS = {
        "Pågår nu · 1 vecka": "1 vecka · avslutat juni 2026",
        f'Senast söndag 14 juni kl 00:00 i {delad["channelName"]}':
            f'Stängde söndag 14 juni kl 00:00 i {delad["channelName"]}',
    }
    fakta = "\n".join(
        f'  <div><span class="fl">{html.escape(f["label"])}</span>'
        f'<span class="fv">{html.escape(ARKIVTEMPUS.get(f["value"], f["value"]))}</span></div>'
        for f in sv["facts"]
    )
    krav = "\n".join(
        f'  <div class="krit"><span class="kn">{i+1}</span><div>'
        f'<div class="kt">{html.escape(k["title"])}</div>'
        f'<div class="kb">{html.escape(k["body"])}</div></div></div>'
        for i, k in enumerate(sv["requirements"])
    )
    inlamning = "\n".join(
        f'    <li>{html.escape(s["text"])}'
        f'{" <b>(väger extra)</b>" if s.get("bonus") else ""}</li>'
        for s in sv["submit"]
    )
    kriterier = "\n".join(
        f'  <div class="krit"><span class="kn">{html.escape(k["no"])}</span><div>'
        f'<div class="kt">{html.escape(k["name"])}</div>'
        f'<div class="kb">{html.escape(k["body"])}</div></div>'
        f'<span class="kv">{k["weight"]}{"%" if not k.get("extra") else "% extra"}</span></div>'
        for k in sv["criteria"]
    )
    priser = "\n".join(
        f'    <li><b>{html.escape(p["name"])}</b>'
        f'{" — " + html.escape(p["detail"]) if p.get("detail") else ""}</li>'
        for p in sv["prizes"]
    )
    tips = "\n".join(f"    <li>{html.escape(x)}</li>" for x in sv["tips"])
    regler = "\n".join(f"    <li>{html.escape(x)}</li>" for x in sv["rules"])

    resurser = []
    for g in sv["resources"]:
        resurser.append(f'  <div class="rg">{html.escape(g["group"])}</div>')
        for i in g["items"]:
            resurser.append(
                f'  <div class="ri"><a href="{i["url"]}" rel="noopener">{html.escape(i["name"])}</a>'
                f'<span>{html.escape(i["note"])}</span></div>'
            )

    return (
        head(cfg, css, jsonld, og_typ="article")
        + toppbar(hoger="Arkiverat")
        + f"""
<article class="prose">
  <div class="kicker">Hackathon</div>
  <h1>{html.escape(sv["tagline"])}</h1>
  <div class="byline"><span>opensverige</span><span class="d">·</span><span>{html.escape(sv["deadlineLabel"])}</span></div>

  <div class="arkiv">
    <p>Det här hackathonet är avslutat. Inlämningen stängde {html.escape(sv["deadlineLabel"]).lower()}.
    Regler, kriterier och resurser står kvar — de fungerar för vilket spelbygge som helst.
    Nästa omgång annonseras i <a href="{delad["discordUrl"]}" rel="noopener">Discorden</a>.</p>
  </div>

  <div class="fakta">
{fakta}
  </div>

  <h2 id="delta">Så deltog man</h2>
  <p>{html.escape(sv["participationLead"])}</p>
{krav}

  <h2 id="inlamning">Så lämnade man in</h2>
  <p>{html.escape(sv["submitPrefix"])} <code>{html.escape(delad["channelName"])}</code> {html.escape(sv["submitBy"])} {html.escape(sv["deadlineLabel"].lower())}:</p>
  <ul>
{inlamning}
  </ul>

  <h2 id="kriterier">Kriterier</h2>
  <p>{html.escape(sv["criteriaLead"])}</p>
{kriterier}

  <h2 id="priser">Priser</h2>
  <ul>
{priser}
  </ul>

  <h2 id="tips">Tips</h2>
  <ul>
{tips}
  </ul>

  <h2 id="resources">Resurser</h2>
  <p>{html.escape(sv["resourcesLead"])}</p>
  <div class="res">
{chr(10).join(resurser)}
  </div>
  <p>{html.escape(sv["resourcesTip"])}</p>

  <h2 id="rules">Regler</h2>
  <ul>
{regler}
  </ul>

  <hr>
  <p>Vill du bygga ett spel med AI? Läs guiden: <a href="/blogg/bygg-spel-med-ai">Bygg ett spel med AI på en vecka</a>.</p>
{discord_cta("Nästa hackathon annonseras i Discorden.")}
</article>
</body></html>
"""
    )


def main():
    css = las_artikel_css()
    (SITE / "showcase").mkdir(parents=True, exist_ok=True)
    (SITE / "blogg").mkdir(parents=True, exist_ok=True)

    sidor = {
        SITE / "showcase" / "index.html": bygg_showcase(css),
        SITE / "blogg" / "index.html": bygg_blogg(css),
        SITE / "varfor.html": bygg_varfor(css),
        SITE / "integritet.html": bygg_integritet(css),
        SITE / "hackathon.html": bygg_hackathon(css),
    }
    for p, innehall in sidor.items():
        p.write_text(innehall, encoding="utf-8")
        print(f"  {p.relative_to(SITE)}  {len(innehall):,} tecken")


if __name__ == "__main__":
    main()
