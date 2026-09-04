import { useRoute, Link } from "wouter";
import { format } from "date-fns";
import { useGetParcel, useArchiveParcel, getGetParcelQueryKey } from "@workspace/api-client-react";
import { ParcelStatus } from "@workspace/api-client-react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { AppLayout } from "@/components/layout/app-layout";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/ui/status-badge";
import { Map, User, FileText, ChevronLeft, MapPin, AlertTriangle, Archive } from "lucide-react";

export function ParcelDetail() {
  const [, params] = useRoute("/parcels/:id");
  const id = params?.id;
  const queryClient = useQueryClient();

  const { data: parcel, isLoading: parcelLoading, isError: parcelError } = useGetParcel(id!, {
    query: { enabled: !!id, queryKey: getGetParcelQueryKey(id!) },
  });

  const archiveParcel = useArchiveParcel();

  // The governed backend has no generic "update status" field — the parcel lifecycle is one-way
  // (ACTIVE -> ARCHIVED) via a dedicated archive operation, not a PATCH to an arbitrary status value.
  const handleArchive = () => {
    if (!id) return;
    archiveParcel.mutate({ parcelId: id }, {
      onSuccess: (updatedParcel) => {
        toast.success("Parcel archived");
        queryClient.setQueryData(getGetParcelQueryKey(id), updatedParcel);
      },
      onError: () => toast.error("Failed to archive parcel"),
    });
  };

  if (parcelLoading) return <AppLayout><div className="animate-pulse space-y-8"><div className="h-20 bg-muted rounded-lg" /><div className="h-64 bg-muted rounded-lg" /></div></AppLayout>;
  if (parcelError) {
    return (
      <AppLayout>
        <div className="p-8 text-center text-muted-foreground flex flex-col items-center gap-3">
          <AlertTriangle className="h-10 w-10 text-destructive/40" />
          Could not load this parcel. Try again shortly.
        </div>
      </AppLayout>
    );
  }
  if (!parcel) return <AppLayout><div className="p-8 text-center text-muted-foreground">Parcel not found.</div></AppLayout>;

  return (
    <AppLayout>
      <div className="flex flex-col gap-8">
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          <Link href="/parcels" className="hover:text-foreground flex items-center">
            <ChevronLeft className="h-4 w-4 mr-1" />
            Back to Registry
          </Link>
          <span>/</span>
          <span>{parcel.parcel_number ?? "Unallocated"}</span>
        </div>

        <div className="flex flex-col md:flex-row md:items-start justify-between gap-6">
          <div>
            <div className="flex items-center gap-4">
              <h1 className="text-3xl font-display font-bold text-foreground">{parcel.parcel_number ?? "Unallocated"}</h1>
              <StatusBadge status={parcel.status} />
            </div>
            <p className="text-muted-foreground mt-2 flex items-center gap-2">
              <MapPin className="h-4 w-4" />
              {parcel.address ?? "—"}, {parcel.lga ?? "—"}, {parcel.state ?? "—"}
            </p>
          </div>

          {parcel.status === ParcelStatus.ACTIVE && (
            <div className="flex items-center gap-3">
              <Button
                variant="outline"
                onClick={handleArchive}
                disabled={archiveParcel.isPending}
              >
                <Archive className="mr-2 h-4 w-4" />
                Archive Parcel
              </Button>
            </div>
          )}
        </div>

        <div className="grid gap-8 lg:grid-cols-3">
          <div className="lg:col-span-2 space-y-8">
            <Card>
              <CardHeader className="border-b bg-muted/20">
                <CardTitle className="text-lg flex items-center gap-2">
                  <User className="h-5 w-5 text-primary" />
                  Owner Information
                </CardTitle>
              </CardHeader>
              <CardContent className="p-6">
                <dl className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                  <div>
                    <dt className="text-sm font-medium text-muted-foreground">Registered Owner</dt>
                    <dd className="text-base font-semibold mt-1">{parcel.current_owner_name ?? "—"}</dd>
                  </div>
                  <div>
                    <dt className="text-sm font-medium text-muted-foreground">Contact</dt>
                    <dd className="text-base mt-1">{parcel.current_owner_contact || "—"}</dd>
                  </div>
                </dl>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="border-b bg-muted/20">
                <CardTitle className="text-lg flex items-center gap-2">
                  <Map className="h-5 w-5 text-primary" />
                  Parcel Specifications
                </CardTitle>
              </CardHeader>
              <CardContent className="p-6">
                <dl className="grid grid-cols-1 sm:grid-cols-3 gap-6">
                  <div>
                    <dt className="text-sm font-medium text-muted-foreground">Area</dt>
                    <dd className="text-base font-semibold mt-1">
                      {typeof parcel.size_sqm === "number" ? `${parcel.size_sqm.toLocaleString()} sqm` : "—"}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-sm font-medium text-muted-foreground">Land Use Type</dt>
                    <dd className="text-base mt-1 capitalize">{parcel.property_type ?? "—"}</dd>
                  </div>
                  {/* Geometry/boundary lives in the separate Spatial bounded context, referenced
                      only via parcel.geometry_reference — not shown here yet; see the Spatial
                      Read Contract Proposal. */}
                  <div className="sm:col-span-3">
                    <dt className="text-sm font-medium text-muted-foreground">Registration Date</dt>
                    <dd className="text-base mt-1">{format(new Date(parcel.created_at), "PPP 'at' p")}</dd>
                  </div>
                </dl>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="border-b bg-muted/20">
                <CardTitle className="text-lg flex items-center gap-2">
                  <FileText className="h-5 w-5 text-primary" />
                  Supporting Evidence
                </CardTitle>
                <CardDescription>Documents verifying the parcel's title and ownership.</CardDescription>
              </CardHeader>
              <CardContent className="p-12 text-center flex flex-col items-center justify-center">
                <div className="h-12 w-12 rounded-full bg-muted flex items-center justify-center mb-3">
                  <FileText className="h-6 w-6 text-muted-foreground" />
                </div>
                <h3 className="text-base font-semibold">Evidence services are not yet connected in this build</h3>
                <p className="text-sm text-muted-foreground mt-1 max-w-sm">
                  Uploading and reviewing survey plans, deeds, and receipts will appear here once
                  that capability is available.
                </p>
              </CardContent>
            </Card>
          </div>

          <div className="space-y-8">
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Audit Log</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="relative border-l border-muted-foreground/20 ml-3 space-y-6 pb-4">
                  <div className="relative pl-6">
                    <div className="absolute left-[-5px] top-1 h-2.5 w-2.5 rounded-full bg-primary ring-4 ring-background" />
                    <div className="text-sm font-medium">Record Created</div>
                    <div className="text-xs text-muted-foreground">{format(new Date(parcel.created_at), "PPp")}</div>
                  </div>
                  {parcel.updated_at !== parcel.created_at && (
                    <div className="relative pl-6">
                      <div className="absolute left-[-5px] top-1 h-2.5 w-2.5 rounded-full bg-muted-foreground ring-4 ring-background" />
                      <div className="text-sm font-medium">Record Updated</div>
                      <div className="text-xs text-muted-foreground">{format(new Date(parcel.updated_at), "PPp")}</div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
