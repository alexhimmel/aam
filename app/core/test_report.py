"""
测试报告 API 模块
生成和提供测试报告（JSON + HTML）
"""

import json
from typing import Dict, List, Any
from datetime import datetime
from sqlalchemy.orm import Session
from app.db.models import Task
from app.db.engine import get_db


class TestReportService:
    """测试报告服务"""
    
    def __init__(self, db: Session):
        """
        初始化测试报告服务
        
        Args:
            db: 数据库会话
        """
        self.db = db
    
    def get_test_results(self, test_file: str = 'all') -> Dict[str, Any]:
        """
        获取测试结果
        
        Args:
            test_file: 测试文件名 ('all' 或具体文件)
            
        Returns:
            测试结果字典
        """
        try:
            import subprocess
            import sys
            
            # 运行测试
            cmd = [sys.executable, '-m', 'pytest', 
                   'tests/test_task_type.py',
                   'tests/test_notification.py',
                   '-v', '--tb=short', '--json-report=reports/tests.json']
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # 解析输出
            output = result.stdout + result.stderr
            
            # 统计结果
            passed = output.count('... ok')
            failed = len([line for line in output.split('\n') if 'FAILED' in line])
            errors = len([line for line in output.split('\n') if 'ERROR' in line])
            total = passed + failed + errors
            duration = result.stdout.split('in ')[1].split(' ')[0] if 'in ' in result.stdout else 'N/A'
            
            return {
                'timestamp': datetime.now().isoformat(),
                'passed': passed,
                'failed': failed,
                'errors': errors,
                'total': total,
                'success_rate': round(passed / total * 100, 2) if total > 0 else 0,
                'duration': duration,
                'output': output
            }
            
        except Exception as e:
            return {
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'error_traceback': result.stderr
            }
    
    def get_html_report(self, test_file: str = 'all') -> str:
        """
        生成 HTML 测试报告
        
        Args:
            test_file: 测试文件名
            
        Returns:
            HTML 报告字符串
        """
        results = self.get_test_results(test_file)
        
        if 'error' in results:
            return self._generate_error_report(results['error'])
        
        return self._generate_html_report(results)
    
    def _generate_html_report(self, results: Dict[str, Any]) -> str:
        """生成 HTML 报告"""
        
        # 解析输出
        output_lines = results['output'].split('\n')
        tests = []
        
        for line in output_lines:
            if '...' in line:
                parts = line.split('...')
                test_name = parts[0].strip()
                status = 'ok' if 'ok' in parts else ('FAILED' if 'FAILED' in parts else 'ERROR')
                tests.append({
                    'name': test_name,
                    'status': status
                })
        
        # 构建 HTML
        html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>测试报告 - AAM</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .status-ok {{ color: #10b981; }}
        .status-failed {{ color: #ef4444; }}
        .status-error {{ color: #f59e0b; }}
    </style>
</head>
<body class="bg-gray-100">
    <div class="container mx-auto px-4 py-8">
        <!-- 导航栏 -->
        <nav class="bg-white shadow mb-8">
            <div class="container mx-auto px-4">
                <div class="flex justify-between items-center">
                    <h1 class="text-2xl font-bold text-gray-800">
                        🧪 测试报告 - AAM
                    </h1>
                    <div class="space-x-4">
                        <a href="/tests/results" class="text-blue-600 hover:text-blue-800">刷新报告</a>
                        <a href="/" class="text-blue-600 hover:text-blue-800">返回首页</a>
                    </div>
                </div>
            </div>
        </nav>
        
        <!-- 概览卡片 -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
            <div class="bg-white p-6 rounded-lg shadow">
                <div class="text-3xl font-bold text-green-600">{results['passed']}</div>
                <div class="text-gray-600">通过</div>
            </div>
            <div class="bg-white p-6 rounded-lg shadow">
                <div class="text-3xl font-bold text-red-600">{results['failed']}</div>
                <div class="text-gray-600">失败</div>
            </div>
            <div class="bg-white p-6 rounded-lg shadow">
                <div class="text-3xl font-bold text-yellow-600">{results['errors']}</div>
                <div class="text-gray-600">错误</div>
            </div>
            <div class="bg-white p-6 rounded-lg shadow">
                <div class="text-3xl font-bold text-blue-600">{results['success_rate']}%</div>
                <div class="text-gray-600">通过率</div>
            </div>
        </div>
        
        <div class="bg-white p-6 rounded-lg shadow mb-8">
            <h2 class="text-xl font-semibold mb-4">📊 测试结果</h2>
            <div class="space-y-2">
                {"".join(self._build_test_row(test) for test in tests)}
            </div>
        </div>
        
        <div class="bg-white p-6 rounded-lg shadow mb-8">
            <h2 class="text-xl font-semibold mb-4">⏱️ 执行时间</h2>
            <p class="text-gray-700">{results['duration']}</p>
        </div>
        
        <div class="bg-white p-6 rounded-lg shadow mb-8">
            <h2 class="text-xl font-semibold mb-4">📝 详细输出</h2>
            <pre class="bg-gray-100 p-4 rounded text-sm overflow-auto max-h-96">
{results['output']}
            </pre>
        </div>
        
        <div class="bg-blue-50 p-6 rounded-lg shadow">
            <h3 class="font-semibold mb-2">🔄 重新测试</h3>
            <a href="/tests/results" class="inline-block bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
                刷新测试结果
            </a>
        </div>
    </div>
</body>
</html>'''
        
        return html
    
    def _build_test_row(self, test: Dict[str, str]) -> str:
        """构建测试用例行"""
        status_class = f'status-{test["status"].lower()}'
        status_icon = {'ok': '✅', 'FAILED': '❌', 'ERROR': '⚠️'}.get(test['status'], '❓')
        return f'''
        <div class="flex items-center justify-between p-3 rounded hover:bg-gray-50">
            <span class="font-mono text-sm">{status_icon} {test['name']}</span>
            <span class="text-sm {status_class}">{test['status']}</span>
        </div>'''
    
    def _generate_error_report(self, error: str) -> str:
        """生成错误报告"""
        return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>测试报告错误 - AAM</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100">
    <div class="container mx-auto px-4 py-8">
        <nav class="bg-white shadow mb-8">
            <div class="container mx-auto px-4">
                <div class="flex justify-between items-center">
                    <h1 class="text-2xl font-bold text-gray-800">
                        🧪 测试报告错误
                    </h1>
                    <a href="/" class="text-blue-600 hover:text-blue-800">返回首页</a>
                </div>
            </div>
        </nav>
        
        <div class="bg-red-50 p-6 rounded-lg shadow">
            <h2 class="text-xl font-semibold mb-4 text-red-800">❌ 测试报告生成失败</h2>
            <pre class="bg-red-100 p-4 rounded text-sm overflow-auto">{error}</pre>
        </div>
        
        <div class="bg-white p-6 rounded-lg shadow mt-8">
            <h3 class="font-semibold mb-2">💡 建议</h3>
            <ul class="list-disc list-inside text-gray-700">
                <li>确保 pytest 已安装：pip install pytest</li>
                <li>确保测试文件存在：tests/test_*.py</li>
                <li>检查网络连接（如果测试需要网络）</li>
            </ul>
        </div>
    </div>
</body>
</html>'''
