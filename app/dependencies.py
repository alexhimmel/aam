"""
依赖注入模块
"""
from sqlalchemy.orm import Session
from app.db.engine import SessionLocal

db = SessionLocal()


def get_db():
    """
    获取数据库会话（依赖注入）
    
    Returns:
        Session: 数据库会话
    """
    return db

