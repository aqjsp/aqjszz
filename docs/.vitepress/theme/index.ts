import DefaultTheme from 'vitepress/theme'
import './custom.css'

// 把路由 / 侧边栏链接规范成可比较的路径：安全解码（文件名里的裸 % 不抛错）、
// 去掉哈希/查询、去掉 index/.html/.md 后缀与结尾斜杠。
function normalizePath(p: string): string {
  let s: string
  try {
    s = decodeURI(p)
  } catch {
    s = p
  }
  return s
    .replace(/[?#].*$/, '')
    .replace(/\.(?:md|html)$/, '')
    .replace(/\/index$/, '')
    .replace(/\/+$/, '')
}

// 点击目录项的 caret 即可切换折叠（对带链接/不带链接的目录都有效），统一入口
function clickCaret(el: Element) {
  ;(el.querySelector('.caret') as HTMLElement | null)?.click()
}

// 在侧边栏里找到"链接正好等于当前路由"的目录项：文章叶子，或带链接的栏目/文件夹（如 /algorithm/）。
// 用路由匹配而非 VitePress 的 .is-active（后者在站内跳转时更新有延迟，会收错路径）。
// location.pathname 是百分号编码的，解码后与侧边栏 href 比较。
function findSidebarItemByRoute(): Element | null {
  const target = normalizePath(window.location.pathname)
  const links = document.querySelectorAll('.VPSidebar a[href]')
  for (const a of links) {
    const href = a.getAttribute('href')
    if (href && normalizePath(href) === target) return a.closest('.VPSidebarItem')
  }
  return null
}

// 收起 group 的所有同级兄弟（手风琴）：点开 双指针 → 链表/二叉树 等自动合上。
// 顶层模块（level-0）各自套在 div.group 里，兄弟要跨 .group 找；其余层级共用同一个 .items 容器。
function collapseSiblings(group: HTMLElement) {
  const siblings = group.classList.contains('level-0')
    ? document.querySelectorAll('.VPSidebar .nav .VPSidebarItem.level-0.collapsible:not(.collapsed)')
    : group.parentElement?.querySelectorAll(':scope > .VPSidebarItem.collapsible:not(.collapsed)') ?? []
  siblings.forEach((o) => {
    if (o !== group) clickCaret(o)
  })
}

// 任意层级手风琴：点击某个可折叠目录（顶层模块 / 栏目 / 分类文件夹）即将展开时，
// 自动收起它的同级兄弟目录，左侧始终只展开当前路径
function setupSidebarAccordion() {
  document.addEventListener(
    'click',
    (e) => {
      const target = e.target as HTMLElement
      const item = target.closest('.item')
      if (!item) return
      const group = item.parentElement
      if (!group || !group.classList.contains('collapsible')) return
      // 捕获阶段先于 Vue toggle：此刻还是折叠态 = 点击后即将展开
      if (!group.classList.contains('collapsed')) return
      collapseSiblings(group)
    },
    true,
  )
}

// 点顶栏 / 切文章 / 直达深层链接：收起不在当前文章路径上的所有可折叠目录（顶层模块 / 栏目 / 文件夹），
// 再完整展开当前路径，最后把高亮项滚进侧边栏可视区。左侧始终只剩当前模块、且定位到对应文章。
// VitePress 会把所有层级的目录项都渲染在 DOM 里（只是用 CSS 隐藏），
// 所以即使父级还没展开，也能直接逐层点每级祖先的 caret。
function syncSidebarToRoute() {
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      const item = findSidebarItemByRoute()
      if (!item) return // 首页 / 404：没有对应目录项，不强行改动

      // 1) 收集从叶子到顶层的整条路径（叶子在前，含自身）
      const path: Element[] = []
      for (let n: Element | null = item; n; n = n.parentElement) {
        if (n.classList.contains('VPSidebarItem')) path.push(n)
      }

      // 2) 收起不在当前路径上的所有可折叠目录
      document
        .querySelectorAll('.VPSidebar .nav .VPSidebarItem.collapsible:not(.collapsed)')
        .forEach((g) => {
          if (!path.includes(g)) clickCaret(g)
        })

      // 3) 沿路径从叶子向上逐层展开
      path.forEach((el) => {
        if (el.classList.contains('collapsed')) clickCaret(el)
      })

      // 4) 把高亮项滚进可视区（只在超出可视范围时才滚，避免频繁抖动）
      const nav = document.querySelector('.VPSidebar .nav')
      const active = item.querySelector('.item') ?? item
      if (nav && active) {
        const navRect = nav.getBoundingClientRect()
        const itemRect = active.getBoundingClientRect()
        const outOfView = itemRect.top < navRect.top || itemRect.bottom > navRect.bottom
        if (outOfView) active.scrollIntoView({ block: 'center' })
      }
    })
  })
}

// 一键到顶按钮（右下角）：SVG 圆环随滚动显示阅读进度，滚动超过一屏后淡入，点击平滑回顶
function setupReadingProgress() {
  const btn = document.createElement('button')
  btn.className = 'back-to-top'
  btn.type = 'button'
  btn.setAttribute('aria-label', '回到顶部')
  btn.innerHTML = `
    <svg class="back-to-top-progress" viewBox="0 0 40 40" aria-hidden="true">
      <circle class="back-to-top-track" cx="20" cy="20" r="16" />
      <circle class="back-to-top-bar" cx="20" cy="20" r="16" />
    </svg>
    <span class="back-to-top-icon">
      <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M12 19V5M5 12l7-7 7 7"/></svg>
    </span>`
  btn.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }))
  document.body.appendChild(btn)

  // 圆环周长：2πr，用 stroke-dashoffset 控制填充比例
  const bar = btn.querySelector('.back-to-top-bar') as SVGCircleElement
  const C = 2 * Math.PI * 16
  bar.style.strokeDasharray = String(C)
  bar.style.strokeDashoffset = String(C)

  const update = () => {
    const doc = document.documentElement
    const max = doc.scrollHeight - window.innerHeight
    const ratio = max > 0 ? Math.min(1, window.scrollY / max) : 0
    bar.style.strokeDashoffset = String(C * (1 - ratio))
    btn.classList.toggle('visible', window.scrollY > window.innerHeight)
  }
  let ticking = false
  window.addEventListener(
    'scroll',
    () => {
      if (!ticking) {
        ticking = true
        requestAnimationFrame(() => {
          ticking = false
          update()
        })
      }
    },
    { passive: true },
  )
  update()
}

export default {
  extends: DefaultTheme,
  enhanceApp({ router }) {
    if (typeof window !== 'undefined') {
      // 首次进入（含硬刷新直达文章）也执行一次
      syncSidebarToRoute()
      router.onAfterRouteChanged = syncSidebarToRoute
      setupSidebarAccordion()
      setupReadingProgress()
    }
  },
}
