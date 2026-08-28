import { useState } from "react";
import { useRoute, Link } from "wouter";
import { format } from "date-fns";
import { useGetParcel, useUpdateParcel, useListParcelEvidence, useAddParcelEvidence, useUpdateEvidence, getGetParcelQueryKey, getListParcelEvidenceQueryKey } from "@workspace/api-client-react";
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
import { TrustScoreGauge } from "@/components/ui/trust-score-gauge";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Map, User, CheckCircle2, XCircle, FileText, Upload, ChevronLeft, MapPin } from "lucide-react";

export function ParcelDetail() {
  const [, params] = useRoute("/parcels/:id");
  const id = params?.id;
  const queryClient = useQueryClient();

  const { data: parcel, isLoading: parcelLoading } = useGetParcel(id!, { query: { enabled: !!id } });
  const { data: evidence, isLoading: evidenceLoading } = useListParcelEvidence(id!, { query: { enabled: !!id } });
  
  const updateParcel = useUpdateParcel();
  const updateEvidence = useUpdateEvidence();

  const handleUpdateStatus = (newStatus: ParcelStatus) => {
    if (!id) return;
    updateParcel.mutate({ id, data: { status: newStatus } }, {
      onSuccess: (updatedParcel) => {
        toast.success(`Status updated to ${newStatus.replace("_", " ")}`);
        queryClient.setQueryData(getGetParcelQueryKey(id), updatedParcel);
      },
      onError: () => toast.error("Failed to update status")
    });
  };

  const handleEvidenceStatus = (evidenceId: string, status: EvidenceStatus) => {
    updateEvidence.mutate({ evidenceId, data: { status } }, {
      onSuccess: () => {
        toast.success("Evidence status updated");
        queryClient.invalidateQueries({ queryKey: getListParcelEvidenceQueryKey(id!) });
        queryClient.invalidateQueries({ queryKey: getGetParcelQueryKey(id!) }); // Trust score might change
      }
    });
  };

  if (parcelLoading) return <AppLayout><div className="animate-pulse space-y-8"><div className="h-20 bg-muted rounded-lg" /><div className="h-64 bg-muted rounded-lg" /></div></AppLayout>;
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
          <span>{parcel.title_number}</span>
        </div>

        <div className="flex flex-col md:flex-row md:items-start justify-between gap-6">
          <div>
            <div className="flex items-center gap-4">
              <h1 className="text-3xl font-display font-bold text-foreground">{parcel.title_number}</h1>
              <StatusBadge status={parcel.status} />
            </div>
            <p className="text-muted-foreground mt-2 flex items-center gap-2">
              <MapPin className="h-4 w-4" />
              {parcel.location_address}, {parcel.lga}, {parcel.state}
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Select value={parcel.status} onValueChange={(val) => handleUpdateStatus(val as ParcelStatus)}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Update Status" />
              </SelectTrigger>
              <SelectContent>
                {Object.values(ParcelStatus).map(s => (
                  <SelectItem key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
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
                    <dd className="text-base font-semibold mt-1">{parcel.owner_name}</dd>
                  </div>
                  <div>
                    <dt className="text-sm font-medium text-muted-foreground">Contact Phone</dt>
                    <dd className="text-base mt-1">{parcel.owner_phone || "—"}</dd>
                  </div>
                  <div>
                    <dt className="text-sm font-medium text-muted-foreground">Contact Email</dt>
                    <dd className="text-base mt-1">{parcel.owner_email || "—"}</dd>
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
                    <dd className="text-base font-semibold mt-1">{parcel.area_sqm.toLocaleString()} sqm</dd>
                  </div>
                  <div>
                    <dt className="text-sm font-medium text-muted-foreground">Land Use Type</dt>
                    <dd className="text-base mt-1 capitalize">{parcel.parcel_type}</dd>
                  </div>
                  <div>
                    <dt className="text-sm font-medium text-muted-foreground">Coordinates</dt>
                    <dd className="text-base mt-1">
                      {parcel.latitude && parcel.longitude ? `${parcel.latitude}, ${parcel.longitude}` : "Not provided"}
                    </dd>
                  </div>
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
                <AddEvidenceDialog parcelId={parcel.id} />
              </CardHeader>
              <CardContent className="p-0">
                {evidenceLoading ? (
                  <div className="p-8 text-center text-muted-foreground animate-pulse">Loading evidence...</div>
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
            <Card className="border-2 border-primary/20 bg-primary/5">
              <CardHeader className="pb-2">
                <CardTitle className="text-center text-primary">Trust Score</CardTitle>
                <CardDescription className="text-center">Computed algorithmically based on evidence and status.</CardDescription>
              </CardHeader>
              <CardContent className="flex justify-center pt-4 pb-8">
                <TrustScoreGauge score={parcel.trust_score} size="lg" />
              </CardContent>
            </Card>

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
