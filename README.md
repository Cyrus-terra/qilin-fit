# qilin-fit

面向 **麒麟 Linux + 奇安信可信浏览器** 的前端兼容开发 Skill。采用 [Agent Skills 标准](https://agentskills.io/specification)，同一份内容可供 CodeBuddy Code、Claude Code、Codex 和其他支持该标准的 Agent 使用。

让 Agent 在开发前确认浏览器基线，在实现时规避风险，在交付时区分“源码检查”“产物检查”和“麒麟真机验证”，而不是只给页面加一层 CSS 补丁。

**这是工程工作流和风险检查工具，不是覆盖所有版本的兼容认证。** 不附带奇安信浏览器二进制，也不代表浏览器厂商。

## 覆盖范围

- **CSS / UI**：颜色和变量、Tailwind、嵌套/层/选择器、容器查询、视口单位、弹窗/动画/层叠、布局、字体、主题与打印。
- **JS / 构建**：语法转译、内置对象与 Web API、polyfill、第三方依赖、动态分包、Worker/WASM、SSR 与浏览器边界。
- **麒麟平台**：CPU 架构、GPU/驱动、中文输入法、字体、DPR/缩放、文件下载、PDF、权限、证书/代理与离线部署。
- **验证交付**：真实支持矩阵、只读静态检查、离线能力探针、功能/视觉/无障碍检查、升级和回退。

核心原则：**产品版本 ≠ Chromium 版本；能力存在 ≠ 企业策略允许；构建成功 ≠ 页面正确；最新 Chrome 正常 ≠ 麒麟真机通过。**

## 快速安装

要求 Python **3.9+**，无需 pip/npm 依赖。在下载或克隆得到的本仓库根目录运行（把目标路径换成自己的项目）：

```sh
# 先预览；目标必须是已存在的项目目录
python3 scripts/install.py --target /path/to/your-project --agent all --dry-run
# 复制标准 Skill 到三个 Agent 的项目级发现目录
python3 scripts/install.py --target /path/to/your-project --agent all
# 或仅安装一个 Agent
python3 scripts/install.py --target /path/to/your-project --agent codex
```

不要把示例 `/path/to/your-project` 原样执行。安装器仅创建所选 Skill，不改项目指令、依赖、配置或业务文件；存在同名目录、符号链接目标时拒绝覆盖。更新请先人工比对，不提供强制覆盖。安装中发生磁盘/权限错误可能留下部分新目录，应先检查再重试。

| Agent | 项目级目标 | 用户级目录（手动安装） | 显式调用 |
| --- | --- | --- | --- |
| CodeBuddy Code | `.codebuddy/skills/qilin-fit/` | `~/.codebuddy/skills/` | `/qilin-fit` |
| Claude Code | `.claude/skills/qilin-fit/` | `~/.claude/skills/` | `/qilin-fit` |
| Codex | `.agents/skills/qilin-fit/` | `~/.agents/skills/` | `$qilin-fit`，或 `/skills` 选择 |

用户级安装时，将整个 `skills/qilin-fit/` 目录复制到表中用户级目录，不是只复制 `SKILL.md`。其他 Agent 按其官方 Skill 搜索路径放置同一目录即可。重启 Agent 或按客户端文档刷新技能列表。不要假设 CodeBuddy 会自动扫描 `.claude`，或当前 Codex 必须使用旧的 `.codex/skills` 路径。

### 让开发时自动加载

`description` 已包含中文/英文环境关键词及常见前端任务，默认允许宿主进行隐式匹配。但 **Agent Skills 标准不保证每次自动调用**，实际行为还取决于客户端版本、技能发现范围、模型选择、上下文预算和组织策略。

对明确要支持该环境的业务项目，建议将以下指令**合并**到现有 Agent 项目指令，不覆盖原文件：CodeBuddy 使用 `CODEBUDDY.md`、Claude Code 使用 `CLAUDE.md`、Codex 使用 `AGENTS.md`。需要多客户端支持时分别合并；只在文件不存在时新建。安装器不会替你修改这些文件。

```markdown
## 前端兼容性约束

本项目需兼容麒麟 Linux 与奇安信可信浏览器。
新增或修改页面、CSS、JS/TS、组件库、构建配置、浏览器 API、下载或打印功能前，
必须先加载 qilin-fit Skill，再按其工作流执行。
若技能未被发现，先报告缺失并请求安装，不假装已加载。
先读取本项目支持矩阵；未知版本不得默认为 Chromium 102。
交付时分别报告源码、构建产物和麒麟真机的验证结果，未执行的写明 not-run。
```

这是项目级约束，不是客户端级强制钩子；如需硬性合并门禁，可将扫描器的退出码接入现有 CI，但必须先审查误报/渐进增强，不把它当真机认证。不要设置 `disable-model-invocation: true` 来实现自动调用——该设置恰恰禁用自动匹配。

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
    ├── scripts/compat_audit.py
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
python3 skills/qilin-fit/scripts/compat_audit.py --help
```

提交兼容问题时，请提供已脱敏的系统/架构、产品及实际内核、最小复现、构建信息、预期/实际结果和真机截图；不要上传账号、客户地址、Cookie、访问令牌或原始业务数据。新增支持结论需注明上游来源和真机证据，区分确定性缺口、候选风险与厂商异常。

本目录可作为独立 GitHub 仓库根目录发布；父工作区已有 Git 仓库，本交付不替你初始化嵌套仓库、不提交或推送，也不附带个人路径/客户原始规范。发布前确认 MIT 许可证符合你的开源计划，并审查全部待上传内容。

格式参考：[Agent Skills](https://agentskills.io/specification)、[Claude Code skills](https://code.claude.com/docs/en/skills)、[Codex skills](https://developers.openai.com/codex/skills)。CodeBuddy 的路径与调用机制核对其安装包内 `cli/skills` 文档；客户端升级后以各自当前文档为准。本次文档核实不等于三个 CLI 的端到端实测。

## License

[MIT](LICENSE)。所引用的外部资料归各自权利人所有；项目为独立社区工具，非麒麟或奇安信官方产品。
