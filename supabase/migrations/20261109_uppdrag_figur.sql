-- Tar uppdrag: medlemmen väljer en tecknad figur som står på kortet i stället för en bild.
-- Migreringen uppdrag_figur i projektet kmkttmasoemqcyzkjuyv.
--
-- Figuren är ett id ur kartans egen lista, f01, f02 och så vidare. Bilderna ligger på kartan,
-- inte här, och ingen bild på medlemmen sparas någonstans. Saknas figur väljer kartan en
-- utifrån profilens adress, så äldre profiler får en figur utan att något behöver fyllas i.
-- Villkoret är ett mönster och inte en lista, så att fler figurer inte kräver en ny migrering.

alter table public.uppdrag_profiler add column figur text;
alter table public.uppdrag_profiler add constraint uppdrag_figur_check
  check (figur is null or figur ~ '^f[0-9]{2}$');

-- Vyn får figuren sist. security_invoker skrivs ut igen, så att den inte hänger på att
-- create or replace behåller den.
create or replace view public.uppdrag_publika with (security_invoker = on) as
  select p.slug, p.namn, p.rubrik, p.lank, p.erbjuder, p.kommun, p.distans, p.omraden,
         p.bolag_namn, p.bolag_webbplats, p.uppdaterad_at, p.figur
  from public.uppdrag_profiler p
  join public.medlemmar m on m.id = p.medlem_id
  where m.uttradd_at is null and m.typ = 'fysisk';

revoke all on public.uppdrag_publika from anon, authenticated;
