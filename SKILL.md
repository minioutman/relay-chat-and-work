---
name: relay-chat-and-work
version: 2.0.0
description: >
  一体化长任务技能: 接力干活 + 跨客户端项目存档/加载。
  核心模型: 每次打开一个新会话=一个新项目,本地按会话标题建项目文件夹,产物归其下;
  存档到 GitHub 私人仓库(<GitHub用户名>-chat-and-work,按 标题_时间_设备名 建文件夹);
  换客户端(如 Minis→Codex)后可用加载功能把项目(对话+产物+项目记录)拉回本地继续做。
  自动维护 ISSUES.md 项目记录(想法/问题/Bug/待办/决策),供下一客户端接续时提示处理。
  触发词: "接力干活"、"接力"、"分阶段做"、"存档对话"、"打包对话"、"加载到本地"、
  "恢复项目"、"继续上次"、"接着干"、"换客户端继续"、"archive/restore"。
---

# relay-chat-and-work: 跨客户端项目接力 + 存加载

让长任务的**项目状态**跨会话、跨客户端的 GitHub 私人仓库可持续续做。

## 核心模型

**每次打开新会话 = 一个新项目。**

本地: `/var/minis/workspace/<会话标题>/`(项目文件夹,所有产物放这里)
存档: `私人库/<会话标题>_<YYYYMMDD_HHMM>_<设备名>/`(完整状态)

换客户端不断链: 今天 Minis 做的,存档进私人库;明天 Codex 加载到本地继续做。

## 数据全部是纯 Markdown

存的是 MD,加载的也是 MD。conversation.md / ISSUES.md / PROJECT_STATUS 皆纯文本,
任何认 Markdown 的客户端都能读写,不绑定 Minis/Codex 专属格式。

## 三大能力

1. **接力干活**: 长任务拆阶段、落盘、跨会话/跨客户端续接
2. **自动存档**: 新对话打开时静默补存上一轮会话(对话+产物+项目记录)→ 私人库
3. **加载到本地**: 按需把存档拉回本地,新客户端继续做(A离线/B产物/C文本/D续做)

## 项目文件夹(本地)

干活时默认把产物放进 `/var/minis/workspace/该会话标题/`,不散落根目录。
存档时精确收集此文件夹 → 对应私人库存档。杜绝跨会话串台。

## 私人仓库命名

**`<GitHub用户名>-chat-and-work`** (private)
本用户账号 `minioutman` → 库名 `minioutman-chat-and-work`。
存iframe: `仓库/<标题>_<时间>_<设备>/` ,例 `官方仓库技能需求查询_2026-08-08_0127_iPhone/`。
设备名用 `apple-device` 获取,可 `--device` 覆盖。

## 存档结构(每会话)

```
<标题>_<时间>_<设备>/
├── conversation.md     完整对话
├── meta.json           元信息(会话ID/标题/设备/产物清单)
├── ISSUES.md           项目记录(想法/问题/Bug/待办/决策) ← 核心续接依据
└── files/              产物文件
```

## 工具脚本(scripts/)

| 脚本 | 用途 |
|------|------|
| `archive_session.py` | 存档: 拉会话→建项目文件夹→收集产物→写meta/issues→更新索引+README |
| `restore_session.py` | 加载: 定位→恢复产物+文本+ISSUES→(可选)触发续聊 |
| `issues.py` | 项目记录管理: add/list/resolve(移到已解决)/delete |

用法:
```
python3 scripts/archive_session.py --id <sid> --workspace /var/minis/workspace --out <私人库目录> [--device 名]
python3 scripts/restore_session.py --query "<标题/别名>" [--out 私人库目录] [--workspace 恢复目录] [--resume]
python3 scripts/issues.py add --type idea|bug|todo|q|decision --title "..." --file <ISSUES.md>
```

## ISSUES 记录机制(跨客户端接续核心)

- **自动搜集**: 干活时遇到想法/问题/bug/待办/决策,调用 issues.py 追加到 ISSUES.md
- **加载提示**: restore 后,新客户端(AI)看到 ISSUES.md 的待解决项,主动提示"要处理吗"
- **解决即移":** 处理完用 `issues.py resolve` 移入「已解决」区(保留历史,不删)
- 决策/待办也记录,保持项目心智模型完整

## 环境适配(换客户端)

- **Minis 环境**: 有 `minis-sessions-cli`,restore 可 `--resume` 用 session_id 触发真续聊
- **其他客户端(Codex 等)**: 无 minis-cli → restore 只输出 MD(conversation+ISSUES+产物),
  AI 读 ISSUES.md / conversation.md 即可接着往下做,不报错不依赖专属命令
- 脚本自动检测 `minis-sessions-cli` 是否存在,决定是否启用续聊

## 环境依赖

- `GITHUB_TOKEN`(GitHub 推送)必须已设置;未设则提示用户设置 [GITHUB_TOKEN](minis://settings/environments)

## 注意

- 存档静默执行,但遇权限/网络错误必须向用户汇报
- 敏感信息(密码/token)不写入存档
- 产物精确收集当前会话项目文件夹,不扫描整个 workspace
