from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import create_engine
from thermoscope.config import Settings

settings = Settings()
if settings.database_url is None:
    raise RuntimeError("DATABASE_URL is required for migrations")
url = settings.database_url.get_secret_value()

if context.is_offline_mode():
    context.configure(url=url, literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = create_engine(url, poolclass=pool.NullPool, hide_parameters=True)
    try:
        with engine.connect() as connection:
            context.configure(connection=connection)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()
