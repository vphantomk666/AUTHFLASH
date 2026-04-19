from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DataBase_URL")

if DATABASE_URL is None:
    raise ValueError("DataBase_URL is not set")

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