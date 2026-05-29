# Booking Scheduler Backend

FastAPI backend for the booking scheduler spec.

## Local Services

Start PostgreSQL 15 and Redis 7:

```powershell
docker compose up -d postgres redis
```

Use these development values:

```env
DATABASE_URL=postgresql+asyncpg://booking_scheduler:booking_scheduler@localhost:5432/booking_scheduler
REDIS_URL=redis://localhost:6379
```

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

## Migrations

```powershell
$env:PYTHONPATH='backend'
.\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini upgrade head
```

## Run

```powershell
$env:PYTHONPATH='backend'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --app-dir backend
```

## Test

```powershell
$env:PYTHONPATH='backend'
.\.venv\Scripts\python.exe -m pytest backend\tests
```
