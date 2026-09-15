import { createClient } from "@supabase/supabase-js";

const url = import.meta.env.VITE_SUPABASE_URL;
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

if (!url || !anonKey) {
  throw new Error(
    "VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY are required (see .env.example). " +
      "Only the public anon key belongs here — never a service-role key.",
  );
}

// The anon key is designed to be public (bundled into the client build) —
// protection comes from the backend independently re-verifying the token and
// from Postgres RLS, never from this key's secrecy. The service-role key
// must never appear in frontend code or env vars prefixed VITE_ (those are
// inlined into the browser bundle at build time).
export const supabase = createClient(url, anonKey);
