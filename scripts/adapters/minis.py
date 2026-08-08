#!/usr/bin/env python3
"""Minis 适配器: 通过 minis-sessions-cli 与 Minis 会话系统交互。"""
import json, subprocess
from .base import AgentAdapter, register_adapter

@register_adapter
class MinisAdapter(AgentAdapter):
    name = "minis"

    @staticmethod
    def is_installed():
        import shutil
        return shutil.which("minis-sessions-cli") is not None

    def _run(self, args, timeout=60):
        r = subprocess.run(["minis-sessions-cli"] + args,
                           capture_output=True, text=True, timeout=timeout)
        try:
            return json.loads(r.stdout)
        except Exception:
            return {"ok": False, "raw": r.stdout}

    def list_sessions(self, limit=50):
        out = self._run(["list", "--limit", str(limit)])
        if not out.get("ok"):
            return []
        result = []
        for s in out["data"]["sessions"]:
            result.append({
                "session_id": s.get("session_id"),
                "title": s.get("title"),
                "started_at": s.get("started_at"),
                "last_active": s.get("last_active"),
                "message_count": s.get("message_count"),
            })
        return result

    def get_conversation(self, session_id, full=True):
        args = ["messages", "--id", session_id] + (["--full"] if full else [])
        out = self._run(args)
        if not out.get("ok"):
            return None
        data = out.get("data", {})
        return {
            "title": data.get("title"),
            "started_at": data.get("started_at"),
            "total": data.get("total", len(data.get("messages", []))),
            "messages": data.get("messages", []),
        }

    def resume(self, session_id, text):
        out = self._run(["send", text, "--session", session_id])
        if out.get("ok"):
            status = out.get("data", {}).get("status") or out.get("data", {}).get("session_id", "")
            return True, f"派发续聊(session {status})"
        return False, "minis send 失败"

    def workspace(self):
        return "/var/minis/workspace"

    def describe(self):
        return "Minis (本地 app), 支持真续聊"
