# Brightleaf Market — Multi-Store Retail Operations Platform

A modern retail operations and reconciliation platform with in-store hub synchronization, AI-powered invoice capture, and automated end-of-day auditing.

---

## Architecture Overview

- **`backend/`**: FastAPI (Python 3.12) REST API & WebSocket server with exact fixed-point decimal arithmetic for financial integrity.
- **`frontend/`**: React + Vite + TypeScript dashboard for live sales, transaction exploration, EOD reconciliation, and price management.
- **`simulator/`**: Standalone in-store hub simulator replaying 14 business days of transaction logs (v2 XML and v3 JSON) and handling change files.
- **`tests/`**: Unit and integration test suites validating parser idempotency, bad-file quarantine, and reconciliation math.
- **`docs/`**: Architecture diagrams, ER diagrams, and API specifications.

---

## 4-Pillar Autonomous Engineering Stack

This project strictly adheres to:
1. **Get Shit Done (GSD)**: Spec-driven, context-engineered architecture.
2. **Roo Code**: Autonomous IDE execution via `.clinerules`.
3. **Ralph Loop**: Single-task iterative execution loop via `progress.txt`.
4. **CodeRabbit**: Continuous code review quality gates via `.coderabbit.yaml`.
