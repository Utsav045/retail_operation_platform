# Phase 2 Specification: Daily EOD & Shift Reconciliation Engine (Module 3)

## 1. Objectives & Business Rules
The primary objective of Module 3 is to provide deterministic, penny-accurate auditing of store operations by comparing:
1. **Computed Ground Truth**: Derived from the ingested transaction logs (TLOGs).
2. **Reported Hub Summaries**: Extracted from `SHIFT_*` and `EOD_*` files written by the in-store hub.

### Core Mathematical Definitions
- **Net Sales** = $\sum \text{completed item lines} - \sum \text{refund item lines}$ (excluding lines with `is_void=True`).
- **Taxes** = $\sum \text{tax lines per group } (T0, T1, T2)$ calculated on taxable base and rounded half-up to cent.
- **Gift Card Loads** = Money received that store owes as future purchasing power. It is **not** a sale and is **not** taxed.
- **Grand Total** = $\text{Net Sales} + \text{Tax} + \text{Gift Card Loads} == \sum \text{Tenders}$.
- **Expected Cash for Shift** = $\text{Opening Float} + \text{Cash Tenders} - \text{Cash Refunds} - \text{Completed Cash Drops}$.
- **Cash Variance (Over/Short)** = $\text{Counted Cash} - \text{Expected Cash}$.

---

## 2. Architectural Components

### 2.1 Summary Parsers (`app/services/parsers/summary_parser.py`)
- **XML v2 Parser**:
  - `ShiftClose`: Extracts `<Tenders>`, `<GiftCards>`, `<CashDrops>`, `<Exceptions>`, `<Cash openingFloat countedCash>`, `<AccountCharges>`.
  - `EndOfDay`: Extracts `<Departments>`, `<Taxes>`, `<Tenders>`, `<GiftCards>`, `<CashDrops>`, `<Exceptions>`, `<Totals>`.
- **JSON v3 Parser**:
  - Converts all `*Minor` integer fields to exact `Decimal(12, 2)` dollars.
  - Normalizes department codes (stripping leading zeros where appropriate).

### 2.2 Relational Models (`app/models/summary.py`)
- Expand `ShiftSummary` and `EndOfDaySummary` with granular JSON or relational fields to capture reported department, tender, and tax breakdowns.
- Create `ReconciliationReport` model to store computed vs. reported comparison results and discrepancy causes.

### 2.3 Reconciliation Engine (`app/services/reconciliation/engine.py`)
- Recomputes ground truth from `transactions`, `transaction_lines`, `transaction_tenders`, `transaction_taxes`, `cash_drops`.
- Evaluates self-consistency of the hub summary:
  - $\sum \text{Reported Departments} \stackrel{?}{=} \text{Reported Net Sales}$
  - $\sum \text{Reported Tenders} \stackrel{?}{=} \text{Reported Grand Total}$
  - $\text{Reported Net Sales} + \text{Reported Tax} + \text{Reported Gift Cards} \stackrel{?}{=} \text{Reported Grand Total}$
- Compares computed vs. reported:
  - Category-by-category comparison (Departments, Tenders, Taxes, Gift Cards, Grand Total, Shift Cash).
  - Assigns status: `MATCHED`, `MISMATCH`, or `REVIEW_REQUIRED`.

### 2.4 Discrepancy Diagnostics & Root Cause Analysis
- Diagnostic heuristics:
  - Check for voided lines improperly included in summary totals.
  - Check for quarantined or missing TLOG batch files.
  - Check for cash drawer theft or cashier shortage (`countedCash != expectedCash`).
  - Isolate the specific transaction or sequence number causing the delta.

---

## 3. Verification & Quality Gates
- `tests/test_reconciliation.py`:
  - 10+ automated test cases covering XML and JSON summary parsing, EOD reconciliation, shift cash reconciliation, and known discrepancy discovery.
- Update `test_scenarios/retail_operations_test_matrix.xlsx`:
  - Add sheet `Phase 2 - Reconciliation Engine`.
  - Record 20+ test scenarios with inputs, expected behavior, actual observed result, and PASSED status.
