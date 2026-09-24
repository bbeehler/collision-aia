-- Check and Declare: consumer badge checks, consumer concerns, reviewer management.
-- Run once in the Supabase SQL Editor after 001 and 002.

-- Directory now includes the postal code so consumers can search by it.
drop function if exists public.get_directory();
create function public.get_directory()
returns table (facility_id uuid, name text, street text, city text, province text, postal text, phone text, website text,
               declared_at timestamptz, expires_at timestamptz, code text, credentials text[])
language sql stable security definer set search_path = public as $$
  select f.id, coalesce(nullif(f.operating_name, ''), f.legal_name), f.street, f.city, f.province, f.postal, f.phone, f.website,
         d.declared_at, d.expires_at, d.code,
         array(select case when c.program = 'other' then coalesce(c.other_name, 'Other') else c.program end
                 from public.credential_claims c where c.facility_id = f.id order by c.program)
    from public.facilities f
    join public.declarations d on d.facility_id = f.id and d.withdrawn_at is null and d.expires_at > now()
   where public.all_yes(f.answers)
     and exists (select 1 from public.credential_claims c where c.facility_id = f.id)
     and not exists (select 1 from public.credential_claims c where c.facility_id = f.id
                      and (c.status <> 'confirmed'
                           or (c.cert_expiry is not null and c.cert_expiry < current_date)
                           or (c.recheck_at is not null and c.recheck_at < now())))
   order by 2;
$$;
grant execute on function public.get_directory() to anon, authenticated;

-- Anyone can check whether a badge ID is genuine and current.
create or replace function public.check_badge(p_code text)
returns table (code text, status text, name text, city text, province text, declared_at timestamptz, expires_at timestamptz,
               withdrawn_at timestamptz, credentials text[])
language sql stable security definer set search_path = public as $$
  select d.code,
         case when d.withdrawn_at is not null then 'withdrawn'
              when d.expires_at <= now() then 'expired'
              when exists (select 1 from public.get_directory() g where g.code = d.code) then 'active'
              else 'not_active' end,
         coalesce(nullif(f.operating_name, ''), f.legal_name), f.city, f.province, d.declared_at, d.expires_at, d.withdrawn_at,
         array(select case when c.program = 'other' then coalesce(c.other_name, 'Other') else c.program end
                 from public.credential_claims c where c.facility_id = f.id and c.status = 'confirmed' order by c.program)
    from public.declarations d join public.facilities f on f.id = d.facility_id
   where upper(d.code) = upper(trim(p_code))
   limit 1;
$$;
grant execute on function public.check_badge(text) to anon, authenticated;

-- Consumer concerns about a listed shop. Submitted through a function; only reviewers can read them.
create table if not exists public.concerns (
  id bigint generated always as identity primary key,
  facility_id uuid references public.facilities(id) on delete set null,
  facility_name text,
  badge_code text,
  submitted_at timestamptz not null default now(),
  reporter_name text,
  reporter_contact text,
  message text not null,
  status text not null default 'new' check (status in ('new', 'reviewing', 'closed')),
  admin_note text,
  updated_at timestamptz,
  updated_by uuid
);
alter table public.concerns enable row level security;
drop policy if exists "reviewers read concerns" on public.concerns;
drop policy if exists "reviewers update concerns" on public.concerns;
create policy "reviewers read concerns" on public.concerns for select using (public.is_admin());
create policy "reviewers update concerns" on public.concerns for update using (public.is_admin());

create or replace function public.submit_concern(p_facility uuid, p_name text, p_contact text, p_message text)
returns text language plpgsql security definer set search_path = public as $$
declare fname text; fcode text;
begin
  if p_message is null or char_length(trim(p_message)) < 10 then return 'too_short'; end if;
  if (select count(*) from public.concerns where submitted_at > now() - interval '1 hour') > 200 then return 'busy'; end if;
  select coalesce(nullif(f.operating_name, ''), f.legal_name), d.code into fname, fcode
    from public.facilities f left join public.declarations d on d.facility_id = f.id and d.withdrawn_at is null
   where f.id = p_facility order by d.declared_at desc limit 1;
  if fname is null then return 'no_facility'; end if;
  insert into public.concerns (facility_id, facility_name, badge_code, reporter_name, reporter_contact, message)
  values (p_facility, fname, fcode, left(trim(p_name), 120), left(trim(p_contact), 200), left(trim(p_message), 4000));
  return 'ok';
end $$;
grant execute on function public.submit_concern(uuid, text, text, text) to anon, authenticated;

-- Reviewer management from the app (reviewers only).
create or replace function public.list_reviewers()
returns table (user_id uuid, email text, added_at timestamptz)
language plpgsql stable security definer set search_path = public, auth as $$
begin
  if not public.is_admin() then raise exception 'Reviewers only'; end if;
  return query select a.user_id, u.email::text, a.created_at from public.admins a join auth.users u on u.id = a.user_id order by u.email;
end $$;

create or replace function public.add_reviewer(p_email text)
returns text language plpgsql security definer set search_path = public, auth as $$
declare uid uuid;
begin
  if not public.is_admin() then raise exception 'Reviewers only'; end if;
  select id into uid from auth.users where lower(email) = lower(trim(p_email));
  if uid is null then return 'no_account'; end if;
  insert into public.admins (user_id) values (uid) on conflict (user_id) do nothing;
  return 'added';
end $$;

create or replace function public.remove_reviewer(p_user uuid)
returns text language plpgsql security definer set search_path = public as $$
begin
  if not public.is_admin() then raise exception 'Reviewers only'; end if;
  if p_user = auth.uid() then return 'self'; end if;
  delete from public.admins where user_id = p_user;
  return 'removed';
end $$;

grant execute on function public.list_reviewers() to authenticated;
grant execute on function public.add_reviewer(text) to authenticated;
grant execute on function public.remove_reviewer(uuid) to authenticated;
