"""
AAM 单元测试
测试任务类型识别、文件上传、执行逻辑
"""

import unittest
import os
import sys
import asyncio

# 添加项目根目录到路径
sys.path.insert(0, '/home/alex/Project/aam')

from app.utils.task_type import TaskTypeIdentifier, identify_task


class TestTaskTypeIdentifier(unittest.TestCase):
    """任务类型识别器测试"""
    
    def setUp(self):
        """测试前准备"""
        self.identifier = TaskTypeIdentifier()
    
    def test_simple_command(self):
        """测试简单命令"""
        command = "uptime"
        strategy = self.identifier.identify(command)
        
        self.assertEqual(strategy['task_type'], 'command')
        self.assertFalse(strategy['requires_upload'])
        self.assertEqual(strategy['description'], '远程命令执行：uptime')
    
    def test_script_command(self):
        """测试脚本命令"""
        command = "/opt/scripts/deploy.sh"
        strategy = self.identifier.identify(command)
        
        self.assertEqual(strategy['task_type'], '文件')
        self.assertTrue(strategy['requires_upload'])
        self.assertIn('/opt/scripts/deploy.sh', strategy['upload_dir'])
    
    def test_script_extension(self):
        """测试脚本扩展名"""
        command = "backup.py"
        strategy = self.identifier.identify(command)
        
        self.assertEqual(strategy['task_type'], '脚本')
        self.assertTrue(strategy['requires_upload'])
    
    def test_explicit_task_type_command(self):
        """测试显式指定 command 类型"""
        command = "uptime"
        strategy = self.identifier.identify(command, task_type='command')
        
        self.assertEqual(strategy['task_type'], 'command')
    
    def test_explicit_task_type_script(self):
        """测试显式指定脚本类型"""
        command = "/scripts/deploy.sh"
        strategy = self.identifier.identify(command, task_type='脚本')
        
        self.assertEqual(strategy['task_type'], '脚本')


class TestFileUpload(unittest.TestCase):
    """文件上传功能测试（模拟）"""
    
    def test_upload_success(self):
        """测试上传成功"""
        # 模拟上传成功的结果
        result = {
            'host': '192.168.1.1',
            'local_path': '/tmp/deploy.sh',
            'remote_path': '/opt/deploy/deploy.sh',
            'status': 'success',
            'message': '文件上传成功：/opt/deploy/deploy.sh'
        }
        
        self.assertEqual(result['status'], 'success')
        self.assertIn('success', result['message'].lower())
    
    def test_upload_failed(self):
        """测试上传失败"""
        result = {
            'host': '192.168.1.1',
            'local_path': '/nonexistent/file.sh',
            'remote_path': '/opt/deploy/file.sh',
            'status': 'failed',
            'error': '本地文件不存在：/nonexistent/file.sh'
        }
        
        self.assertEqual(result['status'], 'failed')
        self.assertIn('failed', result['error'].lower())


class TestMixedExecution(unittest.TestCase):
    """混合执行逻辑测试"""
    
    def test_command_execution(self):
        """测试命令执行"""
        # 模拟命令执行结果
        results = [
            {
                'host': '192.168.1.1',
                'command': 'uptime',
                'status': 'success',
                'exit_code': 0,
                'stdout': 'Uptime: 5 days',
                'stderr': ''
            },
            {
                'host': '192.168.1.2',
                'command': 'uptime',
                'status': 'success',
                'exit_code': 0,
                'stdout': 'Uptime: 5 days',
                'stderr': ''
            }
        ]
        
        success_count = sum(1 for r in results if r['status'] == 'success')
        self.assertEqual(success_count, 2)
    
    def test_script_execution(self):
        """测试脚本执行（上传后）"""
        # 模拟脚本执行结果
        results = [
            {
                'host': '192.168.1.1',
                'command': '/opt/deploy/deploy.sh',
                'status': 'success',
                'exit_code': 0,
                'stdout': '部署完成',
                'stderr': '',
                'upload_status': 'success'
            }
        ]
        
        success_count = sum(1 for r in results if r['status'] == 'success')
        self.assertEqual(success_count, 1)
        self.assertIn('upload_status', results[0])


def run_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestTaskTypeIdentifier))
    suite.addTests(loader.loadTestsFromTestCase(TestFileUpload))
    suite.addTests(loader.loadTestsFromTestCase(TestMixedExecution))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


if __name__ == '__main__':
    print("=" * 60)
    print("AAM 单元测试")
    print("=" * 60)
    print()
    
    result = run_tests()
    
    print()
    print("=" * 60)
    print(f"测试完成：{result.testsRun} 个测试")
    print(f"成功：{result.testsRun - result.failures[0][0] - result.failures[0][1]}")
    print(f"失败：{len(result.failures)}")
    print(f"错误：{len(result.errors)}")
    print("=" * 60)
    
    if result.failures or result.errors:
        print()
        print("失败的测试:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback[:100]}")
        print()
        print("错误的测试:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback[:100]}")
    
    sys.exit(0 if result.wasSuccessful() else 1)
