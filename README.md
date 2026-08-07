# Job Search Manager API

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-D71F00?logo=sqlalchemy&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-4479A1?logo=mysql&logoColor=white)
![Pytest](https://img.shields.io/badge/Pytest-0A9EDC?logo=pytest&logoColor=white)
![Railway](https://img.shields.io/badge/Railway-0B0D0E?logo=railway&logoColor=white)

A production-oriented REST API for managing companies, job applications,
interviews, follow-ups, and job-search priorities.

## Tech Stack

- Python 3.12+
- FastAPI
- Uvicorn
- SQLAlchemy
- MySQL
- PyMySQL
- Pydantic
- Pytest
- HTTPX
- Swagger/OpenAPI
- Railway

## Current Status

### Day 1 foundation:

- FastAPI application initialized
- Environment configuration added
- Health-check endpoint added
- Swagger/OpenAPI documentation enabled
- Virtual environment and dependencies configured

### Day 2 Company Management

- MySQL database connected
- Dedicated application database user configured
- SQLAlchemy engine and session management added
- Company ORM model implemented
- Company request and response schemas implemented
- Company service layer implemented
- Company router implemented
- Full Company CRUD endpoints implemented
- Pydantic request validation added
- 404 and 422 error handling verified
- End-to-end CRUD testing completed with MySQL persistence

## Current Endpoints

### Health

| Method | Endpoint  | Description               |
| ------ | --------- | ------------------------- |
| GET    | `/health` | Verify the API is running |

### Companies

| Method | Endpoint                  | Description                |
| ------ | ------------------------- | -------------------------- |
| POST   | `/companies`              | Create a new company       |
| GET    | `/companies`              | Retrieve all companies     |
| GET    | `/companies/{company_id}` | Retrieve a company by ID   |
| PUT    | `/companies/{company_id}` | Update an existing company |
| DELETE | `/companies/{company_id}` | Delete a company           |

## Requirements

- Python 3.12+
- MySQL 9.x LTS

## Local Development

Create and activate a virtual environment:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Run the API:

```bash
uvicorn app.main:app --reload
```

Swagger UI:

```
http://127.0.0.1:8000/docs
```

## Roadmap

- Day 1 — Project setup
- Day 2 — Company Management API
- Day 3 — Job Applications
- Day 4 — Interviews
- Day 5 — Search, filtering, and pagination
- Day 6 — Validation and exception handling
- Day 7 — Automated testing
- Day 8 — Authentication
- Day 9 — Deployment
- Day 10 — Documentation and polish
