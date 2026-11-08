# 视觉参考

新增页面类型或明显重做布局时，先找已确认的同类页面。缺少时，选 1–2 个具体页面或组件实现，记录借鉴的信息组织、交互关系、视觉选择及适用限制。

编码前明确区域、阅读顺序、主操作位置和必须同时可见的信息。外部源码采用前核对版本兼容性与许可；参考中的内容、图表、主题和实现偏好要按当前任务重新判断。

## 布局与业务组合

- [shadcn/ui Blocks](https://ui.shadcn.com/blocks?category=dashboard)：侧边栏、页头、数据表格与内容区的整体组合；组件使用 Base UI 版本。
- [Ant Design 数据列表](https://ant.design/docs/spec/data-list/)：表格、列表、卡片的选择及搜索、筛选、操作组织；属于参考及存量兼容，不改变当前默认栈。
- [BoardUI](https://www.boardui.com/)：后台、看板、Agent 界面的组件组合。
- [Watermelon UI](https://ui.watermelon.sh/)：基础组件、业务区块与完整页面组合。
- [HeroUI Pro](https://heroui.pro/)：复杂表单、表格、弹层和模板的一致性。
- [Plane 布局](https://docs.plane.so/core-concepts/issues/layouts)：按任务选择视图，组织对象与业务属性。

## 层级、间距与交互

- [Linear 改版](https://linear.app/now/behind-the-latest-design-refresh)：主内容优先、视觉权重、稳定操作位置及图标使用。
- [Carbon Spacing](https://www.carbondesignsystem.com/building-blocks/foundations/spacing/overview)：用间距、对齐和留白表达关系与层级。
- [Vercel Web Interface Guidelines](https://vercel.com/design/guidelines)：键盘、焦点、加载、表单和界面细节；其库偏好不能覆盖当前任务和项目选择。
- [beUI](https://beui.dev/)：按钮、分页、Tabs、头像组及提示的交互动效。
- [Fluid Functionalism](https://www.fluidfunctionalism.com/)：悬停、焦点及状态切换的动效。
- [ThreeUI](https://github.com/MengTo/threeui)：有需要时参考 3D/WebGL 交互组件。

每次只读取相关来源，实际使用时核查具体对象。没有访问或观察到的参考不能声称已核对。
