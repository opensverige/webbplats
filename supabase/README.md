# Medlemsanmälan

Backend för formuläret på `/bli-medlem`. Projektet heter `opensverige-forening`
och ligger i `eu-north-1`.

Koden här hämtades ur den driftsatta funktionen 2026-09-11 och fanns dessförinnan
bara hos Supabase. Om projektet försvinner går den inte att återskapa någon
annanstans — därför ligger den i repot.

## Vad som finns

| Fil | Innehåll |
| --- | --- |
| `functions/medlem/index.ts` | Edge-funktionen bakom `POST /functions/v1/medlem` |
| `schema.sql` | Tabellen `medlemmar`, avläst från databasen |

## Varför endpointen är öppen

`verify_jwt` är avstängt med flit. Stadgarna § 4 säger att medlem är den som
anmäler sig — formuläret får inte kräva ett konto, och IL 7 kap. 10 § förutsätter
att föreningen är öppen. Skyddet ligger därför i lagren under:

- **Origin-kontroll** mot en allowlist. Stoppar andra webbplatser, men inte
  `curl` — CORS är något webbläsaren upprätthåller, inte servern.
- **Honeypot** på fältet `webbplats`. Kollas före valideringen och svarar
  `{"ok":true}` med status 200, så en bot tror att den lyckades. Fångar bara
  den som fyller i alla fält.
- **Strikt validering** i funktionen, upprepad som CHECK-constraints i
  databasen.
- **Unikt index** på `lower(epost)` för aktiva medlemmar, vilket ger 409.

Det som saknas är hastighetsbegränsning. Samma avsändare kan i dag skapa
obegränsat många medlemmar med olika adresser.

## E-post

Utgående post går via Resend från underdomänen `send.opensverige.se`, region
`eu-west-1`, så att uppgifterna stannar inom EU liksom registret.

Underdomänen är vald med flit. Apex `opensverige.se` är fri att användas för
inkommande post längre fram utan att SPF-posterna krockar.

| Post | Namn | Syfte |
| --- | --- | --- |
| TXT | `resend._domainkey.send` | DKIM-signering |
| TXT | `send.send` | SPF |
| MX | `send.send` | studsar tillbaka till Amazon SES |
| CNAME | `rsend.send` | spårning |
| TXT | `_dmarc.send` | `p=reject`, skyddar namnet mot förfalskning |

DNS ligger hos Vercel trots att domänen är registrerad någon annanstans, så
posterna sätts med `vercel dns add opensverige.se <namn> <typ> <värde>`.

DMARC står på `p=reject` direkt. Underdomänen är ny och skickar bara vår egen
post, som är både DKIM-signerad och SPF-godkänd, så det finns ingen äldre
avsändare som kan råka blockeras.

Nyckeln ligger som hemligheten `RESEND_API_KEY` hos Supabase. Den ska aldrig
in i repot.

## Läsa och ändra

Det finns ingen Supabase CLI installerad. Allt går via Management API med en
personlig token, som aldrig ska ligga i repot:

```sh
SB=$(tr -d '\n ' < ~/.sb-token)
REF=kmkttmasoemqcyzkjuyv

# Läsa funktionen som körs (kommer som eszip-bundle, inte källkod)
curl -s -H "Authorization: Bearer $SB" \
  "https://api.supabase.com/v1/projects/$REF/functions/medlem/body" -o medlem.eszip

# Fråga databasen
curl -s -X POST -H "Authorization: Bearer $SB" -H 'Content-Type: application/json' \
  "https://api.supabase.com/v1/projects/$REF/database/query" \
  -d '{"query":"select count(*) from medlemmar"}'
```

Tokenen skapas på <https://supabase.com/dashboard/account/tokens> och ger full
åtkomst till hela kontot. Återkalla den när du är klar.
