"""
执行记录 API
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
from app.db.models import Execution
from app.db.engine import get_db
from app.services.execution_service import ExecutionService

router = APIRouter(prefix="/executions", tags=["执行记录"])

@router.get("/")
async def list_executions(
    task_id: int = None,
    status: str = None,
    limit: int = 50,
    offset: int = 0
):
    """列出执行记录"""
    db = Depends(get_db)
    service = ExecutionService(db)
    executions = service.list_executions(
        task_id=task_id,
        status=status,
        limit=limit,
        offset=offset
    )
    return {"executions": executions, "total": len(executions)}

@router.get("/{execution_id}")
async def get_execution(execution_id: int):
    """获取执行记录详情"""
    db = Depends(get_db)
    service = ExecutionService(db)
    execution = service.get_execution(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    return {"execution": execution}

@router.post("/{execution_id}/retry")
async def retry_execution(execution_id: int):
    """重试执行"""
    db = Depends(get_db)
    service = ExecutionService(db)
    result = service.retry_execution(execution_id)
    if not result:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    return {"execution": result, "message": "重试已提交"}
