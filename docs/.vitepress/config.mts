import { defineConfig } from 'vitepress'
import sidebar from './sidebar'

// 阿Q技术站 —— VitePress 文档站（JavaGuide 同款引擎）
export default defineConfig({
  lang: 'zh-CN',
  title: '阿Q技术站',
  description: '把「会」变成「会复用」。计算机基础、刷题、面经与 Agent 笔记，内容来自开源 GitHub 仓库。',
  cleanUrls: true,
  lastUpdated: true,
  markdown: {
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
