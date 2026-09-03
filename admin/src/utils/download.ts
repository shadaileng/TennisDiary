export interface DownloadFileInput {
  url: string
  fileName: string
  sizeBytes: number
}

export interface DownloadOptions {
  onProgress?: (downloaded: number, total: number) => void
  signal?: AbortSignal
  token?: string
}

/**
 * 管理员文件下载：统一带 X-Auth-Token 鉴权。
 * Chromium 走 showSaveFilePicker 流式写入磁盘（零内存 + 进度回调）；
 * 其他浏览器回退到 <a> 标签原生下载（token 通过 ?token= 查询参数透传）。
 */
export async function downloadAdminFile(
  file: DownloadFileInput,
  options: DownloadOptions = {},
): Promise<void> {
  const token = options.token ?? localStorage.getItem('admin_token') ?? ''
  const url = file.url

  if (typeof window.showSaveFilePicker === 'function') {
    let handle: FileSystemFileHandle
    try {
      handle = await window.showSaveFilePicker({
        suggestedName: file.fileName,
        types: [{ description: '文件', accept: { 'application/octet-stream': [] } }],
      })
    } catch {
      return // 用户取消选择
    }

    const resp = await fetch(url, {
      headers: { 'X-Auth-Token': token },
      signal: options.signal,
    })
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)

    const writable = await handle.createWritable()
    const reader = resp.body!.getReader()
    const total = Number(resp.headers.get('Content-Length') || file.sizeBytes)
    let downloaded = 0
    options.onProgress?.(downloaded, total)

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      await writable.write(value)
      downloaded += value.length
      options.onProgress?.(downloaded, total)
    }

    await writable.close()
  } else {
    const a = document.createElement('a')
    a.href = url + (token ? `?token=${encodeURIComponent(token)}` : '')
    a.download = file.fileName
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  }
}
