#!/usr/bin/env python3
"""Skriver in Discords medlemsantal i all copy på sajten.

Antalet kommer från Discords publika invite-endpoint (with_counts), som till
skillnad från widgeten ger totalt antal medlemmar. Ingen nyckel behövs.

Två sorters siffror:
  - "N+ builders" i löptext, meta och llms.txt avrundas nedåt till närmaste
    hundratal. Den copyn står still mellan deployer och ska aldrig påstå mer
    än vad som är sant.
  - .antal och .onl på förstasidan får exakt värde. De
    skrivs dessutom över live av sidans eget skript vid varje sidladdning.

Körs efter generatorerna i BYGGSTEG, eftersom de skriver "600+" i sin HTML.
Går hämtningen inte igenom används senast kända värde i discord-antal.json,
så ett Discord-avbrott aldrig stoppar en deploy eller sänker siffran.
"""
from __future__ import annotations

import json
import re
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
CACHE = Path(__file__).resolve().parent / "discord-antal.json"
INVITE_URL = "https://discord.com/api/v10/invites/ZbV4qB34um?with_counts=true"

# "600+ builders", "600+ svenska builders", "600+ personer",
# "<b>600+</b> builders" och "<span class="v">600+</span><span class="l">builders".
AVRUNDAT = re.compile(
    r"\b\d{3,5}\+(?=(?:</b>|</span><span class=\"l\">)?\s?(?:svenska )?(?:builders|personer))"
)
EXAKT_ANTAL = re.compile(r'(<(?:b|span) class="antal"[^>]*>)\d+(</(?:b|span)>)')
EXAKT_ONLINE = re.compile(r'(<b class="onl"[^>]*>)\d+(</b>)')


def hamta() -> dict[str, int]:
    req = urllib.request.Request(INVITE_URL, headers={"User-Agent": "opensverige-bygg"})
    with urllib.request.urlopen(req, timeout=10) as r:
        d = json.load(r)
    medlemmar, online = d["approximate_member_count"], d["approximate_presence_count"]
    if not isinstance(medlemmar, int) or not isinstance(online, int) or medlemmar < 100:
        raise ValueError(f"orimligt svar från Discord: {medlemmar}, {online}")
    return {"medlemmar": medlemmar, "online": online, "datum": date.today().isoformat()}


def antal() -> dict[str, int]:
    try:
        d = hamta()
        CACHE.write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8")
        return d
    except Exception as e:
        d = json.loads(CACHE.read_text(encoding="utf-8"))
        print(f"  Discord svarade inte ({e}); använder {d['medlemmar']} från {d['datum']}")
        return d


def main() -> None:
    d = antal()
    avrundat = f"{d['medlemmar'] // 100 * 100}+"
    andrade = 0
    for p in [*SITE.rglob("*.html"), SITE / "llms.txt"]:
        t = p.read_text(encoding="utf-8")
        t2 = AVRUNDAT.sub(avrundat, t)
        t2 = EXAKT_ANTAL.sub(rf"\g<1>{d['medlemmar']}\g<2>", t2)
        t2 = EXAKT_ONLINE.sub(rf"\g<1>{d['online']}\g<2>", t2)
        if t2 != t:
            p.write_text(t2, encoding="utf-8")
            andrade += 1

    api = SITE / "api" / "community.json"
    # Regex i stället för json.dumps: filen är handformaterad och ska inte
    # skrivas om rad för rad vid varje deploy.
    t = api.read_text(encoding="utf-8")
    t = re.sub(r'("discord_members": )\d+', rf"\g<1>{d['medlemmar']}", t)
    t = re.sub(r'("as_of": )"[^"]*"', rf'\g<1>"{d["datum"]}"', t)
    json.loads(t)
    api.write_text(t, encoding="utf-8")

    print(f"  {d['medlemmar']} medlemmar ({avrundat} i copy), {d['online']} online, {andrade} filer")


if __name__ == "__main__":
    main()
