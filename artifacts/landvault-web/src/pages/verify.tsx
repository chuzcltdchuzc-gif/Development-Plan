import { useState } from "react";
import { Link } from "wouter";
import { useListParcels, useListParcelEvidence } from "@workspace/api-client-react";
import { Map, ShieldCheck, Search, CheckCircle2, AlertTriangle, FileText, ChevronRight } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/status-badge";
import { TrustScoreGauge } from "@/components/ui/trust-score-gauge";
import { format } from "date-fns";

export function Verify() {
  const [searchInput, setSearchInput] = useState("");
  const [searchedTitle, setSearchedTitle] = useState<string | null>(null);

  const { data: searchResults, isLoading, isError } = useListParcels(
    { search: searchedTitle || undefined, limit: 1 },
    { query: { enabled: !!searchedTitle } }
  );

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchInput.trim()) {
      setSearchedTitle(searchInput.trim());
    }
  };

  const parcel = searchResults?.items[0];
  const notFound = searchedTitle && searchResults && searchResults.items.length === 0;

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
            <h1 className="text-4xl md:text-5xl font-display font-bold tracking-tight">Title Verification</h1>
            <p className="text-lg text-muted-foreground max-w-xl mx-auto">
              Verify the authenticity and current status of a land parcel registered with the state government.
            </p>
          </div>

          <Card className="border-2 shadow-lg hover-elevate">
            <CardContent className="p-2 sm:p-4">
              <form onSubmit={handleSearch} className="flex flex-col sm:flex-row gap-2">
                <div className="relative flex-1">
                  <Search className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" />
                  <Input 
                    value={searchInput}
                    onChange={(e) => setSearchInput(e.target.value)}
                    placeholder="Enter Title Number (e.g. LV-NG-2024-...)" 
                    className="pl-12 h-14 text-lg bg-transparent border-none focus-visible:ring-0"
                  />
                </div>
                <Button type="submit" size="lg" className="h-14 px-8 text-base">
                  Verify Now
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
                <h3 className="text-xl font-bold text-destructive">Title Not Found</h3>
                <p className="text-muted-foreground mt-2 max-w-md">
                  No records match the title number <span className="font-semibold text-foreground">"{searchedTitle}"</span>. Please check the number and try again.
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
                    <div className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-1">Title Number</div>
                    <div className="text-3xl font-display font-bold text-foreground">{parcel.title_number}</div>
                  </div>
                  <div className="flex items-center gap-6">
                    <div className="text-right">
                      <div className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-1">Status</div>
                      <StatusBadge status={parcel.status} className="text-sm px-3 py-1" />
                    </div>
                    <div className="h-16 w-px bg-border hidden sm:block" />
                    <TrustScoreGauge score={parcel.trust_score} size="md" />
                  </div>
                </div>
                
                <CardContent className="p-0">
                  <dl className="divide-y">
                    <div className="p-6 grid grid-cols-1 sm:grid-cols-3 gap-4">
                      <dt className="text-sm font-medium text-muted-foreground sm:col-span-1 flex items-center gap-2">
                        Registered Owner
                      </dt>
                      <dd className="text-lg font-medium text-foreground sm:col-span-2">
                        {parcel.owner_name}
                      </dd>
                    </div>
                    <div className="p-6 grid grid-cols-1 sm:grid-cols-3 gap-4 bg-muted/10">
                      <dt className="text-sm font-medium text-muted-foreground sm:col-span-1">
                        Location
                      </dt>
                      <dd className="text-base text-foreground sm:col-span-2">
                        {parcel.location_address}<br />
                        {parcel.lga}, {parcel.state} State
                      </dd>
                    </div>
                    <div className="p-6 grid grid-cols-1 sm:grid-cols-3 gap-4">
                      <dt className="text-sm font-medium text-muted-foreground sm:col-span-1">
                        Specifications
                      </dt>
                      <dd className="text-base text-foreground sm:col-span-2">
                        {parcel.area_sqm.toLocaleString()} sqm &middot; <span className="capitalize">{parcel.parcel_type}</span>
                      </dd>
                    </div>
                    <div className="p-6 grid grid-cols-1 sm:grid-cols-3 gap-4 bg-muted/10">
                      <dt className="text-sm font-medium text-muted-foreground sm:col-span-1">
                        Registration Date
                      </dt>
                      <dd className="text-base text-foreground sm:col-span-2">
                        {format(new Date(parcel.created_at), "MMMM do, yyyy")}
                      </dd>
                    </div>
                  </dl>
                </CardContent>
              </Card>

              <PublicEvidenceList parcelId={parcel.id} />
            </div>
          )}
        </div>
      </main>
      
      <footer className="py-6 text-center text-sm text-muted-foreground border-t bg-card">
        &copy; {new Date().getFullYear()} AquaSavannah LandVault. Official State Land Registry.
      </footer>
    </div>
  );
}

function PublicEvidenceList({ parcelId }: { parcelId: string }) {
  const { data: evidence } = useListParcelEvidence(parcelId);

  const verifiedEvidence = evidence?.filter(e => e.status === "verified") || [];

  if (!evidence || verifiedEvidence.length === 0) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2">
          <FileText className="h-5 w-5 text-primary" />
          Verified Documentation
        </CardTitle>
        <CardDescription>Documents that have been cryptographically verified by the registry.</CardDescription>
      </CardHeader>
      <CardContent>
        <ul className="space-y-4">
          {verifiedEvidence.map(item => (
            <li key={item.id} className="flex items-center justify-between p-4 rounded-lg border bg-muted/30">
              <div className="flex items-center gap-3">
                <CheckCircle2 className="h-5 w-5 text-emerald-600" />
                <div>
                  <div className="font-medium">{item.document_type.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase())}</div>
                  <div className="text-xs text-muted-foreground">Verified on {format(new Date(item.uploaded_at), "MMM d, yyyy")}</div>
                </div>
              </div>
              <Button variant="ghost" size="sm" className="hidden sm:flex">
                View Record <ChevronRight className="ml-1 h-4 w-4" />
              </Button>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
