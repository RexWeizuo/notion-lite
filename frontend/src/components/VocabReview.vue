<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api'

const stats = ref({ categories: {}, total: 0, due: 0 })
const words = ref([])
const currentIndex = ref(0)
const currentRound = ref(1)
const dailyNew = ref(50)
const showSettings = ref(false)
const revealed = ref(false)
const reviewed = ref(false)
const userNotes = ref('')
const userMeaning = ref('')
const done = ref(false)
const sessionStats = ref({ known: 0, unknown: 0, mastered: 0 })
const selectedAction = ref('')
const wordDetail = ref(null)

onMounted(loadData)

async function loadData() {
  try {
    stats.value = await api.vocabStats()
    const tasks = await api.vocabDailyTasks()
    dailyNew.value = tasks.settings.daily_new_words
    currentRound.value = tasks.round
    words.value = tasks.words || []
    if (tasks.done || words.value.length === 0) { done.value = true; return }
    currentIndex.value = 0
    revealed.value = false
    reviewed.value = false
    selectedAction.value = ''
    done.value = false
    sessionStats.value = { known: 0, unknown: 0, mastered: 0 }

    // Pre-fill existing notes
    if (words.value.length > 0 && words.value[0]) {
      userNotes.value = words.value[0].user_notes || ''
    }
  } catch (e) { console.error('Vocab load error:', e) }
}

const currentWord = computed(() => words.value[currentIndex.value] || null)

async function fetchWordDetail() {
  if (!currentWord.value) return
  try {
    const blocks = await api.getBlocks(currentWord.value.id)
    if (blocks?.length) wordDetail.value = parseBlocks(blocks[0])
  } catch (e) { wordDetail.value = null }
}

function parseBlocks(block) {
  const content = block?.content
  if (!content?.content) return { cn: '', en: '', examples: [], collocations: [], root: '' }
  const nodes = content.content
  const result = { cn: '', en: '', examples: [], collocations: [], root: '' }
  let inExamples = false, inCollocations = false
  for (const node of nodes) {
    const text = extractText(node)
    if (node.type === 'paragraph') {
      if (text.startsWith('🇨🇳')) result.cn = text.replace('🇨🇳 ', '')
      else if (text.startsWith('🇬🇧')) result.en = text.replace('🇬🇧 ', '')
      else if (text.startsWith('📐')) result.root = text
    } else if (node.type === 'heading') {
      if (text.includes('例句')) { inExamples = true; inCollocations = false; continue }
      if (text.includes('搭配')) { inCollocations = true; inExamples = false; continue }
      inExamples = false; inCollocations = false
    } else if (node.type === 'bulletList') {
      const t = extractDeepText(node)
      if (inCollocations && t) result.collocations.push(t)
    } else if (node.type === 'blockquote') {
      const t = extractDeepText(node)
      if (inExamples && t) result.examples.push(t)
    }
  }
  return result
}

function extractText(node) { return (node.content || []).map(n => n.text || '').join('') }
function extractDeepText(node) {
  if (!node) return ''
  if (node.type === 'text') return node.text || ''
  if (node.content) return node.content.map(extractDeepText).join('')
  return ''
}

function revealAnswer() {
  revealed.value = true
  fetchWordDetail()
  // Load existing notes from word data
  if (currentWord.value) {
    userNotes.value = currentWord.value.user_notes || ''
    userMeaning.value = currentWord.value.user_meaning || userMeaning.value
  }
}

function selectAction(action) {
  selectedAction.value = action
}

async function confirmReview() {
  const word = currentWord.value
  if (!word || !selectedAction.value) return

  const known = selectedAction.value === 'known' || selectedAction.value === 'mastered'
  const mastered = selectedAction.value === 'mastered'

  // Update stats
  if (mastered) sessionStats.value.mastered++
  else if (known) sessionStats.value.known++
  else sessionStats.value.unknown++

  // Save to API
  await api.vocabReview(word.id, {
    known,
    mastered,
    round: currentRound.value,
    user_notes: userNotes.value,
    user_meaning: userMeaning.value,
  })

  // Move to next word
  userNotes.value = ''
  userMeaning.value = ''
  revealed.value = false
  reviewed.value = false
  selectedAction.value = ''
  wordDetail.value = null

  if (currentIndex.value + 1 >= words.value.length) {
    await loadData()
  } else {
    currentIndex.value++
    // Pre-fill notes for next word
    const next = words.value[currentIndex.value]
    if (next) userNotes.value = next.user_notes || ''
  }
}

