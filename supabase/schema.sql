-- Schemat för medlemsregistret, avläst från projektet kmkttmasoemqcyzkjuyv
-- 2026-09-11. Ögonblicksbild, inte en migrering — tabellen finns redan.
--
-- Registret är föreningens röstlängd enligt § 8. Databasen upprepar med flit
-- valideringen som edge-funktionen gör, så en felskriven insert inte kan
-- smita in vid sidan av funktionen.

create table public.medlemmar (
  id                    uuid primary key default gen_random_uuid(),
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
