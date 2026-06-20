<template>
  <div v-if="unit">
    <a href="javascript:history.back()" class="inline-flex items-center gap-1 text-sm text-gray-400 hover:text-gray-600 transition-colors mb-6">
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
      </svg>
      返回
    </a>

    <div class="wiki-card p-6 mb-6">
      <div class="flex items-center gap-3 mb-4">
        <div class="w-3 h-3 rounded-full" :class="unit.isBuilding ? 'bg-amber-500' : 'bg-green-500'" />
        <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">{{ unit.nameZh || unitId }}</h1>
        <span class="text-xs px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400">
          {{ unit.isEconomy ? '经济建筑' : unit.isBuilding ? '建筑' : '兵种' }}
        </span>
      </div>
      <p v-if="unit.owner" class="text-sm text-gray-500 dark:text-gray-400 mb-4">
        所属英雄：
        <NuxtLink :to="`/classes/${unit.ownerIdx}`" class="text-survivor-600 hover:underline">{{ unit.ownerZh }}</NuxtLink>
      </p>

      <div class="section-title">基础属性</div>
      <table class="w-full text-sm mb-4">
        <tbody class="divide-y divide-gray-100 dark:divide-gray-700">
          <tr v-if="unit.hp">
            <td class="py-2 text-gray-600 dark:text-gray-400">生命值</td>
            <td class="py-2 text-right font-mono font-semibold text-gray-900 dark:text-gray-100">{{ unit.hp }}</td>
          </tr>
          <tr v-if="unit.shield">
            <td class="py-2 text-gray-600 dark:text-gray-400">护盾</td>
            <td class="py-2 text-right font-mono font-semibold text-blue-600 dark:text-blue-400">{{ unit.shield }}</td>
          </tr>
          <tr v-if="unit.armor">
            <td class="py-2 text-gray-600 dark:text-gray-400">护甲</td>
            <td class="py-2 text-right font-mono font-semibold text-gray-900 dark:text-gray-100">{{ unit.armor }}</td>
          </tr>
          <tr v-if="unit.speed">
            <td class="py-2 text-gray-600 dark:text-gray-400">移动速度</td>
            <td class="py-2 text-right font-mono font-semibold text-gray-900 dark:text-gray-100">{{ unit.speed }}</td>
          </tr>
        </tbody>
      </table>
<!-- PLACEHOLDER_WEAPON -->
      <div v-if="unit.damage" class="mt-2">
        <div class="section-title">武器</div>
        <table class="w-full text-sm">
          <tbody class="divide-y divide-gray-100 dark:divide-gray-700">
            <tr>
              <td class="py-2 text-gray-600 dark:text-gray-400">伤害</td>
              <td class="py-2 text-right font-mono font-semibold text-red-600 dark:text-red-400">
                {{ unit.damage }}<span v-if="unit.attackCount && unit.attackCount > 1" class="text-gray-400 font-normal"> ×{{ unit.attackCount }}</span>
              </td>
            </tr>
            <tr v-if="unit.attackSpeed">
              <td class="py-2 text-gray-600 dark:text-gray-400">攻击间隔</td>
              <td class="py-2 text-right font-mono font-semibold text-gray-900 dark:text-gray-100">{{ unit.attackSpeed }}s</td>
            </tr>
            <tr v-if="unit.range != null">
              <td class="py-2 text-gray-600 dark:text-gray-400">射程</td>
              <td class="py-2 text-right font-mono font-semibold text-gray-900 dark:text-gray-100">{{ unit.range }}</td>
            </tr>
            <tr v-if="unit.damage && unit.attackSpeed">
              <td class="py-2 text-gray-600 dark:text-gray-400">DPS</td>
              <td class="py-2 text-right font-mono font-semibold text-orange-600 dark:text-orange-400">{{ (unit.damage * (unit.attackCount || 1) / unit.attackSpeed).toFixed(1) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
  <div v-else class="text-center py-20 text-gray-400">
    <p class="text-lg">单位未找到</p>
  </div>
</template>

<script setup lang="ts">
const route = useRoute()
const unitId = route.params.id as string
const { getForHero } = useUnitData()
const { getAll } = useClassData()

const unit = computed(() => {
  const allClasses = getAll()
  for (const cls of allClasses) {
    const data = getForHero(cls.nameEn)
    const allUnits = [...data.troops, ...data.buildings, ...data.economy]
    for (const u of allUnits) {
      if (u.id === unitId) {
        const isBuilding = data.buildings.some(b => b.id === unitId)
        const isEconomy = data.economy.some(e => e.id === unitId)
        return {
          ...u,
          isBuilding: isBuilding || isEconomy,
          isEconomy,
          owner: cls.nameEn,
          ownerZh: cls.nameZh,
          ownerIdx: cls.id,
        }
      }
    }
  }
  return null
})
</script>
