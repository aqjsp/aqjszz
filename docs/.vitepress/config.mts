import { defineConfig } from 'vitepress'
import sidebar from './sidebar'

// 轻量代码语言识别：仅当有"强信号"时才判定，拿不准的一律保持纯文本（该亮的亮、不该亮的不亮）。
function detectCodeLang(code: string): string | null {
  const s = code.trimStart()
  if (!s) return null
  if (/^\s*#\s*include\s*[<"]/.test(s)) return 'cpp'
  if (/\busing\s+namespace\b|\bstd::|\bcout\b|\bcin\b|\bprintf\s*\(/.test(s)) return 'cpp'
  if (/^\s*(class|struct|enum)\s+\w+\s*\{/.test(s) || /^\s*int\s+main\s*\(/.test(s)) return 'cpp'
  if (/^\s*package\s+\w+/.test(s) && /\bfunc\s+\w+\s*\(/.test(s)) return 'go'
  if (/\bpublic\s+static\s+void\s+main\b|\bSystem\.out\.print/.test(s)) return 'java'
  if (/^\s*def\s+\w+\s*\(/m.test(s) || /^\s*(import\s+\w+|from\s+\w+\s+import)/m.test(s)) return 'python'
  if (/\bSELECT\b[\s\S]{0,200}\bFROM\b/i.test(s) || /^\s*(CREATE\s+TABLE|INSERT\s+INTO|UPDATE\s+\w+|DELETE\s+FROM)\b/i.test(s)) return 'sql'
  if (/^\s*#!\s*\/bin\//.test(s) || /^\s*(sudo|apt-get|yum|brew|npm|git|docker|kubectl|ls|cd)\s+\S/m.test(s)) return 'bash'
  if (/^\s*{[\s\S]*"\w+"\s*:/.test(s)) return 'json'
  if (/^(GET|POST|PUT|DELETE|PATCH)\s+\S+\s+HTTP\/1\.[01]\s*$/.test(s) || /^HTTP\/1\.[01]\s+\d{3}/.test(s)) return 'http'
  return null
}

// 阿Q技术站 —— VitePress 文档站
// 导航结构、两栏阅读布局、衬线字体与品牌蓝配色
export default defineConfig({
  lang: 'zh-CN',
  title: '阿Q技术站',
  description: '把「会」变成「会复用」。计算机基础、刷题、面经与 Agent 笔记，内容来自开源 GitHub 仓库。',
  // 文章文件已改成英文名（scripts/sync.py + scripts/slugs.py），URL 带 .html 后缀
  cleanUrls: false,
  lastUpdated: true,
  // C++ 代码里的 lambda `[](int a, int b)` 会被 markdown 解析成"空文本链接"，
  // 死链检查会误报；文章间真实链接已逐一验证存在，故关闭该检查
  ignoreDeadLinks: true,
  markdown: {
    // 语法高亮用 GitHub 主题（现在主流风格）：浅色 GitHub Light / 深色 GitHub Dark
    theme: { light: 'github-light', dark: 'github-dark' },
    // 未标语言的代码块：自动识别并注入语言，让 Shiki 按对应语言高亮；
    // 识别不出的保持纯文本（该亮的亮，不该亮的不亮）
    config(md) {
      const fence = md.renderer.rules.fence
      md.renderer.rules.fence = (tokens, idx, options, env, self) => {
        const t = tokens[idx]
        if (!t.info.trim()) {
          const lang = detectCodeLang(t.content)
          if (lang) t.info = lang
        }
        return fence!(tokens, idx, options, env, self)
      }
    },
    html: false,           // 正文里的 <int>、<cstdlib> 等 C++ 尖括号按文本渲染，不解析为 HTML
    lineNumbers: true,
    image: { lazyLoading: true },
    // 部分文章代码块用了 Shiki 默认未打包的语言标签，映射到已加载语言，
    // 避免每次构建/开发都提示 "The language 'xx' is not loaded" 并退化为纯文本。
    // 注意：目标必须是真实注册的语言（如 bash/json）；text/txt 是特殊占位，
    // 映射到它们反而会抛 "not found" 错误。
    languageAlias: {
      'redis-cli': 'bash',
      'redis': 'bash',
      'git': 'bash',
      'protobuf': 'json',
    },
  },
  head: [
    // 浏览器标签页图标也用 GitHub 头像（圆形裁剪版）
    ['link', { rel: 'icon', type: 'image/png', href: '/favicon.png' }],
  ],
  themeConfig: {
    logo: '/aq.png',
    // 导航栏：高频栏目一字排开，信息密度高
    nav: [
      { text: '首页', link: '/' },
      { text: 'Agent', link: '/agent/' },
      { text: 'C++', link: '/cpp/' },
      { text: 'Go', link: '/golang/' },
      { text: '计算机网络', link: '/network/' },
      { text: '操作系统', link: '/os/' },
      { text: '数据结构', link: '/data-structure/' },
      { text: '数据库', link: '/sql/' },
      { text: '算法刷题', link: '/algorithm/' },
      { text: 'Git', link: '/git/' },
      { text: 'Linux', link: '/linux/' },
      { text: '后端面经', link: '/interview/' },
      { text: 'GitHub', link: 'https://github.com/aqjsp' },
    ],
    sidebar,
    // 文章页右侧「阅读目录」：h2/h3 大纲，滚动跟随高亮
    outline: { label: '阅读目录', level: [2, 3] },
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
