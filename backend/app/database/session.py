import os
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker, declarative_base

from ..utils.logging import get_logger

logger = get_logger(__name__)

raw_database_url = os.getenv("DATABASE_URL", "").strip()
if not raw_database_url or "pooler.supabase.com" in raw_database_url:
    DATABASE_URL = "postgresql://airco:airco123@app-postgres:5432/airco_app"
else:
    DATABASE_URL = raw_database_url

engine_kwargs = {"pool_pre_ping": True}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs["pool_size"] = 5
    engine_kwargs["max_overflow"] = 10

engine = create_engine(DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def _ensure_user_file_record_batch_columns() -> None:
    inspector = inspect(engine)
    if 'user_file_records' not in inspector.get_table_names():
        return

    columns = {column['name'] for column in inspector.get_columns('user_file_records')}

    statements = []
    if 'batch_id' not in columns:
        statements.append(
            "ALTER TABLE user_file_records ADD COLUMN batch_id VARCHAR(64)"
        )
    if 'statement_label' not in columns:
        statements.append(
            "ALTER TABLE user_file_records ADD COLUMN statement_label VARCHAR(255)"
        )

    if not statements:
        return

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


def initialize_database() -> None:
    if DATABASE_URL.startswith("postgresql"):
        # Coordinate schema creation across multiple workers so Postgres DDL does not race.
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT pg_advisory_lock(hashtext('airco_schema_init'))"))
                try:
                    Base.metadata.create_all(bind=connection)
                    connection.execute(
                        text("ALTER TABLE user_file_records ADD COLUMN IF NOT EXISTS batch_id VARCHAR(64)")
                    )
                    connection.execute(
                        text("ALTER TABLE user_file_records ADD COLUMN IF NOT EXISTS statement_label VARCHAR(255)")
                    )
                    connection.execute(
                        text(
                            "CREATE INDEX IF NOT EXISTS ix_user_file_records_user_created_at "
                            "ON user_file_records (user_id, created_at)"
                        )
                    )
                    connection.execute(
                        text(
                            "CREATE INDEX IF NOT EXISTS ix_user_file_records_user_status "
                            "ON user_file_records (user_id, status)"
                        )
                    )
                    connection.execute(
                        text(
                            "CREATE INDEX IF NOT EXISTS ix_user_file_records_user_batch_created_at "
                            "ON user_file_records (user_id, batch_id, created_at)"
                        )
                    )
                    connection.commit()
                except Exception:
                    connection.rollback()
                    raise
                finally:
                    try:
                        connection.execute(text("SELECT pg_advisory_unlock(hashtext('airco_schema_init'))"))
                        connection.commit()
                    except Exception:
                        connection.rollback()
        except OperationalError as exc:
            logger.warning("Database unavailable; skipping schema initialization", error=str(exc))
            return
        except Exception:
            raise
        return

    Base.metadata.create_all(bind=engine)
    _ensure_user_file_record_batch_columns()
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_user_file_records_user_created_at "
                "ON user_file_records (user_id, created_at)"
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_user_file_records_user_status "
                "ON user_file_records (user_id, status)"
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_user_file_records_user_batch_created_at "
                "ON user_file_records (user_id, batch_id, created_at)"
            )
        )
    


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
