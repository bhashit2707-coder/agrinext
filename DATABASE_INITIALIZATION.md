# AgriNext database initialization

AgriNext uses SQLite and creates its schema through `database.init_db()`.

## Fresh local database

From the `backend` directory:

```powershell
python init_database.py
```

This creates the database schema only. It does not seed demo users, sessions, farms or farmer records.

## Database location

By default, the application creates `backend/agrinext.db` when the API imports its router and initializes the schema. To use a different location, set `AGRINEXT_DB_PATH` before starting the backend. Use an absolute path for production persistent storage.

PowerShell example:

```powershell
$env:AGRINEXT_DB_PATH = "C:\AgriNextData\agrinext.db"
python init_database.py
python main.py
```

The parent directory is created automatically. Keep the database outside source-control and release ZIPs. Back it up using an application-consistent procedure before upgrades.

## Environment setup

Copy `.env.example` to `.env`, then enter your own credentials locally. Never share `.env` or include it in a project archive. The release ZIP intentionally excludes `.env` and all database files.


## NASA background jobs

The application automatically creates the `nasa_jobs` table during normal schema initialization. It stores the owner, job type, submitted parameters, lifecycle status, attempt count, timestamps, and result/error. No manual migration is required for an existing SQLite database.

- `POST /api/nasa/jobs/power`, `/smap`, or `/gpm` submits an authenticated job and returns HTTP 202 with a job ID.
- `GET /api/nasa/jobs/{job_id}` returns status and, when complete, the result. Only the owning user can read it.
- `DELETE /api/nasa/jobs/{job_id}` cancels a job only while it remains queued. A running network operation is not forcibly terminated.
- Jobs are processed by a bounded in-process worker pool (`AGRINEXT_NASA_JOB_WORKERS`, default 2, maximum 4). A failed worker attempt is retried once. The queue is capped at 3 active jobs per user and 20 active jobs globally.
- On server restart, unfinished jobs are marked failed with a retry message; completed jobs older than 30 days are cleaned up. Keep the SQLite database on persistent storage.

For multi-instance deployments, this in-process worker pool is not a distributed queue. Use a shared queue/worker system (for example, Redis-backed workers) before scaling the API horizontally.
