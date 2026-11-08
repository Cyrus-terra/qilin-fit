# qilin-fit

**让 Agent 在开发时就考虑麒麟 Linux 与奇安信浏览器兼容，而不是页面出问题后再打补丁。**

适用于 **CodeBuddy Code、Claude Code、Codex、Gemini CLI、Hermes Agent 和 OpenClaw**。六个客户端共用同一份 Agent Skill，并提供原生插件 / 扩展封装及独立 Skill 安装方式。覆盖 CSS、JavaScript、组件库、构建产物，以及中文字体、输入法、弹窗、下载和打印等问题。

## 安装：把仓库地址交给 Agent

不需要自己下载文件、找安装目录或输入命令。复制下面这段话给你正在使用的 Agent，并附上**本仓库实际的 GitHub 地址**即可：

```text
请安装这个 GitHub 仓库中的 qilin-fit：
【在这里粘贴仓库地址】

先阅读 README.md 和 INSTALL.md，再按 INSTALL.md 操作。
默认只为你当前使用的 Agent 做用户级安装，供以后不同项目使用。
请先说明安装位置；修改全局提醒配置前让我确认。
不要替我默认启用任何业务项目，也不要覆盖已有配置。
```

Agent 会负责获取仓库、检查环境和安装。安装工具需要 Python 3.9+，无需额外 Python/npm 包；如果环境缺少依赖或权限，由 Agent 说明，不会擅自修改系统。下载、执行脚本和写入文件时，客户端可能要求你批准权限。

**CodeBuddy、Claude、Codex、Gemini 可在安装时单独同意开启“新项目提醒”。** 如果不同意，只安装 Skill，仍可手动调用；Hermes / OpenClaw 不自动配置通用全局提醒，需在实际加载的项目上下文中显式使用。安装后按客户端提示刷新技能或重启会话。

> 仓库地址只是安装来源，不能让客户端自动执行代码；仍需要 Agent 能访问仓库和本地文件，并按指引完成安装。不会因为打开 GitHub 页面就自动安装。

## 多 Agent 客户端兼容

这里的多 Agent 指不同 AI 客户端的安装与加载兼容，不是自动开启并发子代理。每个客户端选择**原生插件 / 扩展或独立 Skill 中的一种**，不要重复安装同名副本。

| 客户端 | 原生封装 | 独立 Skill 默认用户级目录 | 自动项目级安装 | 可选全局提醒 |
| --- | --- | --- | --- | --- |
| CodeBuddy Code | plugin + marketplace | `~/.codebuddy/skills/qilin-fit/` | 支持 | `~/.codebuddy/CODEBUDDY.md` |
| Claude Code | plugin + marketplace | `~/.claude/skills/qilin-fit/` | 支持 | `~/.claude/CLAUDE.md` |
| Codex | plugin + 仓库 marketplace | `~/.agents/skills/qilin-fit/` | 支持 | `$CODEX_HOME/AGENTS.md`，默认 `~/.codex/AGENTS.md` |
| Gemini CLI | extension | `~/.gemini/skills/qilin-fit/` | 支持，需信任项目 | `~/.gemini/GEMINI.md` |
| Hermes Agent | plugin + Skill 注册 | `~/.hermes/skills/qilin-fit/` | 按版本、信任与 profile 手动核实 | 不自动配置 |
| OpenClaw | plugin + 无依赖 JS 入口 | `~/.openclaw/skills/qilin-fit/` | 按实际 workspace 手动核实 | 不自动配置 |

用户级默认布局可用 Python 3.9+ 安装；以下从已获取的本仓库根目录执行，默认只选择实际使用的客户端：

```sh
python3 scripts/install.py --scope user --agent gemini --dry-run
python3 scripts/install.py --scope user --agent gemini
```

`--agent all` 表示全部六客户端，仅用户级独立安装可用；不是“当前范围支持的部分客户端”。项目级安装和全局提醒请显式选择支持的客户端。Hermes 自定义 profile、OpenClaw 状态目录 / workspace 以及其他自定义布局需先核实，不能照默认路径盲写。

