# Design Decisions

Each entry records a question about how the project works, the decision made, why, and the trade-off accepted.

## Contents

1. [How is the API verified before code reaches `main`?](#how-is-the-api-verified-before-code-reaches-main)
2. [How are pull requests labeled, and why is `pull_request_target` safe here?](#how-are-pull-requests-labeled-and-why-is-pull_request_target-safe-here)
3. [How does code get from a feature branch to production?](#how-does-code-get-from-a-feature-branch-to-production)
4. [How are dependency vulnerabilities and code scanning alerts handled?](#how-are-dependency-vulnerabilities-and-code-scanning-alerts-handled)
5. [How are the company, application, and interview endpoints protected?](#how-are-the-company-application-and-interview-endpoints-protected)
6. [How should security vulnerabilities be reported?](#how-should-security-vulnerabilities-be-reported)
7. [How is the database schema created and changed?](#how-is-the-database-schema-created-and-changed)
8. [How are records owned, and how do existing records get an owner?](#how-are-records-owned-and-how-do-existing-records-get-an-owner)
9. [How is each user's data kept separate?](#how-is-each-users-data-kept-separate)
10. [What happens on delete, duplicates, and database conflicts?](#what-happens-on-delete-duplicates-and-database-conflicts)
11. [How are dates, times, and text inputs validated?](#how-are-dates-times-and-text-inputs-validated)
12. [How is the README kept accurate?](#how-is-the-readme-kept-accurate)
13. [How is the app deployed and migrated on Railway?](#how-is-the-app-deployed-and-migrated-on-railway)
14. [What stops the app from running with unsafe production settings?](#what-stops-the-app-from-running-with-unsafe-production-settings)

---

## How is the API verified before code reaches `main`?

**Decision**

GitHub Actions runs four workflows on pull requests into `develop` and `main`:

| Workflow | Check name(s) | What it does |
| --- | --- | --- |
| `ci.yml` | `ruff`, `tests` | Lints with Ruff and runs the pytest suite with coverage against a disposable MySQL 8.4 service container |
| `codeql.yml` | `Analyze (python)` | CodeQL static analysis (advanced setup) |
| `dependency-review.yml` | `dependency-review` | Blocks pull requests that add dependencies with known high-severity vulnerabilities |
| `bandit.yml` | `bandit` | Python security linter; reports findings to the Security tab |

Dependabot (`.github/dependabot.yml`) opens weekly grouped update pull requests for `pip` and GitHub Actions against `develop`.

**Why**

- Tests run against real MySQL rather than SQLite so that MySQL-specific behavior (enum columns, foreign keys, `DATETIME` handling) is exercised the same way it is in production.
- `app/main.py` creates tables at import time and `tests/conftest.py` drops tables during teardown. CI points every database setting (`DB_*` and `TEST_DATABASE_URL`) at two throwaway databases inside the service container, so a test run can never reach a real database.
- CodeQL uses advanced setup instead of GitHub's default setup because default setup did not analyze Dependabot pull requests, which left the CodeQL check neutral ("1 configuration not found").
- Check names are short and stable (`ruff`, `tests`, `dependency-review`) so branch rulesets can require them by name.
- Ruff starts with error-level rules only (`E4`, `E7`, `E9`, `F`) to catch real bugs without reformatting the whole codebase in one change.

**Trade-off**

- A MySQL service container adds roughly 30–60 seconds to each run compared with SQLite.
- Error-only Ruff rules leave import ordering and style unenforced until a dedicated cleanup.
- Dependabot security updates always target the default branch (`main`) and ignore `target-branch`; only routine version updates go to `develop`.

---

## How are pull requests labeled, and why is `pull_request_target` safe here?

**Decision**

`.github/workflows/labeler.yml` runs [actions/labeler](https://github.com/actions/labeler) on pull requests into `develop` and `main`. It applies labels such as `ci`, `auth`, `database`, `docs`, `dependencies`, and `tests` based on the paths listed in `.github/labeler.yml`.

**Why**

- Labels make the pull request list easy to scan and connect pull requests to the same labels used on issues.
- Adding labels requires a token with `pull-requests: write`. The `pull_request` event only gets a read-only token for Dependabot pull requests, so the labeler uses `pull_request_target`.
- `pull_request_target` runs with write permissions, which is dangerous if the workflow runs code from the pull request. This workflow has no `run:` steps and no checkout; the labeler only reads the list of changed file paths through the GitHub API, and the workflow and label rules always come from the default branch (`main`), never from the pull request.

**Trade-off**

- Because GitHub reads the workflow and rules from the default branch, the labeler does nothing until it reaches `main`, and changes to `.github/labeler.yml` only take effect after a release. Merging it into `develop` alone is not enough.
- `sync-labels` is left off, so labels are only added, never removed automatically, and labels added by hand are preserved.

---

## How does code get from a feature branch to production?

**Decision**

```
feature/* ──PR──▶ develop ──PR──▶ main ──▶ Railway deploys ──▶ tag vX.Y.Z
```

- `main` is production. Railway deploys it, and releases are tags on `main`, not branches.
- `develop` is the integration branch. All feature work merges there first.
- Two rulesets enforce the flow:

| Rule | `main` | `develop` |
| --- | --- | --- |
| Require a pull request | Yes, 0 approvals | Yes, 0 approvals |
| Required checks | `tests`, `ruff`, `Analyze (python)`, `dependency-review`, `source-branch` | `tests`, `ruff` |
| Branch must be up to date | Yes | Yes |
| Conversations resolved | Yes | No |
| Block force push and deletion | Yes | Yes |
| CodeQL code scanning gate | Yes (high or higher) | No |
| Bypass list | Empty | Empty |

- The `source-branch` check (`.github/workflows/source-branch.yml`) fails any pull request into `main` unless it comes from `develop`, `hotfix/*`, or `dependabot/*` in this repository.

**Why**

- **Zero approvals:** this is a solo-maintained repository and GitHub does not let an author approve their own pull request. Requiring one approval would block every merge unless the bypass list were used, which would defeat the rules. Required checks provide the gate instead of reviews.
- **Required checks:** a pull request cannot merge unless linting, the MySQL-backed test suite, CodeQL, and the dependency review pass. `develop` requires only tests and Ruff so feature work stays fast; the full set applies on the way to production.
- **Source-branch check:** rulesets can restrict who pushes and what checks must pass, but not which branch a pull request comes from. A small workflow check fills that gap. `hotfix/*` allows urgent production fixes, and `dependabot/*` is allowed because Dependabot security updates always target the default branch. Pull requests from forks are rejected even if the fork's branch is named `develop`.
- **Empty bypass list:** the rules apply to the repository owner too, so nothing reaches production without passing checks.

**Trade-off**

- Every change needs two pull requests to reach production, which is slower than pushing to `main`.
- After a `hotfix/*` or Dependabot merge into `main`, `main` must be merged back into `develop` to keep the branches in sync.
- Pull requests from `develop` into `main` should use a merge commit, not squash. Squashing rewrites `develop`'s commits on `main`, so the two branches would diverge and every later release pull request would show old changes again.
- With no bypass, a broken required check blocks all merges until the workflow is fixed through a pull request.

---

## How are dependency vulnerabilities and code scanning alerts handled?

**Decision**

- Dependencies were upgraded in one pull request into `develop`: FastAPI 0.128.8 → 0.143.3 and Starlette 0.49.3 → 1.8.0 together (FastAPI 0.128.x requires `starlette<1.0.0`), PyJWT 2.13.0 → 2.15.1, plus FastAPI's new dependency `opentelemetry-api`. After the upgrade, an OSV check of every pinned package reports no known advisories.
- Dependabot pull requests #7 (PyJWT) and #8 (Starlette alone) were closed as superseded instead of merged.
- Bandit excludes `tests/`. The one remaining Bandit finding in `app/` (B106 on `token_type="bearer"`) is suppressed in code with `# nosec B106` and a comment explaining why.

**Why**

- **Upgrade together:** bumping Starlette to 1.x on its own breaks installation against FastAPI 0.128.x. This already happened once and was rolled back with a pin, so the two must move as a pair.
- **Supersede the Dependabot PRs:** both were opened against the old `main`, which has none of the required CI workflows, so they could never satisfy the `main` ruleset. Merging them straight into `main` would also have put `main` ahead of `develop`.
- **Exclude tests from Bandit:** all 252 open code scanning alerts were Bandit findings. 243 were B101 (`assert` used), which is how pytest works, and 8 were B105 (fake passwords in test fixtures). Neither is a risk in test code. CodeQL still analyzes the whole repository.
- **Suppress in code, not only in the UI:** a `# nosec` comment keeps the reason next to the code and survives re-scans; a dismissal in the Security tab is invisible to anyone reading the source.

**Trade-off**

- Excluding `tests/` means Bandit would not catch a genuinely unsafe pattern added to test code.
- The exclusion must be written `./tests`: Bandit matches exclusions against paths like `./tests/test_auth.py`, so a bare `tests` silently excludes nothing.
- Starlette 1.8 deprecates using `httpx` with its test client in favor of `httpx2`. Tests still pass with a deprecation warning; switching is a separate follow-up.
- Dependabot and code scanning alerts are evaluated on the default branch, so they only close after this change reaches `main`.

---

## How are the company, application, and interview endpoints protected?

**Decision**

The companies, applications, and interviews routers each declare the existing authentication dependency once, at router level:

```python
router = APIRouter(
    prefix="/companies",
    tags=["Companies"],
    dependencies=[Depends(get_current_user)],
)
```

Every endpoint on those routers now requires a valid bearer token. Requests with no token, an invalid token, or an expired token get `401`. Registration, login, `/health`, and the API docs stay public.

**Why**

- **One declaration per router:** adding the dependency to each endpoint individually would make it easy for a future endpoint to be added without protection. At router level, new endpoints are protected by default.
- **Reuse the existing dependency:** `get_current_user` (the dependency behind `CurrentUser`) already validates the token and checks the user exists and is active. No second implementation was added.
- **Regression tests guard it:** `tests/test_resource_auth.py` checks every resource endpoint without a token, with an invalid token, and with an expired token; confirms rejected writes don't change data; and fails if a resource endpoint exists that the tests don't list.
- **Swagger shows it:** FastAPI marks each protected operation with the `HTTPBearer` security scheme, so Swagger shows a lock icon and sends the token entered in **Authorize**.

**Trade-off**

- **Data is still shared.** This change only requires a logged-in user. Records have no owner yet, so every authenticated user can read and change every record. Ownership and per-user isolation are planned for v0.2.0.
- Router-level dependencies return no value to the endpoint. When endpoints need the current user (for ownership in v0.2.0), they will take `CurrentUser` as a parameter as well.

---

## How should security vulnerabilities be reported?

**Decision**

`SECURITY.md` at the repository root sends reporters to GitHub's private vulnerability reporting, which is enabled on the repository. It defines the supported version (the latest release on `main`), best-effort response times (acknowledgement within 7 days, assessment within 14), what is in and out of scope, and testing guidelines.

**Why**

- **Private by default:** a public issue would disclose a vulnerability before it can be fixed. GitHub's private reporting creates a draft security advisory that only the maintainer and the reporter can see, and it can be published with credit once a fix is released.
- **GitHub links to it:** a root-level `SECURITY.md` appears in the repository's **Security** tab as the security policy and is shown to anyone opening a new issue.
- **Honest response times:** this is a solo-maintained project, so the policy promises what one person can deliver rather than an enterprise SLA.
- **Known limitations listed up front:** the shared-data limitation (no per-user ownership until v0.2.0) is documented so it isn't reported repeatedly as a new finding.
- **Testing guidelines protect the live demo:** the deployed API is public, so the policy asks testers to use only their own accounts and not to run scanners or load tests against it.

**Trade-off**

- Only the latest release is supported; anyone running an older version must upgrade to get fixes.
- Response times are best effort, not guaranteed.
- The known-limitation section must be updated when v0.2.0 adds ownership, or it will become inaccurate.

---

## How is the database schema created and changed?

**Decision**

- Alembic manages the schema. The first migration, `2bf55ef584f4` ("baseline schema"), is an explicit, reviewable description of the four existing tables. Every later change is a new migration in `alembic/versions/`.
- `Base.metadata.create_all()` was removed from `app/main.py`. Importing or starting the app never connects to the database or changes tables; the schema changes only when someone runs `alembic upgrade head`.
- Existing databases that `create_all()` built (local development, Railway production) are adopted by backing them up, comparing them with the models using `scripts/compare_schema.py`, and then running `alembic stamp 2bf55ef584f4`.
- The test suite refuses to reset a database unless its name contains `test` and differs from `DB_NAME` (`tests/db_safety.py`).
- CI migrates an empty MySQL database, re-runs the upgrade, compares the result with the models (`alembic check` and `scripts/compare_schema.py`), and downgrades and upgrades again.

**Why**

- **`create_all()` can't evolve a schema.** It only creates missing tables; it never adds a column, changes a constraint, or moves data. The upcoming `user_id` ownership columns need real migrations, and an existing production table can't be changed any other way.
- **Import-time database writes are dangerous.** Importing `app.main`, which tests, scripts, and the server all do, used to write to whatever database `DB_*` pointed at. A test run or a tool could create tables in the wrong database. A regression test now imports the app with an unresolvable database host and fails on any connection or SQL statement.
- **Stamping is safe only after a comparison.** `alembic stamp` records a revision without checking anything. Comparing first proves the database really matches the baseline. During development the baseline was verified to produce exactly the same tables, columns, indexes, unique keys, and foreign key names as `create_all()`, so databases created by `create_all()` should match.
- **The test-database guard prevents a costly mistake.** The fixtures drop every table. If `TEST_DATABASE_URL` were misconfigured to point at development or production data, the suite would wipe it. The guard checks the actual engine's URL, rejects missing or invalid configuration, and never prints credentials.
- **Tests alone can't prove migrations are correct**, because the test fixtures build tables from the models. CI therefore checks the migrations separately against an empty database.

**Trade-off**

- **Every model change now needs a migration file**, and autogenerated migrations must be reviewed. During development, the autogenerated baseline downgrade failed on MySQL: it tried to drop an index a foreign key depended on, and MySQL can't roll back DDL, so it left the database half-downgraded. The downgrade was rewritten to drop tables directly.
- **Downgrading the baseline drops every table**, so it is only for disposable databases.
- **Production is not stamped yet.** It is a manual step that must happen before the first migration after the baseline is deployed. Migrations also run manually until deploy-time migrations are added in v0.3.0.
- **Tests still build their schema with `create_all()`** for speed and isolation; the CI migration steps cover the gap.

---

## How are records owned, and how do existing records get an owner?

**Decision**

- `companies` and `job_applications` each have a `user_id` column: NOT NULL, indexed, with a named foreign key to `users.id`. Interviews have no `user_id`; they belong to whoever owns their application.
- Create endpoints take the owner from the bearer token (`CurrentUser`) and pass it to the service. A `user_id` in the request body is ignored, and responses don't expose it.
- The schema change is split into two migrations so existing rows are never lost or guessed:
  1. `865d60d22f27` adds the columns as nullable.
  2. `add88b8a484a` assigns unowned rows to an owner named explicitly with `alembic -x owner_email=...`, then enforces NOT NULL.
- Stage 2 checks everything before writing: an owner is required if unowned rows exist, the owner must exist and be active, and every application must end up with the same owner as its company. If a check fails, it changes nothing and leaves the database at stage 1.

**Implemented vs. pending**

| | Status |
| --- | --- |
| Ownership columns, foreign keys, indexes, model relationships | Implemented |
| Owner set from the token on create | Implemented |
| Staged migration with validation, tested against disposable MySQL | Implemented |
| Production backup, stamp, and migration | **Pending:** manual steps in `docs/database-migrations.md` |
| Which account owns existing production records | **Pending:** not chosen yet |
| Reads, updates, deletes, and parent references scoped to the owner | **Pending:** #20 |

**Why**

- **Applications store `user_id` directly** rather than relying only on their company. Owner filtering then doesn't need a join, and #20 can scope every query the same way. The consistency check keeps the two from disagreeing on existing data. (Enforcing it for new records belongs to #20's parent-ownership checks.)
- **Interviews don't get a column** because an interview can't exist without an application. A second owner field could only ever duplicate the application's, or contradict it.
- **Two stages instead of one** because a NOT NULL column can't be added to a table with rows that have no value. Nullable first, assign, then enforce is the standard safe sequence. It also lets stage 1 run before the new code is deployed, while the old code keeps working.
- **The owner is never guessed.** Assigning everything to "the first user", or deleting rows, would silently hand data to the wrong account or destroy it. Requiring an explicit `owner_email`, and refusing to continue otherwise, keeps that decision with a person.
- **Checks run before writes, and each revision commits on its own** (`transaction_per_migration=True`). MySQL can't roll back schema changes, so a stopped stage 2 must leave the database consistent at stage 1, with the right revision recorded and nothing half-done.
- **The owner comes from the token, not the request body,** so a client can't create records on another user's behalf.

**Trade-off**

- **Isolation is not complete yet.** Records now have owners, but every authenticated user can still read and change every record until #20 scopes the queries.
- Until then, a user can also create an application under another user's company; the parent-ownership check belongs to #20.
- `owner_email` assigns all unowned rows to one account. Splitting existing data between accounts requires manual SQL between the stages.
- **Undoing stage 1 permanently discards owner assignments,** although it keeps the records themselves.
- Production needs a manual, ordered procedure: back up, stamp, stage 1, deploy, stage 2, verify. It stays manual until deploy-time migrations arrive in v0.3.0.

---

## How is each user's data kept separate?

**Decision**

- Every service function that reads or changes companies, applications, or interviews takes a keyword-only `user_id`. Each endpoint passes `current_user.id`.
- **Single-record lookups** (`require_company_by_id`, `require_application_by_id`, `require_interview_by_id`) filter by ID **and** owner in one query.
- **Lists, filters, search, sorting, and pagination** all start from the user's own records.
- **Interviews** are scoped by joining to their application (`JobApplication.user_id`), since they have no owner column of their own.
- **Referenced parents are checked too:** creating or updating an application requires the `company_id` to belong to the user, and creating or updating an interview requires the `application_id` to belong to the user. These checks reuse the same owner-scoped lookups.
- Another user's record returns **404 with the same body as a missing ID** ("Company not found", and so on), not 403.
- Unscoped lookup helpers that bypassed ownership (`db.get` by primary key) were removed. Every remaining lookup is owner-scoped.

**Why**

- **One rule, applied at the data layer.** Scoping inside the queries, rather than loading a record and checking its owner afterwards in each route, means a route can't forget the check; an unscoped lookup simply doesn't exist to call.
- **404 instead of 403:** a 403 would confirm that the ID exists and belongs to someone else, letting a user enumerate other users' records. Treating "not yours" and "doesn't exist" identically reveals nothing.
- **Checking referenced parents** stops a user from attaching their records to someone else's company or application. That would leak the parent's existence, and would mix two users' data under one company.
- **Validation before changes:** ownership checks run before any field is modified, so a rejected create or update writes nothing.
- **Tests guard every path:** `tests/test_isolation.py` has user B try to read, list, filter, search, update, delete, and re-parent user A's records. Removing scoping from a single query fails these tests.

**Trade-off**

- The duplicate-`job_url` check is still global, because the database constraint is global; changing it to per-user is #21. Until then, a user who adds a URL another user already tracks gets a 409.
- Every service call now needs a `user_id`. That's more parameters, but it keeps the scoping explicit and impossible to skip.
- Interview queries add a join to `job_applications`; the join uses the existing indexed foreign key.

---

## What happens on delete, duplicates, and database conflicts?

**Decision**

- **Deleting a company that has applications returns `409 Conflict`** ("Company has job applications. Delete or move them first."). A company with no applications deletes normally. The existing foreign key from `job_applications` (no `ON DELETE` action, so MySQL restricts the delete) also blocks it at the database level.
- **Deleting an application deletes its interviews.** The ORM relationship uses `cascade="all, delete-orphan"` with `passive_deletes=True`, and migration `9e9a352c0176` recreates the interview foreign key as `fk_interviews_application_id_job_applications` with `ON DELETE CASCADE`.
- **Job URLs are unique per user:** `uq_job_applications_user_id_job_url` on `(user_id, job_url)` replaces the global unique key on `job_url`. The service's duplicate check only looks at the user's own applications.
- **Company names have no uniqueness rule.** The README's "prevent duplicate company records" claim was removed instead. Nothing in the project had decided what makes two companies "the same" (for example, separate offices with the same name), so adding a constraint would have invented a rule.
- **Database conflicts:**
  - A global `IntegrityError` handler returns `409` with a generic message ("The request conflicts with existing data.") and logs the database error, method, and path server-side.
  - Every service commit goes through `commit_or_rollback()`, which rolls the session back before re-raising.
  - `get_db()` also rolls back on any exception.

**Why**

- **409 for companies instead of cascading:** deleting an employer shouldn't quietly erase the job history filed under it. An application, by contrast, owns its interviews, which mean nothing on their own, so cascading there is the expected behavior.
- **Database rules back up the service checks.** The service checks give friendly messages, but two concurrent requests can both pass a check. The unique key, the restrictive foreign key, and the cascade foreign key keep the data correct either way.
- **Per-user URLs:** with a global key, user B couldn't track a posting user A already tracked, and the 409 would reveal that someone did. Per user, each person's list is independent.
- **Generic conflict messages:** raw MySQL errors include table, constraint, and column names and the submitted values (for example, `Duplicate entry '9-https://…' for key '…'`). Those go to the server log only.
- **Explicit rollback:** a failed commit leaves the SQLAlchemy session unusable until it's rolled back. Rolling back at the point of failure guarantees nothing from the failed request is left pending, whatever happens afterwards. A test proves the next request on the same session still works.
- **Migration safety:** the migration creates the new per-user key before dropping the global one, so URLs are never left unprotected. It also finds the old constraints by their columns, because the baseline let MySQL name them.

**Trade-off**

- To delete a company, a user must first delete or move its applications, which is an extra step.
- The two delete paths behave differently: company deletes are refused while application deletes cascade. The API documentation and this entry explain the difference.
- The generic 409 doesn't say which value conflicted; the friendlier messages come from the service checks, which cover normal use.
- **Downgrading `9e9a352c0176`** restores the global URL key, and stops without changing anything if two users already share a URL.
- Until `9e9a352c0176` runs in production, the deployed per-user check and the old global key can disagree. Those requests get the generic 409 (see `docs/database-migrations.md`).

---

## How are dates, times, and text inputs validated?

**Decision**

- **Datetime input must include a UTC offset** (`Z`, `+00:00`, `-05:00`, and so on). That applies to `scheduled_at` and the `scheduled_from`/`scheduled_to` filters. A datetime without an offset is rejected with `422` ("Input should have timezone info"). Accepted values are converted to UTC.
- **Storage and output are UTC:**
  - Every datetime column uses `UTCDateTime`, a SQLAlchemy type over MySQL `DATETIME`. It converts offset-aware values to UTC before storing them and marks every value it reads as UTC.
  - Responses therefore always carry an explicit offset (`2026-11-01T15:00:00Z`).
  - Each MySQL connection sets `time_zone = '+00:00'`, so `NOW()` defaults (`created_at`, `updated_at`) are UTC regardless of the server's configuration.
- **Required text** (`Company.name`, `JobApplication.job_title`) has surrounding whitespace removed, and a value that's empty afterwards is rejected.
- **Notes fields** are limited to 65,535 bytes **of UTF-8**, which is MySQL `TEXT`'s capacity, rather than to a character count.
- **`GET /companies`** takes `limit` (1–100, default 20) and `offset` (≥ 0), ordered by name and then ID.
- **Login** no longer checks password length. A short password is just a wrong password and gets the same `401` as any failed login. The 8-character minimum stays at registration.

**Existing stored values**

Values stored before this change are **not converted**. Their original timezone isn't known and can't be recovered:

- Interview times were stored as the wall-clock time the client sent, with any offset dropped.
- `created_at` and `updated_at` came from `NOW()` in the MySQL server's own timezone at the time.

They are now **returned labelled as UTC**. That's correct only if the original input or the server was already UTC, and nothing here changes or relabels production data. Correcting old records would need someone who knows what zone they were entered in.

The new rules apply only to **requests**. Response models accept what's already stored, so a record saved earlier with a blank name or other legacy value can still be read.

**Why**

- **Reject naive datetimes rather than guess.** Assuming UTC (or any zone) for a value without an offset silently stores the wrong instant whenever the guess is wrong, which is exactly the bug the audit found (10:00-05:00 stored as 10:00). Requiring the offset makes the client state what it means.
- **Normalize in the column type** as well as in request validation, so code that writes datetimes without going through the API (scripts, tests, future services) is converted the same way. A test writes a `-05:00` value straight through the ORM to prove it.
- **Bytes, not characters, for notes:** a 16,384-character note made of emoji is 65,536 bytes and wouldn't fit in `TEXT`. A character limit would either reject long plain-text notes unnecessarily or let multi-byte notes overflow into a database error.
- **Strip required text:** a name of only spaces looks empty everywhere it's shown. Stripping also stops near-duplicates like `"Acme"` and `"Acme "`.
- **Paginate companies** for consistency with applications and interviews, and so the list stays bounded. The ID tie-breaker keeps page boundaries stable when names repeat.
- **No length check at login:** returning `422` for a short password tells a caller something about the password rules instead of simply saying the login failed.

**Trade-off**

- **Clients must send offsets.** A request that used to send `2026-11-01T15:00:00` now gets 422 until it adds `Z` or an offset.
- **`GET /companies` now returns at most 20 companies by default.** Clients with more must page with `limit`/`offset`, as they already do for applications and interviews.
- **Old timestamps are labelled UTC without proof.** This is documented rather than "fixed", because fixing it would mean guessing.
- The byte limit is checked after the request body is parsed, so a very large note is still read into memory before being rejected; a request-size limit at the server or proxy is the place to cap that.

---

## How is the README kept accurate?

**Decision**

- The README describes **verified behavior only**:
  - Endpoints require a bearer token, and each user only sees their own records.
  - Another user's record returns 404.
  - Company names aren't unique, and a company with applications can't be deleted.
  - Job URLs are unique per user.
  - Datetimes require an offset and are returned in UTC.
- Test count and coverage come from an actual run of the full suite (213 tests, 99%) on the combined v0.2.0 changes.
- "Production-ready" was removed. Claims about the live demo are limited to what it actually runs: the latest release on `main`.
- The project structure section is generated from the tracked files, including `alembic/`, `docs/`, `scripts/`, and the `exceptions/` and `handlers/` packages, which earlier versions listed as single files.
- Completed items (Alembic migrations, GitHub Actions CI) were removed from "Future Enhancements".
- The coverage screenshot is labelled as being from v0.1.0 rather than replaced with an unverified image.

**Why**

- A reviewer reading the README and then the code should find the same thing. The v0.1.0 README claimed protected endpoints and duplicate-company prevention that didn't exist; overstated claims cost more credibility than missing features.
- Counts and structure drift as code changes, so they are taken from the repository and a real test run rather than written from memory.

**Trade-off**

- The test count must be updated whenever tests are added. It's a number, not a badge, until CI reporting is added in v0.3.0.
- The README describes `develop` once these changes are merged. The live demo only matches it after the next release; the README says so rather than claiming features are already deployed.

---

## How is the app deployed and migrated on Railway?

**Decision**

- `railway.json` in the repository defines how Railway runs the app:
  - Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
  - Pre-deploy command: `alembic upgrade head`.
  - Health check path: `/health`.
- `.python-version` pins Python **3.12**. Railway's builder reads it, and both CI jobs read the same file (`setup-python`'s `python-version-file`), so production and CI use the same minor version.
- The builder isn't pinned in `railway.json`; the service keeps whichever builder it already uses.

**Why**

- **Settings in the repository are reviewed and versioned.** Before this, the start command lived only in the Railway dashboard, where a change leaves no history and can't be reviewed in a pull request. Railway applies `railway.json` on every deploy and uses it in place of the dashboard values.
- **Migrations run before traffic switches.** Railway runs the pre-deploy command in the new build, with the service's environment variables, before starting it. If the migration fails, the deploy stops and the previous version keeps serving. This replaces the manual `alembic upgrade head` step from the v0.2.0 release.
- **`$PORT` and `0.0.0.0`:** Railway assigns the port and health-checks it, and the server must listen on all interfaces to be reachable inside Railway's network. The start command runs in a shell for Railpack builds, so `$PORT` expands.
- **The Python pin closes a gap.** Without a pin, Railpack defaults to Python 3.13 while CI tests on 3.12, so production could run a version nothing was tested on. One file now drives both.
- **Not pinning the builder** avoids changing how the existing service builds as a side effect of this change. Both builders Railway offers for this repository (Railpack and Nixpacks) honor `.python-version`.

**Trade-off**

- **A failed migration blocks the deploy.** That's intended, but it means a broken migration stops a release until it's fixed. The pre-deploy logs in Railway show why.
- Migrations that need input (`-x owner_email=...`) or that would break the still-running old version still need manual steps before the release (see `docs/database-migrations.md`).
- The health check only confirms the process is serving HTTP; it doesn't check the database connection. A database outage is reported by failing requests, not by the deploy.
- Upgrading Python means editing `.python-version`. CI follows automatically, and the change is reviewed like any other.

---

## What stops the app from running with unsafe production settings?

**Decision**

`get_settings()` loads settings and then checks them (`app/config.py`). With `APP_ENV=production`, the app **refuses to start** if any of these are true:

- `JWT_SECRET_KEY` is shorter than the algorithm requires: 32 bytes for HS256, 48 for HS384, 64 for HS512.
- `JWT_SECRET_KEY` is a placeholder from this repository (the `.env.example` value or the CI value).
- `DB_PASSWORD` is empty.
- `ACCESS_TOKEN_EXPIRE_MINUTES` is outside 1–1440.

In every environment:

- `JWT_ALGORITHM` must be `HS256`, `HS384`, or `HS512`.
- Configuration errors (a missing variable, a non-numeric port) are reported **by variable name only**.

In development, test, and CI, the production checks only log a warning.

**Why**

- **The signing secret protects every login.** Anyone who can guess or brute-force it can mint a token for any user. RFC 7518 requires an HMAC key at least as long as the hash output, which is where the 32/48/64-byte minimums come from. They're measured in bytes because that's what HMAC uses.
- **Failing at startup is the safest moment.** `get_settings()` runs when the app, Alembic, and the scripts import their settings, so a bad production configuration stops Railway's pre-deploy migration and the new version never takes traffic. The previous version keeps running.
- **Secrets stay out of logs.** Pydantic's validation errors include the submitted input, so a missing `DB_HOST` would have printed the password and signing secret into the deployment logs. Errors now list variable names and the requirement, without anything derived from a secret (not even its length), and `repr()` of the settings hides both secrets.
- **Algorithm allow-list:** the app signs with a shared secret, so `none` or an asymmetric algorithm (RS256) can only be a misconfiguration. It's rejected everywhere.
- **Warnings outside production** keep existing local setups and tests running while still pointing out what production would refuse.

**Trade-off**

- **A production deploy with a weak secret fails until the secret is fixed.** That's the point, but the variables must be checked before the first deploy that includes this change.
- **Changing `JWT_SECRET_KEY` logs everyone out**, because existing tokens no longer verify. Users simply log in again.
- The check can't judge randomness. A long but guessable secret passes, so the generation command is suggested in every error.
- Only the exact repository placeholders are recognized. Other weak values that meet the length rule aren't detected.

