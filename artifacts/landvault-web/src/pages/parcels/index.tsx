import { useMemo, useState } from "react";
import { Link } from "wouter";
import { useListParcels, ParcelStatus, type Parcel } from "@workspace/api-client-react";
import { AppLayout } from "@/components/layout/app-layout";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/ui/status-badge";
import { Map, Search, AlertTriangle, Plus } from "lucide-react";
import { format } from "date-fns";

const STATES = [
  "Lagos", "Abuja (FCT)", "Rivers", "Kano", "Ogun", "Oyo",
  "Delta", "Edo", "Kaduna", "Anambra", "Enugu", "Imo",
  "Cross River", "Akwa Ibom", "Plateau"
];

// The governed backend's list endpoint accepts no query parameters at all (no filtering, search,
// or pagination is implemented server-side — a known, reported contract gap). Filtering is done
// client-side here, over the real full list, rather than sending parameters the server would
// silently ignore.
function matchesFilters(parcel: Parcel, search: string, status: string, state: string): boolean {
  if (status !== "all" && parcel.status !== status) return false;
  if (state !== "all" && parcel.state !== state) return false;
  if (search) {
    const needle = search.toLowerCase();
    const haystack = [parcel.parcel_number, parcel.current_owner_name, parcel.address]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    if (!haystack.includes(needle)) return false;
  }
  return true;
}

export function ParcelsRegistry() {
  const { data, isLoading, isError } = useListParcels();

  const [searchInput, setSearchInput] = useState("");
  const [status, setStatus] = useState("all");
  const [state, setState] = useState("all");

  const filtered = useMemo(() => {
    if (!data) return [];
    return data.items.filter((p) => matchesFilters(p, searchInput, status, state));
  }, [data, searchInput, status, state]);

  return (
    <AppLayout>
      <div className="flex flex-col gap-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-foreground">Land Registry</h1>
            <p className="text-muted-foreground mt-1 text-lg">Comprehensive database of registered parcels.</p>
          </div>
          <Link href="/parcels/new">
            <Button className="w-full sm:w-auto">
              <Plus className="mr-2 h-4 w-4" />
              Register Parcel
            </Button>
          </Link>
        </div>

        <Card className="p-4">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search by parcel number, owner name, or address..."
                className="pl-10"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
              />
            </div>
            <div className="flex gap-4">
              <Select value={status} onValueChange={setStatus}>
                <SelectTrigger className="w-[140px]">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Statuses</SelectItem>
                  {Object.values(ParcelStatus).map(s => (
                    <SelectItem key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1).toLowerCase()}</SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Select value={state} onValueChange={setState}>
                <SelectTrigger className="w-[140px]">
                  <SelectValue placeholder="State" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All States</SelectItem>
                  {STATES.map(s => (
                    <SelectItem key={s} value={s}>{s}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </Card>

        <Card className="overflow-hidden border">
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="bg-muted/50 text-muted-foreground text-xs uppercase tracking-wider">
                <tr>
                  <th className="px-6 py-4 font-semibold">Parcel Number</th>
                  <th className="px-6 py-4 font-semibold">Owner & Location</th>
                  <th className="px-6 py-4 font-semibold">Details</th>
                  <th className="px-6 py-4 font-semibold text-right">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {isLoading ? (
                  [...Array(5)].map((_, i) => (
                    <tr key={i} className="animate-pulse">
                      <td className="px-6 py-4"><div className="h-4 w-24 bg-muted rounded" /></td>
                      <td className="px-6 py-4">
                        <div className="h-4 w-32 bg-muted rounded mb-2" />
                        <div className="h-3 w-48 bg-muted rounded" />
                      </td>
                      <td className="px-6 py-4"><div className="h-4 w-16 bg-muted rounded" /></td>
                      <td className="px-6 py-4 text-right"><div className="h-6 w-20 bg-muted rounded ml-auto" /></td>
                    </tr>
                  ))
                ) : isError ? (
                  <tr>
                    <td colSpan={4} className="px-6 py-12 text-center">
                      <div className="flex flex-col items-center justify-center text-muted-foreground">
                        <AlertTriangle className="h-10 w-10 mb-4 text-destructive/40" />
                        <h3 className="text-lg font-medium text-foreground">Could not load the registry</h3>
                        <p className="mt-1">The registry could not be reached. Try again shortly.</p>
                      </div>
                    </td>
                  </tr>
                ) : filtered.length > 0 ? (
                  filtered.map(parcel => (
                    <tr key={parcel.parcel_id} className="hover:bg-muted/30 transition-colors group cursor-pointer relative">
                      <td className="px-6 py-4">
                        <Link href={`/parcels/${parcel.parcel_id}`} className="absolute inset-0 z-10">
                          <span className="sr-only">View Parcel</span>
                        </Link>
                        <span className="font-semibold text-primary group-hover:underline">
                          {parcel.parcel_number ?? "Unallocated"}
                        </span>
                        <div className="text-xs text-muted-foreground mt-1">
                          Reg: {format(new Date(parcel.created_at), "MMM d, yyyy")}
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="font-medium text-foreground">{parcel.current_owner_name ?? "—"}</div>
                        <div className="text-muted-foreground mt-1 flex items-center gap-1">
                          <Map className="h-3 w-3 inline" />
                          {parcel.lga ?? "—"}, {parcel.state ?? "—"}
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div>{typeof parcel.size_sqm === "number" ? `${parcel.size_sqm.toLocaleString()} sqm` : "—"}</div>
                        <div className="text-muted-foreground capitalize mt-1">{parcel.property_type ?? "—"}</div>
                      </td>
                      <td className="px-6 py-4 text-right relative z-20">
                        <StatusBadge status={parcel.status} />
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={4} className="px-6 py-12 text-center">
                      <div className="flex flex-col items-center justify-center text-muted-foreground">
                        <Search className="h-10 w-10 mb-4 opacity-20" />
                        <h3 className="text-lg font-medium text-foreground">No parcels found</h3>
                        <p className="mt-1">Try adjusting your filters or search terms.</p>
                      </div>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          {data && (
            <div className="px-6 py-4 border-t bg-muted/20 text-sm text-muted-foreground">
              Showing {filtered.length} of {data.total} parcels
              {/* Server-side pagination doesn't exist yet — the backend's list endpoint returns
                  every parcel in one call. Client-side only for now; a real gap, not hidden. */}
            </div>
          )}
        </Card>
      </div>
    </AppLayout>
  );
}
