---
name: qilin-fit
description: 为国产麒麟 Linux 与奇安信可信浏览器进行前端兼容开发、排错和评审。涉及麒麟、银河麒麟、中标麒麟、奇安信、信创、Qianxin、Kylin、旧 Chromium，或在已声明此目标环境的项目中新增/修改页面、CSS、Tailwind、组件库、JS/TS、构建配置、浏览器 API、字体、弹窗、下载与打印时使用；覆盖源码和构建产物检查、能力降级及真机验证。用户请求初始化、启用、停用或重置 qilin-fit，或首次确认项目兼容约束时也使用。
license: MIT
compatibility: 支持 Agent Skills 的代码 Agent。静态检查需要 Python 3.9+；离线探针用目标浏览器打开。必须由用户提供目标设备信息，真机测试不可由静态检查替代。
metadata:
  version: "1.1.0"
  language: zh-CN
---

# 麒麟 / 奇安信前端兼容开发

## 使用原则

把兼容性作为本次实现的约束，不是做完页面再补颜色。此 Skill 适用于新开发、故障修复、依赖升级和评审；不要求特定框架。只处理任务涉及的风险，不无条件改写整个项目。

**不能承诺覆盖所有奇安信版本。** 产品号、发布渠道和 Chromium 内核号不同；同一内核在不同 CPU、驱动和企业策略下也可能表现不同。未知信息必须标记待确认，不能伪造验证记录。

## 0. 先检查项目决定，只确认一次

1. 确定当前业务项目根目录；单仓/多仓/嵌套项目有歧义时先询问，不盲目使用父工作区或最外层 Git 根。
2. 读取根目录 `.qilin-fit.json`，或用本 Skill 的 `scripts/setup.py --target <已确认项目根> --decision status` 查询。状态缺失为 unknown，损坏/未知格式须报告，不擅自覆盖。
3. **enabled**：继续后续兼容工作流；相关开发无需用户每次重复声明。**disabled**：停止自动兼容流程，不重复询问、不自动配置。用户显式要求本次兼容检查/修复时可按本次授权执行，但不悄悄改变长期决定。
4. **unknown**：通过 Agent 的用户对话提问：“是否为当前项目启用 qilin-fit 麒麟 / 奇安信兼容开发约束？启用会配置项目级规则；不启用会记住决定，不再自动询问；也可稍后决定。”只明确同意写 enabled，只明确拒绝写 disabled；取消或未回答保留 unknown，本会话不反复追问，先继续不依赖兼容约束的原始任务。
5. 用户确认后，运行下面明确决定的命令；Agent shell 常为非交互，不要依赖脚本的 stdin 提问。`--agent` 选择当前/用户授权的客户端；要覆盖多个客户端先说明会更新哪些项目指令。不知道用哪个客户端时询问。

```sh
# 先替换占位符为已确认路径，enable 仅在用户明确同意后执行
python3 "<skill-dir>/scripts/setup.py" --target "<project-root>" --agent "<当前且获授权的客户端>" --decision enable
# 明确拒绝：记录 disabled 并移除本工具管理的项目规则块
python3 "<skill-dir>/scripts/setup.py" --target "<project-root>" --decision disable
# 用户主动要求重新确认时才 reset；不能用升级/重装自动清除拒绝
python3 "<skill-dir>/scripts/setup.py" --target "<project-root>" --decision reset
```

上面的客户端占位符为 `codebuddy`、`claude`、`codex`、`gemini`、`hermes` 或 `openclaw`；只有说明并获准覆盖六客户端时才使用项目配置器的 `--agent all`。项目规则对应 `CODEBUDDY.md`、`CLAUDE.md`、`GEMINI.md` 及 Codex/Hermes/OpenClaw 共享的 `AGENTS.md`；按路径去重。Hermes/OpenClaw 需核实宿主确实加载业务根的 AGENTS.md，Gemini 自定义上下文文件名也需核对；写入成功不代表宿主已加载。

配置器保留块外指令，不改依赖/业务代码。enable/disable/reset 是项目配置更改，应与用户已确认范围一致；`--dry-run` 可预览。明确要求“仅本次检查，不启用项目规则”的任务可直接做只读审计，不能借此持久启用。

