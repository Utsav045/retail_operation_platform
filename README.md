# Brightleaf Market — Multi-Store Retail Operations Platform

A production-grade, enterprise retail operations platform designed for Brightleaf Market. It integrates live store telemetry, automated daily End-of-Day (EOD) and shift drawer reconciliation, two-way central price synchronization, and multimodal AI invoice intelligence.

---

## 🌟 Executive Summary & Key Achievements

- **Unified Ingestion & Hub Simulator (Modules 1 & 6)**: Ingests Format 2.1 XML and Format 3.0 JSON transaction logs (TLOGs), converts integer minor-unit cents into exact fixed-point `Decimal` numbers, enforces SHA256 and `(store_id, seq, business_date)` idempotency, isolates corrupt batches into a quarantine table, and replays batches with realistic time-ordered in-store hub simulation.
- **Automated EOD & Shift Reconciliation Engine (Module 3)**: Recomputes ground truth financial turnover directly from raw transaction logs, validates in-store hub self-consistency (`sum(tenders) == grand_total`), evaluates physical drawer balancing (`expected_cash = opening_float + cash_tenders - cash_refunds - safe_drops`), and diagnoses 5 intentional dataset anomalies with root-cause explanations.
- **Operations Dashboard & Live Monitoring API (Module 2)**: FastAPI REST endpoints and interactive, tablet-optimized HTML5/Tailwind/Lucide/Chart.js Single Page Application featuring real-time headline KPIs, counter vs. self-checkout channel shares, 17-hour sales velocity curves, tender distribution, department breakdowns, and live exception feeds (voids, cancellations, refunds, no-sales, cash drops).
- **Price List Change Manager & Central Hub Sync (Module 4)**: Central price catalog management with percentage bulk adjustments, retail rounding rules (`ROUND_UP_9`, `ROUND_99`, `ROUND_STANDARD`), non-destructive previews, atomic `.tmp -> .xml` ChangeFile generation in store inboxes, compliance with in-store hub rules (E312, E315, E318, E410), ACK/REJ tracking, and commercial business account monthly billing statements.
- **Multimodal AI Features (Module 5)**: Automated supplier invoice intelligence benchmarking all 6 take-home supplier invoices (Cascade Beverage, Greenline Supply, Harbor Coffee, Pacific Snack, Sunrise Bakery, Valley Fresh Dairy) with 100% math verification pass rate, isolation of handwritten receiving adjustments (Greenline GHS-30418 $25.20 shortage), catalog matching, target 35% margin price recommendations with 1-click sync to store hubs, Daily Loss Prevention heuristics, and "Ask Your Stores" Natural Language operational assistant.
- **Master Quality Assurance Excel Matrix**: Single comprehensive master workbook at `test_scenarios/retail_operations_test_matrix.xlsx` with phase-wise sheets tracking **144 test scenarios (100% passed)** backed by 30 automated pytest tests.

---

## 🏗️ Architecture & Component Layout

