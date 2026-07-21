-- Source pattern: 20260718204703_create_profiles.sql (RLS/policy shape) +
-- 20260718211140_grant_profiles_privileges.sql (GRANT shape), adapted per
-- RESEARCH.md Pattern 1 (holdings as an owner-scoped child table, not a
-- jsonb blob) and Pattern 2 (CHECK constraints, not native ENUMs).
--
-- Extends public.profiles with six nullable investor-profile columns
-- (D-01/D-02/D-03/D-04/D-05) and creates public.holdings as a new
-- owner-scoped child table (D-06/D-07) with its own RLS policy set and
-- GRANTs folded into this same migration (Pitfall 3 -- RLS alone is not
-- sufficient on a self-managed local Supabase CLI stack).

-- (1) Extend public.profiles -- all six columns nullable, no DEFAULT, so
-- handle_new_user()'s trigger insert (user_id/created_at only) keeps
-- succeeding for every new signup unmodified (Pitfall 2).
alter table public.profiles
  add column risk_tolerance text
    check (risk_tolerance in ('Conservative', 'Moderate', 'Aggressive')),
  add column time_horizon text
    check (time_horizon in ('<1yr', '1-3yr', '3-5yr', '5-10yr', '10+yr')),
  add column preferred_sectors text[],
  add column excluded_sectors text[],
  add column preferred_asset_types text[],
  add column capital numeric;

-- (2) Create public.holdings -- owner-scoped child table. user_id
-- references auth.users(id) directly (not via profiles.user_id join),
-- per RESEARCH.md Pattern 1, so RLS can use the same
-- (select auth.uid()) = user_id shape already proven on profiles.
-- No uniqueness constraint on (user_id, ticker) -- multiple rows for the
-- same ticker are a legitimate multiple-purchase-lot pattern (RESEARCH.md
-- Open Question 2).
create table public.holdings (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  ticker text not null,
  quantity numeric not null,
  cost_basis numeric,
  created_at timestamptz not null default now()
);

alter table public.holdings enable row level security;

-- Unlike profiles (which relies solely on the handle_new_user() trigger
-- for its only insert path), holdings has no auto-provisioning trigger --
-- it needs explicit client-facing INSERT and DELETE policies in addition
-- to SELECT/UPDATE (RESEARCH.md "Important divergence" callout).
create policy "Users can view their own holdings"
  on public.holdings for select
  using ( (select auth.uid()) = user_id );

create policy "Users can insert their own holdings"
  on public.holdings for insert
  with check ( (select auth.uid()) = user_id );

create policy "Users can update their own holdings"
  on public.holdings for update
  using ( (select auth.uid()) = user_id )
  with check ( (select auth.uid()) = user_id );

create policy "Users can delete their own holdings"
  on public.holdings for delete
  using ( (select auth.uid()) = user_id );

create index holdings_user_id_idx on public.holdings (user_id);

-- (3) GRANTs -- folded into this same migration rather than a deferred
-- follow-up (Pitfall 3, learned the hard way in Phase 1's two retroactive
-- profiles GRANT migrations). No new GRANT needed for public.profiles:
-- the existing `grant select, update on public.profiles to authenticated`
-- (20260718211140_grant_profiles_privileges.sql) already covers the six
-- new columns, since Postgres GRANTs are table-level, not column-level.
grant select, insert, update, delete on public.holdings to authenticated;
grant all on public.holdings to service_role;
