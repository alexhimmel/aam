"""
调度管理服务
"""

from sqlalchemy.orm import Session
from typing import Optional
from app.db.models import Schedule
from datetime import datetime
import crontab

class ScheduleService:
    """调度配置业务逻辑"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def list_schedules(self, task_id: Optional[int] = None) -> list:
        """列出调度配置"""
        query = self.db.query(Schedule)
        
        if task_id is not None:
            query = query.filter(Schedule.task_id == task_id)
        
        schedules = query.filter(Schedule.enabled == True).all()
        return [s.__dict__ for s in schedules]
    
    def get_schedule(self, schedule_id: int) -> Optional[dict]:
        """获取调度配置"""
        schedule = self.db.query(Schedule).filter(Schedule.id == schedule_id).first()
        if not schedule:
            return None
        return schedule.__dict__
    
    def create_schedule(self, task_id: int, cron_expression: str) -> Schedule:
        """创建调度配置"""
        schedule = Schedule(
            task_id=task_id,
            cron_expression=cron_expression,
            enabled=True
        )
        self.db.add(schedule)
        self.db.commit()
        self.db.refresh(schedule)
        return schedule.__dict__
    
    def update_schedule(self, schedule_id: int, schedule_data: dict) -> Optional[dict]:
        """更新调度配置"""
        schedule = self.db.query(Schedule).filter(Schedule.id == schedule_id).first()
        if not schedule:
            return None
        
        # 更新字段
        for key, value in schedule_data.items():
            if hasattr(schedule, key):
                setattr(schedule, key, value)
        
        self.db.commit()
        self.db.refresh(schedule)
        return schedule.__dict__
    
    def toggle_schedule(self, schedule_id: int) -> Optional[dict]:
        """切换调度启用状态"""
        schedule = self.db.query(Schedule).filter(Schedule.id == schedule_id).first()
        if not schedule:
            return None
        
        schedule.enabled = not schedule.enabled
        self.db.commit()
        self.db.refresh(schedule)
        return schedule.__dict__
