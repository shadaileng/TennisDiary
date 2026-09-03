/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
  readonly VITE_ADMIN_BASE: string
  readonly VITE_APP_TITLE: string
  readonly VITE_APP_VERSION: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

// File System Access API（Chromium）
interface Window {
  showSaveFilePicker(options?: {
    suggestedName?: string
    types?: Array<{ description: string; accept: Record<string, string[]> }>
  }): Promise<FileSystemFileHandle>
}

interface FileSystemFileHandle {
  createWritable(): Promise<FileSystemWritableFileStream>
}

interface FileSystemWritableFileStream extends WritableStream<Uint8Array> {
  write(data: Uint8Array | string): Promise<void>
  close(): Promise<void>
}
