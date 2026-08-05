# Generic Data Ingestion Service

A modular FastAPI service that ingests data from **arbitrary public APIs** and stores the responses in a SQLite database — without being tailored to any specific API.

The service accepts one or more URLs, fetches responses concurrently, persists payloads in a database-agnostic JSON form, and returns a per-URL success/failure report. It is designed to remain generic: no API-specific parsers, schemas, or adapters are required.

---

## Features

- Accept one or more API URLs in a single request
- Fetch data concurrently with HTTPX (timeouts + light retries)
- Persist responses as JSON in SQLite via SQLAlchemy
- Per-URL success/failure reporting (partial job success supported)
- Structured logging and consistent error handling
- Docker / docker-compose support
- Interactive OpenAPI docs at `/docs`

---



## Architecture

```text
app/
├── api/routes/       # HTTP endpoints (health, ingest, records, jobs)
├── core/             # Config & logging
├── db/               # SQLAlchemy models & session
├── schemas/          # Pydantic request/response models
├── services/         # ApiFetcher + IngestionService
└── main.py           # FastAPI application entrypoint
```

**Flow:** `POST /api/v1/ingest` → validate URLs → fetch concurrently → store payloads → return job summary with per-URL results.

Storage is intentionally generic: each successful fetch becomes an `ingested_records` row with `source_url`, HTTP metadata, and a JSON `payload`. No API-specific parsers or schemas.

---



## Project Structure

```text
generic-data-ingestion-service/
│
├── app/
│   ├── api/
│   │   └── routes/
│   ├── core/
│   ├── db/
│   ├── schemas/
│   ├── services/
│   ├── __init__.py
│   └── main.py
│
├── data/
│   └── ingestion.db
│
├── tests/
│
├── docs/
│   └── screenshots/
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── README.md
├── .env.example
└── .gitignore
```

This modular structure separates API routes, business logic, database access, configuration, schemas, and testing, making the project easier to maintain, extend, and deploy.

---



## Design Decisions

The architecture prioritizes generality, clarity, and assignment-scale practicality over premature optimization.


| Decision                       | Rationale                                                                                                                                                           |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **API-agnostic architecture**  | The service never binds to a vendor-specific schema. Any public HTTP endpoint that returns JSON or text can be ingested without code changes.                       |
| **Generic JSON storage**       | Responses are stored as serialized JSON text. This avoids inventing per-API tables and keeps the persistence layer extensible.                                      |
| **Separation of concerns**     | Routes, schemas, services, and database models are isolated. Fetching (`ApiFetcher`) is separate from orchestration and persistence (`IngestionService`).           |
| **Async HTTP fetching**        | HTTPX async clients fetch multiple URLs concurrently, reducing wall-clock time for multi-URL jobs.                                                                  |
| **Job tracking**               | Each ingest request creates an `ingestion_jobs` row so operators can audit outcomes (`completed`, `partial`, or `failed`).                                          |
| **Independent URL processing** | One URL failing does not abort the job. Each URL is reported independently, enabling partial success.                                                               |
| **SQLite for simplicity**      | SQLite provides zero-ops local persistence suitable for demos, local development, and assignment evaluation — with a clear path to swap engines via `DATABASE_URL`. |


---



## Trade-offs

These choices keep the project focused and easy to run, at the cost of some production-grade capabilities:


| Trade-off                               | Why it was accepted                                                                                                                                  |
| --------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| **SQLite instead of PostgreSQL**        | Faster setup, no external DB process, and enough durability for assignment-scale workloads. Not ideal for high concurrency or multi-instance writes. |
| **No authentication**                   | Scope stays on generic ingestion. Protecting private APIs and securing the service itself are left as future work.                                   |
| **No background workers**               | Ingestion runs in-request with async I/O. Simpler to reason about and demo; long-running or high-volume jobs would benefit from a queue later.       |
| **Payloads stored directly in SQLite**  | Easy to query and inspect. Large blobs would eventually push toward object storage (e.g. S3).                                                        |
| **Simple retry mechanism**              | Light retries on timeouts and 5xx responses. Full circuit breakers and backoff policies were deferred.                                               |
| **Optimized for assignment simplicity** | The stack favors clarity, Docker one-command startup, and readable modular code over enterprise deployment concerns.                                 |


---



## Assumptions

The current design assumes:

