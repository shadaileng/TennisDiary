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
          text: '方案',
          items: [
            { text: 'Tennis Diary 迁移微信小程序分析', link: '/plans/01-tennis-diary-迁移微信小程序分析' },
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
