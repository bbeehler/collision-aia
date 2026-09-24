-- Check and Declare: super admins, revoking (suspending) and deleting facilities.
-- Run once in the Supabase SQL Editor after 001, 002 and 003.

-- Staff roles. Everyone who is staff when this runs becomes a super admin (at setup, that's you).
alter table public.admins add column if not exists role text not null default 'reviewer';
alter table public.admins drop constraint if exists admins_role_check;
alter table public.admins add constraint admins_role_check check (role in ('reviewer', 'super_admin'));
update public.admins set role = 'super_admin';

create or replace function public.is_super_admin() returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.admins where user_id = auth.uid() and role = 'super_admin');
$$;
grant execute on function public.is_super_admin() to anon, authenticated;

-- Revoked (suspended) facilities
alter table public.facilities add column if not exists suspended_at timestamptz;
alter table public.facilities add column if not exists suspended_reason text;

create or replace function public.facilities_guard() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  new.updated_at := now();
  if auth.uid() is not null and not public.is_super_admin() then
    if tg_op = 'INSERT' then
      new.suspended_at := null; new.suspended_reason := null;
    else
      new.suspended_at := old.suspended_at; new.suspended_reason := old.suspended_reason;
    end if;
  end if;
  if tg_op = 'UPDATE' and auth.uid() is not null and not public.is_admin() then
    new.owner_id := old.owner_id;
  end if;
  return new;
end $$;

create or replace function public.declarations_guard() returns trigger
language plpgsql security definer set search_path = public as $$
declare a jsonb; susp timestamptz;
begin
  if tg_op = 'INSERT' then
    select answers, suspended_at into a, susp from public.facilities where id = new.facility_id;
    if susp is not null then
      raise exception 'This facility has been revoked by AIA Canada. Contact AIA Canada for details.' using errcode = 'check_violation';
    end if;
    if not public.all_yes(a) then
      raise exception 'Every requirement must be answered yes before declaring.' using errcode = 'check_violation';
    end if;
    if auth.uid() is not null and not public.is_admin() then
      new.declared_at := now();
      new.expires_at := now() + interval '365 days';
      new.withdrawn_at := null; new.withdrawn_reason := null;
      new.signed_by := auth.uid();
    end if;
    update public.declarations set withdrawn_at = now(), withdrawn_reason = 'Replaced by a new declaration'
     where facility_id = new.facility_id and withdrawn_at is null;
    return new;
  end if;
  if auth.uid() is not null and not public.is_admin() then
    new.facility_id := old.facility_id; new.code := old.code; new.signer := old.signer; new.title := old.title;
    new.declared_at := old.declared_at; new.expires_at := old.expires_at; new.statement_version := old.statement_version;
    new.signed_by := old.signed_by;
    if old.withdrawn_at is not null then
      new.withdrawn_at := old.withdrawn_at; new.withdrawn_reason := old.withdrawn_reason;
    end if;
  end if;
  return new;
end $$;

-- Directory leaves out revoked facilities
create or replace function public.get_directory()
returns table (facility_id uuid, name text, street text, city text, province text, postal text, phone text, website text,
               declared_at timestamptz, expires_at timestamptz, code text, credentials text[])
language sql stable security definer set search_path = public as $$
  select f.id, coalesce(nullif(f.operating_name, ''), f.legal_name), f.street, f.city, f.province, f.postal, f.phone, f.website,
         d.declared_at, d.expires_at, d.code,
         array(select case when c.program = 'other' then coalesce(c.other_name, 'Other') else c.program end
                 from public.credential_claims c where c.facility_id = f.id order by c.program)
    from public.facilities f
    join public.declarations d on d.facility_id = f.id and d.withdrawn_at is null and d.expires_at > now()
   where f.suspended_at is null
     and public.all_yes(f.answers)
     and exists (select 1 from public.credential_claims c where c.facility_id = f.id)
     and not exists (select 1 from public.credential_claims c where c.facility_id = f.id
                      and (c.status <> 'confirmed'
                           or (c.cert_expiry is not null and c.cert_expiry < current_date)
                           or (c.recheck_at is not null and c.recheck_at < now())))
   order by 2;
