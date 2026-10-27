# DDIA HW 1: Items monitoring

This repository contains an in-memory FastAPI CRUD service, two instrumented
container instances, Prometheus scraping configuration, and Grafana with an
automatically provisioned Prometheus datasource.

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
| Metrics, dc-1 | http://localhost:18081/metrics |
| Metrics, dc-2 | http://localhost:18082/metrics |

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

## HTTP metrics (part 1)

Each application exposes Prometheus text at `GET /metrics`. A middleware
observes completed requests to the three business routes. `GET /health` and
`GET /metrics` are excluded, so health checks and Prometheus scrapes do not
affect business traffic measurements. Unmatched URLs are also excluded because
they have no business route template.

| Metric | Type | Labels | Use |
| --- | --- | --- | --- |
| `items_http_requests_total` | Counter | `pod_id`, `datacenter`, `method`, `route`, `status_code` | RPS and response counts, including 4xx/5xx errors by exact status code. |
| `items_http_request_duration_seconds` | Histogram | `pod_id`, `datacenter`, `method`, `route` (`le` on buckets) | Response latency p50/p95/p99. |

`pod_id` and `datacenter` come from the `POD_ID` and `DATACENTER` environment
variables. The `route` label is the registered template, such as
`/items/{id}`, never the requested item ID. This keeps the number of time
series bounded. The histogram has identical bucket boundaries in both
instances, from 0.5 ms to 10 s plus `+Inf`, so bucket counts can be summed
before calculating percentiles. A Summary's client-side quantiles cannot be
combined across instances.

Example PromQL across both instances:

```promql
# RPS by method and route
sum by (method, route) (rate(items_http_requests_total[1m]))

# Error RPS by exact response code
sum by (method, route, status_code) (
  rate(items_http_requests_total{status_code=~"4..|5.."}[1m])
)

# p95 latency in seconds by method and route (replace 0.95 with 0.50 or 0.99)
histogram_quantile(0.95,
  sum by (le, method, route) (
    rate(items_http_request_duration_seconds_bucket[5m])
  )
)
```

Add `pod_id` and/or `datacenter` matchers inside `{...}` to filter an
instance or datacenter. To aggregate selected instances, keep the `sum by`
clauses as shown.

## Remaining student work

The stack is not yet a completed submission. The following parts remain:

- Add `GET /handlers` for runtime handler discovery.
- Design the dashboard generator, including PromQL aggregation, pod and
  datacenter selectors, non-editable dashboard settings, and startup ordering.
- Choose and implement the load tool, including a gradual ramp, both
  application instances, every business route, and at least two error codes.
- Verify that `docker compose up` displays data in Grafana after 2-3 minutes,
  record a one-minute screencast, and open the final PR.
