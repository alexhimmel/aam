"""
API 依赖注入
"""

from sqlalchemy.orm import Session
from app.db.engine import get_db

def get_db() -> Session:
    """获取数据库会话"""
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()
