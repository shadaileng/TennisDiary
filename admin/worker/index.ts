// Admin 管理端 Cloudflare Workers 静态托管入口
// 纯静态 SPA：Vite 构建产物（dist/）经 assets 绑定伺服，无后端逻辑。
// API 由独立 Worker tennis-diary-proxy（proxy/）承担，VITE_API_BASE_URL 在构建期内联。

interface Env {
  // Vite 构建产物 dist/（wrangler.toml assets.directory）
  ASSETS: Fetcher
}

// 静态资源长缓存（assets 下带 hash 的产物不可变）
const IMMUTABLE_CACHE = "public, max-age=31536000, immutable"
// index.html / SPA fallback 不缓存，始终重新校验
const NO_CACHE = "public, max-age=0, must-revalidate"

const HTML_CONTENT_TYPE = "text/html;charset=UTF-8"

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url)

    // 静态资源（带 hash 的构建产物）交给 assets 绑定，附加长缓存头
    if (url.pathname.startsWith("/assets/")) {
      const resp = await env.ASSETS.fetch(request)
      const headers = new Headers(resp.headers)
      if (!headers.has("Cache-Control")) headers.set("Cache-Control", IMMUTABLE_CACHE)
      return new Response(resp.body, { ...resp, headers })
    }

    // 其余路径：先尝试原样伺服（/favicon.svg 等 public 资源），命中则带 no-cache
    const asset = await env.ASSETS.fetch(request)
    if (asset.status === 200) {
      const headers = new Headers(asset.headers)
      if (!headers.has("Cache-Control")) headers.set("Cache-Control", NO_CACHE)
      return new Response(asset.body, { ...asset, headers })
    }

    // SPA history 路由 fallback：所有未命中的路径返回 index.html
    const index = await env.ASSETS.fetch(new Request(new URL("/index.html", url), request))
    const headers = new Headers(index.headers)
    headers.set("Content-Type", HTML_CONTENT_TYPE)
    if (!headers.has("Cache-Control")) headers.set("Cache-Control", NO_CACHE)
    return new Response(index.body, { ...index, headers })
  },
}
