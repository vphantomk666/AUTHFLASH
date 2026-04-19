from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DataBase_URL")

if DATABASE_URL is None:
    raise ValueError("DataBase_URL is not set")

db_name = "authenticaton"

DATABASE_URL_without_db = DATABASE_URL.rsplit("/", 1)[0]

engine = create_engine(
    DATABASE_URL_without_db,
    pool_pre_ping=True,
    pool_recycle=300
)

try:
    with engine.connect() as conn:
        conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {db_name}"))
        print(f"Database {db_name} ready")
except Exception as e:
    print(f"Note: {e}")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300
)

SessionLocal = sessionmaker(
    autoflush=False,
    autocommit=False,
    bind=engine
)

Base = declarative_base()


# ✅ dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ✅ optional test (safe)
# if __name__ == "__main__":
#     connection = None
#     try:
#         connection = engine.connect()
#         print("✅ Database connected successfully")
#     except Exception as e:
#         print(f"❌ DB connection error: {e}")
#     finally:
#         if connection:
#             connection.close()