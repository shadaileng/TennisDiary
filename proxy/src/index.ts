// UPSTREAM 通过 wrangler secret 或 .dev.vars 注入
// 用法：wrangler secret put UPSTREAM

interface Env {
  UPSTREAM: string
}

const CORS_HEADERS: Record<string, string> = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, X-Auth-Token, Authorization",
  "Access-Control-Max-Age": "86400",
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    // 处理预检请求：网关由 Worker 接管，返回自定义 CORS 头
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: CORS_HEADERS })
    }

    // 构造上游请求：保留路径 + 全部请求头（含 X-Auth-Token）
    const url = new URL(request.url)
    const upstreamUrl = env.UPSTREAM + url.pathname + url.search
    const upstreamReq = new Request(upstreamUrl, {
      method: request.method,
      headers: request.headers,
      body: ["GET", "HEAD"].includes(request.method) ? undefined : request.body,
    })

    // 转发并原样透传响应体，仅附加 CORS 头
    const resp = await fetch(upstreamReq)
    const newResp = new Response(resp.body, resp)
    Object.entries(CORS_HEADERS).forEach(([k, v]) => newResp.headers.set(k, v))
    return newResp
  },
}
