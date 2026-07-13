# Sanaie Platform — Home & Professional Services Marketplace

A local-first FastAPI marketplace connecting clients with verified technicians through competitive bidding.

## Tech Stack

| Layer | Technology |
|---|---|
| Runtime | Python 3.11+ |
| Framework | FastAPI + Uvicorn |
| ORM | SQLAlchemy 2.0 |
| Validation | Pydantic v2 |
| Database | MySQL 8.0 (via pymysql) |
| Auth | JWT (python-jose) + Bcrypt (passlib) |
| Tokens | Access + Refresh tokens |
| Geo | Haversine distance with bounding-box pre-filter |
| File Storage | Local filesystem |
| Rate Limiting | slowapi |
| Migrations | Alembic |
| Tests | pytest + httpx |
| Containers | Docker + Docker Compose |

## Quick Start

### Option A: Docker (recommended)
```bash
docker-compose up --build
```
API available at http://localhost:8000/docs

### Option B: Local Development

#### 1. Create the MySQL Database
```sql
CREATE DATABASE sanaie_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```
Or use the full schema: `database/schema.sql`

#### 2. Install Dependencies
```bash
cd Sanaie-Platform
pip install -r requirements.txt
```

#### 3. Configure Environment
```bash
cp .env.example .env
# Edit .env with your MySQL credentials and a random SECRET_KEY
```

#### 4. Run the Server
```bash
uvicorn app.main:app --reload --port 8000
$env:PYTHONPATH = (Get-Location).Path
flet run frontend/main.py --verbose
net start MySQL80
```

#### 5. Open API Docs
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

#### 6. Run Tests
```bash
pytest tests/ -v
```

## Architecture

```
app/
├── api/
│   ├── deps.py          # Shared deps: auth, role guards, exception handlers
│   └── v1/              # Versioned API routes
├── core/
│   ├── config.py        # Pydantic Settings from .env
│   ├── database.py      # SQLAlchemy engine + session
│   ├── exceptions.py    # Domain exceptions (HTTP-agnostic)
│   └── security.py      # JWT + password hashing
├── enums.py             # Single source of truth for all enums
├── models/              # SQLAlchemy ORM models
├── schemas/             # Pydantic request/response schemas
└── services/            # Business logic (HTTP-agnostic)
```

## API Endpoints

### Auth (`/api/v1/auth`)
- `POST /register` — Register client, worker, or admin
- `POST /login` — OAuth2 login → JWT access + refresh tokens
- `POST /refresh` — Exchange refresh token for new access token

### Users (`/api/v1/users`)
- `GET /me` — My profile
- `PUT /me` — Update profile (name, phone, skills, availability)
- `PUT /me/location` — Update geolocation
- `GET /workers/nearby` — Find nearby workers (bounding-box + Haversine)
- `GET /{user_id}` — Public profile

### Jobs (`/api/v1/jobs`)
- `POST /` — Create job with photo + location (client/admin)
- `GET /` — List jobs (filterable by status, category, full-text search)
- `GET /{id}` — Job details
- `PUT /{id}` — Update job (owner, if open)
- `DELETE /{id}` — Delete job
- `PUT /{id}/complete` — Mark completed
- `PUT /{id}/cancel` — Cancel job
- `GET /my/client` — My client jobs
- `GET /my/worker` — My assigned jobs

### Bids (`/api/v1/bids`)
- `POST /` — Submit bid with message (worker only)
- `GET /job/{id}` — Bids for a job
- `PUT /{id}/accept` — Accept bid → assigns worker, rejects others
- `PUT /{id}/reject` — Reject bid
- `PUT /{id}/withdraw` — Withdraw bid
- `GET /my` — My bids

### Reviews (`/api/v1/reviews`)
- `POST /` — Submit review (client/admin, after completion)
- `GET /worker/{id}` — Worker reviews (paginated)
- `GET /worker/{id}/rating` — Worker avg rating
- `GET /job/{id}` — Job review

## Security Features

- **Password Validation**: Requires uppercase, lowercase, digit, and special character
- **JWT Tokens**: Short-lived access tokens + long-lived refresh tokens
- **Role-Based Access**: `require_role()` dependency for endpoint protection
- **CORS**: Configurable origins (no wildcard in production)
- **Rate Limiting**: Configurable per-minute limits via slowapi
