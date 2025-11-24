from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

import os

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")
SQLALCHEMY_DATABASE_URL2 = os.getenv("DATABASE_URL2")

POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "80"))
MAX_OVERFLOW = int(os.getenv("DB_POOL_MAX_OVERFLOW", "40"))
POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))
POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "1800"))

common_pool_kwargs = {
    "pool_size": POOL_SIZE,
    "max_overflow": MAX_OVERFLOW,
    "pool_timeout": POOL_TIMEOUT,
    "pool_recycle": POOL_RECYCLE,
    "pool_pre_ping": True,
}

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    **common_pool_kwargs,
)

engine2 = create_engine(
    SQLALCHEMY_DATABASE_URL2,
    **common_pool_kwargs,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
SessionLocal2 = sessionmaker(autocommit=False, autoflush=False, bind=engine2)

Base = declarative_base()