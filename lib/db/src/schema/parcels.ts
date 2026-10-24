import { pgTable, text, uuid, numeric, timestamp, doublePrecision, integer } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod/v4";

export const parcelsTable = pgTable("parcels", {
  id: uuid("id").primaryKey().defaultRandom(),
  titleNumber: text("title_number").notNull().unique(),
  ownerName: text("owner_name").notNull(),
  ownerPhone: text("owner_phone"),
  ownerEmail: text("owner_email"),
  locationAddress: text("location_address").notNull(),
  state: text("state").notNull(),
  lga: text("lga").notNull(),
  areaSqm: numeric("area_sqm", { precision: 12, scale: 2 }).notNull(),
  parcelType: text("parcel_type").notNull(), // residential | commercial | agricultural | industrial
  status: text("status").notNull().default("pending"), // pending | registered | disputed | cancelled
  trustScore: integer("trust_score").notNull().default(0),
  latitude: doublePrecision("latitude"),
  longitude: doublePrecision("longitude"),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow().$onUpdate(() => new Date()),
});

export const insertParcelSchema = createInsertSchema(parcelsTable).omit({
  id: true,
  titleNumber: true,
  trustScore: true,
  createdAt: true,
  updatedAt: true,
});
export type InsertParcel = z.infer<typeof insertParcelSchema>;
export type Parcel = typeof parcelsTable.$inferSelect;