用户级安装还需可选全局提醒，才能在此前未接触的新项目第一次相关开发时询问；仅复制标准 Skill 不具备启动/安装回调。`setup.py --global-reminder` 仅自动支持 `codebuddy`、`claude`、`codex`、`gemini`，必须显式选当前/获授权客户端；全局 `all` 会因包含不支持项报错。提醒必须另外获得授权，不因为本项目同意就修改全局。Hermes/OpenClaw 不猜写用户级 profile/workspace，需显式加载或使用已核实的项目上下文。该入口依赖宿主加载用户级指令，不是强制弹窗或钩子。

独立版与原生插件/扩展版共用本入口，每客户端二选一。插件封装不注册会话 Hook，不自动启用项目。CodeBuddy/Claude 独立版通常 `/qilin-fit`、插件版 `/qilin-fit:qilin-fit`；Codex `$qilin-fit` 或 `/skills`；Gemini `/skills list`、`/skills reload` 后要求使用；Hermes 独立版 `/qilin-fit`、插件版 `skill_view("qilin-fit:qilin-fit")`；OpenClaw 用 `openclaw skills list` / `openclaw skills check` 确认后要求使用。以宿主实际发现名称为准；支持模型不同不会改变安装格式。

## 1. 先确定支持契约

1. 优先复用项目已有支持契约、构建配置和兼容测试，保留用户改动。基线和环境未变时，不重复收集设备信息、建立矩阵或运行探针。
2. 首次确定基线或目标环境变化时，从用户、浏览器“关于”页收集产品/渠道、完整产品与 Chromium 版本、麒麟版本/SP 和 CPU 架构；DPR/缩放、字体/GPU、企业策略只按相关风险补充，必要时使用 `assets/browser-probe.html`。UA 只作线索，不能证明实际内核。
3. 首次兼容专项或发布验收时，建立或更新项目支持矩阵；无现成文件时，可使用 `assets/support-matrix.example.json`。记录必需功能、最低实际内核及降级验收标准；日常修改不强制新增矩阵文件，不在 Skill 目录记录业务设备数据。
4. 缺失信息会影响本次实现时再询问；未知基线不能擅自等同 Chromium 102。用户要求先开发时可暂定保守基线，但必须标记 **provisional / 未验证**，不得写“已兼容全部版本”。
5. 首次确定或调整支持范围时读取 [浏览器矩阵](references/browser-matrix.md)。发布验收覆盖实际承诺的版本、渠道和架构；日常修改按第 4 节选最小验证范围，不能靠仅测最新 Chrome 宣称目标真机通过。

## 2. 只读审计，确定最小改动

- 读实际源码和生产构建配置，确认 CSS 工具、UI 库、浏览器/服务端入口、第三方包以及部署方式。
- 按改动选读参考资料，不必每次加载全部文件：

| 任务 | 必读 |
| --- | --- |
| 样式、Tailwind、布局、主题、弹窗 | [CSS 与布局](references/css.md) |
| JS/TS、语法编译、依赖、Web API | [JavaScript 与构建](references/javascript.md) |
| 字体/输入法、文件、PDF、权限、网络、CPU/GPU | [麒麟平台与交付](references/platform.md) |
| 测试、截图、发布验收、数据边界 | [验证与验收](references/verification.md) |
| 查证特性支持或版本依据 | [来源与证据等级](references/sources.md) |

- 需要定位兼容风险时，从 Skill 实际安装路径执行检查器，优先传入改动文件或受影响目录；不因加载 Skill 就扫描整个项目。`<skill-dir>` 表示当前 `SKILL.md` 所在目录，先替换为已确认的实际路径，不要照抄占位符：

```sh
# 仅示例：替换为本次改动文件；可传多个路径
python3 "<skill-dir>/scripts/compat_audit.py" ./src/components/Dialog.vue --min-chromium 102
```

只有支持契约已确定为 102 时才使用示例中的 102；未确定时省略 `--min-chromium`，输出会标记 unknown。路径按真实项目替换。检查器只读、零第三方依赖、不会修改代码；它是词法候选检测，不是 AST、CSS 编译器或兼容性认证。

## 3. 实现规则

### CSS

- 稳定路径优先使用常规 hex/rgb/hsl、传统 `transform`、可回退的布局；现代特性仅在目标支持或可证明渐进增强时使用。
- 针对 102：重点检查 `:has()`、容器查询、新视口单位、独立变换、现代颜色、原生嵌套、Popover 与 Tailwind 生成代码。支持阈值与替代见 CSS 参考。
- Tailwind v4 官方最低 Chrome 111；102 不在支持范围。不能声称调色板补丁、Autoprefixer 或设置 JS target 就解决全部 v4 兼容性。提出受支持方案或经过验证的产物转换；迁移/降级依赖须先确认，不擅自执行。
- `var()` 的 fallback 不等于任意现代颜色回退；`CSS.supports()` 不等于实际像素正确。分别检查解析、计算值和视觉结果。
- 改弹窗定位时保留动画与拖拽的 transform 合成；检查遮罩、焦点、滚动、键盘、Portal 和层叠上下文，不只检查居中截图。

