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
import sys
import urllib.parse
import urllib.request

from slugs import SLUGS, SLUG_TITLES, DIR_EN  # 英文路径 / 中文标题 / 中文目录映射

# 侧边栏目录的中文标签（英文目录段 → 中文名，路径英文、显示中文）
DIR_TITLES = {v: k for k, v in DIR_EN.items()}

OWNER = 'aqjsp'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, 'docs')
VPRESS = os.path.join(DOCS, '.vitepress')

# 「面试经典算法题NN-xxx」按题目序号数字排序（7,8,9,10…15），而不是按字符串（10…15,7,8,9）。
# 文件名已英文化（无编号），题号从 scripts/slugs.py 的中文原始路径提取。
ALGO_NUM_RE = re.compile(r'^面试经典算法题?(\d+)')

# 英文相对路径(含 .md，相对专栏根) → 题目序号（面试经典100题 用，保证原题顺序）
SLUG_ALGO_NUM = {}
for _ch, _en in SLUGS.items():
    _m = ALGO_NUM_RE.match(_ch.split('/')[-1])
    if _m:
        SLUG_ALGO_NUM['/'.join(_en.split('/')[1:]) + '.md'] = int(_m.group(1))


def file_sort_key(rel):
    """侧边栏文件排序：面试经典算法题按序号数字排，其余按字母序。rel 为相对专栏根的路径(含 .md)"""
    n = SLUG_ALGO_NUM.get(rel)
    if n is not None:
        return (0, n, rel.lower())
    return (1, 0, rel.lower())


def dir_sort_key(d, subpaths, prefix):
    """侧边栏目录排序：目录直接子文件带题目序号的（如 面试经典100题 各分类），
    按最小序号排（双指针1、链表7、二叉树16…）；其余目录保持字母序。"""
    nums = []
    for p in subpaths:
        if '/' in p:
            continue
        n = SLUG_ALGO_NUM.get(prefix + d + '/' + p)
        if n is not None:
            nums.append(n)
    return (0, min(nums), d.lower()) if nums else (1, 0, d.lower())


def link_path(p):
    """生成链接目标时把空格编码成 %20：CommonMark 会把裸空格当链接结束符，
    导致 (/cpp/cpp_base/C++ 基础面试问题及详细解答) 被截断成 /cpp/cpp_base/C++。"""
    return p.replace(' ', '%20')


def article_url(rel_md, col_slug):
    """源相对路径（相对专栏根、含 .md）→ 站点 URL 路径（无 .md）。
    优先用 scripts/slugs.py 的手工英文映射；未收录的新文件回退原文件名。"""
    full = f'{col_slug}/{rel_md}'
    if full in SLUGS:
        return SLUGS[full]
    return f'{col_slug}/{link_path(rel_md[:-3] if rel_md.lower().endswith(".md") else rel_md)}'


def write_rewrites():
    """生成 docs/.vitepress/rewrites.ts：中文源路径 → 英文 URL 映射（function 形式用）"""
    lines = ['// 由 scripts/sync.py 自动生成，请勿手改',
             'export const REWRITES: Record<string, string> = {']
    for key in sorted(SLUGS):
        lines.append(f"  '{key}': '{SLUGS[key]}',")
    lines.append('};')
    path = os.path.join(VPRESS, 'rewrites.ts')
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(lines) + '\n')
    print('英文 URL 映射: docs/.vitepress/rewrites.ts')


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


def sanitize_path(path):
    """把路径里的 URL 危险字符换成全角，避免 VitePress 前端路由 decodeURI 报错导致点不进去。
    % 是罪魁祸首（如文件名"答对70%..."会让 decodeURI 抛 URIError），# / ? 会干扰路由。"""
    return (path
            .replace('%', '％')
            .replace('#', '＃')
            .replace('?', '？'))


