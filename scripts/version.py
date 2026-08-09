#!/usr/bin/env python3
"""
__version__ = "2.1.0"

relay-chat-and-work 版本管理器
统一版本号到: SKILL.md frontmatter + 各脚本 __version__ + CHANGELOG.md + git tag

用法:
  version.py --set <版本> [--changelog "<改了什么>"] [--tag-only] [--push]

示例:
  python3 version.py --set 2.1.0 --changelog "新增跨agent适配层,修复产物串台"
"""
import os, re, sys, subprocess, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # skill根目录
SKILL = os.path.join(ROOT, "SKILL.md")
SCRIPTS = os.path.join(ROOT, "scripts")
CHANGELOG = os.path.join(ROOT, "CHANGELOG.md")
VERSION_RE = re.compile(r'^\s*__version__\s*=\s*["\']([^"\']+)["\']', re.M)
SKILL_VER_RE = re.compile(r'^(\s*version:\s*)([\d.]+)$', re.M)

def get_current():
    with open(SKILL, encoding='utf-8') as f:
        m = SKILL_VER_RE.search(f.read())
    return m.group(2).strip() if m else None

def set_skill_version(version):
    with open(SKILL, encoding='utf-8') as f: c = f.read()
    c2 = SKILL_VER_RE.sub(lambda m: m.group(1) + version, c, count=1)
    with open(SKILL, 'w', encoding='utf-8') as f: f.write(c2)

def _iter_py_files():
    for root, dirs, files in os.walk(SCRIPTS):
        if '.git' in dirs: dirs.remove('.git')
        for f in files:
            if f.endswith('.py'):
                yield os.path.join(root, f)

def set_script_versions(version):
    for p in _iter_py_files():
        with open(p, encoding='utf-8') as fh: c = fh.read()
        if not VERSION_RE.search(c):
            c = c.replace('\n"""\n', '\n"""\n__version__ = "' + version + '"\n\n', 1) \
                 if '\n"""\n' in c else ('__version__ = "' + version + '"\n\n' + c)
        else:
            c = VERSION_RE.sub('__version__ = "' + version + '"', c, count=1)
        with open(p, 'w', encoding='utf-8') as fh: fh.write(c)

def update_changelog(version, note, date):
    entry = f"## [{version}] - {date}\n\n{note}\n\n"
    if os.path.exists(CHANGELOG):
        # 在标题(若有)后插入最新条目
        with open(CHANGELOG, encoding='utf-8') as f: c = f.read()
        if c.startswith('#') and '\n' in c:
            head, _, rest = c.partition('\n')
            c = head + '\n\n' + entry + rest.lstrip('\n')
        else:
            c = entry + c
    else:
        c = f"# Changelog\n\n{entry}"
    with open(CHANGELOG, 'w', encoding='utf-8') as f: f.write(c)

def git(op, target_dir=ROOT, *args):
    subprocess.run(["git", op, *args], cwd=target_dir, capture_output=True, text=True)

def main():
    args = sys.argv[1:]
    if "--set" not in args:
        print(f"当前版本: {get_current() or '未识别'}")
        print("用法: version.py --set <版本> [--changelog \"说明\" ] [--push]")
        return
    ver = args[args.index("--set")+1]
    note = args[args.index("--changelog")+1] if "--changelog" in args else "版本更新"
    do_push = "--push" in args
    date = datetime.date.today().isoformat()

    set_skill_version(ver)
    set_script_versions(ver)
    update_changelog(ver, note, date)
    print(f"[版本] 已同步到 v{ver}:")

    # 若在 git 仓库
    if os.path.isdir(os.path.join(ROOT, ".git")):
        git("add", ROOT, "-A")
        git("commit", ROOT, "-m", f"v{ver}: {note}")
        git("tag", ROOT, f"v{ver}")
        print(f"  - commit + tag v{ver}")
        if do_push:
            git("push", ROOT, "origin", "--tags")
            print("  - 已推送到 origin --tags")
    print("  已完成。")

if __name__ == '__main__':
    main()
