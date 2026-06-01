"""
任务执行器模块 - 支持命令、脚本、文件的混合执行
"""

from typing import Callable, List, Optional
import asyncio
import os
from app.core.ssh import SSHConnectionPool
from app.utils.task_type import TaskTypeIdentifier, identify_task
from app.core.notification import NotificationService


class TaskExecutor:
    """任务执行器 - 支持命令、脚本、文件的混合执行"""
    
    def __init__(self, ssh_pool: SSHConnectionPool, notification_service: NotificationService = None):
        """
        初始化任务执行器
        
        Args:
            ssh_pool: SSH 连接池（包含 SFTP 功能）
            notification_service: 通知服务（可选）
        """
        self.ssh_pool = ssh_pool
        self.task_type_identifier = TaskTypeIdentifier()
        self.notification_service = notification_service
    
    async def execute(self, task_id: int, command: str, hosts: list, 
                      task_type: str = 'command', 
                      upload_dir: str = None,
                      working_dir: str = None) -> list:
        """
        执行任务（支持命令、脚本、文件类型）
        
        Args:
            task_id: 任务 ID
            command: 要执行的命令或文件路径
            hosts: 目标主机列表
            task_type: 任务类型（command/脚本/文件）
            upload_dir: 上传目录
            working_dir: 工作目录
            
        Returns:
            执行结果列表
        """
        print(f"开始执行任务 {task_id}: {command}")
        print(f"任务类型：{task_type}")
        print(f"目标主机：{hosts}")
        
        # 识别执行策略
        strategy = self.task_type_identifier.identify(command, task_type)
        
        # 并发执行
        tasks = [(host, command, strategy) for host in hosts]
        results = []
        
        for result in await self.ssh_pool.execute_batch(tasks):
            result['task_id'] = task_id
            results.append(result)
        
        # 统计
        success_count = sum(1 for r in results if r['status'] == 'success')
        failed_count = len(results) - success_count
        
        print(f"执行完成：成功 {success_count}/{len(results)}, 失败 {failed_count}")
        
        # 发送通知
        if self.notification_service:
            # 使用第一个结果作为通知数据（或汇总结果）
            first_result = results[0] if results else {'status': 'unknown'}
            await self.notification_service.send_notification(
                task_id,
                f"任务{task_id}",
                first_result
            )
        
        return results
    
    async def execute_with_upload(self, task_id: int, local_file: str, 
                                  command: str, hosts: list,
                                  upload_dir: str,
                                  working_dir: str = None,
                                  task_type: str = '脚本') -> list:
        """
        执行带上传的任务（先上传文件再执行）
        
        Args:
            task_id: 任务 ID
            local_file: 本地文件路径
            command: 执行命令（可以是文件名或完整路径）
            hosts: 目标主机列表
            upload_dir: 上传目录
            working_dir: 工作目录
            task_type: 任务类型
            
        Returns:
            执行结果列表
        """
        print(f"任务 {task_id} - 开始上传文件")
        print(f"本地文件：{local_file}")
        print(f"上传目录：{upload_dir}")
        
        # 构建上传路径
        remote_path = os.path.join(upload_dir, os.path.basename(local_file))
        
        # 并发上传文件（使用 SSH 连接池的 SFTP 功能）
        upload_tasks = [(host, local_file, remote_path) for host in hosts]
        upload_results = []
        
        for result in await self.ssh_pool.sftp_execute_batch(upload_tasks):
            result['task_id'] = task_id
            upload_results.append(result)
        
        # 检查上传是否全部成功
        upload_failed = sum(1 for r in upload_results if r['status'] == 'failed')
        if upload_failed > 0:
            print(f"文件上传失败：{upload_failed}/{len(upload_results)}")
            return upload_results
        
        print("文件上传成功，开始执行命令...")
        
        # 构建执行命令
        if working_dir:
            # 如果设置了工作目录，使用绝对路径
            exec_path = os.path.join(working_dir, os.path.basename(local_file))
        else:
            exec_path = command
        
        # 执行命令
        exec_tasks = [(host, exec_path, None) for host in hosts]
        results = []
        
        for result in await self.ssh_pool.execute_batch(exec_tasks):
            result['task_id'] = task_id
            result['upload_status'] = 'success'
            results.append(result)
        
        # 统计
        success_count = sum(1 for r in results if r['status'] == 'success')
        failed_count = len(results) - success_count
        
        print(f"执行完成：成功 {success_count}/{len(results)}, 失败 {failed_count}")
        
        # 发送通知
        if self.notification_service:
            # 使用第一个结果作为通知数据（或汇总结果）
            first_result = results[0] if results else {'status': 'unknown'}
            await self.notification_service.send_notification(
                task_id,
                f"任务{task_id}",
                first_result
            )
        
        return results
