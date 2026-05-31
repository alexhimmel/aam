"""
Execution 模型
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base
from datetime import timedelta

SqlAlchemyBase = declarative_base()

class Execution(SqlAlchemyBase):
    """执行记录表"""
    __tablename__ = 'executions'
    
    id = Column(Integer, primary_key=True, comment='执行记录 ID')
    task_id = Column(Integer, ForeignKey('tasks.id'), nullable=False, comment='任务 ID')
    
    # 执行信息
    command = Column(Text, nullable=False, comment='执行的命令')
    target_host = Column(String(50), comment='目标主机')
    session_id = Column(String(100), nullable=True, comment='SSH 会话 ID')
    
    # 状态
    status = Column(String(20), default='pending', comment='执行状态')
    exit_code = Column(Integer, nullable=True, comment='退出码')
    stdout = Column(Text, nullable=True, comment='标准输出')
    stderr = Column(Text, nullable=True, comment='标准错误')
    
    # 时间
    started_at = Column(DateTime(timezone=True), nullable=True, comment='开始时间')
    completed_at = Column(DateTime(timezone=True), nullable=True, comment='完成时间')
    duration_seconds = Column(Integer, nullable=True, comment='执行时长（秒）')
    
    # 错误处理
    error_message = Column(Text, nullable=True, comment='错误消息')
    retry_count = Column(Integer, default=0, comment='重试次数')
    
    # 索引
    __table_args__ = (
        {'mysql_engine': 'InnoDB'},
    )
