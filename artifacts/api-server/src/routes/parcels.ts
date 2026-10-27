import { Router, type IRouter } from "express";
import { eq, ilike, or, sql, and } from "drizzle-orm";
import { db, parcelsTable, evidenceTable } from "@workspace/db";
import {
  CreateParcelBody,
  CreateParcelResponse,
  GetParcelParams,
  GetParcelResponse,
  UpdateParcelParams,
  UpdateParcelBody,
  UpdateParcelResponse,
  DeleteParcelParams,
  ListParcelsQueryParams,
  ListParcelsResponse,
} from "@workspace/api-zod";

const router: IRouter = Router();

function generateTitleNumber(): string {
  const year = new Date().getFullYear();
  const rand = Math.floor(Math.random() * 900000) + 100000;
  return `LV-NG-${year}-${rand}`;
}

function computeTrustScore(parcel: {
  status: string;
  evidenceCount?: number;
}): number {
  let score = 10;
  if (parcel.status === "registered") score += 40;
  if (parcel.status === "disputed") score -= 10;
  const evCount = parcel.evidenceCount ?? 0;
  score += Math.min(evCount * 12, 50);
  return Math.min(100, Math.max(0, score));
}

// GET /parcels
router.get("/parcels", async (req, res): Promise<void> => {
  const query = ListParcelsQueryParams.safeParse(req.query);
  if (!query.success) {
    res.status(400).json({ error: query.error.message });
    return;
  }

  const { status, parcel_type, state, search, limit = 50, offset = 0 } = query.data;

  const conditions = [];
  if (status) conditions.push(eq(parcelsTable.status, status));
  if (parcel_type) conditions.push(eq(parcelsTable.parcelType, parcel_type));
  if (state) conditions.push(eq(parcelsTable.state, state));
  if (search) {
    conditions.push(
      or(
        ilike(parcelsTable.titleNumber, `%${search}%`),
        ilike(parcelsTable.ownerName, `%${search}%`),
        ilike(parcelsTable.locationAddress, `%${search}%`),
      ),
    );
  }

  const where = conditions.length > 0 ? and(...conditions) : undefined;

  const [items, countResult] = await Promise.all([
    db
      .select()
      .from(parcelsTable)
      .where(where)
      .limit(Number(limit))
      .offset(Number(offset))
      .orderBy(sql`${parcelsTable.createdAt} DESC`),
    db.select({ count: sql<number>`count(*)::int` }).from(parcelsTable).where(where),
  ]);

  const total = countResult[0]?.count ?? 0;

  const mapped = items.map((p) => ({
    ...p,
    area_sqm: Number(p.areaSqm),
    title_number: p.titleNumber,
    owner_name: p.ownerName,
    owner_phone: p.ownerPhone ?? null,
    owner_email: p.ownerEmail ?? null,
    location_address: p.locationAddress,
    parcel_type: p.parcelType,
    trust_score: p.trustScore,
    latitude: p.latitude ?? null,
    longitude: p.longitude ?? null,
    created_at: p.createdAt.toISOString(),
    updated_at: p.updatedAt.toISOString(),
  }));

  res.json(ListParcelsResponse.parse({ items: mapped, total }));
});

// POST /parcels
router.post("/parcels", async (req, res): Promise<void> => {
  const parsed = CreateParcelBody.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: parsed.error.message });
    return;
  }

  const d = parsed.data;
  const titleNumber = generateTitleNumber();

  const [parcel] = await db
    .insert(parcelsTable)
    .values({
      titleNumber,
      ownerName: d.owner_name,
      ownerPhone: d.owner_phone ?? null,
      ownerEmail: d.owner_email ?? null,
      locationAddress: d.location_address,
      state: d.state,
      lga: d.lga,
      areaSqm: String(d.area_sqm),
      parcelType: d.parcel_type,
      status: "pending",
      trustScore: 10,
      latitude: d.latitude ?? null,
      longitude: d.longitude ?? null,
    })
    .returning();

  res.status(201).json(
    CreateParcelResponse.parse({
      ...parcel,
      area_sqm: Number(parcel.areaSqm),
      title_number: parcel.titleNumber,
      owner_name: parcel.ownerName,
      owner_phone: parcel.ownerPhone ?? null,
      owner_email: parcel.ownerEmail ?? null,
      location_address: parcel.locationAddress,
      parcel_type: parcel.parcelType,
      trust_score: parcel.trustScore,
      latitude: parcel.latitude ?? null,
      longitude: parcel.longitude ?? null,
      created_at: parcel.createdAt.toISOString(),
      updated_at: parcel.updatedAt.toISOString(),
    }),
  );
});