原生封装不自动配置全局提醒，不执行项目启用，也不注册会话 Hook。原生安装、刷新与验证步骤见 [手动安装与维护](MANUAL.md#原生插件与扩展)，Agent 操作流程见 [INSTALL.md](INSTALL.md)。仓库提供的是封装，不代表已进入官方市场、npm 或 ClawHub；本地包检查也不等于六客户端端到端验证。

## 安装后怎么用

开启新项目提醒后，在新项目第一次相关开发时，Agent 应询问：

> 是否为当前项目启用 qilin-fit 麒麟 / 奇安信兼容开发约束？

| 你的选择 | 后续行为 |
| --- | --- |
| **启用** | 自动配置项目规则，后续相关开发无需重复强调兼容要求 |
| **不启用** | 记住本项目的选择，不再自动询问或配置 |
| **稍后决定** | 不启用，本会话不反复追问，下次仍可确认 |

六个客户端共用项目根目录的 `.qilin-fit.json` 决定；它可以作为团队约定随仓库提交，不是每位成员分别选择。启用项目后，Agent 仍会确认实际浏览器版本，不能默认所有奇安信都是 Chromium 102。

之后直接提出需求即可：

> 新增一个设置页面，包含表单和保存弹窗。

Agent 在已启用项目中应按兼容要求实现、检查并修复代码，而不只是输出一份检测报告。只读检查工具本身不会自动改代码。

## 想改决定？直接告诉 Agent

- “为当前项目启用 qilin-fit。”
- “停用当前项目的 qilin-fit，以后不要再询问。”
- “重置当前项目的 qilin-fit 选择，下次重新确认。”
- “查看当前项目是否启用了 qilin-fit。”
- “关闭所有新项目的 qilin-fit 提醒，保留已有项目的选择。”

若未自动加载，可显式调用：CodeBuddy / Claude 独立版使用 `/qilin-fit`，插件版通常为 `/qilin-fit:qilin-fit`；Codex 使用 `$qilin-fit` 或 `/skills`；Gemini 使用 `/skills list`、`/skills reload` 后要求使用 qilin-fit；Hermes 独立版使用 `/qilin-fit`，插件版通过 `skill_view("qilin-fit:qilin-fit")`；OpenClaw 先用 `openclaw skills list` / `openclaw skills check` 确认，再要求使用 qilin-fit。以宿主实际列出的名称为准。

## 能解决什么

- **样式与布局**：现代颜色、Tailwind、选择器、视口单位、容器查询、弹窗定位、主题和打印。
- **JS 与构建**：语法转换、运行时 API、依赖、动态分包、Worker 和浏览器交付产物。
- **麒麟平台差异**：中文字体、输入法、CPU/GPU、缩放、文件下载、PDF、权限及内网部署。
- **验证与交付**：静态风险检查、离线能力探针、真实版本矩阵与真机验收清单。

## 需要知道的边界

- 新项目提醒是用户级 Agent 指令，**不是强制弹窗**；触发依赖客户端加载及执行指令，通常发生在首次相关开发，而非打开终端时。
- 未经同意不配置全局提醒、不启用业务项目；停用只移除本工具管理的规则，不撤回已完成的业务代码修改。
- 产品版本不等于 Chromium 版本，不承诺“全部版本完全兼容”。Tailwind v4 的颜色补丁也不能代表 Chromium 102 已全面支持。
- 静态检查、探针和普通 Chrome 测试不能替代目标麒麟 / 奇安信真机验收；本项目没有宣称完成厂商认证。

## 更多说明

- [给 Agent 的安装指引](INSTALL.md)：获取仓库后如何安全安装、配置提醒与验证结果。
- [手动安装与维护](MANUAL.md)：命令、安装路径、配置细节、检查工具和测试方法。
- [Skill 工作流](skills/qilin-fit/SKILL.md)：Agent 开发时使用的标准入口。
- [兼容依据与参考来源](skills/qilin-fit/references/sources.md)。

反馈问题时，请提供脱敏的系统 / 浏览器版本、最小复现与预期结果，不要上传账号、Cookie、令牌或真实业务数据。

## 开源许可

[MIT](LICENSE)。独立社区工具，非麒麟或奇安信官方产品。
