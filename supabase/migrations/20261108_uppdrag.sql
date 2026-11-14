-- Tar uppdrag: medlemmar som visar på AI-kartan att de tar uppdrag eller säljer tjänster.
-- Migreringen uppdrag i projektet kmkttmasoemqcyzkjuyv. Bara nya tabeller: medlemmar,
-- anmalningar och den granskade funktionen medlem rörs inte.
--
-- Som i resten av projektet är RLS på utan en enda policy, så bara service_role når raderna.
-- Rättigheterna för anon och authenticated tas dessutom bort, så att inget av det här syns
-- i det automatiska REST-gränssnittet ens om någon råkar lägga till en policy.

-- En profil per medlem. Den raderas med medlemsraden, och funktionen raderar den 30 dagar
-- efter utträde. Inga personnummer: funktionen avvisar dem, och CHECK-villkoren upprepar det.
create table public.uppdrag_profiler (
  medlem_id         uuid primary key references public.medlemmar(id) on delete cascade,
  slug              text not null unique,
  namn              text not null,
  rubrik            text not null,
  lank              text not null,
  erbjuder          text not null,
  kommun            text,
  distans           boolean not null default false,
  omraden           text[] not null default '{}',
  bolag_namn        text,
  bolag_webbplats   text,
  -- Samtycket är skilt från medlemskapet. Versionen pekar på texten som kryssades i.
  samtycke_version  text not null,
  samtycke_at       timestamptz not null,
  skapad_at         timestamptz not null default now(),
  uppdaterad_at     timestamptz not null default now(),

  constraint uppdrag_slug_check     check (slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$' and length(slug) <= 60),
  constraint uppdrag_namn_check     check (length(btrim(namn)) between 1 and 60 and namn !~ '[<>@]' and position('://' in namn) = 0),
  constraint uppdrag_rubrik_check   check (length(btrim(rubrik)) between 1 and 90 and rubrik !~ '[<>]' and position('://' in rubrik) = 0),
  constraint uppdrag_lank_check     check (lank ~ '^https://[^[:space:]<>"]+$' and length(lank) <= 300),
  constraint uppdrag_erbjuder_check check (erbjuder in ('uppdrag', 'tjanster', 'bada')),
  constraint uppdrag_kommun_check   check (kommun is null or kommun ~ '^[0-9]{4}$'),
  constraint uppdrag_omraden_check  check (cardinality(omraden) <= 3),
  constraint uppdrag_bolag_check    check (bolag_namn is null or (length(btrim(bolag_namn)) between 1 and 80 and bolag_namn !~ '[<>]' and position('://' in bolag_namn) = 0)),
  constraint uppdrag_bolagwebb_check check (bolag_webbplats is null or (bolag_webbplats ~ '^https://[^[:space:]<>"]+$' and length(bolag_webbplats) <= 300)),
  -- Tio siffror i följd är ett personnummer eller ett organisationsnummer. Inget av dem hör hemma här.
  constraint uppdrag_inga_personnummer check (
    namn !~ '[0-9]{6}[-+ ]?[0-9]{4}' and rubrik !~ '[0-9]{6}[-+ ]?[0-9]{4}'
    and coalesce(bolag_namn, '') !~ '[0-9]{6}[-+ ]?[0-9]{4}'
  )
);

comment on table public.uppdrag_profiler is
  'Medlemmars profiler under Tar uppdrag på AI-kartan. Rättslig grund: samtycke, skilt från medlemskapet. Raderas på begäran direkt och 30 dagar efter utträde.';

-- Engångslänkar i mejlet. Bara hashen sparas, så en läckt tabell ger inga giltiga länkar.
create table public.uppdrag_lankar (
  token_hash  text primary key,
  medlem_id   uuid not null references public.medlemmar(id) on delete cascade,
  skapad_at   timestamptz not null default now(),
  utgar_at    timestamptz not null,
  anvand_at   timestamptz
);
create index uppdrag_lankar_medlem on public.uppdrag_lankar (medlem_id, skapad_at desc);
create index uppdrag_lankar_skapad on public.uppdrag_lankar (skapad_at);

-- En session på en timme efter att länken öppnats. Bara hashen sparas.
create table public.uppdrag_sessioner (
  session_hash text primary key,
  medlem_id    uuid not null references public.medlemmar(id) on delete cascade,
  utgar_at     timestamptz not null
);

-- Klick per profil och dag, inget om den som klickade. Sparas i 90 dagar.
create table public.uppdrag_klick (
  medlem_id uuid not null references public.medlemmar(id) on delete cascade,
  dag       date not null,
  antal     integer not null default 0,
  primary key (medlem_id, dag)
);

-- Hastighetsgräns per nätverk, som anmalan_forsok men skild från den, så att ett skript
-- här aldrig kan hindra någon från att bli medlem.
create table public.uppdrag_forsok (
  ip_hash text not null,
  at      timestamptz not null default now()
);
create index uppdrag_forsok_ip_at on public.uppdrag_forsok (ip_hash, at desc);
create index uppdrag_forsok_at on public.uppdrag_forsok (at);

alter table public.uppdrag_profiler  enable row level security;
alter table public.uppdrag_lankar    enable row level security;
alter table public.uppdrag_sessioner enable row level security;
alter table public.uppdrag_klick     enable row level security;
alter table public.uppdrag_forsok    enable row level security;

-- Det som syns på kartan: bara publika fält, och bara för aktiva medlemmar som är personer.
-- En medlem som går ur försvinner härifrån i samma stund som utträdet registreras.
create view public.uppdrag_publika with (security_invoker = on) as
  select p.slug, p.namn, p.rubrik, p.lank, p.erbjuder, p.kommun, p.distans, p.omraden,
         p.bolag_namn, p.bolag_webbplats, p.uppdaterad_at
  from public.uppdrag_profiler p
  join public.medlemmar m on m.id = p.medlem_id
  where m.uttradd_at is null and m.typ = 'fysisk';

-- Räknar ett klick och ger tillbaka länken i ett anrop. Ger null för en okänd eller dold profil.
create function public.uppdrag_rakna_klick(p_slug text) returns text
language sql
set search_path = public
as $$
  with p as (
    select p.medlem_id, p.lank
    from public.uppdrag_profiler p
    join public.medlemmar m on m.id = p.medlem_id
    where p.slug = p_slug and m.uttradd_at is null and m.typ = 'fysisk'
  ), ny as (
    insert into public.uppdrag_klick (medlem_id, dag, antal)
    select medlem_id, (now() at time zone 'Europe/Stockholm')::date, 1 from p
    on conflict (medlem_id, dag) do update set antal = public.uppdrag_klick.antal + 1
    returning 1
  )
  select lank from p;
$$;

revoke all on public.uppdrag_profiler, public.uppdrag_lankar, public.uppdrag_sessioner,
  public.uppdrag_klick, public.uppdrag_forsok, public.uppdrag_publika from anon, authenticated;
revoke execute on function public.uppdrag_rakna_klick(text) from public, anon, authenticated;
grant execute on function public.uppdrag_rakna_klick(text) to service_role;
