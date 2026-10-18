# Database Migrations

The database schema is managed with [Alembic](https://alembic.sqlalchemy.org/). The application never creates or changes tables by itself: importing or starting the app does not touch the schema. Every schema change is a migration file in `alembic/versions/`, applied with an explicit command.

Alembic reads the same `DB_*` settings as the application (from environment variables or `.env`), so it targets whichever database `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, and `DB_PASSWORD` point at. **Check those values before running any command below.**

Run all commands from the repository root with the virtual environment active.

## Contents

1. [Initialize an empty database](#initialize-an-empty-database)
2. [Inspect the current revision and history](#inspect-the-current-revision-and-history)
3. [Create a new migration](#create-a-new-migration)
4. [Baseline downgrade behavior](#baseline-downgrade-behavior)
5. [Adopt Alembic for an existing database](#adopt-alembic-for-an-existing-database)
6. [Status of existing databases](#status-of-existing-databases)
7. [Test database safeguards](#test-database-safeguards)

## Initialize an empty database

For a new, empty database (a fresh local setup, for example):

```bash
alembic upgrade head
```

This creates every table and records the current revision in an `alembic_version` table. Running it again is safe; it does nothing when the database is already at the latest revision.

## Inspect the current revision and history

| Command | What it shows |
| --- | --- |
| `alembic current` | The revision the database is at (empty output means it is not tracked by Alembic) |
| `alembic heads` | The latest revision in the code |
| `alembic history --verbose` | Every migration, newest first |
| `alembic check` | Fails if the models differ from the database (database must be at `head`) |
| `python -m scripts.compare_schema` | Read-only comparison of any database with the models; works even if the database was never stamped |
| `alembic upgrade head --sql` | Prints the SQL a migration would run, without connecting |

## Create a new migration

1. Change the SQLAlchemy models in `app/models/`.
2. Point `DB_*` at a **local, disposable** database that is at `head` (`alembic upgrade head`).
3. Generate the migration:

   ```bash
   alembic revision --autogenerate -m "short description of the change"
   ```

4. **Review the generated file in `alembic/versions/` before committing.** Autogenerate is a starting point, not a finished migration:
   - It cannot detect renames; a renamed column or table appears as a drop plus an add, which would delete data. Rewrite these as `op.alter_column(..., new_column_name=...)` or `op.rename_table(...)`.
   - It does not move or transform data. Adding a `NOT NULL` column to a table that has rows needs a default or a backfill step.
   - MySQL cannot drop an index that a foreign key depends on, and MySQL DDL is not transactional: a migration that fails halfway leaves the schema partly changed. Order operations so they cannot fail midway, and test both directions.
5. Test it locally against the disposable database:

   ```bash
   alembic upgrade head
   alembic check
   alembic downgrade -1
   alembic upgrade head
   ```

6. Commit the migration together with the model change. CI runs the migrations on an empty MySQL database and fails if the result does not match the models.

## Baseline downgrade behavior

The first migration, `2bf55ef584f4` ("baseline schema"), creates the tables that existed before Alembic was introduced.

**Downgrading it (`alembic downgrade base`) drops every table and permanently deletes all data in them.** It exists so CI and local development can rebuild from scratch. Never run it against production or any database whose data you need.

## Adopt Alembic for an existing database

Databases created before Alembic (by the old `Base.metadata.create_all()` call) already have the tables but no `alembic_version` record. Running `alembic upgrade head` on them would try to create tables that already exist and fail.

Instead, **stamp** the database: `alembic stamp` writes the revision ID into `alembic_version` and does nothing else. **It does not create, check, or fix any table.** Stamping a database whose schema does not match the baseline would make Alembic believe the schema is correct when it is not, and later migrations could fail or corrupt data. That is why the backup and comparison steps below are required.

### Steps

1. **Back up the database.**
   - Railway: open the MySQL service → **Backups** → create a backup, and confirm it completes. You can also run `mysqldump` from your machine using the connection details from the MySQL service's **Variables** tab.
   - Local MySQL:

     ```bash
     mysqldump --single-transaction -h <host> -u <user> -p <database> > backup-$(date +%F).sql
     ```

2. **Point `DB_*` at that database.** For Railway, set the variables in your shell from the MySQL service's public connection details (do not commit them). Double-check `DB_NAME` and `DB_HOST`.

3. **Confirm it is not already tracked:**

   ```bash
   alembic current
   ```

   Empty output means it has never been stamped. If it shows a revision, stop: it is already managed by Alembic.

4. **Compare the schema with the models (read-only):**

   ```bash
   python -m scripts.compare_schema
   ```

   Continue only if it prints `Schema matches the models.` The baseline was verified to produce exactly the same tables, columns, indexes, unique keys, and foreign keys as `create_all()`, so a database created by `create_all()` from the current models should match.

5. **Stamp it at the baseline revision.** Use the explicit revision ID, not `head`, so that later migrations are not skipped:

   ```bash
   alembic stamp 2bf55ef584f4
   ```

6. **Verify:**

   ```bash
   alembic current   # 2bf55ef584f4
   alembic check     # No new upgrade operations detected.
   ```

7. From now on, apply future migrations with `alembic upgrade head`.

To undo a stamp, run `alembic stamp base`. It only deletes the `alembic_version` record; tables and data are untouched.

### If the schema does not match

Do **not** stamp. Look at the differences `scripts/compare_schema` reports:

- **Missing or extra indexes, or small type differences:** apply SQL by hand to make the database match the baseline (`alembic upgrade 2bf55ef584f4 --sql` prints the exact baseline DDL for reference), then compare again.
- **Missing tables or columns on a local or disposable database you don't need:** drop the database, recreate it empty, and run `alembic upgrade head`.
- **Production, or any database with data you need:** stop and plan the fix before changing anything. Typically: export the data, build a fresh schema with `alembic upgrade head`, and import the data back. Keep the backup from step 1 until the database is verified.

## Status of existing databases

| Database | Status |
| --- | --- |
| CI (`job_search_ci_app`) | Created fresh by `alembic upgrade head` on every run |
| Local development | Created by `create_all()`; needs the adoption steps above |
| Railway production | Created by `create_all()`; **not stamped yet**. Must be adopted (steps above) before any migration after the baseline is deployed |

Until migrations run automatically on deploy (planned for v0.3.0), apply them manually with `alembic upgrade head` against production before deploying code that depends on them.

## Test database safeguards

The test suite (`tests/conftest.py`) drops and recreates all tables, and deletes every row after each test. Before doing anything destructive it checks the URL of the engine it will use (`TEST_DATABASE_URL`) and refuses to continue unless:

- the database name contains `test`, and
- it is different from `DB_NAME`.

A missing or invalid `TEST_DATABASE_URL` also stops the run. Error messages name the database but never print the URL or credentials. The checks live in `tests/db_safety.py` and are covered by `tests/test_db_safety.py`.

The test suite creates its tables directly from the models, so passing tests do not prove the migrations are correct. CI verifies the migrations separately.
