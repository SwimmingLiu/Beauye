# Beauye

为 Coding Harness 提供页面设计、执行验收和独立审查知识。

## 三份 Skill

| Skill | 职责 |
| --- | --- |
| [beauye-execution](skills/beauye-execution/SKILL.md) | 维护任务与范围，组织实现、测试、Review、修复和复查。 |
| [beauye-design](skills/beauye-design/SKILL.md) | 决定信息取舍、区域构图、视觉层级、文案、组件与交互。 |
| [beauye-review](skills/beauye-review/SKILL.md) | 从用户任务反向检查页面，给出有证据的问题、修改建议和复验动作。 |

```mermaid
flowchart LR
    E[执行流程] --> D[页面设计]
    D --> I[实现与真实测试]
    I --> R[页面 Review]
    R -->|问题与建议| E
    E -->|调整设计关系| D
```

三份 Skill 共用当前任务资料。执行阶段维护处理状态，设计阶段保存方案，Review 默认只读提出发现。改变信息或布局关系时回到设计，再实现和复查。

## 使用

按当前 Harness 的 Skill 安装方式，分别安装 `skills/` 下需要的目录。每份目录可以独立使用，包内参考和模板需一并保留。已有同名版本时先备份，再更新。

在支持 `$Skill` 调用的 Harness 中，可以组合调用：

```text
使用 $beauye-execution、$beauye-design 和 $beauye-review，优化素材管理页。先形成方案，再实现和测试，由 Review 审查整页与交互。按发现修复并复查，保留项目现有约束和必要比较信息。
```

也可以直接让 Harness 读取三个 `SKILL.md`。仅设计时交付方案，仅评审时交付问题和建议，要求实现时完成代码与真实检查。

设计先从任务确定内容与操作，再决定构图和表达。优先处理重复信息、操作归属、数字层级和状态时机。交互实现复用兼容的成熟组件，验证实际键盘、焦点、弹层与适配行为。

执行 CLI 需 Python 3.11+。项目构建、浏览器、图片和命令工具沿用 Harness 或项目已有能力。具体使用见[执行入口](skills/beauye-execution/SKILL.md)，记录格式见[记录契约](skills/beauye-execution/references/records.md)。

## 核心文件

```text
skills/
  beauye-execution/   执行脚本、任务模板与检查约定
  beauye-design/      设计规则、示例与页面方案模板
  beauye-review/      审查清单、报告约定与结构示例
```

设计意图、实际观察与审查判断分别保存。执行检查器核对记录、覆盖和新鲜度，真实操作由 Harness 完成。自动检查和代理审查不替代人工审美判断。

许可证见 [LICENSE](LICENSE)。
