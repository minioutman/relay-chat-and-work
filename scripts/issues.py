#!/usr/bin/env python3
"""
relay-chat-and-work: 项目记录管理器(想法/问题/Bug/待办/决策)
维护存到私人库的行为 ISSUES.md 的活日志。

命令:
  issues.py add --type <idea|question|bug|todo|decision> --title "<内容>" [--file <path>]
  issues.py list [--file <path>]
  issues.py resolve --index <n> --title "<解决说明>" [--file <path>]        # 移到已解决
  issues.py delete --index <n> [--file <path>]                              # 彻底删除
  issues.py init [--file <path>]                                            # 若不存在则创建

状态类型:
  idea(想法) question(问题) bug(Bug) todo(待办) decision(决策)
"""
import json, sys, os, argparse, datetime

TYPES = {
    'idea': 'idea', 'question': 'q', 'bug': 'bug',
    'todo': 'todo', 'decision': 'dec',
}
TYPE_CN = {'idea':'想法','question':'问题','bug':'Bug','todo':'待办','decision':'决策'}

DEFAULT_TEMPLATE = """# 项目记录 (想法 / 问题 / Bug / 待办 / 决策)

> 自动维护 · 解决后移入「已解决」区,保留历史。

## 🔴 待解决

<!-- 格式: [-idea] 日期 内容 / [-bug] 日期 内容 / [-todo] 日期 内容 -->
- [todo] {date} 初始化项目记录

## ✅ 已解决
"""

def today():
    return datetime.date.today().isoformat()

def ensure_file(path):
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
        with open(path,'w',encoding='utf-8') as f:
            f.write(DEFAULT_TEMPLATE.replace('{date}', today()))
        return True
    return False

def parse_issues(path):
    """解析 ISSUES.md -> {todo: [], done: []},每项为 dict(type,date,text,raw)。"""
    result = {'todo': [], 'done': []}
    if not os.path.exists(path): return result
    with open(path, encoding='utf-8') as f:
        lines = f.readlines()
    current = None
    import re
    for line in lines:
        ls = line.strip()
        if ls.startswith('# 🔴') or ls == '## 🔴 待解决':
            current = 'todo'; continue
        if ls.startswith('# ✅') or ls == '## ✅ 已解决' or ls == '## ✅ 已解决 ':
            current = 'done'; continue
        m = re.match(r'- \[(idea|q|bug|todo|dec)\]\s*(.*)', ls)
        if m and current:
            ty, rest = m.group(1), m.group(2)
            result[current].append({'type':ty, 'text':rest, 'raw':ls, 'line':line})
    return result

def add(path, type_, text):
    t = TYPES.get(type_, 'todo')
    ensure_file(path)
    with open(path, encoding='utf-8') as f: lines = f.readlines()
    # 在 "## ✅ 已解决" 之前插入
    done_i = None
    for i, ln in enumerate(lines):
        if ln.strip().startswith('## ✅'):
            done_i = i; break
    if done_i is None:
        lines.append(f"- [{t}] {today()} {text}\n")
    else:
        lines.insert(done_i, f"- [{t}] {today()} {text}\n")
    with open(path,'w',encoding='utf-8') as f:
        f.writelines(lines)
    print(f"[add] 已记录 [{type_}]: {text}")
    return True

def resolve(path, index, note=''):
    issues = parse_issues(path)
    if index < 1 or index > len(issues['todo']):
        print(f"[错误] 无第 {index} 条待解决记录", file=sys.stderr); return False
    item = issues['todo'][index-1]
    with open(path, encoding='utf-8') as f: lines = f.readlines()
    # 找到该行并从 todo 移除
    for i, ln in enumerate(lines):
        if ln == item['line']:
            del lines[i]; break
    # 追加到已解决区
    note_s = f" — {note}" if note else ""
    done_i = len(lines)
    for i, ln in enumerate(lines):
        if ln.strip().startswith('## ✅'):
            done_i = i; break
    lines.insert(done_i+1, f"- [resolved:{item['type']}] {today()} {item['text']}{note_s}\n")
    with open(path,'w',encoding='utf-8') as f:
        f.writelines(lines)
    print(f"[resolve] 已解决并移入已解决区")
    return True

def delete(path, index):
    issues = parse_issues(path)
    all_items = issues['todo'] + issues['done']
    if index < 1 or index > len(all_items):
        print(f"[错误] 无第 {index} 条记录", file=sys.stderr); return False
    item = all_items[index-1]
    with open(path, encoding='utf-8') as f: lines = f.readlines()
    for i, ln in enumerate(lines):
        if ln == item['line']:
            del lines[i]; break
    with open(path,'w',encoding='utf-8') as f:
        f.writelines(lines)
    print(f"[delete] 已删除记录")
    return True

def list_issues(path):
    issues = parse_issues(path)
    print(f"=== 待解决 ({len(issues['todo'])}) ===")
    for i, it in enumerate(issues['todo'], 1):
        print(f"  {i}. [{it['type']}] {it['line'].strip()}")
    print(f"=== 已解决 ({len(issues['done'])}) ===")
    for i, it in enumerate(issues['done'], 1):
        print(f"  {i}. [{it['type']}] {it['line'].strip()}")

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd')
    p_add = sub.add_parser('add'); p_add.add_argument('--type', choices=TYPES, default='idea')
    p_add.add_argument('--title', required=True); p_add.add_argument('--file')
    p_list = sub.add_parser('list'); p_list.add_argument('--file')
    p_res = sub.add_parser('resolve'); p_res.add_argument('--index', type=int, required=True)
    p_res.add_argument('--note', default=''); p_res.add_argument('--file')
    p_del = sub.add_parser('delete'); p_del.add_argument('--index', type=int, required=True)
    p_del.add_argument('--file')
    p_init = sub.add_parser('init'); p_init.add_argument('--file')
    args = ap.parse_args()

    default_file = os.environ.get('ISSUES_FILE', 'ISSUES.md')
    if args.cmd == 'add':
        f = args.file or default_file; add(f, args.type, args.title)
    elif args.cmd == 'list':
        f = args.file or default_file; list_issues(f)
    elif args.cmd == 'resolve':
        f = args.file or default_file; resolve(f, args.index, args.note)
    elif args.cmd == 'delete':
        f = args.file or default_file; delete(f, args.index)
    elif args.cmd == 'init':
        f = args.file or default_file; ensure_file(f); print(f"[init] {f} 就绪")
    else:
        ap.print_help()

if __name__ == '__main__':
    main()
