#!/usr/bin/env python3
"""Codex CLI 适配器: ~/.codex/sessions/<session>.jsonl + codex resume 续聊"""
__version__ = "2.1.0"

import os, json, glob, subprocess, datetime
from .base import AgentAdapter, register_adapter

@register_adapter
class CodexAdapter(AgentAdapter):
    name = "codex"

    @staticmethod
    def is_installed():
        import shutil
        return shutil.which("codex") is not None or os.path.isdir(os.path.expanduser("~/.codex/sessions"))

    def _base(self):
        return os.path.expanduser("~/.codex/sessions")

    def list_sessions(self, limit=50):
        base = self._base()
        if not os.path.isdir(base):
            return []
        sessions = []
        for jsonl in glob.glob(os.path.join(base, "*.jsonl")):
            sid = os.path.basename(jsonl).replace(".jsonl", "")
            mtime = os.path.getmtime(jsonl)
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
        jsonl = os.path.join(self._base(), f"{session_id}.jsonl")
        if not os.path.isfile(jsonl):
            return None
        messages = []
        try:
            with open(jsonl, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line: continue
                    try: obj = json.loads(line)
                    except Exception: continue
                    role = obj.get("role")
                    if role not in ("user", "assistant"):
                        continue
                    content = obj.get("content", obj.get("message", ""))
                    if isinstance(content, str):
                        text = content
                    elif isinstance(content, list):
                        text = " ".join(str(p.get("text", "")) for p in content if isinstance(p, dict))
                    else:
                        text = str(content) if content else ""
                    messages.append({"role": role, "created_at": obj.get("timestamp", obj.get("created_at", "")), "text": text})
        except Exception:
            pass
        return {"title": session_id, "started_at": "", "total": len(messages), "messages": messages}

    def resume(self, session_id, text):
        # codex exec --resume <session_id>? codex CLI 支持 codex exec · 续做。
        # 用最通用方式: codex exec 带上上下文说明并指定 resume。
        try:
            cmd = ["codex", "exec", "--session", session_id, text] if False else \
                  ["codex", "exec", "--resume", session_id, text]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if r.returncode == 0:
                return True, "codex exec --resume 已执行"
            # 回退: 尝试 codex --continue
            r2 = subprocess.run(["codex", "--continue", text], capture_output=True, text=True, timeout=120)
            if r2.returncode == 0:
                return True, "codex --continue 已执行"
            return False, f"codex resume 未成功: {r.stderr[:200]}"
        except Exception as e:
            return False, f"codex resume 调用失败: {e}"
