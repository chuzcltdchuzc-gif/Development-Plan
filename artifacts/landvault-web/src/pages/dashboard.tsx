import { useListParcels } from "@workspace/api-client-react";
import { AppLayout } from "@/components/layout/app-layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Map, AlertTriangle, FileText, BarChart3 } from "lucide-react";
import { Link } from "wouter";
import { StatusBadge } from "@/components/ui/status-badge";

export function Dashboard() {
  const { data: recentParcels, isLoading: parcelsLoading, isError: parcelsError } = useListParcels();

  return (
    <AppLayout>
      <div className="flex flex-col gap-8">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Overview</h1>
          <p className="text-muted-foreground mt-1 text-lg">State-level land registry statistics and recent activity.</p>
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          <Card className="lg:col-span-2">
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Recent Parcels</CardTitle>
                <p className="text-sm text-muted-foreground mt-1">Latest land registrations and updates.</p>
              </div>
              <Link href="/parcels" className="text-sm font-medium text-primary hover:underline">
                View All
              </Link>
            </CardHeader>
            <CardContent>
              {parcelsLoading ? (
                <div className="space-y-4">
                  {[...Array(3)].map((_, i) => (
                    <div key={i} className="h-16 animate-pulse rounded-md bg-muted" />
                  ))}
                </div>
              ) : parcelsError ? (
                <div className="flex flex-col items-center justify-center py-8 text-center">
                  <AlertTriangle className="h-12 w-12 text-destructive/50 mb-3" />
                  <h3 className="text-lg font-medium">Could not load parcels</h3>
                  <p className="text-sm text-muted-foreground max-w-sm mt-1">
                    The registry could not be reached. Try again shortly.
                  </p>
                </div>
              ) : recentParcels && recentParcels.length > 0 ? (
                <div className="space-y-4">
                  {recentParcels.slice(0, 5).map((parcel) => (
                    <Link key={parcel.parcel_id} href={`/parcels/${parcel.parcel_id}`} className="block">
                      <div className="flex items-center justify-between rounded-lg border p-4 transition-colors hover:bg-muted/50">
                        <div className="flex items-center gap-4">
                          <div className="flex h-10 w-10 items-center justify-center rounded-md bg-primary/10 text-primary">
                            <Map className="h-5 w-5" />
                          </div>
                          <div>
                            <div className="font-semibold text-foreground">{parcel.parcel_number ?? "Unallocated"}</div>
                            <div className="text-sm text-muted-foreground truncate max-w-[200px] md:max-w-md">
                              {parcel.current_owner_name ?? "—"} &middot; {parcel.address ?? "—"}, {parcel.lga ?? "—"}, {parcel.state ?? "—"}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-6">
                          <div className="hidden text-right md:block">
                            <div className="text-sm font-medium">
                              {typeof parcel.size_sqm === "number" ? `${parcel.size_sqm.toLocaleString()} sqm` : "—"}
                            </div>
                            <div className="text-xs text-muted-foreground capitalize">{parcel.property_type ?? "—"}</div>
                          </div>
                          <StatusBadge status={parcel.status} />
                        </div>
                      </div>
                    </Link>
                  ))}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-8 text-center">
                  <FileText className="h-12 w-12 text-muted-foreground/50 mb-3" />
                  <h3 className="text-lg font-medium">No parcels found</h3>
                  <p className="text-sm text-muted-foreground max-w-sm mt-1">
                    There are no parcels registered in the system yet.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Registry Statistics</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col items-center justify-center py-10 text-center">
              <BarChart3 className="h-10 w-10 text-muted-foreground/40 mb-3" />
              <h3 className="text-sm font-medium text-foreground">Not yet available</h3>
              <p className="text-xs text-muted-foreground mt-1 max-w-[220px]">
                Aggregate registry statistics require a governed backend capability that does not
                exist yet.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </AppLayout>
  );
}
