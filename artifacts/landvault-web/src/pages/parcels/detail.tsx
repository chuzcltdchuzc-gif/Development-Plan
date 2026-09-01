import { useState } from "react";
import { useRoute, Link } from "wouter";
import { format } from "date-fns";
import { useGetParcel, useArchiveParcel, useListParcelEvidence, useAddParcelEvidence, useUpdateEvidence, getGetParcelQueryKey, getListParcelEvidenceQueryKey } from "@workspace/api-client-react";
import { ParcelStatus, EvidenceDocumentType, EvidenceStatus } from "@workspace/api-client-react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { z } from "zod";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import { AppLayout } from "@/components/layout/app-layout";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/ui/status-badge";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Map, User, CheckCircle2, XCircle, FileText, Upload, ChevronLeft, MapPin, AlertTriangle, Archive } from "lucide-react";

export function ParcelDetail() {
  const [, params] = useRoute("/parcels/:id");
  const id = params?.id;
  const queryClient = useQueryClient();

  const { data: parcel, isLoading: parcelLoading, isError: parcelError } = useGetParcel(id!, {
    query: { enabled: !!id, queryKey: getGetParcelQueryKey(id!) },
  });
  const { data: evidence, isLoading: evidenceLoading, isError: evidenceError } = useListParcelEvidence(id!, {
    query: { enabled: !!id, queryKey: getListParcelEvidenceQueryKey(id!) },
  });

  const archiveParcel = useArchiveParcel();
  const updateEvidence = useUpdateEvidence();

  // The governed backend has no generic "update status" field — the parcel lifecycle is one-way
  // (ACTIVE -> ARCHIVED) via a dedicated archive operation, not a PATCH to an arbitrary status value.
  const handleArchive = () => {
    if (!id) return;
    archiveParcel.mutate({ id }, {
      onSuccess: (updatedParcel) => {
        toast.success("Parcel archived");
        queryClient.setQueryData(getGetParcelQueryKey(id), updatedParcel);
      },
      onError: () => toast.error("Failed to archive parcel"),
    });
  };

  const handleEvidenceStatus = (evidenceId: string, status: EvidenceStatus) => {
    updateEvidence.mutate({ evidenceId, data: { status } }, {
      onSuccess: () => {
        toast.success("Evidence status updated");
        queryClient.invalidateQueries({ queryKey: getListParcelEvidenceQueryKey(id!) });
      },
      onError: () => toast.error("Failed to update evidence status"),
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
              <CardHeader className="border-b bg-muted/20 flex flex-row items-center justify-between">
                <div>
                  <CardTitle className="text-lg flex items-center gap-2">
                    <FileText className="h-5 w-5 text-primary" />
                    Supporting Evidence
                  </CardTitle>
                  <CardDescription>Documents verifying the parcel's title and ownership.</CardDescription>
                </div>
                <AddEvidenceDialog parcelId={parcel.parcel_id} />
              </CardHeader>
              <CardContent className="p-0">
                {evidenceLoading ? (
                  <div className="p-8 text-center text-muted-foreground animate-pulse">Loading evidence...</div>
                ) : evidenceError ? (
                  <div className="p-8 text-center text-muted-foreground flex flex-col items-center gap-2">
                    <AlertTriangle className="h-8 w-8 text-destructive/40" />
                    Could not load evidence. Try again shortly.
                  </div>
                ) : evidence && evidence.length > 0 ? (
                  <div className="divide-y">
                    {evidence.map(item => (
                      <div key={item.id} className="p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-muted/10 transition-colors">
                        <div>
                          <div className="flex items-center gap-3">
                            <FileText className="h-8 w-8 text-muted-foreground/50" />
                            <div>
                              <div className="font-semibold text-foreground flex items-center gap-2">
                                {item.file_name}
                                <StatusBadge status={item.status} className="text-[10px] px-2 py-0" />
                              </div>
                              <div className="text-xs text-muted-foreground mt-1 capitalize">
                                {item.document_type.replace(/_/g, " ")} &middot; Uploaded {format(new Date(item.uploaded_at), "MMM d, yyyy")}
                              </div>
                            </div>
                          </div>
                          {item.notes && <p className="text-sm mt-3 text-muted-foreground italic border-l-2 pl-3 ml-11">{item.notes}</p>}
                        </div>
                        
                        {item.status === "pending_review" && (
                          <div className="flex gap-2 shrink-0">
                            <Button size="sm" variant="outline" className="text-emerald-600 hover:text-emerald-700 hover:bg-emerald-50" onClick={() => handleEvidenceStatus(item.id, "verified")}>
                              <CheckCircle2 className="h-4 w-4 mr-1" /> Verify
                            </Button>
                            <Button size="sm" variant="outline" className="text-destructive hover:text-destructive hover:bg-destructive/10" onClick={() => handleEvidenceStatus(item.id, "rejected")}>
                              <XCircle className="h-4 w-4 mr-1" /> Reject
                            </Button>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="p-12 text-center flex flex-col items-center justify-center border-b border-dashed">
                    <div className="h-12 w-12 rounded-full bg-muted flex items-center justify-center mb-3">
                      <FileText className="h-6 w-6 text-muted-foreground" />
                    </div>
                    <h3 className="text-base font-semibold">No evidence documents</h3>
                    <p className="text-sm text-muted-foreground mt-1 mb-4">Upload survey plans, deeds, or receipts to build trust.</p>
                  </div>
                )}
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

const evidenceSchema = z.object({
  document_type: z.nativeEnum(EvidenceDocumentType),
  file_name: z.string().min(1, "File name is required"),
  notes: z.string().optional(),
});

function AddEvidenceDialog({ parcelId }: { parcelId: string }) {
  const [open, setOpen] = useState(false);
  const queryClient = useQueryClient();
  const addEvidence = useAddParcelEvidence();

  const form = useForm<z.infer<typeof evidenceSchema>>({
    resolver: zodResolver(evidenceSchema),
    defaultValues: {
      document_type: "survey_plan",
      file_name: "",
      notes: "",
    }
  });

  const onSubmit = (data: z.infer<typeof evidenceSchema>) => {
    addEvidence.mutate({ id: parcelId, data }, {
      onSuccess: () => {
        toast.success("Evidence added successfully");
        queryClient.invalidateQueries({ queryKey: getListParcelEvidenceQueryKey(parcelId) });
        queryClient.invalidateQueries({ queryKey: getGetParcelQueryKey(parcelId) });
        setOpen(false);
        form.reset();
      }
    });
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm"><Upload className="mr-2 h-4 w-4" /> Add Document</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add Evidence Document</DialogTitle>
          <DialogDescription>Upload supporting documentation for this parcel.</DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4 pt-4">
            <FormField
              control={form.control}
              name="document_type"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Document Type *</FormLabel>
                  <Select onValueChange={field.onChange} defaultValue={field.value}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {Object.values(EvidenceDocumentType).map(t => (
                        <SelectItem key={t} value={t}>{t.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase())}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="file_name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>File Name / Reference *</FormLabel>
                  <FormControl>
                    <Input placeholder="e.g. Survey_Plan_2023.pdf" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="notes"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Notes (Optional)</FormLabel>
                  <FormControl>
                    <Input placeholder="Additional context..." {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <DialogFooter className="pt-4">
              <Button type="submit" disabled={addEvidence.isPending}>Upload Document</Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
