from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

import os

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")
SQLALCHEMY_DATABASE_URL2 = os.getenv("DATABASE_URL2")

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=40,
    pool_recycle=3600,
)

engine2 = create_engine(
    SQLALCHEMY_DATABASE_URL2,
    pool_size=40,
    pool_recycle=3600,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
SessionLocal2 = sessionmaker(autocommit=False, autoflush=False, bind=engine2)

Base = declarative_base()