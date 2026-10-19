# my-skills

个人 Codex skills 仓库。

## 更新记录（最新在前）

- **2026-10-19**：新增 `software-dev-flow` v1.0.261019-1（软件开发协作流程 skill，源码目录 + `dist/software-dev-flow.zip`）。派生自 CY-CHENYUE/project-flow-cy（GPL-3.0-or-later）。
- **2026-10-12**：新增 `self-media-reuse-workflow`。

## Skills

### self-media-reuse-workflow

将一个主题、文章或飞书素材复用为：

- 公众号文章
- 小红书图文
- 30—60 秒口播稿
- Vox 纸贴风逐镜头脚本
- 多风格视觉重制版本
- 飞书文档交付与回查

安装方式：

1. 下载 `dist/self-media-reuse-workflow.zip`
2. 解压到 `~/.codex/skills/`
3. 重启 Codex 或开启新会话后调用

使用示例：

```text
用 self-media-reuse-workflow 把这篇飞书文章改成小红书图文，
先生成 3 个标题、开场钩子、正文和 7 张图的画面文案，等我确认。
```

```text
用 self-media-reuse-workflow 把这个主题写成 30—60 秒口播稿，
并拆成 Vox 贴纸风逐镜头脚本；先给方案，我确认后再消耗。
```

### software-dev-flow

面向**软件开发项目**的 AI 多 Agent 协作 + 软件工程纪律 skill（v1.0.261019-1），派生自 [CY-CHENYUE/project-flow-cy](https://github.com/CY-CHENYUE/project-flow-cy)（GPL-3.0-or-later）。

核心能力：

- **文件化协作**：`flow/` 控制层 + `docs/` 内容层，Agent 间靠 `flow/进展.md` 接力，上下文不锁在对话里
- **契约先行**：跨模块接口先落 `docs/contracts/` 确认，再写实现
- **每任务一分支**：`feat/T03-xxx` / `fix/T07-xxx`
- **测试同棒**：新代码与测试同一棒交付；修 bug 先写能复现的测试
- **四道质量门禁**：构建 / 测试 / 静态检查 / 跨模型评审，进展条如实记门禁状态
- **版本发布**：发布清单、`flow/releases.md` 变更日志、回滚记录

三个操作：初始化接入软件项目（探测真实构建/测试/lint 命令填进门禁命令区）、收工交接（写 handoff）、版本发布（发版清单）。

安装方式：

1. 下载 `dist/software-dev-flow.zip`（zip 内已含顶层 `software-dev-flow/` 目录）
2. 解压到技能目录：Codex 用 `~/.codex/skills/`；Claude Code 用 `~/.claude/skills/`
3. 重启 / 新开会话后调用；源码目录结构见仓库内 `software-dev-flow/`

可选依赖：`jq`（收工自检 Stop hook 的自动续跑需要；缺省时安全放行，不报错）。

使用示例：

```text
用 software-dev-flow 给这个项目接入开发流程，
先给项目边界判断、探测到的构建/测试/lint 命令和创建清单，我确认后再动手。
```

```text
写个 handoff，把这一棒的进展和门禁状态交接给下一个会话。
```

```text
发个新版本：门禁复核、bump 版本号、记 releases.md 变更日志、打 tag。
```

已知限制（2026-10-19 实测）：Stop hook 全量断言与自动续跑需本机安装 `jq`；未移植上游 project-flow-cy 的真实 Codex TUI E2E 测试，兼容结论引用上游证据。
