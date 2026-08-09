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
        if shutil.which("codex") is not None:
            return True
        sessions = os.path.expanduser("~/.codex/sessions")
        return any(
            p.endswith(".jsonl")
            for p in glob.glob(os.path.join(sessions, "**", "*.jsonl"), recursive=True)
        )

    def _base(self):
        return os.path.expanduser("~/.codex/sessions")

    def _all_jsonl(self):
        return [
            p for p in glob.glob(os.path.join(self._base(), "**", "*.jsonl"), recursive=True)
            if p.endswith(".jsonl")
        ]

    def _meta(self, jsonl):
        sid = started = None
        try:
            with open(jsonl, encoding="utf-8") as f:
                for line in f:
                    try:
                        obj = json.loads(line)
                    except Exception:
                        continue
                    if obj.get("type") != "session_meta":
                        continue
                    payload = obj.get("payload", {})
                    sid = payload.get("session_id") or payload.get("id")
                    started = payload.get("timestamp") or obj.get("timestamp")
                    if sid:
                        break
        except Exception:
            pass
        return sid, started

    def list_sessions(self, limit=50):
        groups = {}
        for jsonl in self._all_jsonl():
            sid, started = self._meta(jsonl)
            key = sid or os.path.basename(jsonl)[:-6]
            mtime = os.path.getmtime(jsonl)
            last = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
            g = groups.setdefault(key, {
                "session_id": key,
                "title": "",
                "started_at": started or last,
                "last_active": last,
                "message_count": 0,
            })
            if started and (not g["started_at"] or started < g["started_at"]):
                g["started_at"] = started
            if last > g["last_active"]:
                g["last_active"] = last
            g["message_count"] += self._count(jsonl)
        sessions = list(groups.values())
        sessions.sort(key=lambda x: x["last_active"], reverse=True)
        return sessions[:limit]

    def _count(self, jsonl):
        n = 0
        try:
            with open(jsonl, encoding="utf-8") as f:
                for line in f:
                    try:
                        obj = json.loads(line)
                    except Exception:
                        continue
                    payload = obj.get("payload", {})
                    if obj.get("type") == "response_item" and payload.get("type") == "message":
                        n += 1
        except Exception:
            pass
        return n

    def get_conversation(self, session_id, full=True):
        files = self._session_files(session_id)
        if not files:
            return None
        messages, started_at, seen = [], "", set()
        for jsonl in files:
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
                        if obj.get("type") == "session_meta":
                            payload = obj.get("payload", {})
                            ts = payload.get("timestamp") or obj.get("timestamp", "")
                            if not started_at or (ts and ts < started_at):
                                started_at = ts
                            continue
                        if obj.get("type") != "response_item":
                            continue
                        payload = obj.get("payload", {})
                        if payload.get("type") != "message":
                            continue
                        role = payload.get("role")
                        if role not in ("user", "assistant"):
                            continue
                        msg_id = payload.get("id") or obj.get("id")
                        if msg_id:
                            if msg_id in seen:
                                continue
                            seen.add(msg_id)
                        text = self._extract_text(payload.get("content"))
                        if text:
                            messages.append({
                                "role": role,
                                "created_at": obj.get("timestamp", payload.get("timestamp", "")),
                                "text": text,
                            })
            except Exception:
                continue
        messages.sort(key=lambda m: m["created_at"] or "")
        return {"title": "", "started_at": started_at, "total": len(messages), "messages": messages}

    @staticmethod
    def _extract_text(content):
        if isinstance(content, str):
            return content.strip()
        if not isinstance(content, list):
            return ""
        parts = []
        for item in content:
            if not isinstance(item, dict):
                continue
            if item.get("type") in ("input_text", "output_text", "text", "refusal"):
                text = item.get("text", item.get("content", ""))
                if isinstance(text, str):
                    parts.append(text)
        return " ".join(parts).strip()

    def _session_files(self, sid):
        sid = sid or ""
        files = []
        for p in self._all_jsonl():
            if os.path.basename(p)[:-6] == sid:
                files.append(p)
                continue
            meta_sid, _ = self._meta(p)
            if meta_sid == sid:
                files.append(p)
                continue
            if sid and sid.lower() in os.path.basename(p).lower():
                files.append(p)
        return files

    def workspace(self):
        env = os.environ.get("RELAY_WORKSPACE")
        if env:
            return env
        return os.environ.get("PWD") or os.getcwd()

    def resume(self, session_id, text):
        # codex exec resume 是非交互式续聊;旧版 CLI 回退到 --resume。
        cmds = [
            ["codex", "exec", "resume", session_id, text],
            ["codex", "exec", "--resume", session_id, text],
        ]
        last_err = ""
        for cmd in cmds:
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            except Exception as e:
                last_err = str(e)
                continue
            if r.returncode == 0:
                return True, "codex exec resume 已执行"
            last_err = (r.stderr or r.stdout or "").strip()[:200]
        return False, f"codex resume 未成功: {last_err}"
