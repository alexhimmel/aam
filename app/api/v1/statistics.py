"""
任务统计 API 路由
提供任务概览、按类型/主机/时间维度的统计
"""

from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.engine import get_db
from app.db.models import Task
from app.core.statistics import TaskStatistics
from app.dependencies import get_db
import json

router = APIRouter(prefix="/tasks/statistics", tags=["统计报表"])


@router.get("/overview", response_model=dict, summary="任务概览")
async def get_overview():
    """
    获取任务概览统计
    
    Returns:
        - total: 总任务数
        - success: 成功数
        - failed: 失败数
        - success_rate: 成功率
    """
    db = get_db()
    stats = TaskStatistics(db)
    return stats.get_task_overview()


@router.get("/type", response_model=dict, summary="按任务类型统计")
async def get_type_stats():
    """
    获取按任务类型分类的统计
    
    Returns:
        按 task_type 分类的统计，包含每个类型的任务数和成功数
    """
    db = get_db()
    stats = TaskStatistics(db)
    return stats.get_task_type_stats()


@router.get("/hosts/top/{top_n:int}", response_model=list, summary="主机统计")
async def get_host_stats(top_n: int = 10):
    """
    获取按主机分类的前 N 个统计
    
    Args:
        top_n: 返回前 N 个主机
    """
    db = get_db()
    stats = TaskStatistics(db)
    return stats.get_host_stats(top_n)


@router.get("/time/{days:int}", response_model=dict, summary="时间统计")
async def get_time_stats(days: int = 7):
    """
    获取时间维度的统计
    
    Args:
        days: 统计的天数
    """
    db = get_db()
    stats = TaskStatistics(db)
    return stats.get_time_stats(days)


@router.get("/duration/top/{top_n:int}", response_model=list, summary="耗时最长的任务")
async def get_duration_stats(top_n: int = 10):
    """
    获取耗时最长的前 N 个任务
    
    Args:
        top_n: 返回前 N 个任务
    """
    db = get_db()
    stats = TaskStatistics(db)
    return stats.get_task_duration_stats(top_n)


@router.get("/errors", response_model=dict, summary="错误分析")
async def get_error_analysis():
    """
    获取错误分析
    
    Returns:
        错误类型统计
    """
    db = get_db()
    stats = TaskStatistics(db)
    return stats.get_error_analysis()


@router.get("/{task_id}", response_model=dict, summary="任务详情")
async def get_task_details(task_id: int):
    """
    获取任务的详细信息
    
    Args:
        task_id: 任务 ID
    """
    db = get_db()
    stats = TaskStatistics(db)
    return await stats.get_task_details(task_id)


@router.get("/json", response_model=dict, summary="所有统计（JSON 格式）")
async def get_all_stats_json():
    """
    获取所有统计信息（JSON 格式）
    
    Returns:
        包含概览、类型、主机、时间、耗时、错误分析的完整统计
    """
    db = get_db()
    stats = TaskStatistics(db)
    
    return {
        "overview": stats.get_task_overview(),
        "type": stats.get_task_type_stats(),
        "hosts": stats.get_host_stats(),
        "time": stats.get_time_stats(7),
        "duration": stats.get_task_duration_stats(10),
        "errors": stats.get_error_analysis()
    }
