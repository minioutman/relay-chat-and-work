#!/usr/bin/env python3
"""
relay-chat-and-work: 对话存档脚本
把指定会话导出为 conversation.md + 收集产物文件 + 写 meta.json,
并通过 archive_index.json 维护别名链与标题联动改名,生成根目录总览 README.md。

用法:
  archive_session.py --id <session_id> [--workspace <dir>] [--slug <name>] [--index <path>]
"""
import json, subprocess, sys, os, datetime, shutil, argparse, re

# 适配器层: 动态选择当前环境的 agent(Minis/Codex/Claude/Generic)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from adapters import minis, claude, codex, generic  # noqa: F401
import adapters.base as abase

def get_adapter():
    """返回当前环境的会话适配器。"""
    return abase.active_adapter()

# ---------- 基础工具 ----------
def get_session(sid):
    """改用适配器拉会话,适配当前 agent。"""
    try:
        conv = get_adapter().get_conversation(sid)
        if conv is None:
            return None
        # 包装成原有结构
        return {"data": {"messages": conv.get("messages", []),
                         "title": conv.get("title"),
                         "started_at": conv.get("started_at"),
                         "total": conv.get("total", len(conv.get("messages", [])))},
                "ok": True}
    except Exception as e:
        print(f"[错误] 拉取会话 {sid} 失败: {e}", file=sys.stderr)
        return None

def sanitize_dirname(name):
    name = (name or "").strip().replace("/","_").replace("\\","_")
    name = name.replace(":","_").replace("*","_").replace("?","_")
    name = name.replace('"',"_").replace("<","_").replace(">","_").replace("|","_")
    name = name.strip(". ")
    return name or "untitled-session"

def get_device():
    """获取当前 iOS 设备名,用于存档文件夹名区分多设备。"""
    try:
        out = subprocess.run(["apple-device","--compact"],
                             capture_output=True, text=True, timeout=20)
        d = json.loads(out.stdout)
        name = d.get('data',{}).get('device',{}).get('name') or 'device'
        return sanitize_dirname(name)
    except Exception:
        return 'device'

def build_folder_name(title, started_at, device='device'):
    """文件夹名 = 真实标题 + 会话开始时间 + 设备名。
    例: 如何创建自定义技能_2026-08-09_0148_iPhone"""
    ts = ''
    if started_at:
        t = started_at.strip().replace(' ','_').replace(':','').replace('/','_')
        mm = re.match(r'(\d{4})[_\-](\d{2})[_\-](\d{2})[_\-](\d{2})(\d{2})?', t)
        if mm:
            y,mo,d,h,mi = mm.groups()
            ts = f"{y}-{mo}-{d}_{h or '00'}{mi or '00'}"
        else:
            ts = sanitize_dirname(started_at)
    dev = sanitize_dirname(device or 'device')
    base = sanitize_dirname(title)
    parts = [p for p in (base, ts, dev) if p]
    return "_".join(parts) if parts else "untitled-session"

def get_session_meta(sid):
    """从会话列表接口拿真实标题与开始时间。"""
    try:
        for s in get_adapter().list_sessions(limit=100):
            if s.get('session_id') == sid:
                return {'title': s.get('title'), 'started_at': s.get('started_at')}
    except Exception:
        pass
    return {}

