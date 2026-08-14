terraform {
  required_version = ">= 1.9"
}

# Cloud provider (AWS vs Azure) is an open decision — see docs/REBUILD_PLAN.md
# §6 and CLAUDE.md. Provider config and resources land here once that
# decision is ratified and Phase 10 (Production Readiness) begins; local
# development runs entirely on Docker Compose (infra/docker/) until then.
