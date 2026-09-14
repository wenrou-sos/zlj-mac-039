import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 默认 SQLite 便于本地模拟；部署时设置 DATABASE_URL=postgresql://user:pass@host:5432/yard
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./yard.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def run_migrations():
    """轻量迁移: 旧库缺列时自动补齐 (SQLite/PostgreSQL 通用)"""
    from sqlalchemy import inspect, text
    insp = inspect(engine)
    if "appointments" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("appointments")}
        if "tolerance_hours" not in cols:
            with engine.begin() as conn:
                conn.execute(text(
                    "ALTER TABLE appointments ADD COLUMN tolerance_hours INTEGER DEFAULT 2"))
            print("🔧 迁移: appointments 表补充 tolerance_hours 列")
