# Specification: Phase 12 — Universal Soft Delete Architecture & Hard Delete Prevention

## Objective
Enforce a universal, non-destructive Soft Delete architecture across all database entities in Brightleaf Market. Hard deletes (`DELETE FROM ...` or `session.delete(...)`) are strictly prohibited and structurally prevented. Every entity tracks `is_deleted` and `deleted_at`, standard queries automatically filter active records, and an ORM interceptor guarantees zero hard deletes can ever occur.

---

## 1. Architectural Components

### 1.1 `SoftDeleteMixin` (`backend/app/models/base.py`)
- Columns:
  - `is_deleted`: `Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)`
  - `deleted_at`: `Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)`
- Methods:
  - `soft_delete()`: Sets `is_deleted = True` and `deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)`.
  - `restore()`: Sets `is_deleted = False` and `deleted_at = None`.

### 1.2 Entity Coverage
Applied across all SQLAlchemy models:
- **Master Data**: `Store`, `Device`, `Staff`, `Department`, `TaxGroup`, `Item`, `BusinessAccount`
- **Transactions & Details**: `Transaction`, `TransactionLine`, `TransactionTender`, `TransactionTax`, `GiftCardActivity`, `CashDrop`
- **Reconciliation & Audits**: `ShiftSummary`, `EndOfDaySummary`, `QuarantinedFile`, `FileImportLog`, `SecurityAuditLog`
- **Identity & Auth**: `User`

### 1.3 SQLAlchemy Event Interceptor (`backend/app/core/database.py`)
- Hook `before_flush` on SQLAlchemy Session:
  - Intercepts any call to `session.delete(instance)` where `hasattr(instance, "soft_delete")`.
  - Expunges the deletion and invokes `instance.soft_delete()`.
  - Re-adds instance to session as modified, ensuring zero SQL `DELETE` queries are ever generated.

### 1.4 Query Isolation
- Active entity queries filter `is_deleted == False`.
- In `/api/v1/meta/options`, only non-deleted stores, departments, and accounts are exposed.
- In `/api/v1/pricing/items`, `/api/v1/transactions`, `/api/v1/quarantine`, only active records are queried unless explicitly requested with an `include_deleted=True` flag for admin auditing.

### 1.5 REST Soft-Delete Endpoints
- `DELETE /api/v1/pricing/items/{item_code}`: Soft deletes product.
- `POST /api/v1/pricing/items/{item_code}/restore`: Restores soft-deleted product.
- `DELETE /api/v1/transactions/{transaction_id}`: Soft deletes transaction.
- `DELETE /api/v1/quarantine/{quarantine_id}`: Soft deletes quarantined file record.
- `DELETE /api/v1/auth/users/{user_id}`: Soft deletes user account.

---

## 2. Verification Protocol
1. Schema migration adds `is_deleted` and `deleted_at` with indexes across SQLite tables.
2. Unit and integration tests verify:
   - Soft delete sets `is_deleted=True` and `deleted_at`.
   - Direct `session.delete()` is intercepted and converted to soft delete.
   - Rows remain intact in SQLite (row count does not decrease).
   - Standard queries omit soft-deleted records.
   - Restore restores records to active queries.
3. Master Excel Matrix updated with Sheet 'Phase 12 - Soft Delete'.
