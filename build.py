#!/usr/bin/env python3
"""
Convert Markdown chapters to HTML pages
"""
import os
import re
from pathlib import Path

# HTML template
TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - 解密 Claude Code</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/github-markdown-css/5.5.1/github-markdown.min.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
    <script>hljs.highlightAll();</script>
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
        }}
        .nav a:hover {{
            text-decoration: underline;
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
            max-width: 980px;
            margin: 0 auto;
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
            <a href="../index.html#toc">目录</a>
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

def md_to_html_simple(md_content):
    """Simple markdown to HTML conversion"""
    html = md_content
    
    # Headers
    html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^#### (.+)$', r'<h4>\1</h4>', html, flags=re.MULTILINE)
    
    # Code blocks
    html = re.sub(r'```(\w+)?\n(.*?)\n```', r'<pre><code class="language-\1">\2</code></pre>', html, flags=re.DOTALL)
    
    # Inline code
    html = re.sub(r'`([^`]+)`', r'<code>\1</code>', html)
    
    # Bold
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    
    # Italic
    html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
    
    # Lists
    lines = html.split('\n')
    in_list = False
    result_lines = []
    
    for line in lines:
        if line.strip().startswith('- '):
            if not in_list:
                result_lines.append('<ul>')
                in_list = True
            item = line.strip()[2:]
            result_lines.append(f'<li>{item}</li>')
        else:
            if in_list:
                result_lines.append('</ul>')
                in_list = False
            result_lines.append(line)
    
    if in_list:
        result_lines.append('</ul>')
    
    html = '\n'.join(result_lines)
    
    # Paragraphs
    paragraphs = html.split('\n\n')
    html_paragraphs = []
    for p in paragraphs:
        p = p.strip()
        if p and not p.startswith('<'):
            html_paragraphs.append(f'<p>{p}</p>')
        else:
            html_paragraphs.append(p)
    
    return '\n\n'.join(html_paragraphs)

def build_chapters():
    """Convert all markdown chapters to HTML"""
    chapters_dir = Path('chapters')
    chapters_dir.mkdir(exist_ok=True)
    
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
    
    for i, md_file in enumerate(md_files):
        print(f"Converting {md_file.name}...")
        
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Convert to HTML
        html_content = md_to_html_simple(content)
        
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
    print("\n✅ All chapters converted!")
