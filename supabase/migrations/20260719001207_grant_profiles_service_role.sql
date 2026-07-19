-- Deviation (Rule 1 - bug fix, found during 01-05 Task 2): a self-managed
-- local Supabase CLI stack does not auto-grant the service_role table
-- privileges any more than it auto-granted the authenticated role (see
-- 20260718211140_grant_profiles_privileges.sql) -- service_role initially
-- had zero privileges on public.profiles, so even a service-role-keyed
-- client (used only by tests, to bypass RLS and exercise the profiles
-- table's primary-key unique-violation directly, isolated from the RLS
-- question tested separately in test_rls_policy.py) failed with
-- "permission denied for table profiles" (42501) before ever reaching the
-- constraint check.
--
-- service_role is Supabase's RLS-bypass role for privileged/administrative
-- access -- the deployed Streamlit app itself never loads this key, using
-- only the anon key (Pitfall 5). Granting it full table access here does
-- not weaken RLS or change any grant for the anon/authenticated roles.

grant all on public.profiles to service_role;
