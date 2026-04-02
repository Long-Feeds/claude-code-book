# 《解密 Claude Code：Anthropic CLI 源码深度解析》

本书基于 2026 年 3 月 31 日通过 npm source map 泄露的 Claude Code CLI 源码进行分析。

## 目录

1. [前言：一次意外的源码泄露](./chapters/00-preface.md)
2. [第一章：架构全景图](./chapters/01-architecture.md)
3. [第二章：启动流程与性能优化](./chapters/02-startup.md)
4. [第三章：工具系统设计](./chapters/03-tool-system.md)
5. [第四章：LLM 查询引擎](./chapters/04-query-engine.md)
6. [第五章：权限系统](./chapters/05-permissions.md)
7. [第六章：Agent 子系统与多智能体](./chapters/06-agents.md)
8. [第七章：终端 UI——React 在 CLI 中的实践](./chapters/07-ink-ui.md)
9. [第八章：IDE Bridge——与编辑器集成](./chapters/08-bridge.md)
10. [第九章：MCP 协议集成](./chapters/09-mcp.md)
11. [第十章：插件、技能与内存系统](./chapters/10-plugins-skills-memory.md)
12. [第十一章：特色功能拾遗](./chapters/11-special-features.md)
13. [第十二章：工程启示录](./chapters/12-reflections.md)

## 说明

- 所有代码引用均来自泄露的 `src/` 目录，已标注文件路径与行号
- 图表使用 ASCII/Mermaid 格式，便于博客渲染
- 内容以准确性为第一原则，不猜测未经代码证实的实现
