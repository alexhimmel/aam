"""
SSH 连接池单元测试
"""

import asyncio
import pytest
from unittest.mock import Mock, patch, MagicMock
from app.core.ssh import SSHConnectionPool, SSHConfig


class TestSSHConnectionPool:
    """SSHConnectionPool 测试类"""
    
    @pytest.fixture
    def pool(self):
        """创建 SSH 连接池实例"""
        return SSHConnectionPool(max_connections=5)
    
    @pytest.fixture
    def mock_ssh_client(self):
        """创建 Mock SSH 客户端"""
        client = MagicMock()
        client.exec_command.return_value = (MagicMock(), MagicMock(), MagicMock())
        client.get_transport.return_value.send_eof = MagicMock()
        return client
    
    @pytest.mark.asyncio
    async def test_get_connection_creates_new(self, pool, mock_ssh_client):
        """测试获取新连接"""
        with patch('app.core.ssh.paramiko.SSHClient') as mock_client_class:
            mock_client_class.return_value = mock_ssh_client
            result = await pool.get_connection('test.example.com')
            
            assert mock_client_class.called
            assert 'test.example.com' in pool.pool
            assert result == mock_ssh_client
    
    @pytest.mark.asyncio
    async def test_get_connection_reuses(self, pool, mock_ssh_client):
        """测试连接复用"""
        with patch('app.core.ssh.paramiko.SSHClient') as mock_client_class:
            mock_client_class.return_value = mock_ssh_client
            await pool.get_connection('test.example.com')
            result = await pool.get_connection('test.example.com')
            
            # 第二次调用应该复用连接
            assert result == mock_ssh_client
    
    @pytest.mark.asyncio
    async def test_execute_command_success(self, pool, mock_ssh_client):
        """测试执行命令成功"""
        with patch('app.core.ssh.paramiko.SSHClient') as mock_client_class:
            mock_client_class.return_value = mock_ssh_client
            
            # 设置 exec_command 返回值
            mock_stdout = MagicMock()
            mock_stderr = MagicMock()
            mock_stdout.read.return_value = b'echo "hello"\n'
            mock_stderr.read.return_value = b''
            mock_stdout.channel.recv_exit_status.return_value = 0
            
            mock_client_class.return_value.exec_command.return_value = (mock_stdout, mock_stderr, MagicMock())
            
            result = await pool.execute('test.example.com', 'echo "hello"')
            
            assert result['status'] == 'success'
            assert result['stdout'] == 'echo "hello"\n'
            assert result['exit_code'] == 0
    
    @pytest.mark.asyncio
    async def test_execute_command_timeout(self, pool, mock_ssh_client):
        """测试命令执行超时"""
        with patch('app.core.ssh.paramiko.SSHClient') as mock_client_class:
            mock_client_class.return_value = mock_ssh_client
            
            mock_stdout = MagicMock()
            mock_stdout.channel.recv_exit_status.return_value = 0
            
            mock_client_class.return_value.exec_command.return_value = (mock_stdout, MagicMock(), MagicMock())
            
            result = await pool.execute('test.example.com', 'sleep 10', timeout=1)
            
            assert result['status'] == 'timeout'
    
    @pytest.mark.asyncio
    async def test_execute_batch(self, pool, mock_ssh_client):
        """测试批量执行命令"""
        with patch('app.core.ssh.paramiko.SSHClient') as mock_client_class:
            mock_client_class.return_value = mock_ssh_client
            
            mock_stdout = MagicMock()
            mock_stdout.read.return_value = b'output1\n'
            mock_stderr.read.return_value = b''
            mock_stdout.channel.recv_exit_status.return_value = 0
            
            mock_client_class.return_value.exec_command.return_value = (mock_stdout, MagicMock(), MagicMock())
            
            tasks = [('host1', 'cmd1'), ('host2', 'cmd2')]
            results = await pool.execute_batch(tasks)
            
            assert len(results) == 2
            assert results[0]['command'] == 'cmd1'
            assert results[1]['command'] == 'cmd2'
    
    @pytest.mark.asyncio
    async def test_close_all(self, pool):
        """测试关闭所有连接"""
        pool.pool['host1'] = MagicMock()
        pool.pool['host2'] = MagicMock()
        
        await pool.close_all()
        
        assert len(pool.pool) == 0


class TestSSHConfig:
    """SSHConfig 测试类"""
    
    def test_default_values(self):
        """测试默认值"""
        config = SSHConfig(host='test.example.com')
        
        assert config.host == 'test.example.com'
        assert config.port == 22
        assert config.username == 'root'
        assert config.key_file is None
        assert config.password is None
        assert config.timeout == 30
    
    def test_with_custom_values(self):
        """测试自定义值"""
        config = SSHConfig(
            host='test.example.com',
            port=2222,
            username='admin',
            key_file='/path/to/key',
            password='secret',
            timeout=60
        )
        
        assert config.port == 2222
        assert config.username == 'admin'
        assert config.key_file == '/path/to/key'
        assert config.password == 'secret'
        assert config.timeout == 60


class TestAsyncioToThread:
    """asyncio.to_thread 使用测试"""
    
    @pytest.mark.asyncio
    async def test_to_thread_with_blocking_call(self):
        """测试 asyncio.to_thread 包装同步调用"""
        def blocking_call():
            time.sleep(0.1)
            return 'result'
        
        result = await asyncio.to_thread(blocking_call)
        assert result == 'result'
    
    @pytest.mark.asyncio
    async def test_to_thread_with_timeout(self):
        """测试异步超时"""
        def slow_call():
            time.sleep(10)
            return 'result'
        
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                asyncio.to_thread(slow_call),
                timeout=0.1
            )


import time
