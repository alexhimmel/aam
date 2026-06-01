"""
SSH 客户端模块
负责管理 SSH 连接和执行远程命令
"""

import asyncio
import paramiko
from typing import Dict, Optional, List
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class SSHConfig:
    """SSH 配置类"""
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
    - 异步执行（使用 asyncio.to_thread 包装 Paramiko）
    - 认证配置支持（用户名/密钥/密码）
    """
    
    def __init__(self, max_connections: int = 20):
        self.pool: Dict[str, paramiko.SSHClient] = {}
        self.max_connections = max_connections
        self.lock = asyncio.Lock()
        self._host_locks: Dict[str, asyncio.Lock] = {}
    
    async def _create_connection(self, host: str, config: Optional[SSHConfig] = None) -> paramiko.SSHClient:
        """创建 SSH 连接"""
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        connect_kwargs = {
            'hostname': host,
            'port': config.port if config else 22,
            'username': config.username if config else 'root',
            'timeout': config.timeout if config else 30,
        }
        
        if config and config.key_file:
            connect_kwargs['key_filename'] = config.key_file
        elif config and config.password:
            connect_kwargs['password'] = config.password
        
        await asyncio.to_thread(client.connect, **connect_kwargs)
        
        logger.info(f"创建 SSH 连接：{host}")
        return client
    
    async def _is_connection_alive(self, client: paramiko.SSHClient) -> bool:
        """检查连接是否存活"""
        try:
            transport = await asyncio.to_thread(client.get_transport)
            if transport is None:
                return False
            # 尝试发送 EOF 来检查连接是否存活
            await asyncio.to_thread(transport.send_eof)
            return True
        except Exception:
            return False
    
    async def _read_outputs_inner(self, stdout, stderr, timeout: int = 300):
        """读取 stdout 和 stderr（同步包装）"""
        stdout_content = stdout.read().decode('utf-8', errors='ignore')
        stderr_content = stderr.read().decode('utf-8', errors='ignore')
        return stdout_content, stderr_content
    
    async def get_connection(self, host: str, config: Optional[SSHConfig] = None) -> paramiko.SSHClient:
        """
        获取或创建 SSH 连接（连接复用）
        
        Args:
            host: 目标主机地址
            config: SSH 配置（可选）
            
        Returns:
            SSH 客户端对象
        """
        async with self.lock:
            if host not in self.pool:
                logger.info(f"创建 SSH 连接：{host}")
                client = await self._create_connection(host, config)
                self.pool[host] = client
            else:
                # 检查连接是否存活
                if not await self._is_connection_alive(self.pool[host]):
                    logger.info(f"SSH 连接失效，重建：{host}")
                    self.pool[host] = await self._create_connection(host, config)
            
            return self.pool[host]
    
    async def execute(
        self, 
        host: str, 
        command: str, 
        config: Optional[SSHConfig] = None,
        timeout: int = 300
    ) -> dict:
        """
        执行远程命令（异步 + 认证支持）
        
        Args:
            host: 目标主机
            command: 要执行的命令
            config: SSH 配置（可选）
            timeout: 命令执行超时时间 (秒)
            
        Returns:
            执行结果字典
        """
        try:
            # 获取连接（异步）
            client = await self.get_connection(host, config)
            
            # 执行命令（使用 asyncio.to_thread 包装同步调用）
            stdin, stdout, stderr = await asyncio.to_thread(
                client.exec_command, command
            )
            
            # 等待命令执行（带超时）
            try:
                stdout_content, stderr_content = await asyncio.wait_for(
                    self._read_outputs_inner(stdout, stderr),
                    timeout=timeout - 5
                )
            except asyncio.TimeoutError:
                logger.warning(f"命令执行超时：{host} {command}")
                await asyncio.to_thread(stdout.channel.send_eof)
                exit_code = await asyncio.to_thread(stdout.channel.recv_exit_status)
                return {
                    'host': host,
                    'command': command,
                    'status': 'timeout',
                    'exit_code': exit_code,
                    'stdout': '',
                    'stderr': f'命令执行超时'
                }
            
            exit_code = await asyncio.to_thread(stdout.channel.recv_exit_status)
            
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
            for host in list(self.pool.keys()):
                try:
                    self.pool[host].close()
                    logger.info(f"关闭 SSH 连接：{host}")
                except Exception as e:
                    logger.error(f"关闭连接失败 {host}: {e}")
                del self.pool[host]
    
    async def sftp_connect(self, host: str, config: Optional[SSHConfig] = None):
        """
        获取 SFTP 连接
        
        Args:
            host: 目标主机
            config: SSH 配置（可选）
            
        Returns:
            SFTP 客户端对象
        """
        client = await self.get_connection(host, config)
        sftp = await asyncio.to_thread(client.open_sftp)
        logger.info(f"创建 SFTP 连接：{host}")
        return sftp
    
    async def sftp_execute_batch(self, tasks: List[tuple]) -> List[dict]:
        """
        批量 SFTP 操作（上传/下载）
        
        Args:
            tasks: 任务列表 [(host, local_path, remote_path), ...]
            
        Returns:
            执行结果列表
        """
        async def sftp_single(host: str, local_path: str, remote_path: str) -> dict:
            try:
                sftp = await self.sftp_connect(host)
                
                # 上传文件
                await asyncio.to_thread(sftp.put, local_path, remote_path, dry_run=False)
                await asyncio.to_thread(sftp.close)
                
                return {
                    'host': host,
                    'local_path': local_path,
                    'remote_path': remote_path,
                    'status': 'success',
                    'exit_code': 0
                }
            except Exception as e:
                logger.error(f"SFTP 操作失败 {host}: {e}")
                return {
                    'host': host,
                    'local_path': local_path,
                    'remote_path': remote_path,
                    'status': 'failed',
                    'error': str(e)
                }
        
        # 并发执行（限制最大并发数）
        semaphore = asyncio.Semaphore(self.max_connections)
        
        async def sftp_with_semaphore(host: str, local_path: str, remote_path: str) -> dict:
            async with semaphore:
                return await sftp_single(host, local_path, remote_path)
        
        results = await asyncio.gather(*[
            sftp_with_semaphore(host, local, remote) for host, local, remote in tasks
        ])
        
        return results
