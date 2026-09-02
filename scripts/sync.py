#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sync.py —— 把 GitHub 仓库的 markdown 同步成 VitePress 内容

用法：python3 scripts/sync.py   （项目根目录下执行）
作用：
  1. 拉取各仓库目录树与 .md 正文
  2. 写入 docs/<slug>/ 下，保持原目录结构
  3. 图片相对路径改写为 jsDelivr CDN 地址
  4. 生成每个专栏的 index.md、左侧边栏 sidebar.ts、首页 index.md
数据源优先级：jsDelivr（国内快）→ GitHub API / raw（最新）
"""
import json
import os
import re
import urllib.parse
import urllib.request

OWNER = 'aqjsp'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, 'docs')
VPRESS = os.path.join(DOCS, '.vitepress')

# 专栏配置：repo = GitHub 仓库名，slug = 站点目录名
COLUMNS = [
    {'repo': 'Cpp',                  'slug': 'cpp',           'title': 'C++',        'group': '语言',       'desc': 'C/C++ 基础、STL、新标准与高频面试题',             'branch': 'main'},
    {'repo': 'Golang',               'slug': 'golang',        'title': 'Go 语言',    'group': '语言',       'desc': 'Golang 学习总结',                               'branch': 'main'},
    {'repo': 'Computer-Networks',    'slug': 'network',       'title': '计算机网络', 'group': '计算机基础', 'desc': 'HTTP/HTTPS、TCP/UDP 详解与面试问答',              'branch': 'main'},
    {'repo': 'OS',                   'slug': 'os',            'title': '操作系统',   'group': '计算机基础', 'desc': '进程线程、进程间通信、面试连环问',                 'branch': 'main'},
    {'repo': 'Data-Structure',       'slug': 'data-structure','title': '数据结构',   'group': '计算机基础', 'desc': '二叉树、排序、查找与经典算法思想',                 'branch': 'main'},
    {'repo': 'SQL',                  'slug': 'sql',           'title': '数据库',     'group': '计算机基础', 'desc': 'MySQL、Redis 与分布式锁',                          'branch': 'main'},
    {'repo': 'Algorithm',            'slug': 'algorithm',     'title': '算法刷题',   'group': '刷题',       'desc': 'ACM 模式：华为 OD、牛客 Top101、面试经典 100 题',  'branch': 'main'},
    {'repo': 'Git',                  'slug': 'git',           'title': 'Git',        'group': '工具',       'desc': 'Git 基本命令与实战',                             'branch': 'main'},
    {'repo': 'Linux',                'slug': 'linux',         'title': 'Linux',      'group': '工具',       'desc': 'Linux 常用命令、Shell 与 vi',                    'branch': 'main'},
    {'repo': 'Interview-experience', 'slug': 'interview',     'title': '后端面经',   'group': '求职',       'desc': '按公司分类的 C++ / Go / Java 面经合集',            'branch': 'main'},
]

UA = {'User-Agent': 'aqjsp-site-sync'}


def http_json(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read().decode('utf-8'))


def http_text(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode('utf-8')


def flatten_jsdelivr(data, prefix=''):
    out = []
    for f in data.get('files', []):
        p = f'{prefix}/{f["name"]}' if prefix else f['name']
        if f['type'] == 'directory':
            out.extend(flatten_jsdelivr(f, p))
        else:
            out.append({'path': p, 'type': 'blob', 'size': f.get('size', 0)})
    return out


def fetch_tree(repo, branch):
    try:
        data = http_json(f'https://data.jsdelivr.com/v1/packages/gh/{OWNER}/{repo}@{branch}')
        return flatten_jsdelivr(data)
    except Exception:
        data = http_json(f'https://api.github.com/repos/{OWNER}/{repo}/git/trees/{branch}?recursive=1')
        return [{'path': e['path'], 'type': 'blob', 'size': 0} for e in data.get('tree', [])]


def fetch_file(repo, branch, path):
    enc = '/'.join(urllib.parse.quote(s) for s in path.split('/'))
    urls = [
        f'https://cdn.jsdelivr.net/gh/{OWNER}/{repo}@{branch}/{enc}',
        f'https://raw.githubusercontent.com/{OWNER}/{repo}/{branch}/{enc}',
    ]
    for u in urls:
        try:
            return http_text(u)
        except Exception:
            continue
    return None


def rewrite_images(md, repo, branch):
    """相对路径图片 -> jsDelivr CDN 绝对地址"""
    base = f'https://cdn.jsdelivr.net/gh/{OWNER}/{repo}@{branch}/'

    def repl(m):
        alt, src = m.group(1), m.group(2)
        if re.match(r'^(https?:)?//', src):
            return m.group(0)
        return f'![{alt}]({base}{urllib.parse.quote(src.lstrip("/"))})'

    return re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', repl, md)


def build_sidebar_items(paths, slug, prefix=''):
    """把仓库内 .md 路径构造成 VitePress 侧边栏嵌套结构
    prefix 累积子目录前缀，保证链接是完整路径 /<slug>/<dir>/<file>"""
    nodes = []
    dirs = {}
    files = []
    for p in paths:
        parts = p.split('/')
        if len(parts) == 1:
            files.append(p)
        else:
            dirs.setdefault(parts[0], []).append('/'.join(parts[1:]))

    for d in sorted(dirs):
        nodes.append({'text': d, 'collapsed': False,
                      'items': build_sidebar_items(dirs[d], slug, prefix + d + '/')})
    for f in sorted(files, key=lambda s: s.lower()):
        title = f[:-3] if f.lower().endswith('.md') else f
        link = f'/{slug}/{prefix}{f[:-3] if f.lower().endswith(".md") else f}'
        nodes.append({'text': title, 'link': link})
    return nodes


def main():
    os.makedirs(VPRESS, exist_ok=True)
    os.makedirs(os.path.join(DOCS, 'public'), exist_ok=True)

    groups = {}
    summary = []

    for col in COLUMNS:
        slug, repo, branch = col['slug'], col['repo'], col['branch']
        target = os.path.join(DOCS, slug)
        os.makedirs(target, exist_ok=True)

        tree = fetch_tree(repo, branch)
        mds = [e for e in tree
               if e['type'] == 'blob'
               and e['path'].lower().endswith('.md')
               and not (e['path'].count('/') == 0 and e['path'].lower() == 'readme.md')
               and e.get('size', 1) > 0]

        written, skipped = 0, 0
        for e in mds:
            rel = e['path']
            dst = os.path.join(target, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if os.path.exists(dst) and os.path.getsize(dst) > 0:
                written += 1
                continue
            md = fetch_file(repo, branch, rel)
            if md is None:
                skipped += 1
                continue
            md = rewrite_images(md, repo, branch)
            with open(dst, 'w', encoding='utf-8') as fh:
                fh.write(md)
            written += 1

        links = []
        for p in sorted({e['path'] for e in mds}):
            if p.count('/') == 0:
                links.append(f'- [{p[:-3]}](/{slug}/{p[:-3]})')
        index = [
            f'# {col["title"]}',
            '',
            col['desc'],
            '',
            '> 文章都在左侧目录中，按文件夹浏览。',
            '',
            *links,
            '',
        ]
        with open(os.path.join(target, 'index.md'), 'w', encoding='utf-8') as fh:
            fh.write('\n'.join(index))

        groups.setdefault(col['group'], []).append(col)
        summary.append(f'{repo:<22s} -> /{slug}/   {written} 篇')

    agent_dir = os.path.join(DOCS, 'agent')
    os.makedirs(agent_dir, exist_ok=True)
    with open(os.path.join(agent_dir, 'index.md'), 'w', encoding='utf-8') as fh:
        fh.write('# Agent Harness\n\n内容准备中。后续会更新 Agent 工程、Harness、工具调用等笔记。\n')

    sidebar = ["// 由 scripts/sync.py 自动生成，请勿手改", 'export default {', "  '/': ["]
    for g, cols in groups.items():
        sidebar.append(f"    {{ text: '{g}', collapsed: false, items: [")
        for col in cols:
            slug = col['slug']
            paths = []
            tdir = os.path.join(DOCS, slug)
            for root, _, files in os.walk(tdir):
                for f in files:
                    if f.lower().endswith('.md') and f != 'index.md':
                        full = os.path.relpath(os.path.join(root, f), tdir)
                        paths.append(full)
            items = build_sidebar_items(paths, slug)
            items_js = json.dumps(items, ensure_ascii=False, separators=(',', ':'))
            sidebar.append(f"      {{ text: '{col['title']}', link: '/{slug}/', items: {items_js} }},")
        sidebar.append('    ]},')
    sidebar.append("    { text: 'Agent', collapsed: false, items: [")
    sidebar.append("      { text: 'Agent Harness', link: '/agent/' },")
    sidebar.append('    ]},')
    sidebar.append('  ],')
    sidebar.append('};')
    with open(os.path.join(VPRESS, 'sidebar.ts'), 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(sidebar) + '\n')

    features = []
    for col in COLUMNS:
        features.append(f"  - title: {col['title']}\n    details: {col['desc']}\n    link: /{col['slug']}/")
    features.append("  - title: Agent Harness\n    details: 即将更新：Agent 工程、Harness、工具调用\n    link: /agent/")
    home = [
        '---',
        'layout: home',
        '',
        'hero:',
        '  name: 阿Q技术站',
        '  text: 把「会」变成「会复用」',
        '  tagline: 计算机基础、刷题、面经与 Agent 笔记，全部开源，内容来自 GitHub 仓库。',
        '  image:',
        '    src: /aq.svg',
        '    alt: 阿Q技术站',
        '  actions:',
        '    - theme: brand',
        '      text: 开始学习',
        '      link: /cpp/',
        '    - theme: alt',
        '      text: GitHub',
        '      link: https://github.com/aqjsp',
        '',
        'features:',
        *features,
        '---',
        '',
    ]
    with open(os.path.join(DOCS, 'index.md'), 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(home))

    print('同步完成：')
    for line in summary:
        print(' ', line)
    print(f'侧边栏: docs/.vitepress/sidebar.ts')


if __name__ == '__main__':
    main()
