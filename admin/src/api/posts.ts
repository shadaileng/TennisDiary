import request from './index'

export interface Post {
  id: number
  user_id: number
  date: string
  platform: string
  title: string
  content: string
  status: string
  created_at: string
  user?: {
    id: number
    nickname: string
  }
}

export interface PostListResponse {
  items: Post[]
  total: number
}

export function getPosts(params: { offset?: number; limit?: number; user_id?: number }): Promise<PostListResponse> {
  return request.get('/api/admin/posts', { params })
}

export function getPost(id: number): Promise<Post> {
  return request.get(`/api/admin/posts/${id}`)
}

export function deletePost(id: number) {
  return request.delete(`/api/admin/posts/${id}`)
}
