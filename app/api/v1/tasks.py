"""
任务管理 API
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
from app.db.models import Task
from app.db.engine import get_db
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["任务管理"])

@router.get("/")
async def list_tasks(enabled: bool = True):
    """列出所有任务"""
    db = Depends(get_db)
    service = TaskService(db)
    tasks = service.list_tasks(enabled=enabled)
    return {"tasks": tasks}

@router.post("/")
async def create_task(task_data: dict):
    """创建新任务"""
    db = Depends(get_db)
    service = TaskService(db)
    task = service.create_task(task_data)
    return {"task": task, "message": "任务创建成功"}

@router.get("/{task_id}")
async def get_task(task_id: int):
    """获取任务详情"""
    db = Depends(get_db)
    service = TaskService(db)
    task = service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"task": task}

@router.put("/{task_id}")
async def update_task(task_id: int, task_data: dict):
    """更新任务"""
    db = Depends(get_db)
    service = TaskService(db)
    task = service.update_task(task_id, task_data)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"task": task, "message": "任务更新成功"}

@router.delete("/{task_id}")
async def delete_task(task_id: int):
    """删除任务"""
    db = Depends(get_db)
    service = TaskService(db)
    result = service.delete_task(task_id)
    if not result:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"message": "任务已删除"}

@router.post("/{task_id}/enable")
async def enable_task(task_id: int):
    """启用任务"""
    db = Depends(get_db)
    service = TaskService(db)
    task = service.enable_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"task": task, "message": "任务已启用"}

@router.post("/{task_id}/disable")
async def disable_task(task_id: int):
    """禁用任务"""
    db = Depends(get_db)
    service = TaskService(db)
    task = service.disable_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"task": task, "message": "任务已禁用"}
@router.post("/execute")
async def execute_command(command_data: dict):
    """直接执行命令（临时任务）"""
    from app.db.engine import SessionLocal
    
    db = SessionLocal()
    service = TaskService(db)
    
    result = await service.execute_command(
        name=command_data.get('name', '临时命令'),
        command=command_data.get('command', ''),
        hosts=command_data.get('hosts', ''),
        task_type=command_data.get('task_type', 'command'),
        timeout_seconds=command_data.get('timeout_seconds', 300),
        max_retries=command_data.get('max_retries', 1),
        retry_delay_seconds=command_data.get('retry_delay_seconds', 60),
        ssh_port=command_data.get('ssh_port', 22)
    )
    
    return {
        "success": result.get('success', False),
        "output": result.get('output'),
        "task": result.get('task'),
        "error": result.get('error')
    }
