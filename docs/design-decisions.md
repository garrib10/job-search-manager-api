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
