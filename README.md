# relay-chat-and-work — 接力干活 + 自动存档对话

> Relay your long tasks AND auto-archive your chats. Split work into stages, progress step-by-step, persist to disk, resume across sessions — all while silently backing up each finished conversation (and its files) to your private GitHub repo.

---

## 🇬🇧 English

**relay-chat-and-work** is a single skill for AI agents (Claude Code, Minis, Codex, Gemini CLI — anything that supports Agent Skills) that does two things:

1. **Relay long tasks** — split work into numbered stages, persist progress to disk, and resume across sessions on any device.
2. **Auto-archive chats** — when a new conversation opens, silently back up the previous session (full transcript + generated files) to your **private GitHub repo**, organized by conversation title.

It is **client-agnostic**: everything is plain Markdown, so you can start a task in one agent and continue it in another without losing context. Comes with a cross-agent adapter layer (`scripts/adapters/`) and an `ISSUES.md` project log for tracking open tasks/decisions across sessions.

**Install:**
```bash
# Copy the whole relay-chat-and-work/ folder into your skills directory.
# e.g. Claude Code: ~/.claude/skills/  ·  Codex: ~/.agents/skills/
```

**Do I need a GitHub token?**
- **No, not always.** The core **relay-work** feature (staging, progress on disk, cross-session resume), ISSUES tracking, and local archiving all work purely on local files — no token required.
- **Only the "auto-archive to your private GitHub repo" step needs a token**, because it `git push`es to GitHub. Set the **`GITHUB_TOKEN`** env var to enable that. Without it, the skill still works for everything local, but the remote backup step will error out.

> **Local ≠ relay.** Relay work (picking up a half-finished task) already runs 100% locally — the GitHub archive is only an *optional* cross-device / cross-client backup of your full conversation history. If you never switch devices or clients, local-only is fine; GitHub adds the power to restore everything from anywhere.

**Quick usage:**
- **Relay work** — tell your agent: *"接力干活"* / *"split this into stages"* — it stages, persists progress, and resumes later.
- **Auto-archive** — nothing to say; it silently archives the previous session on the next new chat.

---

## 中文

一个给 AI 助手(Claude / Minis / Codex 等支持 skills 的 Agent)用的**一体化长任务技能**。它把两件事合二为一:

1. **接力干活**(Rely Work)—— 长任务拆阶段、落盘、跨会话续接
2. **对话自动存档**(Auto-Archive)—— 每次新对话打开,自动把上一轮会话(对话全文 + 产物文件)静默备份到你的**私人 GitHub 仓库**

## 它解决什么问题

长任务一次做不完,会话一断上下文就丢;而且时间一长,有价值的对话散落各处、找不到也续不上。

`relay-chat-and-work` 用**进度落盘**让长活能接力;用**自动存档**让每次对话都能永久、分类地保存到你的私人仓库,按对话标题归档,随时可回溯、可续接。

## 核心机制

| 能力 | 说明 |
|------|------|
| 接力干活 | 拆阶段 → 落盘 → 跨会话续接 |
| 自动存档 | 新对话打开时静默补存上一轮会话 |
| 按标题归档 | 私人库 `对话标题/` 分组存放 |
| 产物收集 | 会话产生的文件一并入库 |
| 去重 | 已存会话自动跳过 |

## 私人存档仓库

存储目标: **`<你的GitHub用户名>-chat-and-work`**(private)

例如账号是 `minioutman`,则私人库为 `minioutman/minioutman-chat-and-work`。每个对话 → `仓库/<对话标题>/`:

```
<对话标题>/
├── conversation.md   ← 完整对话
├── meta.json         ← 会话元信息
└── files/            ← 该会话产生的产物文件
```

## 安装

把 `relay-chat-and-work/` 整个目录放进你的 skills 目录。对 Minis 用户:设置 → Skills → 导入。

## 需要 GitHub token 吗?

**不一定。** 分两种情况:

- **接力干活**(拆阶段、进度落盘、跨会话续接)、**ISSUES 记录**、**本地存档** —— 全部只依赖本地文件,**不需要 token**。
- 只有**「自动存档到私人 GitHub 仓库」**这一步需要 token,因为它要 `git push` 到 GitHub。设置环境变量 **`GITHUB_TOKEN`** 即可开启该功能;不设也能用其余所有本地功能,但远程备份那一步会报错。

所以:**只想接力干活→不用 token;想自动备份对话到私人库→需要 token。**

> **本地≠接力。** 接力干活(接着上次没做完的活)**本来就在本地运行**,和 GitHub 无关;GitHub 存档只是对你**完整对话历史**的*可选*跨设备/跨客户端备份。如果你一直只在同一台设备、同一个客户端用,纯本地就够了;接 GitHub 的价值在于——无论换到哪台设备、哪个客户端,一条 `git clone` 就能把所有对话全找回来。

## 用法

**接力干活** —— 对 AI 说:「接力干活」「拆成步骤」「先做xx再做xx」…
**自动存档** —— 无需说话,新对话打开自动静默执行。

## 目录结构

```
relay-chat-and-work/
├── SKILL.md                   # 主文件:触发 + 规则
├── scripts/
│   └── archive_session.py     # 会话存档工具脚本
└── references/
    └── protocol.md            # 进度文件规范
```

## License

MIT