// GET /parcels/:id
router.get("/parcels/:id", async (req, res): Promise<void> => {
  const rawId = Array.isArray(req.params.id) ? req.params.id[0] : req.params.id;

  const [parcel] = await db.select().from(parcelsTable).where(eq(parcelsTable.id, rawId));
  if (!parcel) {
    res.status(404).json({ error: "Parcel not found" });
    return;
  }

  res.json(
    GetParcelResponse.parse({
      ...parcel,
      area_sqm: Number(parcel.areaSqm),
      title_number: parcel.titleNumber,
      owner_name: parcel.ownerName,
      owner_phone: parcel.ownerPhone ?? null,
      owner_email: parcel.ownerEmail ?? null,
      location_address: parcel.locationAddress,
      parcel_type: parcel.parcelType,
      trust_score: parcel.trustScore,
      latitude: parcel.latitude ?? null,
      longitude: parcel.longitude ?? null,
      created_at: parcel.createdAt.toISOString(),
      updated_at: parcel.updatedAt.toISOString(),
    }),
  );
});

// PATCH /parcels/:id
router.patch("/parcels/:id", async (req, res): Promise<void> => {
  const rawId = Array.isArray(req.params.id) ? req.params.id[0] : req.params.id;
  const params = UpdateParcelParams.safeParse({ id: rawId });
  if (!params.success) {
    res.status(400).json({ error: params.error.message });
    return;
  }

  const body = UpdateParcelBody.safeParse(req.body);
  if (!body.success) {
    res.status(400).json({ error: body.error.message });
    return;
  }

  const d = body.data;

  // Build update object (only set provided fields)
  const updates: Partial<typeof parcelsTable.$inferInsert> = {};
  if (d.owner_name !== undefined) updates.ownerName = d.owner_name;
  if (d.owner_phone !== undefined) updates.ownerPhone = d.owner_phone;
  if (d.owner_email !== undefined) updates.ownerEmail = d.owner_email;
  if (d.location_address !== undefined) updates.locationAddress = d.location_address;
  if (d.state !== undefined) updates.state = d.state;
  if (d.lga !== undefined) updates.lga = d.lga;
  if (d.area_sqm !== undefined) updates.areaSqm = String(d.area_sqm);
  if (d.parcel_type !== undefined) updates.parcelType = d.parcel_type;
  if (d.status !== undefined) updates.status = d.status;
  if (d.latitude !== undefined) updates.latitude = d.latitude;
  if (d.longitude !== undefined) updates.longitude = d.longitude;

  if (Object.keys(updates).length === 0) {
    const [existing] = await db.select().from(parcelsTable).where(eq(parcelsTable.id, rawId));
    if (!existing) {
      res.status(404).json({ error: "Parcel not found" });
      return;
    }
    res.json(
      UpdateParcelResponse.parse({
        ...existing,
        area_sqm: Number(existing.areaSqm),
        title_number: existing.titleNumber,
        owner_name: existing.ownerName,
        owner_phone: existing.ownerPhone ?? null,
        owner_email: existing.ownerEmail ?? null,
        location_address: existing.locationAddress,
        parcel_type: existing.parcelType,
        trust_score: existing.trustScore,
        latitude: existing.latitude ?? null,
        longitude: existing.longitude ?? null,
        created_at: existing.createdAt.toISOString(),
        updated_at: existing.updatedAt.toISOString(),
      }),
    );
    return;
  }

  // Recalculate trust score when status changes
  if (d.status) {
    const evidenceCount = await db
      .select({ count: sql<number>`count(*)::int` })
      .from(evidenceTable)
      .where(and(eq(evidenceTable.parcelId, rawId), eq(evidenceTable.status, "verified")));
    const evCount = evidenceCount[0]?.count ?? 0;
    updates.trustScore = computeTrustScore({ status: d.status, evidenceCount: evCount });
  }

  const [updated] = await db
    .update(parcelsTable)
    .set(updates)
    .where(eq(parcelsTable.id, rawId))
    .returning();

  if (!updated) {
    res.status(404).json({ error: "Parcel not found" });
    return;
  }

  res.json(
    UpdateParcelResponse.parse({
      ...updated,
      area_sqm: Number(updated.areaSqm),
      title_number: updated.titleNumber,
      owner_name: updated.ownerName,
      owner_phone: updated.ownerPhone ?? null,
      owner_email: updated.ownerEmail ?? null,
      location_address: updated.locationAddress,
      parcel_type: updated.parcelType,
      trust_score: updated.trustScore,
      latitude: updated.latitude ?? null,
      longitude: updated.longitude ?? null,
      created_at: updated.createdAt.toISOString(),
      updated_at: updated.updatedAt.toISOString(),
    }),
  );
});

// DELETE /parcels/:id
router.delete("/parcels/:id", async (req, res): Promise<void> => {
  const rawId = Array.isArray(req.params.id) ? req.params.id[0] : req.params.id;
  const params = DeleteParcelParams.safeParse({ id: rawId });
  if (!params.success) {
    res.status(400).json({ error: params.error.message });
    return;
  }

  const [deleted] = await db.delete(parcelsTable).where(eq(parcelsTable.id, rawId)).returning();
  if (!deleted) {
    res.status(404).json({ error: "Parcel not found" });
    return;
  }

  res.sendStatus(204);
});

export default router;