async function saveSettings() {
  await api.vocabUpdateSettings({ daily_new_words: dailyNew.value })
  showSettings.value = false
  loadData()
}

async function resetSession() {
  await api.vocabReset()
  done.value = false
  sessionStats.value = { known: 0, unknown: 0, mastered: 0 }
  loadData()
}

const progressPercent = computed(() => {
  if (!words.value.length) return 0
  return Math.round((currentIndex.value / words.value.length) * 100)
})
</script>

<template>
  <div class="flex-1 flex flex-col items-center" style="background: #f5efe0; min-height: 100%; padding: 40px 24px;">
    <div style="max-width: 640px; width: 100%;">
      <!-- Header -->
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; padding-bottom: 12px; border-bottom: 1px solid rgba(201,168,76,0.3);">
        <div style="display: flex; align-items: center; gap: 12px;">
          <span style="font-size: 1.4rem; font-weight: 700; color: #2c1810; letter-spacing: 3px; font-family: 'Noto Serif SC', serif;">📖 单词复习</span>
          <span v-if="!done && currentRound" style="font-size: 0.82rem; color: #c23a2b; background: rgba(194,58,43,0.08); border: 1px solid rgba(194,58,43,0.15); padding: 4px 12px; border-radius: 2px; font-weight: 500;">
            第{{ currentRound }}轮
          </span>
        </div>
        <div style="display: flex; gap: 8px;">
          <button @click="showSettings = !showSettings" style="background: none; border: none; color: #8a7560; cursor: pointer; font-size: 0.9rem; padding: 4px 8px;">⚙️</button>
        </div>
      </div>

      <!-- Stats -->
      <div style="display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap;">
        <div v-for="(count, cat) in stats.categories" :key="cat"
          style="flex: 1; min-width: 60px; text-align: center; background: white; border-radius: 2px; padding: 8px 6px; border: 1px solid rgba(201,168,76,0.2); box-shadow: 0 2px 8px rgba(44,24,16,0.08);">
          <div style="font-size: 1.1rem; font-weight: 700;"
            :style="{ color: cat === '还没学习' ? '#8a7560' : cat === '一轮掌握' ? '#3b4d8f' : cat === '二轮掌握' ? '#5a8a6a' : cat === '三轮掌握' ? '#c9a84c' : '#c23a2b' }">
            {{ count }}
          </div>
          <div style="font-size: 0.7rem; color: #8a7560;">{{ cat }}</div>
        </div>
      </div>

      <!-- Progress bar -->
      <div v-if="!done && words.length" style="background: #e8dcc8; border-radius: 2px; height: 4px; margin-bottom: 24px; overflow: hidden; border: 1px solid rgba(201,168,76,0.3);">
        <div :style="{ background: 'linear-gradient(90deg, #c23a2b, #c9a84c)', height: '100%', width: progressPercent + '%', transition: 'width 0.4s ease' }"></div>
      </div>

      <!-- Settings -->
      <div v-if="showSettings" style="background: white; border: 1px solid rgba(201,168,76,0.3); border-radius: 4px; padding: 16px; margin-bottom: 16px; box-shadow: 0 2px 8px rgba(44,24,16,0.08);">
        <label style="display: flex; align-items: center; gap: 12px; font-size: 0.9rem; color: #4a3228;">
          每日新词
          <input v-model.number="dailyNew" type="number" min="1" max="500"
            style="width: 70px; padding: 8px 12px; background: #e8dcc8; border: 2px solid rgba(201,168,76,0.3); border-radius: 4px; color: #2c1810; font-size: 0.95rem; text-align: center; outline: none;" />
          <button @click="saveSettings"
            style="background: #c23a2b; color: white; border: none; padding: 8px 18px; border-radius: 4px; font-size: 0.9rem; font-weight: 600; cursor: pointer;">保存</button>
        </label>
      </div>

      <!-- Done state -->
      <div v-if="done" style="background: white; border: 1px solid rgba(201,168,76,0.3); border-radius: 4px; padding: 60px 40px; text-align: center; box-shadow: 0 2px 8px rgba(44,24,16,0.08); position: relative; overflow: hidden;">
        <div style="position: absolute; top: 0; left: 0; right: 0; height: 3px; background: linear-gradient(90deg, #c23a2b, #c9a84c);"></div>
        <div style="font-size: 3rem; margin-bottom: 16px;">🎉</div>
        <h2 style="font-family: 'Noto Serif SC', serif; font-size: 1.3rem; color: #2c1810; margin-bottom: 8px; letter-spacing: 2px;">今日任务完成</h2>
        <p style="color: #8a7560; margin-bottom: 24px; font-size: 0.9rem;">
          认识 {{ sessionStats.known }} · 不认识 {{ sessionStats.unknown }} · 已掌握 {{ sessionStats.mastered }}
        </p>
        <div style="display: flex; gap: 12px; justify-content: center;">
          <button @click="loadData" style="background: rgba(44,24,16,0.06); color: #4a3228; border: 1px solid rgba(44,24,16,0.12); padding: 12px 28px; border-radius: 4px; font-size: 0.95rem; font-weight: 600; cursor: pointer; transition: all 0.3s;">🔄 刷新</button>
          <button @click="resetSession" style="background: rgba(44,24,16,0.06); color: #4a3228; border: 1px solid rgba(44,24,16,0.12); padding: 12px 28px; border-radius: 4px; font-size: 0.95rem; font-weight: 600; cursor: pointer; transition: all 0.3s;">🔁 重新开始</button>
        </div>
      </div>

      <!-- Word card -->
      <div v-else-if="currentWord" style="background: white; border: 1px solid rgba(201,168,76,0.3); border-radius: 4px; overflow: hidden; box-shadow: 0 2px 8px rgba(44,24,16,0.08); position: relative;">
        <!-- Top accent bar -->
        <div style="position: absolute; top: 0; left: 0; right: 0; height: 3px; background: linear-gradient(90deg, #c23a2b, #c9a84c);"></div>

        <!-- Badges -->
        <div style="display: flex; justify-content: space-between; padding: 20px 24px 0;">
          <span v-if="currentWord.category && currentWord.category !== '还没学习'" style="font-size: 0.82rem; color: #c9a84c; background: rgba(201,168,76,0.1); border: 1px solid rgba(201,168,76,0.2); padding: 4px 14px; border-radius: 2px; font-weight: 500;">
            {{ currentWord.category }}
          </span>
          <span v-else></span>
          <span style="font-size: 0.82rem; color: #c23a2b; background: rgba(194,58,43,0.08); border: 1px solid rgba(194,58,43,0.15); padding: 4px 14px; border-radius: 2px; font-weight: 500;">
            第{{ currentWord.review_count || 0 }}次
          </span>
        </div>

        <!-- Word text -->
        <div style="padding: 40px 40px 32px; text-align: center;">
          <h1 style="font-family: 'Noto Serif SC', serif; font-size: 3.5rem; font-weight: 900; color: #2c1810; letter-spacing: 2px; margin: 0;">{{ currentWord.title }}</h1>
        </div>

        <!-- Step 1: Input + Reveal button -->
        <div v-if="!revealed" style="padding: 0 40px 32px; display: flex; flex-direction: column; align-items: center; gap: 16px;">
          <input v-model="userMeaning"
            style="width: 100%; max-width: 380px; padding: 16px 20px; background: #f5efe0; border: 2px solid rgba(201,168,76,0.3); border-radius: 4px; color: #2c1810; font-size: 1.05rem; outline: none; text-align: center;"
            placeholder="输入释义…" />
          <button @click="revealAnswer"
            style="width: 100%; max-width: 280px; padding: 14px 32px; background: #c23a2b; color: white; border: none; border-radius: 4px; font-size: 1rem; font-weight: 600; cursor: pointer; box-shadow: 0 4px 12px rgba(194,58,43,0.2); transition: all 0.3s;">
            👁 显示答案
          </button>
        </div>

        <!-- Step 2: Answer + Notes + Review buttons + Confirm -->
        <div v-if="revealed && !reviewed" style="padding: 0 40px 32px;">
          <!-- Meanings -->
          <div style="padding: 24px; background: rgba(245,239,224,0.5); border: 1px solid rgba(201,168,76,0.15); border-radius: 4px; margin-bottom: 20px;">
            <p v-if="wordDetail?.cn" style="font-size: 1.2rem; color: #2c1810; font-weight: 500; line-height: 1.6; margin: 0 0 8px;">{{ wordDetail.cn }}</p>
            <p v-if="wordDetail?.en" style="font-size: 0.95rem; color: #8a7560; font-style: italic; line-height: 1.6; margin: 0 0 12px;">{{ wordDetail.en }}</p>
            <div v-if="wordDetail?.examples?.length" style="margin-top: 12px; padding-top: 12px; border-top: 1px solid rgba(201,168,76,0.2);">
              <p style="font-size: 0.82rem; color: #c23a2b; font-weight: 600; letter-spacing: 1px; margin-bottom: 8px;">例句</p>
              <p v-for="(ex, i) in wordDetail.examples" :key="i" style="font-size: 0.9rem; color: #4a3228; line-height: 1.6; margin: 0 0 4px; padding-left: 16px;">"{{ ex }}"</p>
            </div>
            <div v-if="wordDetail?.collocations?.length" style="margin-top: 10px;">
              <p style="font-size: 0.82rem; color: #c9a84c; font-weight: 600; letter-spacing: 1px; margin-bottom: 4px;">搭配</p>
              <p style="font-size: 0.85rem; color: #4a3228;">{{ wordDetail.collocations.join(' · ') }}</p>
            </div>
            <p v-if="wordDetail?.root" style="font-size: 0.8rem; color: #8a7560; margin-top: 8px;">{{ wordDetail.root }}</p>
          </div>

          <!-- Notes -->
          <textarea v-model="userNotes" rows="2"
            style="width: 100%; padding: 14px 16px; background: #f5efe0; border: 2px solid rgba(201,168,76,0.3); border-radius: 4px; color: #2c1810; font-size: 0.95rem; outline: none; resize: none; box-shadow: 0 2px 8px rgba(44,24,16,0.08); margin-bottom: 16px;"
            placeholder="添加备注…"></textarea>

          <!-- Review buttons -->
          <div style="display: flex; gap: 12px; justify-content: center; flex-wrap: wrap; margin-bottom: 16px;">
            <button @click="selectAction('unknown')"
              :style="{ flex: 1, minWidth: '100px', padding: '14px 20px', border: '1px solid rgba(194,58,43,0.2)', borderRadius: '4px', fontSize: '0.95rem', fontWeight: 600, cursor: 'pointer', transition: 'all 0.3s',
                background: selectedAction === 'unknown' ? '#c23a2b' : 'rgba(194,58,43,0.1)',
                color: selectedAction === 'unknown' ? 'white' : '#c23a2b' }">
              😕 不认识
            </button>
            <button @click="selectAction('known')"
              :style="{ flex: 1, minWidth: '100px', padding: '14px 20px', border: '1px solid rgba(90,138,106,0.2)', borderRadius: '4px', fontSize: '0.95rem', fontWeight: 600, cursor: 'pointer', transition: 'all 0.3s',
                background: selectedAction === 'known' ? '#5a8a6a' : 'rgba(90,138,106,0.1)',
                color: selectedAction === 'known' ? 'white' : '#5a8a6a' }">
              😊 认识
            </button>
            <button @click="selectAction('mastered')"
              :style="{ flex: 1, minWidth: '100px', padding: '14px 20px', border: '1px solid rgba(201,168,76,0.2)', borderRadius: '4px', fontSize: '0.95rem', fontWeight: 600, cursor: 'pointer', transition: 'all 0.3s',
                background: selectedAction === 'mastered' ? '#c9a84c' : 'rgba(201,168,76,0.1)',
                color: selectedAction === 'mastered' ? 'white' : '#c9a84c' }">
              🎓 已掌握
            </button>
          </div>

          <!-- Confirm button -->
          <button @click="confirmReview"
            :disabled="!selectedAction"
            :style="{ width: '100%', padding: '14px', borderRadius: '4px', fontSize: '1rem', fontWeight: 600, cursor: selectedAction ? 'pointer' : 'not-allowed', transition: 'all 0.3s', border: 'none',
              background: selectedAction ? '#c23a2b' : '#e8dcc8',
              color: selectedAction ? 'white' : '#8a7560',
              boxShadow: selectedAction ? '0 4px 12px rgba(194,58,43,0.2)' : 'none' }">
            ✅ 确定
          </button>
        </div>

      </div>
    </div>
  </div>
</template>
