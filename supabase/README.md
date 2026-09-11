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

Funktionen använder en egen nyckel med enbart `sending_access`, låst till
`send.opensverige.se`. Den kan varken läsa utskickshistorik eller röra
domäner. Läcker den kan någon skicka post i vårt namn, men inte komma åt
något. Den ligger som hemligheten `RESEND_API_KEY` hos Supabase och ska
aldrig in i repot.

Administrationsnyckeln som domänen sattes upp med är en annan, och kan
återkallas utan att utskicken slutar fungera.

## Röstlängden

Registret finns bara hos Supabase, och på gratisnivån går säkerhetskopiorna
inte att ladda ner. Det finns dagliga kopior, men ingen kopia utanför
plattformen — försvinner projektet försvinner röstlängden.

```sh
python3 tools/rostlangd.py
```

Skriptet skriver en CSV utanför arkivet, läsbar bara för dig, och vägrar spara
i repot. Kör det inför årsmötet.

Ska en adress rättas är dashboarden bättre än en token. Tabellvyn på
supabase.com låter dig ändra raden direkt, skyddad av lösenord och tvåfaktor,
medan en personlig token ger full åtkomst till hela kontot.

## Att projektet inte pausas

Supabase pausar gratisprojekt som visar låg aktivitet under sju dagar.
Databasen får bara trafik när någon anmäler sig, så en tyst vecka räcker för
att nästa anmälan ska misslyckas. `.github/workflows/halla-vaken.yml` pingar
därför funktionen varje dygn.

GitHub stänger av schemalagda flöden i arkiv som varit orörda i sextio dagar.
Går det längre än så mellan commits måste flödet startas om för hand.

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
