# Brightleaf Retail Operations Platform — Frontend Specification (GSD Phase 7 - Revised)

## Aesthetic & Design Rules
- **Pinterest-Inspired Light Aesthetic**: Soft, airy, warm off-white canvas (`#F8FAFC` / `#FFFFFF`), 1 single dark primary charcoal (`#0F172A`) for high-contrast typography, and gentle pastel highlights (mint green `#ECFDF5`, amber sand `#FFFBEB`, soft coral rose `#FEF2F2`, arctic blue `#EFF6FF`).
- **Theme Toggle**: 1-click Light / Dark Mode switch with `localStorage` persistence.
- **Universal Tooltip Engine**: Every metric, calculation formula, status badge, and technical code is paired with a plain-English explanatory tooltip.
- **Simplified Terminology**: Plain retail wording alongside technical codes (e.g., *"Money Expected in Till"*, *"Cancelled Scanned Items"*).
- **Full Responsiveness**: 100% fluid layouts across mobile (375px+), tablet (768px-1024px), laptop (1280px), and wide desktop (1920px).

## 6 Dedicated Screens
1. **Store Overview & Daily Pulse (`/overview`)**: Top 5 KPI cards, interactive SVG hourly velocity chart, department/tender mix, live exception feed.
2. **Daily Register & Shift Cash Audit (`/reconciliation`)**: Ground truth vs Hub stated comparison, plain-English root cause diagnostics, cashier till balance ledger with formula tooltips.
3. **Transactions & Virtual Thermal Receipt (`/transactions`)**: Responsive filters, high-density ledger, virtual thermal POS receipt drawer with strikethrough voids.
4. **Central Price Book & Store Sync (`/pricing`)**: Catalog browser, bulk pricing assistant with rounding rules, diff preview, hub sync monitor, and commercial statements.
5. **AI Intelligence & Loss Prevention (`/intelligence`)**: Supplier invoice audits, Greenline receiving shortage callout, 35% margin deployer, loss prevention radar, and "Ask Your Stores" console.
6. **System Integrity & Quarantine Vault (`/system`)**: Store hub connection health and raw payload inspector modal.
