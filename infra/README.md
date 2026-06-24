# infra/ — Local Stack

One-command local environment for PartFlow. All data is synthetic.

## Services & ports

| Service  | URL                    | Default login     | Role |
| -------- | ---------------------- | ----------------- | ---- |
| Metabase | http://localhost:3000  | set on first load | Self-service exploration over marts |
| Airflow  | http://localhost:8080  | `airflow` / `airflow` | Orchestration + DQ gates |
| Grafana  | http://localhost:3001  | `admin` / `admin` | Ops/time-series monitoring |
| Postgres | `localhost:5432`       | `partflow` / `partflow` | Warehouse (single source of truth) |
| web      | http://localhost:3002  | —                 | Next.js self-service app (Phase 7) |

A single Postgres instance backs three databases: `partflow` (warehouse),
`airflow` (orchestrator metadata), and `metabase` (BI app state).

## Run

```bash
cp .env.example .env          # optional — compose has sensible defaults
docker compose -f infra/docker-compose.yml up -d
docker compose -f infra/docker-compose.yml ps     # all services healthy
docker compose -f infra/docker-compose.yml down    # stop (add -v to wipe data)
```

The compose file uses `${VAR:-default}` fallbacks, so it boots without a `.env`.
Provide `.env` to override credentials; never commit it.
