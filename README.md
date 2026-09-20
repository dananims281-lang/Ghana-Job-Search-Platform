# Job Matching Platform API

FastAPI service backed by PostgreSQL. Currently implements:

- `POST /jobListings` — employer creates a job listing (requires an existing `company_id`)

Tables: `company`, `job_listing` (see `app/models.py`).

## Setup

1. Create a virtual environment and install dependencies:
   ```
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Make sure Postgres is running and the `myapp` database exists:
   ```
   brew services start postgresql@16
   createdb myapp
   ```

3. Copy `.env.example` to `.env` and set your `DATABASE_URL`:
   ```
   cp .env.example .env
   ```
   Edit `.env` — replace `YOUR_MAC_USERNAME` with your actual Mac username (run `whoami` to check).

4. Run the API:
   ```
   uvicorn app.main:app --reload
   ```
   This also creates the `company` and `job_listing` tables on startup if they don't exist yet.

5. Open the interactive docs at http://127.0.0.1:8000/docs

## Testing POST /jobListings

Since `job_listing` requires a `company_id` foreign key, insert a test company first
(via pgAdmin's Query Tool, or `psql myapp`):

```sql
INSERT INTO company (company_id, name, verified_at)
VALUES (gen_random_uuid(), 'Acme Inc', now())
RETURNING company_id;
```

Copy the returned `company_id`, then call the API:

```
curl -X POST http://127.0.0.1:8000/jobListings \
  -H "Content-Type: application/json" \
  -d '{
        "company_id": "PASTE_COMPANY_ID_HERE",
        "jobName": "Backend Engineer",
        "location": "Remote",
        "salary": 120000,
        "description": "Build and maintain our API services."
      }'
```

## Roadmap (not yet implemented)

- `GET /jobListings?category=&location=`
- `POST /accounts` (user + employer signup)
- `POST /oneclickapply/{jobId}`
- `GET /userapply?jobId={jobId}`
