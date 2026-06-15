# AGENTS.md

本文定义 agent 在 LoopEngineer 仓库中工作的规则。

LoopEngineer 是一个独立的 agent loop control-plane plugin。它的目标是让 AI agent loop 具备上下文安全、路由、编排、证据消费、审计、恢复和成本控制能力。

本文件约束仓库内的实现、规划、审计和文档工作。README 面向用户；AGENTS.md 面向执行本仓库任务的 agent。

---

## 1. 仓库定位

LoopEngineer 是独立产品，不是旧 SKILLS 的临时迁移目录。

LoopEngineer 可以：

- 作为独立 Codex plugin 使用；
- 作为 Loom 的外部伴随插件使用；
- 承载 agent loop 的上下文安全、调度、审计和恢复控制面。

LoopEngineer 不应该：

- 依赖旧 MC-SKILLS 作为运行时；
- 被写成 Loom scenario skill；
- 写入 Loom 的 `.loom/` fact surface；
- 安装进 `plugins/loom/skills/`；
- 把 GitHub、git、CI、review engine 或 worktree 替换掉。

---

## 2. 当前优先级

实现顺序必须遵循：

1. 仓库基线与架构决策；
2. 上下文安全最小版本；
3. 插件骨架与轻量路由；
4. 协议档位与技能重构；
5. 确定性脚本与结构定义；
6. 循环审计、成本控制与观察者策略；
7. 可选 MCP 与钩子；
8. Loom 外部插件集成。

默认优先级：

```text
Context safety first.
Router second.
Heavy orchestration later.
MCP and hooks last.
```

不要在上下文安全、路由和基础结构稳定前推进重型 watcher runtime、MCP 或 hooks。

---

## 3. Issue 驱动工作流

所有非平凡改动必须从 GitHub issue 出发。

开始工作前必须确认：

* 对应 issue 存在；
* issue 未被 blocked-by 阻塞；
* 所属 milestone 正确；
* 父子 issue 范围清晰；
* 本次改动只覆盖当前 issue 的验收标准。

不要把多个阶段混进一个 PR。

尤其禁止：

* 导入和重构混在同一个 PR；
* 文档、脚本、schema、技能大改混在同一个 PR；
* 越过 blocked-by 关系提前实现后续层；
* 在没有 issue 的情况下新增大功能。

---

## 4. 上下文安全规则

LoopEngineer 自身必须遵守它要提供给外部的上下文安全原则。

读取文件时：

* 不要直接 `cat` 大文件；
* 先使用 `find`、`rg`、`wc -l`、`wc -c` 了解范围；
* 只读取和当前 issue 相关的文件；
* 长文件分段读取；
* 不把大段源文件原文粘贴进 issue、PR 或线程正文。

写作和通信时禁止内联：

* 完整日志；
* 完整 diff；
* 完整报告；
* 完整状态表；
* 完整调度池；
* 完整通道表；
* 完整旧线程内容；
* 大型工具输出。

应改为：

* 写入 artifact；
* 发送路径；
* 发送摘要；
* 发送定位信息；
* 说明 next owner 和 next action。

核心规则：

```text
No full artifact inline.
No old thread as state database.
No context guard bypass.
```

---

## 5. 原 MC-SKILLS 使用边界

旧 MC-SKILLS 只作为只读来源，不是 LoopEngineer 的运行时依赖。

允许在以下任务中读取旧 SKILLS：

* 导入线程编排技能；
* 导入调度观察者技能；
* 拆分重型技能入口；
* 对齐协议档位；
* 编写 provenance 或迁移说明。

只读来源示例：

```text
../MC-SKILLS/skills/codex-thread-orchestration/
../MC-SKILLS/skills/codex-scheduler-watcher/
```

读取旧 SKILLS 时必须：

* 只读；
* 不修改 MC-SKILLS；
* 固定 source path 和 source commit；
* 记录 provenance；
* 不把旧 SKILLS 的内部演进叙事写进 LoopEngineer README；
* 不让 LoopEngineer 在运行时依赖旧路径。

LoopEngineer 完成后应自包含，旧 SKILLS 可归档。

---

## 6. Loom 集成边界

LoopEngineer 可以作为 Loom 的外部伴随插件，但不是 Loom 的内部模块。

必须保持以下边界：

* Loom 保持项目操作层权威；
* Loom CLI 保持 Loom 执行控制面权威；
* `.loom/` 仍由 Loom 合同管理；
* LoopEngineer 不直接写 `.loom/`；
* LoopEngineer 不作为 Loom scenario skill；
* LoopEngineer 不作为 Loom repo companion；
* LoopEngineer 不安装到 `plugins/loom/skills/`；
* 集成必须通过显式 adapter contract。

第一阶段只允许设计：

* check；
* verify；
* recommend；
* boundary documentation；
* smoke test planning。

