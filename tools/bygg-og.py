#!/usr/bin/env python3
"""Renderar delningsbilderna i site/assets/ från tools/og/og.html.

Körs för hand när en bild ska ändras. Det är inget byggsteg: bilderna är
incheckade och deployen rör dem inte. Kräver Google Chrome och ImageMagick
(magick), till skillnad från resten av tools/.

    python3 tools/bygg-og.py            # alla kort
    python3 tools/bygg-og.py lurka      # ett kort

En ändrad bild ska få nytt filnamn. /assets/ serveras som immutable i ett år,
och LinkedIn, Slack och Discord sparar bilden per adress.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MALL = ROOT / "tools" / "og" / "og.html"
UT = ROOT / "site" / "assets"
BREDD, HOJD = 1200, 630
VANTA = 60  # sekunder per kort innan vi ger upp

# kort i og.html -> filnamn i site/assets. Filnamnet följer texten på bilden,
# så ny text ger nytt namn av sig självt.
KORT = {
    "skiten": "og-bygg-skiten.jpg",  # startsidan och standard
    "lurka": "og-lurka.jpg",         # /bli-medlem
}

CHROME = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "google-chrome",
    "chromium",
]


def hitta_chrome() -> str:
    for kandidat in CHROME:
        if Path(kandidat).exists() or shutil.which(kandidat):
            return kandidat
    sys.exit("Hittar ingen Chrome. Lägg till sökvägen i CHROME.")


def rendera(chrome: str, kort: str, mal: Path, tmp: Path) -> None:
    png = tmp / f"{kort}.png"
    # Dubbel täthet och nedskalning efteråt ger renare kanter på rubrikerna
    # än en rendering direkt i 1200x630.
    chrome_proc = subprocess.Popen(
        [
            chrome,
            "--headless=new",
            "--hide-scrollbars",
            "--no-first-run",
            f"--user-data-dir={tmp / ('profil-' + kort)}",
            "--force-device-scale-factor=2",
            f"--window-size={BREDD},{HOJD}",
            # Typsnitten hämtas över nätet; budgeten ger dem tid att komma.
            "--virtual-time-budget=6000",
            f"--screenshot={png}",
            f"{MALL.as_uri()}?v={kort}",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    # Chrome skriver bilden men avslutar inte alltid av sig självt på macOS.
    # Vänta därför på filen i stället för på processen, och stäng den sedan.
    storlek, stilla, start = -1, 0, time.monotonic()
    while stilla < 4:
        if time.monotonic() - start > VANTA:
            chrome_proc.kill()
            sys.exit(f"Chrome gav ingen bild för {kort} inom {VANTA} s.")
        time.sleep(0.25)
        nu = png.stat().st_size if png.exists() else -1
        stilla = stilla + 1 if nu == storlek and nu > 0 else 0
        storlek = nu
    chrome_proc.terminate()
    try:
        chrome_proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        chrome_proc.kill()
    # 4:4:4 så att rött mot svart inte blöder i kanterna.
    subprocess.run(
        [
            "magick", str(png),
            "-resize", f"{BREDD}x{HOJD}!",
            "-strip",
            "-sampling-factor", "4:4:4",
            "-quality", "86",
            str(mal),
        ],
        check=True,
    )
    print(f"  ✓ {mal.relative_to(ROOT)}  {mal.stat().st_size // 1024} kB")


def main() -> None:
    valda = sys.argv[1:] or list(KORT)
    okanda = [k for k in valda if k not in KORT]
    if okanda:
        sys.exit(f"Okänt kort: {', '.join(okanda)}. Finns: {', '.join(KORT)}")
    if not shutil.which("magick"):
        sys.exit("Hittar inte magick (ImageMagick).")
    chrome = hitta_chrome()
    with tempfile.TemporaryDirectory() as tmp:
        for kort in valda:
            rendera(chrome, kort, UT / KORT[kort], Path(tmp))


if __name__ == "__main__":
    main()
