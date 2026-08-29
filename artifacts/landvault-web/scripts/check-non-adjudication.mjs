#!/usr/bin/env node
// Engineering Rule #10 (LV-000 v1.8 Article IV §4) — frontend extension.
//
// Governance Authority approved extending the existing backend-only non-adjudication check
// (backend/tests/support/non_adjudication.py) to user-facing frontend source text, on the
// explicit condition that this stays a narrow addition: same detection semantics, no weakening
// of the backend check, no scanner redesign.
//
// This blocklist MUST be kept in sync by hand with `ADJUDICATION_PHRASES` in
// backend/tests/support/non_adjudication.py — there is no automatic cross-language sync (Python
// AST tooling can't easily be shared with a Node script without a new dependency, which would
// itself need separate approval). If the backend list changes, update this one in the same PR.
//
// Zero new dependencies: plain Node ESM, run directly (`node scripts/check-non-adjudication.mjs`).
//
// Usage:
//   node scripts/check-non-adjudication.mjs           # scan real src/, exit 1 on violation
//   node scripts/check-non-adjudication.mjs --self-test # run the embedded false-positive/positive
//                                                         # tests instead (no test framework exists
//                                                         # in this workspace to hang a real test on)

import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, extname } from "node:path";
import { fileURLToPath } from "node:url";

const SRC_ROOT = fileURLToPath(new URL("../src", import.meta.url));
const SCAN_EXTENSIONS = new Set([".ts", ".tsx"]);

// Verbatim copy of ADJUDICATION_PHRASES from backend/tests/support/non_adjudication.py.
// Deliberately multi-word phrases expressing a determination-of-right claim — never bare single
// words like "owner", "confirmed", "verified", or "conflict" in isolation (see that file's own
// docstring for the false-positive reasoning — e.g. `current_owner_name` as a field identifier
// must never trip this).
export const ADJUDICATION_PHRASES = [
  "confirmed owner",
  "confirmed as owner",
  "confirmed as the owner",
  "confirmed as its owner",
  "verified owner",
  "verified as owner",
  "verified as the owner",
  "rightful owner",
  "true owner",
  "real owner",
  "actual owner",
  "the legal owner",
  "legal owner of",
  "legally owns",
  "officially owns",
  "is the owner of this",
  "owns this parcel",
  "owner of record confirmed",
  "confirmed ownership",
  "confirms ownership",
  "ownership is confirmed",
  "ownership has been confirmed",
  "ownership has been determined",
  "ownership is determined",
  "determined ownership",
  "determined the owner",
  "determined to be the owner",
  "title is confirmed",
  "title has been confirmed",
  "title is valid",
  "valid title",
  "confirms title",
  "confirms clear title",
  "resolves the ownership",
  "resolves this claim",
  "resolves the claim",
  "wins the claim",
  "wins the dispute",
  "invalidates the claim",
  "adjudicated ownership",
  "adjudicates ownership",
  "landvault has determined",
  "landvault confirms ownership",
  "landvault has verified ownership",
];

export function findViolations(text) {
  const lowered = text.toLowerCase();
  return ADJUDICATION_PHRASES.filter((phrase) => lowered.includes(phrase));
}

function* walk(dir) {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    const st = statSync(full);
    if (st.isDirectory()) {
      yield* walk(full);
    } else if (SCAN_EXTENSIONS.has(extname(full))) {
      yield full;
    }
  }
}

function scanSource(root) {
  const hits = [];
  for (const file of walk(root)) {
    const lines = readFileSync(file, "utf8").split("\n");
    lines.forEach((line, i) => {
      const violations = findViolations(line);
      if (violations.length > 0) {
        hits.push({ file, line: i + 1, violations, text: line.trim() });
      }
    });
  }
  return hits;
}

function runSelfTest() {
  const failures = [];

  // Positive: a real violation phrase must be detected.
  const positive = findViolations("This document confirms ownership of the parcel.");
  if (positive.length === 0) failures.push("expected a violation for 'confirms ownership', found none");

  // False-positive guards: legitimate single-word usage must NOT trigger, mirroring the backend
  // scanner's own reasoning for why single words are excluded from the blocklist.
  const falsePositiveCases = [
    "current_owner_name",
    "The evidence status is verified.",
    "A spatial conflict was detected between two parcels.",
    "confirmed",
    "owner",
  ];
  for (const text of falsePositiveCases) {
    const hits = findViolations(text);
    if (hits.length > 0) {
      failures.push(`expected no violation for ${JSON.stringify(text)}, got ${JSON.stringify(hits)}`);
    }
  }

  if (failures.length > 0) {
    console.error("check-non-adjudication self-test FAILED:");
    for (const f of failures) console.error(`  - ${f}`);
    process.exit(1);
  }
  console.log("check-non-adjudication self-test passed.");
}

function main() {
  if (process.argv.includes("--self-test")) {
    runSelfTest();
    return;
  }

  const hits = scanSource(SRC_ROOT);
  if (hits.length > 0) {
    console.error("Non-adjudication violation(s) found in frontend source:");
    for (const hit of hits) {
      console.error(`  ${hit.file}:${hit.line} matched ${JSON.stringify(hit.violations)} — ${hit.text}`);
    }
    process.exit(1);
  }
  console.log("check-non-adjudication: no violations found.");
}

main();
