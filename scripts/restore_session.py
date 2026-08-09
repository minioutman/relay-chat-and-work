#!/usr/bin/env python3
"""
__version__ = "2.1.0"

relay-chat-and-work: 加载/恢复到本地功能
把私人库存档的会话恢复回本地: 离线查看(A) + 产物(B) + 对话文本(C) + 会话续聊(D)。

用法:
  restore_session.py --query <标题/别名/关键词>
  restore_session.py --id <session_id>
  restore_session.py --folder <存档文件夹名>

可选:
  --workspace /var/minis/workspace   产物恢复目录(默认)
  --resume                           找到后自动用 session_id 触发续聊 (D2)
  --resume-text "续聊指令"            自定义续聊话语(默认"继续")
"""
import json, subprocess, sys, os, shutil, argparse, datetime

# 适配器层: 动态选择当前 agent
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from adapters import minis, claude, codex, generic  # noqa: F401
import adapters.base as abase

def get_adapter():
    return abase.active_adapter()
# ---------- 工具 ----------
def pull_repo(out_dir):
    """同步私人库最新状态(git pull)。"""
    if not os.path.isdir(os.path.join(out_dir, '.git')):
        print(f"[提示] {out_dir} 不是 git 仓库,尝试 pull...", file=sys.stderr)
        try:
            subprocess.run(["git","pull","--rebase"], cwd=out_dir,
                           capture_output=True, text=True, timeout=120)
        except Exception:
            pass
    else:
        r = subprocess.run(["git","pull","--rebase"], cwd=out_dir,
                           capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            print(f"[警告] git pull 失败: {r.stderr[:300]}", file=sys.stderr)

def load_index(index_path):
    try:
        with open(index_path,'r',encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def list_archive_dirs(out_dir):
    """列出所有存档文件夹(形如 标题_时间_设备)。"""
    if not os.path.isdir(out_dir): return []
    return [d for d in os.listdir(out_dir)
            if os.path.isdir(os.path.join(out_dir,d)) and not d.startswith('.')]

# ---------- 定位会话 ----------
def find_sessions(out_dir, index, query, sid=None, folder=None):
    """返回匹配的会话信息列表: {'session_id','folder','title','started_at','device'}"""
    results = []
    # 1. 从索引精确匹配(session_id)
    if sid and sid in index:
        e = index[sid]
        results.append({**e, "session_id": sid})
        return results
    # 2. 从索引按当前标题/别名匹配
    if query:
        q = query.lower().strip()
        for sid, e in index.items():
            titles = [e.get('current_title',''), e.get('title','')] + list(e.get('aliases',[]))
            if any(q in (t or '').lower() for t in titles):
                results.append({**e, "session_id": sid})
        if results:
            return results
    # 3. 从文件夹名匹配
    if query or folder:
        q = (query or folder).lower().strip()
        for d in list_archive_dirs(out_dir):
            if q in d.lower():
                meta = os.path.join(out_dir, d, 'meta.json')
                e = {'folder': d}
                if os.path.isfile(meta):
                    try:
                        with open(meta, encoding='utf-8') as f:
                            e.update(json.load(f))
                    except Exception:
                        pass
                results.append(e)
    return results

# ---------- 恢复产物 + 文本 (B/C) ----------
def restore_artifacts(session_dir, title, workspace_dir):
    """把存档 files/ 恢复到 workspace/<标题>/,conversation.md 也复制过去。"""
    restored = []
    if not workspace_dir: return restored
    project_dir = os.path.join(workspace_dir, title or 'restored')
    os.makedirs(project_dir, exist_ok=True)
    # 复制 files/
    files_src = os.path.join(session_dir, 'files')
    if os.path.isdir(files_src):
        for root, _, files in os.walk(files_src):
            for f in files:
                src = os.path.join(root, f)
                rel = os.path.relpath(src, files_src)
                dst = os.path.join(project_dir, rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
                restored.append(rel)
    # 复制 conversation.md
    cv = os.path.join(session_dir, 'conversation.md')
    if os.path.isfile(cv):
        dst_cv = os.path.join(project_dir, 'conversation.md')
        shutil.copy2(cv, dst_cv)
        restored.append('conversation.md')
    # 复制 ISSUES.md(项目记录,联动)
    issues_src = os.path.join(session_dir, 'ISSUES.md')
    if os.path.isfile(issues_src):
        dst_is = os.path.join(project_dir, 'ISSUES.md')
        shutil.copy2(issues_src, dst_is)
        restored.append('ISSUES.md')
    return restored, project_dir

# ---------- 会话续聊 (D2) ----------
def resume_session(session_id, resume_text):
    """用适配器触发续聊。Minis 走 send --session;其他环境走各自适配器。"""
    if not session_id: return False, "无 session_id"
    text = resume_text or "继续上次的工作,先回顾一下我们做到哪了,再接着做。"
    try:
        a = get_adapter()
        ok, msg = a.resume(session_id, text)
        if ok:
            return True, f"[{a.name}] {msg}"
        return ok, f"[{a.name}] {msg}"
    except Exception as e:
        return False, f"续聊调用失败: {e}"

# ---------- 主流程 ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", help="按标题/别名/关键词检索")
    ap.add_argument("--id", help="按 session_id 精确指定")
    ap.add_argument("--folder", help="按存档文件夹名精确指定")
    ap.add_argument("--out", default=None,
                    help="私人库本地同步目录(默认缓存目录)")
    ap.add_argument("--archive-repo", help="私人库 git 地址(若需首次 clone)")
    ap.add_argument("--workspace", default=None, help="产物恢复目录")
    ap.add_argument("--resume", action="store_true", help="找到后自动触发续聊(D2)")
    ap.add_argument("--resume-text", help="自定义续聊话语")
    ap.add_argument("--adapter", help="强制指定适配器(minis/codex/claude/generic),测试用")
    args = ap.parse_args()
    if args.adapter:
        os.environ["RELAY_ADAPTER"] = args.adapter
    # 未显式指定时,取当前 agent 的 workspace
    if not args.workspace:
        args.workspace = get_adapter().workspace()

    if not (args.query or args.id or args.folder):
        print("[错误] 必须提供 --query / --id / --folder 之一", file=sys.stderr); sys.exit(1)

    out_dir = args.out
    # 首次:如果目录不存在且给了仓库地址,则 clone
    if not os.path.isdir(out_dir) and args.archive_repo:
        os.makedirs(os.path.dirname(out_dir), exist_ok=True)
        r = subprocess.run(["git","clone",args.archive_repo,out_dir],
                           capture_output=True, text=True, timeout=180)
        if r.returncode!=0:
            print(f"[错误] clone 失败: {r.stderr[:300]}", file=sys.stderr); sys.exit(1)
        print(f"[clone] 已克隆私人库到 {out_dir}")
    if not os.path.isdir(os.path.join(out_dir,'.git')):
        print(f"[错误] {out_dir} 不是 git 仓库;请先 --archive-repo 提供私人库地址",
              file=sys.stderr); sys.exit(1)

    # 1. 同步
    pull_repo(out_dir)
    # 2. 定位
    index = load_index(os.path.join(out_dir,'archive_index.json'))
    matches = find_sessions(out_dir, index, args.query, args.id, args.folder)

    if not matches:
        print("[未找到] 没有匹配的会话。可用 --folder 精确指定。", file=sys.stderr)
        print("现有存档文件夹:")
        for d in list_archive_dirs(out_dir): print("  ", d)
        sys.exit(1)
    if len(matches) > 1:
        print("[模糊] 找到多个匹配:")
        for i,m in enumerate(matches):
            print(f"  {i+1}. {m.get('current_title') or m.get('title','')} | {m.get('started_at','')} | {m.get('folder','')} | {m.get('session_id','')}")
        print("请用 --folder 或 --id 精确指定。", file=sys.stderr)
        sys.exit(1)

    m = matches[0]
    title = m.get('current_title') or m.get('title') or m.get('folder','')
    folder = m.get('folder') or title
    sid = m.get('session_id')
    session_dir = os.path.join(out_dir, folder)

    print(f"[定位] 会话: {title}")
    print(f"  存档文件夹: {folder}")
    print(f"  session_id: {sid}")
    print(f"  开始时间: {m.get('started_at','?')} | 设备: {m.get('device','?')}")

    # B+C 恢复产物与文本
    if os.path.isdir(session_dir):
        restored, project_dir = restore_artifacts(session_dir, title, args.workspace)
        print(f"[恢复] 产物/文本已恢复到 {project_dir} ({len(restored)} 项)")
        for r_ in restored: print(f"    - {r_}")
    else:
        restored = []
        print(f"[提示] 存档目录不存在: {session_dir}", file=sys.stderr)

    # ISSUES 联动提示:恢复出待解决项时,提醒新环境处理
    issues_path = os.path.join(args.workspace, title, 'ISSUES.md')
    if os.path.isfile(issues_path):
        todo_n = 0
        try:
            with open(issues_path, encoding='utf-8') as f:
                content = f.read()
            import re
            m = re.search(r'##\s*🔴.*?(?=##\s*✅|$)', content, re.S)
            if m:
                todo_n = len(re.findall(r'- \[(idea|q|bug|todo|dec)\]', m.group(0)))
            print(f"[提示] ISSUES.md 有 {todo_n} 条待解决(想法/问题/Bug/待办)。")
            print(f"       下一客户端(AI)将提示是否处理,解决后移入「已解决」区。")
        except Exception:
            pass
    else:
        print("[提示] 该项目无 ISSUES.md (未启用项目记录)。")

    # D2 续聊
    if args.resume:
        ok, msg = resume_session(sid, args.resume_text)
        status = "成功" if ok else "失败"
        print(f"[续聊] {status}: {msg}")
        if not ok:
            print("  提示: 可直接手动打开该会话查看。session_id =", sid)

    # 按当前 adapter 给下一步指引
    a = get_adapter()
    if a.name == "minis":
        print("\n[完成] 已在本地恢复。如需在 Minis 打开会话:`minis-sessions-cli open " + (sid or "") + "`")
    else:
        print("\n[完成] 已在本地恢复为纯 Markdown。")
        print("       当前环境无 Minis 续聊;请让当前 AI 阅读 PROJECT 下的")
        print("       conversation.md / ISSUES.md 即可接续先前工作。")
        issues_local = os.path.join(args.workspace, title, 'ISSUES.md')
        if os.path.isfile(issues_local):
            print("       提示: 有待解决项可先处理(见 ISSUES.md)。")

if __name__ == '__main__':
    main()
