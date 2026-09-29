import { Link, useLocation } from "wouter";
import { LayoutDashboard, Map, ShieldCheck, FileCheck, FilePlus, LogOut } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";

const NAV_ITEMS = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/parcels", label: "Registry", icon: Map },
  { href: "/parcels/new", label: "Register Parcel", icon: FilePlus },
  { href: "/verify", label: "Public Verify", icon: ShieldCheck },
];

export function Sidebar() {
  const [location] = useLocation();
  const { user, signOut } = useAuth();

  return (
    <div className="flex h-screen w-64 flex-col border-r bg-sidebar text-sidebar-foreground">
      <div className="flex h-16 items-center border-b border-sidebar-border px-6">
        <div className="flex items-center gap-2 font-display text-lg font-bold tracking-tight">
          <div className="flex h-8 w-8 items-center justify-center rounded bg-primary text-primary-foreground">
            <Map className="h-5 w-5" />
          </div>
          <span className="text-sidebar-foreground">LandVault</span>
        </div>
      </div>
      
      <div className="flex-1 overflow-y-auto py-6">
        <nav className="space-y-1 px-3">
          <div className="mb-4 px-3 text-xs font-semibold uppercase tracking-wider text-sidebar-foreground/50">
            Menu
          </div>
          {NAV_ITEMS.map((item) => {
            const isActive = location === item.href || (item.href !== "/" && location.startsWith(item.href));
            
            return (
              <Link key={item.href} href={item.href} className="block">
                <div
                  className={cn(
                    "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-sidebar-accent text-sidebar-accent-foreground"
                      : "text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground"
                  )}
                >
                  <item.icon className={cn("h-4 w-4", isActive ? "text-sidebar-ring" : "opacity-70")} />
                  {item.label}
                </div>
              </Link>
            );
          })}
        </nav>
      </div>

      <div className="border-t border-sidebar-border p-4">
        {/* Real Supabase session only — no placeholder/fake identity. If this
            renders at all, RequireAuth has already confirmed a session
            exists, so `user` here is never null in practice. */}
        <div className="flex items-center gap-3 rounded-md p-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-sidebar-accent font-bold text-sidebar-foreground">
            {(user?.email ?? "?").charAt(0).toUpperCase()}
          </div>
          <div className="flex flex-col overflow-hidden">
            <span className="text-sm font-semibold truncate">{user?.email ?? "Unknown"}</span>
            <span className="text-xs text-sidebar-foreground/50">Signed in</span>
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="ml-auto shrink-0 text-sidebar-foreground/50 hover:text-sidebar-foreground"
            onClick={() => void signOut()}
            title="Sign out"
          >
            <LogOut className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
