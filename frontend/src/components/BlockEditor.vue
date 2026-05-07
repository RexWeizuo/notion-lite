<script setup>
import { useEditor, EditorContent } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import Image from '@tiptap/extension-image'
import { watch, onBeforeUnmount, ref } from 'vue'
import { api } from '../api'
import DrawingPad from './DrawingPad.vue'

const props = defineProps({ pageId: String, blocks: Array })
const emit = defineEmits(['blocks-changed'])

const pageTitle = ref('无标题')

const editor = useEditor({
  extensions: [StarterKit.configure({ heading: { levels: [1, 2, 3] } }), Image],
  content: null,
  editable: true,
})

let saveTimer = null

function blocksToHtml(blocks) {
  if (!blocks?.length) return '<p></p>'
  return blocks
    .map((b) => {
      const text = jsonToText(b.content)
      switch (b.type) {
        case 'heading_1':
          return `<h1>${text}</h1>`
        case 'heading_2':
          return `<h2>${text}</h2>`
        case 'heading_3':
          return `<h3>${text}</h3>`
        case 'bullet_list':
          return `<ul><li>${text}</li></ul>`
        case 'numbered_list':
          return `<ol><li>${text}</li></ol>`
        case 'code':
          return `<pre><code>${text}</code></pre>`
        case 'quote':
          return `<blockquote>${text}</blockquote>`
        case 'divider':
          return '<hr>'
        default:
          return `<p>${text}</p>`
      }
    })
    .join('')
}

function jsonToText(content) {
  if (!content?.content) return ''
  return content.content.map((n) => n.text || '').join('')
}

async function saveContent() {
  if (!props.pageId) return
  clearTimeout(saveTimer)
  saveTimer = setTimeout(async () => {
    const json = editor.value?.getJSON()
    if (!json) return
    // Full save: delete existing blocks, recreate as one paragraph block
    const existing = await api.getBlocks(props.pageId)
    for (const b of existing) {
      await api.deleteBlock(props.pageId, b.id)
    }
    await api.createBlock(props.pageId, { type: 'paragraph', content: json })
    emit('blocks-changed')
  }, 500)
}

async function loadBlocks() {
  if (!props.pageId || !editor.value) return
  const blocks = await api.getBlocks(props.pageId)
  if (blocks?.length > 0) {
    // Use the first block's content JSON directly (it stores the full TipTap doc)
    const content = blocks[0].content
    if (content && content.type === 'doc') {
      editor.value.commands.setContent(content)
    } else {
      // Fallback: convert blocks to HTML
      editor.value.commands.setContent(blocksToHtml(blocks))
    }
  } else {
    editor.value.commands.setContent('<p></p>')
  }
}

watch(() => props.pageId, loadBlocks)

onBeforeUnmount(() => editor.value?.destroy())

defineExpose({ editor })

// Image upload
const imageInput = ref(null)

function triggerImageUpload() {
  imageInput.value?.click()
}

async function handleImageUpload(e) {
  const file = e.target.files?.[0]
  if (!file) return
  try {
    const result = await api.uploadImage(file)
    editor.value?.chain().focus().setImage({ src: result.url }).run()
  } catch (err) {
    alert('图片上传失败: ' + err.message)
  }
  imageInput.value.value = ''
}

// Drawing pad
const showDrawingPad = ref(false)

function onDrawingSave(url) {
  editor.value?.chain().focus().setImage({ src: url }).run()
  showDrawingPad.value = false
}
</script>

