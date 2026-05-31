"""
数据库基础模型
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base
from datetime import timedelta

SqlAlchemyBase = declarative_base()

class Task(SqlAlchemyBase):
    """任务表"""
    __tablename__ = 'tasks'
    
    id = Column(Integer, primary_key=True, comment='任务 ID')
    name = Column(String(100), unique=True, nullable=False, comment='任务名称')
    command = Column(Text, nullable=True, comment='要执行的命令')
    description = Column(Text, nullable=True, comment='任务描述')
    
    # 调度配置
    schedule = Column(String(50), nullable=True, comment='Cron 表达式')
    timezone = Column(String(50), default='Asia/Shanghai', comment='时区')
    enabled = Column(Boolean, default=True, comment='是否启用')
    
    # 目标设备
    target_hosts = Column(Text, nullable=False, comment='目标主机列表 (JSON)')
    ssh_user = Column(String(50), default='root', comment='SSH 用户名')
    ssh_port = Column(Integer, default=22, comment='SSH 端口')
    
    # 任务类型与执行策略
    task_type = Column(String(20), default='command', comment='任务类型：command/脚本/文件')
    working_dir = Column(Text, nullable=True, comment='工作目录（上传文件的目标目录）')
    upload_dir = Column(String(200), nullable=True, comment='上传目录（文件上传的相对路径）')
    
    # 执行配置
    timeout_seconds = Column(Integer, default=300, comment='命令超时时间（秒）')
    max_retries = Column(Integer, default=3, comment='最大重试次数')
    retry_delay_seconds = Column(Integer, default=60, comment='重试延迟（秒）')
    
    # 状态
    status = Column(String(20), default='draft', comment='任务状态')
    
    # 执行结果
    output = Column(Text, nullable=True, comment='命令输出')
    error = Column(Text, nullable=True, comment='错误信息')
    
    # 时间戳
    created_at = Column(String(50), nullable=True, comment='创建时间')
    updated_at = Column(String(50), nullable=True, comment='更新时间')
    
    __table_args__ = (
        {'mysql_engine': 'InnoDB'},
    )
