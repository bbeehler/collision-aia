-- Check and Declare: schema, security rules and the public directory.
-- Run once in the Supabase SQL editor (or with `supabase db push`).

create extension if not exists pgcrypto;

-- ---------------------------------------------------------------------------
-- Reviewers (AIA Canada staff). Add a reviewer with:
--   insert into public.admins (user_id) select id from auth.users where email = 'name@aiacanada.com';
-- ---------------------------------------------------------------------------
create table if not exists public.admins (
  user_id uuid primary key references auth.users(id) on delete cascade,
  created_at timestamptz not null default now()
);
alter table public.admins enable row level security;

create or replace function public.is_admin() returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.admins where user_id = auth.uid());
$$;

drop policy if exists "read own admin row" on public.admins;
create policy "read own admin row" on public.admins for select using (user_id = auth.uid());

-- ---------------------------------------------------------------------------
-- Requirement IDs from AIA Canada's Statement. Keep in step with app/config.py.
-- ---------------------------------------------------------------------------
create or replace function public.required_ids() returns text[] language sql immutable as $$
  select array['B1','B2','B3','B4','T1','T2','F1','F2','F3','F4','F5','F6','F7','F8','F9','F10','F11','F12','F13','F14','F15',
               'P1','P2','P3','P4','P5','P6'];
$$;
create or replace function public.all_yes(a jsonb) returns boolean language sql immutable as $$
  select not exists (select 1 from unnest(public.required_ids()) r where coalesce(a ->> r, '') <> 'yes');
$$;

-- ---------------------------------------------------------------------------
-- Tables
-- ---------------------------------------------------------------------------
create table if not exists public.facilities (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  legal_name text not null,
  operating_name text,
  street text not null default '',
  city text not null default '',
  province text check (province is null or province in ('AB','BC','MB','NB','NL','NS','NT','NU','ON','PE','QC','SK','YT')),
  postal text,
  phone text,
  website text,
  rep_name text,
  rep_title text,
  rep_email text,
  scope text[] not null default '{}',
  answers jsonb not null default '{}'::jsonb,       -- {"B1": "yes" | "no" | "unsure", ...}
  gap_plan jsonb,                                   -- latest AI gap plan
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists facilities_owner on public.facilities (owner_id);

create table if not exists public.credential_claims (
  id uuid primary key default gen_random_uuid(),
  facility_id uuid not null references public.facilities(id) on delete cascade,
  program text not null,                            -- program ID, e.g. 'ford', 'gm', 'icar-gold', 'other'
  other_name text,
  program_ref text,                                 -- shop's program or facility ID
  cert_number text,
  cert_expiry date,
  status text not null default 'pending' check (status in ('pending','review','confirmed','not_found')),
  review_reason text,
  source text,
  note text,                                        -- shown to the shop
  reviewed_at timestamptz,
  reviewed_by text,                                 -- reviewer user id, or 'verifier'
  recheck_at timestamptz,
  last_auto_check_at timestamptz,
  next_auto_check_at timestamptz,
  submitted_at timestamptz not null default now(),
  created_at timestamptz not null default now()
);
create index if not exists claims_facility on public.credential_claims (facility_id);
create index if not exists claims_due on public.credential_claims (status, program, recheck_at, next_auto_check_at);

create table if not exists public.declarations (
  id uuid primary key default gen_random_uuid(),
  facility_id uuid not null references public.facilities(id) on delete cascade,
  code text not null unique default ('AIA-CD-' || upper(substr(replace(gen_random_uuid()::text, '-', ''), 1, 6))),
  signer text not null,
  title text,
  declared_at timestamptz not null default now(),
  expires_at timestamptz not null default now() + interval '365 days',
  withdrawn_at timestamptz,
  withdrawn_reason text,
  statement_version text not null default '2025 Statement (published September 2025)',
  signed_by uuid default auth.uid()
);
create index if not exists declarations_facility on public.declarations (facility_id, declared_at desc);

create table if not exists public.verification_runs (
  id bigint generated always as identity primary key,
  claim_id uuid not null references public.credential_claims(id) on delete cascade,
  facility_id uuid not null references public.facilities(id) on delete cascade,
  ran_at timestamptz not null default now(),
  outcome text not null,
  reason text not null,
  note text,
  match_score int,
  match_identity text,
  matched_listing jsonb,
  searches jsonb,
  evidence_paths text[]
);
create index if not exists runs_claim on public.verification_runs (claim_id, ran_at desc);

create table if not exists public.facility_history (
  id bigint generated always as identity primary key,
  facility_id uuid not null references public.facilities(id) on delete cascade,
  at timestamptz not null default now(),
  actor uuid default auth.uid(),
  type text not null,
  detail text
);
create index if not exists history_facility on public.facility_history (facility_id, at desc);

-- ---------------------------------------------------------------------------
-- Integrity rules enforced in the database, whatever the client sends
-- ---------------------------------------------------------------------------
create or replace function public.owns_facility(fid uuid) returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.facilities where id = fid and owner_id = auth.uid());
$$;

create or replace function public.facilities_guard() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  new.updated_at := now();
  if tg_op = 'UPDATE' and auth.uid() is not null and not public.is_admin() then
    new.owner_id := old.owner_id;                   -- shops can't hand a facility to someone else
  end if;
  return new;
end $$;
drop trigger if exists facilities_guard on public.facilities;
create trigger facilities_guard before insert or update on public.facilities for each row execute function public.facilities_guard();