不要默认实现 install 或 register 动作。安装动作必须后续显式 opt-in。

---

## 7. Skills 规则

`skills/` 中的技能应保持短入口和按需引用。

技能入口应：

* 说明角色；
* 路由到正确引用；
* 声明硬约束；
* 避免复制大型规则真相；
* 避免承载完整手册。

重型协议应下沉到 references。

不得让低风险任务隐式触发完整 watcher / scheduler 协议。

默认原则：

```text
Do not start watcher if routing is enough.
Do not start scheduler if worker_lite is enough.
Do not create worker if direct execution is enough.
```

---

## 8. Scripts 规则

`scripts/` 中的脚本负责确定性判断，不负责替代 agent 决策。

脚本应：

* 输出机器可读 JSON；
* 支持失败时 fail-closed；
* 有测试；
* 不依赖本机绝对路径；
* 不读取无关仓库状态；
* 不隐式修改 GitHub、git、PR 或 issue。

优先实现：

* context guard；
* schema validate；
* state digest；
* report consume；
* loop audit；
* coordination tax。

---

## 9. Schemas 规则

`schemas/` 定义状态和报告形状。

Schema 应：

* 有有效样例；
* 有无效样例；
* 被测试覆盖；
* 服务脚本和技能协议；
* 避免只做文档摆设。

核心结构包括：

* context budget；
* handoff manifest；
* report；
* dispatch table；
* scheduler pool；
* lane lock table；
* watcher decision。

---

## 10. PR 规则

每个 PR 必须：

* 关联 issue；
* 说明变更范围；
* 说明验证方式；
* 说明非目标；
* 说明剩余风险；
* 遵守上下文安全；
* 不夹带无关重构；
* 不把导入和重构混在一起。

PR body 必须包含以下二级标题，供 reviewer 和 CI 消费：

```text
## Summary
## Scope
## Validation
## Non-goals
## Risk
```

单人维护 public 仓库时，主分支保护默认不要求作者自己无法满足的 approval 或 last push approval。必须保留 PR 合并、required status check、conversation resolved、禁止删除、禁止 force push、线性历史和无 bypass。新增 collaborator、涉及安全/权限/发布/共享合同破坏风险，或仓库进入多人维护时，应重新启用独立 review 要求。

最小 CI 只能作为仓库早期主分支保护的可绑定基线，不代表最终质量门禁。

最小 CI 可以暂时只覆盖：

* 仓库关键文件存在；
* JSON 可解析；
* Markdown 基础卫生；
* 常见本地缓存、日志、临时文件未被提交。

最小 CI 暂时不应伪装成已覆盖：

* 单元测试；
* lint / format；
* schema validation；
* context guard / no-inline policy；
* release 或版本一致性自动化；
* 需要新增依赖、lockfile 或工具链选择的检查。

当对应脚本、schema、测试入口或工具配置在后续 issue 中落地后，必须把相关检查升级进 CI，并在 GitHub 主分支 ruleset 中设置为 required status check。不得把“最小 CI”作为长期跳过验证梯度的理由。

推荐 PR 顺序：

1. 文档和 ADR；
2. context budget；
3. context guard；
4. no-inline policy；
5. handoff rotation；
6. plugin skeleton；
7. loop router；
8. invocation guard；
9. core skill import；
10. skill refactor；
11. schemas；
12. scripts；
13. audit；
14. optional MCP / hooks。

---

## 11. 禁止事项

除非用户或 issue 明确要求，否则不要：

* 创建长期 automation；
* 创建 scheduler thread；
* 创建 worker thread；
* 创建 watcher thread；
* 运行合并；
* 运行发布；
* 直接修改 Loom 的 `.loom/`；
* 直接修改 MC-SKILLS；
* 把大文件全文贴进线程；
* 把旧线程当状态数据库；
* 声称完成但没有证据；
* 跳过 issue dependency；
* 在 README 中以旧 SKILLS 升级作为主叙事。

---

## 12. 完成标准

任务完成必须满足：

* 相关 issue 的验收标准已满足；
* 测试或验证已运行；
* 文档与实际结构一致；
* 没有未说明的范围外修改；
* 没有上下文安全违规；
* 没有把临时路径写成运行时依赖；
* PR 描述能让 reviewer 复现判断。

对于协议类改动，还必须说明：

* 保留了哪些不变量；
* 改动了哪些边界；
* 哪些旧语义被迁移；
* 哪些旧语义被废弃；
* 是否影响 Loom 集成边界。

---

## 13. 失败处理

如果发现任务无法完成，应输出：

* 当前完成了什么；
* 阻塞在哪里；
* 需要哪个 issue、权限、文件或决策；
* 是否存在上下文风险；
* 推荐下一步。

不要伪造完成状态。
不要用 status-only final 代替真实推进。
