# 可选 Codex Hook

适配器是 `scripts/codex_hook.py`，使用同一个 `verification.check_task`。普通使用不需要 Hook；本包不修改全局配置或自动信任代码。

```bash
python3 <skill-dir>/scripts/codex_hook.py --task-dir <task-dir>
```

事件 JSON 从标准输入传入。也可用本次宿主进程的 `BEAUYE_TASK_DIR` 指定任务；没有任务目录时不拦截。任务标识必须属于当前项目，不能把一个任务的准备状态复用到另一项目。

PreToolUse 对支持的相关写入检查模式、路径范围与准备条件。纯评审不能写应用代码；纯设计仅允许方案与任务资料；实现任务的所有已解析写入路径都要落在 change_scope 中。缺少方案或越出范围时返回明确拒绝。PostToolUse 在实际修改后补充复查信息，不能撤销已发生的写入。Stop 在具备检查条件且有待补事项时最多自动续查一次。

路径以项目为基准：普通文件路径精确匹配；已有目录或带尾斜线的路径包含后代；`*`、`?`、`[...]` 匹配单段，`**` 可跨越多段。任务资料和已知生成目录不阻塞；无法解析的写入不能保证覆盖。

续查预算按任务保存，与源码指纹无关；重复事件、源码反复变化和 stop_hook_active 都不能造成持续续跑。工具、角色、数据或观察来源不明时保留未验证，不能靠等待把结果变成通过。

适配器仅运行固定检查器，不执行事件载荷里的任意命令。它略过无关读取、其他项目和任务证据写入；无法可靠解析的 shell 写入不能保证拦截，仍由 Skill 主动调用检查器。

启用前核对实际宿主的事件、工具覆盖、路径和信任状态。当前事件输入输出依据 [OpenAI 官方 Hooks 文档](https://learn.chatgpt.com/docs/hooks)；插件 Hook 的安装与信任另见 [Plugin 打包说明](https://developers.openai.com/plugins/build/plugins)。Hook 不是完整执行边界，不能把这些可选事件当作 Skill 的强制运行前提。
