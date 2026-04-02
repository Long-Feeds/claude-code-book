# 第11章：特色功能拾遗

> 一个软件系统的气质，往往体现在那些不在主干流程上的功能里。本章聚焦 Claude Code 中几个设计独到的组件：任务管理、会话历史、REPL 执行环境、Jupyter 笔记本支持、网络访问、成本追踪、版本迁移以及 Sleep 工具——每一个都藏着值得细品的工程细节。

---

## 11.1 TodoWriteTool：会话内任务管理

### 设计定位

`TodoWriteTool` 不是一个文件系统工具，而是一个**会话内状态管理工具**——它维护的是当前 AI 工作循环中的任务清单，存储在内存中（`AppState.todos`），会话结束后消失。

```typescript
// src/tools/TodoWriteTool/TodoWriteTool.ts:65-69
async call({ todos }, context) {
  const appState = context.getAppState()
  const todoKey = context.agentId ?? getSessionId()
  const oldTodos = appState.todos[todoKey] ?? []
  const allDone = todos.every(_ => _.status === 'completed')
  const newTodos = allDone ? [] : todos
```

一个有趣的设计：当所有任务都标记为 `completed` 时，列表自动清空（`newTodos = []`）。这避免了已完成列表污染后续会话的上下文。

### 触发规则的精细设计

TodoWrite 的提示词对"何时使用"和"何时不用"都有精确规定：

**应该使用的场景**（`src/tools/TodoWriteTool/prompt.ts`）：
- 需要 3 个及以上步骤的复杂任务
- 用户提供了多项任务（编号或逗号分隔）
- 开始一个任务之前先将其标记为 `in_progress`（而不是完成后再回来标记）
- 发现新的后续任务时及时追加

**不应该使用的场景**：
- 单一、直接的任务
- 纯粹的对话或信息查询
- 少于 3 个轻微步骤的任务

这种精细的触发条件设计是行为引导（behavioral steering）的典范：不是禁止或强制，而是通过清晰的边界告诉模型在什么情境下这个工具是有价值的。

### 验证推送机制

代码中有一个有趣的实验性功能（通过 Feature Flag 控制）：当主线程 Agent 关闭一个包含 3+ 项的任务列表，且其中没有"验证步骤"时，系统会在工具结果中追加一条提醒：

```typescript
// src/tools/TodoWriteTool/TodoWriteTool.ts:72-80
let verificationNudgeNeeded = false
if (
  feature('VERIFICATION_AGENT') &&
  getFeatureValue_CACHED_MAY_BE_STALE('tengu_hive_evidence', false) &&
  !context.agentId &&
  ...
```

这是一种"在行为发生的确切时机插入提醒"的设计模式——在任务列表关闭的瞬间推送验证提示，而不是在系统提示词中泛泛要求"要验证"。

---

## 11.2 会话历史：`src/history.ts`

### 历史记录的存储策略

会话历史存储为 JSONL 格式文件，上限为 100 条：

```typescript
// src/history.ts:19-20
const MAX_HISTORY_ITEMS = 100
const MAX_PASTED_CONTENT_LENGTH = 1024
```

### 粘贴内容的引用机制

history.ts 中最精妙的设计是**粘贴内容的引用系统**。当用户粘贴大段文本时，历史记录不直接存储原文，而是存储一个占位引用：

