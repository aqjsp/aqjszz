import { defineConfig } from 'vitepress'
import sidebar from './sidebar'

// 阿Q技术站 —— VitePress 文档站（JavaGuide 同款引擎）
export default defineConfig({
  lang: 'zh-CN',
  title: '阿Q技术站',
  description: '把「会」变成「会复用」。计算机基础、刷题、面经与 Agent 笔记，内容来自开源 GitHub 仓库。',
  cleanUrls: true,
  lastUpdated: true,
  // C++ 代码里的 lambda `[](int a, int b)` 会被 markdown 解析成"空文本链接"，
  // 死链检查会误报；文章间真实链接已逐一验证存在，故关闭该检查
  ignoreDeadLinks: true,
  markdown: {
    html: false,           // 正文里的 <int>、<cstdlib> 等 C++ 尖括号按文本渲染，不解析为 HTML
    lineNumbers: true,
    image: { lazyLoading: true },
  },
  themeConfig: {
    logo: '/aq.svg',
    nav: [
      { text: '首页', link: '/' },
      { text: 'GitHub', link: 'https://github.com/aqjsp' },
    ],
    sidebar,
    outline: { label: '本页大纲', level: [2, 3] },
    search: { provider: 'local' },
    socialLinks: [{ icon: 'github', link: 'https://github.com/aqjsp' }],
    docFooter: { prev: '上一篇', next: '下一篇' },
    lastUpdated: { text: '最后更新于' },
    darkModeSwitchLabel: '深浅色',
    sidebarMenuLabel: '目录',
    returnToTopLabel: '回到顶部',
    footer: {
      message: '内容来自 github.com/aqjsp · 公众号：阿Q技术站',
      copyright: '© 2026 阿Q技术站',
    },
  },
})
