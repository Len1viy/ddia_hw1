# DDIA HW 1: Items monitoring

This repository contains the allowed project scaffold: an in-memory FastAPI
CRUD service, two container instances, Prometheus scraping configuration, and
Grafana with an automatically provisioned Prometheus datasource.

## Run locally

Docker Engine and Docker Compose are required.

```sh
cp .env.example .env
docker compose up --build
```

Local endpoints:

| Service | URL |
| --- | --- |
| Grafana | http://localhost:13030 |
| Prometheus | http://localhost:19090 |
| Application, dc-1 | http://localhost:18081/health |
| Application, dc-2 | http://localhost:18082/health |

Grafana's local example login is configured in `.env`. Edit that private file
to choose your own password; do not commit it.

The two application containers use the same image and receive different
`POD_ID` and `DATACENTER` environment variables. Storage is in memory and is
separate in each container.

## CRUD API

The business API has exactly three routes, in addition to `GET /health`:

| Method | Path | Action |
| --- | --- | --- |
| POST | `/items` | Create an item; returns 201 and an integer ID. |
| GET | `/items/{id}` | Read an item; missing IDs return 404. |
| PUT | `/items/{id}` | Replace an item; missing IDs return 404. |

`POST` and `PUT` accept JSON such as:

```json
{"name": "example", "description": "optional text"}
```

Example:

```sh
curl -X POST http://localhost:18081/items \
  -H 'Content-Type: application/json' \
  -d '{"name":"example"}'
```

## Remaining student work

The stack is not yet a completed submission. The following parts require the
student's own design and implementation under the homework's AI-use rules:

- Choose and implement the Prometheus metric types, names, labels, and
  instrumentation. Add `GET /metrics` and `GET /handlers`.
- Design the dashboard generator, including PromQL aggregation, pod and
  datacenter selectors, non-editable dashboard settings, and startup ordering.
- Choose and implement the load tool, including a gradual ramp, both
  application instances, every business route, and at least two error codes.
- Document the latency metric choice and final metric names and labels here.
- Verify that `docker compose up` displays data in Grafana after 2-3 minutes,
  record a one-minute screencast, and open the final PR.

Until `/metrics` is implemented, the Prometheus scrape targets will be down.
