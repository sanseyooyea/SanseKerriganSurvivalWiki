<template>
  <button @click="$emit('click')" :class="order"
    class="wiki-card relative flex flex-col items-center text-center px-2 sm:px-3 hover:-translate-y-0.5 transition-transform"
    :style="{ paddingTop: isFirst ? '1.5rem' : '1rem', paddingBottom: isFirst ? '1.25rem' : '0.875rem' }">
    <!-- 奖牌 -->
    <div class="absolute -top-3 left-1/2 -translate-x-1/2 w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold shadow-card ring-2 ring-white dark:ring-gray-800"
      :class="medalClass">
      {{ player.rank }}
    </div>
    <!-- 皇冠（仅第一名） -->
    <svg v-if="isFirst" class="w-5 h-5 text-yellow-400 mb-1 mt-2" fill="currentColor" viewBox="0 0 24 24">
      <path d="M5 16L3 7l5.5 4L12 5l3.5 6L21 7l-2 9H5zm0 2h14v2H5v-2z"/>
    </svg>
    <div :class="isFirst ? 'mt-1' : 'mt-4'" class="w-full">
      <div class="font-semibold text-gray-900 dark:text-gray-100 truncate"
        :class="isFirst ? 'text-base' : 'text-sm'">
        {{ player.display_name || '未知玩家' }}
      </div>
      <div v-if="player.identity" class="text-[11px] text-gray-400 dark:text-gray-500 truncate mt-0.5">
        {{ player.identity }}
      </div>
      <div class="font-bold font-mono mt-2" :class="[mmrColor, isFirst ? 'text-2xl' : 'text-xl']">
        {{ player.mmr }}
      </div>
      <div v-if="player.team_name" class="inline-block mt-1.5 px-2 py-0.5 rounded text-[10px] font-medium" :class="tagClass">
        {{ player.team_name }}
      </div>
    </div>
  </button>
</template>

<script setup lang="ts">
const props = defineProps<{
  player: any
  board: 'kerrigan' | 'survivor'
  order: string
}>()
defineEmits<{ click: [] }>()

const isFirst = computed(() => props.player.rank === 1)

const medalClass = computed(() => {
  if (props.player.rank === 1) return 'bg-yellow-400 text-yellow-900'
  if (props.player.rank === 2) return 'bg-gray-300 text-gray-700'
  return 'bg-amber-600 text-amber-50'
})

const mmrColor = computed(() => props.board === 'kerrigan'
  ? 'text-kerrigan-600 dark:text-kerrigan-400'
  : 'text-survivor-600 dark:text-survivor-400')

const tagClass = computed(() => props.board === 'kerrigan'
  ? 'bg-kerrigan-50 text-kerrigan-600 dark:bg-kerrigan-800/30 dark:text-kerrigan-200'
  : 'bg-survivor-50 text-survivor-600 dark:bg-survivor-800/30 dark:text-survivor-200')
</script>
