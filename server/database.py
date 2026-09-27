"""
server/database.py

Configures database connections using SQLAlchemy.
Supports production PostgreSQL databases (via DATABASE_URL)
with automatic fallback to local SQLite (sqlite:///./data/smarteval.db)
for zero-configuration local development.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Priority 1: Environment variable DATABASE_URL (for PostgreSQL in production, Docker, or Cloud)
# Priority 2: Local SQLite file in data/ directory
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/smarteval.db")

# Handle Heroku / Render "postgres://" url prefix -> "postgresql://"
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Ensure data directory exists if using SQLite
if DATABASE_URL.startswith("sqlite"):
    os.makedirs("data", exist_ok=True)
    connect_args = {"check_same_thread": False}
else:
    connect_args = {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Dependency that provides a database session to FastAPI route handlers."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Create all tables in the database."""
    Base.metadata.create_all(bind=engine)
