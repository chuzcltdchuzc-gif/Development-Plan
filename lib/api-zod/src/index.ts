export * from "./generated/api";
// Not a blanket `export * from "./generated/types"`: orval's "zod" target
// (mode: "split") emits a standalone TS-interface file per schema under
// generated/types/ *and* a same-named zod-schema `const` in generated/api.ts
// for any operation with named query parameters (e.g. IMVP-5's
// UploadParcelEvidenceParams) — re-exporting both from here is an ambiguous
// double export TypeScript rejects. generated/api.ts's zod schemas are the
// package's actual useful surface (nothing in this workspace consumes the
// parallel plain-type barrel today); a consumer that wants a plain type can
// still derive one with `z.infer<typeof X>` or import the specific file
// directly from generated/types/.