def collect_workspace_files(workspace_dir, project_dir, out_dir):
    """按「项目文件夹精确收集」: 只收集 workspace 下与当前会话标题同名
    的文件夹(<workspace>/<title>/),不扫描整个 workspace,杜绝串台。
    若该文件夹不存在,则回退为收集全部相关文件(需手动排除内部仓库)。
    返回相对 workspace 的路径列表。"""
    copied = []
    if not workspace_dir or not os.path.isdir(workspace_dir):
        return copied
    # 优先: 精确的项目文件夹
    candidates = []
    if project_dir and os.path.isdir(project_dir):
        candidates = [project_dir]
    else:
        # 回退: 整个 workspace(排除源码库/归档库)
        excl = {'relay-work-repo','relay-chat-and-work-repo','chatarchive-work',
                'relay-chat-and-work'}
        for d in os.listdir(workspace_dir):
            full = os.path.join(workspace_dir, d)
            if os.path.isdir(full) and d not in excl and not d.startswith('.'):
                candidates.append(full)
    out_abs = os.path.abspath(out_dir)
    exts = ('.py','.sh','.md','.json','.csv','.png','.jpg','.html','.js','.ts','.txt','.log')
    for root in candidates:
        base = os.path.abspath(root)
        for r, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for f in files:
                if f.startswith('.'): continue
                if not f.endswith(exts): continue
                src = os.path.join(r, f)
                if os.path.abspath(src).startswith(out_abs + os.sep): continue
                rel = os.path.relpath(src, base)
                rel_ws = os.path.relpath(src, os.path.abspath(workspace_dir))
                if rel_ws.startswith('..'): continue
                dst = os.path.join(out_dir, 'files', rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                try:
                    shutil.copy2(src, dst)
                    copied.append(rel_ws)
                except Exception:
                    pass
    return copied

def build_conversation_md(msgs, title, sid, started_at):
    lines = [f"# {title}", "",
             f"> 自动存档 | 会话ID: `{sid}` | 开始时间: {started_at or '未知'}", ""]
    for m in msgs:
        role = m.get('role','?')
        text = m.get('text','')
        ts = m.get('created_at','')
        tag = '👤 用户' if role=='user' else ('🤖 AI' if role=='assistant' else f'🔧 {role}')
        lines.append(f"## {tag}  |  {ts}")
        lines.append("")
        lines.append(text)
        lines.append("")
    return "\n".join(lines)

# ---------- 索引 / 别名链 ----------
def load_index(index_path):
    if index_path and os.path.isfile(index_path):
        try:
            with open(index_path,'r',encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_index(index_path, index):
    if not index_path: return
    with open(index_path,'w',encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

def append_alias(sid, index, new_title, old_title):
    """把旧标题追加进别名链(若还没记录),防止重复。"""
    entry = index.get(sid)
    if not entry: return
    aliases = entry.get('aliases', [])
    if old_title and old_title != new_title and old_title not in aliases:
        # 保留当前标题也进 aliases 作为链尾,但避免和 current_title 重复
        aliases.append(old_title)
    # 去重、去空
    seen, clean = set(), []
    for a in aliases:
        if a and a not in seen and a != new_title:
            seen.add(a); clean.append(a)
    entry['aliases'] = clean

# ---------- 总览 README ----------
def build_readme(out_dir, index):
    rows = []
    for sid in sorted(index, key=lambda s: index[s].get('started_at') or ''):
        e = index[sid]
        cur = e.get('current_title') or e.get('title') or e.get('folder','')
        aliases = '; '.join(e.get('aliases',[])) or '—'
        st = e.get('started_at') or '?'
        rows.append(f"| {cur} | {aliases} | {st} | `{sid[:8]}..` |")
    body = "\n".join(rows) if rows else "*（暂无会话存档）*"
    readme = f"""# 会话存档总览

> 自动存档 · 每次新对话补存上一轮会话到此私人仓库。
> 总量: {len(index)} 个会话

## 会话列表

| 当前标题 | 曾用名(别名) | 开始时间 | 会话ID |
|---------|--------------|---------|--------|
{body}

如需检索: 按「当前标题」或「曾用名」查找;跨 AI 沟通请引用「会话ID」以确保唯一对应。
"""
    readme_path = os.path.join(out_dir, 'README.md')
    with open(readme_path,'w',encoding='utf-8') as f:
        f.write(readme)
    return readme_path

# ---------- 主流程 ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True)
    ap.add_argument("--workspace", default=None, help="工作区目录(默认取当前agent的workspace)")
    ap.add_argument("--out", required=True, help="档案输出目录(私人库克隆目录)")
    ap.add_argument("--slug", help="可选覆盖文件夹名")
    ap.add_argument("--device", help="设备名;缺省自动检测")
    ap.add_argument("--index", default="archive_index.json", help="索引文件名/路径")
    ap.add_argument("--adapter", help="强制指定适配器名(minis/codex/claude/generic)")
    args = ap.parse_args()

    sid = args.id
    # 解析工作区: 用户未显式指定时取当前agent的workspace
    ws = args.workspace or get_adapter().workspace()
    args.workspace = ws
    session = get_session(sid)
    if not session or not session.get('ok'):
        print("[错误] 无法读取会话元信息", file=sys.stderr); sys.exit(1)
    data = session.get('data', {})
    msgs = data.get('messages', [])
    meta_info = get_session_meta(sid)
    real_title = meta_info.get('title') or data.get('title') or (msgs[0]['text'][:40] if msgs else 'untitled')
    started_at = meta_info.get('started_at') or data.get('started_at')
    device = args.device or get_device()

    index_path = args.index if os.path.isabs(args.index) else os.path.join(args.out, args.index)
    index = load_index(index_path)
    existing = index.get(sid)

    # 计算目标文件夹名
    if args.slug:
        folder = sanitize_dirname(args.slug); title = args.slug
    else:
        title = real_title
        folder = build_folder_name(real_title, started_at, device)
    session_dir = os.path.join(args.out, folder)
    # 本地的项目文件夹 = workspace/<标题>/ (精确收集产物源)
    project_dir = os.path.join(args.workspace, title)

    renamed = False
    old_title = None
    # ---- 标题联动改名 + 记录别名 ----
    if existing:
        old_title = existing.get('current_title') or existing.get('title')
        old_folder = existing.get('folder')
        if old_folder and old_folder != folder:
            old_dir = os.path.join(args.out, old_folder)
            if os.path.isdir(old_dir) and not os.path.isdir(session_dir):
                try:
                    r1 = subprocess.run(["git","rm","-r","--quiet",old_folder], cwd=args.out, capture_output=True, text=True)
                    r2 = subprocess.run(["git","mv","--quiet",old_folder,folder], cwd=args.out, capture_output=True, text=True)
                    if not os.path.isdir(session_dir):
                        os.rename(old_dir, session_dir)
                    print(f"[改名] 会话标题变更: '{old_folder}' -> '{folder}'")
                    renamed = True
                    # 更新 conversation.md 里的标题行
                    cvp = os.path.join(session_dir,'conversation.md')
                    if os.path.isfile(cvp):
                        with open(cvp,encoding='utf-8') as f: c = f.read()
                        with open(cvp,'w',encoding='utf-8') as f:
                            f.write(c.replace(old_title or existing['folder'], title, 1))
                except Exception as e:
                    print(f"[警告] 改名失败: {e}", file=sys.stderr)

    files_dir = os.path.join(session_dir, 'files')
    os.makedirs(files_dir, exist_ok=True)

    # 写对话文件(新会话才写;已存在且只改名的跳过)
    cvpath = os.path.join(session_dir,'conversation.md')
    if not os.path.isfile(cvpath):
        with open(cvpath,'w',encoding='utf-8') as f:
            f.write(build_conversation_md(msgs, title, sid, started_at))

    # 产物
    copied = collect_workspace_files(args.workspace, project_dir, session_dir)

    # meta.json(含别名链)
    meta = {
        "session_id": sid,
        "current_title": title,
        "started_at": started_at,
        "device": device,
        "project_dir": f"{title}/",
        "total_messages": data.get('total', len(msgs)),
        "archived_at": datetime.datetime.now().isoformat(timespec='seconds'),
        "collected_files": copied,
    }
    with open(os.path.join(session_dir,'meta.json'),'w',encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    # 更新索引(含别名链)
    index[sid] = {
        "folder": folder,
        "current_title": title,
        "started_at": started_at,
        "device": device,
        "aliases": existing.get('aliases', []) if existing else [],
    }
    if renamed:
        append_alias(sid, index, title, old_title)
    save_index(index_path, index)

    # 总览 README
    build_readme(args.out, index)

    print(f"[完成] 已存档: {session_dir}")
    print(f"  文件夹名: {folder}")
    print(f"  标题: {title} | 开始时间: {started_at}")
    print(f"  消息数: {meta['total_messages']} | 产物: {len(copied)}")
    if renamed:
        print(f"  ↳ 别名已记录: {index[sid]['aliases']}")

if __name__ == '__main__':
    main()