- Target sources are **public APIs** reachable over HTTP(S)
- The runtime environment has **internet connectivity**
- Responses are primarily **JSON or plain text**
- Source APIs do **not require authentication** (API keys, OAuth, etc.)
- **SQLite** is sufficient for assignment-scale workloads and local demos
- Callers provide valid absolute URLs in the ingest request body

---



## Tech Stack


| Component   | Choice       |
| ----------- | ------------ |
| API         | FastAPI      |
| HTTP client | HTTPX        |
| ORM         | SQLAlchemy 2 |
| Database    | SQLite       |
| Runtime     | Uvicorn      |
| Packaging   | Docker       |
| Tests       | pytest       |


---



## Quick Start (local)



### Prerequisites

- Python 3.11+
- pip



### Setup

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env   # Windows
# cp .env.example .env   # macOS / Linux
```



### Run

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open:

- API docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health: [http://localhost:8000/health](http://localhost:8000/health)

---



## Quick Start (Docker)

### Run with Docker

If the hosted Render deployment is unavailable or sleeping due to the free tier, the project can be executed locally using Docker.

```bash
docker compose up --build
```

Service listens on [http://localhost:8000](http://localhost:8000). SQLite data is persisted in the `ingestion-data` volume.

### Docker Verification

This project was successfully verified using Docker.

Verification steps:

Built using:

```bash
docker compose up --build
```

- FastAPI service started successfully.
- Swagger documentation was accessible at: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health endpoint responded successfully.
- Data ingestion APIs functioned correctly inside the Docker container.
- SQLite persistence worked correctly through the mounted Docker volume.

This confirms that the application can be run either locally using Python or through Docker with identical functionality.

---

## Live Demo

The application is deployed on Render and can be accessed using the links below.

### API Base URL

[https://generic-data-ingestion-service-9e83.onrender.com](https://generic-data-ingestion-service-9e83.onrender.com)

### Interactive Swagger UI

[https://generic-data-ingestion-service-9e83.onrender.com/docs](https://generic-data-ingestion-service-9e83.onrender.com/docs)

### Health Check

[https://generic-data-ingestion-service-9e83.onrender.com/health](https://generic-data-ingestion-service-9e83.onrender.com/health)

### OpenAPI Specification

[https://generic-data-ingestion-service-9e83.onrender.com/openapi.json](https://generic-data-ingestion-service-9e83.onrender.com/openapi.json)

---

## Live Demo Note

The application is deployed on **Render's Free Tier**.

If the service has been idle for some time, the first request may take approximately **30–60 seconds** while the Render instance wakes up.

Once active, all subsequent requests respond normally.

For reviewers who prefer to run the project locally or if the hosted service is temporarily unavailable, Docker support is included and the project can be started with a single command.

---

## API Overview



### Ingest one or more URLs

```http
POST /api/v1/ingest
Content-Type: application/json

{
  "urls": [
    "https://jsonplaceholder.typicode.com/posts/1",
    "https://jsonplaceholder.typicode.com/users"
  ]
}
```

Example response:

```json
{
  "job_id": 1,
  "status": "completed",
  "success_count": 2,
  "failure_count": 0,
  "results": [
    {
      "url": "https://jsonplaceholder.typicode.com/posts/1",
      "success": true,
      "status_code": 200,
      "record_id": 1,
      "record_count": 1,
      "error": null
    }
  ]
}
```

Job `status` values:


| Status      | Meaning                          |
| ----------- | -------------------------------- |
| `completed` | All URLs succeeded               |
| `partial`   | Some URLs succeeded, some failed |
| `failed`    | All URLs failed                  |




### Other endpoints


| Method | Path                   | Description         |
| ------ | ---------------------- | ------------------- |
| GET    | `/health`              | Liveness check      |
| GET    | `/api/v1/records`      | List stored records |
| GET    | `/api/v1/records/{id}` | Get one record      |
| GET    | `/api/v1/jobs`         | List ingestion jobs |
| GET    | `/api/v1/jobs/{id}`    | Get one job         |


---



## Configuration

Environment variables (see `.env.example`):


| Variable               | Default                         | Description            |
| ---------------------- | ------------------------------- | ---------------------- |
| `DATABASE_URL`         | `sqlite:///./data/ingestion.db` | SQLAlchemy DB URL      |
| `LOG_LEVEL`            | `INFO`                          | Logging level          |
| `HTTP_TIMEOUT_SECONDS` | `30`                            | Per-request timeout    |
| `HTTP_MAX_RETRIES`     | `2`                             | Retries on timeout/5xx |
| `DEBUG`                | `false`                         | SQLAlchemy echo SQL    |


