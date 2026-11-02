# 手动安装与维护说明

普通用户无需执行本文命令，直接按 [README](README.md) 将仓库地址交给 Agent 即可。本文供手动操作、故障排查与维护使用；Agent 安装流程见 [INSTALL.md](INSTALL.md)。

## 手动安装

要求 Python **3.9+**，无需 pip/npm 依赖。在下载或克隆得到的本仓库根目录运行（把目标路径换成自己的项目）：

```sh
# 先预览；目标必须是已存在的项目目录
python3 scripts/install.py --target /path/to/your-project --agent all --dry-run
# 复制标准 Skill 到三个 Agent 的项目级发现目录
python3 scripts/install.py --target /path/to/your-project --agent all
# 或仅安装一个 Agent
python3 scripts/install.py --target /path/to/your-project --agent codex
```

不要把示例 `/path/to/your-project` 原样执行。安装器复制所选 Skill 后，在交互终端首次询问当前项目是否启用；明确同意后才合并项目规则，拒绝仅记录状态。它不修改业务代码或依赖；存在同名目录、符号链接目标时拒绝覆盖。更新请先人工比对，不提供强制覆盖。安装中发生磁盘/权限错误可能留下部分新目录，应先检查再重试。

| Agent | 项目级目标 | 用户级目录（手动安装） | 显式调用 |
| --- | --- | --- | --- |
| CodeBuddy Code | `.codebuddy/skills/qilin-fit/` | `~/.codebuddy/skills/` | `/qilin-fit` |
| Claude Code | `.claude/skills/qilin-fit/` | `~/.claude/skills/` | `/qilin-fit` |
| Codex | `.agents/skills/qilin-fit/` | `~/.agents/skills/` | `$qilin-fit`，或 `/skills` 选择 |

用户级安装时，将整个 `skills/qilin-fit/` 目录复制到表中用户级目录，不是只复制 `SKILL.md`。其他 Agent 按其官方 Skill 搜索路径放置同一目录即可。重启 Agent 或按客户端文档刷新技能列表。不要假设 CodeBuddy 会自动扫描 `.claude`，或当前 Codex 必须使用旧的 `.codex/skills` 路径。

### 每个项目只确认一次

项目级安装完成后，交互终端会提示是否启用：

| 选择 | 持久状态 | 行为 |
| --- | --- | --- |
| 启用 | enabled | 合并所选 Agent 的项目规则，相关前端开发前加载 Skill |
| 不启用 | disabled | 不增加兼容规则；本项目不再自动询问 |
| 稍后 / 空输入 / 取消 | unknown | 不自动启用；本会话不要反复追问，下次可再确认 |

决定记录在业务项目根的 `.qilin-fit.json`，由三个 Agent 共享，不是每个 Agent 各问一次。文件可随仓库提交作为团队约定；它不是每位成员独立的个人偏好。损坏或未知格式会明确报错，不静默重置。

启用时在所选 `CODEBUDDY.md`、`CLAUDE.md`、`AGENTS.md` 中合并 qilin-fit 标记区块，保留其他内容；停用/重置会从三个文件中移除自己的区块，不删除文件。若新建 `CODEBUDDY.md` 会遮蔽已有 `AGENTS.md`，会保留 `@AGENTS.md` 引用，停用后也不移除此继承关系。检测到并行配置时会提示核对加载优先级。明确启用不代表内核已确认，仍不能默认 102。

非交互安装（例如 Agent 的 shell 工具、CI 或管道）不会等待输入，也不会默认同意。Agent 应通过用户对话确认，再执行明确的启用或拒绝命令；没有回答不能当作拒绝。仅手动复制 Skill 文件夹也没有安装回调，首次加载后才执行确认流程。

### 手动启用、停用、重置与查看

安装后直接运行 Skill 内的配置器，不需要重新复制安装。以下从本仓库根执行；项目内安装后也可把路径换成实际 Skill 所在位置：


```sh
python3 skills/qilin-fit/scripts/setup.py --target /path/to/your-project --agent all --decision status
python3 skills/qilin-fit/scripts/setup.py --target /path/to/your-project --agent all --decision enable --dry-run
python3 skills/qilin-fit/scripts/setup.py --target /path/to/your-project --agent all --decision enable
python3 skills/qilin-fit/scripts/setup.py --target /path/to/your-project --decision disable
python3 skills/qilin-fit/scripts/setup.py --target /path/to/your-project --decision reset
```

`--decision ask` 会读取既有决定：enabled/disabled 不重复询问，unknown 才在交互终端询问。显式 enable/disable/reset 是用户主动更改；reset 才会重新开放下次确认。默认再次安装仍拒绝覆盖已有 Skill，改决定应运行 setup 而不是重装。

