# 任务与观察记录

记录版本为 1。先用 `beauye.py init` 创建实际项目的任务，不要把示例里的路径、条件或结果当作事实。

```text
.beauye/tasks/<task-id>/
  task.json           范围、页面清单与当前条件
  plan.md             页面方案，也可引用现成文件
  observations/       每份实际观察一个 JSON
  evidence/           截图、命令输出等实际产物
  adapter/            可选 Hook 私有续查状态
```

每个任务使用独立目录。Harness 更新方案与任务清单；Hook 不改这两类资料。观察按独立标识保存，保留旧记录，不以覆盖文件掩盖问题。相同当前条件下仍有问题记录时先明确解决与归档，再保存复查结果。

## task.json

`schema_version`、`task_id`、`mode`、`project_root`、`rule_version` 标识本次任务。`mode` 为 `implement`、`review` 或 `design`。

`change_scope` 保存路径与来源，`review_scope` 保存 `full` 或 `limited` 及来源。有限验收必须来自用户明确要求，不能从修改路径推断。`plan_path` 可相对任务目录或为已有方案的绝对路径；未填写的初始方案带有 `beauye:needs-plan` 标记，完成方案后移除。

`page_inventory` 保存清单完整性，以及 routes、navigation、permissions 三类发现来源。每页记录 id、route、roles、affected、mobile、screenshot_required、states、interactions。默认状态使用 `default`；交互使用稳定的检查名称，例如 `filter`、`submit`、`keyboard`。

`desktop_viewport` 记录主桌面尺寸。每页与角色都需要主桌面的默认画面观察；affected 页面增加规定视口。每个适用状态和交互还需自己的观察，不要求所有状态和视口做无意义的全排列。

`environment` 记录当前 runtime、data、roles。它们应标识实际运行的实现或服务、数据版本和角色配置，不能只写希望运行的地址。未知时使用 null 并保留未验证。

`project_checks` 记录项目已有命令的 id、参数列表和 required；检查器只核对记录，不执行这些命令。初始化发现结果需核对项目本身的检查约定。

## observations/*.json

每份观察保存 `schema_version`、独立 `id`、`task_id`、`kind`、`result`、`origin`、`fingerprint`、`environment`、`action`、`expected`、`actual` 与 `artifacts`。字段结构见[观察示例](../assets/observation.example.json)。

`kind` 分为 visual、interaction、project。页面观察的 `subject` 指定 page_id、role、viewport、state、data_condition。交互与工程检查还需 `check_id`；工程检查附加准确的 command 与 exit_code。

`origin.kind` 区分 tool、human、agent；reference 指明实际工具结果或观察来源。代理陈述不能当作已经执行的工具事实。工具或人工观察也属于有来源的声明，检查器不提供独立认证。

`result` 为 passed、issue、unverified 或 not_applicable。未验证和不适用的原因放在 actual 中。工程通过需要准确匹配命令、零退出码及实际日志；要求截图的画面需要实际截图路径。默认桌面页面观察不能用“不适用”代替已经检查。

fingerprint 使用当前 `check --phase after-edit` 输出，同时绑定应用输入、页面方案与任务检查约定，不能用原始源码摘要代替。更改方案、路由、角色、状态、视口、检查命令或范围时，旧记录需要重新核验。environment 保存观察时的实际条件。写入观察前后保持源码与运行条件稳定；此后发生变化，就复查并记录新的结果。

## 检查输出

`check` 输出 JSON，包括 status、fingerprint、requirements、findings、coverage 和 can_claim_full_review。退出码 0 表示当前阶段满足检查条件；1 表示缺口、问题、未知或过期；2 表示无法读取或记录契约无效。

before-write 只检查当前适用的准备条件，不要求新项目在编码前已经运行。delivery 检查当前范围的全部要求；design 只判断方案交接准备情况，不产生运行通过声明。

coverage 从原始记录计算，不另维护手工完成数量。只有非空且明确完整的全量清单、对应当前条件的实际页面观察及其余必检要求完成，can_claim_full_review 才可能为 true。记录一致不等于独立证明工具已运行或视觉合格。
