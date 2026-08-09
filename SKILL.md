---
name: relay-chat-and-work
version: 2.1.0
description: >
  接力干活 + 自动存档对话的一体化长任务技能。
  两大核心能力:
  (1) 接力干活: 把长任务拆成有编号阶段,分步推进,进度落盘,跨会话续接;
  (2) 自动存档对话: 每次新对话打开,自动把上一轮会话的全部对话+产物文件,
      打包进用户的 GitHub 私人仓库(命名 <GitHub用户名>-chat-and-work),
      按对话标题建文件夹,静默完成不打扰。
  触发词: "接力干活"、"接力"、"分阶段做"、"拆成步骤"、"存档对话"、
  "打包对话"、"存对话"、"archive this chat"、"继续"、"接着干"、"续上"。
---

# relay-chat-and-work

长任务的接力推进 + 对话自动存档一体化技能。

## 三大能力

1. **接力干活**(Rely Work)—— 长任务拆阶段、落盘、跨会话续接
2. **对话自动存档**(Auto-Archive)—— 新对话打开时静默补存上一轮会话
3. **按对话标题归档** —— 私人库按 `对话标题/` 建文件夹,分组存放

## 存档目标仓库

私人库命名规则:**`<GitHub用户名>-chat-and-work`**

- 本用户 GitHub 账号: `minioutman`
- 即私人库: `minioutman/minioutman-chat-and-work`(private)
- 每个对话 → `仓库/<对话标题>/`

## 能力一: 自动存档对话(Auto-Archive)

**触发方式(无需用户说话,静默执行,不提醒):**
每次用户打开一个新对话时,自动执行——检索上一个会话是否未打包,若未打包则补存。

### 流程
1. `minis-sessions-cli list` 找出上一个会话(前一个非当前会话,注意排除本会话自身)
2. 用 `minis-sessions-cli messages --id <prev_id> --full` 拉完整对话
3. 打包结构:
   ```
   <上一轮对话标题>/
   ├── conversation.md   ← 完整对话(按消息角色分段)
   ├── meta.json         ← 会话元信息(时间/总数/收集的产物)
   └── files/            ← 该会话产生的产物文件
   ```
4. 记录「已存会话 id」到存档索引(如 `archive_index.json`),避免重复打包
5. 执行 `scripts/archive_session.py --push`,由脚本完成 commit + push 到 `minioutman-chat-and-work`

### 去重规则
- 每次存完在索引里记录会话 id
- 下次遇到已存 id 直接跳过,不重复

### 存档工具
用内置脚本 `scripts/archive_session.py`:
```
python3 scripts/archive_session.py --id <session_id> \
  --workspace /var/minis/workspace --out <目标目录> --slug <标题>
```
加 `--push` 才会 git commit + push 到私人库;不加则只写本地存档。

## 能力二: 接力干活(Rely Work)

把长任务拆成阶段,推进 + 落盘 + 续接。详见能力一的流程,方法同 relay-work:
1. 接任务 → 拆成有编号的阶段(每段有明确交付物)
2. 初始化进度文件(`/var/minis/workspace/relay-work/` 下)
3. 逐阶段推进,每完成一段更新进度文件
4. 默认自动推进;需要用户拍板的停下并置「等待确认」
5. 跨会话续接:读进度文件 → 看续接点 → 无缝继续

进度文件规范见 `references/protocol.md`。

## 环境依赖

- `GITHUB_TOKEN`(GitHub 推送身份认证)必须已设置
- 若未设置:告知用户设置 [GITHUB_TOKEN](minis://settings/environments),并给出创建 token 指引

## 注意

- 存档动作为静默执行,但若遇到权限失败/网络错误,须向用户汇报,不静默吞掉。
- 产物文件从 `/var/minis/workspace` 收集(排除隐藏文件、.git、本技能源码仓库自身)。
- 敏感信息(密码/token)不写入存档;发现要跳过。
