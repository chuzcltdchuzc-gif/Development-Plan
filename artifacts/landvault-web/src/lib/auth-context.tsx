import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import type { Session, User } from "@supabase/supabase-js";
import { setAuthTokenGetter } from "@workspace/api-client-react";
import { supabase } from "@/lib/supabase-client";

interface AuthContextValue {
  session: Session | null;
  user: User | null;
  isLoading: boolean;
  signInWithPassword: (email: string, password: string) => Promise<{ error: string | null }>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

// Wired once, at module scope, not per-render: `setAuthTokenGetter` replaces
// whatever getter was previously registered (there is exactly one, module-
// level slot in custom-fetch.ts), so this must not be called repeatedly
// inside a component body/effect that re-runs.
setAuthTokenGetter(async () => {
  // Reads Supabase's own locally-cached session; supabase-js transparently
  // refreshes the access token before it expires, so this never needs its
  // own refresh logic — that would duplicate exactly what the SDK exists to
  // get right (IMVP-3 dependency justification).
  const { data } = await supabase.auth.getSession();
  return data.session?.access_token ?? null;
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Session restoration: Supabase persists the session in local storage by
    // default and getSession() reads it back synchronously-ish on startup —
    // a page refresh must not silently drop to an anonymous state while this
    // resolves, hence isLoading gating what the rest of the app renders.
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
      setIsLoading(false);
    });

    const { data: subscription } = supabase.auth.onAuthStateChange((_event, newSession) => {
      setSession(newSession);
    });

    return () => subscription.subscription.unsubscribe();
  }, []);

  const signInWithPassword = async (email: string, password: string) => {
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    return { error: error?.message ?? null };
  };

  const signOut = async () => {
    await supabase.auth.signOut();
  };

  return (
    <AuthContext.Provider
      value={{ session, user: session?.user ?? null, isLoading, signInWithPassword, signOut }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
