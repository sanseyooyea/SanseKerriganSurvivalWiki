<template>
  <div class="space-y-1.5">
    <div v-for="r in roles" :key="r.role_id"
      class="flex items-center gap-3 py-1.5 px-2 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition">
      <img :src="`/icons/${roleIcon(r.role_name)}.png`" class="w-7 h-7 rounded" :alt="r.role_name" />
      <span class="text-sm font-medium text-gray-800 dark:text-gray-200 w-24 truncate">{{ roleName(r.role_name) }}</span>
      <span class="text-sm font-mono font-bold text-gray-900 dark:text-gray-100 w-14 text-right">{{ r.mmr }}</span>
      <div class="flex-1 mx-2">
        <div class="h-1.5 rounded-full bg-gray-100 dark:bg-gray-700 overflow-hidden">
          <div class="h-full rounded-full" :class="team === 'survivor' ? 'bg-survivor-400' : 'bg-kerrigan-400'"
            :style="`width: ${Math.min(r.win_rate * 100, 100)}%`" />
        </div>
      </div>
      <span class="text-xs font-mono w-10 text-right" :class="r.win_rate >= 0.5 ? 'text-green-600' : 'text-red-500'">
        {{ (r.win_rate * 100).toFixed(0) }}%
      </span>
      <span class="text-xs text-gray-400 w-10 text-right">{{ r.plays }}场</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import iconMap from '~/data/role-icon-map.json'
import nameMap from '~/data/role-name-map.json'

defineProps<{
  roles: any[]
  team: 'survivor' | 'kerrigan'
}>()

function roleIcon(name: string): string {
  const map = iconMap as Record<string, string>
  return map[name] || map[name.replace(/ /g, '_')] || '00'
}

function roleName(name: string): string {
  const map = nameMap as Record<string, string>
  return map[name] || map[name.replace(/ /g, '_')] || name
}
</script>
