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

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True)
    ap.add_argument("--workspace", default="/var/minis/workspace")
    ap.add_argument("--out", required=True, help="输出目录(含会话文件夹)")
    ap.add_argument("--slug", help="文件夹名;缺省用会话标题")
    args = ap.parse_args()

    sid = args.id
    session = get_session(sid)
    if not session or not session.get('ok'):
        print("[错误] 无法读取会话元信息", file=sys.stderr); sys.exit(1)

    data = session.get('data', {})
    msgs = data.get('messages', [])
    # 标题:优先列表里的 title,否则用第一条消息
    title = args.slug or data.get('title') or (msgs[0]['text'][:40] if msgs else 'untitled')
    folder = sanitize_dirname(title if args.slug else data.get('title'))

    # 目标文件夹
    session_dir = os.path.join(args.out, folder)
    files_dir = os.path.join(session_dir, 'files')
    os.makedirs(files_dir, exist_ok=True)

    # 1. 对话 md
    conv_md = build_conversation_md(msgs)
    with open(os.path.join(session_dir,'conversation.md'),'w',encoding='utf-8') as f:
        f.write(f"# {title}\n\n> 自动存档 | 会话ID: {sid}\n\n")
        f.write(conv_md)

    # 2. 产物文件
    copied = collect_workspace_files(args.workspace, sid, session_dir)

    # 3. meta.json
    meta = {
        "session_id": sid,
        "title": title,
        "started_at": data.get('started_at'),
        "total_messages": data.get('total', len(msgs)),
        "archived_at": datetime.datetime.now().isoformat(timespec='seconds'),
        "collected_files": copied,
    }
    with open(os.path.join(session_dir,'meta.json'),'w',encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"[完成] 已存档: {session_dir}")
    print(f"  文件夹名: {folder}")
    print(f"  消息数: {meta['total_messages']}")
    print(f"  收集产物文件: {len(copied)}")

if __name__ == '__main__':
    main()
