# Job Search Manager API

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-D71F00?logo=sqlalchemy&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-4479A1?logo=mysql&logoColor=white)
![Pytest](https://img.shields.io/badge/Pytest-0A9EDC?logo=pytest&logoColor=white)
![Railway](https://img.shields.io/badge/Railway-0B0D0E?logo=railway&logoColor=white)

A REST API built with **FastAPI**, **SQLAlchemy**, and **MySQL** for managing a job search. Each user registers, logs in with a JWT, and tracks their own companies, job applications, and interviews; one user's records are never visible to another.

The project follows a layered architecture with separate routers, services, models, and schemas. Schema changes are managed with Alembic migrations, every pull request runs the test suite against MySQL in CI, and the API is deployed to Railway.

---

## Live Demo

| Resource        | URL                                                             |
| --------------- | --------------------------------------------------------------- |
| Production API  | https://job-search-manager-api-production.up.railway.app        |
| Swagger UI      | https://job-search-manager-api-production.up.railway.app/docs   |
| Health Endpoint | https://job-search-manager-api-production.up.railway.app/health |

The live demo runs the latest release from the `main` branch. Work merged into `develop` appears there after the next release.

---

## Key Features

### Company Management

- Create, update, retrieve, and delete companies
- Store company website, industry, location, and notes
- Paginated list ordered by name, then ID
- A company that still has job applications can't be deleted (`409 Conflict`); delete or move its applications first
- Company names don't have to be unique

### Job Application Management

- Track job applications
- Associate applications with companies
- Store salary ranges, work arrangement, application status, and notes
- Prevent tracking the same posting twice: a job URL is unique per user, and different users can track the same posting
- Deleting an application also deletes its interviews

### Interview Management

- Schedule interviews
- Track interview type, status, and outcome
- Prevent scheduling the same application twice at the same moment
- Associate interviews with job applications
- Times are sent with a UTC offset and returned in UTC

### Authentication

- User registration
- Secure password hashing with Argon2
- JWT access tokens
- Every company, application, and interview endpoint requires a bearer token
- Each user only sees and changes their own records; another user's record returns `404 Not Found`, the same as a missing one
- Applications can only be filed under the user's own companies, and interviews under the user's own applications

### Search & Filtering

Job Applications

- Status
- Company
- Location
- Work Arrangement
- Date Applied
- Full-text search
- Sorting
- Pagination

Interviews

- Application
- Interview Type
- Status
- Outcome
- Scheduled Date
- Sorting
- Pagination

Companies

- Pagination

### Validation & Error Handling

- Global exception handlers with consistent error responses
- Request validation with Pydantic
- Required text is trimmed, and blank values are rejected
- Notes are limited to 65,535 bytes (MySQL `TEXT`)
- Datetimes must include a UTC offset (`2026-11-02T15:00:00Z`); values without one are rejected
- Duplicate detection, plus a generic `409 Conflict` for database constraint conflicts (details are logged, never returned)
- Date-range validation

### Automated Testing

- 213 automated tests, 99% code coverage
- Dedicated MySQL test database, with a guard that refuses to reset any database whose name lacks `test` or matches `DB_NAME`
- CRUD, validation, and end-to-end workflow tests
- Authentication and cross-user isolation tests
- Migration tests run against MySQL

---

## Tech Stack

### Backend

- Python 3.12+
- FastAPI
- SQLAlchemy
- MySQL
- PyMySQL

### Authentication

- PyJWT
- pwdlib (Argon2)
- HTTP Bearer Authentication

### Validation

- Pydantic
- pydantic-settings

### Database Migrations

- Alembic

### Testing

- Pytest
- pytest-cov
- HTTPX

### Documentation

- Swagger / OpenAPI

### CI and Security Scanning

- GitHub Actions (tests, Ruff, migration checks)
- CodeQL, Bandit, Dependency Review, Dependabot

### Deployment

- Railway

---

## Architecture

```
Client
      │
      ▼
FastAPI Routers
      │
      ▼
Service Layer
      │
      ▼
SQLAlchemy ORM
      │
      ▼
MySQL Database
```

The application follows a layered architecture that separates routing, business logic, validation, and database access to improve maintainability and testability.

---

## Project Structure

```text
app/
├── enums/            # Status, type, and outcome enums
├── exceptions/       # Application exceptions (not found, conflict, validation)
├── handlers/         # Global exception handlers
├── models/           # SQLAlchemy models
├── routers/          # FastAPI routes
├── schemas/          # Pydantic request/response models and shared field types
├── services/         # Business logic and owner-scoped queries
├── config.py         # Settings from environment variables
├── database.py       # Engine, sessions, commit/rollback helper
├── db_types.py       # UTC datetime column type
├── security.py       # Password hashing and JWTs
└── main.py           # FastAPI app

alembic/              # Migration environment and versions/
alembic.ini
docs/
├── database-migrations.md
└── design-decisions.md
scripts/
└── compare_schema.py # Read-only schema check before adopting migrations

tests/
├── conftest.py       # Fixtures, test database guard
├── db_safety.py      # Guards for destructive test setup
├── migration_utils.py
└── test_*.py         # API, isolation, validation, and migration tests
```

---

## Screenshots

### Swagger UI

<img src="assets/swagger-ui.png" alt="Swagger UI" width="1000">

### Test Coverage Report

Screenshot from v0.1.0 (70 tests). The current figures are under [Testing](#testing).

<img src="assets/coverage-report.png" alt="Test Coverage Report" width="1000">

### Railway Deployment

<img src="assets/railway-dashboard.png" alt="Railway Deployment" width="1000">

## API Endpoints

### Health

| Method | Endpoint  |
| ------ | --------- |
| GET    | `/health` |

### Authentication

| Method | Endpoint         |
| ------ | ---------------- |
| POST   | `/auth/register` |
| POST   | `/auth/login`    |
| GET    | `/auth/me`       |

### Companies

| Method | Endpoint          |
| ------ | ----------------- |
| POST   | `/companies`      |
| GET    | `/companies`      |
| GET    | `/companies/{id}` |
| PUT    | `/companies/{id}` |
| DELETE | `/companies/{id}` |

### Job Applications

| Method | Endpoint             |
| ------ | -------------------- |
| POST   | `/applications`      |
| GET    | `/applications`      |
| GET    | `/applications/{id}` |
| PUT    | `/applications/{id}` |
| DELETE | `/applications/{id}` |

### Interviews

| Method | Endpoint           |
| ------ | ------------------ |
| POST   | `/interviews`      |
| GET    | `/interviews`      |
| GET    | `/interviews/{id}` |
| PUT    | `/interviews/{id}` |
| DELETE | `/interviews/{id}` |

All company, application, and interview endpoints require `Authorization: Bearer <JWT>` and only work with the logged-in user's records.

---

## Example Requests

### Register

```http
POST /auth/register
```

```json
{
  "email": "user@example.com",
  "password": "TestPassword123!"
}
```

### Login

```http
POST /auth/login
```

```json
{
  "email": "user@example.com",
  "password": "TestPassword123!"
}
```

### Authenticated Request

```http
GET /auth/me
Authorization: Bearer <JWT>
```

### Schedule an Interview

```http
POST /interviews
Authorization: Bearer <JWT>
```

```json
{
  "application_id": 1,
  "interview_type": "technical",
  "scheduled_at": "2026-11-02T10:00:00-05:00"
}
```

The response returns the time in UTC: `"scheduled_at": "2026-11-02T15:00:00Z"`.

---

## Local Development

### Clone

```bash
git clone <repository-url>
```

### Create a virtual environment

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

### Install dependencies

```bash
pip install -r requirements.txt
```

### Create the database schema

The app does not create tables on startup. Apply the migrations to the database configured in `.env`:

```bash
alembic upgrade head
```

If your database was created by an older version of this project, adopt it instead of upgrading; see [docs/database-migrations.md](docs/database-migrations.md).

### Run the application

```bash
uvicorn app.main:app --reload
```

Swagger:

```
http://127.0.0.1:8000/docs
```

---

## Testing

The project includes automated tests covering:

- Authentication
- Companies
- Job Applications
- Interviews
- Cross-user isolation
- Validation, timezones, and exception handling
- Database migrations
- End-to-end API workflows

Tests need a disposable MySQL database set in `TEST_DATABASE_URL`. The suite drops and recreates its tables, and refuses to run unless the database name contains `test` and differs from `DB_NAME`.

Run all tests:

```bash
python -m pytest
```

Generate a coverage report:

```bash
python -m pytest --cov=app --cov-report=term-missing --cov-report=html
```

Current test suite:

- **213 automated tests**
- **99% code coverage**

---

## Future Enhancements

- Refresh tokens
- Role-based authorization
- Docker support
- Email notifications
- Saved searches
- Application reminders

---

## License

MIT
