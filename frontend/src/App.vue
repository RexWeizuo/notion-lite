<script setup>
import { ref } from 'vue'
import Sidebar from './components/Sidebar.vue'
import BlockEditor from './components/BlockEditor.vue'
import VocabReview from './components/VocabReview.vue'
import { api } from './api'

const currentPageId = ref(null)
const currentPage = ref(null)
const pageBlocks = ref([])
const fileInput = ref(null)
const sidebarVisible = ref(true)
const sidebarWidth = ref(420)
const showVocabReview = ref(false)
const sidebarRef = ref(null)

async function selectPage(pageId) {
  showVocabReview.value = false
  currentPageId.value = pageId
  currentPage.value = await api.getPage(pageId)
  pageBlocks.value = await api.getBlocks(pageId)
}

async function refreshBlocks() {
  if (currentPageId.value) {
    pageBlocks.value = await api.getBlocks(currentPageId.value)
  }
}

async function updateTitle() {
  if (!currentPage.value) return
  await api.updatePage(currentPageId.value, { title: currentPage.value.title })
  // Sync sidebar title
  if (sidebarRef.value) sidebarRef.value.loadTree()
}

async function deleteCurrentPage() {
  if (!currentPageId.value) return
  if (!confirm('确定删除这个页面？子页面也会被删除。')) return
  await api.deletePage(currentPageId.value)
  currentPageId.value = null
  currentPage.value = null
  pageBlocks.value = []
}

async function exportMd() {
  if (!currentPageId.value) return
  try {
    const data = await api.exportMarkdown(currentPageId.value)
    const blob = new Blob([data.markdown], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${data.title || 'note'}.md`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    alert('导出失败: ' + e.message)
  }
}

function triggerImport() {
  fileInput.value?.click()
}

async function handleImport(e) {
  const file = e.target.files?.[0]
  if (!file) return
  try {
    const text = await file.text()
    const title = file.name.replace(/\.md$/, '')
    const result = await api.importMarkdown(text, title)
    currentPageId.value = null
    currentPage.value = null
    pageBlocks.value = []
    setTimeout(async () => {
      await selectPage(result.page_id)
    }, 200)
  } catch (e) {
    alert('导入失败: ' + e.message)
  }
  fileInput.value.value = ''
}
</script>

<template>
  <div class="flex h-screen bg-white">
    <!-- Sidebar toggle button (always visible) -->
    <button
      @click="sidebarVisible = !sidebarVisible"
      class="flex-shrink-0 w-8 h-full flex items-center justify-center border-r bg-gray-50 hover:bg-gray-100 transition-colors cursor-pointer group"
      :title="sidebarVisible ? '隐藏侧边栏' : '显示侧边栏'"
    >
      <span class="text-gray-400 text-xs group-hover:text-gray-600 transition-colors">
        {{ sidebarVisible ? '◀' : '▶' }}
      </span>
    </button>

    <!-- Sidebar -->
    <div
      :style="{ width: sidebarVisible ? sidebarWidth + 'px' : '0px' }"
      class="flex-shrink-0"
    >
      <div class="h-full">
        <Sidebar ref="sidebarRef" @select-page="selectPage" @open-vocab="showVocabReview = true; currentPageId = null; currentPage = null" />
      </div>
    </div>

    <main class="flex-1 flex flex-col min-w-0">
      <template v-if="showVocabReview">
        <VocabReview @close="showVocabReview = false" />
      </template>
      <template v-else-if="currentPage">
        <header class="px-8 py-4 border-b flex items-center gap-3">
          <input
            v-model="currentPage.title"
            @blur="updateTitle"
            @keyup.enter="$event.target.blur()"
            class="text-2xl font-bold bg-transparent border-none outline-none flex-1"
            placeholder="无标题"
          />
          <button
            @click="exportMd"
            class="text-sm text-gray-400 hover:text-gray-600 px-2 py-1 rounded hover:bg-gray-100"
            title="导出 Markdown"
          >
            ⬇ 导出
          </button>
          <button
            @click="triggerImport"
            class="text-sm text-gray-400 hover:text-gray-600 px-2 py-1 rounded hover:bg-gray-100"
            title="导入 Markdown"
          >
            ⬆ 导入
          </button>
          <button
            @click="deleteCurrentPage"
            class="text-sm text-red-400 hover:text-red-600 opacity-0 hover:opacity-100 transition-opacity"
          >
            🗑 删除
          </button>
        </header>
        <BlockEditor
          :pageId="currentPageId"
          :blocks="pageBlocks"
          @blocks-changed="refreshBlocks"
        />
      </template>
      <div v-else class="flex-1 flex items-center justify-center text-gray-400">
        <p>选择或创建一个页面开始写作 ✍️</p>
      </div>
    </main>
    <input
      ref="fileInput"
      type="file"
      accept=".md"
      class="hidden"
      @change="handleImport"
    />
  </div>
</template>
