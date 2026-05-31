"""
数据库迁移脚本
创建所有表
"""

from app.db.engine import init_db, engine
from app.db.models import Base

def migrate():
    """创建表结构"""
    print("创建数据库表...")
    Base.metadata.create_all(bind=engine)
    print("表创建完成")

def drop_all():
    """删除所有表（危险）"""
    print("删除所有表...")
    Base.metadata.drop_all(bind=engine)
    print("表已删除")

if __name__ == '__main__':
    migrate()
