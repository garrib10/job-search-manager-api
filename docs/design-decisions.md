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

