import { Router, type IRouter } from "express";
import { eq, and, sql } from "drizzle-orm";
import { db, evidenceTable, parcelsTable } from "@workspace/db";
import {
  ListParcelEvidenceParams,
  ListParcelEvidenceResponse,
  AddParcelEvidenceParams,
  AddParcelEvidenceBody,
  AddParcelEvidenceResponse,
  UpdateEvidenceParams,
  UpdateEvidenceBody,
  UpdateEvidenceResponse,
  DeleteEvidenceParams,
} from "@workspace/api-zod";

const router: IRouter = Router();

function toEvidenceShape(e: typeof evidenceTable.$inferSelect) {
  return {
    id: e.id,
    parcel_id: e.parcelId,
    document_type: e.documentType,
    file_name: e.fileName,
    notes: e.notes ?? null,
    status: e.status,
    uploaded_at: e.uploadedAt.toISOString(),
  };
}

async function recalcTrustScore(parcelId: string) {
  const [parcel] = await db.select().from(parcelsTable).where(eq(parcelsTable.id, parcelId));
  if (!parcel) return;

  const [evResult] = await db
    .select({ count: sql<number>`count(*)::int` })
    .from(evidenceTable)
    .where(and(eq(evidenceTable.parcelId, parcelId), eq(evidenceTable.status, "verified")));

  const evCount = evResult?.count ?? 0;
  let score = 10;
  if (parcel.status === "registered") score += 40;
  if (parcel.status === "disputed") score -= 10;
  score += Math.min(evCount * 12, 50);
  const trustScore = Math.min(100, Math.max(0, score));

  await db.update(parcelsTable).set({ trustScore }).where(eq(parcelsTable.id, parcelId));
}

// GET /parcels/:id/evidence
router.get("/parcels/:id/evidence", async (req, res): Promise<void> => {
  const rawId = Array.isArray(req.params.id) ? req.params.id[0] : req.params.id;
  const params = ListParcelEvidenceParams.safeParse({ id: rawId });
  if (!params.success) {
    res.status(400).json({ error: params.error.message });
    return;
  }

  const items = await db
    .select()
    .from(evidenceTable)
    .where(eq(evidenceTable.parcelId, rawId))
    .orderBy(sql`${evidenceTable.uploadedAt} DESC`);

  res.json(ListParcelEvidenceResponse.parse(items.map(toEvidenceShape)));
});

// POST /parcels/:id/evidence
router.post("/parcels/:id/evidence", async (req, res): Promise<void> => {
  const rawId = Array.isArray(req.params.id) ? req.params.id[0] : req.params.id;
  const params = AddParcelEvidenceParams.safeParse({ id: rawId });
  if (!params.success) {
    res.status(400).json({ error: params.error.message });
    return;
  }

  // Verify parcel exists
  const [parcel] = await db.select().from(parcelsTable).where(eq(parcelsTable.id, rawId));
  if (!parcel) {
    res.status(404).json({ error: "Parcel not found" });
    return;
  }

  const body = AddParcelEvidenceBody.safeParse(req.body);
  if (!body.success) {
    res.status(400).json({ error: body.error.message });
    return;
  }

  const d = body.data;
  const [ev] = await db
    .insert(evidenceTable)
    .values({
      parcelId: rawId,
      documentType: d.document_type,
      fileName: d.file_name,
      notes: d.notes ?? null,
      status: "pending_review",
    })
    .returning();

  res.status(201).json(AddParcelEvidenceResponse.parse(toEvidenceShape(ev)));
});

// PATCH /evidence/:evidenceId
router.patch("/evidence/:evidenceId", async (req, res): Promise<void> => {
  const rawId = Array.isArray(req.params.evidenceId) ? req.params.evidenceId[0] : req.params.evidenceId;
  const params = UpdateEvidenceParams.safeParse({ evidenceId: rawId });
  if (!params.success) {
    res.status(400).json({ error: params.error.message });
    return;
  }

  const body = UpdateEvidenceBody.safeParse(req.body);
  if (!body.success) {
    res.status(400).json({ error: body.error.message });
    return;
  }

  const d = body.data;
  const updates: Partial<typeof evidenceTable.$inferInsert> = {};
  if (d.status !== undefined) updates.status = d.status;
  if (d.notes !== undefined) updates.notes = d.notes;

  const [updated] = await db
    .update(evidenceTable)
    .set(updates)
    .where(eq(evidenceTable.id, rawId))
    .returning();

  if (!updated) {
    res.status(404).json({ error: "Evidence not found" });
    return;
  }

  // Recalculate trust score when evidence status changes
  if (d.status) {
    await recalcTrustScore(updated.parcelId);
  }

  res.json(UpdateEvidenceResponse.parse(toEvidenceShape(updated)));
});

// DELETE /evidence/:evidenceId
router.delete("/evidence/:evidenceId", async (req, res): Promise<void> => {
  const rawId = Array.isArray(req.params.evidenceId) ? req.params.evidenceId[0] : req.params.evidenceId;
  const params = DeleteEvidenceParams.safeParse({ evidenceId: rawId });
  if (!params.success) {
    res.status(400).json({ error: params.error.message });
    return;
  }

  const [deleted] = await db.delete(evidenceTable).where(eq(evidenceTable.id, rawId)).returning();
  if (!deleted) {
    res.status(404).json({ error: "Evidence not found" });
    return;
  }

  // Recalculate trust score after deletion
  await recalcTrustScore(deleted.parcelId);

  res.sendStatus(204);
});

export default router;
