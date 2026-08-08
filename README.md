# relay-work — 接力干活技能

> Relay your long tasks: split into stages, progress step-by-step, persist to disk, and resume across sessions.

一个给 AI 助手(Claude / Minis / Codex 等支持 skills 的 Agent)用的「长任务接力」技能。把一个大活/长任务拆成多个有编号的阶段,分阶段一路推进,每阶段的进度持久化到文件,从而支持**跨会话续接**——下次说一句"继续"就能从上次停下的地方无缝接上,不重复已完成的工作。

## 它解决什么问题

长任务(写多章节的书/文档、批量处理数据、多步骤生成报告、跨多次会话的项目)一次做不完,而且会话一断上下文就丢。relay-work 用**进度落盘**把"做到哪了、下一步干嘛"固化下来,让 AI 能自己接力一路做完,也能随时停下等你确认再接着干。

## 核心机制

| 能力 | 说明 |
|------|------|
| 拆阶段 | 把任务拆成阶段链,上一段的产出 = 下一段的输入 |
| 进度落盘 | 每阶段状态写到进度文件(目标/计划/续接点) |
| 自动接力 | 阶段之间默认自动推进,产出校验通过即开下一段 |
| 关键点停下 | 改你的东西/不可逆操作/方向分歧时停下等确认 |
| 跨会话续接 | 读进度文件 → 看「续接点」→ 无缝继续 |

## 安装

把 `relay-work/` 整个目录放进你的 skills 目录即可。对 Minis 用户:

```
设置 → Skills → 导入
```

支持 skills 的 Claude Code / Codex 等,放到对应的 skills 目录(`~/.claude/skills/` 等)。

## 用法

当你对 AI 说这些词,技能会被触发:

- 「接力干活」「拆成步骤一步步做」「先做xx再做xx」
- 「做一半下次继续」「接着干」「继续上次」「续上」
- long task / multi-step / resume / continue where I left off

然后 AI 会:
1. 把任务拆成有编号的阶段(每阶段有明确交付物)
2. 建进度文件(默认工作区 `relay-work/` 下)
3. 逐阶段推进并实时存档
4. 遇到要你拍板的停下,存好「续接点」等你

下次说「接着干」,AI 读档从续接点继续。

## 目录结构

```
relay-work/
├── SKILL.md                 # 主文件:触发条件 + 接力工作法规则
└── references/
    └── protocol.md          # 进度文件规范(存哪、状态流转、续接点格式)
```

## License

MIT
