"""
任务统计报表模块
提供执行成功率、耗时统计等功能
"""

from typing import List, Dict
from sqlalchemy.orm import Session
from app.db.models import Task
from app.db.engine import get_db
from sqlalchemy import func, extract


class TaskStatistics:
    """任务统计服务"""
    
    def __init__(self, db: Session):
        """
        初始化统计服务

        Args:
            db: 数据库会话（通过 get_db 注入）
        """
        self.db = db
    
    def get_task_overview(self) -> Dict:
        """
        获取任务概览统计
        
        Returns:
            包含总任务数、成功/失败数的字典
        """
        total = Task.query.count()
        success_count = Task.query.filter(Task.status == 'success').count()
        failed_count = Task.query.filter(Task.status == 'failed').count()
        
        return {
            'total': total,
            'success': success_count,
            'failed': failed_count,
            'success_rate': round(success_count / total * 100, 2) if total > 0 else 0
        }
    
    def get_task_type_stats(self) -> Dict:
        """
        获取按任务类型分类的统计
        
        Returns:
            按 task_type 分类的统计字典
        """
        stats = Task.query.with_entities(
            Task.task_type.label('type'),
            func.count(Task.id).label('count'),
            func.sum(func.cast(Task.status == 'success', func.integer())).label('success')
        ).group_by(Task.task_type).all()
        
        result = {
            'command': {'count': 0, 'success': 0},
            '脚本': {'count': 0, 'success': 0},
            '文件': {'count': 0, 'success': 0}
        }
        
        for row in stats:
            result[row.type]['count'] = row.count
            result[row.type]['success'] = row.success
        
        return result
    
    def get_host_stats(self, top_n: int = 10) -> List[Dict]:
        """
        获取按主机分类的前 N 个统计
        
        Args:
            top_n: 返回前 N 个主机
            
        Returns:
            主机统计列表
        """
        stats = Task.query.with_entities(
            Task.host.label('host'),
            func.count(Task.id).label('total'),
            func.sum(func.cast(Task.status == 'success', func.integer())).label('success'),
            func.min(Task.created_at).label('first_run'),
            func.max(Task.created_at).label('last_run')
        ).group_by(Task.host).order_by(func.desc(func.count(Task.id))).limit(top_n).all()
        
        return [{
            'host': row.host,
            'total': row.total,
            'success': row.success,
            'success_rate': round(row.success / row.total * 100, 2) if row.total > 0 else 0,
            'first_run': row.first_run,
            'last_run': row.last_run
        } for row in stats]
    
    def get_time_stats(self, days: int = 7) -> Dict:
        """
        获取时间维度的统计
        
        Args:
            days: 统计的天数
            
        Returns:
            按天统计的字典
        """
        from sqlalchemy import text
        
        query = text("""
            SELECT 
                DATE(created_at) as date,
                COUNT(*) as total,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success,
                AVG(EXTRACT(EPOCH FROM (completed_at - created_at)) / 60) as avg_duration_min
            FROM tasks
            WHERE created_at >= DATE('now', '-' || :days || ' days')
            GROUP BY DATE(created_at)
            ORDER BY date
        """)
        
        stats = self.db.execute(query, {'days': days}).fetchall()
        
        return {
            row.date: {
                'total': row.total,
                'success': row.success,
                'success_rate': round(row.success / row.total * 100, 2) if row.total > 0 else 0,
                'avg_duration_min': round(row.avg_duration_min, 2)
            } for row in stats
        }
    
    def get_task_duration_stats(self, top_n: int = 10) -> List[Dict]:
        """
        获取耗时最长的前 N 个任务
        
        Args:
            top_n: 返回前 N 个任务
            
        Returns:
            任务耗时统计列表
        """
        stats = Task.query.with_entities(
            Task.id.label('task_id'),
            Task.task_name.label('task_name'),
            func.round(func.extract(epoch, (Task.created_at - Task.completed_at)) / 60, 2).label('duration_min'),
            Task.status,
            Task.host
        ).filter(Task.status == 'success').order_by(
            func.desc(func.extract(epoch, (Task.created_at - Task.completed_at)))
        ).limit(top_n).all()
        
        return [{
            'task_id': row.task_id,
            'task_name': row.task_name,
            'duration_min': row.duration_min,
            'status': row.status,
            'host': row.host
        } for row in stats]
    
    def get_error_analysis(self) -> Dict:
        """
        获取错误分析
        
        Returns:
            错误类型统计
        """
        stats = Task.query.with_entities(
            func.substr(Task.stderr, 1, 20).label('error_prefix'),
            func.count(Task.id).label('count')
        ).filter(Task.status == 'failed').group_by(
            func.substr(Task.stderr, 1, 20)
        ).order_by(func.desc(func.count(Task.id))).limit(10).all()
        
        return {
            row.error_prefix: row.count 
            for row in stats
        }
    
    async def get_task_details(self, task_id: int) -> Dict:
        """
        获取任务的详细信息
        
        Args:
            task_id: 任务 ID
            
        Returns:
            任务详细信息
        """
        task = Task.query.filter(Task.id == task_id).first()
        
        if not task:
            return None
        
        # 计算耗时（秒）
        if task.completed_at:
            duration = (task.created_at - task.completed_at).total_seconds()
        else:
            duration = None
        
        return {
            'id': task.id,
            'task_name': task.task_name,
            'task_type': task.task_type,
            'command': task.command,
            'host': task.host,
            'status': task.status,
            'exit_code': task.exit_code,
            'stdout': task.stdout[:500] + '...' if len(task.stdout) > 500 else task.stdout,
            'stderr': task.stderr[:500] + '...' if len(task.stderr) > 500 else task.stderr,
            'created_at': task.created_at.isoformat() if task.created_at else None,
            'completed_at': task.completed_at.isoformat() if task.completed_at else None,
            'duration_seconds': duration,
            'upload_dir': task.upload_dir,
            'working_dir': task.working_dir
        }
