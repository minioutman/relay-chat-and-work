#!/usr/bin/env python3
"""Claude Code 适配器: ~/.claude/projects/<proj>/<session>.jsonl"""
__version__ = "2.1.0"

import os, json, glob, subprocess
from .base import AgentAdapter, register_adapter

@register_adapter
class ClaudeAdapter(AgentAdapter):
    name = "claude"

    @staticmethod
    def is_installed():
        import shutil
        return shutil.which("claude") is not None or os.path.isdir(os.path.expanduser("~/.claude"))

    def _base(self):
        return os.path.expanduser("~/.claude/projects")

    def list_sessions(self, limit=50):
        base = self._base()
        if not os.path.isdir(base):
            return []
        sessions = []
        for jsonl in glob.glob(os.path.join(base, "**", "*"), recursive=True):
            if not jsonl.endswith(".jsonl"):
                continue
            sid = os.path.basename(jsonl).replace(".jsonl", "")
            mtime = os.path.getmtime(jsonl)
            import datetime
            last = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
            sessions.append({"session_id": sid, "title": sid, "started_at": last,
                             "last_active": last, "message_count": self._count(jsonl)})
        sessions.sort(key=lambda x: x["last_active"], reverse=True)
        return sessions[:limit]

    def _count(self, jsonl):
        n = 0
        try:
            with open(jsonl, encoding="utf-8") as f:
                n = sum(1 for _ in f)
        except Exception:
            pass
        return n

    def get_conversation(self, session_id, full=True):
        jsonl = self._find(session_id)
        if not jsonl:
            return None
        messages, role_names = [], {"user": "user", "assistant": "assistant"}
        try:
            with open(jsonl, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except Exception:
                        continue
                    mtype = obj.get("type")
                    if mtype in ("user_message", "student"):
                        text = obj.get("message", {}).get("content", "")
                        if isinstance(text, list):
                            text = " ".join(str(p.get("text", "")) for p in text if isinstance(p, dict))
                        messages.append({"role": "user", "created_at": obj.get("timestamp", ""), "text": text})
                    elif mtype in ("assistant"):
                        text = obj.get("message", {}).get("content", "")
                        if isinstance(text, list):
                            text = " ".join(str(p.get("text", "")) for p in text if isinstance(p, dict))
                        messages.append({"role": "assistant", "created_at": obj.get("timestamp", ""), "text": text})
        except Exception:
            pass
        return {"title": session_id, "started_at": "", "total": len(messages), "messages": messages}

    def _find(self, sid):
        for p in glob.glob(os.path.join(self._base(), "**", "*.jsonl"), recursive=True):
            if os.path.basename(p).replace(".jsonl", "") == sid:
                return p
        return None

    def resume(self, session_id, text):
        return False, "claude-code 自动续聊需手动 'claude --resume' 打开会话;由使用者执行"
