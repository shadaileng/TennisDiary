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
            { text: 'B1-1：FastAPI 项目初始化与目录结构', link: '/plans/02-B1-1-FastAPI项目初始化与目录结构' },
            { text: 'B1-2：核心配置模块', link: '/plans/03-B1-2-核心配置模块' },
            { text: 'B1-3：数据库模型', link: '/plans/04-B1-3-数据库模型' },
            { text: 'B1-4：基于 loguru 的日志系统', link: '/plans/05-B1-4-基于loguru的日志系统' },
            { text: 'B1-6：日记 CRUD 接口', link: '/plans/06-B1-6-日记接口' },
            { text: 'B1-7：装备 CRUD 接口', link: '/plans/07-B1-7-装备接口' },
            { text: 'B1-8：体重记录接口', link: '/plans/08-B1-8-体重记录接口' },
            { text: 'B1-9：打卡接口', link: '/plans/09-B1-9-打卡接口' },
            { text: 'B1-10：统计汇总接口', link: '/plans/10-B1-10-统计汇总接口' },
            { text: 'B1-11：文件下载接口', link: '/plans/11-B1-11-文件下载接口' },
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
