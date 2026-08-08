#!/usr/bin/env python3
"""通用兜底适配器: 没有任何已知 CLI 会话系统时的 fallback。
只依赖纯 Markdown / git,适用于任何环境(云端 IDE、ChatGPT 等只传 MD)。
"""
import os
from .base import AgentAdapter, register_adapter

@register_adapter
class GenericAdapter(AgentAdapter):
    name = "generic"

    @staticmethod
    def is_installed():
        # 通用兜底: 永远匹配(优先级最低,放最后)
        return True

    def list_sessions(self, limit=50):
        # 无本地会话系统 → 空列表;若指定了私人库目录,可从 archive_index/README 读
        return []

    def get_conversation(self, session_id, full=True):
        return None

    def resume(self, session_id, text):
        return False, "generic(纯MD环境): 无本地会话续聊;请引用 conversation.md/ISSUES.md 由 AI 接着做"

    def workspace(self):
        env = os.environ.get("RELAY_WORKSPACE")
        if env and os.path.isdir(env):
            return env
        if os.path.isdir(os.path.expanduser("~/workspace")):
            return os.path.expanduser("~/workspace")
        return os.environ.get("PWD") or os.getcwd()

    def describe(self):
        return "通用(纯 MD): 任何环境,靠 Markdown 传上下文续做"