def build_sidebar_items(paths, slug, prefix=''):
    """把仓库内 .md 路径构造成 VitePress 侧边栏嵌套结构
    prefix 累积子目录前缀，保证链接是完整路径 /<slug>/<dir>/<file>
    目录组默认 collapsed: True（折叠），当前文章所在组 VitePress 会自动展开，
    避免左侧目录一次性全展开显得拥挤"""
    nodes = []
    dirs = {}
    files = []
    for p in paths:
        parts = p.split('/')
        if len(parts) == 1:
            files.append(p)
        else:
            dirs.setdefault(parts[0], []).append('/'.join(parts[1:]))

    for d in sorted(dirs, key=lambda d: dir_sort_key(d, dirs[d], prefix)):
        nodes.append({'text': DIR_TITLES.get(d, d), 'collapsed': True,
                      'items': build_sidebar_items(dirs[d], slug, prefix + d + '/')})
    for f in sorted(files, key=lambda f: file_sort_key(prefix + f)):
        url = article_url(prefix + f, slug)
        title = SLUG_TITLES.get(url, f[:-3] if f.lower().endswith('.md') else f)
        link = f'/{url}.html'
        nodes.append({'text': title, 'link': link})
    return nodes


def collect_md_paths(slug):
    """收集某专栏 docs/<slug>/ 下除 index.md 外的所有 markdown 相对路径"""
    paths = []
    tdir = os.path.join(DOCS, slug)
    if not os.path.isdir(tdir):
        return paths
    for root, _, files in os.walk(tdir):
        for f in files:
            if f.lower().endswith('.md') and f != 'index.md':
                paths.append(os.path.relpath(os.path.join(root, f), tdir))
    return paths


def build_sidebar(groups):
    """生成单一侧边栏：所有顶层模块（语言/计算机基础/刷题/工具/求职/Agent）都在，
    只是默认折叠（collapsed: true）。配合前端"切换自动互斥"逻辑：
    点顶栏或切文章时，只展开当前模块，其它模块保持折叠但可见。"""
    sidebar = ["// 由 scripts/sync.py 自动生成，请勿手改", 'export default {', "  '/': ["]
    blocks = []
    for g, cols in groups.items():
        lines = [f"    {{ text: '{g}', collapsed: true, items: ["]
        for col in cols:
            slug = col['slug']
            items = build_sidebar_items(collect_md_paths(slug), slug)
            items_js = json.dumps(items, ensure_ascii=False, separators=(',', ':'))
            lines.append(f"      {{ text: '{col['title']}', link: '/{slug}/', collapsed: true, items: {items_js} }},")
        lines.append('    ]},')
        blocks.append('\n'.join(lines))
    # Agent 紧跟第一个模块（语言）之后，保持高优先级
    agent_block = "\n".join([
        "    { text: 'Agent', collapsed: true, items: [",
        "      { text: 'Agent Harness', link: '/agent/' },",
        "    ]},",
    ])
    blocks.insert(1, agent_block)
    sidebar.append('\n'.join(blocks))
    sidebar.append('  ],')
    sidebar.append('};')
    return '\n'.join(sidebar) + '\n'


