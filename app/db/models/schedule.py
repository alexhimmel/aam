"""
Schedule 模型
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base

SqlAlchemyBase = declarative_base()

class Schedule(SqlAlchemyBase):
    """调度配置表"""
    __tablename__ = 'schedules'
    
    id = Column(Integer, primary_key=True, comment='ID')
    task_id = Column(Integer, ForeignKey('tasks.id'), nullable=False, comment='任务 ID')
    cron_expression = Column(String(50), nullable=False, comment='Cron 表达式')
    last_run_at = Column(DateTime(timezone=True), nullable=True, comment='上次运行时间')
    next_run_at = Column(DateTime(timezone=True), nullable=True, comment='下次运行时间')
    timezone = Column(String(50), default='Asia/Shanghai', comment='时区')
    enabled = Column(Boolean, default=True, comment='是否启用')
    
    __table_args__ = (
        {'mysql_engine': 'InnoDB'},
    )
