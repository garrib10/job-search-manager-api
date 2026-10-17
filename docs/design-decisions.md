# Design Decisions

Each entry records a question about how the project works, the decision made, why, and the trade-off accepted.

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
- `pull_request_target` runs with write permissions, which is dangerous if the workflow runs code from the pull request. This workflow has no `run:` steps and no checkout; the labeler only reads the list of changed file paths through the GitHub API, and the workflow and label rules always come from the base branch.

**Trade-off**

- Because the workflow and rules are read from the base branch, changes to `.github/labeler.yml` only take effect after they are merged, and the pull request that adds the labeler is not labeled by it.
- `sync-labels` is left off, so labels are only added, never removed automatically, and labels added by hand are preserved.
