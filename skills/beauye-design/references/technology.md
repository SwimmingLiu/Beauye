# 技术选型

这是当前默认值，不自动授权改变存量项目。用户当前要求与明确项目约束优先；同类方案需要选择且无其他约束时，采用下列分工。

## 新项目

- Vite + React + TypeScript：开发与页面实现。
- Base UI：优先用于无样式的交互行为与可访问性底层。
- Tailwind CSS：优先用于样式与状态表达，保留 CSS 变量、design tokens、Grid、Flex 和统一 gap。
- shadcn/ui：采用 Base UI 版本，作为兼容的组件代码与组合层，与 Base UI 配合使用。

Base UI 本身无样式并支持 Tailwind；不能因选用该库就认为页面已经具备视觉设计或已通过可访问性验证。具体组件能力和版本在采用前读取项目与官方资料。

成熟组件是默认实现来源。按[组件复用约定](component-reuse.md)确认实际导入和使用：项目已有业务组件优先，随后选兼容的成熟基础组件，组合为业务组件。库名、相似 CSS 或同名手写控件不能证明复用；Dialog、Tooltip、Switch、Select 等交互不默认自行实现焦点圈、键盘状态机和浮层定位。

## 存量与按需能力

与当前栈兼容的已有业务组件仍优先复用。Ant Design 属于存量项目兼容选项；迁移范围按任务决定，不能从默认值更新推导出整站迁移授权。

需要后端或 SSR 时优先 Fastify + Platformatic Watt，纯前端页面任务无需加入它们。Relay + GraphQL 只在项目数据需求适合时选择，不是所有任务的强制依赖。

XDS 是 X 自有组件库的架构参照，不是本项目必装库。BoardUI、HeroUI Pro、Linear、Carbon 等属于参考来源，也不等于需要全部安装。

Lucide/SVG、Framer Motion、Three.js/WebGL 和 imagegen 按原用途、按需使用；Mermaid、Markdown、HTML 用于文档表达。保留项目尺寸、圆角、间距、品牌与同类页面的已确认约定。

## 选型依据

[X 工程说明](https://blog.x.com/en/engineering/rebuilding-the-global-town-square-from-scratch)、[Base UI](https://base-ui.com/react/overview/about)、[Base UI 样式](https://base-ui.com/react/handbook/styling)、[shadcn/ui 默认底层说明](https://ui.shadcn.com/docs/changelog/2026-07-base-ui-default)。
