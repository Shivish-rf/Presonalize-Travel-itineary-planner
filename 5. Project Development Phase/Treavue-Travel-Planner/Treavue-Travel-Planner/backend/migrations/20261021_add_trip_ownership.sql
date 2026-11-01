-- Phase 1: add ownership without assigning legacy rows to an arbitrary user.
alter table public.trips
  add column if not exists user_id uuid references auth.users (id) on delete cascade;

create index if not exists trips_user_id_created_at_idx
  on public.trips (user_id, created_at desc);

alter table public.trips enable row level security;

-- Remove any earlier policies so no permissive policy can widen access.
do $$
declare
  existing_policy record;
begin
  for existing_policy in
    select policyname
    from pg_policies
    where schemaname = 'public' and tablename = 'trips'
  loop
    execute format(
      'drop policy if exists %I on public.trips',
      existing_policy.policyname
    );
  end loop;
end;
$$;

revoke all on table public.trips from public, anon;
grant select, insert, update, delete on table public.trips to authenticated;

create policy "Users can read their own trips"
  on public.trips for select to authenticated
  using ((select auth.uid()) = user_id);

drop policy if exists "Users can create their own trips" on public.trips;
create policy "Users can create their own trips"
  on public.trips for insert to authenticated
  with check ((select auth.uid()) = user_id);

drop policy if exists "Users can update their own trips" on public.trips;
create policy "Users can update their own trips"
  on public.trips for update to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

drop policy if exists "Users can delete their own trips" on public.trips;
create policy "Users can delete their own trips"
  on public.trips for delete to authenticated
  using ((select auth.uid()) = user_id);

-- After manually reviewing and assigning/deleting every legacy row with NULL
-- user_id, run the following separately to make ownership mandatory:
-- alter table public.trips alter column user_id set not null;
