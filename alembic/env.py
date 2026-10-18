from logging.config import fileConfig

from sqlalchemy import create_engine, pool

from alembic import context
from app.config import get_settings
from app.database import Base

# WHY:
# Importing app.models registers every table with Base.metadata so autogenerate
# and `alembic check` can see them. app.main is deliberately not imported: the
# migration environment only needs model metadata, not the FastAPI app.
import app.models  # noqa: F401, E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# WHY:
# The URL comes from the same DB_* settings the application uses, so no
# credentials live in alembic.ini. It is passed straight to SQLAlchemy rather
# than through config.set_main_option(), whose ini interpolation breaks on "%"
# in passwords, and it is never logged.
database_url = get_settings().database_url


def run_migrations_offline() -> None:
    """Emit migration SQL to stdout without connecting (`alembic upgrade head --sql`)."""
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_with_connection(connection) -> None:
    # WHY:
    # MySQL commits DDL immediately, so each revision runs in its own
    # transaction and records its version as soon as it finishes. If a later
    # revision stops (for example, the ownership migration's safety checks),
    # the database is left at the last completed revision, matching its schema.
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        transaction_per_migration=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations against the database configured by DB_* settings.

    WHY:
    Callers such as the migration tests can pass an existing connection in
    `config.attributes["connection"]` so migrations run against the disposable
    test database instead of DB_*.
    """
    connection = config.attributes.get("connection")

    if connection is not None:
        run_with_connection(connection)
        return

    connectable = create_engine(database_url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        run_with_connection(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