<template>
  <div class="flex-1 overflow-y-auto">
    <div class="max-w-3xl mx-auto px-8 py-6">
      <!-- Toolbar -->
      <div v-if="editor" class="flex gap-1 mb-4 border-b pb-2 flex-wrap">
        <button
          @click="editor.chain().focus().toggleHeading({ level: 1 }).run()"
          :class="{ 'bg-gray-200': editor.isActive('heading', { level: 1 }) }"
          class="px-2 py-1 rounded text-sm hover:bg-gray-100"
        >
          H1
        </button>
        <button
          @click="editor.chain().focus().toggleHeading({ level: 2 }).run()"
          :class="{ 'bg-gray-200': editor.isActive('heading', { level: 2 }) }"
          class="px-2 py-1 rounded text-sm hover:bg-gray-100"
        >
          H2
        </button>
        <button
          @click="editor.chain().focus().toggleHeading({ level: 3 }).run()"
          :class="{ 'bg-gray-200': editor.isActive('heading', { level: 3 }) }"
          class="px-2 py-1 rounded text-sm hover:bg-gray-100"
        >
          H3
        </button>
        <span class="w-px bg-gray-300 mx-1"></span>
        <button
          @click="editor.chain().focus().toggleBulletList().run()"
          :class="{ 'bg-gray-200': editor.isActive('bulletList') }"
          class="px-2 py-1 rounded text-sm hover:bg-gray-100"
        >
          • 列表
        </button>
        <button
          @click="editor.chain().focus().toggleOrderedList().run()"
          :class="{ 'bg-gray-200': editor.isActive('orderedList') }"
          class="px-2 py-1 rounded text-sm hover:bg-gray-100"
        >
          1. 编号
        </button>
        <button
          @click="editor.chain().focus().toggleCodeBlock().run()"
          :class="{ 'bg-gray-200': editor.isActive('codeBlock') }"
          class="px-2 py-1 rounded text-sm hover:bg-gray-100"
        >
          &lt;/&gt;
        </button>
        <button
          @click="editor.chain().focus().toggleBlockquote().run()"
          :class="{ 'bg-gray-200': editor.isActive('blockquote') }"
          class="px-2 py-1 rounded text-sm hover:bg-gray-100"
        >
          " 引用
        </button>
        <button
          @click="editor.chain().focus().setHorizontalRule().run()"
          class="px-2 py-1 rounded text-sm hover:bg-gray-100"
        >
          ―
        </button>
        <button
          @click="triggerImageUpload"
          class="px-2 py-1 rounded text-sm hover:bg-gray-100"
          title="插入图片"
        >
          📷
        </button>
        <button
          @click="showDrawingPad = true"
          class="px-2 py-1 rounded text-sm hover:bg-gray-100"
          title="手写画板"
        >
          ✏️
        </button>
      </div>
      <!-- Editor -->
      <EditorContent :editor="editor" class="prose max-w-none" @input="saveContent" />
      <input
        ref="imageInput"
        type="file"
        accept="image/*"
        class="hidden"
        @change="handleImageUpload"
      />
    </div>
    <!-- Drawing Pad overlay -->
    <DrawingPad
      v-if="showDrawingPad"
      @close="showDrawingPad = false"
      @save="onDrawingSave"
    />
  </div>
</template>

<style>
.ProseMirror {
  outline: none;
  min-height: 300px;
}
.ProseMirror h1 { font-size: 1.875rem; font-weight: 700; margin: 1rem 0 0.5rem; }
.ProseMirror h2 { font-size: 1.5rem; font-weight: 600; margin: 0.75rem 0 0.5rem; }
.ProseMirror h3 { font-size: 1.25rem; font-weight: 600; margin: 0.5rem 0 0.25rem; }
.ProseMirror p { margin: 0.25rem 0; line-height: 1.75; }
.ProseMirror ul, .ProseMirror ol { padding-left: 1.5rem; margin: 0.25rem 0; }
.ProseMirror blockquote {
  border-left: 3px solid #d1d5db;
  padding-left: 1rem;
  color: #6b7280;
  margin: 0.5rem 0;
}
.ProseMirror pre {
  background: #1f2937;
  color: #f3f4f6;
  padding: 1rem;
  border-radius: 0.5rem;
  margin: 0.5rem 0;
  font-family: 'Fira Code', monospace;
  font-size: 0.875rem;
}
.ProseMirror code { background: #f3f4f6; padding: 0.125rem 0.25rem; border-radius: 0.25rem; }
.ProseMirror pre code { background: none; padding: 0; }
.ProseMirror hr { border: none; border-top: 1px solid #e5e7eb; margin: 1rem 0; }
</style>
