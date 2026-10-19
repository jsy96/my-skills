# 初始化 SOP(把一个软件项目接入开发流程)

> 一身两用:**执行规范**(skill / AI 照着把项目接入)+ **验证清单**(跑完逐项核对,确认已正确接入)。

---

## 原则
- 新项目全量铺开;**已有项目非破坏合并**(缺啥补啥,不覆盖)。
- **幂等**:可重复跑,不产生重复或破坏。
- **一个项目边界一个控制面**:单仓多子项目只建一套根级 `flow/`、`docs/` 和 hook;子项目不机械复制控制层。
- **文档默认集中**:跨模块和需要统一查找的文档(含契约)进入根级 `docs/`;不搬动已有 README、生成文档或必须紧贴代码的说明。
- **命令必须真实**:门禁命令区只写从项目配置里实际探测到的命令;探测不到留 TODO 占位并标注,**禁止编造**。
- 动手前先列「将创建 / 修改清单」给用户确认(同 `文档维护SOP.md` 的提议 → 确认 → 写入)。
- 已有 JSON 配置用结构化方式合并;不能安全合并时,只生成建议文件并请用户确认,不硬改。

## 步骤
1. **扫描项目边界**:
   - 看根级和候选子目录的 `.git`、workspace / 构建配置(`pnpm-workspace.yaml`、npm/yarn workspaces、Cargo / Go workspace 等)、包清单、CI 和发布方式。
   - 列出有独立职责的候选子项目;排除 `node_modules/`、`dist/`、`build/`、`venv/`、临时目录和普通工具目录。
   - 按 `多子项目结构.md` 判断单体项目、单仓多子项目或多个独立仓库。拿不准就把判断依据列给用户确认。
2. **探测技术栈与门禁命令**(软件项目核心步骤):
   - 构建命令:读 `package.json` scripts、`Makefile`、`CMakeLists.txt`、`pyproject.toml`、`Cargo.toml`、CI 配置等。
   - 测试命令:测试框架配置(`jest`、`pytest`、`go test`、`ctest`…)对应的真实调用方式。
   - 静态检查:lint / typecheck / formatter 配置(eslint、ruff、clippy、msbuild warnings…)。
   - 把探测结果整理成「门禁命令区」草稿,**逐条注明出处文件**;探测不到的门写 `TODO(未探测到,需用户补充)`。
   - 版本规范:项目已有版本号 / changelog 约定则记录下来,发布时跟随。
3. **判断接入状态**:有无 `AGENTS.md`、`flow/`、其他协作骨架(含 project-flow-cy 的标记块)→ 决定全量铺、补差异还是非破坏合并。
4. **先报清单并确认**:说明边界判断、探测到的门禁命令及出处、根级将创建 / 修改的文件、各子项目局部入口,以及明确不会创建 / 移动的内容。用户确认后再动手。
5. **铺根级骨架**:每个项目边界只建一套 `flow/`(`charter.md` `plan.md` `进展.md` `decisions.md` `踩坑记录.md` `releases.md` `tasks/`)+ `docs/`(软件版子目录 + `README.md`)。保留已有代码布局;不替 monorepo 猜造业务目录。〔归属规则见 `开发工作流程.md`〕
6. **根级入口注入**:
   - 写 `AGENTS.md`(从 `templates/AGENTS.md`:精要规则 + **门禁命令区** + 约束 + 目录地图 + 指针;已有项目则**合并**进现有 AGENTS.md)。
   - 建软链:`ln -s AGENTS.md CLAUDE.md`(Windows 改复制一份)。
   - (可选)写 `DESIGN.md`——仅当项目有 UI / 设计 / 创意工作。
7. **单仓多子项目的局部入口**:
   - 每个有独立职责的子项目从 `templates/MODULE_AGENTS.md` 生成 `<module>/AGENTS.md`,替换占位符,填入**本模块**的构建 / 测试 / lint 命令(同样只写探测到的真实命令)。
   - 在同目录建立 `CLAUDE.md -> AGENTS.md`(Windows 改复制)。局部入口只写本模块职责、命令、约束和根级指针。
   - 不在子项目重复创建 `flow/`、`docs/`、`.hooks/`、`.claude/`、`.codex/`;不移动已有局部文档。根级 `docs/README.md` 对保留在模块内的文档加索引。
8. **装根级 hook**:复制 `.hooks/stop-devcheck.sh` → `chmod +x` → 写根级 `.claude/settings.json` 与 `.codex/hooks.json`。
   - 读取实际 `codex --version`:可解析且不低于 `0.145.0` 时启用单次自动续跑;更旧或未知版本由脚本安全放行。`0.144.1` 是已知不兼容版本,应先升级。
   - Codex 当前 `features.hooks` 默认 true;检测有效状态,若被关才**提醒用户**开(或 `--enable hooks`),**不擅自改全局 `~/.codex/config.toml`**。
   - 提醒:Codex 项目级 `.codex/` 层需项目 trust,且需 `/hooks` 审核批准。〔细节见 `hook机制.md`〕
