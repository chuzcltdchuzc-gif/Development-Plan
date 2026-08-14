import { useGetDashboardStats, useListParcels } from "@workspace/api-client-react";
import { AppLayout } from "@/components/layout/app-layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TrustScoreGauge } from "@/components/ui/trust-score-gauge";
import { Map, AlertTriangle, CheckCircle2, Clock, Activity, FileText } from "lucide-react";
import { Link } from "wouter";
import { StatusBadge } from "@/components/ui/status-badge";

export function Dashboard() {
  const { data: stats, isLoading: statsLoading } = useGetDashboardStats();
  const { data: recentParcels, isLoading: parcelsLoading } = useListParcels({ limit: 5 });

  return (
    <AppLayout>
      <div className="flex flex-col gap-8">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Overview</h1>
          <p className="text-muted-foreground mt-1 text-lg">State-level land registry statistics and recent activity.</p>
        </div>

        {statsLoading ? (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {[...Array(4)].map((_, i) => (
              <Card key={i} className="h-32 animate-pulse bg-muted" />
            ))}
          </div>
        ) : stats ? (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">Total Parcels</CardTitle>
                <Map className="h-4 w-4 text-primary" />
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-display font-bold">{stats.total_parcels.toLocaleString()}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  +{stats.registrations_last_7_days} this week
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">Registered</CardTitle>
                <CheckCircle2 className="h-4 w-4 text-emerald-600" />
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-display font-bold text-emerald-600">{stats.registered_parcels.toLocaleString()}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  Verified land titles
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">Pending Action</CardTitle>
                <Clock className="h-4 w-4 text-amber-500" />
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-display font-bold text-amber-600">{stats.pending_parcels.toLocaleString()}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  Awaiting review
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">Disputed</CardTitle>
                <AlertTriangle className="h-4 w-4 text-destructive" />
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-display font-bold text-destructive">{stats.disputed_parcels.toLocaleString()}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  Active conflicts
                </p>
              </CardContent>
            </Card>
          </div>
        ) : null}

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
              ) : recentParcels && recentParcels.items.length > 0 ? (
                <div className="space-y-4">
                  {recentParcels.items.map((parcel) => (
                    <Link key={parcel.id} href={`/parcels/${parcel.id}`} className="block">
                      <div className="flex items-center justify-between rounded-lg border p-4 transition-colors hover:bg-muted/50">
                        <div className="flex items-center gap-4">
                          <div className="flex h-10 w-10 items-center justify-center rounded-md bg-primary/10 text-primary">
                            <Map className="h-5 w-5" />
                          </div>
                          <div>
                            <div className="font-semibold text-foreground">{parcel.title_number}</div>
                            <div className="text-sm text-muted-foreground truncate max-w-[200px] md:max-w-md">
                              {parcel.owner_name} &middot; {parcel.location_address}, {parcel.lga}, {parcel.state}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-6">
                          <div className="hidden text-right md:block">
                            <div className="text-sm font-medium">{parcel.area_sqm.toLocaleString()} sqm</div>
                            <div className="text-xs text-muted-foreground capitalize">{parcel.parcel_type}</div>
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
              <CardTitle>System Trust Metrics</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col items-center justify-center pt-6">
              {statsLoading ? (
                <div className="h-32 w-32 animate-pulse rounded-full bg-muted" />
              ) : stats ? (
                <>
                  <TrustScoreGauge score={stats.avg_trust_score} size="lg" />
                  <div className="mt-8 w-full space-y-4">
                    <div className="flex items-center justify-between border-b pb-2">
                      <span className="text-sm text-muted-foreground">Evidence Verified</span>
                      <span className="font-medium text-emerald-600">{stats.evidence_verified}</span>
                    </div>
                    <div className="flex items-center justify-between border-b pb-2">
                      <span className="text-sm text-muted-foreground">Evidence Pending Review</span>
                      <span className="font-medium text-amber-500">{stats.evidence_pending}</span>
                    </div>
                  </div>
                </>
              ) : null}
            </CardContent>
          </Card>
        </div>
      </div>
    </AppLayout>
  );
}
