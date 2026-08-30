import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./zenvoraa.db")

if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

def get_engine():
    global DATABASE_URL
    if DATABASE_URL and not DATABASE_URL.startswith("sqlite"):
        try:
            eng = create_engine(
                DATABASE_URL,
                connect_args={"connect_timeout": 3},
                pool_pre_ping=True
            )
            with eng.connect() as conn:
                conn.execute(text("SELECT 1"))
            return eng
        except Exception as e:
            print(f"⚠️ Remote PostgreSQL unreachable ({e}). Using local SQLite database.")
            DATABASE_URL = "sqlite:///./zenvoraa.db"
    
    return create_engine(
        "sqlite:///./zenvoraa.db",
        connect_args={"check_same_thread": False},
        pool_pre_ping=True
    )

engine = get_engine()

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()