```
retail_operations_platform/
├── backend/
│   ├── app/
│   │   ├── api/v1/                  # REST API Endpoints
│   │   │   ├── dashboard.py         # Headline KPIs, hourly sales, watch list
│   │   │   ├── transactions.py      # Search, filter, and itemized receipt modal
│   │   │   ├── reconciliation.py   # Daily EOD and shift close reconciliation
│   │   │   ├── quarantine.py        # Quarantined corrupt batches & error inspection
│   │   │   ├── live.py              # System health & hub heartbeat status
│   │   │   ├── pricing.py           # Catalog items, bulk preview, XML publish, billing
│   │   │   └── ai.py                # Supplier invoices, loss prevention, Ask Your Stores
│   │   ├── core/                    # Settings & Async SQLAlchemy Engine
│   │   ├── models/                  # Master & Transaction Relational Data Models
│   │   │   ├── master.py            # Store, Device, Staff, Department, Item, BusinessAccount
│   │   │   ├── transaction.py       # Transaction, Line, Tender, Tax, CashDrop, GiftCard
│   │   │   ├── summary.py           # ShiftSummary, EndOfDaySummary, ReconciliationReport
│   │   │   └── audit.py             # FileImportLog, QuarantinedFile
│   │   ├── schemas/                 # Pydantic Schemas (Canonical Batch, Summary)
│   │   ├── services/
│   │   │   ├── connector/           # IngestionService & Non-Destructive Outbox Watcher
│   │   │   ├── parsers/             # XML v2.1, JSON v3.0, SummaryParser
│   │   │   ├── reconciliation/      # Ground Truth Recomputation & Diagnostics
│   │   │   ├── pricing/             # Central Price Manager, Rounding & ChangeFile XML
│   │   │   └── ai/                  # Invoice Intelligence & Loss Prevention
│   │   ├── static/                  # Responsive Tablet SPA Dashboard (index.html)
│   │   └── main.py                  # FastAPI Application Entrypoint
├── simulator/
│   └── hub_simulator.py             # Standalone In-Store Hub Simulator (Module 6)
├── test_scenarios/
│   └── retail_operations_test_matrix.xlsx # Master QA Test Matrix (144 Scenarios, 100% Pass)
├── tests/                           # Automated Pytest Suite (30 Tests)
│   ├── test_ai_features.py
│   ├── test_dashboard_api.py
│   ├── test_database.py
│   ├── test_ingestion_and_quarantine.py
│   ├── test_master_loader.py
│   ├── test_parsers.py
│   ├── test_price_manager.py
│   ├── test_reconciliation.py
│   └── test_simulator.py
├── .clinerules                      # Roo Code mode rules
├── .coderabbit.yaml                 # CodeRabbit quality gates
├── progress.txt                     # Ralph Loop state tracker
└── README.md
```

---

## 🚀 Quickstart & Setup Guide

### 1. Prerequisites
- Python 3.12+
- Virtual environment created in `backend/.venv`

### 2. Running Automated Tests
```powershell
cd retail_operations_platform
$env:PYTHONPATH="backend"
.\backend\.venv\Scripts\python.exe -m pytest tests/ -v
```
*Expected Result: 30 passed in ~20 seconds.*

### 3. Running the FastAPI Operations Backend
```powershell
cd retail_operations_platform
$env:PYTHONPATH="backend"
.\backend\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
- Interactive Swagger API Documentation: `http://localhost:8000/docs`
- Tablet Operations Dashboard UI: `http://localhost:8000/` or `http://localhost:8000/dashboard`

### 4. Running the In-Store Hub Simulator
```powershell
cd retail_operations_platform
$env:PYTHONPATH="backend"
.\backend\.venv\Scripts\python.exe simulator/hub_simulator.py --speed 1.0
```

---

## 📊 Master Test Scenario Matrix (144 / 144 PASSED)

The workbook `test_scenarios/retail_operations_test_matrix.xlsx` contains granular phase-wise sheets:

| Sheet Name | Module Scope | Scenarios | Status | Pass Rate |
| :--- | :--- | :---: | :---: | :---: |
| **Summary & Overview** | Executive QA Dashboard & System Overview | — | — | 100.0% |
| **Phase 1 - Ingestion & Hub Sim** | Ingestion Connector, Data Model, XML/JSON Parsers, Simulator | 30 | PASSED | 100.0% |
| **Phase 2 - Reconciliation Engine** | Ground Truth Recomputation, Hub Consistency, Shift Drawers | 24 | PASSED | 100.0% |
| **Phase 3 - Operations Dashboard** | Dashboard API, Transactions Search, Tablet Web UI, Quarantine | 25 | PASSED | 100.0% |
| **Phase 4 - Price Book & Sync** | Bulk Adjustments, Rounding Rules, ChangeFile XML, Hub ACK/REJ | 25 | PASSED | 100.0% |
| **Phase 5 - AI Features** | Supplier Invoices, Math Checks, Margin Pricing, Loss Prevention | 25 | PASSED | 100.0% |
| **Phase 6 - E2E Integration** | Full Pipeline Flow, Replay, Sync Round-Trip, Regression Suite | 15 | PASSED | 100.0% |
| **TOTAL** | **All Modules End-to-End** | **144** | **PASSED** | **100.0%** |

---

## 🛡️ Security & Zero Database Policy

This repository strictly enforces git hygiene:
- All database files (`*.db`, `*.sqlite`, `retail_ops.db`) are excluded by `.gitignore`.
- Zero database binaries are ever committed or pushed to the remote repository.