旧版本手动添加、没有 qilin-fit 标记的兼容约束不会被自动删除；若停用后仍被其他指令要求兼容，需要人工检查旧规则。标记损坏、冲突、链接文件或不安全路径会拒绝修改。各文件先统一预检，再逐个原子替换；多个文件不具备事务原子性，I/O 失败须检查部分完成状态。

### 新项目也提示：可选用户级安装与全局提醒

仅项目级安装不能发现未来所有新项目。要实现跨项目提醒，需要用户级 Skill 加上用户级指令入口：


```sh
python3 scripts/install.py --scope user --agent all --global-reminder --dry-run
python3 scripts/install.py --scope user --agent all --global-reminder
```

`--global-reminder` 会在交互终端**另行征求授权**；同意才合并用户级指令，拒绝不修改全局指令。不会注册 hooks、不改现有 Agent 设置、不运行后台监控。非交互环境保持待确认；明确授权后可手动运行：


```sh
# 修改用户级指令前先预览；去掉 --dry-run 才会实际写入
python3 skills/qilin-fit/scripts/setup.py --global-reminder --agent all --decision enable --dry-run
# 关闭全局提醒，不改已有项目决定
python3 skills/qilin-fit/scripts/setup.py --global-reminder --agent all --decision disable
```

全局提醒合并位置：CodeBuddy 的 `~/.codebuddy/CODEBUDDY.md`、Claude Code 的 `~/.claude/CLAUDE.md`、Codex 的 `$CODEX_HOME/AGENTS.md`（默认 `~/.codex/AGENTS.md`）。注意 Codex 的**指令目录**与 `~/.agents/skills/` 的**技能目录**不同。

全局提醒要求 Agent 在首次相关开发前确定实际业务项目根并检查状态；unknown 先问，disabled 跳过且不再问，enabled 按规则开发。不要把父工作区、主目录或嵌套项目随意视为同一个项目；根目录不明确时先确认，不能盲目用最外层 Git 根目录。

此适配使用用户级指令，而不是启动时强制弹窗：它依赖客户端加载指令及模型执行，通常在用户第一次提出相关开发任务时询问，不保证打开终端就弹出。组织策略、指令覆盖或客户端限制可能影响触发；未发现 Skill 时应报告缺失，不伪装成功。Claude 自定义配置目录等非默认布局需要按客户端当前文档手工适配；不要误写到未生效的默认位置。Codex 若存在非空 `AGENTS.override.md` 遮蔽用户级 `AGENTS.md`，配置器会拒绝声称启用成功，须先人工处理指令优先级。

本仓库开发和测试只使用临时目录，**没有实际修改你的用户级 Agent 指令或启用业务项目**。自动检查和真机验收仍不可被项目规则替代。

## 使用示例

在 Agent 中提出正常开发需求：

> 为这个支持麒麟和奇安信的项目新增设置页。先确认支持矩阵，再检查 Tailwind、弹窗、字体、JS 和下载功能，分别报告自动检查及真机待验收项。

如果自动匹配未发生，用表中显式命令加载，再说明任务。**仅安装到本仓库并不会自动约束工作区所有其他项目**，应安装到实际业务项目或配置用户级技能。

### 只读静态检查

在本仓库根目录运行；以下 102 是**已确认基线时的示例**，不是对所有奇安信浏览器的假设：

```sh
# 源码，未知内核时省略 --min-chromium
python3 skills/qilin-fit/scripts/compat_audit.py /path/to/project/src --min-chromium 102
# JSON；生产包须明确允许扫描构建目录
python3 skills/qilin-fit/scripts/compat_audit.py /path/to/project/dist --include-build --min-chromium 102 --format json
# 自选风险阈值作为退出码门禁
python3 skills/qilin-fit/scripts/compat_audit.py /path/to/project/src --min-chromium 102 --fail-on warning
```

- 默认 `--fail-on none`，发现风险不阻止运行。退出码：`0` 命令成功且未触发选定闸门；`1` 触发风险闸门；`2` 参数、读取或执行错误。**0 不代表兼容通过。**
- 检测源码及生成代码的候选风险，包含特性阈值、位置、依据和评审提示；不是 AST 解析或完整依赖分析。注释、字符串、测试文件、别名和运行时生成代码会造成误报/漏报；有能力检测/渐进增强也仍需人工复核。
- 默认跳过依赖、Agent 配置目录和构建目录；`--include-build` 才检查构建包。不跟随文件或祖先目录的符号链接；如 macOS `/var`、`/tmp` 别名使路径被跳过，先确认真实路径再扫描。默认单文件大小上限 5 MiB，可用 `--max-file-bytes` 调整；检查输出中的未扫描和错误信息。
- 扫描源码目录通常不包含根 `package.json`；评估 Tailwind 版本时应额外把实际 `package.json` 路径传入，检查锁定版本，不能只靠范围声明。
- 详细规则和使用参数以 `--help` 及检查器代码为准；新增风险应同时补测试和参考来源，不靠“禁止所有新语法”维持兼容。

