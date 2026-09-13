import { useState } from "react";
import { useRoute, Link } from "wouter";
import { format } from "date-fns";
import {
  useGetParcel, useArchiveParcel, getGetParcelQueryKey,
  useListParcelEvidence, uploadParcelEvidence, getListParcelEvidenceQueryKey,
} from "@workspace/api-client-react";
import { ParcelStatus, EvidenceType } from "@workspace/api-client-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { AppLayout } from "@/components/layout/app-layout";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/ui/status-badge";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Map, User, FileText, ChevronLeft, MapPin, AlertTriangle, Archive, Upload } from "lucide-react";

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

            <EvidenceCard parcelId={parcel.parcel_id} />
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

const MAX_UPLOAD_BYTES = 10 * 1024 * 1024;
const ACCEPTED_FILE_TYPES = ".pdf,.jpg,.jpeg,.png";

function EvidenceCard({ parcelId }: { parcelId: string }) {
  const queryClient = useQueryClient();
  const evidenceQueryKey = getListParcelEvidenceQueryKey(parcelId);
  const { data: evidence, isLoading, isError } = useListParcelEvidence(parcelId, {
    query: { queryKey: evidenceQueryKey },
  });

  const [open, setOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [evidenceType, setEvidenceType] = useState<EvidenceType>(EvidenceType.SURVEY_PLAN);
  const [basis, setBasis] = useState("");

  // useUploadParcelEvidence's own request options are fixed once, at hook
  // creation — not per .mutate() call — but the Content-Type header here
  // must match whichever file the user actually picked, so this calls the
  // generated uploadParcelEvidence() function directly inside a plain
  // useMutation instead of the generated react-query wrapper. Still 100%
  // generated request-building code (uploadParcelEvidence itself); nothing
  // here hand-rolls HTTP.
  const upload = useMutation({
    mutationFn: () => {
      if (!file) throw new Error("no file selected");
      return uploadParcelEvidence(
        parcelId,
        file,
        { filename: file.name, evidence_type: evidenceType, basis },
        { headers: { "Content-Type": file.type } },
      );
    },
    onSuccess: () => {
      toast.success("Evidence uploaded");
      queryClient.invalidateQueries({ queryKey: evidenceQueryKey });
      setOpen(false);
      setFile(null);
      setBasis("");
      setEvidenceType(EvidenceType.SURVEY_PLAN);
    },
    onError: () => toast.error("Failed to upload evidence"),
  });

  return (
    <Card>
      <CardHeader className="border-b bg-muted/20 flex flex-row items-center justify-between">
        <div>
          <CardTitle className="text-lg flex items-center gap-2">
            <FileText className="h-5 w-5 text-primary" />
            Supporting Evidence
          </CardTitle>
          <CardDescription>Documents submitted as supporting evidence for this parcel.</CardDescription>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button size="sm"><Upload className="mr-2 h-4 w-4" /> Add Document</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Submit Supporting Evidence</DialogTitle>
              <DialogDescription>
                LandVault records submitted evidence. It does not determine legal ownership,
                adjudicate disputes, or replace government title systems.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 pt-2">
              <div className="space-y-1.5">
                <label className="text-sm font-medium">Document Type</label>
                <Select
                  value={evidenceType}
                  onValueChange={(value) => setEvidenceType(value as EvidenceType)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.values(EvidenceType).map((type) => (
                      <SelectItem key={type} value={type}>
                        {type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-medium">File (PDF, JPEG, or PNG, max 10 MB)</label>
                <Input
                  type="file"
                  accept={ACCEPTED_FILE_TYPES}
                  onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                />
                {file && file.size > MAX_UPLOAD_BYTES && (
                  <p className="text-sm text-destructive">This file exceeds the 10 MB limit.</p>
                )}
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-medium">Description</label>
                <Input
                  value={basis}
                  onChange={(e) => setBasis(e.target.value)}
                  placeholder="e.g. Submitted by registrant as supporting survey documentation"
                />
              </div>
            </div>
            <DialogFooter className="pt-4">
              <Button
                onClick={() => upload.mutate()}
                disabled={!file || file.size > MAX_UPLOAD_BYTES || !basis || upload.isPending}
              >
                {upload.isPending ? "Uploading..." : "Upload"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </CardHeader>
      <CardContent className="p-0">
        {isLoading ? (
          <div className="p-8 text-center text-muted-foreground animate-pulse">Loading evidence...</div>
        ) : isError ? (
          <div className="p-8 text-center text-muted-foreground flex flex-col items-center gap-2">
            <AlertTriangle className="h-8 w-8 text-destructive/40" />
            Could not load evidence. Try again shortly.
          </div>
        ) : evidence && evidence.length > 0 ? (
          <div className="divide-y">
            {evidence.map((item) => (
              <div key={item.evidence_id} className="p-6 flex items-start gap-3">
                <FileText className="h-8 w-8 text-muted-foreground/50 shrink-0" />
                <div>
                  <div className="font-semibold text-foreground flex items-center gap-2">
                    {item.filename}
                    <StatusBadge status={item.status} className="text-[10px] px-2 py-0" />
                  </div>
                  <div className="text-xs text-muted-foreground mt-1 capitalize">
                    {item.evidence_type.replace(/_/g, " ").toLowerCase()} &middot; Uploaded{" "}
                    {format(new Date(item.created_at), "MMM d, yyyy")}
                  </div>
                  {item.basis && (
                    <p className="text-sm mt-2 text-muted-foreground italic border-l-2 pl-3">
                      {item.basis}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-12 text-center flex flex-col items-center justify-center border-b border-dashed">
            <div className="h-12 w-12 rounded-full bg-muted flex items-center justify-center mb-3">
              <FileText className="h-6 w-6 text-muted-foreground" />
            </div>
            <h3 className="text-base font-semibold">No evidence documents</h3>
            <p className="text-sm text-muted-foreground mt-1 mb-4">
              Upload survey plans, deeds, or receipts to submit them as supporting evidence.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
