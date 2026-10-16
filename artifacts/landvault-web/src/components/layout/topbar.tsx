import { Bell, Search, Settings } from "lucide-react";

export function Topbar() {
  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b bg-card px-6">
      <div className="flex flex-1 items-center gap-4">
        <div className="relative w-full max-w-md">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            type="search"
            placeholder="Search by title number, owner, or address..."
            className="h-10 w-full rounded-md border bg-muted/50 pl-10 pr-4 text-sm outline-none transition-colors focus:border-primary focus:bg-background focus:ring-1 focus:ring-ring"
          />
        </div>
      </div>
      
      <div className="flex items-center gap-4">
        <button className="flex h-9 w-9 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground">
          <Bell className="h-5 w-5" />
        </button>
        <button className="flex h-9 w-9 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground">
          <Settings className="h-5 w-5" />
        </button>
      </div>
    </header>
  );
}
