<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api'
import PageTreeItem from './PageTreeItem.vue'

const emit = defineEmits(['select-page', 'open-vocab'])

const pages = ref([])

async function loadTree() {
  pages.value = await api.getPageTree()
}

async function addPage(parentId = null) {
  await api.createPage({ title: '无标题', parent_page_id: parentId })
  await loadTree()
}

onMounted(loadTree)

defineExpose({ loadTree })
</script>

<template>
  <aside class="h-full bg-gray-50 border-r flex flex-col flex-shrink-0">
    <div class="p-4 font-bold text-lg border-b text-gray-800">📒 Notion-Lite</div>
    <button
      @click="emit('open-vocab')"
      class="mx-2 mt-2 px-3 py-2 rounded-lg text-sm text-left bg-gradient-to-r from-blue-50 to-indigo-50 hover:from-blue-100 hover:to-indigo-100 border border-blue-200 transition-all flex items-center gap-2"
    >
      <span class="text-lg">📖</span>
      <span class="font-medium text-blue-700">单词复习</span>
    </button>
    <div class="flex-1 overflow-y-auto overflow-x-auto p-2">
      <PageTreeItem
        v-for="page in pages"
        :key="page.id"
        :page="page"
        :depth="0"
        :siblings="pages"
        @select="emit('select-page', $event)"
        @add-child="addPage"
        @refresh="loadTree"
      />
    </div>
    <div class="p-3 border-t">
      <button
        @click="addPage(null)"
        class="w-full text-left text-sm text-gray-500 hover:bg-gray-200 px-2 py-1 rounded transition-colors"
      >
        + 新建页面
      </button>
    </div>
  </aside>
</template>
