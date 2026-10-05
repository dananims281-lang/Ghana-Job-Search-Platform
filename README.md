# Job Matching Platform API

FastAPI service backed by PostgreSQL. Currently implements:

- `POST /companies` — employer registers a company (starts unverified)
- `GET /companies/{company_id}` — public company profile, including `open_jobs_count`
- `POST /jobs` — employer creates a job (requires an existing `company_id`)

Tables: `company`, `jobs` (see `app/models.py`). Schema changes for existing databases live in `migrations/`.

## Setup

1. Create a virtual environment and install dependencies:
   ```
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Make sure Postgres is running and the `ghana_jobs` database exists:
   ```
   brew services start postgresql@16
   createdb ghana_jobs
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
   This also creates the `company` and `jobs` tables on startup if they don't exist yet.

5. Open the interactive docs at http://127.0.0.1:8000/docs

## Upgrading an existing database

If your database already has tables from an earlier version, `create_all` will NOT alter them.
Run the migrations you haven't run yet, in order:

```
psql ghana_jobs -f migrations/001_expand_job_listing.sql   # expands job_listing to the new fields
psql ghana_jobs -f migrations/002_rename_job_listing_to_jobs.sql   # renames job_listing -> jobs
psql ghana_jobs -f migrations/003_expand_company.sql   # adds description, location, created_at to company
```

It backfills old rows with `country = 'GH'`, `salary_currency = 'GHS'`, `category = 'other'`
and `employment_type = 'full_time'`, so review those rows afterwards.
On a fresh database you can skip this; starting the app creates the new tables.

## Testing the company endpoints

Create a company:

```
curl -X POST http://127.0.0.1:8000/companies \
  -H "Content-Type: application/json" \
  -d '{
        "name": "Acme Logistics",
        "website": "https://acmelogistics.com",
        "description": "Freight and logistics across West Africa.",
        "location": { "country": "GH", "region": "Greater Accra", "city": "Accra" }
      }'
```

Only `name` is required. `website` must be a full URL (`https://...`), `location.country` a 2-letter ISO code.
New companies are always unverified; `verified` is not accepted from the client.
To mark one verified while testing: `UPDATE company SET verified_at = now() WHERE company_id = '...';`

Fetch it (copy the `id` from the response above):

```
curl http://127.0.0.1:8000/companies/PASTE_COMPANY_ID_HERE
```

`open_jobs_count` counts that company's jobs with `status = open`. An unknown id returns 404.

## Testing POST /jobs

Since `jobs` requires a `company_id`, create a company first with `POST /companies` (above),
copy its `id`, then call the API:

```
curl -X POST http://127.0.0.1:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{
        "company_id": "PASTE_COMPANY_ID_HERE",
        "title": "Backend Developer",
        "description": "Build and maintain our API services.",
        "category": "technology",
        "employment_type": "full_time",
        "experience_level": "mid",
        "location": {
          "work_mode": "hybrid",
          "country": "GH",
          "region": "Greater Accra",
          "city": "Accra"
        },
        "salary": { "min": 8000, "max": 12000, "currency": "GHS", "period": "monthly" },
        "requirements": ["3+ years Python", "Experience with PostgreSQL"],
        "benefits": ["Health insurance"],
        "expires_at": "2027-01-31T23:59:59Z"
      }'
```

Field rules:

- `employment_type`: `full_time` | `part_time` | `contract` | `internship` | `temporary`
- `experience_level` (optional): `entry` | `mid` | `senior` | `lead`
- `status` (optional, default `open`): `open` | `draft`
- `location.work_mode`: `onsite` | `hybrid` | `remote`. `city` is required unless `remote`.
- `location.country`: 2-letter ISO code (e.g. `GH`). `salary.currency`: 3-letter ISO code (e.g. `GHS`).
- `salary` is optional. If sent, it needs `currency`, `period` (`hourly` | `monthly` | `yearly`) and at least `min` or `max`.

## Roadmap (not yet implemented)

- `GET /jobs?category=&country=&city=`
- `GET /jobs/{job_id}`
- `POST /accounts` (user + employer signup)
- `POST /oneclickapply/{jobId}`
- `GET /userapply?jobId={jobId}`
