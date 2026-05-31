"""
数据库迁移脚本 - 添加任务功能字段
添加任务类型、工作目录、上传目录等字段
"""

from sqlalchemy import text


def migrate():
    """添加新字段到 tasks 表"""
    print("开始迁移：添加任务功能字段...")
    
    # 添加 task_type 字段
    print("添加 task_type 字段...")
    engine = text("ALTER TABLE tasks ADD COLUMN task_type VARCHAR(20) DEFAULT 'command'")
    
    # 添加 working_dir 字段
    print("添加 working_dir 字段...")
    engine += text("ALTER TABLE tasks ADD COLUMN working_dir TEXT")
    
    # 添加 upload_dir 字段
    print("添加 upload_dir 字段...")
    engine += text("ALTER TABLE tasks ADD COLUMN upload_dir VARCHAR(200)")
    
    # 执行迁移
    from app.db.engine import engine as db_engine
    with db_engine.connect() as conn:
        conn.execute(engine)
        conn.commit()
    
    print("迁移完成！")
    print("新增字段:")
    print("  - task_type: 任务类型 (command/脚本/文件)")
    print("  - working_dir: 工作目录 (上传文件的目标目录)")
    print("  - upload_dir: 上传目录 (文件上传的相对路径)")
    print()
    print("默认值:")
    print("  - task_type='command' (保持向后兼容)")
    print("  - working_dir=NULL (可选)")
    print("  - upload_dir=NULL (仅脚本/文件任务使用)")


def drop_all():
    """删除所有表（危险，仅用于重置）"""
    print("删除所有表...")
    from app.db.models import Base
    from app.db.engine import engine as db_engine
    Base.metadata.drop_all(bind=db_engine)
    print("表已删除")


if __name__ == '__main__':
    migrate()
