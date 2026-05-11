import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from utils.runtime_paths import load_app_env


load_app_env()


def _env_value(primary_name, fallback_name, default_value):
    return os.getenv(primary_name) or os.getenv(fallback_name, default_value)


DB_USER = _env_value("MYSQLUSER", "DB_USER", "root")
DB_PASSWORD = _env_value("MYSQLPASSWORD", "DB_PASSWORD", "12345678")
DB_HOST = _env_value("MYSQLHOST", "DB_HOST", "localhost")
DB_NAME = _env_value("MYSQLDATABASE", "DB_NAME", "dorm_management")
DB_PORT = _env_value("MYSQLPORT", "DB_PORT", "3306")

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=20,
    max_overflow=20,
    pool_timeout=5,
    connect_args={
        "connect_timeout": 5,
        "read_timeout": 10,
        "write_timeout": 10,
    },
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
