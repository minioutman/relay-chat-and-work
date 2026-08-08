#!/usr/bin/env python3
"""环境检测工具:列出当前环境的 agent 适配器,供脚本交互选择。
用法:
  python3 env_detect.py          → 检测当前环境
  python3 env_detect.py --list   → 列出全部可用适配器
  python3 env_detect.py --adapter <name>   → 打印指定适配器的能力
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入所有适配器注册进 registry
from adapters import minis, claude, codex, generic  # noqa
from adapters.base import _registry, active_adapter

def main():
    args = sys.argv[1:]
    if "--list" in args:
        print("可用适配器:")
        for name, cls in _registry.items():
            try:
                inst = cls()
                print(f"  {name:10} installed={cls.is_installed()} | {inst.describe()}")
            except Exception as e:
                print(f"  {name:10} 加载失败: {e}")
        return
    if "--adapter" in args:
        i = args.index("--adapter")
        name = args[i+1]
        cls = _registry.get(name)
        if not cls:
            print(f"无 {name}", file=sys.stderr); sys.exit(1)
        print(f"{name}: {cls().describe()} installed={cls.is_installed()}")
        return
    # 默认: 检测当前
    a = active_adapter()
    print(f"当前环境适配器: [{a.name}] {a.describe()}")
    print(f"  workspace: {a.workspace()}")
    sess = a.list_sessions(limit=3)
    print(f"  可列出的会话数(限3): {len(sess)}")
    for s in sess[:3]:
        print(f"    - {s.get('title')} | {s.get('last_active')} | {s.get('message_count')}msgs")

if __name__ == '__main__':
    main()