---



## Error Handling

- Invalid request bodies → FastAPI / Pydantic `422`
- Missing records/jobs → `404`
- Network / HTTP failures for a URL → recorded in that URL's result; other URLs continue
- Unexpected server errors → `500` with a generic JSON body (details logged)

---



## Testing

Unit tests are written with **pytest** and cover payload serialization helpers, record counting, and request schema validation.

Run the suite from the project root:

```bash
python -m pytest
```

**Result:** ✔ **5 tests passing**

---



## Public APIs Tested

The service has been exercised against multiple **unrelated** public APIs to confirm it is not coupled to any single provider:


| API                                                      | Example use                                  |
| -------------------------------------------------------- | -------------------------------------------- |
| [JSONPlaceholder](https://jsonplaceholder.typicode.com/) | Posts, users, and nested resources           |
| [DummyJSON](https://dummyjson.com/)                      | Products and other sample JSON payloads      |
| [GitHub REST API](https://docs.github.com/en/rest)       | Public endpoints such as Zen / user metadata |
| [RandomUser API](https://randomuser.me/)                 | Random profile JSON responses                |


Successful ingestion across these sources demonstrates that the pipeline is **completely generic**: the same endpoint and storage model work without API-specific adapters.

---



## Screenshots

The following screenshots demonstrate the application's functionality. All images are located under `docs/screenshots/`.

---



### 1. Swagger UI

Swagger UI

Interactive OpenAPI documentation automatically generated by FastAPI, showing all available endpoints and allowing API testing directly from the browser.

---



### 2. Successful Ingestion

Successful Ingestion

Example of a successful ingestion job where all requested public APIs were fetched, persisted, and returned with a `completed` status.

---



### 3. Partial Ingestion

Partial Ingestion

Example of a partial ingestion where one API succeeded while another failed. The service continued processing remaining URLs and reported individual results without terminating the entire job.

---



### 4. Stored Records

Stored Records

Stored API responses retrieved through the `GET /api/v1/records` endpoint, demonstrating successful persistence of payloads in SQLite.

---



### 5. Jobs History

Jobs History

History of ingestion jobs retrieved through the `GET /api/v1/jobs` endpoint, including completed and partial executions with success and failure statistics.

---



## Project Milestones Covered

1. Planning & requirements
2. Modular architecture
3. Project setup (venv-friendly, deps, config)
4. Core ingestion (HTTPX fetcher)
5. Database persistence (SQLAlchemy + SQLite)
6. Enhancements (concurrent fetch, retries, job tracking)
7. Docker & deployment
8. Documentation (this README + OpenAPI)

---



## Future Improvements

Existing roadmap items:

- Authentication / API keys for protected sources
- Smarter pagination handling across APIs
- Optional AWS S3 payload offload
- Background task queue (e.g. Celery / RQ / ARQ)
- Stronger retry / circuit-breaker policies
- Metrics and monitoring (Prometheus, OpenTelemetry)

Expanded production roadmap:

- **PostgreSQL** (or other server databases) for multi-writer / production durability
- **Redis** caching for repeated source fetches
- **Authentication** for both the service API and upstream sources
- **Background workers** for long-running or high-volume ingestion
- **Kafka** (or similar) for event-driven ingestion pipelines
- **S3 storage** for large payload offload
- **Prometheus** metrics export
- **OpenTelemetry** distributed tracing
- **Kubernetes** deployment manifests and horizontal scaling

---



## AI Usage

**Cursor AI** and **ChatGPT** were used as development assistants during this project. AI support covered:

- Architecture brainstorming and modular layout options
- Documentation drafting and README structure
- Boilerplate generation (project scaffolding, config patterns)
- Debugging assistance during local verification

Every AI-generated suggestion was **reviewed and validated** before inclusion. Application behavior was confirmed through local runs, Swagger UI testing, and pytest.

**Notable issue caught during review:** An early AI-generated request example contained a trailing comma inside the JSON request body, producing a FastAPI `422` validation error. The issue was identified through Swagger testing and corrected manually.

---



## License

MIT