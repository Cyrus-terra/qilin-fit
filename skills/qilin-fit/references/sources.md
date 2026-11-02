# 来源、证据与验证边界

## 如何使用本清单

本技能是工程排查流程，不是浏览器厂商认证，也不承诺所有版本。
来源用于核实具体主张；每次交付仍要依据当前项目与实际终端取证。
在线文档会变更，记录访问日期；需要可重放时锁定 BCD 提交或依赖版本。
本文编制核查日期：2026-11-02。
不复制原始业务数据、私人绝对路径、设备标识或未经授权的日志。

## 浏览器厂商官方发布信息

### Chromium 93 与先锋版 3.0

- 来源：[速度最高提升23%！奇安信可信浏览器率先更新至Chromium93内核](https://www.qianxin.com/news/detail?news_id=1164)。
- 发布日期：2021-07-06。
- 可确认：文末明确提到麒麟应用商店上架基于 93 内核的先锋版 3.0。
- 边界：不能推导其他 3.x、所有架构或所有渠道都采用该内核。
- 边界：历史上架事实不能证明当前商店版本或现场安装版本。

### Chromium 102

- 来源：[硬核推新！奇安信可信浏览器率先升级至Chromium102内核](https://qianxin.com/news/detail?news_id=4995)。
- 发布日期：2022-05-31。
- 可确认：先锋版升级至 Chromium 102，并曾在麒麟应用商店上架。
- 边界：正文未提供可映射的数字产品版本，不补写虚构版本号。
- 边界：不能认定所有奇安信浏览器最低内核都是 102。

### Chromium 132

- 来源：[持续领先！奇安信可信浏览器率先升级至Chromium132内核](https://qianxin.com/news/detail?news_id=12893)。
- 发布日期：2024-12-25；文内叙述 12 月 17 日升级。
- 可确认：先锋版升级至 Chromium 132，并曾上架所述应用商店。
- 边界：未给出数字产品版本，也不是各架构/渠道同步更新的证明。
- 边界：宣传中的广泛能力表述不能代替具体 API 支持表与实测。

以上只使用技术发布事实，不据新闻中的其他表述推导工程结论。
93、102、109、120、132 在本技能中也可作为测试档位；测试档位不是产品映射。

## 上游支持数据

### MDN Browser Compatibility Data

- 来源：[mdn/browser-compat-data](https://github.com/mdn/browser-compat-data)。
- 用途：查精确特性条目的 Chrome 支持版本、子功能、标志、部分实现与备注。
- CSS 条目：`css/at-rules/layer.json`、`css/at-rules/container.json`、`css/selectors/has.json`。
- CSS 条目：`css/properties/translate.json`、`css/types/length.json`、`css/types/color.json`。
- JS 条目：`javascript/builtins/Array.json`、`Object.json`、`Promise.json` 等。
- 浏览器 API 通常按接口和成员拆分，不以文件片段没出现就断言不存在。
- 查到 `mirror` 要沿继承关系解析，不能将其直接当版本号。
- 支持项可能是数组，需检查版本移除、flags、prefix 与 partial_implementation。
- `version_added: true` 不等于已知具体起点；`false` 不等于未来永不支持。
- 不把跨浏览器 Baseline 日期误读为 Chrome 的首次支持版本。
- 边界：BCD 描述上游浏览器，不能证明厂商分支、CPU、驱动与策略下的实际行为。

### CSS 自定义属性

- 来源：[MDN：Using CSS custom properties](https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_cascading_variables/Using_CSS_custom_properties)。
- 用途：核对 `var()` 后备、继承与计算值阶段无效的行为。
- 边界：变量存在而替换后的值不适用于目标属性，后备并不自动生效。
- 边界：`@supports` 可支持渐进增强，不保证最终渲染、色彩或可访问性正确。

### 结构化复制

- 来源：[MDN：Window.structuredClone()](https://developer.mozilla.org/en-US/docs/Web/API/Window/structuredClone)。
- 用途：核对支持类型、transfer 行为、异常与深复制语义。
- 边界：JSON 往返不是等价替代；window 与 worker 作用域分别确认。
- 边界：页面正文没有给出具体版本时，应继续查 BCD，而非推测版本。

## 可选工具链与样式框架

### Tailwind CSS

- 来源：[Compatibility](https://tailwindcss.com/docs/compatibility)。
- 来源：[Upgrade guide](https://tailwindcss.com/docs/upgrade-guide)。
- 可确认：v4 核心浏览器基线是 Chrome 111、Safari 16.4、Firefox 128。
- 可确认：官方建议需兼容更老浏览器的项目保留 v3.4。
- 边界：迁往 v3.4 需用户确认、依赖和样式迁移验证，不是机械改版本。
- 边界：不能只替换颜色就宣称 v4 在 Chromium 102 全面可用。
- 边界：技能不依赖 Tailwind；框架缺席时跳过此分支。

### Vite

- 来源：[Building for Production](https://vite.dev/guide/build.html)。
- 用途：核对 `build.target`、模块基础要求与默认不补齐运行时 API 的边界。
- 边界：默认目标随主版本变化，以项目安装版本为准。
- 边界：修改 JS target 不证明所有 CSS、worker 与外部脚本已转换。

### Babel

- 来源：[@babel/preset-env](https://babeljs.io/docs/babel-preset-env)。
- 用途：核对 targets、Browserslist 集成、转换插件与 polyfill 路径。
- 边界：Babel 7 与 Babel 8 不共用所有配置；Babel 8 已移除 `useBuiltIns`/`corejs` 选项。
- 边界：按项目版本使用相应文档与 polyfill 插件，不复制跨大版本配置。

### TypeScript

- 来源：[TSConfig target](https://www.typescriptlang.org/tsconfig/target.html)。
- 用途：区分输出语法目标与类型库声明。
- 边界：`lib` 提供类型知识，不安装运行时实现；类型检查通过不是终端通过。

## 平台依据应从现场补充

麒麟具体发行版/SP、架构安装包、GPU 驱动、输入法与本地组件的支持清单应取自相应官方材料。
本技能不臆造某个厂商下载链接，也不把单篇历史公告当全部平台支持矩阵。
有关国密、证书、代理与企业策略的结论需有部署要求和获准的现场证据。
没有文档或真机证据时写“待确认”，不编造可用性或厂商承诺。

## 证据优先级与冲突处理

1. 实际支持范围由用户授权与交付约定确定。
2. 现场版本与配置决定具体测试组合，不由产品品牌推断。
3. 精确上游条目说明一般支持起点，不抵消实际失败证据。
4. 最小复现与同版本上游对照协助区分厂商、平台和应用问题。
5. 验收结果仅覆盖测试产物、时间、功能和终端组合。

扫描结果是风险清单，不是标准符合性证明，也不是厂商缺陷证明。
现代 CSS 有可靠渐进增强时可以保留，不能把全部现代语法都当阻断。
未知引擎只做风险评审；未经真机复测不得签署全面通过。
发现来源失效、文档更新或结论矛盾，保留不确定性并重新取证。