def main():
    os.makedirs(VPRESS, exist_ok=True)
    os.makedirs(os.path.join(DOCS, 'public'), exist_ok=True)

    local_only = '--no-fetch' in sys.argv  # 本地重生成：不拉取仓库，仅重算链接/侧边栏/首页/rewrites
    groups = {}
    summary = []

    for col in COLUMNS:
        slug, repo, branch = col['slug'], col['repo'], col['branch']
        target = os.path.join(DOCS, slug)
        os.makedirs(target, exist_ok=True)

        if local_only:
            rel_paths = collect_md_paths(slug)
            written = len(rel_paths)
            skipped = 0
        else:
            tree = fetch_tree(repo, branch)
            mds = [e for e in tree
                   if e['type'] == 'blob'
                   and e['path'].lower().endswith('.md')
                   and not (e['path'].count('/') == 0 and e['path'].lower() == 'readme.md')
                   and e.get('size', 1) > 0]
            written, skipped = 0, 0
            for e in mds:
                rel = sanitize_path(e['path'])
                write_rel = SLUGS.get(f'{slug}/{rel}', rel)  # 中文源名 → 英文文件名
                dst = os.path.join(target, write_rel)
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
            rel_paths = [SLUGS.get(f'{slug}/{sanitize_path(e["path"])}', sanitize_path(e["path"])) for e in mds]

        # 专栏 index（仅顶层文件，链接用英文 slug）
        links = []
        for p in sorted(set(rel_paths)):
            if p.count('/') == 0:
                url = article_url(p, slug)
                title = SLUG_TITLES.get(url, p[:-3])
                links.append(f'- [{title}](/{url}.html)')
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

    sidebar = build_sidebar(groups)
    with open(os.path.join(VPRESS, 'sidebar.ts'), 'w', encoding='utf-8') as fh:
        fh.write(sidebar)

    write_rewrites()

    # ---------- 首页：hero + 核心入口 + 精选文章 + 关于 ----------
    # 精选文章：每专栏取目录层级最浅的 3 篇作为首页推荐
    featured = []
    for col in COLUMNS:
        slug = col['slug']
        tdir = os.path.join(DOCS, slug)
        shallow = []
        for root, _, files in os.walk(tdir):
            for f in files:
                if f.lower().endswith('.md') and f != 'index.md':
                    full = os.path.relpath(os.path.join(root, f), tdir)
                    shallow.append(full)
        shallow.sort(key=lambda p: (p.count('/'), p.lower()))
        picked = shallow[:3]  # 保留 .md 后缀，供 article_url 查英文映射
        if picked:
            links = '、'.join(
                f'[{SLUG_TITLES.get(article_url(t, slug), t.split("/")[-1][:-3])}](/{article_url(t, slug)}.html)'
                for t in picked
            )
            featured.append(f'- **{col["title"]}**：{links}')

    home = [
        '---',
        'layout: home',
        '',
        'hero:',
        '  name: 阿Q技术站',
        '  tagline: 面向 C++ / Go 后端开发者的开源知识库，把「会」变成「会复用」。计算机基础、刷题、面经与 Agent 笔记，内容全部开源。',
        '  actions:',
        '    - theme: brand',
        '      text: 开始阅读',
        '      link: /cpp/',
        '    - theme: alt',
        '      text: GitHub',
        '      link: https://github.com/aqjsp',
        '',
        '---',
        '',
        '## 核心入口',
        '',
    ]
    # 核心入口：后端面试主线 + Agent 放最前（高优先级），随后是各技术模块
    home.append('- **后端面试主线**：[后端面经](/interview/)（⭐网站核心）：按公司分类的 C++ / Go / Java 面试经验合集，覆盖语言、计算机基础、数据库与项目场景追问，适合集中刷面试题。')
    home.append('- **Agent**：[Agent Harness](/agent/)：即将更新 Agent 工程、Harness、工具调用等笔记。')
    for g, cols in groups.items():
        links = ' · '.join(f'[{c["title"]}](/{c["slug"]}/)' for c in cols)
        if g == '求职':
            continue  # 后端面试主线 已在开头
        elif g == '语言':
            home.append(f'- **{g}**：{links}，夯实语言功底。')
        elif g == '计算机基础':
            home.append(f'- **计算机基础**：{links}：后端面试绕不开的底层基础，适合补齐短板。')
        elif g == '刷题':
            home.append('- **算法刷题**：[算法刷题指南](/algorithm/)：ACM 模式 —— 华为 OD、牛客 Top101、面试经典 100 题。')
        else:
            home.append(f'- **开发工具**：{links}：日常开发必备的效率工具。')
    home += [
        '',
        '## 精选文章',
        '',
        *featured,
        '',
        '## 关于阿Q技术站',
        '',
        '阿Q技术站是一份面向 C++ / Go 后端开发者的开源知识库，内容来自 [github.com/aqjsp](https://github.com/aqjsp) 下的 10 个开源仓库，从语言基础到计算机底层、从算法刷题到面试经验，持续开源维护。',
        '',
        '网站内容覆盖：',
        '',
        '- **后端面试**：C++ / Go / Java 面经，计算机网络、操作系统、数据库等高频面试题。',
        '- **算法刷题**：华为 OD、牛客 Top101、面试经典 100 题，ACM 模式逐题精讲。',
        '- **开发工具**：Git、Linux、Shell 等日常开发必备技能。',
        '',
        '如果觉得阿Q技术站的内容对你有帮助的话，还请点个免费的 Star（绝不强制，觉得内容不错再点赞就好），这是对我最大的鼓励，感谢一路同行！传送门：[GitHub](https://github.com/aqjsp)',
        '',
        '## 关注与支持',
        '',
        '- 公众号 **阿Q技术站**：第一时间获取内容更新与技术干货。',
        '- GitHub 主页：[aqjsp](https://github.com/aqjsp)：所有内容源仓库，欢迎 Star、提 Issue、参与贡献。',
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
