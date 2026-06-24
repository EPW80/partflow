# web/ — Next.js Self-Service App

Read-only presentation layer over dbt marts for non-technical supply chain users.

## Rules
- IMPORTANT: Read-only. This app NEVER writes to Postgres — no INSERT/UPDATE/DELETE, no migrations. Connect with a read-only DB role so a bug can't mutate the warehouse.
- IMPORTANT: Don't compute KPIs here. If a number isn't in a mart, the fix is a new mart column in `transform/`, not a calculation in a component.
- Do fetch data in Server Components / route handlers; reserve client components for interactivity only.
- Do design for non-technical readers: plain-language labels, a tooltip defining each KPI, sensible default filters, no jargon in the UI.
- Don't use `any`. Type query results against the mart schema.

## Stack
Next.js (App Router), TypeScript, server-side Postgres queries via a read-only role, charts for trend views.

## Test before commit
`npm run typecheck && npm run test`. Must build with zero type errors.
