"""
SSH 客户端模块
负责管理 SSH 连接和执行远程命令
"""

import asyncio
import paramiko
from typing import Dict, Optional, List
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class SSHConfig:
    """SSH 连接配置"""
    host: str
    port: int = 22
    username: str = 'root'
    key_file: Optional[str] = None
    password: Optional[str] = None
    timeout: int = 30


class SSHConnectionPool:
    """
    SSH 连接池 - 管理多台设备的连接
    
    特性：
    - 连接复用（避免频繁建立连接）
    - 连接保活（自动检测失效连接）
    - 并发控制（支持 20 台设备并发）
    - 异常处理（自动重试、失败隔离）
    """
    
    def __init__(self, max_connections: int = 20, key_file: Optional[str] = None):
        """
        初始化 SSH 连接池
        
        Args:
            max_connections: 最大并发连接数（默认 20）
            key_file: SSH 私钥文件路径（可选）
        """
        self.max_connections = max_connections
        self.key_file = key_file
        self.pool: Dict[str, paramiko.SSHClient] = {}
        self.lock = asyncio.Lock()
        self._host_locks: Dict[str, asyncio.Lock] = {}
    
    async def get_connection(self, host: str) -> paramiko.SSHClient:
        """
        获取或创建 SSH 连接（连接复用）
        
        Args:
            host: 目标主机地址
            
        Returns:
            SSH 客户端对象
        """
        async with self._get_lock(host):
            if host not in self.pool:
                logger.info(f"创建 SSH 连接：{host}")
                client = self._create_connection(host)
                self.pool[host] = client
            else:
                # 检查连接是否存活
                if not await self._is_connection_alive(client):
                    logger.info(f"SSH 连接失效，重建：{host}")
                    self.pool[host] = self._create_connection(host)
            
            return self.pool[host]
    
    async def execute(self, host: str, command: str) -> dict:
        """
        执行远程命令
        
        Args:
            host: 目标主机
            command: 要执行的命令
            
        Returns:
            执行结果字典
        """
        try:
            async with self.get_connection(host) as client:
                stdin, stdout, stderr = client.exec_command(command)
                
                # 等待命令执行（带超时）
                try:
                    await asyncio.wait_for(
                        asyncio.gather(
                            asyncio.create_task(self._read_stdout(stdout)),
                            asyncio.create_task(self._read_stderr(stderr)),
                        ),
                        timeout=295  # 比 command timeout 少 5 秒
                    )
                except asyncio.TimeoutError:
                    logger.warning(f"命令执行超时：{host} {command}")
                    stdout.channel.send_eof()
                    exit_code = stdout.channel.recv_exit_status()
                    return {
                        'host': host,
                        'command': command,
                        'status': 'timeout',
                        'exit_code': exit_code,
                        'stdout': '',
                        'stderr': f'命令执行超时'
                    }
                
                exit_code = stdout.channel.recv_exit_status()
                
                stdout_content = stdout.read().decode('utf-8', errors='ignore').strip()
                stderr_content = stderr.read().decode('utf-8', errors='ignore').strip()
                
                return {
                    'host': host,
                    'command': command,
                    'status': 'success' if exit_code == 0 else 'failed',
                    'exit_code': exit_code,
                    'stdout': stdout_content,
                    'stderr': stderr_content
                }
                
        except paramiko.SSHException as e:
            logger.error(f"SSH 连接错误 {host}: {e}")
            return {
                'host': host,
                'command': command,
                'status': 'failed',
                'error': f"SSH 连接错误：{str(e)}"
            }
        except Exception as e:
            logger.error(f"执行命令错误 {host}: {e}")
            return {
                'host': host,
                'command': command,
                'status': 'failed',
                'error': str(e)
            }
    
    async def execute_batch(self, tasks: List[tuple]) -> List[dict]:
        """
        批量执行命令（并发控制）
        
        Args:
            tasks: 任务列表 [(host, command), ...]
            
        Returns:
            执行结果列表
        """
        async def execute_single(host: str, command: str) -> dict:
            return await self.execute(host, command)
        
        # 并发执行（限制最大并发数）
        semaphore = asyncio.Semaphore(self.max_connections)
        
        async def execute_with_semaphore(host: str, command: str) -> dict:
            async with semaphore:
                return await execute_single(host, command)
        
        tasks = [(host, cmd) for host, cmd in tasks]
        results = await asyncio.gather(*[
            execute_with_semaphore(host, cmd) for host, cmd in tasks
        ])
        
        return results
    
    async def close_connection(self, host: str):
        """关闭特定主机的连接"""
        async with self.lock:
            if host in self.pool:
                try:
                    self.pool[host].close()
                    logger.info(f"关闭 SSH 连接：{host}")
                except Exception as e:
                    logger.error(f"关闭连接失败 {host}: {e}")
                del self.pool[host]
    
    async def close_all(self):
        """关闭所有连接"""
        async with self.lock:
            for host, client in list(self.pool.items()):
                try:
                    client.close()
                except:
                    pass
            self.pool.clear()
            logger.info("所有 SSH 连接已关闭")
    
    def _create_connection(self, host: str) -> paramiko.SSHClient:
        """创建 SSH 连接"""
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # 使用密钥或密码认证
        if self.key_file:
            try:
                client.connect(
                    hostname=host,
                    port=22,
                    username=self.username,
                    key_filename=self.key_file,
                    timeout=30
                )
            except Exception as e:
                logger.error(f"密钥认证失败 {host}: {e}")
                raise
        else:
            client.connect(
                hostname=host,
                port=22,
                username=self.username,
                timeout=30
            )
        
        logger.info(f"SSH 连接成功：{host}")
        return client
    
    def _is_connection_alive(self, client: paramiko.SSHClient) -> bool:
        """检查连接是否存活"""
        try:
            client.get_transport().send_eof()
            return True
        except:
            return False
    
    async def _read_stdout(self, stdout) -> str:
        """读取 stdout"""
        return stdout.read().decode('utf-8', errors='ignore')
    
    async def _read_stderr(self, stderr) -> str:
        """读取 stderr"""
        return stderr.read().decode('utf-8', errors='ignore')
    
    async def _get_lock(self, host: str) -> asyncio.Lock:
        """获取主机级别的锁（避免同一主机并发冲突）"""
        if host not in self._host_locks:
            self._host_locks[host] = asyncio.Lock()
        return self._host_locks[host]