9. **方法论详规随项目**:把 7 份详规复制进根级 `flow/规范/`(自包含)。
10. **收尾引导**:填 `flow/charter.md` 的技术栈与质量基线;确认 `docs/contracts/` 契约目录用法;多子项目时确认子项目地图。

## 已有项目的非破坏合并细则
- 模板文件不存在才复制;已有 `flow/*.md`、`docs/README.md`、`DESIGN.md` 默认不覆盖。
- `AGENTS.md` 已存在:在文件末尾维护一个 `<!-- software-dev-flow:start -->` / `<!-- software-dev-flow:end -->` 包住的协作约定块;已有该块则只更新块内内容,块外原文不动。
- **已接入 project-flow-cy 的项目**:检测到 `<!-- project-flow-cy:start -->` 块或其 `flow/规范/` 副本时,**不重复通用协作内容**,只补差异:门禁命令区、软件铁律、`质量门禁.md`、`版本发布.md`、`flow/releases.md`、`docs/contracts/` 等软件工程部分;`进展.md` / `decisions.md` / `踩坑记录.md` 沿用原文件,仅在模板缺失字段(如门禁状态)上补说明。冲突点列清单请用户确认。
- `CLAUDE.md`:不存在则软链到 `AGENTS.md`;已是正确软链则跳过;若已存在且不是该软链,列为冲突项请用户确认,不要覆盖。
- 子项目局部入口遵守同一规则:已有 `<module>/AGENTS.md` 就只维护明确标记的块;已有 `<module>/CLAUDE.md` 且不是正确软链时列为冲突项。不要把根级 `AGENTS.md` 全文复制进模块。
- 已有子项目 `docs/`、README 或其他说明不迁移、不删除。需要统一发现时,只提议在根级 `docs/README.md` 增加索引;已有索引块只更新块内内容。
- `.hooks/stop-devcheck.sh`:不存在则复制;存在则先比对内容,确认它就是旧版本 skill 脚本时更新,否则生成 `.hooks/stop-devcheck.software-dev-flow.new.sh` 并请用户确认。
- `.claude/settings.json` 与 `.codex/hooks.json`:不存在则复制;存在则只补 `Stop` 事件下本脚本的 command handler,保留其他 hook。若 JSON 解析失败或结构不明,生成 `.software-dev-flow.suggested.*.json` 并请用户确认。
- `flow/规范/`:可覆盖更新这 7 份方法论副本,因为它们是 skill 注入的规范副本;覆盖前仍在清单里说明。

## 接入自检(跑完逐项核对)
- [ ] 已报告项目边界判断;单仓多子项目没有被误拆成多套总体流程,独立仓库也没有被误合并
- [ ] 门禁命令区每条命令都有出处(探测到的文件),或明确标 TODO;没有编造的命令
- [ ] 根级 `flow/`(charter/plan/进展/decisions/踩坑记录/releases/tasks)与软件版 `docs/` 已建;已有代码目录保持原样
- [ ] `AGENTS.md` 存在;读 `CLAUDE.md` = `AGENTS.md`(软链解析正确)
- [ ] AGENTS.md 里有:目录地图 + 开工/收工 + 门禁命令区 + 核心约束 + 详规指针
- [ ] 每个有独立职责的子项目都有局部 `AGENTS.md` 与同源 `CLAUDE.md`;根级相对路径均可解析
- [ ] 子项目没有新增重复的 `flow/`、`docs/` 或 hook;保留在模块内的文档已从根级 `docs/README.md` 索引
- [ ] (若有 UI / 设计工作)`DESIGN.md` 存在
- [ ] 在 `software-dev-flow` Skill 源码目录运行 `bash tests/test-stop-hook.sh`;确认目标项目 `.hooks/stop-devcheck.sh` 可执行:Claude 只按 `prompt_id`、兼容的 Codex 只按 `turn_id` 界定回合,首次 Stop 输出 `decision:block`,同一 scope 的 active 或重复 Stop 输出 `continue:true`;错误字段、旧版、未知版本、非法输入和缺少专属稳定 ID 时安全放行
- [ ] `.claude/settings.json`、`.codex/hooks.json` 已写
- [ ] Codex 项目已 trust;`features.hooks` 未被关闭;`/hooks` 已批准
- [ ] 根级 `flow/规范/` 下 7 份详规齐
- [ ] `flow/charter.md` 已开始填(含技术栈与质量基线)
