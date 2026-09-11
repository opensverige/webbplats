#!/usr/bin/env python3
"""Bygg om sajten och stega ut till draft eller produktion.

    python3 tools/deploy.py draft        # bygg + noindex, ingen deploy
    python3 tools/deploy.py prod         # bygg + indexerbart, ingen deploy
    python3 tools/deploy.py draft --push # samma, och kör vercel deploy

Draft-läget är avsiktligt destruktivt mot indexerbarheten: det skriver
noindex i varje sida och Disallow: / i robots.txt, så draft-domänen aldrig
kan konkurrera med opensverige.se om samma innehåll. Prod-läget bygger
alltid om från källan först, så en draft-build kan inte läcka vidare.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
BYGGSTEG = [
    "tools/migrera-blogg.py",
    "tools/seo-sidor.py",
    "tools/bygg-sidor.py",
    "tools/bygg-gollum.py",
    "tools/bygg-404.py",
    "tools/footer.py",
    "tools/verifiera.py",
]

ROBOTS_PROD = "index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1"
ROBOTS_NOINDEX = "noindex,nofollow"
ROBOTS_TAGG = '<meta name="robots" content="{}">'
ROBOTS_DRAFT = """# Draftmiljö. Inget här ska indexeras.
# Produktionens robots.txt genereras av tools/deploy.py prod.
User-agent: *
Disallow: /
"""


def kor(steg: str) -> None:
    r = subprocess.run([sys.executable, steg], cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stdout.write(r.stdout)
        sys.stderr.write(r.stderr)
        sys.exit(f"\n{steg} misslyckades — avbryter deploy.")
    print(f"  ✓ {steg}")


def html_filer():
    return sorted(SITE.rglob("*.html"))


def satt_robots(varde: str) -> int:
    """Skriv om robots-taggens värde i varje sida. Idempotent i båda
    riktningarna: taggen byts på plats, aldrig raderad, så en draft-build
    kan alltid vändas tillbaka till ett indexerbart bygge."""
    tagg = ROBOTS_TAGG.format(varde)
    n = 0
    for f in html_filer():
        t = f.read_text(encoding="utf-8")
        if re.search(r'<meta name="robots" content="[^"]*">', t):
            t2 = re.sub(r'<meta name="robots" content="[^"]*">', tagg, t)
        else:
            t2 = t.replace("</title>", "</title>\n" + tagg, 1)
        if t2 != t:
            f.write_text(t2, encoding="utf-8")
            n += 1
    return n


def rensa_draftspar() -> int:
    """Ta bort noindex och lägg tillbaka produktionens robots.txt.

    Måste köras före bygget, inte efter: verifiera.py granskar robots.txt
    och skulle annars fälla bygget på draftens Disallow: /.
    """
    skrap = SITE / "robots.txt.prod"
    if skrap.exists():
        shutil.move(str(skrap), str(SITE / "robots.txt"))
    return satt_robots(ROBOTS_PROD)


def kontrollera_prod() -> None:
    """Sista spärren: inget indexerbart bygge får innehålla draftspår."""
    fel = []
    for f in html_filer():
        # 404-sidan ska vara noindex även i produktion. Den är inte en sida
        # någon ska hitta i en sökmotor.
        if f.name == "404.html":
            continue
        t = f.read_text(encoding="utf-8")
        if ROBOTS_NOINDEX in t:
            fel.append(f"{f.relative_to(SITE)}: innehåller noindex")
        if ROBOTS_TAGG.format(ROBOTS_PROD) not in t:
            fel.append(f"{f.relative_to(SITE)}: saknar indexerbar robots-tagg")
    robots = (SITE / "robots.txt").read_text(encoding="utf-8")
    if re.search(r"^Disallow: /$", robots, re.M):
        fel.append("robots.txt: Disallow: / blockerar hela sajten")
    if "Sitemap: https://opensverige.se/sitemap.xml" not in robots:
        fel.append("robots.txt: saknar sitemap-rad")
    if fel:
        for x in fel:
            print(f"  x {x}")
        sys.exit("\nProduktionsbygget är inte indexerbart — avbryter.")


def main() -> None:
    lage = sys.argv[1] if len(sys.argv) > 1 else ""
    if lage not in {"draft", "prod"}:
        sys.exit(__doc__)
    pusha = "--push" in sys.argv[2:]

    print(f"Bygger sajten ({lage})")
    if lage == "prod":
        rensat = rensa_draftspar()
        if rensat:
            print(f"  ✓ städat draftspår från {rensat} sidor")
    for steg in BYGGSTEG:
        kor(steg)

    if lage == "draft":
        (SITE / "robots.txt.prod").write_text(
            (SITE / "robots.txt").read_text(encoding="utf-8"), encoding="utf-8"
        )
        (SITE / "robots.txt").write_text(ROBOTS_DRAFT, encoding="utf-8")
        print(f"  ✓ noindex på {satt_robots(ROBOTS_NOINDEX)} sidor, robots.txt blockerar allt")
    else:
        kontrollera_prod()
        indexerbara = [f for f in html_filer() if f.name != "404.html"]
        print(f"  ✓ {len(indexerbara)} sidor indexerbara, robots.txt öppen")

    sitemap = (SITE / "sitemap.xml").read_text(encoding="utf-8")
    kanon = len(re.findall(r"<loc>", sitemap))
    api = json.loads((SITE / "api" / "community.json").read_text(encoding="utf-8"))
    print(
        f"\n{len(html_filer())} sidor · {kanon} i sitemap · "
        f"{api['stats']['discord_members']} builders i Discorden · "
        f"{api['stats']['registered_members']} i medlemsregistret"
    )

    if not pusha:
        print(f"\nInget deployat. Kör med --push när du är nöjd:"
              f"\n  python3 tools/deploy.py {lage} --push")
        return

    mal = ["vercel", "deploy", str(SITE)] + (["--prod"] if lage == "prod" else [])
    print(f"\n$ {' '.join(mal)}")
    subprocess.run(mal, cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
