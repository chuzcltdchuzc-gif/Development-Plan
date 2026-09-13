import { pgTable, text, uuid, timestamp } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod/v4";
import { parcelsTable } from "./parcels";

export const evidenceTable = pgTable("evidence", {
  id: uuid("id").primaryKey().defaultRandom(),
  parcelId: uuid("parcel_id").notNull().references(() => parcelsTable.id, { onDelete: "cascade" }),
  documentType: text("document_type").notNull(),
  // survey_plan | certificate_of_occupancy | deed_of_assignment | affidavit | purchase_receipt | governors_consent | court_order | other
  fileName: text("file_name").notNull(),
  notes: text("notes"),
  status: text("status").notNull().default("pending_review"), // pending_review | verified | rejected
  uploadedAt: timestamp("uploaded_at", { withTimezone: true }).notNull().defaultNow(),
});

export const insertEvidenceSchema = createInsertSchema(evidenceTable).omit({
  id: true,
  uploadedAt: true,
});
export type InsertEvidence = z.infer<typeof insertEvidenceSchema>;
export type Evidence = typeof evidenceTable.$inferSelect;
