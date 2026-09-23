# Medlemsanmälan

Backend för formuläret på `/bli-medlem`. Projektet heter `opensverige-forening`
och ligger i `eu-north-1`.

Koden här hämtades ur den driftsatta funktionen 2026-09-11 och fanns dessförinnan
bara hos Supabase. Om projektet försvinner går den inte att återskapa någon
annanstans — därför ligger den i repot.

## Vad som finns

| Fil | Innehåll |
| --- | --- |
| `functions/medlem/index.ts` | Edge-funktionen bakom `POST /functions/v1/medlem` och `/medlem/bekrafta` |
| `functions/medlem/hjalp.ts` | Rena hjälpfunktioner: escaping, validering, token |
| `functions/medlem/hjalp_test.ts` | Tester för dem, `deno test --allow-net=jsr.io` |
| `schema.sql` | Tabellerna `medlemmar`, `anmalningar`, `anmalan_forsok` och `utskick` |

## Flödet i två steg

Sedan 2026-09-24 bekräftas e-postadressen innan medlemskapet skapas.

1. **Formuläret** skickar `POST /medlem`. Funktionen sparar en rad i
   `anmalningar` med en hashad engångstoken och mejlar en länk till
   `/bekrafta?t=…`. Ingen medlem skapas här, inget nummer delas ut.
2. **Länken** öppnar `site/bekrafta.html`, som skickar token med
   `POST /medlem/bekrafta`. Först nu skapas raden i `medlemmar`, numret delas
   ut och välkomstmejlet går. Sidan visar numret och det delbara kortet.

Sidan gör anropet, inte länken i sig. Mejlskannrar förhämtar länkar och hade
annars förbrukat engångstoken innan personen hann klicka.

Svaret på formuläret är detsamma oavsett om adressen är ny, väntar på
bekräftelse eller redan är medlem, och innehåller aldrig något medlemsnummer.
Skillnaden syns först på bekräftelsesidan, dit bara den som äger inkorgen
kommer. Så kan ingen utifrån testa sig fram till vilka som är medlemmar.

**Varför det inte strider mot § 4.** Stadgarna säger att medlem är den som
anmäler sig och accepterar stadgarna. En anmälan någon annan skickat i ditt
namn är inte din anmälan. Bekräftelsen är alltså inte ett extra villkor för
medlemskap utan sättet föreningen vet att det är du som anmält dig.
Medlemskapet börjar när adressen bekräftats; `stadgar_accepterad_at` är
tidpunkten formuläret skickades och `anmald_at` tidpunkten för bekräftelsen.
De 29 medlemmar som anmält sig före 2026-09-24 är orörda.

**Länken** gäller i 24 timmar och kan bara användas en gång. Nytt mejl kan
begäras högst tre gånger per länkcykel och tidigast tio minuter emellan;
funktionen svarar ok även när den håller inne, så inget läcker.

**Obekräftade anmälningar** raderas sju dagar efter att länken gått ut. Ett
mejl som inte går att skicka raderar anmälan direkt, så ett nytt försök inte
stoppas av omsändningsregeln.

**Välkomstmejlet** är ett kvitto, aldrig ett villkor. Är Resend nere eller
dagskvoten slut när någon bekräftar är hen medlem ändå; numret står på sidan.

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
- **Unikt index** på `lower(epost)` för aktiva medlemmar. Dubbletten syns
  aldrig i svaret, bara på bekräftelsesidan.
- **Hastighetsbegränsning** per nätverk: 20 anrop per tio minuter och 50 per
  dygn, räknat på en saltad hash av `cf-connecting-ip`. Det är adressen
  Cloudflare sett ansluta, och kan inte sättas av klienten. Första värdet i
  `x-forwarded-for` kunde det.
- **Sändtak** på 90 mejl per dygn totalt, under Resends gratisnivå på 100.
  Utan det kunde ett skript tömma kvoten och hindra riktiga anmälningar. Nås
  taket svarar formuläret 503 med en tydlig text.
