# Brightleaf Market — Project Roadmap & Phase Tracker

## Unified 4-Pillar Stack
1. **GSD Protocol**: Spec-driven architecture & roadmap lock.
2. **Roo Code**: Strict context hygiene & `.clinerules`.
3. **Ralph Loop**: Single atomic task progression via `progress.txt`.
4. **CodeRabbit**: Zero hallucination, strict decimal precision, quality gatekeeper.

---

## Phase Breakdown

### [x] Phase 1: Ingestion Pipeline & Hub Simulator (COMPLETED)
- Relational schema with exact `Numeric(12, 2)` precision.
- Master data loaders (stores, devices, staff, business accounts, pricelist XML).
- Format 2.1 XML and Format 3.0 JSON TLOG parsers.
- Non-destructive connector with SHA256 & transaction-level idempotency and quarantine engine.
- Standalone in-store hub simulator with replay and ACK/REJ validation rules (E301-E410).
- 11 automated pytest suites (100% pass rate).
- Excel Test Matrix: Sheet `Phase 1 - Ingestion & Hub Sim` (30 test scenarios, 100% pass rate).

### [>] Phase 2: Daily EOD & Shift Reconciliation Engine (CURRENT)
- Parser for `SHIFT_*` and `EOD_*` summaries (Format 2.1 XML and Format 3.0 JSON).
- Ground truth re-computation engine from raw transaction logs.
- Shift cash reconciliation: `expected_cash = opening_float + cash_tenders - cash_refunds - completed_cash_drops`.
- EOD summary comparison: department sales, tenders, taxes, gift cards, and grand totals.
- Hub self-consistency validator (`sum(tenders) == grand_total`, `sum(depts) == net_sales`).
- Discrepancy detector & root cause diagnostic analyzer (explaining deliberate data flaws).
- Status classifier: `MATCHED`, `MISMATCH`, `REVIEW_REQUIRED`.
- Automated test suite in `tests/test_reconciliation.py`.
- Excel Test Matrix: Add Sheet `Phase 2 - Reconciliation Engine` with full execution proofs.

### [ ] Phase 3: Operations Dashboard & Live Monitoring API (PENDING)
- FastAPI backend endpoints for daily store view, sales by hour, tender breakdowns, watch list.
- Reactive live feed / polling for incoming hub batches.
- Transactions search, filter, and detail drilldown.
- Quarantined files and flagged records management API.

### [ ] Phase 4: Price List Change Manager & Full Two-Way Sync (PENDING)
- Central price list catalog with variant pricing.
- Bulk price adjustments and single item edits.
- Specification-compliant change file generator for `inbox/`.
- ACK/REJ tracking with retry capability for rejected changes.
- Commercial business account statements and charge auditing.

### [ ] Phase 5: AI Features (Invoice Capture & Loss Prevention) (PENDING)
- 5A: Supplier invoice text/photo extraction (PDF text, OCR/multimodal).
- Deterministic calculation checks on invoice math.
- Price book candidate matching and margin calculation.
- 5C: Daily loss-prevention summary of unusual cashier patterns.
