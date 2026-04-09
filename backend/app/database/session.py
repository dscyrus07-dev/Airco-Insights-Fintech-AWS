import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

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


def initialize_database() -> None:
    if DATABASE_URL.startswith("postgresql"):
        # Coordinate schema creation across multiple workers so Postgres DDL does not race.
        with engine.begin() as connection:
            connection.execute(text("SELECT pg_advisory_lock(hashtext('airco_schema_init'))"))
            try:
                Base.metadata.create_all(bind=connection)
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
            finally:
                connection.execute(text("SELECT pg_advisory_unlock(hashtext('airco_schema_init'))"))
        return

    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
