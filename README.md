# aqjszz · 阿Q技术站网站

用 [VitePress](https://vitepress.dev/)搭建的技术文档站：
左目录、中正文、右大纲、站内搜索、深浅色，全部由成熟主题提供。

- 内容源：`github.com/aqjsp` 下的 10 个仓库（C++ / Go / 计算机网络 / 操作系统 / 数据结构 / 数据库 / 算法刷题 / Git / Linux / 后端面经）
- 内容同步：`scripts/sync.py` 拉取仓库 markdown → `docs/`，并自动生成侧边栏与首页
- 更新内容：改 GitHub 仓库 → 重新 `python3 scripts/sync.py` → 构建发布

## 环境要求

- Node.js ≥ 18（[nodejs.org](https://nodejs.org) 下载安装即可）
- Python 3（macOS 自带）

## 本地运行

```bash
# 首次：安装依赖
npm install

# 开发预览（改代码热更新）
npm run docs:dev
# 打开 http://localhost:5173

# 拉取最新文章
python3 scripts/sync.py

# 构建上线产物
npm run docs:build
npm run docs:preview
```

## 发布

构建产物在 `docs/.vitepress/dist`，可部署到 GitHub Pages / Vercel / 任意静态托管。

## 目录

```
aqjszz/
├── package.json           # 脚本：dev / build / preview / sync
├── scripts/sync.py        # 内容同步（从 GitHub 拉 markdown 生成 docs/）
└── docs/
    ├── index.md           # 首页（自动生成）
    ├── .vitepress/
    │   ├── config.mts     # 站点配置
    │   └── sidebar.ts     # 侧边栏（sync 自动生成）
    ├── public/aq.png      # logo（GitHub 头像）
    └── cpp/ network/ ...  # 各专栏内容（sync 自动生成）
```
