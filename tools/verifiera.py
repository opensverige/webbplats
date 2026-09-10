#!/usr/bin/env python3
"""Genererar sitemap.xml och verifierar sajten före deploy.

Kontrollerar: interna länkar, SEO-taggar, JSON-LD, canonical-konsekvens,
bildreferenser och att sitemap matchar faktiska filer.

Körs: python3 tools/verifiera.py
Avslutar med kod 1 om något är fel.
"""

import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
BASE = "https://opensverige.se"

# Prioritet och ändringsfrekvens per sökväg
SITEMAP_VIKT = {
    "/": ("1.0", "weekly"),
    "/blogg": ("0.8", "weekly"),
    "/showcase": ("0.8", "weekly"),
    "/gollum": ("0.8", "monthly"),
    "/varfor": ("0.7", "monthly"),
    "/bli-medlem": ("0.7", "monthly"),
    "/hackathon": ("0.5", "yearly"),
    "/stadgar": ("0.4", "yearly"),
    "/regler": ("0.4", "yearly"),
    "/integritet": ("0.3", "yearly"),
}
BLOGG_VIKT = ("0.6", "monthly")
GOLLUM_VIKT = ("0.4", "yearly")

fel = []
varning = []


def sokvag_for(p: Path) -> str:
    """Filsökväg -> publik URL-sökväg (cleanUrls i vercel.json)."""
    rel = p.relative_to(SITE).as_posix()
    if rel == "index.html":
        return "/"
    if rel.endswith("/index.html"):
        return "/" + rel[: -len("/index.html")]
    return "/" + rel[: -len(".html")]


def alla_sidor():
    return sorted(SITE.rglob("*.html"))


def bygg_sitemap(sidor):
    idag = date.today().isoformat()
    poster = []
    for p in sidor:
        sv = sokvag_for(p)
        if sv.startswith("/blogg/"):
            pri, frek = BLOGG_VIKT
        elif sv.startswith("/gollum/"):
            pri, frek = GOLLUM_VIKT
        elif sv in SITEMAP_VIKT:
            pri, frek = SITEMAP_VIKT[sv]
        else:
            varning.append(f"sitemap: {sv} saknar prioritet, hoppas över")
            continue
        loc = BASE + ("" if sv == "/" else sv)
        poster.append((loc, pri, frek))

    # Startsidan först, sen efter prioritet
    poster.sort(key=lambda x: (x[0] != BASE, -float(x[1]), x[0]))

    rader = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for loc, pri, frek in poster:
        rader += [
            "  <url>",
            f"    <loc>{loc}</loc>",
            f"    <lastmod>{idag}</lastmod>",
            f"    <changefreq>{frek}</changefreq>",
            f"    <priority>{pri}</priority>",
            "  </url>",
        ]
    rader.append("</urlset>")
    (SITE / "sitemap.xml").write_text("\n".join(rader) + "\n", encoding="utf-8")
    return [loc for loc, _, _ in poster]


def kontrollera_sida(p: Path, giltiga: set):
    h = p.read_text(encoding="utf-8")
    namn = p.relative_to(SITE).as_posix()
    sv = sokvag_for(p)

    # Obligatoriska taggar
    for monster, etikett in [
        (r"<title>[^<]+</title>", "title"),
        (r'<meta name="description" content="[^"]{40,}"', "description (min 40 tecken)"),
        (r'<link rel="canonical"', "canonical"),
        (r'<meta name="robots"', "robots"),
        (r'<meta property="og:title"', "og:title"),
        (r'<meta property="og:image"', "og:image"),
        (r'<meta name="twitter:card"', "twitter:card"),
        (r'<script type="application/ld\+json">', "JSON-LD"),
    ]:
        if not re.search(monster, h):
            fel.append(f"{namn}: saknar {etikett}")

    # Exakt en h1 i markup. Skript räknas inte: quizen renderar en vy i taget
    # via innerHTML, så dess h1-mallar är aldrig samtidigt i DOM:en.
    markup = re.sub(r"<script\b.*?</script>", "", h, flags=re.S | re.I)
    antal_h1 = len(re.findall(r"<h1[\s>]", markup))
    if antal_h1 != 1:
        fel.append(f"{namn}: {antal_h1} st h1 (ska vara 1)")

    # Canonical ska matcha filens sökväg
    m = re.search(r'<link rel="canonical" href="([^"]+)"', h)
    if m:
        vantat = BASE + ("/" if sv == "/" else sv)
        if m.group(1) != vantat:
            fel.append(f"{namn}: canonical {m.group(1)} != {vantat}")

    # JSON-LD ska parsa
    for block in re.findall(
        r'<script type="application/ld\+json">(.*?)</script>', h, re.S
    ):
        try:
            json.loads(block)
        except Exception as e:
            fel.append(f"{namn}: ogiltig JSON-LD ({e})")

    # noindex får inte läcka till produktion
    if re.search(r'content="[^"]*noindex', h):
        fel.append(f"{namn}: innehåller noindex")

    # Interna länkar
    for href in re.findall(r'href="(/[^"#?]*)', h):
        if href.startswith(("/assets/", "/favicon/", "/api/")):
            if not (SITE / href.lstrip("/")).exists():
                fel.append(f"{namn}: bruten resurslänk {href}")
            continue
        if href.rstrip("/") == "":
            continue
        if href.rstrip("/") not in giltiga:
            fel.append(f"{namn}: bruten intern länk {href}")

    # Tomma länkar
    for tom in re.findall(r'href="#"', h):
        varning.append(f"{namn}: tom länk href=\"#\"")

    # Bildreferenser
    for src in re.findall(r'src="(/[^"]+)"', h):
        if not (SITE / src.lstrip("/")).exists():
            fel.append(f"{namn}: saknad bild {src}")

    # Alt-text
    for tagg in re.findall(r"<img[^>]*>", h):
        if "alt=" not in tagg:
            fel.append(f"{namn}: img utan alt: {tagg[:70]}")


def main():
    sidor = alla_sidor()
    giltiga = {sokvag_for(p).rstrip("/") or "/" for p in sidor}
    giltiga.add("/")

    lokationer = bygg_sitemap(sidor)

    for p in sidor:
        kontrollera_sida(p, giltiga)

    # robots.txt ska peka på sitemap
    robots = (SITE / "robots.txt").read_text(encoding="utf-8")
    if f"Sitemap: {BASE}/sitemap.xml" not in robots:
        fel.append("robots.txt: saknar Sitemap-rad")
    if re.search(r"^\s*Disallow:\s*/\s*$", robots, re.M):
        fel.append("robots.txt: Disallow: / blockerar hela sajten")

    # llms.txt får inte peka på sidor som inte finns
    llms = (SITE / "llms.txt").read_text(encoding="utf-8")
    for url in re.findall(rf"{re.escape(BASE)}(/[a-z0-9\-/.]*)", llms):
        rensad = url.rstrip("/") or "/"
        if "." in rensad or rensad.startswith("/api"):
            continue
        if rensad not in giltiga:
            varning.append(f"llms.txt: pekar på {url} som inte finns ännu")

    print(f"Sidor: {len(sidor)}   Sitemap-URL:er: {len(lokationer)}")
    print("Sökvägar:", ", ".join(sorted(giltiga)))

    if varning:
        print(f"\n{len(varning)} varning(ar):")
        for v in sorted(set(varning)):
            print(f"  ! {v}")

    if fel:
        print(f"\n{len(fel)} FEL:")
        for f in fel:
            print(f"  x {f}")
        sys.exit(1)

    print("\nAllt OK.")


if __name__ == "__main__":
    main()
