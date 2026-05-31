"""
通知服务单元测试
测试邮件和 Webhook 通知功能
"""

import asyncio
import pytest
from unittest.mock import Mock, patch, MagicMock
from app.core.notification import NotificationService


class TestNotificationService:
    """通知服务测试类"""
    
    @pytest.fixture
    def mock_email_config(self):
        """邮件配置 fixture"""
        return {
            'enabled': True,
            'smtp_server': 'smtp.example.com',
            'smtp_port': 587,
            'use_tls': True,
            'username': 'test@example.com',
            'password': 'test_password',
            'from': 'test@example.com',
            'to': 'admin@example.com'
        }
    
    @pytest.fixture
    def mock_webhook_config(self):
        """Webhook 配置 fixture"""
        return {
            'enabled': True,
            'url': 'https://hooks.slack.com/test',
            'platform': 'slack'
        }
    
    @pytest.fixture
    def notification_service(self, mock_email_config, mock_webhook_config):
        """通知服务 fixture"""
        return NotificationService({
            'email': mock_email_config,
            'webhook': mock_webhook_config
        })
    
    @pytest.mark.asyncio
    async def test_send_email_enabled(self, notification_service):
        """测试启用邮件通知"""
        result = {'status': 'success', 'command': 'uptime'}
        
        with patch('app.core.notification.smtplib.SMTP') as mock_smtp:
            mock_smtp_instance = Mock()
            mock_smtp.return_value.__enter__.return_value = mock_smtp_instance
            mock_smtp_instance.send_message.return_value = None
            
            success = await notification_service.send_email(1, '任务 1', result)
            
            assert success is True
            mock_smtp.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_email_disabled(self, notification_service):
        """测试禁用邮件通知"""
        result = {'status': 'success', 'command': 'uptime'}
        
        # 禁用邮件
        notification_service.email_config['enabled'] = False
        
        success = await notification_service.send_email(1, '任务 1', result)
        
        assert success is False
    
    @pytest.mark.asyncio
    async def test_send_webhook_slack(self, notification_service):
        """测试发送 Slack Webhook"""
        result = {'status': 'success', 'command': 'uptime'}
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = Mock()
            mock_response.status = 200
            mock_context = Mock().__enter__
            mock_context.return_value = mock_response
            mock_session.return_value.__aenter__.return_value = mock_response
            
            success = await notification_service.send_webhook(1, '任务 1', result)
            
            assert success is True
    
    @pytest.mark.asyncio
    async def test_send_webhook_discord(self, notification_service):
        """测试发送 Discord Webhook"""
        result = {'status': 'failed', 'command': 'uptime'}
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = Mock()
            mock_response.status = 200
            mock_context = Mock().__enter__
            mock_context.return_value = mock_response
            mock_session.return_value.__aenter__.return_value = mock_response
            
            success = await notification_service.send_webhook(
                1, '任务 1', result,
                webhook_url='https://discord.com/webhook/test'
            )
            
            assert success is True
    
    @pytest.mark.asyncio
    async def test_send_webhook_dingtalk(self, notification_service):
        """测试发送钉钉 Webhook"""
        result = {'status': 'success', 'command': 'uptime'}
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = Mock()
            mock_response.status = 200
            mock_context = Mock().__enter__
            mock_context.return_value = mock_response
            mock_session.return_value.__aenter__.return_value = mock_response
            
            success = await notification_service.send_webhook(
                1, '任务 1', result,
                webhook_url='https://oapi.dingtalk.com/robot/send'
            )
            
            assert success is True
    
    @pytest.mark.asyncio
    async def test_send_notification_both_enabled(self, notification_service):
        """测试邮件和 Webhook 都启用"""
        result = {'status': 'success', 'command': 'uptime'}
        
        with patch('app.core.notification.smtplib.SMTP') as mock_smtp, \
             patch('aiohttp.ClientSession') as mock_session:
            
            # 模拟邮件成功
            mock_smtp_instance = Mock()
            mock_smtp.return_value.__enter__.return_value = mock_smtp_instance
            mock_smtp_instance.send_message.return_value = None
            
            # 模拟 Webhook 成功
            mock_response = Mock()
            mock_response.status = 200
            mock_context = Mock().__enter__
            mock_context.return_value = mock_response
            mock_session.return_value.__aenter__.return_value = mock_response
            
            success = await notification_service.send_notification(1, '任务 1', result)
            
            assert success is True
    
    @pytest.mark.asyncio
    async def test_send_notification_both_disabled(self, notification_service):
        """测试邮件和 Webhook 都禁用"""
        result = {'status': 'success', 'command': 'uptime'}
        
        # 禁用所有通知
        notification_service.email_config['enabled'] = False
        notification_service.webhook_config['enabled'] = False
        
        success = await notification_service.send_notification(1, '任务 1', result)
        
        assert success is False