- **Bekräftad adress** innan något hamnar i `medlemmar`. Se flödet ovan.
- **Escaping och teckenkontroll.** Namn, firmanamn, företrädare och Discord
  får inte innehålla `<`, `>`, `://` eller kontrolltecken, och personnamn inte
  `@`. Det som ändå hamnar i ett mejl HTML-escapas. Innan 2026-09-24 sattes
  namnet oescapat i välkomstmejlet, så vem som helst kunde få en länk skickad
  från vår signerade avsändare till valfri adress.

## E-post

Utgående post går via Resend från underdomänen `send.opensverige.se`, region
`eu-west-1`, så att uppgifterna stannar inom EU liksom registret.

Två mejl per medlem: bekräftelselänken och välkomstmejlet med numret. Med
dagens takt är det långt under gratisnivåns 3 000 per månad; dagstaket på
100 är den gräns som spelar roll, se sändtaket ovan.

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

## Stadgeversionen

`stadgar_version` är **1.0**. Stadgarna antogs 2026-04-23, BankID-signerades i
maj 2026 och har aldrig ändrats. Någon stadgeändring enligt § 11 har inte skett.

Fram till 2026-09-12 sparades värdet `2026-09-10`. Det datumet var när HTML:en
skrevs rent, inte ett föreningsbeslut. Att spara det som den version medlemmen
accepterat pekade på ett dokument som inte finns i beslutsloggen, vilket hade
gjort det oklart vad som gällde vid en tvist eller uteslutning.

**Rättelse 2026-09-12:** de 13 medlemmar som anmält sig fram till dess fick
`stadgar_version` ändrad från `2026-09-10` till `1.0`. Texten de accepterade var
hela tiden version 1.0 — det var etiketten som var fel, inte dokumentet. Efter
rättelsen pekar varje medlemsrad på den stadgeversion som faktiskt är beslutad
och signerad.

Ändras stadgarna någon gång måste tre saker uppdateras samtidigt:
`STADGAR_VERSION` i edge-funktionen, kryssrutans etikett i `site/bli-medlem.html`
och sidhuvudet i `site/stadgar.html`. Gamla medlemsrader ska då **inte** skrivas
om — de ska fortsätta peka på den version de faktiskt accepterade.

## Medlemsnumret

Kolumnen `nummer` sätts av Postgres själv och ändras aldrig. Den som är nr 12
förblir nr 12, även om medlemmar före hen går ur. Numret delas ut när adressen
bekräftats, aldrig tidigare, så en spammare kan inte bränna serien. Det står i
välkomstmejlet, på bekräftelsesidan och på den delbara bilden, så det måste
hålla över tid.

Tidigare räknades numret fram som antalet aktiva medlemmar vid anmälan. Det gav
kollisioner: gick någon ur sjönk antalet, och nästa medlem fick en siffra som
redan tillhörde en annan. Siffran sparades inte heller någonstans.

Sekvensen ger glapp. En misslyckad insättning — oftast en adress som redan finns
— förbrukar ett nummer utan att skapa en rad. Medlem nummer tio kan alltså ha
nummer 12. Det är avsiktligt: hellre hål i serien än två personer med samma
nummer.

Numret räknas om från 1 med `alter table medlemmar alter column nummer restart
with 1`. Det får bara göras när registret är tomt.

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

## Läsa, ändra och driftsätta

Det finns ingen Supabase CLI installerad. Allt går via Management API med en
personlig token, som aldrig ska ligga i repot. Funktionen driftsätts med
`verify_jwt` avstängt och båda filerna:

```sh
SB=$(tr -d '\n ' < ~/.sb-token)
REF=kmkttmasoemqcyzkjuyv
cd supabase/functions/medlem
curl -sS -X POST -H "Authorization: Bearer $SB" \
  "https://api.supabase.com/v1/projects/$REF/functions/deploy?slug=medlem" \
  -F 'metadata={"entrypoint_path":"index.ts","name":"medlem","verify_jwt":false};type=application/json' \
  -F "file=@index.ts" -F "file=@hjalp.ts"
```

Kör testerna först: `deno test --allow-net=jsr.io hjalp_test.ts` och
`deno check index.ts`.

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
