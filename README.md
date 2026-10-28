# DDIA HW 1: Items monitoring

This repository contains an in-memory FastAPI CRUD service, two instrumented
container instances, Prometheus, a generated Grafana dashboard, and a
continuous load generator.

## Run locally

Docker Engine and Docker Compose are required.

```sh
cp .env.example .env
docker compose up
```

Local endpoints:

| Service | URL |
| --- | --- |
| Grafana | http://localhost:13030 |
| Generated dashboard | http://localhost:13030/d/ddia-hw1-items/ddia-hw1-c2b7-http-handlers |
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

The business API has exactly three routes. Service endpoints are `GET /health`,
`GET /metrics`, and `GET /handlers`.

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
observes requests to the business routes and `GET /handlers`. `GET /health` and
`GET /metrics` are excluded, so health checks and Prometheus scrapes do not
affect traffic measurements. Unmatched URLs are also excluded because they
have no route template.

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

## Generated dashboard (part 2)

`GET /handlers` lists the registered method and path template of every
instrumented route. The generator reads this endpoint from **both** app
instances at startup and checks that they agree. It does not keep a route list
in its own code. At present this yields four handlers: the three CRUD routes
and `GET /handlers` itself.

The `dashboard_generator` Compose service starts only after both apps and
Grafana pass their health checks. It uses the administrator credentials from
`.env` to call Grafana's HTTP API. The Prometheus datasource is provisioned
with UID `prometheus`; the dashboard uses a stable UID and is replaced on each
generator run. The generator is a one-shot CLI process that should exit with
code 0. Its output contains the number of generated panels and the dashboard
path, but no credentials.

Each discovered handler gets three panels: p50/p95/p99 latency, total RPS,
and error RPS grouped by exact 4xx/5xx status code. The PromQL selectors use
the **Datacenter** and **Pod** variables. Both support multiple selections
and **All**. Rate queries sum the selected instances; latency queries first
sum histogram buckets by `le`, then call `histogram_quantile`. The dashboard
has `editable: false` and refreshes every five seconds.

To add a route, register it in the FastAPI app and restart the stack with
`docker compose down` followed by `docker compose up --build`. The next
generator run discovers the new route and adds its three panels. Grafana data
is stored in a named volume, while the generator overwrites only the
dashboard with its own UID.

## Background load (part 3)

The `load_generator` service starts after both apps are healthy **and** the
dashboard generator has exited successfully. It creates one anchor item in
each app instance, then sends requests to both instances continuously. The
default target is **30 RPS total**: it ramps linearly from 2 RPS over 150
seconds (2.5 minutes) and then stays at 30 RPS until the stack is stopped.
Eight workers keep the request schedule moving if an individual request is
slow.

The deterministic 50-request cycle exercises POST, GET, PUT, and
`GET /handlers` on both pods. Two requests per cycle intentionally fail:
`GET /items/2147483647` returns 404 and an invalid `POST /items` returns 422.
The expected error share is therefore **4%**, with two separate status codes
visible on the dashboard. Successful POSTs happen once per cycle, limiting
growth of the in-memory store during a long run.

Every 30 seconds, the generator logs its target and observed RPS, completed
request count, status-code counts, and per-pod counts. To inspect it while
the stack runs:

```sh
docker compose logs -f load_generator
```

The defaults are defined in `compose.yaml` as `LOAD_INITIAL_RPS`,
`LOAD_TARGET_RPS`, and `LOAD_RAMP_SECONDS`. To rebuild after code changes,
run `docker compose up --build`. Stop the stack with `docker compose down`.

## Remaining student work

The stack is implemented. The following submission steps remain:

- Record a one-minute screencast with the live dashboard and load.
- Open the final PR with a link to the screencast.
