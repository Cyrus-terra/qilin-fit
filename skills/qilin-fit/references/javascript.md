# JavaScript 与 Web API

## 三类兼容问题先分开

| 类型 | 典型表现 | 可采用手段 |
| --- | --- | --- |
| 语法解析 | 页面启动前 SyntaxError，入口都没有执行 | 真实 targets 下的转译、替换不支持语法 |
| 运行时内建 | `toSorted is not a function` 等 | 业务替代、按需 ponyfill/polyfill、降低依赖要求 |
| 浏览器 API | 对象不存在、权限拒绝、网络或策略阻断 | 能力和行为检测、权限流程、替代交互 |

语法转译不等于补齐内建，也不等于模拟所有 Web API。
运行前不支持的语法会令整个脚本解析失败，不能靠脚本内部 if 分支保护。
服务端 Node 能执行，不代表浏览器能执行；反之亦然。

## 浏览器与服务端边界

1. 标记页面入口、动态分包、worker、Service Worker 和第三方脚本。
2. 区分服务端专用代码、构建时脚本、SSR 代码与客户端共享模块。
3. 检查共享依赖是否引用 Node 的 `fs`、`net`、`process` 或其他专用能力。
4. 不把 Node 内建模块 polyfill 当作浏览器具有文件系统或网络原始权限。
5. SSR 不在模块顶层无条件读取 `window`、`document`、`localStorage`。
6. 浏览器 API 按正确生命周期访问，避免服务端渲染与客户端 hydration 不一致。
7. 检查时区、语言、随机值和日期格式是否导致 SSR 文本不匹配。
8. 不因运行环境保护而把鉴权、密钥或可信业务判定移入客户端。

## 构建目标要落到产物

- 使用已确认的最低内核配置浏览器 targets，不能把未知版本默认为 102。
- Browserslist 是否被 Vite、Babel、CSS 工具实际读取，需逐项确认。
- Vite 的 `build.target` 主要约束语法转换，不自动提供所有运行时能力。
- Vite 的 CSS target 与 JS target、worker 构建目标分别核实。
- Babel `preset-env` 的 targets 与 core-js 注入模式按项目版本核对。
- Babel 7 的 `useBuiltIns`/`corejs` 配置不直接套用于 Babel 8；后者按官方文档使用独立 polyfill 插件。
- TypeScript 的 `target` 决定部分输出语法，`lib` 只是类型声明集合。
- 在 TypeScript 中勾选新 lib，不会让目标浏览器生成对应 API。
- 检查依赖中的预构建 ESM、外置 CDN 脚本、动态 import 与插件输出。
- 检查生产压缩器是否生成目标不支持的语法。
- 验证打包器对特定语法的转换限制；不保证所有语法都能降级。
- 修改配置后检查最终 JS，而不只检查配置文件是否含某个版本号。
- 构建器升级会改变默认目标，必须复查锁定版本与发行说明。

