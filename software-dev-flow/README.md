# software-dev-flow

一套面向**软件开发项目**的 **AI 多 Agent 协作 + 软件工程纪律** skill,派生自 [CY-CHENYUE/project-flow-cy](https://github.com/CY-CHENYUE/project-flow-cy)(GPL-3.0-or-later)。

核心是四句话:

- 上下文落进文件,不锁在对话里;Agent 之间靠 `flow/` 和 `docs/` 异步接力。
- 契约先行:跨模块接口先落 `docs/contracts/` 并确认,再写实现。
- 测试同棒:新代码与对应测试同一棒交付;修 bug 先补能复现的测试。
- 门禁全绿才收工:构建 / 测试 / 静态检查 / 跨模型评审,四道门如实记录,红了不绕过。

这个 skill 负责三件事:

1. **初始化 / 接入软件项目**:判断单体、单仓多子项目(monorepo)或多独立仓库;探测真实的构建 / 测试 / lint 命令填进 `AGENTS.md` 门禁命令区;铺 `flow/`(含变更日志 `releases.md`)+ 软件版 `docs/`(含契约、测试、runbook 目录);装收工自检 hook;复制方法论详规。
2. **收工交接**:在 `flow/进展.md` 顶部追加一条交接记录(含门禁状态),并把同一条贴回对话。
3. **版本发布**:走发布清单(门禁复核 → 版本号 → 变更日志 → tag → 发布动作 → 交接)。

它不处理具体业务内容。技术选型、业务代码、调研、设计稿仍由对应项目和对应 Agent 完成;`software-dev-flow` 只负责把协作方式、工程纪律和交接结构立起来。

## 与 project-flow-cy 的关系

| | project-flow-cy | software-dev-flow |
|---|---|---|
| 定位 | 通用项目协作(代码 / 调研 / 内容 / 方案) | 专注**软件项目**的协作 + 工程纪律 |
| 生命周期 | 五段:立项 / 拆解 / 执行 / 评审 / 沉淀 | 六段:立项(需求)/ 设计与拆解(契约先行)/ 实现(每任务一分支)/ 测试(同棒)/ 评审与门禁 / 发布与沉淀 |
| 质量约束 | 跨模型评审 | **四道门**:构建 / 测试 / 静态检查 / 评审,含 DoD、豁免与失败处理(`references/质量门禁.md`) |
| 版本发布 | 无 | 发布清单、语义化版本、`flow/releases.md` 变更日志、回滚(`references/版本发布.md`) |
| 目录 | `flow/` + `docs/` | 同左,`flow/` 加 `releases.md`,`docs/` 加 `requirements/ contracts/ testing/ runbooks/` |
| 接入已用 project-flow-cy 的项目 | — | 非破坏补差异,不重建控制层 |

协作骨架(flow/docs 分层、AGENTS.md↔CLAUDE.md 运行时合同、进展日志接力、非破坏合并、Stop hook 机制)派生自 project-flow-cy,继承 GPL-3.0-or-later 并在 `NOTICE` 中保留出处。

## 安装

方式一:clone 到你的 skill 扫描目录(Claude Code 常用 `~/.claude/skills/` 或统一技能目录):

```bash
git clone <本仓库地址> ~/.claude/skills/software-dev-flow
```

方式二(本机当前用法,2026-10-19 实测):实体在 `~/.agents/skills/software-dev-flow`,`~/.claude/skills/software-dev-flow` 软链指向它:

```bash
ln -s ~/.agents/skills/software-dev-flow ~/.claude/skills/software-dev-flow
```

安装或更新后新开会话,确认 skill 列表里出现 `software-dev-flow`。

**可选依赖**:`jq`(Stop hook 自动续跑需要;缺 jq 时 hook 安全放行,不报错)。Windows 可 `choco install jq`。

## 怎么用

### 初始化 / 接入项目

在目标项目目录里说:

```
用 software-dev-flow 接入开发流程
```

或:

```
给这个软件项目搭 flow/docs 开发协作骨架
```

执行时会先读 `references/初始化SOP.md`;多子项目还会读 `references/多子项目结构.md`。先报告项目边界判断、探测到的门禁命令(注明出处)和将创建 / 修改的文件,等你确认后动手。已有项目(含已接入 project-flow-cy 的)走非破坏合并:缺什么补什么,不覆盖已有内容。

初始化后的典型结构:

```text
项目/
├── AGENTS.md  ←→ CLAUDE.md          # 运行时合同,含门禁命令区
├── DESIGN.md                        # 可选,有 UI / 设计工作才建
├── flow/                            # 唯一控制层
│   ├── charter.md                   # 目标 / 范围 / 技术栈 / 质量基线
│   ├── plan.md                      # 计划=契约,任务表带分支列
│   ├── 进展.md                      # append,顶部=交接棒,含门禁状态
│   ├── decisions.md
│   ├── 踩坑记录.md
│   ├── releases.md                  # 变更日志
│   ├── tasks/
│   └── 规范/                        # 7 份方法论详规副本
├── docs/                            # 集中内容层
│   ├── requirements/  architecture/  contracts/
│   ├── modules/  testing/  runbooks/  reviews/
├── frontend/  backend/ …            # 保留项目自己的代码布局
└── .hooks/ .claude/ .codex/         # 只放根级
```

### 收工交接

```
写个 handoff
```

skill 会在 `flow/进展.md` 顶部追加一条:做了什么 / 为什么 / 怎么理解 / 产出(路径)/ **门禁状态** / 问题→解决 / 下一步,同一条也贴回对话。

### 版本发布

```
发个新版本
```

skill 会走 `references/版本发布.md` 的清单,并在 `flow/releases.md` 顶部记变更日志。

## 文件职责

| 路径 | 作用 |
|---|---|
| `SKILL.md` | skill 入口,定义触发和三类操作(初始化 / 交接 / 发布) |
| `LICENSE` / `NOTICE` | GPL-3.0-or-later 许可证;派生自 project-flow-cy 的版权与出处说明 |
| `references/开发工作流程.md` | 六段式主循环、四个核心机制、目录归属 |
| `references/初始化SOP.md` | 项目接入流程(含技术栈探测)和自检清单 |
| `references/多子项目结构.md` | 单体、monorepo、多独立仓库的边界和目录规则 |
| `references/文档维护SOP.md` | `AGENTS.md` 怎么维护(含 DESIGN.md 边界) |
| `references/质量门禁.md` | 四道门、DoD、失败处理与豁免、评审怎么做 |
| `references/版本发布.md` | 发布清单、版本策略、变更日志、回滚 |
| `references/hook机制.md` | 收工自检 hook 的机制与安装说明 |
| `assets/templates/AGENTS.md` | 根级运行时合同模板(含门禁命令区) |
| `assets/templates/MODULE_AGENTS.md` | 子项目局部规则入口模板 |
| `assets/templates/flow/` | 控制层模板(charter / plan / 进展 / decisions / 踩坑记录 / releases / 任务卡) |
| `assets/templates/docs/README.md` | 内容层目录说明模板 |
| `assets/templates/.hooks/` `.claude/` `.codex/` | Stop hook 脚本与双端薄配置 |
| `evals/evals.json` | 单仓、多独立仓库、非破坏接入、project-flow-cy 升级、交接、发布六类行为用例 |
| `tests/test-stop-hook.sh` | 验证版本门、双端专属回合 ID、单次续跑、异常输入与缺 jq 安全放行 |

## 方法论要点

- **一个项目边界一个控制面**:单仓多子项目只保留一套根级 `flow/`、`docs/` 和 hook。
- **契约先行**:`docs/contracts/` 是模块间唯一真相源;改接口先改契约,再改两端代码。
- **测试同棒**:不留"以后补测试";修 bug 先写能复现的测试(红→修→绿)。
- **门禁如实记录**:未跑写未跑,不装绿;豁免必须用户确认并留痕。
- **审稿模型 ≠ 产出模型**:交付前换另一个模型评审,错误不相关。
- **进展日志是接力棒**:`flow/进展.md` 新记录放最上面,顶部那条就是当前 handoff。
- **非破坏接入**:已有项目只补缺失内容,冲突先列清单请用户确认。
- **命令必须真实**:门禁命令区只写探测到的命令,探测不到标 TODO,禁止编造。

## 边界

- 不替你做技术选型、写业务代码、调研或设计成品。
- 不猜发布命令:发布动作以项目脚本和 `docs/runbooks/` 为准。
- 不自动提交或推送 GitHub。
- 不把一个 monorepo 的每个代码目录机械初始化成独立项目。
- 不擅自覆盖已有 `AGENTS.md`、`CLAUDE.md`、hook 配置或用户文档。
- 不擅自修改全局 Codex / Claude 配置。

## 已知限制(2026-10-19 实测)

- 本机未安装 `jq`:Stop hook 自动续跑不生效(安全放行),`tests/test-stop-hook.sh` 只跑安全放行子集并输出 SKIP;装 jq 后可跑全量断言。
- 未移植上游 project-flow-cy 的真实 Codex TUI E2E 测试(`test-codex-stop-hook-e2e.sh`);Codex `0.145.0` 兼容结论引用上游回归证据,本 skill 继承同一版本门。

## 许可

GPL-3.0-or-later。使用、复制、修改或分发本项目时,请保留 `NOTICE` 中的版权和许可证声明;分发修改版或派生版本需按同一许可证开源,并保留对 project-flow-cy 的派生说明。

---

## 更新记录(最新在前)

- **v1.0.261019-1**(2026-10-19):首个版本。基于 project-flow-cy 的协作架构,新增软件工程纪律:六段式开发主循环、契约先行、每任务一分支、测试同棒、四道质量门禁(构建/测试/静态检查/跨模型评审)、版本发布流程与 `flow/releases.md` 变更日志;7 份方法论详规、全套项目注入模板、Stop hook(`stop-devcheck.sh`)与双端配置、6 条行为评测用例、stop-hook 回归测试;接入 project-flow-cy 已有项目时非破坏补差异。本机实测:stop-hook 测试安全放行子集通过(jq 缺失,全量断言待装 jq 后跑)。
