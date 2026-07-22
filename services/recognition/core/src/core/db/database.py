import json

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from core.config import config

engine = create_engine(
    config.DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    json_serializer=lambda value: json.dumps(value, ensure_ascii=False),
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """数据库会话依赖 - FastAPI 中使用 yield 自动关闭"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
