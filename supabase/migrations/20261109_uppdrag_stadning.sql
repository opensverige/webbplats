-- Städningen för Tar uppdrag, varje natt oavsett trafik. Migreringen uppdrag_stadning.
-- Funktionen uppdrag städar också ibland, men bara när någon skriver. Utan det här kunde en
-- profil ligga kvar längre än de 30 dagar efter utträde som /integritet på kartan lovar.
create extension if not exists pg_cron;

create function public.uppdrag_stada() returns void
language sql
set search_path = public
as $$
  delete from public.uppdrag_forsok where at < now() - interval '1 day';
  delete from public.uppdrag_lankar where utgar_at < now() - interval '1 day';
  delete from public.uppdrag_sessioner where utgar_at < now();
  delete from public.uppdrag_klick where dag < (now() at time zone 'Europe/Stockholm')::date - 90;
  delete from public.uppdrag_klick where medlem_id in
    (select id from public.medlemmar where uttradd_at < now() - interval '30 days');
  delete from public.uppdrag_profiler where medlem_id in
    (select id from public.medlemmar where uttradd_at < now() - interval '30 days');
$$;

revoke execute on function public.uppdrag_stada() from public, anon, authenticated;

select cron.schedule('uppdrag-stada', '17 3 * * *', 'select public.uppdrag_stada()');