### JS / 依赖

- 区分语法转译、内置对象 polyfill 和需要权限/原生平台支持的 Web API。TypeScript `target`、`lib`、构建 `target` 不能互相替代。
- 对浏览器交付链配置真实最低内核，检查依赖、动态 chunk、worker、第三方脚本及 CSS 产物；Node 服务端 API 不能当作浏览器 API 使用。
- 新 API 在入口处能力检测，采用业务可接受的降级；语法解析失败发生在检测之前，不能用 `if` 包住新语法代替转译。
- 不 blanket 禁用可选链等已支持能力，也不默认补全全部 polyfill。不得为了兼容关闭 CSP、证书验证、沙箱或其他安全措施。

### 平台 / 数据

- 按改动涉及的能力选择字体、中文输入法组合事件、架构/GPU、下载/打印、文件名、代理/证书、离线部署或企业权限策略检查，不将平台清单作为每次必测项。
- 涉及外部/AI 数据时，在边界按实际 schema 校验并展示明确失败/缺失状态；不要把未知评分静默补成有效分数，也不强制引入指定校验库。与浏览器无关的业务改动不扩大范围。

## 4. 按变更风险选择验证

遵循项目已有必需检查；下列三档不是每次顺序执行的清单。加载 Skill 本身不触发测试、构建或探针。

| 档位 / 触发 | 最小验证范围 |
| --- | --- |
| 日常修改：文案、局部样式、未改变兼容机制的业务逻辑 | 检查改动文件、受影响布局或行为，复用相关现有测试；仅有具体兼容风险时扫描相关文件。不默认全量单测/lint、生产构建、产物扫描、探针或终端矩阵。 |
| 兼容专项：修复兼容故障、新增浏览器能力，或修改依赖、构建目标、转译、polyfill、共享主题/样式 | 扫描受影响源码；涉及生成代码或构建转换时生产构建并检查相关 CSS/JS 产物。复测原故障和相邻路径，选择最低基线及受影响终端；仅在能力未知或环境变化时补探针。 |
| 正式发布兼容验收：用户要求、项目发布门禁或支持范围变化 | 按 [验证与验收](references/verification.md) 裁剪实际交付矩阵，检查生产产物和核心流程；只对项目使用且本次需验收的能力安排截图、键盘、输入法、缩放、打印等检查。 |

- 扫描产物时使用 `--include-build`，确认路径是实际浏览器交付代码而非源码映射或 Node 服务端包；记录必要的误报、豁免和未覆盖范围。不凭配置推断转换有效。
- 同一代码、配置与环境下复用已有有效证据，包括其他 Skill 执行的检查；无新改动或未解决风险，不重复跑同一命令。不为无关业务改动重复 AI/schema 校验测试。
- 普通 Chrome、Playwright 的近期 Chromium 或伪造 UA 不能替代目标真机。缺少所选档位需要的环境或检查失败时，说明未验证项与影响；不为日常修改制造整套验收阻塞，不生成虚假截图或成功结论。

```sh
# 兼容专项/发布需要产物检查时，替换为真实受影响的浏览器产物路径
python3 "<skill-dir>/scripts/compat_audit.py" ./dist --include-build --min-chromium 102 --format json
```

对候选风险设置 `--fail-on warning` CI 闸门是可选项目决定，不是默认步骤；先处理误报和有证据的渐进增强。

## 5. 交付格式

简短输出：

- **支持契约**：实际版本/架构、最低内核；unknown/provisional 必须注明。
- **修改与依据**：问题、位置、降级/转换方式；引用代码时用 `path:line`。
- **验证结果**：源码、产物、普通浏览器、麒麟真机分别写 pass/fail/not-run，不混为一个“通过”。
- **残余风险**：无法验证的版本、策略/硬件限制及需用户确认的取舍。

Skill 描述用于自动匹配；启用后由配置器合并的项目级指令要求相关开发前加载本 Skill。未确认项目可通过安装器或获准的用户级提醒发起首次确认；disabled 不自动启用或重复询问。Skill 自身不能替代宿主发现机制，也不能绕过权限或强制模型调用。
