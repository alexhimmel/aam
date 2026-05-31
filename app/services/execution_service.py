"""
执行记录服务
"""

from sqlalchemy.orm import Session
from typing import Optional
from app.db.models import Execution
from datetime import datetime

class ExecutionService:
    """执行记录业务逻辑"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def list_executions(
        self,
        task_id: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> list:
        """列出执行记录"""
        query = self.db.query(Execution)
        
        if task_id is not None:
            query = query.filter(Execution.task_id == task_id)
        if status is not None:
            query = query.filter(Execution.status == status)
        
        executions = query.order_by(Execution.started_at.desc()) \
            .limit(limit) \
            .offset(offset) \
            .all()
        
        return [e.__dict__ for e in executions]
    
    def get_execution(self, execution_id: int) -> Optional[dict]:
        """获取执行记录"""
        execution = self.db.query(Execution).filter(Execution.id == execution_id).first()
        if not execution:
            return None
        return execution.__dict__
    
    def create_execution(self, task_id: int, command: str, target_host: str) -> Execution:
        """创建执行记录"""
        execution = Execution(
            task_id=task_id,
            command=command,
            target_host=target_host,
            status='pending'
        )
        self.db.add(execution)
        self.db.commit()
        self.db.refresh(execution)
        return execution.__dict__
    
    def update_execution(self, execution_id: int, execution_data: dict) -> Optional[dict]:
        """更新执行记录"""
        execution = self.db.query(Execution).filter(Execution.id == execution_id).first()
        if not execution:
            return None
        
        # 更新字段
        for key, value in execution_data.items():
            if hasattr(execution, key):
                setattr(execution, key, value)
        
        self.db.commit()
        self.db.refresh(execution)
        return execution.__dict__
    
    def retry_execution(self, execution_id: int) -> Optional[dict]:
        """重试执行"""
        execution = self.db.query(Execution).filter(Execution.id == execution_id).first()
        if not execution:
            return None
        
        execution.status = 'pending'
        execution.retry_count = 0
        execution.started_at = None
        execution.completed_at = None
        execution.error_message = None
        execution.stderr = None
        execution.exit_code = None
        execution.stdout = None
        
        self.db.commit()
        self.db.refresh(execution)
        return execution.__dict__
