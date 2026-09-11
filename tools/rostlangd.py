#!/usr/bin/env python3
"""Exporterar röstlängden enligt § 8 till en CSV-fil.

Registret finns bara hos Supabase, och på gratisnivån går säkerhetskopiorna
inte att ladda ner. Kör det här inför årsmötet, och gärna då och då däremellan,
så att föreningen har en egen kopia.

Filen innehåller medlemmarnas personuppgifter. Den skrivs därför utanför
arkivet och skriptet vägrar spara den någon annanstans.

    python3 tools/rostlangd.py              # ~/rostlangd-ÅÅÅÅ-MM-DD.csv
    python3 tools/rostlangd.py <sökväg>
"""
import csv
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

PROJEKT = "kmkttmasoemqcyzkjuyv"
TOKEN = Path.home() / ".sb-token"
ARKIV = Path(__file__).resolve().parent.parent

FALT = [
    "namn",
    "epost",
    "typ",
    "firmanamn",
    "orgnr",
    "foretradare",
    "discord",
    "kalla",
    "stadgar_version",
    "stadgar_accepterad_at",
    "anmald_at",
]


def fraga(sql: str, token: str) -> list[dict]:
    svar = subprocess.run(
        [
            "curl", "-sS", "-X", "POST",
            "-H", f"Authorization: Bearer {token}",
            "-H", "Content-Type: application/json",
            f"https://api.supabase.com/v1/projects/{PROJEKT}/database/query",
            "-d", json.dumps({"query": sql}),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(svar.stdout)
    if isinstance(data, dict) and data.get("message"):
        sys.exit(f"Supabase svarade: {data['message']}")
    return data


def main() -> None:
    if not TOKEN.exists():
        sys.exit(f"Ingen token i {TOKEN}. Skapa en på supabase.com/dashboard/account/tokens")
    token = TOKEN.read_text(encoding="utf-8").strip()

    mal = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else (
        Path.home() / f"rostlangd-{date.today()}.csv"
    )
    mal = mal.resolve()
    # Röstlängden är personuppgifter och arkivet är publikt.
    if ARKIV in mal.parents or mal.parent == ARKIV:
        sys.exit(f"Vägrar skriva i arkivet. Välj en sökväg utanför {ARKIV}")

    rader = fraga(
        f"select {', '.join(FALT)} from medlemmar "
        "where uttradd_at is null order by anmald_at",
        token,
    )

    with mal.open("w", encoding="utf-8", newline="") as f:
        skriv = csv.DictWriter(f, fieldnames=["nr", *FALT])
        skriv.writeheader()
        for i, r in enumerate(rader, 1):
            skriv.writerow({"nr": i, **{k: r.get(k) or "" for k in FALT}})
    mal.chmod(0o600)

    juridiska = sum(1 for r in rader if r.get("typ") == "juridisk")
    print(f"{len(rader)} röstberättigade medlemmar, varav {juridiska} juridiska personer")
    print(f"Skrivet till {mal} (läsbar bara för dig)")
    if not rader:
        print("Registret är tomt. Filen innehåller bara rubrikraden.")


if __name__ == "__main__":
    main()