class SFTPConnectionPool:
    """
    SFTP 连接池 - 管理 SFTP 上传
    """
    
    def __init__(self, ssh_pool: SSHConnectionPool):
        """
        初始化 SFTP 连接池
        
        Args:
            ssh_pool: SSH 连接池实例
        """
        self.ssh_pool = ssh_pool
        self.sftp_pool: Dict[str, paramiko.SFTPClient] = {}
        self.lock = asyncio.Lock()
    
    async def upload_file(self, host: str, local_path: str, remote_path: str) -> dict:
        """
        上传文件到目标机器
        
        Args:
            host: 目标主机
            local_path: 本地文件路径
            remote_path: 远程文件路径
            
        Returns:
            上传结果字典
        """
        try:
            async with self.get_connection(host) as sftp:
                # 确保远程目录存在
                remote_dir = os.path.dirname(remote_path)
                if remote_dir:
                    try:
                        await sftp.mkdir(remote_dir, create_parents=True)
                    except Exception as e:
                        if "File exists" not in str(e):
                            logger.warning(f"创建远程目录失败 {host} {remote_dir}: {e}")
                
                # 上传文件
                sftp.put(local_path, remote_path)
                
                # 设置执行权限（如果是脚本）
                if remote_path.endswith(('.sh', '.bat', '.cmd', '.ps1')):
                    try:
                        stdin, stdout, stderr = self.ssh_pool.execute(host, f"chmod +x {remote_path}")
                        if stdout['status'] == 'success':
                            logger.info(f"设置执行权限成功 {host} {remote_path}")
                    except Exception as e:
                        logger.warning(f"设置执行权限失败 {host} {remote_path}: {e}")
                
                return {
                    'host': host,
                    'local_path': local_path,
                    'remote_path': remote_path,
                    'status': 'success',
                    'message': f"文件上传成功：{remote_path}"
                }
                
        except FileNotFoundError:
            return {
                'host': host,
                'local_path': local_path,
                'remote_path': remote_path,
                'status': 'failed',
                'error': f"本地文件不存在：{local_path}"
            }
        except paramiko.SFTPError as e:
            logger.error(f"SFTP 错误 {host}: {e}")
            return {
                'host': host,
                'local_path': local_path,
                'remote_path': remote_path,
                'status': 'failed',
                'error': f"SFTP 错误：{str(e)}"
            }
        except Exception as e:
            logger.error(f"上传文件错误 {host}: {e}")
            return {
                'host': host,
                'local_path': local_path,
                'remote_path': remote_path,
                'status': 'failed',
                'error': str(e)
            }
    
    async def get_connection(self, host: str) -> paramiko.SFTPClient:
        """
        获取或创建 SFTP 连接（连接复用）
        
        Args:
            host: 目标主机
            
        Returns:
            SFTP 客户端对象
        """
        async with self.lock:
            if host not in self.sftp_pool:
                logger.info(f"创建 SFTP 连接：{host}")
                client = self.ssh_pool.pool[host].open_sftp()
                self.sftp_pool[host] = client
            else:
                # 检查连接是否可用
                try:
                    self.sftp_pool[host].stat('/')
                except Exception:
                    logger.info(f"SFTP 连接失效，重建：{host}")
                    self.sftp_pool[host] = self.ssh_pool.pool[host].open_sftp()
            
            return self.sftp_pool[host]
    
    async def close_all(self):
        """关闭所有 SFTP 连接"""
        async with self.lock:
            for host, sftp in list(self.sftp_pool.items()):
                try:
                    sftp.close()
                except:
                    pass
            self.sftp_pool.clear()
            logger.info("所有 SFTP 连接已关闭")


import os
