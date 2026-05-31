"""
测试报告 API 路由
提供测试结果 JSON 和 HTML 报告
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.engine import get_db
from app.db.models import Task
from app.core.test_report import TestReportService
from app.dependencies import get_db

router = APIRouter(prefix="/tests", tags=["测试报告"])


@router.get("/results", summary="获取测试结果 JSON")
async def get_test_results():
    """
    获取测试结果（JSON 格式）
    
    Returns:
        - timestamp: 测试时间
        - passed: 通过的测试数
        - failed: 失败的测试数
        - errors: 错误数
        - total: 总测试数
        - success_rate: 通过率
        - duration: 执行时间
        - output: 详细输出
    """
    db = get_db()
    service = TestReportService(db)
    return service.get_test_results()


@router.get("/report", summary="获取测试报告 HTML")
async def get_test_report():
    """
    获取测试报告（HTML 格式）
    
    Returns:
        HTML 格式的测试报告
    """
    db = get_db()
    service = TestReportService(db)
    return service.get_html_report()


@router.get("/overview", summary="测试结果概览")
async def get_test_overview():
    """
    获取测试结果概览
    
    Returns:
        测试概览信息（不含详细输出）
    """
    db = get_db()
    service = TestReportService(db)
    
    try:
        import subprocess
        import sys
        
        cmd = [sys.executable, '-m', 'pytest', 
               'tests/test_task_type.py',
               'tests/test_notification.py',
               '-v', '--tb=short', '--no-header', '--color=yes']
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = result.stdout + result.stderr
        
        # 解析
        passed = output.count('... ok')
        failed = len([line for line in output.split('\n') if 'FAILED' in line])
        errors = len([line for line in output.split('\n') if 'ERROR' in line])
        total = passed + failed + errors
        duration_str = 'N/A'
        if 'in ' in result.stdout:
            duration_str = result.stdout.split('in ')[1].split(' ')[0]
        
        return {
            'timestamp': datetime.now().isoformat(),
            'passed': passed,
            'failed': failed,
            'errors': errors,
            'total': total,
            'success_rate': round(passed / total * 100, 2) if total > 0 else 0,
            'duration': duration_str
        }
    except Exception as e:
        return {
            'error': str(e),
            'error_traceback': result.stderr
        }
