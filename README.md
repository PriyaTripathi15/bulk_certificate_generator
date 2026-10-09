# Bulk Certificate Generator

A small FastAPI backend that accepts one bulk request, validates recipients, creates PDF certificates from one fixed template, tracks job progress in SQLite, and provides certificate downloads.

## Requirements
- Python 3.10+
- pip

## Setup

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

## Run the API

```bash
uvicorn app.main:app --reload
```

Open interactive API docs at `http://127.0.0.1:8000/docs`. The default database is `certificates.db`; generated PDFs are stored in `generated_certificates/`.

## Submit one bulk job

```bash
curl -X POST http://127.0.0.1:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "recipients": [
      {"name": "Asha Sharma", "email": "asha@example.com", "course": "Python Basics"},
      {"name": "Rahul Verma", "email": "rahul@example.com", "course": "Web Development"}
    ]
  }'
```

The endpoint returns HTTP `202 Accepted` with a job ID, current status, counts, and recipient records. Each recipient gets a unique certificate ID.

## Check progress and results

```bash
curl http://127.0.0.1:8000/jobs/1
```

Statuses:
- Job: `queued`, `processing`, `completed`, `completed_with_errors`, or `failed`
- Recipient: `pending`, `processing`, `succeeded`, or `failed`

`progress_percent` is calculated as `(succeeded + failed) / total * 100`. A recipient's `download_url` is populated only after successful generation.

## Retrieve a PDF

Use the URL returned for a successful recipient:

```bash
curl -L http://127.0.0.1:8000/certificates/CERT-ABC123DEF456 --output certificate.pdf
```

Use the actual certificate ID from the API response. A not-yet-generated certificate returns HTTP `409`; an unknown ID returns `404`.

## Tests

```bash
pytest -q
```

## Design decisions

1. **Bulk API:** One `POST /jobs` request accepts 1–1,000 recipients, rather than one request per certificate.
2. **Validation:** Pydantic validates required fields, string lengths, and email format before a job is created. Invalid request data receives `422`.
3. **Relational storage:** SQLAlchemy models persist job and per-recipient statuses in SQLite. `DATABASE_URL` can point to another SQLAlchemy-supported relational database.
4. **Failure isolation:** Each PDF is generated inside its own `try/except`. A single recipient failure is recorded without stopping other recipients.
5. **Background processing:** FastAPI `BackgroundTasks` runs the generation after the initial response, so the client can poll the job. This is suitable for a small assignment/demo. For large production workloads, replace it with a durable worker queue such as Celery or RQ; in-process tasks may be lost if the server stops.
6. **Certificate output:** ReportLab generates PDFs using one fixed template. The certificate ID is stored in the database and used for retrieval.
7. **Security/production notes:** Add authentication/authorization, rate limits, retention cleanup, and a persistent shared file store before exposing this API publicly. The demo does not send certificates by email.

## API summary

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/jobs` | Create a bulk generation job |
| `GET` | `/jobs/{job_id}` | Read job progress and per-recipient results |
| `GET` | `/certificates/{certificate_id}` | Download a generated PDF |
