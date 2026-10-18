"""
Compare a live database's schema with the SQLAlchemy models. Read-only.

Usage (from the repository root, with DB_* pointing at the database to check):

    python -m scripts.compare_schema

Exits 0 when the schema matches the models and 1 when it does not, listing each
difference. Use it before `alembic stamp` when adopting Alembic for a database
that was created by Base.metadata.create_all(): unlike `alembic check`, it does
not require the database to be stamped first. It never writes to the database
and never prints connection details. See docs/database-migrations.md.
"""

import sys

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, pool

import app.models  # noqa: F401  (registers every table with Base.metadata)
from app.config import get_settings
from app.database import Base


def describe(difference) -> str:
    """Turn one Alembic autogenerate difference into a readable line."""
    if isinstance(difference, list):
        return "; ".join(describe(item) for item in difference)

    operation = difference[0]

    if operation in ("add_table", "remove_table"):
        return f"{operation}: {difference[1].name}"

    if operation in ("add_index", "remove_index"):
        index = difference[1]
        return f"{operation}: {index.name} on {index.table.name}"

    if operation in ("add_column", "remove_column"):
        _, _, table_name, column = difference
        return f"{operation}: {table_name}.{column.name}"

    if operation.startswith("modify_"):
        _, _, table_name, column_name, _, existing, new = difference
        return f"{operation}: {table_name}.{column_name} ({existing!r} -> {new!r})"

    return f"{operation}: {difference[1:]!r}"


def main() -> int:
    engine = create_engine(get_settings().database_url, poolclass=pool.NullPool)

    with engine.connect() as connection:
        context = MigrationContext.configure(connection, opts={"compare_type": True})
        differences = compare_metadata(context, Base.metadata)

    if not differences:
        print("Schema matches the models.")
        return 0

    print(f"Schema does NOT match the models ({len(differences)} difference(s)):")
    for difference in differences:
        print(f"  - {describe(difference)}")

    return 1


if __name__ == "__main__":
    sys.exit(main())
