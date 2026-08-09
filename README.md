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

**Create a least-privilege `GITHUB_TOKEN`:**

Prefer a **fine-grained personal access token** — it scopes access to only the repos you pick.

1. GitHub → Settings → Developer settings → **Personal access tokens → Fine-grained tokens** → **Generate new token**.
2. **Token name**: anything, e.g. `relay-chat-and-work`.
3. **Expiration**: `90 days` or shorter (rotating is safer).
4. **Repository access**: **Only select repositories**, then check:
   - your archive target `https://github.com/<you>/<you>-chat-and-work`
   - and the skill repo itself if your tool needs to push it.
5. Under **Permissions**, set **Contents → Read and write** (the only permission needed to push). Leave everything else at its default.
6. **Generate token** and **copy it immediately** (shown only once).

> If your tool only supports classic tokens: use **Tokens (classic) → Generate** and check **`repo`** (full read/write, needed to push public + private). It's broader than fine-grained, so prefer fine-grained when possible.

Finally, set it as the `GITHUB_TOKEN` environment variable:
```
GITHUB_TOKEN=your_token
```

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

## 如何创建最小权限的 GITHUB_TOKEN

> 直接创建 **fine-grained (细粒度) Personal Access Token** 最安全——它只授权"那几个指定仓库"。

1. 打开 **GitHub → 头像 → Settings → Developer settings → Personal access tokens → Fine-grained tokens**,点 **Generate new token**。
2. **Token name**:随便填,如 `relay-chat-and-work`。
3. **Expiration**:建议选 `90 days` 或更短(过期后需重新生成,更安全)。
4. **Repository access**:选 **Only select repositories**(指定仓库),勾选:
   - 自动存档目标私人库:`<你的用户名>-chat-and-work`
   - 如果你的工具也要 push 技能公开库,一并勾上 `relay-chat-and-work`
5. **Permissions** 里,展开 **Contents**,改成 **Read and write**(这是 push 文件所需的唯一权限)。其余全部保持默认(只读/不授权)。
6. 点 **Generate token**,马上**复制并保存**这个 token(只会显示一次)。

> 如果你用的工具只支持老式 token,就建 **Classic token**: 同上入口选 **Tokens (classic) → Generate**,勾选 **`repo`**(完整仓库读写,含 push 公开+私人库),别的都别勾。注意 classic 的 `repo` 权限范围偏大,不如 fine-grained 精确。

最后把 token 设置成环境变量 `GITHUB_TOKEN` 即可,例如在配置里加:
```
GITHUB_TOKEN=你的token
```

一个可选的裁剪技巧:如果只想 push **公开**库、绝不碰私人库,可用只含 `public_repo` 权限的 classic token;但请记得这个 skill 的自动存档目标是**私人库**,所以默认至少要能写那一个私人仓库。

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
