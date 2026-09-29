import { Router, type IRouter } from "express";
import { eq, sql } from "drizzle-orm";
import { db, parcelsTable, evidenceTable } from "@workspace/db";
import { GetDashboardStatsResponse } from "@workspace/api-zod";

const router: IRouter = Router();

router.get("/dashboard/stats", async (_req, res): Promise<void> => {
  const [
    totalResult,
    registeredResult,
    pendingResult,
    disputedResult,
    avgTrustResult,
    recentResult,
    evVerifiedResult,
    evPendingResult,
  ] = await Promise.all([
    db.select({ count: sql<number>`count(*)::int` }).from(parcelsTable),
    db.select({ count: sql<number>`count(*)::int` }).from(parcelsTable).where(eq(parcelsTable.status, "registered")),
    db.select({ count: sql<number>`count(*)::int` }).from(parcelsTable).where(eq(parcelsTable.status, "pending")),
    db.select({ count: sql<number>`count(*)::int` }).from(parcelsTable).where(eq(parcelsTable.status, "disputed")),
    db.select({ avg: sql<number>`coalesce(avg(trust_score), 0)` }).from(parcelsTable),
    db
      .select({ count: sql<number>`count(*)::int` })
      .from(parcelsTable)
      .where(sql`created_at >= now() - interval '7 days'`),
    db.select({ count: sql<number>`count(*)::int` }).from(evidenceTable).where(eq(evidenceTable.status, "verified")),
    db.select({ count: sql<number>`count(*)::int` }).from(evidenceTable).where(eq(evidenceTable.status, "pending_review")),
  ]);

  res.json(
    GetDashboardStatsResponse.parse({
      total_parcels: totalResult[0]?.count ?? 0,
      registered_parcels: registeredResult[0]?.count ?? 0,
      pending_parcels: pendingResult[0]?.count ?? 0,
      disputed_parcels: disputedResult[0]?.count ?? 0,
      avg_trust_score: Math.round(Number(avgTrustResult[0]?.avg ?? 0)),
      registrations_last_7_days: recentResult[0]?.count ?? 0,
      evidence_verified: evVerifiedResult[0]?.count ?? 0,
      evidence_pending: evPendingResult[0]?.count ?? 0,
    }),
  );
});

export default router;
