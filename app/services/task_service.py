"""
任务管理服务
"""

from sqlalchemy.orm import Session
from typing import Optional, List
from app.db.models import Task
import time
import asyncio

class TaskService:
    """任务管理业务逻辑"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def list_tasks(self, enabled: Optional[bool] = None) -> List[dict]:
        """列出任务"""
        query = self.db.query(Task)
        
        if enabled is not None:
            query = query.filter(Task.enabled == enabled)
        
        tasks = query.all()
        return [t.__dict__ for t in tasks]
    
    def get_task(self, task_id: int) -> Optional[dict]:
        """获取任务"""
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return None
        return task.__dict__
    
    def create_task(self, task_data: dict) -> Task:
        """创建任务"""
        task = Task(**task_data)
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task.__dict__
    
    def update_task(self, task_id: int, task_data: dict) -> Optional[dict]:
        """更新任务"""
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return None
        
        # 更新字段
        for key, value in task_data.items():
            if hasattr(task, key):
                setattr(task, key, value)
        
        self.db.commit()
        self.db.refresh(task)
        return task.__dict__
    
    def delete_task(self, task_id: int) -> bool:
        """删除任务"""
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return False
        
        self.db.delete(task)
        self.db.commit()
        return True
    
    def enable_task(self, task_id: int) -> Optional[dict]:
        """启用任务"""
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return None
        
        task.enabled = True
        self.db.commit()
        self.db.refresh(task)
        return task.__dict__
    
    def disable_task(self, task_id: int) -> Optional[dict]:
        """禁用任务"""
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return None
        
        task.enabled = False
        self.db.commit()
        self.db.refresh(task)
        return task.__dict__
    
    async def execute_command(
        self,
        name: str,
        command: str,
        hosts: str,
        task_type: str = 'command',
        timeout_seconds: int = 300,
        max_retries: int = 1,
        retry_delay_seconds: int = 60,
        ssh_port: int = 22,
        username: str = 'root',
        password: Optional[str] = None,
        key_file: Optional[str] = None
    ) -> dict:
        """直接执行命令（临时任务）- 异步版本"""
        from datetime import datetime
        import time

        # 解析 hosts 列表
        host_list = [h.strip() for h in hosts.split(',') if h.strip()]
        if not host_list:
            return {
                'success': False,
                'error': '没有指定目标主机'
            }

        all_output = []

        for host in host_list:
            host_output = []
            for attempt in range(max_retries):
                try:
                    # 连接主机 - 使用 get_connection 方法并传递认证配置
                    from app.core.ssh import SSHConnectionPool, SSHConfig
                    pool = SSHConnectionPool()
                    config = SSHConfig(
                        host=host,
                        port=ssh_port,
                        username=username,
                        password=password,
                        key_file=key_file,
                        timeout=10
                    )
                    # 修复：使用正确的 async 方法调用
                    client = await pool.get_connection(host, config=config)

                    # 执行命令（使用 execute 方法）
                    exec_result = await pool.execute(host, command, config=config, timeout=timeout_seconds)
                    
                    if exec_result.get('status') == 'success':
                        stdout = exec_result.get('stdout', '')
                        host_output.append(f"=== {host} ===\n")
                        host_output.append(stdout)
                        host_output.append(f"\n")
                        all_output.extend(host_output)
                        
                        # 创建任务记录
                        task = Task(
                            name=name,
                            command=command,
                            target_hosts=hosts,
                            status='completed',
                            task_type=task_type,
                            output='\n'.join(host_output),
                            error=None,
                            enabled=False,
                            created_at=datetime.now().isoformat()
                        )
                        self.db.add(task)
                        self.db.commit()
                        return {
                            'success': True,
                            'output': all_output,
                            'task': task.__dict__
                        }
                    else:
                        host_output.append(f"执行失败：{exec_result.get('error', '')}\n")
                        
                except Exception as e:
                    host_output.append(f"连接失败：{str(e)}\n")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay_seconds)
                    else:
                        break
            
            all_output.extend(host_output)
        
        # 创建失败任务记录
        task = Task(
            name=name,
            command=command,
            target_hosts=hosts,
            status='failed',
            task_type=task_type,
            output='\n'.join(host_output) if host_output else '',
            error='\n'.join(host_output) if host_output else '执行失败',
            enabled=False,
            created_at=datetime.now().isoformat()
        )
        self.db.add(task)
        self.db.commit()
        return {
            'success': False,
            'output': all_output,
            'task': task.__dict__,
            'error': '命令执行失败'
        }
