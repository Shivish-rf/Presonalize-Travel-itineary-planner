# Backend trip storage

Saved trips use Supabase Auth and the `public.trips` table. The browser uses
only `VITE_SUPABASE_URL` and the public `VITE_SUPABASE_ANON_KEY` for email and
password authentication. FastAPI verifies each bearer token against Supabase
Auth using `SUPABASE_URL` and the project's low-privilege
`SUPABASE_AUTH_API_KEY` (publishable or legacy anon key), then uses that same
verified access token for trip storage. The database applies its per-user RLS
policies, and trip queries also constrain `user_id` to the verified identity; a
client-supplied owner ID is never accepted. Trip synchronization does not use a
privileged service-role or secret key.

## Required Supabase setup

1. In the Supabase dashboard, open **SQL Editor**, review and run
   [`migrations/20261021_add_trip_ownership.sql`](./migrations/20261021_add_trip_ownership.sql).
   This adds a nullable `user_id`, an index, enables RLS, and creates restrictive
   per-user policies. Do not expose the API before the migration is applied.
2. Existing rows will have `user_id = NULL` and will not be visible through the
   authenticated application. Preserve them while ownership is unknown; do not
   assign them to an arbitrary account or delete them as part of setup. After a
   verified account exists, associate a row only when its owner can be
   independently confirmed. Keep unresolved rows nullable and inaccessible.
   Make `user_id` non-null only after every legacy row has been safely resolved.
3. Enable email/password under **Authentication → Providers → Email**.
   Configure email confirmation and redirect URLs for the frontend as desired.
4. Set `VITE_SUPABASE_URL` and the project’s **publishable/anon** key in
   `artifacts/treavue/.env.local`. Vite reads this frontend-specific file;
`backend/.env` does not configure the browser. Set `SUPABASE_URL`,
`SUPABASE_AUTH_API_KEY` to that same project's publishable/anon key in the
backend environment. The Auth API key is sent to Supabase Auth while validating
access tokens and to PostgREST while the verified user's access token enforces
RLS. Never put a secret/service-role key in a `VITE_*` variable or frontend
bundle.
5. Restart both development servers. Sign up, confirm email if enabled, then
   sign in. Existing browser-only trips are offered for explicit import after
   login; they are not automatically transferred between accounts.

Keep the backend private until HTTPS, rate limiting, appropriate secret
handling, and production operational controls are in place. Trip database
requests use the verified user's JWT, so Supabase RLS and the API's explicit
identity filters both enforce ownership.
