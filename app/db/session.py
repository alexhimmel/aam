"""
数据库会话管理
"""

from sqlalchemy.orm import Session
from app.db.engine import SessionLocal, Base

def create_db_session():
    """创建数据库会话工厂"""
    return SessionLocal


def get_base():
    """获取 Base 类"""
    return Base
