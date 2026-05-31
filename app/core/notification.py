"""
通知服务模块
支持邮件和 Webhook 通知
"""

import smtplib
import json
from typing import Optional, Dict
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

logger = logging.getLogger(__name__)


class NotificationService:
    """通知服务 - 支持邮件和 Webhook"""
    
    def __init__(self, config: Dict):
        """
        初始化通知服务
        
        Args:
            config: 配置字典，包含 email 和 webhook 配置
        """
        self.config = config
        self.email_config = config.get('email', {})
        self.webhook_config = config.get('webhook', {})
    
    async def send_email(self, task_id: int, task_name: str, result: dict) -> bool:
        """
        发送邮件通知
        
        Args:
            task_id: 任务 ID
            task_name: 任务名称
            result: 执行结果
            
        Returns:
            是否发送成功
        """
        if not self.email_config.get('enabled', False):
            logger.info(f"邮件通知已禁用，跳过任务 {task_id}")
            return False
        
        try:
            # 构建邮件内容
            subject = self._build_subject(task_id, task_name, result)
            body = self._build_body(task_id, task_name, result)
            
            # 设置邮件
            msg = MIMEMultipart()
            msg['From'] = self.email_config.get('from', 'aam@localhost')
            msg['To'] = self.email_config.get('to', '')
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # 发送邮件
            server = smtplib.SMTP(self.email_config.get('smtp_server', 'localhost'),
                                self.email_config.get('smtp_port', 25))
            if self.email_config.get('use_tls', False):
                server.starttls()
            if self.email_config.get('username'):
                server.login(self.email_config.get('username'),
                           self.email_config.get('password'))
            
            server.send_message(msg)
            server.quit()
            
            logger.info(f"邮件通知成功：任务 {task_id} {task_name}")
            return True
            
        except Exception as e:
            logger.error(f"邮件通知失败 {task_id}: {e}")
            return False
    
    def _build_subject(self, task_id: int, task_name: str, result: dict) -> str:
        """构建邮件主题"""
        status = result.get('status', 'unknown')
        return f"[{'✅成功' if status == 'success' else '❌失败'}] AAM 任务 {task_id}: {task_name}"
    
    def _build_body(self, task_id: int, task_name: str, result: dict) -> str:
        """构建邮件正文"""
        host = result.get('host', 'unknown')
        command = result.get('command', '')
        exit_code = result.get('exit_code', -1)
        stdout = result.get('stdout', '')
        stderr = result.get('stderr', '')
        
        status_icon = '✅成功' if exit_code == 0 else '❌失败'
        
        body = f"""
AAM 任务执行通知

任务 ID: {task_id}
任务名称：{task_name}
主机：{host}
命令：{command}
状态：{status_icon}
退出码：{exit_code}

输出:
{stdout}

错误信息:
{stderr}
"""
        return body
    
    async def send_webhook(self, task_id: int, task_name: str, result: dict) -> bool:
        """
        发送 Webhook 通知
        
        Args:
            task_id: 任务 ID
            task_name: 任务名称
            result: 执行结果
            
        Returns:
            是否发送成功
        """
        if not self.webhook_config.get('enabled', False):
            logger.info(f"Webhook 通知已禁用，跳过任务 {task_id}")
            return False
        
        try:
            webhook_url = self.webhook_config.get('url', '')
            if not webhook_url:
                return False
            
            # 构建 payload
            payload = {
                'task_id': task_id,
                'task_name': task_name,
                'status': result.get('status'),
                'host': result.get('host'),
                'command': result.get('command'),
                'exit_code': result.get('exit_code'),
                'stdout': result.get('stdout', ''),
                'stderr': result.get('stderr', ''),
                'timestamp': str(result.get('timestamp') or result.get('created_at'))
            }
            
            # 不同平台的格式
            if 'slack' in webhook_url.lower():
                payload = self._build_slack_payload(payload)
            elif 'discord' in webhook_url.lower():
                payload = self._build_discord_payload(payload)
            elif 'dingtalk' in webhook_url.lower() or 'ding' in webhook_url.lower():
                payload = self._build_dingtalk_payload(payload)
            
            # 发送请求
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload, timeout=30) as resp:
                    if resp.status == 200 or resp.status == 201:
                        logger.info(f"Webhook 通知成功：任务 {task_id} {task_name}")
                        return True
                    else:
                        logger.error(f"Webhook 通知失败 {task_id}: HTTP {resp.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"Webhook 通知失败 {task_id}: {e}")
            return False
    
    def _build_slack_payload(self, payload: dict) -> dict:
        """构建 Slack 格式"""
        return {
            "text": f"AAM 任务执行：{payload['task_name']}",
            "attachments": [
                {
                    "color": "good" if payload['status'] == 'success' else "danger",
                    "fields": [
                        {"title": "任务 ID", "value": str(payload['task_id']), "short": True},
                        {"title": "状态", "value": payload['status'], "short": True},
                        {"title": "主机", "value": payload['host'], "short": True},
                        {"title": "命令", "value": payload['command'], "short": False},
                        {"title": "退出码", "value": str(payload['exit_code']), "short": True},
                    ]
                }
            ]
        }
    
    def _build_discord_payload(self, payload: dict) -> dict:
        """构建 Discord 格式"""
        embed = {
            "title": f"AAM 任务执行：{payload['task_name']}",
            "description": f"任务 ID: {payload['task_id']}",
            "color": 0x00FF00 if payload['status'] == 'success' else 0xFF0000,
            "fields": [
                {"name": "主机", "value": payload['host'], "inline": True},
                {"name": "命令", "value": payload['command'], "inline": False},
                {"name": "状态", "value": payload['status'], "inline": True},
                {"name": "退出码", "value": str(payload['exit_code']), "inline": True},
            ],
            "footer": {
                "text": "AAM Task Management"
            }
        }
        return {"embeds": [embed]}
    
    def _build_dingtalk_payload(self, payload: dict) -> dict:
        """构建钉钉格式"""
        markdown = f"""# AAM 任务执行通知

**任务名称**：{payload['task_name']}
**任务 ID**：{payload['task_id']}
**状态**：{'✅ 成功' if payload['status'] == 'success' else '❌ 失败'}
**主机**：{payload['host']}
**命令**：{payload['command']}
**退出码**：{payload['exit_code']}
"""
        return {
            "msgtype": "markdown",
            "markdown": markdown
        }
    
    async def send_notification(self, task_id: int, task_name: str, result: dict) -> bool:
        """
        发送通知（邮件或 Webhook）
        
        Args:
            task_id: 任务 ID
            task_name: 任务名称
            result: 执行结果
            
        Returns:
            是否至少一个通知成功
        """
        success = False
        
        # 发送邮件
        if self.email_config.get('enabled', False):
            if await self.send_email(task_id, task_name, result):
                success = True
        
        # 发送 Webhook
        if self.webhook_config.get('enabled', False):
            if await self.send_webhook(task_id, task_name, result):
                success = True
        
        return success
