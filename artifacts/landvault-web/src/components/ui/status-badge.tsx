import { cn } from "@/lib/utils";
import { type ParcelStatus, type EvidenceStatus } from "@workspace/api-client-react";

interface StatusBadgeProps {
  status: ParcelStatus | EvidenceStatus;
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  let label = status.replace("_", " ");
  label = label.charAt(0).toUpperCase() + label.slice(1);

  let variantClass = "bg-muted text-muted-foreground";

  switch (status) {
    case "ACTIVE":
      variantClass = "bg-emerald-600/10 text-emerald-600 border-emerald-600/20 border";
      break;
    case "ARCHIVED":
      variantClass = "bg-slate-500/10 text-slate-600 border-slate-500/20 border";
      break;
    // Evidence lifecycle (B5 IMVP-5) — RECEIVED/HASHED/SEALED, a storage-
    // integrity state, never an ownership/legal-validity claim. IMVP-5
    // never reaches SEALED (no code path calls seal()); the case is here
    // only because the domain/generated type already includes it.
    case "RECEIVED":
      variantClass = "bg-amber-500/10 text-amber-600 border-amber-500/20 border";
      break;
    case "HASHED":
      variantClass = "bg-emerald-600/10 text-emerald-600 border-emerald-600/20 border";
      break;
    case "SEALED":
      variantClass = "bg-blue-600/10 text-blue-600 border-blue-600/20 border";
      break;
  }

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide",
        variantClass,
        className
      )}
    >
      {label}
    </span>
  );
}