$$;

create or replace function public.suspend_facility(p_facility uuid, p_reason text)
returns text language plpgsql security definer set search_path = public as $$
begin
  if not public.is_super_admin() then raise exception 'Super admins only'; end if;
  if p_reason is null or trim(p_reason) = '' then return 'reason_required'; end if;
  update public.facilities set suspended_at = now(), suspended_reason = trim(p_reason) where id = p_facility;
  update public.declarations set withdrawn_at = now(), withdrawn_reason = 'Revoked by AIA Canada: ' || trim(p_reason)
   where facility_id = p_facility and withdrawn_at is null;
  insert into public.facility_history (facility_id, type, detail) values (p_facility, 'facility_revoked', trim(p_reason));
  return 'ok';
end $$;

create or replace function public.reinstate_facility(p_facility uuid)
returns text language plpgsql security definer set search_path = public as $$
begin
  if not public.is_super_admin() then raise exception 'Super admins only'; end if;
  update public.facilities set suspended_at = null, suspended_reason = null where id = p_facility;
  insert into public.facility_history (facility_id, type, detail) values (p_facility, 'facility_reinstated', 'Shop can declare again');
  return 'ok';
end $$;

create or replace function public.delete_facility(p_facility uuid)
returns text language plpgsql security definer set search_path = public as $$
begin
  if not public.is_super_admin() then raise exception 'Super admins only'; end if;
  delete from public.facilities where id = p_facility;   -- answers, credentials, declarations, runs and history go with it
  return 'deleted';
end $$;

-- Staff management: super admins only
drop function if exists public.list_reviewers();
create function public.list_reviewers()
returns table (user_id uuid, email text, role text, added_at timestamptz)
language plpgsql stable security definer set search_path = public, auth as $$
begin
  if not public.is_super_admin() then raise exception 'Super admins only'; end if;
  return query select a.user_id, u.email::text, a.role, a.created_at from public.admins a join auth.users u on u.id = a.user_id order by u.email;
end $$;

create or replace function public.add_staff(p_email text, p_role text)
returns text language plpgsql security definer set search_path = public, auth as $$
declare uid uuid;
begin
  if not public.is_super_admin() then raise exception 'Super admins only'; end if;
  if p_role not in ('reviewer', 'super_admin') then return 'bad_role'; end if;
  select id into uid from auth.users where lower(email) = lower(trim(p_email));
  if uid is null then return 'no_account'; end if;
  insert into public.admins (user_id, role) values (uid, p_role) on conflict (user_id) do update set role = excluded.role;
  return 'added';
end $$;

create or replace function public.add_reviewer(p_email text)
returns text language sql security definer set search_path = public as $$ select public.add_staff(p_email, 'reviewer'); $$;

create or replace function public.set_staff_role(p_user uuid, p_role text)
returns text language plpgsql security definer set search_path = public as $$
begin
  if not public.is_super_admin() then raise exception 'Super admins only'; end if;
  if p_role not in ('reviewer', 'super_admin') then return 'bad_role'; end if;
  if p_user = auth.uid() and p_role <> 'super_admin' then return 'self'; end if;
  update public.admins set role = p_role where user_id = p_user;
  return 'ok';
end $$;

create or replace function public.remove_reviewer(p_user uuid)
returns text language plpgsql security definer set search_path = public as $$
begin
  if not public.is_super_admin() then raise exception 'Super admins only'; end if;
  if p_user = auth.uid() then return 'self'; end if;
  delete from public.admins where user_id = p_user;
  return 'removed';
end $$;

grant execute on function public.list_reviewers() to authenticated;
grant execute on function public.add_staff(text, text) to authenticated;
grant execute on function public.add_reviewer(text) to authenticated;
grant execute on function public.set_staff_role(uuid, text) to authenticated;
grant execute on function public.remove_reviewer(uuid) to authenticated;
grant execute on function public.suspend_facility(uuid, text) to authenticated;
grant execute on function public.reinstate_facility(uuid) to authenticated;
grant execute on function public.delete_facility(uuid) to authenticated;
