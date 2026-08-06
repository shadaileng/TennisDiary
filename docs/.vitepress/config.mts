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
        {
          text: '实施步骤 — Phase 1（小程序前端）',
          collapsed: false,
          items: [
            { text: 'Phase1：uni-app 小程序前端工程初始化', link: '/plans/12-Phase1-uni-app小程序前端工程初始化' },
            { text: 'Phase1-1：uni-app 工程初始化', link: '/plans/13-Phase1-1-uni-app工程初始化' },
            { text: 'Phase1-2：目录结构与 TabBar', link: '/plans/14-Phase1-2-目录结构与TabBar' },
            { text: 'Phase1-3：Tailwind CSS 集成', link: '/plans/15-Phase1-3-Tailwind集成' },
            { text: 'Phase1-4：Tailwind 自定义组件', link: '/plans/16-Phase1-4-Tailwind自定义组件' },
            { text: 'Phase1-5：types 类型迁移', link: '/plans/17-Phase1-5-types类型迁移' },
            { text: 'Phase1-6：Pinia store 搭建', link: '/plans/18-Phase1-6-PiniaStore搭建' },
            { text: 'Phase1-7：网络层封装', link: '/plans/19-Phase1-7-网络层封装' },
            { text: 'Phase1-8：对接 B1 登录流程', link: '/plans/20-Phase1-8-对接B1登录流程' },
            { text: '21：前后端 .env 配置模板', link: '/plans/21-环境变量配置模板' },
            { text: '22：前端环境变量 AppID 注入与域名白名单校验', link: '/plans/22-前端环境变量-AppID与域名白名单校验' },
            { text: '23：构建警告清理 Tailwind 与 Sass 弃用警告', link: '/plans/23-构建警告清理-Tailwind与Sass弃用警告' },
            { text: '24：修复 WXSS 编译错误与联调排障', link: '/plans/24-修复wxss编译错误与联调排障' },
            { text: '25：静默登录门控 首次启动不请求后台', link: '/plans/25-静默登录门控-首次启动不请求后台' },
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
