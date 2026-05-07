<script setup>
import { ref } from 'vue'
import { api } from '../api'

const props = defineProps({
  page: Object,
  depth: { type: Number, default: 0 },
  siblings: Array,  // array of sibling pages at this level
})
const emit = defineEmits(['select', 'add-child', 'refresh'])

const expanded = ref(true)
const dropIndicator = ref(null) // 'above' | 'below' | 'onto' | null

async function handleAddChild() {
  await emit('add-child', props.page.id)
  emit('refresh')
}

function onDragStart(e) {
  e.dataTransfer.setData('text/plain', props.page.id)
  e.dataTransfer.effectAllowed = 'move'
}

function onDragOver(e) {
  e.preventDefault()
  if (!e.dataTransfer.types.includes('text/plain')) return
  e.dataTransfer.dropEffect = 'move'

  const rect = e.currentTarget.getBoundingClientRect()
  const y = e.clientY - rect.top
  const h = rect.height

  if (y < h * 0.25) dropIndicator.value = 'above'
  else if (y > h * 0.75) dropIndicator.value = 'below'
  else dropIndicator.value = 'onto'
}

function onDragLeave() {
  dropIndicator.value = null
}

function resetDropState() {
  dropIndicator.value = null
}

async function onDrop(e) {
  e.preventDefault()
  resetDropState()
  const draggedId = e.dataTransfer.getData('text/plain')
  if (!draggedId || draggedId === props.page.id) return

  // Compute drop mode from pointer position
  const rect = e.currentTarget.getBoundingClientRect()
  const y = e.clientY - rect.top
  const h = rect.height
  let mode = y < h * 0.25 ? 'above' : y > h * 0.75 ? 'below' : 'onto'

  try {
    if (mode === 'onto') {
      await api.movePage(draggedId, { parent_page_id: props.page.id, position: 0 })
    } else {
      const list = props.siblings || []
      const myIndex = list.findIndex(p => p.id === props.page.id)
      const newPos = mode === 'above' ? myIndex : myIndex + 1
      await api.movePage(draggedId, {
        parent_page_id: props.page.parent_page_id || null,
        position: newPos,
      })
    }
    emit('refresh')
  } catch (err) {
    console.error('Move failed:', err)
  }
}
</script>

<template>
  <div>
    <div
      :draggable="true"
      :class="[
        'flex items-center gap-1 px-2 py-1 rounded cursor-pointer hover:bg-gray-200 text-sm group',
        'border border-transparent transition-colors',
        dropIndicator === 'onto' ? 'border-blue-400 bg-blue-50' : '',
      ]"
      :style="{ paddingLeft: (depth * 16 + 8) + 'px' }"
      @click="emit('select', page.id)"
      @dragstart="onDragStart"
      @dragover="onDragOver"
      @dragleave="onDragLeave"
      @drop="onDrop"
    >
      <!-- Drop above indicator -->
      <div
        v-if="dropIndicator === 'above'"
        class="absolute left-0 right-0 top-0 h-0.5 bg-blue-500 -translate-y-px"
        style="margin-left: 0; margin-right: 0"
      />

      <button
        v-if="page.children?.length"
        @click.stop="expanded = !expanded"
        class="text-xs w-4 text-gray-400"
      >
        {{ expanded ? '▾' : '▸' }}
      </button>
      <span v-else class="w-4"></span>
      <span class="mr-1">{{ page.icon || '📄' }}</span>
      <span class="flex-1 text-sm whitespace-nowrap">{{ page.title }}</span>
      <button
        @click.stop="handleAddChild"
        class="opacity-0 group-hover:opacity-100 text-xs text-gray-400 hover:text-gray-600 px-1"
      >
        +
      </button>

      <!-- Drop below indicator -->
      <div
        v-if="dropIndicator === 'below'"
        class="absolute left-0 right-0 bottom-0 h-0.5 bg-blue-500 translate-y-px"
        style="margin-left: 0; margin-right: 0"
      />
    </div>
    <template v-if="expanded && page.children?.length">
      <PageTreeItem
        v-for="child in page.children"
        :key="child.id"
        :page="child"
        :depth="depth + 1"
        :siblings="page.children"
        @select="emit('select', $event)"
        @add-child="emit('add-child', $event)"
        @refresh="emit('refresh')"
      />
    </template>
  </div>
</template>
