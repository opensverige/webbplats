-- Tar uppdrag: kunskaper som medlemmen skriver själv. Migreringen uppdrag_kunskaper i projektet
-- kmkttmasoemqcyzkjuyv.
--
-- Kunskaperna är korta ord som RAG eller Python, högst sex och högst 24 tecken var. Funktionen
-- uppdrag prövar dem. Tabellen håller taket även om något skulle skriva förbi funktionen.
-- Bilden är frivillig från samma version av funktionen: kolumnen bild fick redan vara null.

alter table public.uppdrag_profiler add column kunskaper text[] not null default '{}';
alter table public.uppdrag_profiler add constraint uppdrag_kunskaper_check check (
  cardinality(kunskaper) <= 6 and char_length(array_to_string(kunskaper, '')) <= 144
);

-- Vyn får kolumnen sist. Den byggs om på plats, så rättigheterna står kvar.
create or replace view public.uppdrag_publika with (security_invoker = on) as
  select p.slug, p.namn, p.rubrik, p.lank, p.erbjuder, p.kommun, p.distans, p.omraden,
         p.bolag_namn, p.bolag_webbplats, p.uppdaterad_at, p.bild, p.kunskaper
  from public.uppdrag_profiler p
  join public.medlemmar m on m.id = p.medlem_id
  where m.uttradd_at is null and m.typ = 'fysisk';

revoke all on public.uppdrag_publika from anon, authenticated;
