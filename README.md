# ![Beauye](assets/beauye-poster.png)

<p align="center">
面向 Coding Harness 的页面设计、执行验收与独立审查 Skill。
</p>

<p align="center">
<a href="#快速开始">快速开始</a> ·
<a href="#三份能力">三份能力</a> ·
<a href="#协作流程">协作流程</a> ·
<a href="#使用边界">使用边界</a>
</p>

Beauye 把用户任务、信息取舍、空间构图和真实交互放进同一份页面方案，再通过实现、实测和独立 Review 复查结果。适用于新增页面、布局改版和 UI 审查。

## 快速开始

按当前 Harness 的 Skill 安装方式，安装 `skills/` 下所需的目录，并保留包内参考与模板。已有同名版本时先备份，再更新。

以支持 Skill 安装的 Codex 为例，可以直接输入：

```text
请从 SwimmingLiu/Beauye 安装以下 Skill：
skills/beauye-execution
skills/beauye-design
skills/beauye-review
```

安装后，在支持 `$Skill` 调用的 Harness 中组合使用：

```text
使用 $beauye-execution、$beauye-design 和 $beauye-review，
优化素材管理页，保留现有业务与必要的多字段比较。
先形成方案，再实现和测试，独立 Review 后修复并复查。
```

也可以直接让 Harness 读取下方三个 `SKILL.md`。仅设计时形成方案，仅评审时给出问题与建议；要求实现时完成代码和真实检查。

## 三份能力

| [页面设计](skills/beauye-design/SKILL.md) | [执行验收](skills/beauye-execution/SKILL.md) | [独立审查](skills/beauye-review/SKILL.md) |
| --- | --- | --- |
| `beauye-design` | `beauye-execution` | `beauye-review` |
| 确定内容、区域、层级、文案、组件与交互。 | 维护任务与范围，组织实现、测试、修复和复查。 | 反向检查区域是否必要、操作是否合理、行为是否有证据。 |
| 交付页面方案与设计取舍。 | 保存真实操作、检查结果与证据。 | 交付问题、影响、修改建议与复验动作。 |

设计先确定用户要查看、比较、判断和完成什么，再选择页面表达。减少重复内容，明确主要操作，突出关键数字，按需要呈现帮助与确认。交互实现复用兼容的成熟组件，并检查实际键盘、焦点、弹层和窄屏行为。

## 协作流程

```mermaid
flowchart LR
    E[执行流程] --> D[页面设计]
    D --> I[实现与真实测试]
    I --> R[独立 Review]
    R -->|问题与建议| E
    E -->|调整设计关系| D
```

三份 Skill 共用当前任务资料。执行阶段维护处理状态，设计阶段保存方案，Review 默认只读提出发现。涉及内容、布局或操作关系的改变时，先调整方案，再实现和复查。

<details>
<summary>目录与执行入口</summary>

```text
skills/
  beauye-design/      设计规则、示例与页面方案模板
  beauye-execution/   执行脚本、任务模板与检查约定
  beauye-review/      审查清单、报告约定与结构示例
```

执行 CLI 需 Python 3.11+。项目构建、浏览器、图片和命令工具沿用 Harness 或项目已有能力。具体用法见[执行入口](skills/beauye-execution/SKILL.md)，数据格式见[记录契约](skills/beauye-execution/references/records.md)。

</details>

## 使用边界

每份 Skill 都可以独立使用，也可接入已有页面方案和任务记录。存量项目优先沿用兼容的业务组件与设计变量。

设计意图、实际观察与审查判断分别保存。执行检查器核对范围、覆盖和证据新鲜度，真实项目命令与浏览器操作由 Harness 完成。自动检查和代理审查不替代人工审美判断。

---

<p align="center">
<a href="LICENSE">许可证</a> · <a href="skills/beauye-design/references/examples.md">设计示例</a> · <a href="skills/beauye-review/references/review-checklist.md">审查清单</a>
</p>
