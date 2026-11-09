-- Tar uppdrag: medlemmens egen bild i stället för en tecknad figur. Migreringen uppdrag_bild i
-- projektet kmkttmasoemqcyzkjuyv. Figuren från uppdrag_figur tas bort.
--
-- Bilderna ligger i lagringen uppdrag-bilder, som inte är publik och inte går att lista. Bara
-- funktionen uppdrag når den, med service_role, och den lämnar ut en bild bara för en profil som
-- syns i listan. Webbläsaren beskär och kodar om bilden innan den skickas, så metadata som plats
-- följer inte med, och funktionen stoppar en bild som ändå bär EXIF eller XMP.

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('uppdrag-bilder', 'uppdrag-bilder', false, 307200, array['image/webp', 'image/jpeg']);

-- Vyn läser kolumnen som tas bort, så den byggs om.
drop view public.uppdrag_publika;

alter table public.uppdrag_profiler drop constraint uppdrag_figur_check;
alter table public.uppdrag_profiler drop column figur;

-- Filnamnet i lagringen: ett slumpat uuid och formatet. Null för en profil från innan bilden fanns.
alter table public.uppdrag_profiler add column bild text;
alter table public.uppdrag_profiler add constraint uppdrag_bild_check check (
  bild is null or bild ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.(webp|jpg)$'
);

create view public.uppdrag_publika with (security_invoker = on) as
  select p.slug, p.namn, p.rubrik, p.lank, p.erbjuder, p.kommun, p.distans, p.omraden,
         p.bolag_namn, p.bolag_webbplats, p.uppdaterad_at, p.bild
  from public.uppdrag_profiler p
  join public.medlemmar m on m.id = p.medlem_id
  where m.uttradd_at is null and m.typ = 'fysisk';

revoke all on public.uppdrag_publika from anon, authenticated;
