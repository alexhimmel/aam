"""
SSH 客户端模块
负责管理 SSH 连接和执行远程命令
"""

import asyncio
import paramiko
from typing import Dict, Optional, List
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name)


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
    - 异步执行（使用 asyncio.to_thread 包装 Paramiko）
    - 认证配置支持（用户名/密钥/密码）
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
    
    async def get_connection(self, host: str, config: Optional[SSHConfig] = None) -> paramiko.SSHClient:
        """
        获取或创建 SSH 连接（连接复用）
        
        Args:
            host: 目标主机地址
            config: SSH 配置（可选）
            
        Returns:
            SSH 客户端对象
        """
        async with self._get_lock(host):
            if host not in self.pool:
                logger.info(f"创建 SSH 连接：{host}")
                client = await self._create_connection(host, config)
                self.pool[host] = client
            else:
                # 检查连接是否存活
                if not await self._is_connection_alive(client):
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
                stdout_content, stderr_content = await asyncio.to_thread(
                    self._read_outputs, stdout, stderr, timeout=timeout - 5
                )
            except asyncio.TimeoutError:
                logger.warning(f"命令执行超时：{host} {command}")
                asyncio.to_thread(stdout.channel.send_eof)
                exit_code = asyncio.to_thread(stdout.channel.recv_exit_status)
                return {
                    'host': host,
                    'command': command,
                    'status': 'timeout',
                    'exit_code': exit_code,
                    'stdout': '',
                    'stderr': f'命令执行超时'
                }
            
            exit_code = stdout.channel.recv_exit_status()
            
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
            for host, client in list(self.pool.items()):
                try:
                    client.close()
                except:
                    pass
            self.pool.clear()
            logger.info("所有 SSH 连接已关闭")
    
    async def _create_connection(self, host: str, config: Optional[SSHConfig] = None) -> paramiko.SSHClient:
        """创建 SSH 连接（支持认证配置）"""
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # 使用配置或默认配置
        cfg = config or SSHConfig(host=host)
        
        # 使用密钥或密码认证
        if cfg.key_file:
            try:
                await asyncio.to_thread(
                    client.connect,
                    hostname=host,
                    port=cfg.port,
                    username=cfg.username,
                    key_filename=cfg.key_file,
                    timeout=cfg.timeout
                )
                logger.info(f"密钥认证成功：{host}")
            except Exception as e:
                logger.error(f"密钥认证失败 {host}: {e}")
                # 尝试密码认证
                if cfg.password:
                    try:
                        await asyncio.to_thread(
                            client.connect,
                            hostname=host,
                            port=cfg.port,
                            username=cfg.username,
                            password=cfg.password,
                            timeout=cfg.timeout
                        )
                        logger.info(f"密码认证成功：{host}")
                    except Exception as e2:
                        logger.error(f"密码认证失败 {host}: {e2}")
                        raise
        else:
            # 默认密码认证（如果提供）
            if cfg.password:
                try:
                    await asyncio.to_thread(
                        client.connect,
                        hostname=host,
                        port=cfg.port,
                        username=cfg.username,
                        password=cfg.password,
                        timeout=cfg.timeout
                    )
                    logger.info(f"密码认证成功：{host}")
                except Exception as e:
                    logger.error(f"密码认证失败 {host}: {e}")
                    raise
            else:
                # 默认密钥认证
                try:
                    await asyncio.to_thread(
                        client.connect,
                        hostname=host,
                        port=cfg.port,
                        username=cfg.username,
                        timeout=cfg.timeout
                    )
                    logger.info(f"默认认证成功：{host}")
                except Exception as e:
                    logger.error(f"默认认证失败 {host}: {e}")
                    raise
        
        return client
    
    async def _is_connection_alive(self, client: paramiko.SSHClient) -> bool:
        """检查连接是否存活"""
        try:
            asyncio.to_thread(client.get_transport).send_eof
            return True
        except:
            return False
    
    async def _read_outputs(self, stdout, stderr, timeout: int = 300):
        """读取 stdout 和 stderr"""
        def read_outputs():
            stdout_content = stdout.read().decode('utf-8', errors='ignore')
            stderr_content = stderr.read().decode('utf-8', errors='ignore')
            return stdout_content, stderr_content
        
        return await asyncio.to_thread(read_outputs, timeout=timeout)
    
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
            client = await self.ssh_pool.get_connection(host)
            sftp = client.open_sftp()
            
            # 确保远程目录存在
            import os
            remote_dir = os.path.dirname(remote_path)
            if remote_dir:
                try:
                    sftp.mkdir(remote_dir, create=True)
                except Exception as e:
                    if "File exists" not in str(e):
                        logger.warning(f"创建远程目录失败 {host} {remote_dir}: {e}")
            
            # 上传文件
            sftp.put(local_path, remote_path)
            
            # 设置执行权限（如果是脚本）
            if remote_path.endswith(('.sh', '.bat', '.cmd', '.ps1')):
                try:
                    result = await asyncio.to_thread(
                        self.ssh_pool.pool[host].exec_command,
                        f"chmod +x {remote_path}"
                    )
                    stdout, stderr = result
                    exit_code = stdout.channel.recv_exit_status()
                    if exit_code == 0:
                        logger.info(f"设置执行权限成功 {host} {remote_path}")
                except Exception as e:
                    logger.warning(f"设置执行权限失败 {host} {remote_path}: {e}")
            
            sftp.close()
            
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
        except Exception as e:
            logger.error(f"上传文件错误 {host}: {e}")
            return {
                'host': host,
                'local_path': local_path,
                'remote_path': remote_path,
                'status': 'failed',
                'error': str(e)
            }
    
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
