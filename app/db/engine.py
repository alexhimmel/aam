"""
数据库引擎配置
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from typing import Optional

# 数据库配置
DATABASE_URL: str = os.getenv(
    'DATABASE_URL',
    'sqlite:////home/alex/.local/share/aam/db.sqlite'
)

# SQLite 开发环境（默认）
if 'postgresql' in DATABASE_URL or 'postgres' in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace('postgresql://', 'sqlite:///').replace('@localhost:5432', '')

# SQLite 开发环境
if DATABASE_URL.startswith('sqlite'):
    DATABASE_URL = DATABASE_URL.replace('sqlite:///', 'sqlite:///')

engine = create_engine(
    DATABASE_URL,
    echo=False,  # 生产环境设为 False
    pool_recycle=3600,
    pool_size=10,
    max_overflow=20,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False
)

Base = declarative_base()


# 导出对象
__all__ = ['engine', 'SessionLocal', 'Base', 'get_db', 'init_db', 'drop_db']


def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化数据库（创建表）"""
    Base.metadata.create_all(bind=engine)
    print("数据库表已创建")


def drop_db():
    """删除所有表（危险操作）"""
    Base.metadata.drop_all(bind=engine)
    print("数据库表已删除")