```typescript
// src/history.ts:51-56
export function formatPastedTextRef(id: number, numLines: number): string {
  if (numLines === 0) {
    return `[Pasted text #${id}]`
  }
  return `[Pasted text #${id} +${numLines} lines]`
}
```

历史条目中存储 `[Pasted text #1 +10 lines]` 这样的占位符，而不是完整文本。大段粘贴内容（超过 1024 字节）存入独立的 paste store，并通过内容哈希关联。

这个设计解决了一个实际问题：历史文件中若直接存储大段代码片段，文件会迅速膨胀，加载也会变慢。通过引用+外部存储，历史文件保持轻量，实际内容按需恢复。

图片的处理方式类似，使用 `[Image #N]` 占位符，还原时转换为多模态内容块（content block）。

---

## 11.3 REPL 工具：隐藏的批量执行模式

### REPL 模式的本质

REPL（Read-Eval-Print Loop）工具是一个面向 Anthropic 内部员工（`USER_TYPE === 'ant'`）的特殊执行模式，目前在外部版本中默认关闭：

```typescript
// src/tools/REPLTool/constants.ts:23-30
export function isReplModeEnabled(): boolean {
  if (isEnvDefinedFalsy(process.env.CLAUDE_CODE_REPL)) return false
  if (isEnvTruthy(process.env.CLAUDE_REPL_MODE)) return true
  return (
    process.env.USER_TYPE === 'ant' &&
    process.env.CLAUDE_CODE_ENTRYPOINT === 'cli'
  )
}
```

### "原始工具"隐藏机制

REPL 模式开启时，一组常规工具会从模型的可用工具列表中**隐藏**：

```typescript
// src/tools/REPLTool/constants.ts:37-46
export const REPL_ONLY_TOOLS = new Set([
  FILE_READ_TOOL_NAME,    // FileRead
  FILE_WRITE_TOOL_NAME,   // FileWrite
  FILE_EDIT_TOOL_NAME,    // FileEdit
  GLOB_TOOL_NAME,         // Glob
  GREP_TOOL_NAME,         // Grep
  BASH_TOOL_NAME,         // Bash
  NOTEBOOK_EDIT_TOOL_NAME, // NotebookEdit
  AGENT_TOOL_NAME,        // Agent
])
```

这些工具在 REPL 模式下不是"不可用"，而是"只能在 REPL VM 上下文内访问"。

```typescript
// src/tools/REPLTool/primitiveTools.ts:14-17
/**
 * Primitive tools hidden from direct model use when REPL mode is on
 * (REPL_ONLY_TOOLS) but still accessible inside the REPL VM context.
 */
```

REPL 模式的设计逻辑：强制模型以脚本形式批量执行操作，而非逐步调用单个工具。对于需要大规模文件操作的场景，这能显著提高效率，同时减少 API 往返次数。

---

## 11.4 NotebookEditTool：Jupyter 笔记本的原生支持

### 细粒度 Cell 编辑

`NotebookEditTool` 不是对 `.ipynb` 文件做简单的文本替换，而是理解 Jupyter 笔记本的结构，支持三种编辑模式：

```typescript
// src/tools/NotebookEditTool/NotebookEditTool.ts:50-57
edit_mode: z
  .enum(['replace', 'insert', 'delete'])
  .optional()
  .describe(
    'The type of edit to make (replace, insert, delete). Defaults to replace.',
  ),
```

配合 `cell_id` 字段，可以精确定位到笔记本中的特定 cell 进行操作，而不是替换整个文件。

```typescript
// src/tools/NotebookEditTool/NotebookEditTool.ts:40-48
cell_id: z
  .string()
  .optional()
  .describe(
    'The ID of the cell to edit. When inserting a new cell, the new cell will
     be inserted after the cell with this ID, or at the beginning if not specified.',
  ),
```

### Cell 类型感知

工具支持 `code` 和 `markdown` 两种 cell 类型，并在插入模式下要求显式指定类型，避免歧义。

这个工具的存在说明 Claude Code 的定位不仅限于软件开发，还覆盖了数据科学工作流。

---

## 11.5 网络访问：WebFetch 与 WebSearch

### WebFetchTool：有限的主动抓取

`WebFetchTool` 采取了一种务实的安全策略——**预审批域名列表**（`src/tools/WebFetchTool/preapproved.ts`）：

```typescript
// src/tools/WebFetchTool/preapproved.ts:14-20
export const PREAPPROVED_HOSTS = new Set([
  'platform.claude.com',
  'docs.python.org',
  'developer.mozilla.org',
  'github.com/anthropics',
  'react.dev',
  // ... 130+ 技术文档域名
])
```

这份列表覆盖了主流编程语言文档、框架文档、云服务文档等约 130 个域名。落在此列表内的 URL 无需用户授权即可访问；其他域名需要用户明确批准。

代码中有一处重要的安全注释：

```typescript
// src/tools/WebFetchTool/preapproved.ts:6-11
// SECURITY WARNING: These preapproved domains are ONLY for WebFetch (GET requests only).
// The sandbox system deliberately does NOT inherit this list for network restrictions,
// as arbitrary network access (POST, uploads, etc.) to these domains could enable
// data exfiltration.
```

预审批只适用于只读的 GET 请求，沙盒系统的网络限制不继承此列表——这防止了通过向 HuggingFace、Kaggle 等允许文件上传的域名发送 POST 请求来泄露数据。

权限检查使用域名作为规则内容：

```typescript
// src/tools/WebFetchTool/WebFetchTool.ts:50-64
function webFetchToolInputToPermissionRuleContent(input): string {
  try {
    const { url } = parsedInput.data
    const hostname = new URL(url).hostname
    return `domain:${hostname}`  // 权限规则格式
  } catch {
    return `input:${input.toString()}`
  }
}
```

### WebSearchTool：调用 Claude 的原生搜索

`WebSearchTool` 通过 Anthropic API 的 beta 功能（`BetaWebSearchTool20250305`）实现网络搜索，底层调用的是 Claude 模型自带的搜索能力，而非第三方搜索 API：

```typescript
// src/tools/WebSearchTool/WebSearchTool.ts:3-4
import type {
  BetaWebSearchTool20250305,
} from '@anthropic-ai/sdk/resources/beta/messages/messages.mjs'
```

搜索支持域名白名单和黑名单过滤：

```typescript
// src/tools/WebSearchTool/WebSearchTool.ts:31-37
allowed_domains: z
  .array(z.string())
  .optional()
  .describe('Only include search results from these domains'),
blocked_domains: z
  .array(z.string())
  .optional()
  .describe('Never include search results from these domains'),
```

---

## 11.6 成本追踪：`src/cost-tracker.ts`

### 追踪的维度

成本追踪器记录了丰富的使用指标：

```typescript
// src/cost-tracker.ts:71-80
type StoredCostState = {
  totalCostUSD: number
  totalAPIDuration: number
  totalAPIDurationWithoutRetries: number
  totalToolDuration: number
  totalLinesAdded: number
  totalLinesRemoved: number
  lastDuration: number | undefined
  modelUsage: { [modelName: string]: ModelUsage } | undefined
}
```

除了 API 花费（美元）、API 调用时长，还追踪了**工具执行时长**（`totalToolDuration`）和**代码行变更数**（`linesAdded`/`linesRemoved`）。后两者不是成本指标，而是生产力指标——可以回答"这次会话 AI 帮我改了多少代码"。

### 会话间的成本持久化

成本状态与会话 ID 绑定，存入项目配置（project config），支持恢复：

```typescript
// src/cost-tracker.ts:87-95
export function getStoredSessionCosts(
  sessionId: string,
): StoredCostState | undefined {
  const projectConfig = getCurrentProjectConfig()
  // Only return costs if this is the same session that was last saved
  if (projectConfig.lastSessionId !== sessionId) {
    return undefined
  }
```

这允许在 `--resume` 恢复会话时，从上次中断处继续累计成本，而非重新计数。

### FPS 监控

注意 `saveCurrentSessionCosts` 接受一个 `fpsMetrics` 参数：

```typescript
// src/cost-tracker.ts:143
export function saveCurrentSessionCosts(fpsMetrics?: FpsMetrics): void {
  saveCurrentProjectConfig(current => ({
    ...
    lastFpsAverage: fpsMetrics?.averageFps,
    lastFpsLow1Pct: fpsMetrics?.low1PctFps,
```

Claude Code 还在监控 UI 渲染帧率（FPS）！`low1PctFps` 是"最慢 1% 帧"的帧率指标，用于衡量卡顿情况。这对一个基于 React + Ink 渲染的 CLI 应用来说是相当专业的性能追踪。

---

## 11.7 版本迁移系统：`src/migrations/`

### 迁移文件命名规律

迁移文件列表揭示了产品演进历史：

```
migrateAutoUpdatesToSettings.ts        — 自动更新设置迁移
migrateFennecToOpus.ts                 — 模型别名迁移（Fennec → Opus）
migrateLegacyOpusToCurrent.ts          — Opus 版本迁移
migrateOpusToOpus1m.ts                 — Opus 扩展上下文迁移
migrateSonnet1mToSonnet45.ts           — Sonnet 模型升级迁移
migrateSonnet45ToSonnet46.ts           — Sonnet 4.5 → 4.6 迁移
migrateReplBridgeEnabledToRemoteControlAtStartup.ts  — 功能迁移
```

### 迁移的设计原则

以 `migrateSonnet45ToSonnet46.ts` 为例：

```typescript
// src/migrations/migrateSonnet45ToSonnet46.ts:29-46
export function migrateSonnet45ToSonnet46(): void {
  if (getAPIProvider() !== 'firstParty') return
  if (!isProSubscriber() && !isMaxSubscriber() && ...) return

  const model = getSettingsForSource('userSettings')?.model
  // 只迁移用户通过 /model 主动设置的模型
  // projectSettings 和 localSettings 保持不变
  if (model !== 'claude-sonnet-4-5-20250929' && ...) return
  ...
  updateSettingsForSource('userSettings', {
    model: has1m ? 'sonnet[1m]' : 'sonnet',
  })
```

迁移函数的设计遵循以下原则：
1. **幂等**：多次执行结果相同
2. **保守**：只迁移用户主动设置的值，不动项目/本地配置
3. **分层**：只迁移 `userSettings`，保留项目级配置
4. **可观测**：迁移完成后上报分析事件

这些迁移在 CLI 启动时按序执行，确保老版本的配置文件能够无缝升级。

---

## 11.8 Zod Schema 系统：`src/schemas/`

### 钩子系统的 Schema 设计

`src/schemas/hooks.ts` 定义了钩子配置的完整 Schema，最能体现 Zod 在这个项目中的使用方式：

```typescript
// src/schemas/hooks.ts:32-59
function buildHookSchemas() {
  const BashCommandHookSchema = z.object({
    type: z.literal('command'),
    command: z.string(),
    if: IfConditionSchema(),        // 条件过滤：权限规则语法
    shell: z.enum(SHELL_TYPES),     // bash / powershell
    timeout: z.number().positive(), // 单个钩子的超时
    statusMessage: z.string(),      // 进度条显示文本
    once: z.boolean(),              // 执行一次后自动移除
    async: z.boolean(),             // 异步后台运行
    asyncRewake: z.boolean(),       // 异步完成后唤醒 Agent
  })
```

`if` 条件字段支持权限规则语法（如 `Bash(git *)`），让钩子可以只对特定工具调用触发，避免对每次工具使用都执行钩子造成的性能开销。

注意文件头部的注释：

```typescript
// src/schemas/hooks.ts:1-9
/**
 * Hook Zod schemas extracted to break import cycles.
 *
 * This file contains hook-related schema definitions that were originally
 * in src/utils/settings/types.ts. By extracting them here, we break the
 * circular dependency between settings/types.ts and plugins/schemas.ts.
 */
```

Schema 被单独提取到 `schemas/` 目录，是为了打破 `settings/types.ts` 和 `plugins/schemas.ts` 之间的循环依赖——这是大型 TypeScript 项目中常见的架构问题，通过引入专门的 schema 层来解决。

---

## 11.9 SleepTool：优雅等待的艺术

```typescript
// src/tools/SleepTool/prompt.ts:7-17
export const SLEEP_TOOL_PROMPT = `Wait for a specified duration.
The user can interrupt the sleep at any time.

Use this when the user tells you to sleep or rest, when you have nothing to do,
or when you're waiting for something.

You may receive <tick> prompts — these are periodic check-ins.
Look for useful work to do before sleeping.

You can call this concurrently with other tools — it won't interfere with them.

Prefer this over \`Bash(sleep ...)\` — it doesn't hold a shell process.

Each wake-up costs an API call, but the prompt cache expires after 5 minutes
of inactivity — balance accordingly.`
```

这段提示词信息量极大：

1. **`<tick>` 机制**：Agent 在等待期间会定期收到 tick 信号，这是一个"心跳"机制，让长期运行的 Assistant（如 KAIROS 模式）能够响应周期性任务而不阻塞。

2. **不占用 shell 进程**：相比 `Bash(sleep 10)`，SleepTool 只是 Agent 循环中的一次等待，不消耗任何系统资源。

3. **提示词缓存提示**：注释中直接告诉模型"每次唤醒都有 API 成本，提示词缓存 5 分钟后过期"——这是把基础设施知识直接编码进行为指导的例子。

4. **可并发**：睡眠可以与其他工具并发调用，这在多工具并行场景中有实际价值。

---

## 11.10 输出样式系统：`src/outputStyles/`

Claude Code 支持自定义**输出样式**，存储为 Markdown 文件：

```
.claude/output-styles/*.md   → 项目级样式
~/.claude/output-styles/*.md → 用户级样式（被项目级覆盖）
```

```typescript
// src/outputStyles/loadOutputStylesDir.ts:26-29
export const getOutputStyleDirStyles = memoize(
  async (cwd: string): Promise<OutputStyleConfig[]> => {
    const markdownFiles = await loadMarkdownFilesForSubdir('output-styles', cwd)
```

每个样式文件的文件名就是样式名，frontmatter 提供名称和描述，文件内容作为提示词。这让用户可以为不同场景（如"简洁报告"、"详细解释"）预定义输出风格，通过 `/style` 命令切换。

---

## 11.11 native-ts：从 Rust 到纯 TypeScript

`src/native-ts/` 目录包含原本是 Rust NAPI 原生模块的纯 TypeScript 移植版本，其中最有趣的是文件索引：

```typescript
// src/native-ts/file-index/index.ts:1-10
/**
 * Pure-TypeScript port of vendor/file-index-src (Rust NAPI module).
 *
 * The native module wraps nucleo (https://github.com/helix-editor/nucleo)
 * for high-performance fuzzy file searching.
 * This port reimplements the same API and scoring behavior
 * without native dependencies.
 */
```

系统实现了与 Helix 编辑器使用的 `nucleo` 模糊搜索引擎相同的算法：

```typescript
// src/native-ts/file-index/index.ts:23-31
// nucleo-style scoring constants (approximating fzf-v2 / nucleo bonuses)
const SCORE_MATCH = 16
const BONUS_BOUNDARY = 8
const BONUS_CAMEL = 6
const BONUS_CONSECUTIVE = 4
const BONUS_FIRST_CHAR = 8
const PENALTY_GAP_START = 3
const PENALTY_GAP_EXTENSION = 1
```

测试路径有 1.05 倍惩罚系数，让非测试文件在搜索结果中排名更高。这是一个在 TypeScript 中手动实现的高性能模糊搜索引擎，为跨平台部署（无需 Rust 编译工具链）的场景提供降级方案。

---

## 小结

本章涉及的功能展示了 Claude Code 超越"AI 代码助手"定位的工程深度：

- **TodoWrite**：会话内任务流水线管理
- **历史记录**：带引用机制的轻量持久化
- **REPL 模式**：强制批量执行的高效操作模式
- **Notebook 支持**：覆盖数据科学工作流
- **成本追踪**：不仅追踪开销，还追踪生产力指标
- **迁移系统**：优雅处理配置的历史演进
- **SleepTool**：资源感知的等待机制

这些设计共同体现了一个工程原则：**每个功能都应清楚地知道自己的边界**——TodoWrite 知道何时不该用，WebFetch 知道哪些域名可以不经授权访问，SleepTool 知道自己的成本影响。清晰的边界定义，是复杂系统保持可维护性的关键。
