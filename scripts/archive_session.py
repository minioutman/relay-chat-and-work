#!/usr/bin/env python3
"""
relay-chat-and-work: 对话存档脚本
把指定会话导出为 conversation.md + 收集产物文件 + 写 meta.json
用法:
  archive_session.py --id <session_id> [--workspace <dir>] [--slug <name>]
"""
import json, subprocess, sys, os, datetime, shutil, argparse

def get_session(sid):
    try:
        out = subprocess.run(
            ["minis-sessions-cli","messages","--id",sid,"--full"],
            capture_output=True, text=True, timeout=60)
        return json.loads(out.stdout)
    except Exception as e:
        print(f"[错误] 拉取会话 {sid} 失败: {e}", file=sys.stderr)
        return None

def sanitize_dirname(name):
    name = (name or "").strip().replace("/","_").replace("\\","_")
    name = name.replace(":","_").replace("*","_").replace("?","_")
    name = name.replace('"',"_").replace("<","_").replace(">","_").replace("|","_")
    name = name.strip(". ")
    return name or "untitled-session"

def collect_workspace_files(workspace_dir, sid, out_dir, exclude_dirs=()):
    """收集 workspace 中跟此会话可能相关的产物文件。
    排除: 隐藏目录、存档输出目录(out_dir)、技能源码仓库、以及手动指定的 exclude_dirs。
    用相对 workspace 的路径在 files/ 下创建镜像结构。"""
    if not workspace_dir or not os.path.isdir(workspace_dir):
        return []
    copied = []
    exts = ('.py','.sh','.md','.json','.csv','.png','.jpg','.html','.js','.ts','.txt','.log')
    base = os.path.abspath(workspace_dir)
    out_abs = os.path.abspath(out_dir)
    # 构建需要排除的目录名集合(源码库名 + 存档输出名)
    excl_names = set()
    for d in list(exclude_dirs) + [out_dir]:
        n = os.path.basename(os.path.normpath(d))
        if n: excl_names.add(n)
    excl_names.update({'relay-work-repo','relay-chat-and-work-repo','chatarchive-work'})
    for root, dirs, files in os.walk(workspace_dir):
        # 剪枝:排除隐藏目录、输出目录自身、源码库
        dirs[:] = [d for d in dirs
                   if not d.startswith('.')
                   and os.path.abspath(os.path.join(root,d)) != out_abs
                   and d not in excl_names]
        for f in files:
            if f.startswith('.'): continue
            if not f.endswith(exts): continue
            src = os.path.join(root, f)
            # 跳过输出目录里的文件(即使已进入 walk)
            if os.path.abspath(src).startswith(out_abs + os.sep): continue
            rel = os.path.relpath(src, base)
            if rel.startswith('..'): continue  # 只收 workspace 内部的
            dst = os.path.join(out_dir, 'files', rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            try:
                shutil.copy2(src, dst)
                copied.append(rel)
            except Exception:
                pass
    return copied

def build_conversation_md(msgs):
    lines = []
    for m in msgs:
        role = m.get('role','?')
        text = m.get('text','')
        ts = m.get('created_at','')
        tag = '👤 用户' if role=='user' else ('🤖 AI' if role=='assistant' else f'🔧 {role}')
        lines.append(f"## {tag}  |  {ts}\n\n{text}\n")
    return "\n".join(lines)

def get_session_meta(sid):
    """从 list 接口拿到会话的真实标题和开始时间(文件命名用)。"""
    try:
        out = subprocess.run(
            ["minis-sessions-cli","list","--limit","100"],
            capture_output=True, text=True, timeout=60)
        d = json.loads(out.stdout)
        for s in d.get('data',{}).get('sessions',[]):
            if s.get('session_id') == sid:
                return {'title': s.get('title'), 'started_at': s.get('started_at')}
    except Exception:
        pass
    return {}

def build_folder_name(title, started_at):
    """文件夹名 = 真实标题 + 会话开始时间,便于区分同名会话。
    例: 如何创建自定义技能_2026-08-09_0148"""
    # 规范化时间 "2026-08-09 01:48" -> "2026-08-09_0148"
    ts = ''
    if started_at:
        t = started_at.strip().replace(' ','_')
        t = t.replace(':','').replace('/','_')
        # 去掉秒等,只留 年月日_时分
        import re
        mm = re.match(r'(\d{4})[_\-](\d{2})[_\-](\d{2})[_\-](\d{2})(\d{2})?', t)
        if mm:
            y,mo,d,h,mi = mm.groups()
            ts = f"{y}-{mo}-{d}_{h or '00'}{mi or '00'}"
        else:
            ts = sanitize_dirname(started_at)
    base = sanitize_dirname(title)
    return f"{base}_{ts}" if ts else base

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True)
    ap.add_argument("--workspace", default="/var/minis/workspace")
    ap.add_argument("--out", required=True, help="输出目录(含会话文件夹)")
    ap.add_argument("--slug", help="可选: 覆盖文件夹名(仅当不想用真实标题时)")
    args = ap.parse_args()

    sid = args.id
    session = get_session(sid)
    if not session or not session.get('ok'):
        print("[错误] 无法读取会话元信息", file=sys.stderr); sys.exit(1)

    data = session.get('data', {})
    msgs = data.get('messages', [])
    # 从 list 拿真实标题 + 开始时间
    meta_info = get_session_meta(sid)
    real_title = meta_info.get('title') or data.get('title') or (msgs[0]['text'][:40] if msgs else 'untitled')
    started_at = meta_info.get('started_at') or data.get('started_at')

    # 文件夹名: 真实标题 + 开始时间;除非显式传 --slug
    if args.slug:
        folder = sanitize_dirname(args.slug)
        title = args.slug
    else:
        title = real_title
        folder = build_folder_name(real_title, started_at)

    # 目标文件夹
    session_dir = os.path.join(args.out, folder)
    files_dir = os.path.join(session_dir, 'files')
    os.makedirs(files_dir, exist_ok=True)

    # 1. 对话 md
    conv_md = build_conversation_md(msgs)
    with open(os.path.join(session_dir,'conversation.md'),'w',encoding='utf-8') as f:
        f.write(f"# {title}\n\n> 自动存档 | 会话ID: {sid} | 开始时间: {started_at or '未知'}\n\n")
        f.write(conv_md)

    # 2. 产物文件
    copied = collect_workspace_files(args.workspace, sid, session_dir)

    # 3. meta.json
    meta = {
        "session_id": sid,
        "title": title,
        "started_at": started_at,
        "total_messages": data.get('total', len(msgs)),
        "archived_at": datetime.datetime.now().isoformat(timespec='seconds'),
        "collected_files": copied,
    }
    with open(os.path.join(session_dir,'meta.json'),'w',encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"[完成] 已存档: {session_dir}")
    print(f"  文件夹名: {folder}")
    print(f"  标题: {title} | 开始时间: {started_at}")
    print(f"  消息数: {meta['total_messages']}")
    print(f"  收集产物文件: {len(copied)}")

if __name__ == '__main__':
    main()
