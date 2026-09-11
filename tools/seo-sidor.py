#!/usr/bin/env python3
"""Normaliserar SEO-head och interna länkar på de handskrivna sidorna.

Engångsverktyg, som migrera-blogg.py. Efter körning är HTML-filerna källan.
Idempotent: kör om utan att dubblera taggar.
"""

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
BASE = "https://opensverige.se"
DISCORD = "https://discord.gg/ZbV4qB34um"

SIDOR = {
    "bli-medlem.html": {
        "sokvag": "/bli-medlem",
        "titel": "Bli medlem i opensverige — gratis, en röst på årsmötet",
        "beskrivning": "Bli medlem i ideella föreningen opensverige. Avgiften är frivillig, du får en röst på årsmötet och rätt att söka resurser ur labbet. Tre fält.",
        "og_titel": "Bli medlem i opensverige",
        "brodsmula": "Bli medlem",
    },
    "stadgar.html": {
        "sokvag": "/stadgar",
        "titel": "Stadgar — ideella föreningen opensverige",
        "beskrivning": "Stadgarna för ideella föreningen opensverige i sin helhet. Medlemsavgiften är frivillig och medlemskap får aldrig villkoras av betalning.",
        "og_titel": "Stadgar — opensverige",
        "brodsmula": "Stadgar",
    },
    "regler.html": {
        "sokvag": "/regler",
        "titel": "Regler i Discorden — opensverige",
        "beskrivning": "Fritt språk, hårt mot idéer och mjukt mot människor. Reglerna som gäller i opensverige Discord: vad som är okej och vad som aldrig är det.",
        "og_titel": "Regler — opensverige",
        "brodsmula": "Regler",
    },
}

# Taggar som skriptet äger. Tas bort före injicering så körningen blir idempotent.
AGDA = re.compile(
    r'\n?[ \t]*<(?:'
    r'meta\s+name="(?:description|robots|theme-color|author|keywords|twitter:[^"]+)"'
    r'|meta\s+property="og:[^"]+"'
    r'|link\s+rel="(?:canonical|icon|apple-touch-icon|manifest)"'
    r')[^>]*>',
    re.I,
)


def bygg_head(cfg):
    url = BASE + cfg["sokvag"]
    b = html.escape(cfg["beskrivning"], quote=True)
    ogt = html.escape(cfg["og_titel"], quote=True)
    return f"""<meta name="description" content="{b}">
<link rel="canonical" href="{url}">
<meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1">
<meta name="theme-color" content="#fbfaf7">
<meta name="author" content="opensverige">
<meta property="og:type" content="website">
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
<link rel="manifest" href="/favicon/site.webmanifest">"""


def bygg_jsonld(cfg):
    url = BASE + cfg["sokvag"]
    return {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebPage",
                "@id": f"{url}#webpage",
                "url": url,
                "name": cfg["titel"],
                "description": cfg["beskrivning"],
                "inLanguage": "sv-SE",
                "isPartOf": {"@id": f"{BASE}/#website"},
                "about": {"@id": f"{BASE}/#organization"},
            },
            {
                "@type": "BreadcrumbList",
                "@id": f"{url}#breadcrumb",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Start", "item": f"{BASE}/"},
                    {"@type": "ListItem", "position": 2, "name": cfg["brodsmula"]},
                ],
            },
        ],
    }


def fixa_lankar(h):
    h = re.sub(r'href="v7\.html"', 'href="/"', h)
    for sida in ["bli-medlem", "stadgar", "regler"]:
        h = re.sub(rf'href="{sida}\.html"', f'href="/{sida}"', h)
    h = re.sub(r'href="artikel\.html"', 'href="/blogg/mcp-vs-rest"', h)
    h = re.sub(r'src="logo\.png"', 'src="/assets/logo.webp"', h)
    for img in ["hand", "grok", "r-low", "r-max", "r-ultra"]:
        h = re.sub(rf'src="{img}\.png"', f'src="/assets/{img}.webp"', h)
    # Discord-knappar utan mål
    h = re.sub(
        r'(class="dbtn[^"]*") href="#">(<svg)',
        rf'\1 href="{DISCORD}" rel="noopener">\2',
        h,
    )
    return h


def main():
    for filnamn, cfg in SIDOR.items():
        p = SITE / filnamn
        h = p.read_text(encoding="utf-8")

        # Rensa taggar skriptet äger, samt tidigare injicerad JSON-LD
        h = AGDA.sub("", h)
        h = re.sub(
            r'\n?<script type="application/ld\+json">.*?</script>', "", h, flags=re.S
        )

        # Titel
        h = re.sub(
            r"<title>.*?</title>",
            f'<title>{html.escape(cfg["titel"])}</title>',
            h,
            count=1,
            flags=re.S,
        )

        # Head efter title
        h = re.sub(
            r"(</title>)", r"\1\n" + bygg_head(cfg).replace("\\", "\\\\"), h, count=1
        )

        # JSON-LD före </head>
        ld = json.dumps(bygg_jsonld(cfg), ensure_ascii=False, indent=2)
        h = h.replace(
            "</head>",
            f'<script type="application/ld+json">\n{ld}\n</script>\n</head>',
            1,
        )

        h = fixa_lankar(h)
        p.write_text(h, encoding="utf-8")

        kvar = len(re.findall(r'href="#"', h)) + len(
            re.findall(r'href="[^"]*\.html"', h)
        )
        print(f'  {filnamn:20} canonical={cfg["sokvag"]:14} kvar_att_kolla={kvar}')


if __name__ == "__main__":
    main()
