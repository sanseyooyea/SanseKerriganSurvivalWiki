<template>
  <div v-if="ranks" class="inline-flex items-center gap-1">
    <span class="rank-badge" :class="tierClass(ranks.survivor?.tier)" :title="`生存者: ${ranks.survivor?.tier} (${cores?.survivor || '?'})`">
      {{ tierIcon(ranks.survivor?.tier) }}
    </span>
    <span class="rank-badge" :class="tierClass(ranks.kerrigan?.tier)" :title="`凯瑞甘: ${ranks.kerrigan?.tier} (${cores?.kerrigan || '?'})`">
      {{ tierIcon(ranks.kerrigan?.tier) }}
    </span>
  </div>
  <span v-else-if="showUnranked" class="text-xs text-gray-300" title="未定级">-</span>
</template>

<script setup lang="ts">
const props = defineProps<{
  handle?: string
  showUnranked?: boolean
}>()

const ranks = ref<any>(null)
const cores = ref<any>(null)

onMounted(async () => {
  if (!props.handle) return
  try {
    const data = await $fetch<any>('/api/mmr', { params: { handle: props.handle } })
    if (data) {
      ranks.value = data.ranks
      cores.value = data.cores
    }
  } catch {}
})

function tierIcon(tier?: string) {
  const map: Record<string, string> = {
    '青铜': 'B', '白银': 'S', '黄金': 'G', '白金': 'P', '钻石': 'D', '大师': 'M', '宗师': 'GM'
  }
  return map[tier || ''] || '?'
}

function tierClass(tier?: string) {
  const map: Record<string, string> = {
    '青铜': 'tier-bronze', '白银': 'tier-silver', '黄金': 'tier-gold',
    '白金': 'tier-platinum', '钻石': 'tier-diamond', '大师': 'tier-master', '宗师': 'tier-gm'
  }
  return map[tier || ''] || 'tier-unranked'
}
</script>

<style scoped>
.rank-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.25rem;
  height: 1.25rem;
  border-radius: 0.25rem;
  font-size: 0.625rem;
  font-weight: 700;
  cursor: default;
}
.tier-bronze { background: #cd7f32; color: white; }
.tier-silver { background: #c0c0c0; color: #333; }
.tier-gold { background: #ffd700; color: #333; }
.tier-platinum { background: #4dd0e1; color: #333; }
.tier-diamond { background: #7c4dff; color: white; }
.tier-master { background: #e91e63; color: white; }
.tier-gm { background: #ff6f00; color: white; }
.tier-unranked { background: #e5e7eb; color: #9ca3af; }
</style>
