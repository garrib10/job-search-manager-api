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

