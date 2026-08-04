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

- Python
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

Day 1 foundation:

- FastAPI application initialized
- Environment configuration added
- Health-check endpoint added
- Swagger/OpenAPI documentation enabled
- Virtual environment and dependencies configured

## Local Development

Create and activate a virtual environment:

```bash
python3 -m venv .venv
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
