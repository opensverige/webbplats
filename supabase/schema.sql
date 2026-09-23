-- Schemat för medlemsregistret, avläst från projektet kmkttmasoemqcyzkjuyv
-- 2026-09-11 och kompletterat 2026-09-24. Ögonblicksbild, inte en migrering —
-- tabellerna finns redan. Tillägget 2026-09-24 ligger som migreringen
-- anmalningar_och_utskick i projektet.
--
-- Registret är föreningens röstlängd enligt § 8. Databasen upprepar med flit
-- valideringen som edge-funktionen gör, så en felskriven insert inte kan
-- smita in vid sidan av funktionen.

create table public.medlemmar (
  id                    uuid primary key default gen_random_uuid(),
  -- Permanent medlemsnummer. Att i stället räkna rader gav kollisioner:
  -- går någon ur sjunker antalet, och nästa medlem får en siffra som
  -- redan är tagen. Sekvensen ger glapp när en insättning misslyckas, och
  -- det är priset för att två personer aldrig kan dela nummer.
  nummer                bigint generated always as identity,
  namn                  text not null,
  epost                 text not null,
  typ                   text not null default 'fysisk',
  firmanamn             text,
  orgnr                 text,
  foretradare           text,
  discord               text,
  stadgar_version       text not null,
  stadgar_accepterad_at timestamptz not null default now(),
  kalla                 text not null default 'webb',
  anmald_at             timestamptz not null default now(),
  -- Utträde tömmer inte raden. Den som varit medlem ska gå att hitta i en
  -- gammal röstlängd, och unika e-postindexet gäller bara aktiva.
  uttradd_at            timestamptz,

  constraint medlemmar_namn_check  check (length(btrim(namn)) > 0),
  constraint medlemmar_epost_check check (position('@' in epost) > 1),
  constraint medlemmar_typ_check   check (typ = any (array['fysisk', 'juridisk'])),
  constraint medlemmar_kalla_check check (kalla = any (array['webb', 'discord'])),
  constraint medlemmar_nummer_unik unique (nummer),
  -- Juridisk person röstar genom en fysisk företrädare, § 8.
  constraint juridisk_kraver_foretradare
    check (typ <> 'juridisk' or (firmanamn is not null and foretradare is not null))
);

-- Samma adress får bli medlem igen efter utträde, men inte vara medlem två
-- gånger samtidigt. Ger felkod 23505 som funktionen översätter till 409.
create unique index medlemmar_epost_aktiv
  on public.medlemmar (lower(epost))
  where uttradd_at is null;

create index medlemmar_anmald_at on public.medlemmar (anmald_at desc);

-- RLS på utan en enda policy = ingen når tabellen utom service_role, som
-- bara edge-funktionen har. Registret är därmed inte läsbart utifrån.
alter table public.medlemmar enable row level security;

-- Hastighetsbegränsning för anmälningsformuläret. Ingen IP-adress lagras,
-- bara sha256(ANMALAN_SALT + ip). Rader äldre än ett dygn städas bort av
-- funktionen, eftersom projektet inte har någon cron.
create table public.anmalan_forsok (
  ip_hash text not null,
  at      timestamptz not null default now()
);

create index anmalan_forsok_ip_at on public.anmalan_forsok (ip_hash, at desc);
create index anmalan_forsok_at    on public.anmalan_forsok (at);

alter table public.anmalan_forsok enable row level security;

-- Väntande anmälningar. En rad här är ingen medlem: först när adressen
-- bekräftats via engångslänken skapas raden i medlemmar och numret delas ut.
-- Bara hashen av token sparas, så en läckt tabell ger inga giltiga länkar.
create table public.anmalningar (
  id                uuid primary key default gen_random_uuid(),
  token_hash        text not null unique,
  namn              text not null,
  epost             text not null,
  typ               text not null default 'fysisk',
  firmanamn         text,
  orgnr             text,
  foretradare       text,
  discord           text,
  kalla             text not null default 'webb',
  stadgar_version   text not null,
  skapad_at         timestamptz not null default now(),
  utgar_at          timestamptz not null,
  bekraftad_at      timestamptz,
  -- Omsändning: antal skickade bekräftelsemejl och när det senaste gick.
  skickade          integer not null default 1,
  senast_skickad_at timestamptz not null default now(),

  constraint anmalningar_namn_check  check (length(btrim(namn)) > 0),
  constraint anmalningar_epost_check check (position('@' in epost) > 1),
  constraint anmalningar_typ_check   check (typ = any (array['fysisk', 'juridisk'])),
  constraint anmalningar_kalla_check check (kalla = any (array['webb', 'discord'])),
  constraint anmalningar_juridisk_kraver_foretradare
    check (typ <> 'juridisk' or (firmanamn is not null and foretradare is not null))
);

comment on table public.anmalningar is
  'Obekräftade medlemsanmälningar. Raderas sju dagar efter att länken gått ut. Rättslig grund: avtal (åtgärd på begäran före medlemskap).';

-- Högst en väntande anmälan per adress. Skickas formuläret igen roteras
-- token på den befintliga raden i stället för att en ny skapas.
create unique index anmalningar_epost_vantande
  on public.anmalningar (lower(epost))
  where bekraftad_at is null;

create index anmalningar_utgar_at on public.anmalningar (utgar_at);

alter table public.anmalningar enable row level security;

-- En rad per skickat mejl, så funktionen kan hålla sig under Resends
-- dagstak. Rader äldre än ett dygn städas bort av funktionen.
create table public.utskick (
  at timestamptz not null default now()
);

create index utskick_at on public.utskick (at);

alter table public.utskick enable row level security;
