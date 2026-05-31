"""
调度配置 API
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
from app.db.models import Schedule
from app.db.engine import get_db

router = APIRouter(prefix="/schedules", tags=["调度配置"])

@router.get("/")
async def list_schedules(task_id: int = None):
    """列出调度配置"""
    db = Depends(get_db)
    schedules = db.query(Schedule).filter(
        Schedule.enabled == True,
        (task_id is None) | (Schedule.task_id == task_id)
    ).all()
    return {"schedules": [s.__dict__ for s in schedules]}

@router.get("/{schedule_id}")
async def get_schedule(schedule_id: int):
    """获取调度配置"""
    db = Depends(get_db)
    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="调度配置不存在")
    return {"schedule": schedule.__dict__}

@router.put("/{schedule_id}")
async def update_schedule(schedule_id: int, schedule_data: dict):
    """更新调度配置"""
    db = Depends(get_db)
    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="调度配置不存在")
    
    # 更新字段
    for key, value in schedule_data.items():
        if hasattr(schedule, key):
            setattr(schedule, key, value)
    
    db.commit()
    db.refresh(schedule)
    return {"schedule": schedule.__dict__, "message": "调度配置已更新"}

@router.post("/{schedule_id}/toggle")
async def toggle_schedule(schedule_id: int):
    """切换调度启用状态"""
    db = Depends(get_db)
    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="调度配置不存在")
    
    schedule.enabled = not schedule.enabled
    db.commit()
    return {"schedule": schedule.__dict__, "message": f"调度{'已启用' if schedule.enabled else '已禁用'}"}
