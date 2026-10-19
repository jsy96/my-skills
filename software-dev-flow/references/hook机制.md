# Hook 机制(收工自检)

> Claude Code 与通过兼容门的 Codex 在每个用户回合收尾时自动续跑一次,先执行当前路径生效的 `AGENTS.md`/`CLAUDE.md` 中已有的业务专项收工检查,再检查三件事:① 文档是否要按 `文档维护SOP.md` 更新;② 是否已在 Hook 所属项目根的 `flow/进展.md` 顶部留下交接记录;③ 本轮若改了代码,构建 / 测试 / lint / 评审四道门禁是否已跑且结果如实记录。
> Hook 是防漂移兜底,不替代 Agent 主动遵守收工约定。

## 作用域

| 内容 | 作用域 | 位置 |
|---|---|---|
| Hook 定义与行为 | 项目级 | 项目根 `.hooks/`、`.claude/settings.json`、`.codex/hooks.json` |
| Codex Hook 能力开关 | 机器级,当前默认开启 | `~/.codex/config.toml` 的 `features.hooks` 或启动参数 `--enable hooks` |

一个项目边界只安装一套根级 Hook。单仓多子项目不在子项目重复安装。Codex 只有在项目被 trust 后才加载项目级 `.codex/`。

**依赖**:脚本依赖 `jq` 解析回合输入;缺 `jq` 时安全放行(不续跑、不报错)。要启用自动续跑,先安装 `jq`。

## 共享脚本

Claude Code 与 Codex 共用 `.hooks/stop-devcheck.sh`,调用时传入 `claude` 或 `codex`。脚本全文见 `assets/templates/.hooks/stop-devcheck.sh`,关键语义:

- Claude Code 只接受 `prompt_id`,Codex 只接受 `turn_id`,不在两种字段之间回退;marker 键同时包含 `session_id`,不同工具、会话和用户回合互不污染。
- marker(`mkdir /tmp/software-dev-stopcheck-<UID>/<tool>-<key>`)表示该用户回合已经触发过,保持单调存在。首次通过原子 `mkdir` 成功的调用返回 `decision:block`;同一 scope 后续无论 `stop_hook_active` 是否正确设置,都只返回 `continue:true`。
- Codex 只有在本机可解析版本不低于 `0.145.0` 时启用自动续跑。旧版本、未知版本、非法或不适合作为文件名的 ID、缺少 `jq`、缺少本工具专属稳定 scope 或 marker 无法建立时安全放行;脚本不依赖外部 `tr` 或 `id` 命令。
- 续跑 `reason` 用 `jq -n` 生成,避免手工转义中文和引号,内容为:① 文档自检(结构 / 契约 / 心智 / 命令变更 → 提议更新 `AGENTS.md` 或 `DESIGN.md`);② 交接(在项目根 `flow/进展.md` 顶部追加一条并贴回复,决策落 `decisions.md`、坑落 `踩坑记录.md`);③ 门禁(本轮改了代码 → 按 `AGENTS.md` 门禁命令区跑构建 / 测试 / lint 并如实记门禁状态;评审门未过不标完成)。
- 上层项目 Hook 被子目录复用时,续跑提示先读取当前路径实际生效的 Agent 入口并执行其中的专项收工检查;项目交接仍只写回 Hook 所属项目根的 `flow/`,不会在子目录另建第二套控制层。

## 两端薄配置

```jsonc
// .claude/settings.json
{ "hooks": { "Stop": [ { "matcher": "", "hooks": [
  { "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/.hooks/stop-devcheck.sh\" claude" }
] } ] } }

// .codex/hooks.json
{ "hooks": { "Stop": [ { "hooks": [
  { "type": "command", "command": "root=\"$(git rev-parse --show-toplevel 2>/dev/null || pwd)\"; if [ ! -f \"$root/.hooks/stop-devcheck.sh\" ]; then d=\"$PWD\"; while [ \"$d\" != \"/\" ] && [ ! -f \"$d/.hooks/stop-devcheck.sh\" ]; do d=\"$(dirname \"$d\")\"; done; root=\"$d\"; fi; if [ ! -f \"$root/.hooks/stop-devcheck.sh\" ]; then printf '%s\\n' '{\"continue\":true,\"systemMessage\":\"software-dev-flow stop hook script not found\"}'; exit 0; fi; bash \"$root/.hooks/stop-devcheck.sh\" codex", "timeout": 30, "statusMessage": "收工自检" }
] } ] } }
```

脚本承载行为,配置只负责定位并调用脚本。后续只改脚本不会改变 Codex 的 command trusted hash。

## Codex 兼容与批准

- Codex 当前 `features.hooks` 默认开启;若用户显式关闭,只提醒在 `~/.codex/config.toml` 开启或用 `--enable hooks`,不要擅自修改全局配置。
- 项目级 `.codex/hooks.json` 需项目 trust,首次安装或 command 改动后还需在 TUI 用 `/hooks` 审核批准。
- Codex CLI `0.144.1` 曾把 `decision:block` 产生的 continuation prompt 保存为裸 UUID message ID,继续或恢复任务时触发 `invalid_id_prefix`。
- Codex CLI `0.145.0` 已通过真实 TUI 三段回归(首次自动续跑、同会话继续、退出后恢复;`msg_...` Hook prompt ID 唯一,裸 UUID 与 `invalid_id_prefix` 均为 0)——证据来自上游 project-flow-cy 的测试;本 skill 继承同一兼容门,不外推到更旧或无法识别的客户端,脚本对它们安全放行。

## 回归测试

在 `software-dev-flow` Skill 源码目录运行确定性测试:

```bash
bash tests/test-stop-hook.sh
```

它覆盖:版本门(新旧 Codex 版本)、Claude 专属 `prompt_id`、Codex 专属 `turn_id`、错误字段拒绝、不同 session/tool 隔离、`stop_hook_active` 放行、重复 Stop 单次续跑、非法 ID 字符、缺 `jq` 安全放行。本机缺 `jq` 时测试输出 SKIP 并只验证安全放行路径;安装 `jq` 后可跑全量断言。

(上游 project-flow-cy 另有调用在线模型的真实 Codex TUI E2E;本 skill 未包含该 E2E 脚本,兼容结论引用上游证据。)

## 安装

由 `初始化SOP.md` 执行:复制脚本 → `chmod +x .hooks/stop-devcheck.sh` → 合并两端配置 → 检查 Codex 版本与 hooks 开关 → 提醒 trust 项目及 `/hooks` 批准。
