-- Deviation (Rule 1 - bug fix, found during 01-02 Task 2): the prior
-- migration (20260718204703_create_profiles.sql) enabled RLS and defined
-- SELECT/UPDATE policies on public.profiles, but never GRANTed the
-- underlying table privileges to the `authenticated` role. On a
-- self-managed local Supabase CLI stack (no dashboard auto-grant step),
-- Postgres requires both a GRANT *and* a passing RLS policy for a role to
-- touch a table -- RLS alone is not sufficient. Without this grant, every
-- authenticated client request against profiles fails with
-- "permission denied for table profiles" (42501) regardless of RLS.
--
-- This does not weaken RLS: `authenticated` can now attempt SELECT/UPDATE,
-- but each row is still filtered by the existing
-- `(select auth.uid()) = user_id` policies.

grant select, update on public.profiles to authenticated;
