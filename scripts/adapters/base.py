#!/usr/bin/env python3
"""适配器抽象基类:所有 agent 适配器实现统一接口,方便扩展新客户端。"""
import abc

class AgentAdapter(abc.ABC):
    """统一接口。每个 agent 适配器继承并实现。"""

    # 唯一标识,如 'minis' / 'codex' / 'claude' / 'gemini' / 'generic'
    name = "base"

    # ---- 检测 ----
    @staticmethod
    @abc.abstractmethod
    def is_installed() -> bool:
        """返回当前环境是否是该 agent(检测命令或配置目录)。"""

    # ---- 会话: 列出 ----
    @abc.abstractmethod
    def list_sessions(self, limit=50):
        """返回会话列表: [{session_id, title, started_at, last_active, message_count}]"""

    # ---- 会话: 取对话 ----
    @abc.abstractmethod
    def get_conversation(self, session_id, full=True):
        """返回该会话对话: {title, started_at, total, messages:[{role,created_at,text}]}"""

    # ---- 续聊(可能不支持) ----
    def resume(self, session_id, text):
        """触发续聊。不支持的 agent 返回 (False, 'not_supported')。"""
        return False, "not_supported"

    # ---- 工作区(产物收集目标) ----
    def workspace(self):
        """返回当前 agent 的工作/工作区目录。"""
        return None

    # ---- 元信息 ----
    def describe(self):
        return f"{self.name} adapter"

# 工厂: 按当前环境自动选择适配器
_registry = {}

def register_adapter(cls):
    _registry[cls.name] = cls
    return cls

def active_adapter():
    """返回当前环境下第一个 is_installed() 为真的适配器;都不匹配则 generic。
    可通过环境变量 RELAY_ADAPTER 强制指定(测试/跨环境用)。"""
    import os
    forced = os.environ.get("RELAY_ADAPTER")
    if forced:
        cls = _registry.get(forced)
        if cls:
            return cls()
    for name, cls in _registry.items():
        try:
            if cls.is_installed():
                return cls()
        except Exception:
            continue
    from . import generic
    return generic.GenericAdapter()

def get_adapter(name):
    cls = _registry.get(name)
    return cls() if cls else None
