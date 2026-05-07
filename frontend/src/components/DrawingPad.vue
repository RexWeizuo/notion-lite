<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'

const emit = defineEmits(['close', 'save'])

const canvasRef = ref(null)
const containerRef = ref(null)
const isDrawing = ref(false)
const tool = ref('pen')
const color = ref('#000000')
const lineWidth = ref(3)
let ctx = null
let lastX = 0
let lastY = 0
let resizeObserver = null

function initCanvas() {
  const canvas = canvasRef.value
  const container = containerRef.value
  if (!canvas || !container) return

  // Save existing drawing
  let savedImage = null
  if (ctx && canvas.width > 0 && canvas.height > 0) {
    savedImage = ctx.getImageData(0, 0, canvas.width, canvas.height)
  }

  const w = container.clientWidth
  const h = container.clientHeight
  if (w === 0 || h === 0) return

  // 1:1 pixel mapping — canvas internal size = CSS display size
  canvas.width = w
  canvas.height = h
  canvas.style.width = w + 'px'
  canvas.style.height = h + 'px'

  ctx = canvas.getContext('2d')
  ctx.lineCap = 'round'
  ctx.lineJoin = 'round'

  if (savedImage) {
    const temp = document.createElement('canvas')
    temp.width = savedImage.width
    temp.height = savedImage.height
    const tctx = temp.getContext('2d')
    tctx.putImageData(savedImage, 0, 0)
    ctx.drawImage(temp, 0, 0, w, h)
  } else {
    ctx.fillStyle = '#ffffff'
    ctx.fillRect(0, 0, w, h)
  }
}

onMounted(async () => {
  await nextTick()
  initCanvas()
  resizeObserver = new ResizeObserver(() => initCanvas())
  if (containerRef.value) resizeObserver.observe(containerRef.value)

  const onKey = (e) => { if (e.key === 'Escape') emit('close') }
  window.addEventListener('keydown', onKey)
  onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
})

function getPos(e) {
  const rect = canvasRef.value.getBoundingClientRect()
  const clientX = e.touches ? e.touches[0].clientX : e.clientX
  const clientY = e.touches ? e.touches[0].clientY : e.clientY
  return { x: clientX - rect.left, y: clientY - rect.top }
}

function startDraw(e) {
  e.preventDefault()
  isDrawing.value = true
  const pos = getPos(e)
  lastX = pos.x
  lastY = pos.y
}

function draw(e) {
  if (!isDrawing.value || !ctx) return
  e.preventDefault()
  const pos = getPos(e)
  ctx.strokeStyle = tool.value === 'eraser' ? '#ffffff' : color.value
  ctx.lineWidth = tool.value === 'eraser' ? lineWidth.value * 3 : lineWidth.value
  ctx.beginPath()
  ctx.moveTo(lastX, lastY)
  ctx.lineTo(pos.x, pos.y)
  ctx.stroke()
  lastX = pos.x
  lastY = pos.y
}

function stopDraw() {
  isDrawing.value = false
}

function clearCanvas() {
  if (!ctx) return
  const canvas = canvasRef.value
  ctx.fillStyle = '#ffffff'
  ctx.fillRect(0, 0, canvas.width, canvas.height)
}

function insertDrawing() {
  const canvas = canvasRef.value
  if (!canvas) return
  canvas.toBlob(async (blob) => {
    if (!blob) return
    try {
      const { api } = await import('../api')
      const file = new File([blob], `drawing-${Date.now()}.png`, { type: 'image/png' })
      const result = await api.uploadImage(file)
      emit('save', result.url)
    } catch (err) {
      alert('上传失败: ' + err.message)
    }
  }, 'image/png')
}
</script>

<template>
  <div class="fixed inset-0 z-50 flex flex-col bg-white select-none">
    <!-- Toolbar -->
    <div class="flex items-center gap-3 px-4 py-2 border-b bg-gray-50 flex-shrink-0">
      <span class="text-sm font-semibold text-gray-600">✏️ 手写画板</span>
      <span class="w-px bg-gray-300 h-5 mx-1"></span>

      <button
        @click="tool = 'pen'"
        :class="tool === 'pen' ? 'bg-blue-100 text-blue-700' : 'hover:bg-gray-200'"
        class="px-3 py-1 rounded text-sm transition-colors"
      >✒️ 笔</button>
      <button
        @click="tool = 'eraser'"
        :class="tool === 'eraser' ? 'bg-blue-100 text-blue-700' : 'hover:bg-gray-200'"
        class="px-3 py-1 rounded text-sm transition-colors"
      >🧹 橡皮</button>

      <span class="w-px bg-gray-300 h-5 mx-1"></span>

      <label class="flex items-center gap-1 text-sm text-gray-600">
        颜色 <input v-model="color" type="color" class="w-6 h-6 rounded cursor-pointer border-0" />
      </label>
      <label class="flex items-center gap-1 text-sm text-gray-600">
        粗细
        <select v-model.number="lineWidth" class="border rounded px-1 py-0.5 text-sm">
          <option :value="1">细</option>
          <option :value="3">中</option>
          <option :value="6">粗</option>
          <option :value="12">特粗</option>
        </select>
      </label>

      <div class="flex-1"></div>

      <button @click="clearCanvas" class="px-3 py-1 rounded text-sm text-red-500 hover:bg-red-50 transition-colors">
        🗑 清空
      </button>
      <button @click="insertDrawing" class="px-4 py-1 rounded text-sm bg-blue-500 text-white hover:bg-blue-600 transition-colors">
        ✅ 插入
      </button>
      <button @click="emit('close')" class="px-3 py-1 rounded text-sm text-gray-500 hover:bg-gray-200 transition-colors">
        ✕ 关闭
      </button>
    </div>

    <!-- Canvas fills remaining space -->
    <div ref="containerRef" class="flex-1 bg-white overflow-hidden">
      <canvas
        ref="canvasRef"
        class="block cursor-crosshair touch-none"
        @mousedown="startDraw"
        @mousemove="draw"
        @mouseup="stopDraw"
        @mouseleave="stopDraw"
        @touchstart.prevent="startDraw"
        @touchmove.prevent="draw"
        @touchend="stopDraw"
      />
    </div>
  </div>
</template>
