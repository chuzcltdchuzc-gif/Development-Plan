import { useMemo, useState } from "react";
import { Link } from "wouter";
import { useListParcels, getListParcelsQueryKey } from "@workspace/api-client-react";
import { Map, ShieldCheck, Search, CheckCircle2, AlertTriangle } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/status-badge";
import { format } from "date-fns";

// The governed backend's list endpoint accepts no query parameters — this page fetches the full
// list and searches client-side, same approach as the Registry list page (a known, reported
// contract gap, not a client omission).
export function Verify() {
  const [searchInput, setSearchInput] = useState("");
  const [searchedNumber, setSearchedNumber] = useState<string | null>(null);

  const { data: allParcels, isLoading, isError } = useListParcels({
    query: { enabled: !!searchedNumber, queryKey: getListParcelsQueryKey() },
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchInput.trim()) {
      setSearchedNumber(searchInput.trim());
    }
  };

  const parcel = useMemo(() => {
    if (!searchedNumber || !allParcels) return undefined;
    const needle = searchedNumber.trim().toLowerCase();
    return allParcels.items.find((p) => p.parcel_number?.toLowerCase() === needle);
  }, [allParcels, searchedNumber]);

  const notFound = searchedNumber && allParcels && !parcel;

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <header className="h-16 border-b flex items-center px-6 md:px-12 bg-card">
        <Link href="/" className="flex items-center gap-2 font-display text-xl font-bold tracking-tight text-foreground">
          <div className="flex h-8 w-8 items-center justify-center rounded bg-primary text-primary-foreground">
            <Map className="h-5 w-5" />
          </div>
          LandVault
        </Link>
        <div className="ml-auto flex items-center gap-4 text-sm font-medium">
          <Link href="/" className="text-muted-foreground hover:text-foreground">Staff Login</Link>
        </div>
      </header>

      <main className="flex-1 flex flex-col items-center p-6 md:p-12">
        <div className="w-full max-w-3xl space-y-8">
          <div className="text-center space-y-4 py-8">
            <ShieldCheck className="h-16 w-16 text-primary mx-auto" />
            <h1 className="text-4xl md:text-5xl font-display font-bold tracking-tight">Evidence Record Verification</h1>
            <p className="text-lg text-muted-foreground max-w-xl mx-auto">
              Check whether a submitted registry record exists for a given parcel number.
            </p>
            <p className="text-sm text-muted-foreground max-w-xl mx-auto">
              AquaSavannah LandVault records submitted evidence and verification events. It does not
              determine legal ownership, adjudicate disputes, or replace government title systems.
            </p>
          </div>

          {isError && (
            <Card className="border-destructive/50 bg-destructive/5">
              <CardContent className="flex flex-col items-center justify-center py-8 text-center">
                <AlertTriangle className="h-10 w-10 text-destructive mb-3" />
                <p className="text-muted-foreground">The registry could not be reached. Try again shortly.</p>
              </CardContent>
            </Card>
          )}

          <Card className="border-2 shadow-lg hover-elevate">
            <CardContent className="p-2 sm:p-4">
              <form onSubmit={handleSearch} className="flex flex-col sm:flex-row gap-2">
                <div className="relative flex-1">
                  <Search className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    value={searchInput}
                    onChange={(e) => setSearchInput(e.target.value)}
                    placeholder="Enter Parcel Number (e.g. LV-NG-2024-...)"
                    className="pl-12 h-14 text-lg bg-transparent border-none focus-visible:ring-0"
                  />
                </div>
                <Button type="submit" size="lg" className="h-14 px-8 text-base">
                  Check Record
                </Button>
              </form>
            </CardContent>
          </Card>

          {isLoading && (
            <div className="py-12 flex justify-center">
              <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full" />
            </div>
          )}

          {notFound && (
            <Card className="border-destructive/50 bg-destructive/5 mt-8">
              <CardContent className="flex flex-col items-center justify-center py-12 text-center">
                <AlertTriangle className="h-12 w-12 text-destructive mb-4" />
                <h3 className="text-xl font-bold text-destructive">No Record Found</h3>
                <p className="text-muted-foreground mt-2 max-w-md">
                  No submitted record matches the parcel number <span className="font-semibold text-foreground">"{searchedNumber}"</span>. Please check the number and try again.
                </p>
              </CardContent>
            </Card>
          )}

          {parcel && (
            <div className="space-y-6 mt-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
              <div className="flex items-center gap-3 px-2">
                <CheckCircle2 className="h-6 w-6 text-emerald-600" />
                <h2 className="text-2xl font-bold">Record Found</h2>
              </div>

              <Card className="overflow-hidden border-2 border-primary/20">
                <div className="bg-muted/30 p-6 sm:p-8 flex flex-col sm:flex-row sm:items-center justify-between gap-6 border-b">
                  <div>
                    <div className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-1">Parcel Number</div>
                    <div className="text-3xl font-display font-bold text-foreground">{parcel.parcel_number}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-1">Status</div>
                    <StatusBadge status={parcel.status} className="text-sm px-3 py-1" />
                  </div>
                </div>

                <CardContent className="p-0">
                  <dl className="divide-y">
                    <div className="p-6 grid grid-cols-1 sm:grid-cols-3 gap-4">
                      <dt className="text-sm font-medium text-muted-foreground sm:col-span-1 flex items-center gap-2">
                        Submitted Owner Reference
                      </dt>
                      <dd className="text-lg font-medium text-foreground sm:col-span-2">
                        {parcel.current_owner_name ?? "—"}
                      </dd>
                    </div>
                    <div className="p-6 grid grid-cols-1 sm:grid-cols-3 gap-4 bg-muted/10">
                      <dt className="text-sm font-medium text-muted-foreground sm:col-span-1">
                        Location
                      </dt>
                      <dd className="text-base text-foreground sm:col-span-2">
                        {parcel.address ?? "—"}<br />
                        {parcel.lga ?? "—"}, {parcel.state ?? "—"} State
                      </dd>
                    </div>
                    <div className="p-6 grid grid-cols-1 sm:grid-cols-3 gap-4">
                      <dt className="text-sm font-medium text-muted-foreground sm:col-span-1">
                        Specifications
                      </dt>
                      <dd className="text-base text-foreground sm:col-span-2">
                        {typeof parcel.size_sqm === "number" ? `${parcel.size_sqm.toLocaleString()} sqm` : "—"} &middot; <span className="capitalize">{parcel.property_type ?? "—"}</span>
                      </dd>
                    </div>
                    <div className="p-6 grid grid-cols-1 sm:grid-cols-3 gap-4 bg-muted/10">
                      <dt className="text-sm font-medium text-muted-foreground sm:col-span-1">
                        Submission Date
                      </dt>
                      <dd className="text-base text-foreground sm:col-span-2">
                        {format(new Date(parcel.created_at), "MMMM do, yyyy")}
                      </dd>
                    </div>
                  </dl>
                </CardContent>
              </Card>

              <p className="text-xs text-muted-foreground text-center max-w-md mx-auto">
                This record reflects submitted evidence and registry status only. It is not a
                determination of legal ownership and does not replace government title systems.
              </p>
            </div>
          )}
        </div>
      </main>
      
      <footer className="py-6 text-center text-sm text-muted-foreground border-t bg-card">
        &copy; {new Date().getFullYear()} AquaSavannah LandVault. Evidence and verification record, not a determination of legal title.
      </footer>
    </div>
  );
}
