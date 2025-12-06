from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os

# Database Configuration (replace with your actual PostgreSQL connection string)
# For simplicity, we'll use a local SQLite file in this running example.
# Replace with 'postgresql://user:password@host:port/dbname' for PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./notes_app.db")

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False} # Needed for SQLite
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()