#!/usr/bin/env python3
"""
Convert Markdown chapters to HTML with proper rendering
Uses Python-Markdown with extensions for tables, fenced code, etc.
"""
import re
import markdown
from pathlib import Path

# HTML template with Mermaid support
TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - 解密 Claude Code</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/github-markdown-css/5.5.1/github-markdown.min.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/mermaid/10.9.0/mermaid.min.js"></script>
    <script>
        hljs.highlightAll();
        mermaid.initialize({{ startOnLoad: true, theme: 'default' }});
    </script>
    <style>
        body {{
            margin: 0;
            padding: 0;
            background: #f6f8fa;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', sans-serif;
        }}
        .nav {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            position: sticky;
            top: 0;
            z-index: 1000;
        }}
        .nav-container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .nav a {{
            color: white;
            text-decoration: none;
            font-weight: 500;
            transition: opacity 0.3s;
        }}
        .nav a:hover {{
            opacity: 0.8;
        }}
        .container {{
            max-width: 1200px;
            margin: 40px auto;
            padding: 0 20px;
        }}
        .content {{
            background: white;
            padding: 60px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }}
        .markdown-body {{
            box-sizing: border-box;
            min-width: 200px;
            max-width: 100%;
            margin: 0 auto;
        }}
        .markdown-body pre {{
            background: #f6f8fa;
            border-radius: 6px;
            padding: 16px;
        }}
        .markdown-body code {{
            background: #f6f8fa;
            padding: 0.2em 0.4em;
            border-radius: 3px;
            font-size: 85%;
        }}
        .markdown-body pre code {{
            background: transparent;
            padding: 0;
        }}
        .markdown-body table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
        }}
        .markdown-body table th,
        .markdown-body table td {{
            border: 1px solid #dfe2e5;
            padding: 8px 13px;
        }}
        .markdown-body table th {{
            background: #f6f8fa;
            font-weight: 600;
        }}
        .mermaid {{
            text-align: center;
            margin: 30px 0;
        }}
        .pagination {{
            display: flex;
            justify-content: space-between;
            margin-top: 60px;
            padding-top: 30px;
            border-top: 1px solid #e1e4e8;
        }}
        .pagination a {{
            display: inline-block;
            padding: 10px 20px;
            background: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 6px;
            transition: all 0.3s;
        }}
        .pagination a:hover {{
            background: #764ba2;
            transform: translateY(-2px);
        }}
        .pagination .prev::before {{
            content: "← ";
        }}
        .pagination .next::after {{
            content: " →";
        }}
        blockquote {{
            border-left: 4px solid #667eea;
            padding-left: 20px;
            color: #6a737d;
            margin: 20px 0;
        }}
        @media (max-width: 768px) {{
            .content {{
                padding: 30px 20px;
            }}
        }}
    </style>
</head>
<body>
    <div class="nav">
        <div class="nav-container">
            <a href="../index.html">📘 解密 Claude Code</a>
            <a href="../index.html">目录</a>
        </div>
    </div>
    
    <div class="container">
        <div class="content">
            <article class="markdown-body">
{content}
            </article>
            
            <div class="pagination">
                <div>{prev_link}</div>
                <div>{next_link}</div>
            </div>
        </div>
    </div>
</body>
</html>
"""

def build_chapters():
    """Convert all markdown chapters to HTML"""
    chapters_dir = Path('chapters')
    
    # Get all markdown files
    md_files = sorted(chapters_dir.glob('*.md'))
    
    chapter_titles = [
        "前言：一次意外的源码泄露",
        "架构全景图",
        "启动流程与性能优化",
        "工具系统设计",
        "LLM 查询引擎",
        "权限系统",
        "Agent 子系统与多智能体",
        "终端 UI——React 在 CLI 中的实践",
        "IDE Bridge——与编辑器集成",
        "MCP 协议集成",
        "插件、技能与内存系统",
        "特色功能拾遗",
        "工程启示录"
    ]
    
    # Markdown extensions
    md = markdown.Markdown(extensions=[
        'extra',           # Tables, fenced code blocks, etc.
        'codehilite',      # Code highlighting
        'toc',             # Table of contents
        'attr_list',       # Attribute lists
        'def_list',        # Definition lists
        'footnotes',       # Footnotes
        'md_in_html',      # Markdown in HTML
    ])
    
    for i, md_file in enumerate(md_files):
        print(f"Converting {md_file.name}...")
        
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Pre-process: extract mermaid fenced blocks BEFORE markdown conversion
        # so codehilite doesn't mangle them into syntax-highlighted <pre> blocks.
        # Replace ```mermaid ... ``` with raw <div class="mermaid">...</div>
        # which md_in_html extension will pass through unchanged.
        content = re.sub(
            r'```mermaid\n(.*?)```',
            lambda m: f'<div class="mermaid">\n{m.group(1).strip()}\n</div>',
            content,
            flags=re.DOTALL
        )

        # Convert to HTML
        html_content = md.convert(content)
        md.reset()  # Reset for next file
        
        # Pagination links
        prev_link = ""
        next_link = ""
        
        if i > 0:
            prev_file = md_files[i-1].stem + '.html'
            prev_link = f'<a href="{prev_file}" class="prev">上一章</a>'
        
        if i < len(md_files) - 1:
            next_file = md_files[i+1].stem + '.html'
            next_link = f'<a href="{next_file}" class="next">下一章</a>'
        
        # Get title
        title = chapter_titles[i] if i < len(chapter_titles) else md_file.stem
        
        # Generate HTML
        html = TEMPLATE.format(
            title=title,
            content=html_content,
            prev_link=prev_link,
            next_link=next_link
        )
        
        # Write HTML file
        html_file = chapters_dir / (md_file.stem + '.html')
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"  ✓ Created {html_file.name}")

if __name__ == '__main__':
    build_chapters()
    print("\n✅ All chapters converted with proper Markdown rendering!")
