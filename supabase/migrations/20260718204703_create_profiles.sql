-- Source pattern: official Supabase docs — supabase.com/docs/guides/auth/managing-user-data
-- (RESEARCH.md Pattern 4), adapted for D-10's column naming.
--
-- Creates the profiles stub table (user_id, created_at, last_login only —
-- no investor-profile fields; those belong to Phase 2), enables Row Level
-- Security restricting SELECT/UPDATE to the owning user (D-11), and
-- auto-provisions a profiles row via a SECURITY DEFINER trigger on
-- auth.users insert so both the password and magic-link signup paths are
-- covered by a single mechanism (AUTH-02).

create table public.profiles (
  user_id uuid not null references auth.users(id) on delete cascade,
  created_at timestamptz not null default now(),
  last_login timestamptz,
  primary key (user_id)
);

alter table public.profiles enable row level security;

create policy "Users can view their own profile"
  on public.profiles for select
  using ( (select auth.uid()) = user_id );

create policy "Users can update their own profile"
  on public.profiles for update
  using ( (select auth.uid()) = user_id )
  with check ( (select auth.uid()) = user_id );
-- Note: INSERT is handled by the SECURITY DEFINER trigger below, not by
-- client inserts — so no client-facing INSERT policy is needed for the
-- stub row itself.

create function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = ''
as $$
begin
  insert into public.profiles (user_id, created_at)
  values (new.id, now());
  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();
