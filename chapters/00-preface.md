# 前言——一次意外的源码泄露

> 2026年3月31日，Anthropic 的 Claude Code CLI 因 npm 包中遗留了 source map 文件，完整的 TypeScript 源码意外暴露在公众面前。这本书，就是对那份源码的系统性解读。

---

## 事件始末

2026年3月31日，安全研究员 Chaofan Shou（Twitter 账号 @Fried_rice）发布了一条推文：

> *"Claude code source code has been leaked via a map file in their npm registry!"*
>
> — [@Fried_rice, 2026-03-31](https://x.com/Fried_rice/status/2038894956459290963)

这条推文随即在开发者社区引发广泛关注。事件的技术细节并不复杂：Anthropic 在发布 Claude Code 的 npm 包时，意外地在构建产物中保留了 `.map`（source map）文件。Source map 是 JavaScript 构建工具链中用于调试的映射文件，它保存了编译后代码与原始源码之间的对应关系。更关键的是，该 `.map` 文件包含了一个指向完整未混淆 TypeScript 源码压缩包的 URL，而这个 URL 指向的是 Anthropic 的 R2 对象存储桶，任何人都可以直接下载。

于是，在短短数小时内，完整的 Claude Code 源代码在互联网上广泛流传。

这并非黑客入侵，也没有任何服务器被攻破。这是一次典型的"供应链意外泄露"——一个在构建配置中被遗忘的开关，让商业软件的核心代码彻底裸露。

---

## Claude Code 是什么

Claude Code 是 Anthropic 推出的官方命令行工具（CLI），让开发者可以直接在终端中与 Claude 模型交互，完成软件工程任务。它不仅仅是一个聊天界面的命令行版本，而是一个深度集成到开发工作流中的 AI 编程助手：

- **编辑文件**：直接读取、修改、创建代码文件
- **执行命令**：在 shell 中运行任意命令
- **搜索代码库**：通过 ripgrep 进行全文搜索，通过 glob 进行文件定位
- **管理 git**：提交、查看差异、处理 PR
- **多智能体协作**：生成子 Agent 并行处理复杂任务
- **IDE 集成**：通过 Bridge 系统连接 VS Code 和 JetBrains

Claude Code 的定位是"在终端里工作的编程伙伴"，它的设计哲学是让 AI 能够访问开发者本地环境中的一切——文件系统、命令行、版本控制——而不是局限在一个沙盒化的代码补全框架里。

---

## 代码库规模

根据 README 及实际统计数据，泄露的源码规模相当可观：

| 指标 | 数值 |
|------|------|
| 总文件数 | ~1,900 个文件 |
| 总代码行数 | 512,000+ 行 |
| TypeScript 源文件数 | 1,884 个 `.ts` / `.tsx` 文件 |
| 最大单文件 | `main.tsx`（4,683 行）|
| 核心引擎文件 | `QueryEngine.ts`（1,295 行）|

这不是一个小型工具的代码量。相比之下，许多知名开源项目的核心代码库也不过如此规模。这个数字揭示了 Claude Code 背后的工程投入：它是一个功能完整、经过生产验证的商业软件产品。

顶层目录结构如下：

```
src/
├── main.tsx          # 入口（Commander.js CLI 解析 + React/Ink 渲染器初始化）
├── QueryEngine.ts    # LLM 查询引擎（核心 API 调用层）
├── Tool.ts           # 工具类型定义基础
├── commands.ts       # 斜杠命令注册表
├── tools.ts          # 工具注册表
├── context.ts        # 系统与用户上下文收集
├── cost-tracker.ts   # Token 费用追踪
│
├── commands/         # 斜杠命令实现（约 50 个）
├── tools/            # Agent 工具实现（约 40 个）
├── components/       # Ink UI 组件（约 140 个）
├── hooks/            # React Hooks
├── services/         # 外部服务集成
├── screens/          # 全屏 UI（Doctor、REPL、Resume）
├── bridge/           # IDE 集成桥接层
├── coordinator/      # 多 Agent 协调器
├── plugins/          # 插件系统
├── skills/           # 技能系统
├── state/            # 状态管理
├── memdir/           # 持久化记忆目录
├── tasks/            # 任务管理
└── ...               # 其他子系统
```

---

## 技术栈一览

Claude Code 的技术选型颇具特色：

| 层次 | 技术 |
|------|------|
| 运行时 | [Bun](https://bun.sh)（非 Node.js） |
| 语言 | TypeScript（strict 模式） |
| 终端 UI | React + [Ink](https://github.com/vadimdemedes/ink) |
| CLI 解析 | Commander.js（extra-typings） |
| Schema 验证 | Zod v4 |
| 代码搜索 | ripgrep |
| 协议 | MCP SDK、LSP |
| API | Anthropic SDK |
| 遥测 | OpenTelemetry + gRPC |
| 特性开关 | GrowthBook |
| 认证 | OAuth 2.0、JWT、macOS Keychain |

选择 Bun 而非 Node.js 是一个有意为之的决策：Bun 提供了更快的启动速度（对 CLI 工具至关重要）和内置的 `bun:bundle` 特性开关系统，后者被 Claude Code 大量用于死代码消除。

---

## 这本书会讲什么

本书面向对 AI 工程、CLI 工具设计或大型 TypeScript 项目架构感兴趣的开发者。我们将系统性地解读这份意外公开的源码，从宏观架构到微观实现，还原一个商业 AI 编程助手的完整工程图景。

**本书结构如下：**

- **第 00 章（本章）**：泄露事件背景与代码库总览
- **第 01 章：架构全景图** — 高层架构、子系统关系、入口点分析
- **第 02 章：启动流程与性能优化** — 并行预取、懒加载、启动分析器
- **第 03 章：工具系统** — 工具定义、输入 Schema、权限模型
- **第 04 章：LLM 查询引擎** — 流式响应、工具调用循环、重试逻辑
- **第 05 章：权限系统** — 六种权限模式、用户确认流程
- **第 06 章：Agent 子系统与多智能体协作** — AgentTool、coordinator、swarm 机制
- **第 07 章：终端 UI** — React/Ink 渲染引擎、键位绑定、Vim 模式
- **第 08 章：Remote Control Bridge** — VS Code/JetBrains 双向通信
- **第 09 章：MCP 协议集成** — Model Context Protocol 的实现细节
- **第 10 章：插件、技能与记忆系统** — 可扩展性设计与跨会话记忆
- **第 11 章：特色功能拾遗** — 任务管理、Notebook 支持、成本追踪等
- **第 12 章：工程启示录** — 架构反思与工程实践总结

---

## 阅读说明

本书所有代码引用均来自泄露的源码，文件路径以 `src/` 为根。行号基于原始文件，可能因后续版本变化而偏移。

代码块中的文件路径格式为：

```
src/文件路径:行号
```

所有内容均以分析和教育为目的。原始源码版权归 Anthropic 所有。

---

*让我们翻开这份意外的礼物，看看世界上最先进的 AI 编程助手，是如何被构建出来的。*
