const BASE = '/api'

async function request(method, path, body) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
  }
  if (body) opts.body = JSON.stringify(body)
  const res = await fetch(`${BASE}${path}`, opts)
  if (res.status === 204) return null
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Request failed')
  }
  return res.json()
}

export const api = {
  // Pages
  getPageTree: () => request('GET', '/pages/tree'),
  getPage: (id) => request('GET', `/pages/${id}`),
  createPage: (data) => request('POST', '/pages', data),
  updatePage: (id, data) => request('PUT', `/pages/${id}`, data),
  deletePage: (id) => request('DELETE', `/pages/${id}`),
  movePage: (id, data) => request('PUT', `/pages/${id}/move`, data),

  // Blocks
  getBlocks: (pageId) => request('GET', `/pages/${pageId}/blocks`),
  createBlock: (pageId, data) => request('POST', `/pages/${pageId}/blocks`, data),
  updateBlock: (pageId, blockId, data) =>
    request('PUT', `/pages/${pageId}/blocks/${blockId}`, data),
  deleteBlock: (pageId, blockId) =>
    request('DELETE', `/pages/${pageId}/blocks/${blockId}`),
  reorderBlocks: (pageId, updates) =>
    request('PUT', `/pages/${pageId}/blocks/reorder`, { updates }),

  // Markdown
  exportMarkdown: (pageId) => request('GET', `/pages/${pageId}/export/markdown`),
  importMarkdown: (markdown, title) =>
    request('POST', '/pages/import/markdown', { markdown, title }),

  // Upload
  async uploadImage(file) {
    const form = new FormData()
    form.append('file', file)
    const res = await fetch(`${BASE}/upload`, { method: 'POST', body: form })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }))
      throw new Error(err.detail || 'Upload failed')
    }
    return res.json()
  },

  // Vocabulary
  vocabStats: () => request('GET', '/vocab/stats'),
  vocabDailyTasks: () => request('GET', '/vocab/daily-tasks'),
  vocabReview: (pageId, data) => request('POST', `/vocab/${pageId}/review`, data),
  vocabUpdateSettings: (data) => request('PUT', '/vocab/settings', data),
  vocabReset: () => request('POST', '/vocab/reset'),
}
