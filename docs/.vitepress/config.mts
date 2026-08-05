import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'Tennis Diary 文档',
  description: 'Tennis Diary 项目文档',
  lang: 'zh-CN',
  srcExclude: ['reference/**'],
  cleanUrls: true,
  vite: {
    server: {
      host: true,
      allowedHosts: true,
    },
  },
  themeConfig: {
    nav: [
      { text: '首页', link: '/' },
      { text: '方案', link: '/plans/01-tennis-diary-迁移微信小程序分析' },
      { text: '指南', link: '/guides/01-vitepress-踩坑记录' },
    ],
    sidebar: {
      '/plans/': [
        {
          text: '分析报告',
          items: [
            { text: 'Tennis Diary 迁移微信小程序分析', link: '/plans/01-tennis-diary-迁移微信小程序分析' },
          ],
        },
        {
          text: '实施步骤 — Phase B1（后台）',
          collapsed: false,
          items: [
            { text: 'B1-1：FastAPI 项目初始化与目录结构', link: '/plans/01-B1-1-FastAPI项目初始化与目录结构' },
            { text: 'B1-2：核心配置模块', link: '/plans/01-B1-2-核心配置模块' },
            { text: 'B1-3：数据库模型', link: '/plans/01-B1-3-数据库模型' },
          ],
        },
      ],
      '/guides/': [
        {
          text: '指南',
          items: [
            { text: 'VitePress 踩坑记录', link: '/guides/01-vitepress-踩坑记录' },
          ],
        },
      ],
    },
    socialLinks: [],
  },
})
