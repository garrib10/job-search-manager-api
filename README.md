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

### Day 3 Job Application Management

- JobApplication ORM model implemented
- Company ↔ JobApplication relationship established
- ApplicationStatus and WorkArrangement enums added
- Job Application request and response schemas implemented
- Application service layer implemented
- Application router implemented
- Full Job Application CRUD endpoints implemented
- Foreign key validation added
- Duplicate job URL validation added
- End-to-end CRUD testing completed
- MySQL relationship verification completed

### Day 4 Interview Management

- Interview ORM model implemented
- JobApplication ↔ Interview relationship established
- InterviewType, InterviewStatus, and InterviewOutcome enums added
- Interview request and response schemas implemented
- Interview service layer implemented
- Interview router implemented
- Full Interview CRUD endpoints implemented
- Job application relationship validation added
- End-to-end CRUD testing completed
- MySQL relationship verification completed

### Day 5 Search & Filtering

- Added application filtering
- Added interview filtering
- Added company name search
- Added partial text search
- Added application date range filtering
- Added interview scheduled date filtering
- Added sorting
- Added pagination
- Added multi-filter support
- Added validation for invalid filter values
- Verified filters against MySQL

### Day 6 Validation & Error Handling

- Added custom exception classes
- Added global exception handlers
- Moved business validation into the service layer
- Added duplicate interview scheduling validation
- Added application date-range validation
- Added interview date-range validation
- Verified all validation paths
- Completed end-to-end regression testing

### Day 7 Automated Testing & Quality Assurance

- Implemented a dedicated MySQL test database
- Configured Pytest with reusable fixtures
- Added automated CRUD tests for Companies
- Added automated CRUD tests for Job Applications
- Added automated CRUD tests for Interviews
- Created end-to-end workflow tests covering complete job search scenarios
- Tested validation rules, custom exceptions, and business logic
- Verified filtering, searching, sorting, and pagination
- Generated code coverage reports using pytest-cov
- Achieved 55 automated tests with approximately 97% code coverage
- Verified application stability through a full regression test suite

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

### Job Applications

| Method | Endpoint                         | Description                        |
| ------ | -------------------------------- | ---------------------------------- |
| POST   | `/applications`                  | Create a new job application       |
| GET    | `/applications`                  | Retrieve all job applications      |
| GET    | `/applications/{application_id}` | Retrieve a job application by ID   |
| PUT    | `/applications/{application_id}` | Update an existing job application |
| DELETE | `/applications/{application_id}` | Delete a job application           |

#### Query Parameters (GET /applications)

- status_filter
- company_id
- company
- location
- work_arrangement
- search
- date_applied_from
- date_applied_to
- sort_by
- sort_order
- limit
- offset

### Interviews

| Method | Endpoint                     | Description                  |
| ------ | ---------------------------- | ---------------------------- |
| POST   | `/interviews`                | Create a new interview       |
| GET    | `/interviews`                | Retrieve all interviews      |
| GET    | `/interviews/{interview_id}` | Retrieve an interview by ID  |
| PUT    | `/interviews/{interview_id}` | Update an existing interview |
| DELETE | `/interviews/{interview_id}` | Delete an interview          |

#### Query Parameters (GET /interviews)

- application_id
- interview_type
- status_filter
- outcome
- scheduled_from
- scheduled_to
- sort_order
- limit
- offset

### Example Requests

### Applications

```http
GET /applications?status_filter=saved
```

```http
GET /applications?company=Stripe
```

```http
GET /applications?search=Python
```

```http
GET /applications?work_arrangement=hybrid
```

```http
GET /applications?limit=10&offset=0
```

### Interviews

```http
GET /interviews?status_filter=scheduled
```

```http
GET /interviews?application_id=2
```

```http
GET /interviews?interview_type=behavioral
```

```http
GET /interviews?scheduled_from=2026-08-01T00:00:00
```

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