-- Changing any answer away from "yes" withdraws the active declaration.
create or replace function public.facilities_withdraw_on_change() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if new.answers is distinct from old.answers and not public.all_yes(new.answers) then
    update public.declarations
       set withdrawn_at = now(), withdrawn_reason = 'A requirement answer changed from yes'
     where facility_id = new.id and withdrawn_at is null and expires_at > now();
  end if;
  return new;
end $$;
drop trigger if exists facilities_withdraw_on_change on public.facilities;
create trigger facilities_withdraw_on_change after update on public.facilities for each row execute function public.facilities_withdraw_on_change();

-- Shops can add, edit and remove claims, but only reviewers and the verifier set a review outcome.
create or replace function public.claims_guard() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if auth.uid() is null or public.is_admin() then
    return new;                                     -- service role (verifier) or reviewer
  end if;
  new.status := 'pending';
  new.source := null; new.note := null; new.review_reason := null;
  new.reviewed_at := null; new.reviewed_by := null; new.recheck_at := null; new.next_auto_check_at := null;
  new.last_auto_check_at := case when tg_op = 'UPDATE' then old.last_auto_check_at else null end;
  new.submitted_at := now();
  return new;
end $$;
drop trigger if exists claims_guard on public.credential_claims;
create trigger claims_guard before insert or update on public.credential_claims for each row execute function public.claims_guard();

-- Declarations: only when every requirement is yes; dates are set by the server; shops can only withdraw.
create or replace function public.declarations_guard() returns trigger
language plpgsql security definer set search_path = public as $$
declare a jsonb;
begin
  if tg_op = 'INSERT' then
    select answers into a from public.facilities where id = new.facility_id;
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
drop trigger if exists declarations_guard on public.declarations;
create trigger declarations_guard before insert or update on public.declarations for each row execute function public.declarations_guard();

-- ---------------------------------------------------------------------------
-- Row-level security
-- ---------------------------------------------------------------------------
alter table public.facilities enable row level security;
alter table public.credential_claims enable row level security;
alter table public.declarations enable row level security;
alter table public.verification_runs enable row level security;
alter table public.facility_history enable row level security;

drop policy if exists "facilities read" on public.facilities;
drop policy if exists "facilities insert" on public.facilities;
drop policy if exists "facilities update" on public.facilities;
drop policy if exists "facilities delete" on public.facilities;
create policy "facilities read" on public.facilities for select using (owner_id = auth.uid() or public.is_admin());
create policy "facilities insert" on public.facilities for insert with check (owner_id = auth.uid());
create policy "facilities update" on public.facilities for update using (owner_id = auth.uid() or public.is_admin());
create policy "facilities delete" on public.facilities for delete using (owner_id = auth.uid());

drop policy if exists "claims read" on public.credential_claims;
drop policy if exists "claims insert" on public.credential_claims;
drop policy if exists "claims update" on public.credential_claims;
drop policy if exists "claims delete" on public.credential_claims;
create policy "claims read" on public.credential_claims for select using (public.owns_facility(facility_id) or public.is_admin());
create policy "claims insert" on public.credential_claims for insert with check (public.owns_facility(facility_id));
create policy "claims update" on public.credential_claims for update using (public.owns_facility(facility_id) or public.is_admin());
create policy "claims delete" on public.credential_claims for delete using (public.owns_facility(facility_id) or public.is_admin());

drop policy if exists "declarations read" on public.declarations;
drop policy if exists "declarations insert" on public.declarations;
drop policy if exists "declarations update" on public.declarations;
create policy "declarations read" on public.declarations for select using (public.owns_facility(facility_id) or public.is_admin());
create policy "declarations insert" on public.declarations for insert with check (public.owns_facility(facility_id));
create policy "declarations update" on public.declarations for update using (public.owns_facility(facility_id) or public.is_admin());

drop policy if exists "runs read" on public.verification_runs;
create policy "runs read" on public.verification_runs for select using (public.is_admin());

drop policy if exists "history read" on public.facility_history;
drop policy if exists "history insert" on public.facility_history;
create policy "history read" on public.facility_history for select using (public.owns_facility(facility_id) or public.is_admin());
create policy "history insert" on public.facility_history for insert with check (public.owns_facility(facility_id) or public.is_admin());

-- ---------------------------------------------------------------------------
-- Public directory: facilities with an active badge. Safe to call without signing in.
-- ---------------------------------------------------------------------------
create or replace function public.get_directory()
returns table (facility_id uuid, name text, street text, city text, province text, phone text, website text,
               declared_at timestamptz, expires_at timestamptz, code text, credentials text[])
language sql stable security definer set search_path = public as $$
  select f.id, coalesce(nullif(f.operating_name, ''), f.legal_name), f.street, f.city, f.province, f.phone, f.website,
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

grant execute on function public.is_admin() to anon, authenticated;
grant execute on function public.get_directory() to anon, authenticated;

-- ---------------------------------------------------------------------------
-- Screenshots from automated checks (private; reviewers only)
-- ---------------------------------------------------------------------------
insert into storage.buckets (id, name, public) values ('verification-evidence', 'verification-evidence', false)
on conflict (id) do nothing;
drop policy if exists "reviewers read evidence" on storage.objects;
create policy "reviewers read evidence" on storage.objects for select
  using (bucket_id = 'verification-evidence' and public.is_admin());
