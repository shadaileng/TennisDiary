/**
 * 阶段三 (149) HF Space 反代 Cloudflare Worker
 *
 * 部署方式：Cloudflare Pages/Workers 部署
 * 路由：api.yourdomain.com → 此 Worker (处理 HTTPS、安全头、原始请求转发)
 *
 * 功能：
 * - 处理 HTTPS 与 SSL 证书（由 Cloudflare 托管）
 * - 透传 X-Auth-Token (避免重复 Authorization)
 * - 设置安全头（CSP、HSTS 等）
 * - 流量路由与缓存策略
 * - 隐藏 HF Space 真实域名
 *
 * 配置步骤：
 * 1. 在 Cloudflare 账户创建 Worker：`td-hf-proxy`
 * 2. 绑定域名：`api.yourdomain.com`
 * 3. 路由：`api.yourdomain.com/*`
 * 4. 将本代码部署到 Worker
 * 5. 设置环境变量：
 *    - HF_SPACE_URL: https://tennis-diary-server.hf.space
 *
 * 注意：Cloudflare 会自动处理 HTTP/2、HTTP/3、Compression 等
 */

// Cloudflare 环境变量
const HF_SPACE_URL = 'https://tennis-diary-server.hf.space'

addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request))
})

async function handleRequest(request) {
  const url = new URL(request.url)

  // 构建目标 URL
  const targetUrl = HF_SPACE_URL + url.pathname + url.search

  // 修改请求头
  const headers = new Headers(request.headers)

  // 透传 X-Auth-Token (避免重复 Authorization)
  const authToken = headers.get('x-auth-token') || headers.get('X-Auth-Token')
  if (authToken) {
    // Cloudflare 自动添加 X-Auth-Token
    headers.set('Authorization', `Bearer ${authToken}`)
  }

  // 设置 X-Forwarded 头（供后端识别真实客户端）
  headers.set('X-Forwarded-For', request.headers.get('CF-Connecting-IP'))
  headers.set('X-Forwarded-Proto', request.headers.get('CF-Scheme') || 'https')
  headers.set('X-Forwarded-Host', request.headers.get('Host'))

  // 透传 Range 头 (支持文件 Range 下载)
  const range = request.headers.get('Range')
  if (range) {
    headers.set('Range', range)
  }

  // 透传 Content-Type (对上传请求重要)
  // 不删除 Content-Length，避免干扰上传

  // 禁用请求缓冲 (支持 SSE 流式传输)
  headers.set('Expect', '')

  // 设置安全头（Cloudflare 已处理部分）
  headers.set('X-Content-Type-Options', 'nosniff')
  headers.set('X-XSS-Protection', '1; mode=block')

  // 尝试使用 fetch API 的 duplex 选项（可能需要调整）
  try {
    const response = await fetch(targetUrl, {
      headers: headers,
      method: request.method,
      body: request.method !== 'GET' && request.method !== 'HEAD' ? request.body : undefined,
      duplex: 'half'
    })

    // 透传响应头
    const responseHeaders = new Headers(response.headers)

    // 添加安全头（Cloudflare 已处理部分）
    responseHeaders.set('X-Content-Type-Options', 'nosniff')
    responseHeaders.set('X-XSS-Protection', '1; mode=block')
    responseHeaders.set('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')

    // 设置缓存策略（根据路径）
    const path = url.pathname
    if (path.startsWith('/api/') || path.startsWith('/sse/')) {
      responseHeaders.set('Cache-Control', 'no-cache, no-store, must-revalidate')
      responseHeaders.set('Pragma', 'no-cache')
    }

    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders
    })
  } catch (error) {
    console.error('Worker 错误:', error)

    // 错误处理：返回友好错误信息
    return new Response(JSON.stringify({
      error: 'Service temporarily unavailable',
      message: '后端服务暂时不可用，请稍后重试',
      timestamp: Date.now()
    }), {
      status: 503,
      headers: {
        'Content-Type': 'application/json',
        'X-Content-Type-Options': 'nosniff',
        'X-XSS-Protection': '1; mode=block'
      }
    })
  }
}
