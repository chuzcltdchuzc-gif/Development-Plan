import { setBaseUrl } from "@workspace/api-client-react";

// Every generated API operation (@workspace/api-client-react) requests a
// relative path like /v1/parcels — customFetch only prepends a base URL
// when one has been configured via setBaseUrl(), which nothing previously
// called. Without it, that relative path resolves against whatever origin
// served the page itself (this Vite app in dev, or wherever the static
// build is hosted in production) — not the FastAPI backend — and the
// request silently hit this app's own SPA fallback (a 200 text/html
// response) instead of the backend (IMVP-4 API-origin runtime defect).
//
// Fail-closed, same pattern as supabase-client.ts: a missing origin must
// not silently fall back to same-origin, since that's exactly the bug
// this closes. This is a plain absolute origin, not a proxy — it works
// identically for local dev and for a deployed build (e.g. Vercel),
// pointed at whichever FastAPI deployment is current.
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL;

if (!apiBaseUrl) {
  throw new Error(
    "VITE_API_BASE_URL is required (see .env.example) — without it, API requests " +
      "resolve against this app's own origin instead of the FastAPI backend.",
  );
}

setBaseUrl(apiBaseUrl);
