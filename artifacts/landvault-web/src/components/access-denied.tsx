import { ShieldAlert } from "lucide-react";
import { ApiError } from "@workspace/api-client-react";

/** True for a backend 403 specifically — "authenticated but unauthorized"
 * (a real Supabase session with no corresponding governed LandVault
 * authority), distinct from an unreachable backend or a 401 (session
 * missing/expired, which route protection already redirects for). */
export function isAccessDeniedError(error: unknown): boolean {
  return error instanceof ApiError && error.status === 403;
}

export function AccessDenied() {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <ShieldAlert className="h-10 w-10 text-destructive/50 mb-3" />
      <h3 className="text-lg font-medium">Access denied</h3>
      <p className="text-sm text-muted-foreground max-w-sm mt-1">
        You're signed in, but your account isn't authorized for this. Contact a registry
        administrator if you believe this is a mistake.
      </p>
    </div>
  );
}