### 离线真机探针

将 `skills/qilin-fit/assets/browser-probe.html` 复制到目标机器，用奇安信打开，无需安装依赖或联网。它提供能力存在性检测、CSS 语法检测、可视对照及手动信息录入，用户点击后才导出本地 JSON。

- 不读取 Cookie、存储内容或业务输入，不发请求、不自动上传，不主动申请权限。导出包含 UA/平台等设备信息，分享前自行审查并脱敏。
- `file://` 与业务 HTTPS 的权限、同源和安全上下文不同；可通过项目批准的 HTTP(S) 测试服务打开同一页面，但**探针仍不会实际执行所有 API**。
- `CSS.supports` 和对象存在不证明渲染正确或 API 可用；probe 的人工字段也不是自动检测证据。必须结合真实项目、控制台/网络、截图和功能验收。
- `support-matrix.example.json` 是待填模板，不是任何设备的测试结果。

## 版本与支持边界

官方资料可确认的历史点包括先锋版 3.0 使用 Chromium 93，以及后续先锋版升级 Chromium 102、132；后两条公告没有给出完整产品版本映射。不能由此推断全部渠道、CPU 架构和麒麟 SP 都一致。见 [浏览器矩阵](skills/qilin-fit/references/browser-matrix.md) 与 [来源](skills/qilin-fit/references/sources.md)。

Tailwind v4 官方最低 Chrome 111；若实际最低内核为 102，不能宣称 hex 覆盖层已让 v4 全面兼容。需要受支持工具链或经过产物/真机验证的转换方案。依赖迁移由项目维护者确认。

没有普适的“所有版本全部问题”清单。新版本、厂商回移特性、策略、内核补丁及硬件差异都需要持续补充证据；未知和未测试必须明确标记。本项目没有声称在真实麒麟/奇安信设备完成认证。

## 目录

```text
.
├── README.md
├── LICENSE
├── scripts/install.py
├── tests/
└── skills/qilin-fit/
    ├── SKILL.md
    ├── scripts/
    │   ├── compat_audit.py
    │   └── setup.py
    ├── assets/
    │   ├── browser-probe.html
    │   └── support-matrix.example.json
    └── references/
        ├── browser-matrix.md
        ├── css.md
        ├── javascript.md
        ├── platform.md
        ├── verification.md
        └── sources.md
```

主入口只使用标准 frontmatter，避免产品专有字段绑死某个 Agent。参考文档按需加载，不把所有规范塞进上下文；安装不需要第三方下载器。

## 开发与发布

```sh
python3 -m unittest discover -s tests -v
# 可选：探针的模拟 DOM 回归需要 Node.js 18+，并非真机测试
node --test tests/test_browser_probe.mjs
python3 scripts/install.py --help
python3 skills/qilin-fit/scripts/setup.py --help
python3 skills/qilin-fit/scripts/compat_audit.py --help
```

提交兼容问题时，请提供已脱敏的系统/架构、产品及实际内核、最小复现、构建信息、预期/实际结果和真机截图；不要上传账号、客户地址、Cookie、访问令牌或原始业务数据。新增支持结论需注明上游来源和真机证据，区分确定性缺口、候选风险与厂商异常。

本目录可作为独立 GitHub 仓库根目录发布；父工作区已有 Git 仓库，本交付不替你初始化嵌套仓库、不提交或推送，也不附带个人路径/客户原始规范。发布前确认 MIT 许可证符合你的开源计划，并审查全部待上传内容。

格式参考：[Agent Skills](https://agentskills.io/specification)、[Claude Code skills](https://code.claude.com/docs/en/skills)、[Codex skills](https://developers.openai.com/codex/skills)。CodeBuddy 的路径与调用机制核对其安装包内 `cli/skills` 文档；客户端升级后以各自当前文档为准。本次文档核实不等于三个 CLI 的端到端实测。

## License

[MIT](LICENSE)。所引用的外部资料归各自权利人所有；项目为独立社区工具，非麒麟或奇安信官方产品。
