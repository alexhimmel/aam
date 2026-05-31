"""
任务类型识别模块
负责判断任务类型并确定执行策略
"""

import os
import re
from typing import Optional, Tuple


class TaskTypeIdentifier:
    """任务类型识别器"""
    
    # 任务类型定义
    TASK_TYPE_COMMAND = "command"
    TASK_TYPE_SCRIPT = "脚本"
    TASK_TYPE_FILE = "文件"
    
    # 常见脚本扩展名
    SCRIPT_EXTENSIONS = {
        '.sh', '.bash', '.zsh', '.ps1', '.bat', '.cmd',
        '.py', '.pl', '.rb', '.js', '.ts', '.php', '.go', '.java'
    }
    
    # 路径分隔符（兼容不同系统）
    PATH_DELIMITERS = {'/', '\\'}
    
    def __init__(self):
        """初始化任务类型识别器"""
        pass
    
    def identify(self, command: str, task_type: Optional[str] = None) -> dict:
        """
        识别任务类型并确定执行策略
        
        Args:
            command: 命令字符串
            task_type: 任务类型（可选，如果提供则直接使用）
            
        Returns:
            包含任务类型和执行策略的字典
        """
        # 如果 task_type 已提供，直接使用
        if task_type:
            return self._build_strategy(task_type, command)
        
        # 否则根据命令内容自动识别
        command_stripped = command.strip()
        
        # 检查是否包含文件路径（以路径分隔符开头）
        if self._is_file_command(command_stripped):
            return self._build_strategy(self.TASK_TYPE_FILE, command)
        
        # 检查是否以常见脚本扩展名结尾
        if self._is_script_command(command_stripped):
            return self._build_strategy(self.TASK_TYPE_SCRIPT, command)
        
        # 默认为命令类型
        return self._build_strategy(self.TASK_TYPE_COMMAND, command)
    
    def _is_file_command(self, command: str) -> bool:
        """
        检查命令是否为文件执行命令
        
        Args:
            command: 命令字符串
            
        Returns:
            是否为文件执行命令
        """
        # 去除引号
        command_clean = command.strip().strip('"').strip("'").strip()
        
        # 检查是否以路径分隔符开头（表示文件路径）
        for delimiter in self.PATH_DELIMITERS:
            if command_clean.startswith(delimiter):
                return True
        
        return False
    
    def _is_script_command(self, command: str) -> bool:
        """
        检查命令是否为脚本执行命令
        
        Args:
            command: 命令字符串
            
        Returns:
            是否为脚本执行命令
        """
        # 去除引号
        command_clean = command.strip().strip('"').strip("'").strip()
        
        # 检查命令是否以可执行文件结尾
        for ext in self.SCRIPT_EXTENSIONS:
            if command_clean.endswith(ext):
                return True
        
        return False
    
    def _build_strategy(self, task_type: str, command: str) -> dict:
        """
        构建执行策略
        
        Args:
            task_type: 任务类型
            command: 命令字符串
            
        Returns:
            执行策略字典
        """
        # 规范化命令
        command_normalized = command.strip().strip('"').strip("'").strip()
        
        strategy = {
            'task_type': task_type,
            'command': command_normalized,
            'requires_upload': False,
            'upload_dir': None,
            'working_dir': None,
            'execution_path': command_normalized,
            'description': self._get_task_description(task_type, command)
        }
        
        # 如果是脚本或文件类型，检查是否设置了上传目录
        if task_type in [self.TASK_TYPE_SCRIPT, self.TASK_TYPE_FILE]:
            # 检查命令中是否包含路径
            for delimiter in self.PATH_DELIMITERS:
                if delimiter in command_normalized:
                    strategy['requires_upload'] = True
                    strategy['working_dir'] = '/tmp/aam'  # 默认上传目录
                    # 从命令中提取相对路径
                    strategy['upload_dir'] = self._extract_path_from_command(command_normalized)
        
        return strategy
    
    def _extract_path_from_command(self, command: str) -> str:
        """
        从命令中提取路径
        
        Args:
            command: 命令字符串
            
        Returns:
            提取的路径
        """
        # 去除引号
        command_clean = command.strip().strip('"').strip("'").strip()
        
        # 查找路径分隔符的位置
        for delimiter in self.PATH_DELIMITERS:
            idx = command_clean.find(delimiter)
            if idx != -1:
                # 找到路径分隔符后的内容
                return command_clean[idx:].strip()
        
        return command_clean
    
    def _get_task_description(self, task_type: str, command: str) -> str:
        """
        获取任务描述
        
        Args:
            task_type: 任务类型
            command: 命令字符串
            
        Returns:
            任务描述
        """
        descriptions = {
            self.TASK_TYPE_COMMAND: f"远程命令执行：{command}",
            self.TASK_TYPE_SCRIPT: f"脚本执行：{command}（需要上传）",
            self.TASK_TYPE_FILE: f"文件执行：{command}（需要上传）"
        }
        
        return descriptions.get(task_type, f"任务：{command}")


# 创建全局实例
task_type_identifier = TaskTypeIdentifier()


def identify_task(command: str, task_type: Optional[str] = None) -> dict:
    """
    便捷函数：识别任务类型
    
    Args:
        command: 命令字符串
        task_type: 任务类型（可选）
        
    Returns:
        执行策略字典
    """
    return task_type_identifier.identify(command, task_type)
