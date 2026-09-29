import { type ReactNode } from "react";
import { Redirect } from "wouter";
import { Loader2 } from "lucide-react";
import { useAuth } from "@/lib/auth-context";

/** Gates a route on session presence — not on backend authorization (which
 * can only be known by actually calling the API; see AccessDenied for that
 * case). Prevents a governed screen from rendering merely because its URL
 * was navigated to directly with no session at all. */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { session, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!session) {
    return <Redirect to="/sign-in" />;
  }

  return <>{children}</>;
}