参阅 [Vite 构建文档](https://vite.dev/guide/build.html)、[Babel preset-env](https://babeljs.io/docs/babel-preset-env)、[TypeScript target](https://www.typescriptlang.org/tsconfig/target.html)。

## 少量定位用版本参考

下表仅指上游 Chrome 的对应条目，不是厂商承诺，也不是完整 API 清单。
版本来自 [MDN BCD](https://github.com/mdn/browser-compat-data)，更新前核对当前数据及子条目。

| 能力 | 上游 Chrome 起点 | 注意 |
| --- | --- | --- |
| `Array.prototype.at()` | 92 | 其他对象上的同名方法分别查证 |
| `Object.hasOwn()` | 93 | 避免把原型链检查当等价替代 |
| `structuredClone()` | 98 | 不等价于 JSON 序列化复制，核对可克隆类型和 transfer |
| `Array.prototype.toSorted()` / `toReversed()` / `toSpliced()` / `with()` | 110 | 非变异语义，不直接替换成原地修改方法 |
| `Promise.withResolvers()` | 119 | 依赖包可能在初始化时直接调用 |
| `Array.fromAsync()` | 121 | 异步迭代、顺序和异常语义需保留 |

不要为未查证的 API 编造统一“ES202x 对应 Chrome xx”表。
同一标准版本中的各项能力可能有不同支持时间。
`Temporal`、新 Intl 子能力、正则扩展、import attributes 等需按精确条目查证。

## polyfill 的边界

- 优先确认调用是否必需；不为未使用能力引入全量补丁包。
- ponyfill 可降低全局污染，但依赖直接调用全局 API 时仍需处理。
- 确认补丁在依赖执行前加载，覆盖动态路由与 worker 的独立作用域。
- 检查许可证、包体、性能和 CSP，不静默追加远程 CDN。
- 原生能力存在但有差异时，不能仅以 `typeof` 为证据。
- 无法完整模拟的能力必须有降级方案或明确最低浏览器要求。
- `BigInt` 的语法与运算语义不能靠普通内建 polyfill 无损补齐。
- 大整数不得转成 Number 而丢失精度；JSON 传输需明确约定。
- 不用 JSON 往返实现通用 `structuredClone`，它会丢失类型并可能失败。
- 不用移除安全检查、禁用证书验证或放宽 CSP 作为“兼容补丁”。

## 模块、worker 与 WebAssembly

- ES modules、动态 import、top-level await、import maps 分别核对支持。
- 解析失败要定位具体文件；分包 404 或 MIME 错误不能误判成语法不支持。
- Worker 分 classic 与 module，检查构建输出、URL、同源/CORS 与 CSP。
- `new Worker(new URL(..., import.meta.url))` 是否被构建工具正确处理需看产物。
- SharedWorker 与 Service Worker 不是 DedicatedWorker 的可互换替代。
- 测试 worker 启动、消息传递、transfer、异常和退出，不只测构造函数存在。
- WebAssembly 基础能力、SIMD、threads、异常等扩展分别查版本与架构。
- Wasm threads 常涉及 SharedArrayBuffer 和跨源隔离，核查 COOP/COEP 与依赖资源。
- 核查 Wasm MIME、CSP 限制及 streaming 加载；有无后备取决于具体库。
- GPU、音视频与高性能路径需真机检查，不能由 V8 版本推断。

## Intl、时间与文本

- 核查所需 locale、数字、货币、日期格式和 ICU 数据实际表现。
- `Intl.Segmenter`、`Intl.DisplayNames` 等分别测试，不以 `Intl` 存在推定全部可用。
- 不依赖非标准日期字符串解析；使用明确协议、时区与非法值处理。
- `Temporal` 必须单独查目标版本并决定库或替代，不能假定现代浏览器都有。
- Unicode、emoji、组合字符的截断和长度不能仅以 UTF-16 code unit 代替。
- 需要精确金额、时间或标识时，定义服务端与前端一致的数据协议。

## Web API、存储与权限

- 对 Clipboard、文件选择器、定位、通知、摄像头分别查安全上下文和用户激活要求。
- 对存在的 API 处理拒绝、取消和策略阻断，不循环强制请求权限。
- `fetch`、AbortController、Streams 及其子方法分开检查。
- WebSocket/SSE 的失败可能来自代理、认证或空闲超时，先看网络证据。
- localStorage 可能因策略或配额失败；IndexedDB 要测升级、事务与存储受限情形。
- 私密窗口、受管配置和存储清理会改变持久性；不能承诺永不丢失。
- 权限 API 支持与权限名称支持不一致时，使用真实业务操作验证。
- Cookie 的 SameSite、Secure、第三方限制和单点登录需整链路验证。
- 不把 API 不存在、权限拒绝、后端失败三类错误合并成一个“浏览器不支持”。

## 可选的 AI/结构化数据路径

只有项目确实消费 AI 输出或外部 JSON 时才启用本节检查。
不强制引入 zod 或任何固定验证库，可复用项目已有边界验证方式。
解析成功不代表结构有效；分别验证字段、类型、范围、枚举和必要关联约束。
解析失败、缺失字段或服务失败必须显示失败/待复核，不静默转成有效评分。
展示外部文本不使用未经净化的 HTML，不执行模型返回的代码或指令。
只发送经授权且最小化的数据；不得为排错上传真实业务数据或凭据。
业务决定以约定的可信服务端逻辑为准，不依赖可篡改的客户端评分。

## 验证完成条件

覆盖首次进入、懒加载、权限拒绝、异常输入、刷新和回退恢复。
记录具体 API、文件位置、目标终端与失败阶段，保存脱敏最小复现。
静态扫描与桌面自动化均不能替代 [真机验收](verification.md)。
